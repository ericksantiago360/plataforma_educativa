from academico.models import ControlEscolar
from cuentas.tests import BaseAuthTest
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
