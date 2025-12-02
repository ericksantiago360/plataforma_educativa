from django.contrib import admin
from .models import Tarea, Comunicado

@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'estado', 'fecha_vencimiento')
    search_fields = ('titulo',)
    list_filter = ('estado', 'fecha_vencimiento')

@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'fecha_creacion', 'activo')
    search_fields = ('titulo',)
    list_filter = ('activo', 'fecha_creacion')
