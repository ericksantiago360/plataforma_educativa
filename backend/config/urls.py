from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('estudiantes.urls')),
    path('api/', include('cursos.urls')),
    path('api/', include('coordinacion.urls')),
]
