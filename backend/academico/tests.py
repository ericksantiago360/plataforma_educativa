import os
import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from academico import archivos
from academico.models import ArchivoContenido, ContenidoMateria, ControlEscolar, Materia
from cuentas.tests import BaseAuthTest
from estudiantes.models import Estudiante
from perfiles.models import PerfilEstudiante


class CalificacionesTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.materia = self.foro.clase.materia
        self.registro = ControlEscolar.objects.create(estudiante=self.ana, materia=self.materia, periodo='2026-2')
        self.perfil = PerfilEstudiante.objects.create(estudiante=self.ana, nivel_educativo='licenciatura',
                                                      programa='p', periodo_actual='2026-2', materias_totales=10)
        self.url = f'/api/control-escolar/{self.registro.id}/'

    def test_profesor_captura_y_el_perfil_se_actualiza(self):
        self.client.force_authenticate(self.profe)
        r = self.client.patch(self.url, {'calificacion': '9.5', 'estado': 'aprobado'})
        self.assertEqual(r.status_code, 200)

        self.perfil.refresh_from_db()
        self.assertEqual((self.perfil.materias_cursadas, float(self.perfil.promedio), self.perfil.progreso_academico),
                         (1, 9.5, 10))

    def perfil_actual(self):
        self.perfil.refresh_from_db()
        return self.perfil.materias_cursadas, float(self.perfil.promedio)

    def test_promedio_ignora_materias_en_curso_y_bajas(self):
        otra = Materia.objects.create(nombre='Cálculo', codigo='CAL', creditos=3, nivel=1, descripcion='', curso=self.curso)
        tercera = Materia.objects.create(nombre='Geometría', codigo='GEO', creditos=3, nivel=1, descripcion='', curso=self.curso)
        ControlEscolar.objects.create(estudiante=self.ana, materia=otra, periodo='2026-2', estado='cursando', calificacion=4)
        ControlEscolar.objects.create(estudiante=self.ana, materia=tercera, periodo='2026-2', estado='baja', calificacion=3)

        self.client.force_authenticate(self.profe)
        self.client.patch(self.url, {'calificacion': '9.5', 'estado': 'aprobado'})
        self.assertEqual(self.perfil_actual(), (1, 9.5))

    def test_solo_cuenta_el_ultimo_intento_de_cada_materia(self):
        # Reprobó en 2026-9 y aprobó en 2026-10: '2026-10' es posterior aunque como texto ordene antes
        self.registro.delete()
        ControlEscolar.objects.create(estudiante=self.ana, materia=self.materia, periodo='2026-9', estado='reprobado', calificacion=5)
        ControlEscolar.objects.create(estudiante=self.ana, materia=self.materia, periodo='2026-10', estado='aprobado', calificacion=9)
        self.perfil.recalcular()
        self.assertEqual(self.perfil_actual(), (1, 9.0))

    def test_borrar_calificacion_recalcula_el_perfil(self):
        self.client.force_authenticate(self.profe)
        self.client.patch(self.url, {'calificacion': '9.5', 'estado': 'aprobado'})
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.perfil.refresh_from_db()
        self.assertEqual((self.perfil.materias_cursadas, float(self.perfil.promedio), self.perfil.progreso_academico),
                         (0, 0.0, 0))

    def test_rango_de_calificacion(self):
        self.client.force_authenticate(self.profe)
        for valor in ('-1', '10.5', '11'):
            self.assertEqual(self.client.patch(self.url, {'calificacion': valor}).status_code, 400)

    def test_aprobado_requiere_calificacion(self):
        self.client.force_authenticate(self.profe)
        r = self.client.patch(self.url, {'estado': 'aprobado'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('calificacion', r.data)

    def test_otro_profesor_no_califica(self):
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.client.patch(self.url, {'calificacion': '10'}).status_code, 404)

    def test_estudiante_no_se_califica(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.patch(self.url, {'calificacion': '10'}).status_code, 403)


class MateriaTests(BaseAuthTest):
    DATOS = {'nombre': 'Estadística', 'codigo': 'est-101', 'creditos': 6, 'nivel': 2, 'descripcion': 'd'}

    def test_staff_crea_materia(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/materias/', {**self.DATOS, 'curso': self.curso.id})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['codigo'], r.data['curso_nombre']), ('EST-101', 'Mate'))  # código normalizado

    def test_codigo_repetido_sin_importar_mayusculas(self):
        self.client.force_authenticate(self.staff)
        self.client.post('/api/materias/', {**self.DATOS, 'curso': self.curso.id})
        r = self.client.post('/api/materias/', {**self.DATOS, 'codigo': 'EST-101', 'curso': self.curso.id})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(str(r.data['codigo'][0]), 'Ya existe una materia con este código.')

    def test_editar_sin_cambiar_codigo_no_choca_consigo_misma(self):
        self.client.force_authenticate(self.staff)
        materia = self.foro.clase.materia
        r = self.client.patch(f'/api/materias/{materia.id}/', {'codigo': materia.codigo, 'activo': False})
        self.assertEqual(r.status_code, 200)

    def test_valores_invalidos(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/materias/', {**self.DATOS, 'creditos': -1, 'nivel': 0, 'curso': self.curso.id})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {'creditos', 'nivel'})

    def test_profesor_y_estudiante_no_crean(self):
        for usuario in (self.profe, self.u_ana):
            self.client.force_authenticate(usuario)
            r = self.client.post('/api/materias/', {**self.DATOS, 'curso': self.curso.id})
            self.assertEqual(r.status_code, 403)


class InscribirGrupoTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.materia = self.foro.clase.materia  # pertenece a self.curso (Ana inscrita)
        self.curso.estudiantes.add(self.beto)
        self.url = f'/api/materias/{self.materia.id}/inscribir_grupo/'
        self.client.force_authenticate(self.staff)

    def test_inscribe_a_todo_el_grupo_una_sola_vez(self):
        r = self.client.post(self.url, {'periodo': '2026-2'})
        self.assertEqual((r.status_code, r.data), (200, {'inscritos': 2, 'ya_inscritos': 0}))
        self.assertEqual(ControlEscolar.objects.filter(materia=self.materia, periodo='2026-2', estado='cursando').count(), 2)

        r = self.client.post(self.url, {'periodo': '2026-2'})
        self.assertEqual(r.data, {'inscritos': 0, 'ya_inscritos': 2})

    def test_omite_alumnos_inactivos(self):
        self.beto.activo = False
        self.beto.save()
        self.assertEqual(self.client.post(self.url, {'periodo': '2026-2'}).data['inscritos'], 1)

    def test_periodo_con_formato_invalido(self):
        for periodo in ('', 'Agosto 2026', '26-2'):
            self.assertEqual(self.client.post(self.url, {'periodo': periodo}).status_code, 400)

    def test_materia_inactiva(self):
        self.materia.activo = False
        self.materia.save()
        self.assertEqual(self.client.post(self.url, {'periodo': '2026-2'}).status_code, 400)

    def test_profesor_no_inscribe_grupos(self):
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.post(self.url, {'periodo': '2026-2'}).status_code, 403)

    def test_registro_individual_exige_alumno_del_curso(self):
        self.curso.estudiantes.remove(self.beto)
        r = self.client.post('/api/control-escolar/', {'estudiante': self.beto.id, 'materia': self.materia.id, 'periodo': '2026-2'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('estudiante', r.data)


PDF = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF'
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
MP4 = b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 32


class ContenidoBase(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        ajustes = override_settings(MEDIA_ROOT=self.media)
        ajustes.enable()
        self.addCleanup(ajustes.disable)

        self.materia = self.foro.clase.materia  # curso de self.profe, con Ana inscrita
        self.materia_ajena = Materia.objects.get(curso=self.curso_ajeno)

    def crear(self, publicado=True, materia=None):
        return ContenidoMateria.objects.create(materia=materia or self.materia, titulo='Unidad 1', publicado=publicado)

    def subir(self, contenido, nombre, datos):
        return self.client.post(f'/api/contenidos/{contenido.id}/subir_archivo/',
                                {'archivo': SimpleUploadedFile(nombre, datos)}, format='multipart')


class ContenidoTests(ContenidoBase):
    def test_profesor_crea_y_el_html_se_sanea(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/contenidos/', {
            'materia': self.materia.id, 'titulo': 'Unidad 1',
            'cuerpo': '<h2>Intro</h2><script>alert(1)</script><p onclick="x()">Hola <a href="javascript:x()">mal</a></p>'
                      '<table><tr><td colspan="2" style="color:red">celda</td></tr></table>',
            'publicado': True,
        }, format='json')
        self.assertEqual(r.status_code, 201)
        cuerpo = r.data['cuerpo']
        for prohibido in ('script', 'onclick', 'javascript:', 'style'):
            self.assertNotIn(prohibido, cuerpo)
        self.assertIn('<td colspan="2">celda</td>', cuerpo)
        self.assertEqual(r.data['autor_nombre'], 'profe')

    def test_profesor_no_crea_en_materia_ajena(self):
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/contenidos/', {'materia': self.materia_ajena.id, 'titulo': 'x'}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_enlaces_de_youtube(self):
        self.client.force_authenticate(self.profe)
        for url in ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10', 'https://youtu.be/dQw4w9WgXcQ',
                    'https://www.youtube.com/shorts/dQw4w9WgXcQ'):
            r = self.client.post('/api/contenidos/', {'materia': self.materia.id, 'titulo': 't', 'video_url': url}, format='json')
            self.assertEqual(r.data['video_youtube'], 'dQw4w9WgXcQ', url)
        for url in ('https://vimeo.com/123', 'https://evil.com/?v=dQw4w9WgXcQ', 'javascript:alert(1)'):
            r = self.client.post('/api/contenidos/', {'materia': self.materia.id, 'titulo': 't', 'video_url': url}, format='json')
            self.assertEqual(r.status_code, 400, url)

    def test_estudiante_solo_ve_lo_publicado(self):
        publicado, borrador = self.crear(), self.crear(publicado=False)
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids(f'/api/contenidos/?materia={self.materia.id}'), {publicado.id})
        self.assertEqual(self.client.get(f'/api/contenidos/{borrador.id}/').status_code, 404)
        self.assertEqual(self.client.post('/api/contenidos/', {'materia': self.materia.id, 'titulo': 'x'}).status_code, 403)

    def test_estudiante_de_otro_curso_no_ve_nada(self):
        self.crear()
        self.client.force_authenticate(self.u_beto)
        self.assertEqual(self.ids('/api/contenidos/'), set())


class AdjuntosTests(ContenidoBase):
    def test_sube_pdf_imagen_y_video(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        for nombre, datos, tipo in [('guia.pdf', PDF, 'documento'), ('foto.png', PNG, 'imagen'), ('clase.mp4', MP4, 'video')]:
            r = self.subir(contenido, nombre, datos)
            self.assertEqual((r.status_code, r.data['tipo'], r.data['nombre']), (201, tipo, nombre))
            self.assertNotIn(self.media, str(r.data))  # no se expone la ruta en disco

    def test_rechaza_archivos_disfrazados_o_no_permitidos(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        casos = [('falso.pdf', b'<html><script>alert(1)</script></html>'),   # HTML renombrado
                 ('virus.exe', b'MZ\x90\x00'),
                 ('dibujo.svg', b'<svg onload="alert(1)"/>'),
                 ('vacio.pdf', b'')]
        for nombre, datos in casos:
            r = self.subir(contenido, nombre, datos)
            self.assertEqual(r.status_code, 400, nombre)
        self.assertEqual(ArchivoContenido.objects.count(), 0)

    def test_limite_de_tamano(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        with mock.patch.dict(archivos.TAMANO_MAXIMO, {'documento': 10}):
            r = self.subir(contenido, 'grande.pdf', PDF)
        self.assertEqual(r.status_code, 400)
        self.assertIn('máximo', r.data['archivo'][0])

    def test_maximo_de_archivos_por_contenido(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        with mock.patch('academico.views.MAXIMO_ARCHIVOS_POR_CONTENIDO', 2):
            self.assertEqual(self.subir(contenido, 'a.pdf', PDF).status_code, 201)
            self.assertEqual(self.subir(contenido, 'b.pdf', PDF).status_code, 201)
            r = self.subir(contenido, 'c.pdf', PDF)
        self.assertEqual(r.status_code, 400)
        self.assertIn('Máximo 2', r.data['archivo'][0])
        self.assertEqual(contenido.archivos.count(), 2)

    def test_estudiante_y_otro_profesor_no_suben(self):
        contenido = self.crear()
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.subir(contenido, 'a.pdf', PDF).status_code, 403)
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.subir(contenido, 'a.pdf', PDF).status_code, 404)

    # Fijo: el .env local puede activar nginx, y aquí se prueba la entrega directa desde Django
    @override_settings(SERVIR_ARCHIVOS_CON_NGINX=False)
    def test_descarga_protegida(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        url = self.subir(contenido, 'guía 1.pdf', PDF).data['url']

        self.client.force_authenticate(self.u_ana)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), PDF)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn('inline', r['Content-Disposition'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

        self.client.force_authenticate(self.u_beto)  # no está en el curso
        self.assertEqual(self.client.get(url).status_code, 404)

        contenido.publicado = False
        contenido.save()
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_descarga_por_nginx(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        url = self.subir(contenido, 'notas.docx', b'PK\x03\x04' + b'\x00' * 30).data['url']
        with override_settings(SERVIR_ARCHIVOS_CON_NGINX=True):
            r = self.client.get(url)
        adjunto = ArchivoContenido.objects.get()
        self.assertEqual(r['X-Accel-Redirect'], f'/archivos-protegidos/{adjunto.archivo.name}')
        self.assertIn('attachment', r['Content-Disposition'])  # Office se descarga
        self.assertEqual(r.content, b'')

    def test_borrar_quita_los_archivos_del_disco(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        self.subir(contenido, 'a.pdf', PDF)
        self.subir(contenido, 'b.png', PNG)
        rutas = [a.archivo.path for a in ArchivoContenido.objects.all()]
        self.assertTrue(all(os.path.exists(r) for r in rutas))

        primero = ArchivoContenido.objects.first()
        self.assertEqual(self.client.delete(f'/api/archivos-contenido/{primero.id}/').status_code, 204)
        self.assertFalse(os.path.exists(rutas[0]))

        self.assertEqual(self.client.delete(f'/api/contenidos/{contenido.id}/').status_code, 204)
        self.assertFalse(any(os.path.exists(r) for r in rutas))

    def test_estudiante_no_borra_adjuntos(self):
        contenido = self.crear()
        self.client.force_authenticate(self.profe)
        archivo_id = self.subir(contenido, 'a.pdf', PDF).data['id']
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.delete(f'/api/archivos-contenido/{archivo_id}/').status_code, 403)


class ReportesTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.materia = self.foro.clase.materia  # Álgebra, del curso de self.profe
        self.calculo = Materia.objects.create(nombre='Cálculo', codigo='CAL', creditos=5, nivel=2, descripcion='', curso=self.curso)
        PerfilEstudiante.objects.create(estudiante=self.ana, nivel_educativo='licenciatura', programa='Ingeniería',
                                        periodo_actual='2026-10', materias_totales=10)
        crear = ControlEscolar.objects.create
        crear(estudiante=self.ana, materia=self.materia, periodo='2026-9', estado='reprobado', calificacion=5)
        crear(estudiante=self.ana, materia=self.materia, periodo='2026-10', estado='aprobado', calificacion=9)
        crear(estudiante=self.ana, materia=self.calculo, periodo='2026-10', estado='cursando', calificacion=6)

    def assertPdf(self, r, nombre):
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertEqual(r['Content-Disposition'], f'attachment; filename="{nombre}"')
        self.assertEqual(r['Cache-Control'], 'no-store')
        self.assertTrue(r.content.startswith(b'%PDF'))

    # ---------- Kardex ----------

    def test_datos_del_kardex(self):
        from academico.reportes import datos_kardex
        datos = datos_kardex(self.ana)
        # Periodos en orden numérico: 2026-9 antes que 2026-10
        self.assertEqual([fila[0] for fila in datos['filas']], ['2026-9', '2026-10', '2026-10'])
        self.assertEqual(datos['filas'][0][4:], ['5.0', 'Reprobado'])
        # Promedio: solo el último intento final de Álgebra (9); Cálculo sigue en curso
        self.assertEqual(datos['resumen'], {'promedio': 9, 'aprobadas': 1, 'creditos': 3, 'materias_totales': 10})
        self.assertEqual((datos['programa'], datos['nivel']), ('Ingeniería', 'Carrera Profesional'))

    def test_alumno_descarga_su_kardex(self):
        self.client.force_authenticate(self.u_ana)
        self.assertPdf(self.client.get(f'/api/estudiantes/{self.ana.id}/kardex/'), 'kardex-1.pdf')

    def test_alumno_no_descarga_el_kardex_de_otro(self):
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(f'/api/estudiantes/{self.beto.id}/kardex/').status_code, 404)

    def test_staff_descarga_cualquier_kardex_y_el_profesor_no(self):
        self.client.force_authenticate(self.staff)
        self.assertPdf(self.client.get(f'/api/estudiantes/{self.beto.id}/kardex/'), 'kardex-2.pdf')  # sin historial ni perfil
        self.client.force_authenticate(self.profe)
        self.assertEqual(self.client.get(f'/api/estudiantes/{self.ana.id}/kardex/').status_code, 403)

    def test_caracteres_especiales_no_rompen_el_pdf(self):
        Estudiante.objects.filter(pk=self.ana.pk).update(nombre='<b>Ana & "Ñoño"</b>')
        Materia.objects.filter(pk=self.calculo.pk).update(nombre='Cálculo <diferencial> & integral ' * 5)
        self.client.force_authenticate(self.u_ana)
        self.assertPdf(self.client.get(f'/api/estudiantes/{self.ana.id}/kardex/'), 'kardex-1.pdf')

    # ---------- Reporte de grupo ----------

    def test_datos_del_reporte_de_grupo(self):
        from academico.reportes import datos_reporte_grupo
        self.curso.estudiantes.add(self.beto)
        ControlEscolar.objects.create(estudiante=self.beto, materia=self.calculo, periodo='2026-10', estado='aprobado', calificacion=8)
        datos = datos_reporte_grupo(self.calculo, '2026-10')
        # Orden por apellido: A (Ana) y luego B (Beto)
        self.assertEqual([fila[1] for fila in datos['filas']], ['1', '2'])
        self.assertEqual((datos['profesor'], datos['periodo']), ('profe', '2026-10'))
        # El promedio del grupo solo toma calificaciones finales (Ana sigue cursando)
        self.assertEqual(datos['resumen'], {'alumnos': 2, 'cursando': 1, 'aprobado': 1, 'reprobado': 0, 'baja': 0, 'promedio': 8})

    def test_profesor_descarga_el_reporte_de_su_materia(self):
        self.client.force_authenticate(self.profe)
        r = self.client.get(f'/api/materias/{self.materia.id}/reporte_grupo/?periodo=2026-10')
        self.assertPdf(r, 'grupo-ALG-2026-10.pdf')

    def test_reporte_de_periodo_sin_alumnos(self):
        self.client.force_authenticate(self.staff)
        r = self.client.get(f'/api/materias/{self.materia.id}/reporte_grupo/?periodo=2020-1')
        self.assertPdf(r, 'grupo-ALG-2020-1.pdf')

    def test_reporte_de_grupo_permisos(self):
        url = f'/api/materias/{self.materia.id}/reporte_grupo/?periodo=2026-10'
        self.client.force_authenticate(self.otro_profe)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_reporte_de_grupo_exige_periodo_valido(self):
        self.client.force_authenticate(self.profe)
        for periodo in ('', 'otoño', '2026'):
            r = self.client.get(f'/api/materias/{self.materia.id}/reporte_grupo/?periodo={periodo}')
            self.assertEqual(r.status_code, 400, periodo)
