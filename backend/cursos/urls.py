from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CursoViewSet
from .zoom_views import ClaseZoomViewSet, ParticipanteClaseViewSet

router = DefaultRouter()
router.register(r'cursos', CursoViewSet)
router.register(r'clases-zoom', ClaseZoomViewSet)
router.register(r'participantes-clase', ParticipanteClaseViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
