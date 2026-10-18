from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.utils import timezone

from academico.models import ControlEscolar
from coordinacion.models import Comunicado
from cuentas.tests import BaseAuthTest
from estudiantes.models import Estudiante
from pagos.models import Cargo, ConceptoPago
from servicios.models import MesaAyuda


class AvisosBase(BaseAuthTest):
    """Los avisos salen al confirmar la transacción: cada petición se hace dentro de captureOnCommitCallbacks."""

    def peticion(self, metodo, url, datos=None):
        # En JSON, como el frontend: con formularios, DRF toma un booleano ausente (p. ej. "activo") como False
        with self.captureOnCommitCallbacks(execute=True):
            return getattr(self.client, metodo)(url, datos or {}, format='json')

    def destinatarios(self):
        return sorted(correo for mensaje in mail.outbox for correo in mensaje.to)


class TareaYComunicadoTests(AvisosBase):
    def test_tarea_nueva_avisa_a_los_alumnos_activos_del_curso(self):
        self.curso.estudiantes.add(self.beto)
        Estudiante.objects.filter(pk=self.beto.pk).update(activo=False)
        self.client.force_authenticate(self.profe)
        r = self.peticion('post', '/api/tareas/', {'titulo': 'Ensayo', 'descripcion': 'd', 'curso': self.curso.id,
                                                    'fecha_vencimiento': (timezone.now() + timedelta(days=2)).isoformat()})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.destinatarios(), ['ana@x.com'])
        self.assertEqual(mail.outbox[0].subject, '[Campus Virtual] Nueva tarea: Ensayo')
        self.assertIn('Mate', mail.outbox[0].body)

    def test_comunicado_de_curso_y_general(self):
        self.client.force_authenticate(self.staff)
        self.peticion('post', '/api/comunicados/', {'titulo': 'Examen', 'contenido': 'El lunes', 'curso': self.curso.id})
        self.assertEqual(self.destinatarios(), ['ana@x.com'])

        mail.outbox.clear()
        self.peticion('post', '/api/comunicados/', {'titulo': 'Vacaciones', 'contenido': 'Del 1 al 15'})
        self.assertEqual(self.destinatarios(), ['ana@x.com', 'beto@x.com'])

    def test_comunicado_inactivo_no_avisa(self):
        self.client.force_authenticate(self.staff)
        self.peticion('post', '/api/comunicados/', {'titulo': 'Borrador', 'contenido': 'x', 'activo': False})
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(Comunicado.objects.exists())


class CalificacionTests(AvisosBase):
    def setUp(self):
        super().setUp()
        self.registro = ControlEscolar.objects.create(estudiante=self.ana, materia=self.foro.clase.materia, periodo='2026-2')
        self.url = f'/api/control-escolar/{self.registro.id}/'
        self.client.force_authenticate(self.profe)

    def test_calificacion_final_avisa_una_vez(self):
        self.peticion('patch', self.url, {'calificacion': '8.5', 'estado': 'aprobado'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('8.5 — Aprobado', mail.outbox[0].body)
        # Guardar sin cambios no vuelve a avisar
        self.peticion('patch', self.url, {'calificacion': '8.5'})
        self.assertEqual(len(mail.outbox), 1)

    def test_calificacion_parcial_no_avisa(self):
        self.peticion('patch', self.url, {'calificacion': '6'})  # sigue cursando
        self.assertEqual(len(mail.outbox), 0)


class PagosTests(AvisosBase):
    def setUp(self):
        super().setUp()
        self.concepto = ConceptoPago.objects.create(nombre='Colegiatura', tipo='colegiatura', monto=Decimal('3500'))
        self.client.force_authenticate(self.staff)

    def test_cargo_masivo_avisa_a_cada_alumno(self):
        r = self.peticion('post', '/api/cargos/masivo/', {'concepto': self.concepto.id, 'periodo': '2026-2',
                                                          'fecha_limite': '2026-09-10'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.destinatarios(), ['ana@x.com', 'beto@x.com'])
        self.assertIn('$3,500.00 MXN', mail.outbox[0].body)
        self.assertIn('10/09/2026', mail.outbox[0].body)

    def test_pago_avisa_con_el_recibo_adjunto_y_la_anulacion_tambien(self):
        cargo = Cargo.objects.create(estudiante=self.ana, concepto=self.concepto, descripcion='Colegiatura',
                                     tipo='colegiatura', monto=Decimal('3500'))
        r = self.peticion('post', f'/api/cargos/{cargo.id}/pagar/', {'monto': '1000', 'metodo': 'efectivo'})
        folio = r.data['pago']['folio']
        aviso = mail.outbox[0]
        self.assertEqual(aviso.subject, f'[Campus Virtual] Pago recibido {folio}')
        self.assertIn('Saldo pendiente del concepto: $2,500.00 MXN', aviso.body)
        nombre, contenido, tipo = aviso.attachments[0]
        self.assertEqual((nombre, tipo), (f'recibo-{folio}.pdf', 'application/pdf'))
        self.assertTrue(contenido.startswith(b'%PDF'))

        self.peticion('post', f"/api/pagos/{r.data['pago']['id']}/anular/", {'motivo': 'Error de captura'})
        self.assertEqual(mail.outbox[1].subject, f'[Campus Virtual] Pago anulado {folio}')
        self.assertIn('Error de captura', mail.outbox[1].body)
        self.assertIn('$3,500.00 MXN', mail.outbox[1].body)

    def test_pago_rechazado_no_avisa(self):
        cargo = Cargo.objects.create(estudiante=self.ana, descripcion='x', tipo='tramite', monto=Decimal('10'))
        self.peticion('post', f'/api/cargos/{cargo.id}/pagar/', {'monto': '999', 'metodo': 'efectivo'})
        self.assertEqual(len(mail.outbox), 0)

    def test_si_falla_el_correo_la_operacion_se_conserva(self):
        cargo = Cargo.objects.create(estudiante=self.ana, descripcion='x', tipo='tramite', monto=Decimal('10'))
        with mock.patch('notificaciones.correo.get_connection', side_effect=ConnectionRefusedError('SMTP caído')), \
                self.assertLogs('notificaciones.correo', level='ERROR'):
            r = self.peticion('post', f'/api/cargos/{cargo.id}/pagar/', {'monto': '10', 'metodo': 'efectivo'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(cargo.pagos.count(), 1)


class MesaAyudaTests(AvisosBase):
    def test_respuesta_del_staff_avisa_al_alumno(self):
        ticket = MesaAyuda.objects.create(estudiante=self.ana, categoria='tecnico', asunto='No veo mis tareas', descripcion='d')
        self.client.force_authenticate(self.staff)
        self.peticion('patch', f'/api/mesa-ayuda/{ticket.id}/', {'estado': 'resuelto', 'respuesta': 'Ya quedó'})
        self.assertEqual(self.destinatarios(), ['ana@x.com'])
        self.assertIn('Resuelto', mail.outbox[0].body)
        self.assertIn('Ya quedó', mail.outbox[0].body)

    def test_abrir_un_ticket_no_avisa(self):
        self.client.force_authenticate(self.u_ana)
        self.peticion('post', '/api/mesa-ayuda/', {'categoria': 'tecnico', 'asunto': 'a', 'descripcion': 'd'})
        self.assertEqual(len(mail.outbox), 0)
