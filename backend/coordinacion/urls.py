from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TareaViewSet, ComunicadoViewSet

router = DefaultRouter()
router.register(r'tareas', TareaViewSet)
router.register(r'comunicados', ComunicadoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
