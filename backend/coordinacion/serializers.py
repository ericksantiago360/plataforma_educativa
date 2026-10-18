from rest_framework import serializers
from cuentas.roles import estudiante_de
from .models import Tarea, EntregaTarea, Comunicado

class TareaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get('request')
        estudiante = estudiante_de(request.user) if request else None
        if estudiante:
            # El alumno ve su propio avance
            entrega = instance.entregas.filter(estudiante=estudiante).first()
            estado = entrega.estado if entrega else 'pendiente'
            datos['estado'] = estado
            datos['estado_nombre'] = dict(EntregaTarea.ESTADOS)[estado]
        else:
            # Profesor y staff ven el avance del grupo (solo alumnos inscritos hoy en el curso)
            inscritos = instance.curso.estudiantes.all()
            datos['resumen'] = {
                'completadas': instance.entregas.filter(estado='completada', estudiante__in=inscritos).count(),
                'en_progreso': instance.entregas.filter(estado='en_progreso', estudiante__in=inscritos).count(),
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
