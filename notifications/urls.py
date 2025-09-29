from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FCMTokenViewSet,
    NotificationViewSet,
    NotificationTemplateViewSet,
    NotificationTestViewSet
)

router = DefaultRouter()
router.register(r'fcm-tokens', FCMTokenViewSet, basename='fcm-tokens')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'templates', NotificationTemplateViewSet, basename='notification-templates')
router.register(r'test', NotificationTestViewSet, basename='notification-test')

urlpatterns = [
    path('api/', include(router.urls)),

    # Endpoint específico para registrar token FCM desde Flutter
    path('api/fcm-token/', FCMTokenViewSet.as_view({
        'post': 'create'
    }), name='fcm-token-register'),

    # Endpoint para notificaciones no leídas
    path('api/unread/', NotificationViewSet.as_view({
        'get': 'unread'
    }), name='unread-notifications'),
]