from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleViewSet, VehicleAccessLogViewSet, VehicleOCRViewSet

# Crear router para las APIs
router = DefaultRouter()
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'access-logs', VehicleAccessLogViewSet, basename='vehicle-access-log')
router.register(r'ocr', VehicleOCRViewSet, basename='vehicle-ocr')

app_name = 'ai_security'

urlpatterns = [
    path('api/', include(router.urls)),
]