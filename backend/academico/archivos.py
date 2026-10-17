"""Validación de adjuntos, saneamiento del HTML del editor y enlaces de YouTube para el contenido de materias."""
import os
import re

import nh3
from django.core.exceptions import ValidationError

MB = 1024 * 1024

# extensión → (tipo, content-type, firma que debe tener el archivo al inicio)
# La firma evita, por ejemplo, que un HTML renombrado a .pdf se acepte como documento.
FIRMA_ZIP = b'PK\x03\x04'          # docx, pptx, xlsx son ZIP
FIRMA_OLE = b'\xd0\xcf\x11\xe0'    # doc, ppt, xls (formato Office antiguo)
FORMATOS = {
    '.pdf': ('documento', 'application/pdf', [b'%PDF']),
    '.doc': ('documento', 'application/msword', [FIRMA_OLE]),
    '.docx': ('documento', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', [FIRMA_ZIP]),
    '.ppt': ('documento', 'application/vnd.ms-powerpoint', [FIRMA_OLE]),
    '.pptx': ('documento', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', [FIRMA_ZIP]),
    '.xls': ('documento', 'application/vnd.ms-excel', [FIRMA_OLE]),
    '.xlsx': ('documento', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', [FIRMA_ZIP]),
    '.jpg': ('imagen', 'image/jpeg', [b'\xff\xd8\xff']),
    '.jpeg': ('imagen', 'image/jpeg', [b'\xff\xd8\xff']),
    '.png': ('imagen', 'image/png', [b'\x89PNG\r\n\x1a\n']),
    '.gif': ('imagen', 'image/gif', [b'GIF87a', b'GIF89a']),
    '.webp': ('imagen', 'image/webp', [b'RIFF']),
    '.mp4': ('video', 'video/mp4', []),   # se revisa aparte: 'ftyp' en la posición 4
    '.webm': ('video', 'video/webm', [b'\x1a\x45\xdf\xa3']),
}

TAMANO_MAXIMO = {'documento': 25 * MB, 'imagen': 10 * MB, 'video': 200 * MB}


def formato_de(nombre):
    return FORMATOS.get(os.path.splitext(nombre)[1].lower())


def validar_archivo(archivo):
    """Devuelve el tipo ('documento', 'imagen' o 'video') o lanza ValidationError."""
    formato = formato_de(archivo.name)
    if formato is None:
        permitidas = ', '.join(sorted(FORMATOS))
        raise ValidationError(f'Formato no permitido. Usa: {permitidas}.')
    tipo, _, firmas = formato

    limite = TAMANO_MAXIMO[tipo]
    if archivo.size > limite:
        raise ValidationError(f'El archivo pesa {archivo.size / MB:.1f} MB; el máximo para {tipo}s es {limite // MB} MB.')
    if archivo.size == 0:
        raise ValidationError('El archivo está vacío.')

    archivo.seek(0)
    inicio = archivo.read(16)
    archivo.seek(0)
    extension = os.path.splitext(archivo.name)[1].lower()
    if extension == '.mp4':
        valido = inicio[4:8] == b'ftyp'
    elif extension == '.webp':
        valido = inicio[:4] == b'RIFF' and inicio[8:12] == b'WEBP'
    else:
        valido = any(inicio.startswith(firma) for firma in firmas)
    if not valido:
        raise ValidationError('El contenido del archivo no corresponde a su extensión.')
    return tipo


# HTML del editor: solo formato de texto, enlaces y tablas. Nada de scripts, estilos ni eventos.
ETIQUETAS_PERMITIDAS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup', 'code', 'pre', 'blockquote', 'hr',
    'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'a',
    'table', 'caption', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
}
ATRIBUTOS_PERMITIDOS = {
    'a': {'href', 'title'},
    'th': {'colspan', 'rowspan', 'scope'},
    'td': {'colspan', 'rowspan'},
}


def sanear_html(html):
    return nh3.clean(
        html or '',
        tags=ETIQUETAS_PERMITIDAS,
        attributes=ATRIBUTOS_PERMITIDOS,
        url_schemes={'http', 'https', 'mailto'},
        link_rel='noopener noreferrer',
    )


# youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID, youtube.com/shorts/ID
PATRON_YOUTUBE = re.compile(
    r'^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})(?:[?&#].*)?$'
)


def id_de_youtube(url):
    coincidencia = PATRON_YOUTUBE.match((url or '').strip())
    return coincidencia.group(1) if coincidencia else None
