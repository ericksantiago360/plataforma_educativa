"""
Reportes en PDF: kardex de un estudiante y reporte de grupo de una materia en un periodo.
Cada reporte se arma en dos pasos: datos_* reúne lo que se imprime (y es lo que revisan las pruebas)
y pdf_* lo dibuja con reportlab.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import content_disposition_header
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from perfiles.models import clave_periodo, promedio_de, ultimos_intentos

INSTITUCION = 'Campus Virtual'
ESTADOS = {'cursando': 'Cursando', 'aprobado': 'Aprobado', 'reprobado': 'Reprobado', 'baja': 'Baja'}

AZUL = colors.HexColor('#2563eb')
GRIS = colors.HexColor('#f3f4f6')
BORDE = colors.HexColor('#d1d5db')


def _calificacion(valor):
    return f'{valor:.1f}' if valor is not None else '—'


def respuesta_pdf(contenido, nombre_archivo):
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    respuesta['Content-Disposition'] = content_disposition_header(True, nombre_archivo)
    respuesta['Cache-Control'] = 'no-store'  # datos personales: que no queden en cachés compartidas
    return respuesta


# ---------- Datos ----------

def datos_kardex(estudiante):
    registros = sorted(
        estudiante.historial_escolar.select_related('materia'),
        key=lambda r: (clave_periodo(r.periodo), r.materia.nombre),
    )
    finales = ultimos_intentos(registros)
    perfil = getattr(estudiante, 'perfil', None)
    aprobadas = [r for r in finales if r.estado == 'aprobado']
    return {
        'estudiante': f'{estudiante.nombre} {estudiante.apellido}',
        'matricula': estudiante.matricula,
        'programa': perfil.programa if perfil else '',
        'nivel': perfil.get_nivel_educativo_display() if perfil else '',
        'filas': [
            [r.periodo, r.materia.codigo, r.materia.nombre, str(r.materia.creditos),
             _calificacion(r.calificacion), ESTADOS.get(r.estado, r.estado)]
            for r in registros
        ],
        'resumen': {
            'promedio': promedio_de(finales),
            'aprobadas': len(aprobadas),
            'creditos': sum(r.materia.creditos for r in aprobadas),
            'materias_totales': perfil.materias_totales if perfil else None,
        },
    }


def datos_reporte_grupo(materia, periodo):
    registros = list(materia.controlescolar_set.filter(periodo=periodo)
                     .select_related('estudiante').order_by('estudiante__apellido', 'estudiante__nombre'))
    titular = materia.curso.titular
    conteo = {estado: sum(1 for r in registros if r.estado == estado) for estado in ESTADOS}
    return {
        'materia': f'{materia.codigo} - {materia.nombre}',
        'curso': materia.curso.nombre,
        'profesor': (titular.get_full_name() or titular.username) if titular else materia.curso.profesor,
        'periodo': periodo,
        'filas': [
            [str(i), r.estudiante.matricula, f'{r.estudiante.apellido}, {r.estudiante.nombre}',
             _calificacion(r.calificacion), ESTADOS.get(r.estado, r.estado)]
            for i, r in enumerate(registros, start=1)
        ],
        'resumen': {
            'alumnos': len(registros),
            **conteo,
            # Promedio del grupo con calificaciones finales; los que siguen cursando no cuentan
            'promedio': promedio_de([r for r in registros if r.estado in ('aprobado', 'reprobado')]),
        },
    }


# ---------- PDF ----------

def _documento(titulo, bloques):
    salida = BytesIO()
    estilos = getSampleStyleSheet()
    emitido = timezone.localtime().strftime('%d/%m/%Y %H:%M')

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, 1.2 * cm, f'{INSTITUCION} · {titulo} · Emitido el {emitido}')
        canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f'Página {doc.page}')
        canvas.restoreState()

    encabezado = [
        Paragraph(f'<font color="#2563eb"><b>{INSTITUCION}</b></font>', estilos['Title']),
        Paragraph(escape(titulo), estilos['Heading2']),
        Spacer(1, 0.3 * cm),
    ]
    doc = SimpleDocTemplate(salida, pagesize=letter, title=titulo, author=INSTITUCION,
                            leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm)
    doc.build(encabezado + bloques, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()


def _datos_generales(pares):
    """Tabla de dos columnas 'Etiqueta: valor' para el encabezado del reporte."""
    estilos = getSampleStyleSheet()
    filas = [[Paragraph(f'<b>{escape(etiqueta)}</b>', estilos['Normal']), Paragraph(escape(str(valor)), estilos['Normal'])]
             for etiqueta, valor in pares if valor not in (None, '')]
    tabla = Table(filas, colWidths=[4 * cm, None], hAlign='LEFT')
    tabla.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 2), ('TOPPADDING', (0, 0), (-1, -1), 2)]))
    return tabla


def _tabla(encabezados, filas, anchos, columna_texto):
    """Tabla con encabezado azul y filas alternadas; columna_texto se ajusta en varias líneas si es larga."""
    estilos = getSampleStyleSheet()
    celda = estilos['BodyText'].clone('celda', fontSize=9, leading=11)
    cuerpo = [[Paragraph(escape(valor), celda) if i == columna_texto else valor for i, valor in enumerate(fila)]
              for fila in filas]
    tabla = Table([encabezados] + cuerpo, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS]),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tabla


def _sin_registros(texto):
    return Paragraph(f'<i>{escape(texto)}</i>', getSampleStyleSheet()['Normal'])


def pdf_kardex(datos):
    resumen = datos['resumen']
    avance = f"{resumen['aprobadas']} de {resumen['materias_totales']}" if resumen['materias_totales'] else resumen['aprobadas']
    bloques = [
        _datos_generales([('Estudiante', datos['estudiante']), ('Matrícula', datos['matricula']),
                          ('Programa', datos['programa']), ('Nivel', datos['nivel'])]),
        Spacer(1, 0.5 * cm),
        _tabla(['Periodo', 'Código', 'Materia', 'Créditos', 'Calif.', 'Estado'], datos['filas'],
               [2.2 * cm, 2.3 * cm, None, 1.8 * cm, 1.6 * cm, 2.3 * cm], columna_texto=2)
        if datos['filas'] else _sin_registros('Aún no hay materias registradas.'),
        Spacer(1, 0.5 * cm),
        _datos_generales([('Promedio general', f"{resumen['promedio']:.2f}"), ('Materias aprobadas', avance),
                          ('Créditos aprobados', resumen['creditos'])]),
        Spacer(1, 0.2 * cm),
        Paragraph('<font size="8" color="grey">El promedio considera la última calificación final (aprobada o reprobada) '
                  'de cada materia.</font>', getSampleStyleSheet()['Normal']),
    ]
    return _documento('Kardex', bloques)


def pdf_reporte_grupo(datos):
    resumen = datos['resumen']
    bloques = [
        _datos_generales([('Materia', datos['materia']), ('Curso', datos['curso']),
                          ('Profesor', datos['profesor']), ('Periodo', datos['periodo'])]),
        Spacer(1, 0.5 * cm),
        _tabla(['#', 'Matrícula', 'Alumno', 'Calif.', 'Estado'], datos['filas'],
               [1 * cm, 3 * cm, None, 1.8 * cm, 2.5 * cm], columna_texto=2)
        if datos['filas'] else _sin_registros('No hay alumnos registrados en esta materia para el periodo.'),
        Spacer(1, 0.5 * cm),
        _datos_generales([('Alumnos', resumen['alumnos']), ('Aprobados', resumen['aprobado']),
                          ('Reprobados', resumen['reprobado']), ('Cursando', resumen['cursando']),
                          ('Bajas', resumen['baja']), ('Promedio del grupo', f"{resumen['promedio']:.2f}")]),
    ]
    return _documento('Reporte de grupo', bloques)
