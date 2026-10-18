from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from coordinacion.models import Comunicado, EntregaTarea, Tarea
from cuentas.tests import BaseAuthTest


class CrearTareaTests(BaseAuthTest):
    def datos(self, curso):
        return {'titulo': 'Ensayo', 'descripcion': 'd', 'curso': curso.id,
                'fecha_vencimiento': (timezone.now() + timedelta(days=3)).isoformat()}

    def test_profesor_crea_tarea_en_su_curso(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/tareas/', self.datos(self.curso))
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['curso_nombre'], 'Mate')
        self.assertEqual(r.data['resumen'], {'completadas': 0, 'en_progreso': 0, 'alumnos': 1})

    def test_estudiante_no_crea_tareas(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.post('/api/tareas/', self.datos(self.curso)).status_code, 403)


class AvanceTareaTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.tarea = Tarea.objects.create(titulo='t', descripcion='d', curso=self.curso,
                                          fecha_vencimiento=timezone.now() + timedelta(days=1))
        self.url = f'/api/tareas/{self.tarea.id}/'

    def marcar(self, estado, tarea=None):
        return self.client.post(f'/api/tareas/{(tarea or self.tarea).id}/estado/', {'estado': estado})

    def test_sin_registro_la_tarea_esta_pendiente(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.get(self.url)
        self.assertEqual((r.data['estado'], r.data['estado_nombre']), ('pendiente', 'Pendiente'))
        self.assertNotIn('resumen', r.data)

    def test_alumno_inscrito_despues_tambien_la_tiene(self):
        self.curso.estudiantes.add(self.beto)
        self.client.force_authenticate(self.u_beto)
        self.assertIn(self.tarea.id, self.ids('/api/tareas/'))

    def test_cada_alumno_tiene_su_propio_avance(self):
        self.curso.estudiantes.add(self.beto)
        self.client.force_authenticate(self.u_ana)
        r = self.marcar('completada')
        self.assertEqual((r.status_code, r.data['estado']), (200, 'completada'))
        # Volver a marcar actualiza el mismo registro
        self.marcar('en_progreso')
        self.marcar('completada')
        self.assertEqual(EntregaTarea.objects.count(), 1)

        self.client.force_authenticate(self.u_beto)
        self.assertEqual(self.client.get(self.url).data['estado'], 'pendiente')

    def test_profesor_ve_el_avance_del_grupo(self):
        self.curso.estudiantes.add(self.beto)
        EntregaTarea.objects.create(tarea=self.tarea, estudiante=self.ana, estado='completada')
        EntregaTarea.objects.create(tarea=self.tarea, estudiante=self.beto, estado='en_progreso')
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.get(self.url).data['resumen'], {'completadas': 1, 'en_progreso': 1, 'alumnos': 2})

        # Quien deja el curso ya no cuenta en el resumen
        self.curso.estudiantes.remove(self.beto)
        self.assertEqual(self.client.get(self.url).data['resumen'], {'completadas': 1, 'en_progreso': 0, 'alumnos': 1})

    def test_estado_invalido(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.marcar('entregadisima').status_code, 400)
        self.assertFalse(EntregaTarea.objects.exists())

    def test_no_marca_tareas_de_otro_curso(self):
        ajena = Tarea.objects.create(titulo='h', descripcion='d', curso=self.curso_ajeno, fecha_vencimiento=timezone.now())
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.marcar('completada', ajena).status_code, 404)

    def test_profesor_no_marca_avance(self):
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.marcar('completada').status_code, 403)

    def test_estudiante_no_edita_la_tarea(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.patch(self.url, {'titulo': 'x'}).status_code, 403)


class ComunicadoTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.general = Comunicado.objects.create(titulo='General', contenido='c')
        self.de_mate = Comunicado.objects.create(titulo='Mate', contenido='c', curso=self.curso)
        self.de_historia = Comunicado.objects.create(titulo='Historia', contenido='c', curso=self.curso_ajeno)
        self.inactivo = Comunicado.objects.create(titulo='Viejo', contenido='c', activo=False)

    def test_estudiante_ve_generales_y_de_sus_cursos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/comunicados/'), {self.general.id, self.de_mate.id})
        self.assertEqual(self.client.get(f'/api/comunicados/{self.de_historia.id}/').status_code, 404)

    def test_profesor_ve_generales_y_de_sus_cursos(self):
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.ids('/api/comunicados/'), {self.general.id, self.de_historia.id})

    def test_staff_ve_todos_incluso_inactivos(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.ids('/api/comunicados/'),
                         {self.general.id, self.de_mate.id, self.de_historia.id, self.inactivo.id})

    def test_usuario_sin_rol_no_ve_nada(self):
        self.client.force_authenticate(User.objects.create_user('nadie', password='x'))
        self.assertEqual(self.ids('/api/comunicados/'), set())

    def test_solo_staff_publica(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/comunicados/', {'titulo': 't', 'contenido': 'c', 'curso': self.curso.id})
        self.assertEqual(r.status_code, 403)
