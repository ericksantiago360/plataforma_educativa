from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (BibliotecaDigitalViewSet, MesaAyudaViewSet, EventoCalendarioViewSet, CentroIdiomasViewSet,
                    ClaseIdiomasViewSet, MaterialIdiomasViewSet)

router = DefaultRouter()
router.register(r'biblioteca', BibliotecaDigitalViewSet)
router.register(r'mesa-ayuda', MesaAyudaViewSet)
router.register(r'calendario', EventoCalendarioViewSet)
router.register(r'idiomas', CentroIdiomasViewSet)
router.register(r'idiomas-clases', ClaseIdiomasViewSet)
router.register(r'idiomas-materiales', MaterialIdiomasViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
