from django.contrib import admin
from .models import Tarea, EntregaTarea, Comunicado

class EntregaTareaInline(admin.TabularInline):
    model = EntregaTarea
    extra = 0

@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'fecha_vencimiento')
    search_fields = ('titulo',)
    list_filter = ('curso', 'fecha_vencimiento')
    inlines = [EntregaTareaInline]

@admin.register(Comunicado)
class ComunicadoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'curso', 'fecha_creacion', 'activo')
    search_fields = ('titulo',)
    list_filter = ('activo', 'fecha_creacion')
