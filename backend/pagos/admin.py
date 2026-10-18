from django.contrib import admin
from .models import ConceptoPago, Cargo, Pago

@admin.register(ConceptoPago)
class ConceptoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'monto', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)

class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ('fecha', 'registrado_por')
    can_delete = False  # los pagos se anulan, no se borran

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'estudiante', 'periodo', 'monto', 'cancelado', 'creado')
    list_filter = ('tipo', 'cancelado', 'periodo')
    search_fields = ('descripcion', 'estudiante__nombre', 'estudiante__apellido', 'estudiante__matricula')
    inlines = [PagoInline]
