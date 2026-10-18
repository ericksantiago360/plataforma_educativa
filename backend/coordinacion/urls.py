from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TareaViewSet, ArchivoEntregaViewSet, ComunicadoViewSet

router = DefaultRouter()
router.register(r'tareas', TareaViewSet)
router.register(r'comunicados', ComunicadoViewSet)
router.register(r'archivos-entrega', ArchivoEntregaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
