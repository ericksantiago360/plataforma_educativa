from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConceptoPagoViewSet, CargoViewSet, PagoViewSet

router = DefaultRouter()
router.register(r'conceptos-pago', ConceptoPagoViewSet)
router.register(r'cargos', CargoViewSet)
router.register(r'pagos', PagoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
