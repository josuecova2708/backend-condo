from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import FCMToken, Notification, NotificationTemplate
from .serializers import FCMTokenSerializer, NotificationSerializer, NotificationTemplateSerializer
from .services import FirebaseService


class FCMTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de tokens FCM
    """
    serializer_class = FCMTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar tokens del usuario actual
        """
        return FCMToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Crear o actualizar token FCM para el usuario actual
        """
        token = serializer.validated_data['token']
        device_type = serializer.validated_data.get('device_type', 'android')

        # Verificar si ya existe el token para este usuario
        existing_token, created = FCMToken.objects.get_or_create(
            user=self.request.user,
            token=token,
            defaults={
                'device_type': device_type,
                'is_active': True
            }
        )

        if not created:
            # Si ya existe, actualizar y activar
            existing_token.device_type = device_type
            existing_token.is_active = True
            existing_token.save()

        return existing_token

    def create(self, request, *args, **kwargs):
        """
        Registrar token FCM
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_instance = self.perform_create(serializer)

        return Response({
            'success': True,
            'message': 'Token FCM registrado exitosamente',
            'token_id': token_instance.id
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Desactivar un token FCM
        """
        try:
            token = self.get_object()
            token.is_active = False
            token.save()

            return Response({
                'success': True,
                'message': 'Token desactivado exitosamente'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar notificaciones del usuario
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar notificaciones del usuario actual
        """
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Obtener notificaciones no leídas
        """
        unread_notifications = self.get_queryset().filter(
            status__in=['sent', 'pending']
        ).exclude(status='read')

        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Obtener count de notificaciones no leídas
        """
        count = self.get_queryset().filter(
            status__in=['sent', 'pending']
        ).exclude(status='read').count()

        return Response({
            'unread_count': count
        })

    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """
        Marcar notificación como leída
        """
        try:
            notification = self.get_object()
            notification.mark_as_read()

            return Response({
                'success': True,
                'message': 'Notificación marcada como leída'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """
        Marcar todas las notificaciones como leídas
        """
        try:
            updated_count = self.get_queryset().filter(
                status__in=['sent', 'pending']
            ).exclude(status='read').update(
                status='read',
                read_at=timezone.now()
            )

            return Response({
                'success': True,
                'message': f'{updated_count} notificaciones marcadas como leídas'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar plantillas de notificaciones (solo lectura)
    """
    queryset = NotificationTemplate.objects.filter(is_active=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]


class NotificationTestViewSet(viewsets.ViewSet):
    """
    ViewSet para probar notificaciones (solo en desarrollo)
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def send_test(self, request):
        """
        Enviar notificación de prueba al usuario actual
        """
        try:
            notification_type = request.data.get('type', 'general')
            context = request.data.get('context', {})

            # Agregar datos del usuario al contexto
            context.update({
                'name': request.user.get_full_name() or request.user.username,
                'entity_id': '999'  # ID de prueba
            })

            success = FirebaseService.send_notification(
                user=request.user,
                notification_type=notification_type,
                context=context
            )

            if success:
                return Response({
                    'success': True,
                    'message': f'Notificación de prueba enviada: {notification_type}'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'No se pudo enviar la notificación'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def available_types(self, request):
        """
        Obtener tipos de notificaciones disponibles
        """
        templates = NotificationTemplate.objects.filter(is_active=True)
        types = [
            {
                'type': template.notification_type,
                'name': template.get_notification_type_display(),
                'title_template': template.title_template,
                'body_template': template.body_template
            }
            for template in templates
        ]

        return Response({
            'available_types': types
        })
