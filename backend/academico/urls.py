from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MateriaViewSet, ClaseEnLineaViewSet, ForoClaseViewSet, MensajeForoViewSet, ControlEscolarViewSet

router = DefaultRouter()
router.register(r'materias', MateriaViewSet)
router.register(r'clases', ClaseEnLineaViewSet)
router.register(r'foros', ForoClaseViewSet)
router.register(r'mensajes-foro', MensajeForoViewSet)
router.register(r'control-escolar', ControlEscolarViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
