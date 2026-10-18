from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactosView, ConversacionViewSet

router = DefaultRouter()
router.register(r'chat/conversaciones', ConversacionViewSet, basename='conversacion')

urlpatterns = [
    path('chat/contactos/', ContactosView.as_view()),
    path('', include(router.urls)),
]
