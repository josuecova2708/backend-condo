from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaComunViewSet, ReservaAreaViewSet

router = DefaultRouter()
router.register(r'areas', AreaComunViewSet, basename='area-comun')
router.register(r'reservas', ReservaAreaViewSet, basename='reserva-area')

urlpatterns = [
    path('', include(router.urls)),
]