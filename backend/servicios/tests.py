from datetime import date, timedelta

from django.utils import timezone

from cuentas.tests import BaseAuthTest
from servicios.models import BibliotecaDigital, CentroIdiomas, EventoCalendario, MesaAyuda


class BibliotecaTests(BaseAuthTest):
    def test_recursos_inactivos_solo_para_staff(self):
        datos = dict(autor='a', categoria='c', descripcion='', url_recurso='https://x.com',
                     tipo_recurso='libro', fecha_publicacion=date.today())
        activo = BibliotecaDigital.objects.create(titulo='Activo', **datos)
        inactivo = BibliotecaDigital.objects.create(titulo='Baja', activo=False, **datos)

        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/biblioteca/'), {activo.id})
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.ids('/api/biblioteca/'), {activo.id, inactivo.id})


class CalendarioTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        ahora = timezone.now()
        datos = dict(descripcion='', tipo_evento='evento')
        self.general = EventoCalendario.objects.create(titulo='General', todos_estudiantes=True,
                                                       fecha_inicio=ahora, fecha_fin=ahora + timedelta(days=1), **datos)
        self.de_mate = EventoCalendario.objects.create(titulo='Examen Mate', fecha_inicio=ahora,
                                                       fecha_fin=ahora + timedelta(days=1), **datos)
        self.de_mate.cursos.add(self.curso)
        self.de_historia = EventoCalendario.objects.create(titulo='Examen Historia', fecha_inicio=ahora,
                                                           fecha_fin=ahora + timedelta(days=1), **datos)
        self.de_historia.cursos.add(self.curso_ajeno)
        self.pasado = EventoCalendario.objects.create(titulo='Pasado', todos_estudiantes=True,
                                                      fecha_inicio=ahora - timedelta(days=9),
                                                      fecha_fin=ahora - timedelta(days=8), **datos)

    def test_estudiante_ve_generales_y_de_sus_cursos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/calendario/'), {self.general.id, self.de_mate.id, self.pasado.id})

    def test_profesor_ve_generales_y_de_sus_cursos(self):
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.ids('/api/calendario/'), {self.general.id, self.de_historia.id, self.pasado.id})

    def test_filtro_proximos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/calendario/?proximos=1'), {self.general.id, self.de_mate.id})


class IdiomasTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.ingles = CentroIdiomas.objects.create(idioma='ingles', nivel='basico', nombre_curso='Inglés I',
                                                   descripcion='', duracion_semanas=8, precio=0, instructor='x',
                                                   cupo_maximo=1, fecha_inicio=date.today())

    def test_inscribirse_y_cancelar(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['inscrito'], r.data['cupos_disponibles']), (True, 0))

        r = self.client.post(f'/api/idiomas/{self.ingles.id}/cancelar/')
        self.assertEqual((r.data['inscrito'], r.data['cupos_disponibles']), (False, 1))

    def test_sin_cupo(self):
        self.ingles.estudiantes_inscritos.add(self.beto)
        self.client.force_authenticate(self.u_ana)
        r = self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.ingles.estudiantes_inscritos.filter(pk=self.ana.pk).exists())

    def test_inscribirse_dos_veces_no_duplica_ni_falla(self):
        self.client.force_authenticate(self.u_ana)
        self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        r = self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        self.assertEqual(r.status_code, 200)

    def test_profesor_no_se_inscribe(self):
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/').status_code, 403)

    def test_estudiante_no_edita_el_catalogo(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.patch(f'/api/idiomas/{self.ingles.id}/', {'cupo_maximo': 99})
        self.assertEqual(r.status_code, 403)

    def test_lista_de_inscritos_solo_para_staff(self):
        self.ingles.estudiantes_inscritos.add(self.beto)
        self.client.force_authenticate(self.u_ana)
        self.assertNotIn('estudiantes_inscritos', self.client.get(f'/api/idiomas/{self.ingles.id}/').data)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(f'/api/idiomas/{self.ingles.id}/').data['estudiantes_inscritos'], [self.beto.id])


class MesaAyudaTests(BaseAuthTest):
    def test_staff_responde_y_estudiante_lo_ve(self):
        ticket = MesaAyuda.objects.create(estudiante=self.ana, categoria='tecnico', asunto='a', descripcion='d')
        self.client.force_authenticate(self.staff)
        r = self.client.patch(f'/api/mesa-ayuda/{ticket.id}/', {'estado': 'resuelto', 'respuesta': 'Listo'})
        self.assertEqual(r.status_code, 200)

        self.client.force_authenticate(self.u_ana)
        datos = self.client.get(f'/api/mesa-ayuda/{ticket.id}/').data
        self.assertEqual((datos['estado_nombre'], datos['respuesta']), ('Resuelto', 'Listo'))

    def test_estudiante_no_cambia_estado(self):
        ticket = MesaAyuda.objects.create(estudiante=self.ana, categoria='tecnico', asunto='a', descripcion='d')
        self.client.force_authenticate(self.u_ana)
        r = self.client.patch(f'/api/mesa-ayuda/{ticket.id}/', {'estado': 'cerrado'})
        self.assertEqual(r.status_code, 403)
