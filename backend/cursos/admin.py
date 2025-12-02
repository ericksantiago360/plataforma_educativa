from django.contrib import admin
from .models import Curso

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'profesor', 'creditos', 'activo')
    search_fields = ('nombre', 'codigo', 'profesor')
    list_filter = ('activo', 'fecha_inicio')
