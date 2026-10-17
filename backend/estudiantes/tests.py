from django.contrib.auth.models import User

from cuentas.tests import BaseAuthTest
from estudiantes.models import Estudiante

DATOS_ALTA = {
    'nombre': 'Lucía', 'apellido': 'Ramos', 'email': 'lucia@x.com', 'matricula': '2026100',
    'nivel_educativo': 'licenciatura', 'programa': 'Lic. en Administración',
    'periodo_actual': '2026-2', 'materias_totales': 40,
}


class AltaEstudianteTests(BaseAuthTest):
    def test_staff_da_de_alta_con_cuenta_y_perfil(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/estudiantes/alta/', DATOS_ALTA)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['usuario'], '2026100')

        estudiante = Estudiante.objects.get(matricula='2026100')
        self.assertEqual(estudiante.perfil.programa, 'Lic. en Administración')
        # La contraseña temporal sirve para iniciar sesión
        self.assertTrue(estudiante.usuario.check_password(r.data['password_temporal']))

    def test_matricula_ya_usada_como_usuario(self):
        User.objects.create_user('2026100')
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/estudiantes/alta/', DATOS_ALTA)
        self.assertEqual(r.status_code, 400)
        self.assertIn('matricula', r.data)
        self.assertFalse(Estudiante.objects.filter(matricula='2026100').exists())

    def test_si_falla_no_deja_usuario_huerfano(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/estudiantes/alta/', {**DATOS_ALTA, 'email': self.ana.email})  # email repetido
        self.assertEqual(r.status_code, 400)
        self.assertFalse(User.objects.filter(username='2026100').exists())

    def test_profesor_y_estudiante_no_dan_de_alta(self):
        for usuario in (self.profe, self.u_ana):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.post('/api/estudiantes/alta/', DATOS_ALTA).status_code, 403)
