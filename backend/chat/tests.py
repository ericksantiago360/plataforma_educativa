from datetime import date

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import Group, User
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from chat.models import Conversacion, Mensaje
from config.asgi import application
from cuentas.tests import BaseAuthTest
from cursos.models import Curso
from estudiantes.models import Estudiante

MEMORIA = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


class ChatApiTests(BaseAuthTest):
    def sala(self, curso):
        return Conversacion.objects.get(curso=curso)

    def ids_conversaciones(self, usuario):
        self.client.force_authenticate(usuario)
        return {c['id'] for c in self.client.get('/api/chat/conversaciones/').data}

    def test_cada_quien_ve_las_salas_de_sus_cursos(self):
        self.assertEqual(len(self.ids_conversaciones(self.u_ana)), 1)  # la sala se crea al primer uso
        self.assertEqual(self.ids_conversaciones(self.u_ana), {self.sala(self.curso).id})
        self.assertEqual(self.ids_conversaciones(self.profe), {self.sala(self.curso).id})
        self.assertEqual(self.ids_conversaciones(self.u_beto), {self.sala(self.curso_ajeno).id})
        self.assertEqual(self.ids_conversaciones(self.staff), set())  # el staff atiende por privado
        self.assertEqual(self.ids_conversaciones(User.objects.create_user('nadie', password='x')), set())

    def test_quien_deja_el_curso_deja_de_ver_la_sala(self):
        sala = self.ids_conversaciones(self.u_ana).pop()
        self.curso.estudiantes.remove(self.ana)
        self.assertEqual(self.ids_conversaciones(self.u_ana), set())
        self.assertEqual(self.client.get(f'/api/chat/conversaciones/{sala}/mensajes/').status_code, 404)

    def test_contactos_por_rol(self):
        def contactos(usuario):
            self.client.force_authenticate(usuario)
            return {c['id'] for c in self.client.get('/api/chat/contactos/').data}
        self.assertEqual(contactos(self.u_ana), {self.profe.id, self.staff.id})  # su profesor y Control Escolar
        self.assertEqual(contactos(self.profe), {self.u_ana.id})                  # solo alumnos de sus cursos
        self.assertEqual(contactos(self.staff), {self.u_ana.id, self.u_beto.id})
        Estudiante.objects.filter(pk=self.beto.pk).update(activo=False)
        self.assertEqual(contactos(self.staff), {self.u_ana.id})

    def test_abrir_privada_una_sola_vez(self):
        self.client.force_authenticate(self.u_ana)
        r = self.client.post('/api/chat/conversaciones/privada/', {'usuario': self.profe.id})
        self.assertEqual((r.status_code, r.data['titulo'], r.data['subtitulo']), (201, 'profe', 'Profesor'))
        otra = self.client.post('/api/chat/conversaciones/privada/', {'usuario': self.profe.id})
        self.assertEqual((otra.status_code, otra.data['id']), (200, r.data['id']))

        # Desde el otro lado es la misma conversación, titulada con el nombre del alumno
        self.client.force_authenticate(self.profe)
        r = self.client.post('/api/chat/conversaciones/privada/', {'usuario': self.u_ana.id})
        self.assertEqual((r.status_code, r.data['id'], r.data['titulo']), (200, otra.data['id'], 'Ana A'))

    def test_privadas_no_permitidas(self):
        casos = [(self.u_ana, self.otro_profe), (self.u_ana, self.u_beto), (self.profe, self.u_beto), (self.profe, self.staff)]
        for usuario, otro in casos:
            self.client.force_authenticate(usuario)
            r = self.client.post('/api/chat/conversaciones/privada/', {'usuario': otro.id})
            self.assertEqual(r.status_code, 403, (usuario.username, otro.username))
        r = self.client.post('/api/chat/conversaciones/privada/', {'usuario': 'abc'})
        self.assertEqual(r.status_code, 400)

    def test_historial_paginado(self):
        sala = self.ids_conversaciones(self.u_ana).pop()
        Mensaje.objects.bulk_create([Mensaje(conversacion_id=sala, autor=self.profe, texto=f'm{i}') for i in range(60)])
        r = self.client.get(f'/api/chat/conversaciones/{sala}/mensajes/')
        textos = [m['texto'] for m in r.data['mensajes']]
        self.assertEqual((textos[0], textos[-1], len(textos), r.data['hay_mas']), ('m10', 'm59', 50, True))

        antes = r.data['mensajes'][0]['id']
        r = self.client.get(f'/api/chat/conversaciones/{sala}/mensajes/?antes={antes}')
        self.assertEqual(([m['texto'] for m in r.data['mensajes']][-1], len(r.data['mensajes']), r.data['hay_mas']), ('m9', 10, False))

    def test_no_leidos_y_marcar_leido(self):
        sala = self.ids_conversaciones(self.u_ana).pop()
        Mensaje.objects.create(conversacion_id=sala, autor=self.profe, texto='Hola grupo')
        Mensaje.objects.create(conversacion_id=sala, autor=self.u_ana, texto='Hola profe')  # lo propio no cuenta
        conversacion = self.client.get('/api/chat/conversaciones/').data[0]
        self.assertEqual((conversacion['no_leidos'], conversacion['ultimo']['texto']), (1, 'Hola profe'))

        self.assertEqual(self.client.post(f'/api/chat/conversaciones/{sala}/leer/').status_code, 204)
        self.assertEqual(self.client.get('/api/chat/conversaciones/').data[0]['no_leidos'], 0)

    def test_conversacion_ajena(self):
        sala_ajena = Conversacion.objects.create(tipo='curso', curso=self.curso_ajeno)
        self.client.force_authenticate(self.u_ana)
        self.assertEqual(self.client.get(f'/api/chat/conversaciones/{sala_ajena.id}/mensajes/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/chat/conversaciones/{sala_ajena.id}/leer/').status_code, 404)


@override_settings(CHANNEL_LAYERS=MEMORIA)
class ChatWebSocketTests(TransactionTestCase):
    """Conexiones WebSocket reales contra el ASGI del proyecto, con la cookie de sesión de cada usuario."""

    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name='Profesor')
        self.profe = User.objects.create_user('profe', password='x')
        self.profe.groups.add(grupo)
        self.staff = User.objects.create_user('staff', password='x', is_staff=True)
        self.u_ana = User.objects.create_user('ana', password='x')
        self.u_beto = User.objects.create_user('beto', password='x')
        self.ana = Estudiante.objects.create(usuario=self.u_ana, nombre='Ana', apellido='A', email='ana@x.com', matricula='1')
        self.beto = Estudiante.objects.create(usuario=self.u_beto, nombre='Beto', apellido='B', email='beto@x.com', matricula='2')
        hoy = date.today()
        self.curso = Curso.objects.create(nombre='Mate', codigo='M1', descripcion='', profesor='p', titular=self.profe,
                                          fecha_inicio=hoy, fecha_fin=hoy)
        self.curso.estudiantes.add(self.ana)
        self.sala = Conversacion.objects.create(tipo='curso', curso=self.curso)

    def cookie(self, usuario):
        cliente = APIClient()
        cliente.force_login(usuario)
        return cliente.cookies['sessionid'].value

    async def conectar(self, usuario=None, origen='http://localhost'):
        cabeceras = [(b'origin', origen.encode()), (b'host', b'localhost')]
        if usuario is not None:
            sesion = await sync_to_async(self.cookie)(usuario)
            cabeceras.append((b'cookie', f'sessionid={sesion}'.encode()))
        comunicador = WebsocketCommunicator(application, '/ws/chat/', headers=cabeceras)
        conectado, _ = await comunicador.connect()
        return comunicador, conectado

    async def enviar(self, comunicador, texto, conversacion=None):
        await comunicador.send_json_to({'tipo': 'mensaje', 'conversacion': conversacion or self.sala.id, 'texto': texto})

    async def test_sin_sesion_o_de_otro_origen_no_conecta(self):
        _, conectado = await self.conectar()
        self.assertFalse(conectado)
        _, conectado = await self.conectar(self.u_ana, origen='https://sitio-malicioso.com')
        self.assertFalse(conectado)

    async def test_mensaje_en_la_sala_llega_a_todos_sus_miembros_y_a_nadie_mas(self):
        ana, _ = await self.conectar(self.u_ana)
        profe, _ = await self.conectar(self.profe)
        beto, _ = await self.conectar(self.u_beto)

        await self.enviar(ana, '¿Hay clase mañana?')
        for comunicador in (ana, profe):
            recibido = await comunicador.receive_json_from(timeout=2)
            self.assertEqual((recibido['tipo'], recibido['mensaje']['texto'], recibido['mensaje']['autor_nombre']),
                             ('mensaje', '¿Hay clase mañana?', 'Ana A'))
        self.assertTrue(await beto.receive_nothing(timeout=0.3))
        self.assertEqual(await sync_to_async(Mensaje.objects.filter(conversacion=self.sala).count)(), 1)
        for comunicador in (ana, profe, beto):
            await comunicador.disconnect()

    async def test_no_escribe_en_una_conversacion_ajena(self):
        beto, _ = await self.conectar(self.u_beto)
        await self.enviar(beto, 'intruso')
        self.assertEqual((await beto.receive_json_from(timeout=2))['tipo'], 'error')
        self.assertFalse(await sync_to_async(Mensaje.objects.exists)())
        await beto.disconnect()

    async def test_valida_el_texto_y_limita_la_velocidad(self):
        ana, _ = await self.conectar(self.u_ana)
        for texto in ('   ', 'x' * 2001):
            await self.enviar(ana, texto)
            self.assertEqual((await ana.receive_json_from(timeout=2))['tipo'], 'error')

        for i in range(10):
            await self.enviar(ana, f'm{i}')
            self.assertEqual((await ana.receive_json_from(timeout=2))['tipo'], 'mensaje')
        await self.enviar(ana, 'uno de más')
        respuesta = await ana.receive_json_from(timeout=2)
        self.assertEqual(respuesta['tipo'], 'error')
        self.assertIn('muy rápido', respuesta['detalle'])
        await ana.disconnect()

    async def test_privada_nueva_llega_a_las_pestanas_abiertas(self):
        ana, _ = await self.conectar(self.u_ana)
        profe, _ = await self.conectar(self.profe)

        def abrir_privada():
            cliente = APIClient()
            cliente.force_authenticate(self.u_ana)
            return cliente.post('/api/chat/conversaciones/privada/', {'usuario': self.profe.id}).data['id']
        privada = await sync_to_async(abrir_privada)()

        for comunicador in (ana, profe):
            self.assertEqual(await comunicador.receive_json_from(timeout=2), {'tipo': 'conversacion_nueva', 'conversacion': privada})
        await self.enviar(profe, 'Te escribo por privado', conversacion=privada)
        self.assertEqual((await ana.receive_json_from(timeout=2))['mensaje']['texto'], 'Te escribo por privado')
        await ana.disconnect()
        await profe.disconnect()

    async def test_alumno_dado_de_baja_no_conecta_ni_escribe(self):
        ana, _ = await self.conectar(self.u_ana)
        await sync_to_async(Estudiante.objects.filter(pk=self.ana.pk).update)(activo=False)
        await self.enviar(ana, 'sigo aquí')
        self.assertEqual((await ana.receive_output(timeout=2))['type'], 'websocket.close')
        self.assertFalse(await sync_to_async(Mensaje.objects.exists)())

        _, conectado = await self.conectar(self.u_ana)
        self.assertFalse(conectado)
