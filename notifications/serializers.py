from rest_framework import serializers
from .models import FCMToken, Notification, NotificationTemplate


class FCMTokenSerializer(serializers.ModelSerializer):
    """
    Serializer para tokens FCM
    """
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'device_type', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_token(self, value):
        """
        Validar que el token no esté vacío
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El token FCM no puede estar vacío")
        return value


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer para notificaciones
    """
    notification_type_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'notification_type', 'notification_type_display',
            'title', 'body', 'data', 'status', 'status_display', 'fcm_message_id',
            'error_message', 'read_at', 'created_at', 'updated_at', 'is_read'
        ]
        read_only_fields = [
            'id', 'user', 'fcm_message_id', 'error_message', 'created_at', 'updated_at'
        ]

    def get_notification_type_display(self, obj):
        """
        Obtener el display name del tipo de notificación
        """
        type_choices = dict(NotificationTemplate.TYPE_CHOICES)
        return type_choices.get(obj.notification_type, obj.notification_type)

    def get_status_display(self, obj):
        """
        Obtener el display name del estado
        """
        return obj.get_status_display()

    def get_user_name(self, obj):
        """
        Obtener el nombre completo del usuario
        """
        return obj.user.get_full_name() or obj.user.username


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer para plantillas de notificaciones
    """
    notification_type_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title_template', 'body_template', 'is_active'
        ]

    def get_notification_type_display(self, obj):
        """
        Obtener el display name del tipo
        """
        return obj.get_notification_type_display()


class NotificationCreateSerializer(serializers.Serializer):
    """
    Serializer para crear notificaciones manualmente (admin)
    """
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista de IDs de usuarios destinatarios"
    )
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.TYPE_CHOICES,
        help_text="Tipo de notificación"
    )
    context = serializers.DictField(
        required=False,
        default=dict,
        help_text="Datos adicionales para la plantilla"
    )

    def validate_user_ids(self, value):
        """
        Validar que los IDs de usuarios existan
        """
        if not value:
            raise serializers.ValidationError("Debe especificar al menos un usuario")

        from django.contrib.auth import get_user_model
        User = get_user_model()

        existing_users = User.objects.filter(id__in=value)
        if len(existing_users) != len(value):
            invalid_ids = set(value) - set(existing_users.values_list('id', flat=True))
            raise serializers.ValidationError(f"Usuarios no encontrados: {list(invalid_ids)}")

        return value

    def validate_notification_type(self, value):
        """
        Validar que exista una plantilla activa para el tipo
        """
        if not NotificationTemplate.objects.filter(
            notification_type=value,
            is_active=True
        ).exists():
            raise serializers.ValidationError(f"No existe plantilla activa para el tipo: {value}")

        return value


class FCMTokenCreateSerializer(serializers.Serializer):
    """
    Serializer simplificado para crear tokens FCM desde Flutter
    """
    fcm_token = serializers.CharField(max_length=500)
    device_type = serializers.ChoiceField(
        choices=[('android', 'Android'), ('ios', 'iOS')],
        default='android'
    )

    def validate_fcm_token(self, value):
        """
        Validar token FCM
        """
        if not value or not value.strip():
            raise serializers.ValidationError("El token FCM no puede estar vacío")
        return value.strip()