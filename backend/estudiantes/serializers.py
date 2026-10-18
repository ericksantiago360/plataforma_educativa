import secrets

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from cuentas.models import EstadoCuenta
from perfiles.models import PerfilEstudiante
from .models import Estudiante

class EstudianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estudiante
        fields = ['id', 'nombre', 'apellido', 'email', 'matricula', 'telefono', 'fecha_inscripcion', 'activo']

class AltaEstudianteSerializer(serializers.ModelSerializer):
    """
    Alta completa desde Control Escolar: crea el Estudiante, su cuenta de acceso
    (usuario = matrícula, contraseña temporal aleatoria) y su perfil académico.
    """
    nivel_educativo = serializers.ChoiceField(choices=PerfilEstudiante.NIVELES_EDUCATIVOS, write_only=True)
    programa = serializers.CharField(max_length=200, write_only=True)
    periodo_actual = serializers.CharField(max_length=50, write_only=True)
    materias_totales = serializers.IntegerField(min_value=0, default=0, write_only=True)

    class Meta:
        model = Estudiante
        fields = ['id', 'nombre', 'apellido', 'email', 'matricula', 'telefono',
                  'nivel_educativo', 'programa', 'periodo_actual', 'materias_totales']
        # Los validadores automáticos de unicidad dan mensajes genéricos ("un/a estudiante con este/a…");
        # se reemplazan por los de validate_matricula / validate_email
        extra_kwargs = {'matricula': {'validators': []}, 'email': {'validators': []}}

    def validate_matricula(self, valor):
        # La matrícula también será el nombre de usuario
        if Estudiante.objects.filter(matricula=valor).exists() or User.objects.filter(username=valor).exists():
            raise serializers.ValidationError('Ya existe un estudiante o usuario con esta matrícula.')
        return valor

    def validate_email(self, valor):
        if Estudiante.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError('Ya existe un estudiante con este correo.')
        return valor

    @transaction.atomic
    def create(self, datos):
        datos_perfil = {campo: datos.pop(campo) for campo in ('nivel_educativo', 'programa', 'periodo_actual', 'materias_totales')}
        self.password_temporal = secrets.token_urlsafe(9)
        usuario = User.objects.create_user(
            username=datos['matricula'],
            password=self.password_temporal,
            first_name=datos['nombre'],
            last_name=datos['apellido'],
            email=datos['email'],
        )
        # La contraseña temporal la conoce quien hizo el alta: el alumno debe cambiarla al entrar
        EstadoCuenta.objects.create(usuario=usuario, debe_cambiar_password=True)
        estudiante = Estudiante.objects.create(usuario=usuario, **datos)
        PerfilEstudiante.objects.create(estudiante=estudiante, **datos_perfil)
        return estudiante
