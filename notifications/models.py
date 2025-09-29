from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel

User = get_user_model()


class FCMToken(TimeStampedModel):
    """
    Modelo para almacenar tokens FCM de usuarios
    """
    DEVICE_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fcm_tokens',
        help_text="Usuario propietario del token"
    )
    token = models.TextField(
        help_text="Token FCM del dispositivo"
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_CHOICES,
        default='android',
        help_text="Tipo de dispositivo"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Si el token está activo"
    )

    class Meta:
        db_table = 'fcm_tokens'
        verbose_name = 'Token FCM'
        verbose_name_plural = 'Tokens FCM'
        unique_together = ['user', 'token']  # Un usuario puede tener el mismo token solo una vez
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.device_type} - {self.token[:20]}..."


class NotificationTemplate(models.Model):
    """
    Plantillas para diferentes tipos de notificaciones
    """
    TYPE_CHOICES = [
        ('reservation_confirmed', 'Reserva Confirmada'),
        ('reservation_reminder', 'Recordatorio de Reserva'),
        ('new_charge', 'Nuevo Cargo'),
        ('payment_due', 'Pago Vencido'),
        ('general', 'General'),
    ]

    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        unique=True,
        help_text="Tipo de notificación"
    )
    title_template = models.CharField(
        max_length=100,
        help_text="Plantilla del título (puede usar variables como {name})"
    )
    body_template = models.TextField(
        help_text="Plantilla del cuerpo (puede usar variables como {area}, {date})"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Si la plantilla está activa"
    )

    class Meta:
        db_table = 'notification_templates'
        verbose_name = 'Plantilla de Notificación'
        verbose_name_plural = 'Plantillas de Notificaciones'
        ordering = ['notification_type']

    def __str__(self):
        return f"{self.get_notification_type_display()}"

    def render(self, **context):
        """
        Renderizar la plantilla con variables de contexto
        """
        title = self.title_template.format(**context)
        body = self.body_template.format(**context)
        return title, body

    def render_title(self, context):
        """
        Renderizar solo el título
        """
        return self.title_template.format(**context)

    def render_body(self, context):
        """
        Renderizar solo el cuerpo
        """
        return self.body_template.format(**context)


class Notification(TimeStampedModel):
    """
    Modelo para almacenar el historial de notificaciones enviadas
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviada'),
        ('failed', 'Fallida'),
        ('read', 'Leída'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="Usuario que recibe la notificación"
    )
    notification_type = models.CharField(
        max_length=30,
        help_text="Tipo de notificación"
    )
    title = models.CharField(
        max_length=100,
        help_text="Título de la notificación"
    )
    body = models.TextField(
        help_text="Cuerpo de la notificación"
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos adicionales (entity_id, type, etc.)"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Estado de la notificación"
    )
    fcm_message_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID del mensaje FCM"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Mensaje de error si falla el envío"
    )
    read_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha cuando se leyó la notificación"
    )

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {self.get_status_display()}"

    def mark_as_read(self):
        """
        Marcar notificación como leída
        """
        from django.utils import timezone
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])

    @property
    def is_read(self):
        """
        Verificar si la notificación ha sido leída
        """
        return self.status == 'read'
