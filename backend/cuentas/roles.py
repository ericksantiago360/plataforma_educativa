GRUPO_PROFESOR = 'Profesor'

STAFF = 'staff'
PROFESOR = 'profesor'
ESTUDIANTE = 'estudiante'


def es_profesor(user):
    return user.is_authenticated and user.groups.filter(name=GRUPO_PROFESOR).exists()


def estudiante_de(user):
    """Devuelve el Estudiante enlazado al usuario, o None."""
    if not user.is_authenticated:
        return None
    return getattr(user, 'estudiante', None)


def rol_de(user):
    if not user.is_authenticated:
        return None
    if user.is_staff:
        return STAFF
    if es_profesor(user):
        return PROFESOR
    if estudiante_de(user):
        return ESTUDIANTE
    return None
