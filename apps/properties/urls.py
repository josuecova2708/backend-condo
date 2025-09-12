from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.properties.views import (
    UnidadHabitacionalViewSet,
    PropietarioViewSet,
    ResidenteViewSet,
    HistorialPropietariosViewSet
)

app_name = 'properties'

router = DefaultRouter()
router.register(r'unidades', UnidadHabitacionalViewSet, basename='unidad')
router.register(r'propietarios', PropietarioViewSet, basename='propietario')
router.register(r'residentes', ResidenteViewSet, basename='residente')
router.register(r'historial-propietarios', HistorialPropietariosViewSet, basename='historial-propietario')

urlpatterns = [
    path('', include(router.urls)),
]