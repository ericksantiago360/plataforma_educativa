from django.contrib import admin

from .models import CentroIdiomas, ClaseIdiomas, MaterialIdiomas


class ClaseIdiomasInline(admin.TabularInline):
    model = ClaseIdiomas
    extra = 1


class MaterialIdiomasInline(admin.TabularInline):
    model = MaterialIdiomas
    extra = 1


@admin.register(CentroIdiomas)
class CentroIdiomasAdmin(admin.ModelAdmin):
    list_display = ('nombre_curso', 'idioma', 'nivel', 'instructor', 'fecha_inicio', 'precio', 'activo')
    list_filter = ('idioma', 'nivel', 'activo')
    inlines = [ClaseIdiomasInline, MaterialIdiomasInline]


admin.site.register(ClaseIdiomas)
admin.site.register(MaterialIdiomas)
