from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VehicleViewSet,
    VehicleAccessLogViewSet,
    VehicleOCRViewSet,
    PersonProfileViewSet,
    FacialAccessLogViewSet,
    FacialRecognitionViewSet,
    CameraViewSet
)
from .views_actividadsospechosa import ActividadSospechosaViewSet

# Crear router para las APIs
router = DefaultRouter()
# Vehicle-related endpoints
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'access-logs', VehicleAccessLogViewSet, basename='vehicle-access-log')
router.register(r'ocr', VehicleOCRViewSet, basename='vehicle-ocr')

# Facial recognition endpoints
router.register(r'facial-recognition', FacialRecognitionViewSet, basename='facial-recognition')
router.register(r'person-profiles', PersonProfileViewSet, basename='person-profile')
router.register(r'facial-access-logs', FacialAccessLogViewSet, basename='facial-access-log')

# Camera endpoints
router.register(r'cameras', CameraViewSet, basename='camera')

# Suspicious activity endpoints
router.register(r'actividad-sospechosa', ActividadSospechosaViewSet, basename='actividad-sospechosa')

app_name = 'ai_security'

urlpatterns = [
    path('api/', include(router.urls)),
]