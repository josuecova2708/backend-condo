from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.views import CondominioViewSet, BloqueViewSet, ConfiguracionSistemaViewSet

app_name = 'core'

router = DefaultRouter()
router.register(r'condominios', CondominioViewSet, basename='condominio')
router.register(r'bloques', BloqueViewSet, basename='bloque')
router.register(r'configuraciones', ConfiguracionSistemaViewSet, basename='configuracion')

urlpatterns = [
    path('', include(router.urls)),
]