from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import Client
from django.utils import timezone
from rest_framework.test import APITestCase

from academico.models import ClaseEnLinea, ForoClase, Materia, MensajeForo
from coordinacion.models import Tarea
from cursos.models import Curso
from estudiantes.models import Estudiante
from servicios.models import MesaAyuda


class BaseAuthTest(APITestCase):
    def setUp(self):
        cache.clear()  # el límite de intentos de login se guarda en caché y no debe pasar de un test a otro
        grupo_profesor = Group.objects.get(name='Profesor')

        self.staff = User.objects.create_user('staff', password='x', is_staff=True)
        self.profe = User.objects.create_user('profe', password='x')
        self.profe.groups.add(grupo_profesor)
        self.otro_profe = User.objects.create_user('otro_profe', password='x')
        self.otro_profe.groups.add(grupo_profesor)

        self.u_ana = User.objects.create_user('ana', password='x')
        self.u_beto = User.objects.create_user('beto', password='x')
        self.ana = Estudiante.objects.create(usuario=self.u_ana, nombre='Ana', apellido='A', email='ana@x.com', matricula='1')
        self.beto = Estudiante.objects.create(usuario=self.u_beto, nombre='Beto', apellido='B', email='beto@x.com', matricula='2')

        hoy = date.today()
        self.curso = Curso.objects.create(nombre='Mate', codigo='M1', descripcion='', profesor='Profe',
                                          titular=self.profe, fecha_inicio=hoy, fecha_fin=hoy)
        self.curso_ajeno = Curso.objects.create(nombre='Historia', codigo='H1', descripcion='', profesor='Otro',
                                                titular=self.otro_profe, fecha_inicio=hoy, fecha_fin=hoy)
        self.curso.estudiantes.add(self.ana)
        self.curso_ajeno.estudiantes.add(self.beto)

        materia = Materia.objects.create(nombre='Álgebra', codigo='ALG', creditos=3, nivel=1, descripcion='', curso=self.curso)
        clase = ClaseEnLinea.objects.create(materia=materia, titulo='C1', descripcion='',
                                            fecha_clase=timezone.now(), duracion_minutos=60)
        self.foro = ForoClase.objects.create(clase=clase, titulo='Dudas', descripcion='')
        materia_ajena = Materia.objects.create(nombre='Edad Media', codigo='EM', creditos=3, nivel=1, descripcion='', curso=self.curso_ajeno)
        clase_ajena = ClaseEnLinea.objects.create(materia=materia_ajena, titulo='C2', descripcion='',
                                                  fecha_clase=timezone.now(), duracion_minutos=60)
        self.foro_ajeno = ForoClase.objects.create(clase=clase_ajena, titulo='Dudas H', descripcion='')

    def ids(self, url):
        return {r['id'] for r in self.client.get(url).data['results']}


class SesionTests(BaseAuthTest):
    def test_api_requiere_sesion(self):
        self.assertEqual(self.client.get('/api/cursos/').status_code, 403)

    def test_login_me_logout(self):
        r = self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['rol'], 'estudiante')
        self.assertEqual(r.data['estudiante']['id'], self.ana.id)

        self.assertEqual(self.client.get('/api/auth/me/').data['usuario'], 'ana')

        self.client.post('/api/auth/logout/')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 403)

    def test_login_incorrecto(self):
        r = self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'mal'})
        self.assertEqual(r.status_code, 400)

    def test_login_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        r = client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'})
        self.assertEqual(r.status_code, 403)

        client.get('/api/auth/csrf/')
        token = client.cookies['csrftoken'].value
        r = client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)

    def test_roles(self):
        for usuario, rol in [('staff', 'staff'), ('profe', 'profesor'), ('ana', 'estudiante')]:
            self.client.force_authenticate(User.objects.get(username=usuario))
            self.assertEqual(self.client.get('/api/auth/me/').data['rol'], rol)


class EstudianteTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.u_ana)

    def test_solo_ve_su_registro(self):
        self.assertEqual(self.ids('/api/estudiantes/'), {self.ana.id})
        self.assertEqual(self.client.get(f'/api/estudiantes/{self.beto.id}/').status_code, 404)

    def test_solo_ve_sus_cursos(self):
        self.assertEqual(self.ids('/api/cursos/'), {self.curso.id})

    def test_no_puede_escribir_cursos(self):
        r = self.client.patch(f'/api/cursos/{self.curso.id}/', {'nombre': 'X'})
        self.assertEqual(r.status_code, 403)

    def test_mensaje_foro_se_firma_con_la_sesion(self):
        r = self.client.post('/api/mensajes-foro/', {'foro': self.foro.id, 'contenido': 'hola', 'estudiante': self.beto.id})
        self.assertEqual(r.status_code, 201)
        mensaje = MensajeForo.objects.get()
        self.assertEqual((mensaje.autor, mensaje.estudiante), (self.u_ana, self.ana))
        self.assertEqual(r.data['autor_rol'], 'estudiante')

    def test_no_publica_en_foro_ajeno(self):
        r = self.client.post('/api/mensajes-foro/', {'foro': self.foro_ajeno.id, 'contenido': 'hola'})
        self.assertEqual(r.status_code, 403)

    def test_no_edita_mensaje_ajeno(self):
        self.curso.estudiantes.add(self.beto)
        mensaje = MensajeForo.objects.create(foro=self.foro, autor=self.u_beto, estudiante=self.beto, contenido='de beto')
        r = self.client.patch(f'/api/mensajes-foro/{mensaje.id}/', {'contenido': 'hackeado'})
        self.assertEqual(r.status_code, 403)

    def test_edita_su_mensaje(self):
        mensaje = MensajeForo.objects.create(foro=self.foro, autor=self.u_ana, estudiante=self.ana, contenido='original')
        r = self.client.patch(f'/api/mensajes-foro/{mensaje.id}/', {'contenido': 'corregido'})
        self.assertEqual(r.status_code, 200)
        mensaje.refresh_from_db()
        self.assertEqual((mensaje.contenido, mensaje.editado), ('corregido', True))

    def test_no_edita_en_foro_cerrado(self):
        mensaje = MensajeForo.objects.create(foro=self.foro, autor=self.u_ana, estudiante=self.ana, contenido='original')
        self.foro.activo = False
        self.foro.save()
        r = self.client.patch(f'/api/mensajes-foro/{mensaje.id}/', {'contenido': 'tarde'})
        self.assertEqual(r.status_code, 403)

    def test_no_publica_en_foro_cerrado(self):
        self.foro.activo = False
        self.foro.save()
        r = self.client.post('/api/mensajes-foro/', {'foro': self.foro.id, 'contenido': 'hola'})
        self.assertEqual(r.status_code, 403)

    def test_filtra_mensajes_por_foro(self):
        materia = self.foro.clase.materia
        clase = ClaseEnLinea.objects.create(materia=materia, titulo='C3', descripcion='',
                                            fecha_clase=timezone.now(), duracion_minutos=60)
        otro_foro = ForoClase.objects.create(clase=clase, titulo='Otro', descripcion='')
        mensaje = MensajeForo.objects.create(foro=self.foro, estudiante=self.ana, contenido='a')
        MensajeForo.objects.create(foro=otro_foro, estudiante=self.ana, contenido='b')

        self.assertEqual(self.ids(f'/api/mensajes-foro/?foro={self.foro.id}'), {mensaje.id})
        self.assertEqual(self.client.get('/api/mensajes-foro/?foro=abc').status_code, 400)

    def test_ticket_ignora_estado_y_respuesta_del_cliente(self):
        r = self.client.post('/api/mesa-ayuda/', {
            'categoria': 'tecnico', 'asunto': 'a', 'descripcion': 'd',
            'estado': 'resuelto', 'respuesta': 'yo mismo',
        })
        self.assertEqual(r.status_code, 201)
        ticket = MesaAyuda.objects.get()
        self.assertEqual((ticket.estudiante, ticket.estado, ticket.respuesta), (self.ana, 'abierto', ''))


class ProfesorTests(BaseAuthTest):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.profe)

    def test_ve_alumnos_de_sus_cursos(self):
        self.assertEqual(self.ids('/api/estudiantes/'), {self.ana.id})

    def test_edita_su_curso_pero_no_el_ajeno(self):
        self.assertEqual(self.client.patch(f'/api/cursos/{self.curso.id}/', {'nombre': 'Mate II'}).status_code, 200)
        self.assertEqual(self.client.patch(f'/api/cursos/{self.curso_ajeno.id}/', {'nombre': 'X'}).status_code, 404)

    def test_no_crea_ni_borra_cursos(self):
        self.assertEqual(self.client.delete(f'/api/cursos/{self.curso.id}/').status_code, 403)

    def test_no_se_quita_la_titularidad(self):
        r = self.client.patch(f'/api/cursos/{self.curso.id}/', {'titular': self.otro_profe.id})
        self.assertEqual(r.status_code, 403)

    def test_tareas_solo_en_sus_cursos(self):
        datos = {'titulo': 't', 'descripcion': 'd', 'fecha_vencimiento': (timezone.now() + timedelta(days=1)).isoformat()}
        r = self.client.post('/api/tareas/', {**datos, 'curso': self.curso.id})
        self.assertEqual(r.status_code, 201)
        r = self.client.post('/api/tareas/', {**datos, 'curso': self.curso_ajeno.id})
        self.assertEqual(r.status_code, 403)

    def test_no_mueve_tarea_a_curso_ajeno(self):
        tarea = Tarea.objects.create(titulo='t', descripcion='d', curso=self.curso, fecha_vencimiento=timezone.now())
        r = self.client.patch(f'/api/tareas/{tarea.id}/', {'curso': self.curso_ajeno.id})
        self.assertEqual(r.status_code, 403)

    def test_publica_en_foro_de_su_curso(self):
        r = self.client.post('/api/mensajes-foro/', {'foro': self.foro.id, 'contenido': 'Bienvenidos'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['autor_nombre'], r.data['autor_rol']), ('profe', 'profesor'))
        mensaje = MensajeForo.objects.get()
        self.assertEqual((mensaje.autor, mensaje.estudiante), (self.profe, None))

    def test_no_publica_en_foro_ajeno(self):
        r = self.client.post('/api/mensajes-foro/', {'foro': self.foro_ajeno.id, 'contenido': 'hola'})
        self.assertEqual(r.status_code, 403)

    def test_edita_su_mensaje_pero_no_el_de_un_alumno(self):
        propio = MensajeForo.objects.create(foro=self.foro, autor=self.profe, contenido='a')
        del_alumno = MensajeForo.objects.create(foro=self.foro, autor=self.u_ana, estudiante=self.ana, contenido='b')
        self.assertEqual(self.client.patch(f'/api/mensajes-foro/{propio.id}/', {'contenido': 'a2'}).status_code, 200)
        self.assertEqual(self.client.patch(f'/api/mensajes-foro/{del_alumno.id}/', {'contenido': 'b2'}).status_code, 403)

    def test_modera_foro_de_su_curso(self):
        mensaje = MensajeForo.objects.create(foro=self.foro, estudiante=self.ana, contenido='spam')
        self.assertEqual(self.client.delete(f'/api/mensajes-foro/{mensaje.id}/').status_code, 204)


class StaffTests(BaseAuthTest):
    def test_ve_y_edita_todo(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.ids('/api/cursos/'), {self.curso.id, self.curso_ajeno.id})
        self.assertEqual(self.client.patch(f'/api/cursos/{self.curso_ajeno.id}/', {'nombre': 'H'}).status_code, 200)


class UsuarioSinRolTests(BaseAuthTest):
    def test_no_ve_datos_privados(self):
        self.client.force_authenticate(User.objects.create_user('nadie', password='x'))
        self.assertEqual(self.ids('/api/estudiantes/'), set())
        self.assertEqual(self.ids('/api/cursos/'), set())


class EstudianteDadoDeBajaTests(BaseAuthTest):
    def dar_de_baja(self, estudiante, activo=False):
        estudiante.activo = activo
        estudiante.save()

    def test_no_inicia_sesion(self):
        self.dar_de_baja(self.ana)
        r = self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'})
        self.assertEqual(r.status_code, 403)
        self.assertIn('dada de baja', r.data['detail'])
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 403)

    def test_con_contrasena_incorrecta_no_revela_la_baja(self):
        self.dar_de_baja(self.ana)
        r = self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'mal'})
        self.assertEqual((r.status_code, r.data['detail']), (400, 'Usuario o contraseña incorrectos.'))

    def test_sesion_abierta_deja_de_servir(self):
        # Sesión real (no force_authenticate) para pasar por la clase de autenticación
        self.client.login(username='ana', password='x')
        self.assertEqual(self.client.get('/api/cursos/').status_code, 200)

        self.dar_de_baja(self.ana)
        self.assertEqual(self.client.get('/api/cursos/').status_code, 403)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 403)

        self.dar_de_baja(self.ana, activo=True)
        self.assertEqual(self.client.get('/api/cursos/').status_code, 200)

    def test_la_baja_de_uno_no_afecta_a_otros(self):
        self.dar_de_baja(self.beto)
        r = self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'})
        self.assertEqual(r.status_code, 200)


class CambiarPasswordTests(BaseAuthTest):
    URL = '/api/auth/cambiar-password/'
    NUEVA = 'Tortuga-Azul-2026'

    def setUp(self):
        super().setUp()
        # Sesión real: cambiar la contraseña debe conservarla (update_session_auth_hash)
        self.client.login(username='ana', password='x')

    def cambiar(self, actual='x', nueva=NUEVA, client=None):
        return (client or self.client).post(self.URL, {'password_actual': actual, 'password_nueva': nueva})

    def test_cambia_la_contrasena_y_conserva_la_sesion(self):
        r = self.cambiar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)

        self.client.logout()
        self.assertEqual(self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': 'x'}).status_code, 400)
        self.assertEqual(self.client.post('/api/auth/login/', {'usuario': 'ana', 'password': self.NUEVA}).status_code, 200)

    def test_contrasena_actual_incorrecta(self):
        r = self.cambiar(actual='mal')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password_actual', r.data)
        self.u_ana.refresh_from_db()
        self.assertTrue(self.u_ana.check_password('x'))

    def test_valida_la_contrasena_nueva(self):
        for debil in ('abc', '12345678', 'password', 'qwertyuiop'):
            r = self.cambiar(nueva=debil)
            self.assertEqual(r.status_code, 400, debil)
            self.assertIn('password_nueva', r.data)

    def test_la_nueva_debe_ser_distinta(self):
        self.u_ana.set_password(self.NUEVA)
        self.u_ana.save()
        self.client.login(username='ana', password=self.NUEVA)
        r = self.cambiar(actual=self.NUEVA, nueva=self.NUEVA)
        self.assertEqual(r.status_code, 400)
        self.assertIn('distinta', r.data['password_nueva'][0])

    def test_cierra_las_otras_sesiones(self):
        otra = self.client_class()
        otra.login(username='ana', password='x')
        self.assertEqual(otra.get('/api/auth/me/').status_code, 200)

        self.cambiar()
        self.assertEqual(otra.get('/api/auth/me/').status_code, 403)

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.cambiar().status_code, 403)

    def test_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username='ana', password='x')
        r = client.post(self.URL, {'password_actual': 'x', 'password_nueva': self.NUEVA})
        self.assertEqual(r.status_code, 403)

    def test_limite_de_intentos(self):
        for _ in range(5):
            self.cambiar(actual='mal')
        self.assertEqual(self.cambiar().status_code, 429)


class PasswordTemporalTests(BaseAuthTest):
    def test_el_alta_obliga_a_cambiar_la_contrasena_temporal(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post('/api/estudiantes/alta/', {
            'nombre': 'Carla', 'apellido': 'C', 'email': 'carla@x.com', 'matricula': 'A100',
            'nivel_educativo': 'licenciatura', 'programa': 'p', 'periodo_actual': '2026-2',
        })
        self.assertEqual(r.status_code, 201)
        temporal = r.data['password_temporal']
        self.client.force_authenticate(None)

        r = self.client.post('/api/auth/login/', {'usuario': 'A100', 'password': temporal})
        self.assertTrue(r.data['debe_cambiar_password'])
        r = self.client.post('/api/auth/cambiar-password/', {'password_actual': temporal, 'password_nueva': 'Tortuga-Azul-2026'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['debe_cambiar_password'])
        self.assertFalse(self.client.get('/api/auth/me/').data['debe_cambiar_password'])

    def test_las_cuentas_existentes_no_quedan_obligadas(self):
        self.client.force_authenticate(self.u_ana)
        self.assertFalse(self.client.get('/api/auth/me/').data['debe_cambiar_password'])
