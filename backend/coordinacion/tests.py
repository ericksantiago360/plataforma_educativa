import os
import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from academico.tests import PDF, PNG
from coordinacion.models import ArchivoEntrega, Comunicado, EntregaTarea, Tarea
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
        self.assertEqual(r.data['resumen'], {'completadas': 0, 'en_progreso': 0, 'con_archivos': 0, 'alumnos': 1})

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
        self.assertEqual(self.client.get(self.url).data['resumen'], {'completadas': 1, 'en_progreso': 1, 'con_archivos': 0, 'alumnos': 2})

        # Quien deja el curso ya no cuenta en el resumen
        self.curso.estudiantes.remove(self.beto)
        self.assertEqual(self.client.get(self.url).data['resumen'], {'completadas': 1, 'en_progreso': 0, 'con_archivos': 0, 'alumnos': 1})

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


class EntregaConArchivosTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        ajustes = override_settings(MEDIA_ROOT=self.media, SERVIR_ARCHIVOS_CON_NGINX=False)
        ajustes.enable()
        self.addCleanup(ajustes.disable)

        self.tarea = Tarea.objects.create(titulo='Ensayo', descripcion='d', curso=self.curso,
                                          fecha_vencimiento=timezone.now() + timedelta(days=1))

    def entregar(self, nombre='ensayo.pdf', datos=PDF, tarea=None):
        return self.client.post(f'/api/tareas/{(tarea or self.tarea).id}/entregar/',
                                {'archivo': SimpleUploadedFile(nombre, datos)}, format='multipart')

    def entregar_como_ana(self):
        self.client.force_authenticate(self.u_ana)
        return self.entregar().data['archivos'][0]

    def test_alumno_entrega_y_la_tarea_queda_completada(self):
        self.client.force_authenticate(self.u_ana)
        r = self.entregar()
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['estado'], r.data['tarde']), ('completada', False))
        self.assertIsNotNone(r.data['entregado'])
        self.assertEqual([a['nombre'] for a in r.data['archivos']], ['ensayo.pdf'])
        self.assertNotIn(self.media, str(r.data))  # no se expone la ruta en disco

        # Varios archivos en la misma entrega
        self.entregar('portada.png', PNG)
        self.assertEqual(len(self.client.get(f'/api/tareas/{self.tarea.id}/').data['archivos']), 2)

    def test_entrega_tarde_se_permite_y_se_marca(self):
        Tarea.objects.filter(pk=self.tarea.pk).update(fecha_vencimiento=timezone.now() - timedelta(hours=1))
        self.client.force_authenticate(self.u_ana)
        r = self.entregar()
        self.assertEqual((r.status_code, r.data['tarde']), (201, True))

    def test_rechaza_archivos_invalidos(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.entregar('falso.pdf', b'<html></html>').status_code, 400)
        self.assertEqual(self.entregar('virus.exe', b'MZ\x90\x00').status_code, 400)
        r = self.client.post(f'/api/tareas/{self.tarea.id}/entregar/', {}, format='multipart')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ArchivoEntrega.objects.exists())

    def test_maximo_de_archivos_por_entrega(self):
        self.client.force_authenticate(self.u_ana)
        with mock.patch('coordinacion.views.MAXIMO_ARCHIVOS_POR_ENTREGA', 1):
            self.assertEqual(self.entregar().status_code, 201)
            self.assertEqual(self.entregar().status_code, 400)
        self.assertEqual(ArchivoEntrega.objects.count(), 1)

    def test_solo_alumnos_del_curso_entregan(self):
        self.client.force_authenticate(self.u_beto)  # no está en el curso
        self.assertEqual(self.entregar().status_code, 404)
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.entregar().status_code, 403)

    def test_descarga_protegida(self):
        archivo = self.entregar_como_ana()
        r = self.client.get(archivo['url'])
        self.assertEqual((r.status_code, b''.join(r.streaming_content)), (200, PDF))
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

        for usuario, esperado in [(self.profe, 200), (self.staff, 200), (self.otro_profe, 404), (self.u_beto, 404)]:
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get(archivo['url']).status_code, esperado, usuario.username)

    def test_alumno_quita_su_archivo_y_se_borra_del_disco(self):
        archivo = self.entregar_como_ana()
        ruta = ArchivoEntrega.objects.get().archivo.path
        self.assertTrue(os.path.exists(ruta))

        self.assertEqual(self.client.delete(f'/api/archivos-entrega/{archivo["id"]}/').status_code, 204)
        self.assertFalse(os.path.exists(ruta))
        # Sin archivos ya no hay fecha de entrega
        self.assertIsNone(self.client.get(f'/api/tareas/{self.tarea.id}/').data['entregado'])

    def test_profesor_no_borra_el_trabajo_del_alumno(self):
        archivo = self.entregar_como_ana()
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.delete(f'/api/archivos-entrega/{archivo["id"]}/').status_code, 403)
        self.assertTrue(ArchivoEntrega.objects.exists())

    def test_borrar_la_tarea_borra_los_archivos(self):
        self.entregar_como_ana()
        ruta = ArchivoEntrega.objects.get().archivo.path
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.delete(f'/api/tareas/{self.tarea.id}/').status_code, 204)
        self.assertFalse(os.path.exists(ruta))

    def test_profesor_ve_las_entregas_del_grupo(self):
        self.curso.estudiantes.add(self.beto)
        self.entregar_como_ana()

        self.client.force_authenticate(self.profe)
        r = self.client.get(f'/api/tareas/{self.tarea.id}/entregas/')
        self.assertEqual(r.status_code, 200)
        filas = {fila['estudiante']: fila for fila in r.data}
        self.assertEqual((filas[self.ana.id]['estado'], len(filas[self.ana.id]['archivos'])), ('completada', 1))
        self.assertEqual((filas[self.beto.id]['estado'], filas[self.beto.id]['archivos']), ('pendiente', []))
        self.assertEqual(self.client.get(f'/api/tareas/{self.tarea.id}/').data['resumen']['con_archivos'], 1)

    def test_estudiante_y_otro_profesor_no_ven_las_entregas(self):
        url = f'/api/tareas/{self.tarea.id}/entregas/'
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.client.get(url).status_code, 404)
