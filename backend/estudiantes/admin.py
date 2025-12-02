from django.contrib import admin
from .models import Estudiante

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'matricula', 'email', 'activo')
    search_fields = ('nombre', 'apellido', 'matricula', 'email')
    list_filter = ('activo', 'fecha_inscripcion')
