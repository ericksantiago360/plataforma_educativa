from django.contrib import admin
from .models import Conversacion, Mensaje

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tipo', 'ultimo_mensaje')
    list_filter = ('tipo',)

@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = ('autor', 'conversacion', 'texto', 'enviado')
    search_fields = ('texto', 'autor__username')
