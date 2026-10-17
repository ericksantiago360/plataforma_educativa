from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PerfilEstudianteViewSet, TutorViewSet, AsignacionTutorViewSet

router = DefaultRouter()
router.register(r'perfiles', PerfilEstudianteViewSet)
router.register(r'tutores', TutorViewSet)
router.register(r'asignaciones-tutor', AsignacionTutorViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
