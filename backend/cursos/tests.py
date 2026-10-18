import os
from datetime import timedelta
from unittest import mock

import jwt
from django.utils import timezone

from cuentas.tests import BaseAuthTest
from .models import ClaseZoom, ParticipanteClase


class InscripcionCursoTests(BaseAuthTest):
    def test_staff_inscribe_y_quita(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.curso.estudiantes.filter(pk=self.beto.pk).exists())

        self.client.post(f'/api/cursos/{self.curso.id}/quitar/', {'estudiante': self.beto.id})
        self.assertFalse(self.curso.estudiantes.filter(pk=self.beto.pk).exists())

    def test_estudiante_invalido(self):
        self.client.force_authenticate(self.staff)
        for valor in ('', 'abc', 99999):
            r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': valor})
            self.assertEqual(r.status_code, 400)

    def test_profesor_no_inscribe(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post(f'/api/cursos/{self.curso.id}/inscribir/', {'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 403)

    def test_inscritos_para_profesor_pero_no_para_estudiante(self):
        self.client.force_authenticate(self.profe)
        r = self.client.get(f'/api/cursos/{self.curso.id}/inscritos/')
        self.assertEqual([e['id'] for e in r.data], [self.ana.id])

        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(f'/api/cursos/{self.curso.id}/inscritos/').status_code, 403)


ZOOM_ENV = {'ZOOM_SDK_KEY': 'clave', 'ZOOM_SDK_SECRET': 'secreto'}


@mock.patch.dict(os.environ, ZOOM_ENV)
class ClaseZoomTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        inicio = timezone.now() + timedelta(hours=1)
        self.clase = ClaseZoom.objects.create(curso=self.curso, titulo='Z1', descripcion='',
                                              fecha_hora_inicio=inicio, session_name='mate-1', password='p1')
        self.clase_ajena = ClaseZoom.objects.create(curso=self.curso_ajeno, titulo='Z2', descripcion='',
                                                    fecha_hora_inicio=inicio, session_name='hist-1', password='p2')

    def unirse(self, clase, **datos):
        return self.client.post(f'/api/clases-zoom/{clase.id}/join/', datos, format='json')

    def rol_en_firma(self, respuesta):
        return jwt.decode(respuesta.data['signature'], 'secreto', algorithms=['HS256'])['role_type']

    def test_estudiante_solo_ve_clases_de_sus_cursos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/clases-zoom/'), {self.clase.id})
        self.assertEqual([c['id'] for c in self.client.get('/api/clases-zoom/upcoming/').data], [self.clase.id])
        self.assertEqual(self.client.get(f'/api/clases-zoom/{self.clase_ajena.id}/').status_code, 404)

        ClaseZoom.objects.update(estado='en_vivo')
        self.assertEqual([c['id'] for c in self.client.get('/api/clases-zoom/live/').data], [self.clase.id])

    def test_estudiante_no_modifica_clases(self):
        self.client.force_authenticate(self.u_ana)
        url = f'/api/clases-zoom/{self.clase.id}/'
        self.assertEqual(self.client.patch(url, {'titulo': 'X'}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.post(url + 'end/').status_code, 403)
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.estado, 'programada')

    def test_estudiante_se_une_como_participante_aunque_pida_ser_anfitrion(self):
        self.client.force_authenticate(self.u_ana)
        r = self.unirse(self.clase, is_host=True, user_name='Profesor')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['role'], self.rol_en_firma(r), r.data['userName']), (0, 0, 'ana'))
        # Un alumno que entra temprano no inicia la clase
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.estado, 'programada')

    def test_estudiante_no_se_une_a_clase_ajena(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.unirse(self.clase_ajena).status_code, 404)

    def test_profesor_se_une_como_anfitrion_e_inicia_la_clase(self):
        self.client.force_authenticate(self.profe)
        r = self.unirse(self.clase)
        self.assertEqual((r.data['role'], self.rol_en_firma(r)), (1, 1))
        self.clase.refresh_from_db()
        self.assertEqual(self.clase.estado, 'en_vivo')

    def test_profesor_gestiona_solo_clases_de_sus_cursos(self):
        self.client.force_authenticate(self.profe)
        datos = {'titulo': 'Z3', 'descripcion': 'd', 'fecha_hora_inicio': timezone.now().isoformat()}
        r = self.client.post('/api/clases-zoom/', {**datos, 'curso': self.curso.id, 'session_name': 'mate-2'})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/api/clases-zoom/', {**datos, 'curso': self.curso_ajeno.id, 'session_name': 'hist-2'})
        self.assertEqual(r.status_code, 403)

        self.assertEqual(self.client.post(f'/api/clases-zoom/{self.clase.id}/end/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/clases-zoom/{self.clase_ajena.id}/end/').status_code, 404)
        self.assertEqual(self.unirse(self.clase_ajena).status_code, 404)

    def test_no_se_une_a_clase_finalizada_o_cancelada(self):
        self.client.force_authenticate(self.u_ana)
        for estado in ('finalizada', 'cancelada'):
            ClaseZoom.objects.filter(pk=self.clase.pk).update(estado=estado)
            self.assertEqual(self.unirse(self.clase).status_code, 400)

    def test_sin_credenciales_de_zoom(self):
        self.client.force_authenticate(self.u_ana)
        with mock.patch.dict(os.environ, {'ZOOM_SDK_KEY': '', 'ZOOM_SDK_SECRET': ''}):
            self.assertEqual(self.unirse(self.clase).status_code, 503)


class ParticipanteClaseTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.clase = ClaseZoom.objects.create(curso=self.curso, titulo='Z1', descripcion='',
                                              fecha_hora_inicio=timezone.now(), session_name='mate-1')
        self.clase_ajena = ClaseZoom.objects.create(curso=self.curso_ajeno, titulo='Z2', descripcion='',
                                                    fecha_hora_inicio=timezone.now(), session_name='hist-1')

    def test_estudiante_solo_ve_su_asistencia_y_no_la_modifica(self):
        propia = ParticipanteClase.objects.create(clase=self.clase, estudiante=self.ana)
        ParticipanteClase.objects.create(clase=self.clase_ajena, estudiante=self.beto)

        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/participantes-clase/'), {propia.id})
        self.assertEqual(self.client.patch(f'/api/participantes-clase/{propia.id}/', {'asistio': True}).status_code, 403)
        r = self.client.post('/api/participantes-clase/', {'clase': self.clase.id, 'estudiante': self.ana.id, 'asistio': True})
        self.assertEqual(r.status_code, 403)

    def test_profesor_registra_asistencia_solo_en_sus_clases(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/participantes-clase/', {'clase': self.clase.id, 'estudiante': self.ana.id, 'asistio': True})
        self.assertEqual(r.status_code, 201)
        # Beto no está inscrito en el curso de la clase
        r = self.client.post('/api/participantes-clase/', {'clase': self.clase.id, 'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 400)
        r = self.client.post('/api/participantes-clase/', {'clase': self.clase_ajena.id, 'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 403)
