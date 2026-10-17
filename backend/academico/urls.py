from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (MateriaViewSet, ClaseEnLineaViewSet, ForoClaseViewSet, MensajeForoViewSet, ControlEscolarViewSet,
                    ContenidoMateriaViewSet, ArchivoContenidoViewSet)

router = DefaultRouter()
router.register(r'materias', MateriaViewSet)
router.register(r'clases', ClaseEnLineaViewSet)
router.register(r'foros', ForoClaseViewSet)
router.register(r'mensajes-foro', MensajeForoViewSet)
router.register(r'control-escolar', ControlEscolarViewSet)
router.register(r'contenidos', ContenidoMateriaViewSet)
router.register(r'archivos-contenido', ArchivoContenidoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
