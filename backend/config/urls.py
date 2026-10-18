from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('cuentas.urls')),
    path('api/', include('estudiantes.urls')),
    path('api/', include('cursos.urls')),
    path('api/', include('coordinacion.urls')),
    path('api/', include('perfiles.urls')),
    path('api/', include('servicios.urls')),
    path('api/', include('academico.urls')),
    path('api/', include('pagos.urls')),
]
