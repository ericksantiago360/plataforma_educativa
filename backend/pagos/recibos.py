"""Recibo de pago en PDF, con el mismo formato que los reportes académicos."""
from xml.sax.saxutils import escape

from django.db.models import Sum
from django.utils import timezone
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer

from academico.reportes import _datos_generales, _documento


def _pesos(monto):
    return f'${monto:,.2f} MXN'


def _saldo_tras(pago):
    """Saldo del cargo justo después de este pago: reimprimir un recibo viejo no debe cambiarlo."""
    pagado = pago.cargo.pagos.filter(anulado=False, pk__lte=pago.pk).aggregate(t=Sum('monto'))['t'] or 0
    return max(pago.cargo.monto - pagado, 0)


def datos_recibo(pago):
    cargo = pago.cargo
    estudiante = cargo.estudiante
    return {
        'folio': pago.folio,
        'fecha': timezone.localtime(pago.fecha).strftime('%d/%m/%Y %H:%M'),
        'estudiante': f'{estudiante.nombre} {estudiante.apellido}',
        'matricula': estudiante.matricula,
        'concepto': cargo.descripcion + (f' ({cargo.periodo})' if cargo.periodo else ''),
        'monto': _pesos(pago.monto),
        'metodo': pago.get_metodo_display(),
        'referencia': pago.referencia,
        'saldo': _pesos(_saldo_tras(pago)),
        'anulado': pago.motivo_anulacion if pago.anulado else None,
    }


def pdf_recibo(datos):
    estilos = getSampleStyleSheet()
    bloques = []
    if datos['anulado'] is not None:
        bloques += [
            Paragraph('<font color="#ef4444" size="16"><b>PAGO ANULADO</b></font>', estilos['Normal']),
            Paragraph(f"Motivo: {escape(datos['anulado'])}", estilos['Normal']),
            Spacer(1, 0.4 * cm),
        ]
    bloques += [
        _datos_generales([('Folio', datos['folio']), ('Fecha', datos['fecha']), ('Estudiante', datos['estudiante']),
                          ('Matrícula', datos['matricula'])]),
        Spacer(1, 0.5 * cm),
        _datos_generales([('Concepto', datos['concepto']), ('Importe pagado', datos['monto']),
                          ('Forma de pago', datos['metodo']), ('Referencia', datos['referencia']),
                          ('Saldo tras este pago', datos['saldo'])]),
    ]
    return _documento(f"Recibo de pago {datos['folio']}", bloques)
