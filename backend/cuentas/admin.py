from django.contrib import admin
from .models import EstadoCuenta

@admin.register(EstadoCuenta)
class EstadoCuentaAdmin(admin.ModelAdmin):
    # Marcar debe_cambiar_password obliga al usuario a elegir una contraseña nueva al entrar
    list_display = ('usuario', 'debe_cambiar_password')
    list_filter = ('debe_cambiar_password',)
    search_fields = ('usuario__username',)
