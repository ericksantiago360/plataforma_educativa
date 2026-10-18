"""
Avisos por correo a los alumnos.

Se envían cuando la operación ya se guardó (transaction.on_commit) y un fallo del servidor de correo
solo se registra en el log: nunca deshace ni rompe lo que hizo el usuario.
El servidor se configura con las variables EMAIL_* (ver settings.py); en desarrollo, Mailpit los atrapa.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.utils import timezone

from estudiantes.models import Estudiante
from pagos.recibos import datos_recibo, pdf_recibo

logger = logging.getLogger(__name__)

INSTITUCION = 'Campus Virtual'
ESTADOS_FINALES = ('aprobado', 'reprobado')


def _pesos(monto):
    return f'${monto:,.2f} MXN'


def _mensaje(estudiante, asunto, cuerpo, adjuntos=()):
    texto = (f'Hola {estudiante.nombre}:\n\n{cuerpo}\n\n'
             f'Entra a la plataforma para ver los detalles: {settings.URL_PLATAFORMA}\n\n'
             f'— {INSTITUCION}\nEste es un aviso automático; por favor no respondas a este correo.')
    mensaje = EmailMessage(f'[{INSTITUCION}] {asunto}', texto, to=[estudiante.email])
    for nombre, contenido, tipo in adjuntos:
        mensaje.attach(nombre, contenido, tipo)
    return mensaje


def enviar(mensajes):
    mensajes = [m for m in mensajes if all(m.to)]
    if not mensajes:
        return

    def _enviar():
        try:
            # Una sola conexión para todo el lote (p. ej. una colegiatura a todo el alumnado)
            with get_connection() as conexion:
                conexion.send_messages(mensajes)
        except Exception:
            logger.exception('No se pudieron enviar %d avisos por correo', len(mensajes))

    transaction.on_commit(_enviar)


# ---------- Avisos ----------

def avisar_tarea_nueva(tarea):
    fecha = timezone.localtime(tarea.fecha_vencimiento).strftime('%d/%m/%Y %H:%M')
    enviar([
        _mensaje(alumno, f'Nueva tarea: {tarea.titulo}',
                 f'Tienes una tarea nueva en {tarea.curso.nombre}: "{tarea.titulo}".\nFecha de entrega: {fecha}.')
        for alumno in tarea.curso.estudiantes.filter(activo=True)
    ])


def avisar_calificacion(registro):
    if registro.estado not in ESTADOS_FINALES or not registro.estudiante.activo:
        return
    calificacion = f'{registro.calificacion:.1f}' if registro.calificacion is not None else 'sin calificación'
    enviar([_mensaje(registro.estudiante, f'Calificación de {registro.materia.nombre}',
                     f'Se registró tu calificación de {registro.materia.nombre} ({registro.periodo}): '
                     f'{calificacion} — {registro.get_estado_display()}.')])


def avisar_cargos(cargos):
    enviar([
        _mensaje(cargo.estudiante, f'Nuevo cargo: {cargo.descripcion}',
                 f'Se generó un cargo por "{cargo.descripcion}"{f" ({cargo.periodo})" if cargo.periodo else ""} '
                 f'de {_pesos(cargo.monto)}.'
                 + (f'\nFecha límite de pago: {cargo.fecha_limite.strftime("%d/%m/%Y")}.' if cargo.fecha_limite else '')
                 + '\nPuedes pagar en caja, por transferencia o depósito.')
        for cargo in cargos if cargo.estudiante.activo
    ])


def avisar_pago(pago):
    cargo = pago.cargo
    enviar([_mensaje(cargo.estudiante, f'Pago recibido {pago.folio}',
                     f'Registramos tu pago de {_pesos(pago.monto)} por "{cargo.descripcion}" '
                     f'({pago.get_metodo_display().lower()}).\nSaldo pendiente del concepto: {_pesos(cargo.saldo)}.\n'
                     f'Adjuntamos tu recibo.',
                     adjuntos=[(f'recibo-{pago.folio}.pdf', pdf_recibo(datos_recibo(pago)), 'application/pdf')])])


def avisar_pago_anulado(pago):
    cargo = pago.cargo
    enviar([_mensaje(cargo.estudiante, f'Pago anulado {pago.folio}',
                     f'Se anuló el pago {pago.folio} de {_pesos(pago.monto)} por "{cargo.descripcion}".\n'
                     f'Motivo: {pago.motivo_anulacion}\nSaldo pendiente del concepto: {_pesos(cargo.saldo)}.\n'
                     f'Si tienes dudas, acude a Control Escolar.')])


def avisar_respuesta_ticket(ticket):
    cuerpo = f'Tu solicitud "{ticket.asunto}" en la Mesa de Ayuda ahora está: {ticket.get_estado_display()}.'
    if ticket.respuesta:
        cuerpo += f'\n\nRespuesta:\n{ticket.respuesta}'
    enviar([_mensaje(ticket.estudiante, f'Mesa de Ayuda: {ticket.asunto}', cuerpo)])


def avisar_comunicado(comunicado):
    # Sin curso, el comunicado es para todo el alumnado activo
    alumnos = comunicado.curso.estudiantes.filter(activo=True) if comunicado.curso else Estudiante.objects.filter(activo=True)
    enviar([_mensaje(alumno, comunicado.titulo, comunicado.contenido) for alumno in alumnos])
