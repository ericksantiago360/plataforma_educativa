"""
Quién conversa con quién.
  - Sala de curso: el profesor titular y los alumnos activos inscritos (se calcula al momento: si alguien deja
    el curso, deja de ver la sala).
  - Privadas: alumno ↔ profesor de alguno de sus cursos, y alumno ↔ staff (Control Escolar).
Los estudiantes dados de baja no entran a nada (además la sesión ya no les sirve).
"""
from django.contrib.auth.models import User
from django.db.models import Q

from cuentas.roles import ESTUDIANTE, PROFESOR, STAFF, dado_de_baja, estudiante_de, rol_de
from cursos.models import Curso
from .models import Conversacion

MAXIMO_TEXTO = 2000


def nombre_de(user):
    estudiante = getattr(user, 'estudiante', None)
    if estudiante:
        return f'{estudiante.nombre} {estudiante.apellido}'
    return user.get_full_name() or user.username


def _activo(user):
    return user.is_authenticated and not dado_de_baja(user) and rol_de(user) is not None


def cursos_con_sala(user):
    rol = rol_de(user)
    if rol == PROFESOR:
        return Curso.objects.filter(titular=user)
    if rol == ESTUDIANTE:
        return estudiante_de(user).cursos.all()
    return Curso.objects.none()  # el staff atiende por privado, no está en las salas


def contactos(user):
    """Usuarios con los que user puede abrir una conversación privada."""
    rol = rol_de(user)
    if not _activo(user):
        return User.objects.none()
    if rol == ESTUDIANTE:
        titulares = Q(cursos_impartidos__estudiantes=estudiante_de(user))
        return User.objects.filter(titulares | Q(is_staff=True), is_active=True).exclude(pk=user.pk).distinct()
    alumnos = User.objects.filter(estudiante__activo=True, is_active=True)
    if rol == PROFESOR:
        return alumnos.filter(estudiante__cursos__titular=user).distinct()
    if rol == STAFF:
        return alumnos
    return User.objects.none()


def puede_conversar(user, otro):
    return contactos(user).filter(pk=otro.pk).exists()


def conversaciones_de(user):
    """Salas de sus cursos (se crean al primer uso) y sus privadas."""
    if not _activo(user):
        return Conversacion.objects.none()
    cursos = list(cursos_con_sala(user))
    con_sala = set(Conversacion.objects.filter(curso__in=cursos).values_list('curso_id', flat=True))
    for curso in cursos:
        if curso.pk not in con_sala:
            Conversacion.objects.get_or_create(tipo='curso', curso=curso)
    return Conversacion.objects.filter(Q(curso__in=cursos) | Q(participantes=user)).distinct()


def puede_ver(user, conversacion):
    return conversaciones_de(user).filter(pk=conversacion.pk).exists()


def privada_entre(user, otro):
    menor, mayor = sorted([user.pk, otro.pk])
    conversacion, creada = Conversacion.objects.get_or_create(tipo='privada', clave=f'{menor}-{mayor}')
    if creada:
        conversacion.participantes.add(user, otro)
    return conversacion, creada
