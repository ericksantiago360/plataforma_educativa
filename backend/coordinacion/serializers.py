from rest_framework import serializers
from cuentas.roles import estudiante_de
from .models import Tarea, EntregaTarea, ArchivoEntrega, Comunicado

class ArchivoEntregaSerializer(serializers.ModelSerializer):
    # Nunca se expone la ruta en disco: solo la URL que revisa permisos
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        return f'/api/archivos-entrega/{obj.id}/descargar/'

    class Meta:
        model = ArchivoEntrega
        fields = ['id', 'nombre', 'tipo', 'tamano', 'subido', 'url']

def datos_de_entrega(entrega):
    """Estado, fecha de entrega y archivos de un alumno en una tarea (entrega puede ser None: pendiente sin archivos)."""
    estado = entrega.estado if entrega else 'pendiente'
    return {
        'estado': estado,
        'estado_nombre': dict(EntregaTarea.ESTADOS)[estado],
        'entregado': serializers.DateTimeField().to_representation(entrega.entregado) if entrega and entrega.entregado else None,
        'tarde': entrega.tarde if entrega else False,
        'archivos': ArchivoEntregaSerializer(entrega.archivos.all(), many=True).data if entrega else [],
    }

class TareaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get('request')
        estudiante = estudiante_de(request.user) if request else None
        if estudiante:
            # El alumno ve su propio avance y sus archivos
            datos.update(datos_de_entrega(instance.entregas.filter(estudiante=estudiante).first()))
        else:
            # Profesor y staff ven el avance del grupo (solo alumnos inscritos hoy en el curso)
            inscritos = instance.curso.estudiantes.all()
            datos['resumen'] = {
                'completadas': instance.entregas.filter(estado='completada', estudiante__in=inscritos).count(),
                'en_progreso': instance.entregas.filter(estado='en_progreso', estudiante__in=inscritos).count(),
                'con_archivos': instance.entregas.filter(archivos__isnull=False, estudiante__in=inscritos).distinct().count(),
                'alumnos': inscritos.count(),
            }
        return datos

    class Meta:
        model = Tarea
        fields = ['id', 'titulo', 'descripcion', 'curso', 'curso_nombre', 'fecha_vencimiento', 'creado']

class ComunicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunicado
        fields = ['id', 'titulo', 'contenido', 'curso', 'fecha_creacion', 'activo']
