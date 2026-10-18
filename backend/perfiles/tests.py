from cuentas.tests import BaseAuthTest
from perfiles.models import PerfilEstudiante


class PerfilTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.perfil = PerfilEstudiante.objects.create(estudiante=self.ana, nivel_educativo='licenciatura',
                                                      programa='Ingeniería', periodo_actual='2026-2', materias_totales=10)
        self.url = f'/api/perfiles/{self.perfil.id}/'

    def test_staff_no_edita_a_mano_lo_que_se_calcula_del_historial(self):
        self.client.force_authenticate(self.staff)
        r = self.client.patch(self.url, {'promedio': '10', 'progreso_academico': 100, 'materias_cursadas': 9,
                                         'programa': 'Arquitectura'})
        self.assertEqual(r.status_code, 200)
        self.perfil.refresh_from_db()
        # El programa sí se edita; las estadísticas siguen saliendo del historial
        self.assertEqual((self.perfil.programa, float(self.perfil.promedio), self.perfil.progreso_academico,
                          self.perfil.materias_cursadas), ('Arquitectura', 0.0, 0, 0))

    def test_estudiante_solo_ve_su_perfil_y_no_lo_edita(self):
        PerfilEstudiante.objects.create(estudiante=self.beto, nivel_educativo='licenciatura',
                                        programa='p', periodo_actual='2026-2')
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.ids('/api/perfiles/'), {self.perfil.id})
        self.assertEqual(self.client.patch(self.url, {'programa': 'x'}).status_code, 403)
