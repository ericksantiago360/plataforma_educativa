from datetime import date, timedelta

from django.utils import timezone

from cuentas.tests import BaseAuthTest
from pagos.models import Cargo, Pago
from servicios.models import BibliotecaDigital, CentroIdiomas, ClaseIdiomas, EventoCalendario, MaterialIdiomas, MesaAyuda


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


class IdiomasCursoTests(BaseAuthTest):
    """Lo que recibe el alumno al inscribirse: clases, materiales y el estado de su pago."""

    def setUp(self):
        super().setUp()
        self.ingles = CentroIdiomas.objects.create(idioma='ingles', nivel='basico', nombre_curso='Inglés I',
                                                   descripcion='', duracion_semanas=8, precio=1500, instructor='x',
                                                   cupo_maximo=5, fecha_inicio=date.today() + timedelta(days=10),
                                                   horario='Lun y mié 18:00', lugar='Salón 3')
        ClaseIdiomas.objects.create(curso=self.ingles, titulo='Clase 1', fecha_hora=timezone.now() + timedelta(days=10))
        self.visible = MaterialIdiomas.objects.create(curso=self.ingles, titulo='Vocabulario', enlace='https://x.com/v')
        self.borrador = MaterialIdiomas.objects.create(curso=self.ingles, titulo='Borrador', publicado=False)
        self.url = f'/api/idiomas/{self.ingles.id}/mi_curso/'

    def inscribir_a_ana(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/').status_code, 200)

    def test_no_inscrito_no_ve_el_curso(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_inscrito_ve_clases_materiales_publicados_y_su_cargo(self):
        self.inscribir_a_ana()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c['titulo'] for c in r.data['clases']], ['Clase 1'])
        self.assertEqual([m['titulo'] for m in r.data['materiales']], ['Vocabulario'])  # sin el borrador
        self.assertEqual((r.data['cargo']['estado'], r.data['cargo']['saldo']), ('pendiente', 1500))
        self.assertEqual(r.data['curso']['horario'], 'Lun y mié 18:00')

    def test_el_cargo_refleja_los_pagos(self):
        self.inscribir_a_ana()
        cargo = Cargo.objects.get(curso_idiomas=self.ingles, estudiante=self.ana)
        Pago.objects.create(cargo=cargo, monto=500, metodo='efectivo')
        cargo_api = self.client.get(self.url).data['cargo']
        self.assertEqual((cargo_api['estado'], cargo_api['pagado'], cargo_api['saldo']), ('parcial', 500, 1000))

    def test_otro_inscrito_no_ve_el_cargo_de_ana(self):
        self.inscribir_a_ana()
        self.client.force_authenticate(self.u_beto)
        self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        self.assertEqual(self.client.get(self.url).data['cargo']['saldo'], 1500)  # el suyo, no el de ana
        self.assertEqual(Cargo.objects.filter(curso_idiomas=self.ingles).count(), 2)

    def test_staff_ve_los_borradores_y_no_tiene_cargo(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get(self.url)
        self.assertEqual({m['titulo'] for m in r.data['materiales']}, {'Vocabulario', 'Borrador'})
        self.assertIsNone(r.data['cargo'])

    def test_inscritos_solo_para_staff_con_estado_de_pago(self):
        self.inscribir_a_ana()
        self.assertEqual(self.client.get(f'/api/idiomas/{self.ingles.id}/inscritos/').status_code, 403)
        self.client.force_authenticate(self.staff)
        r = self.client.get(f'/api/idiomas/{self.ingles.id}/inscritos/')
        self.assertEqual([(i['matricula'], i['cargo']['estado']) for i in r.data], [('1', 'pendiente')])

    def test_no_se_inscribe_a_un_curso_que_ya_inicio(self):
        self.ingles.fecha_inicio = date.today() - timedelta(days=1)
        self.ingles.save()
        self.client.force_authenticate(self.u_ana)
        r = self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(self.ingles.estudiantes_inscritos.filter(pk=self.ana.pk).exists())
        self.assertFalse(Cargo.objects.filter(curso_idiomas=self.ingles).exists())

    def test_quien_ya_estaba_inscrito_sigue_pudiendo_reinscribir_sin_error(self):
        self.inscribir_a_ana()
        self.ingles.fecha_inicio = date.today() - timedelta(days=1)
        self.ingles.save()
        self.assertEqual(self.client.post(f'/api/idiomas/{self.ingles.id}/inscribir/').status_code, 200)

    def test_alumno_solo_lee_clases_y_materiales_de_sus_cursos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/idiomas-clases/'), set())  # aún no inscrita
        self.inscribir_a_ana()
        self.assertEqual(len(self.client.get('/api/idiomas-clases/').data['results']), 1)
        self.assertEqual({m['titulo'] for m in self.client.get('/api/idiomas-materiales/').data['results']}, {'Vocabulario'})

    def test_alumno_no_escribe_clases_ni_materiales(self):
        self.inscribir_a_ana()
        r = self.client.post('/api/idiomas-materiales/', {'curso': self.ingles.id, 'titulo': 'x'})
        self.assertEqual(r.status_code, 403)

    def test_staff_crea_una_clase(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/idiomas-clases/', {'curso': self.ingles.id, 'titulo': 'Clase 2',
                                                      'fecha_hora': (timezone.now() + timedelta(days=17)).isoformat(),
                                                      'duracion_minutos': 90})
        self.assertEqual(r.status_code, 201)


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
