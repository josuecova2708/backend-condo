import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.contrib.auth import get_user_model
import firebase_admin
from firebase_admin import credentials, messaging
import os
import tempfile

from .models import FCMToken, Notification, NotificationTemplate

User = get_user_model()
logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Servicio para gestionar notificaciones push con Firebase Cloud Messaging
    """

    _app = None
    _initialized = False

    @classmethod
    def _initialize_firebase(cls):
        """
        Inicializar Firebase Admin SDK
        """
        if cls._initialized:
            return

        try:
            # Verificar si ya existe una app inicializada
            if firebase_admin._apps:
                cls._app = firebase_admin.get_app()
                cls._initialized = True
                logger.info("✅ Firebase ya estaba inicializado")
                return

            # Configurar credenciales
            cred = None

            if settings.FIREBASE_CREDENTIALS_JSON:
                # Usar credenciales desde variable de entorno
                logger.info("🔧 Usando credenciales Firebase desde variable de entorno")
                try:
                    if isinstance(settings.FIREBASE_CREDENTIALS_JSON, str):
                        cred_data = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    else:
                        cred_data = settings.FIREBASE_CREDENTIALS_JSON

                    # Crear archivo temporal
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                        json.dump(cred_data, temp_file)
                        temp_path = temp_file.name

                    cred = credentials.Certificate(temp_path)

                except Exception as e:
                    logger.error(f"❌ Error procesando credenciales JSON: {e}")

            elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                # Usar archivo local
                logger.info("🔧 Usando credenciales Firebase desde archivo local")
                cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))

            if cred:
                cls._app = firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info("✅ Firebase inicializado correctamente")
            else:
                logger.error("❌ No se encontraron credenciales de Firebase")

        except Exception as e:
            logger.error(f"❌ Error inicializando Firebase: {e}")

    @classmethod
    def send_notification(cls, user: User, notification_type: str, context: Dict[str, Any] = None) -> bool:
        """
        Enviar notificación push a un usuario específico

        Args:
            user: Usuario destinatario
            notification_type: Tipo de notificación
            context: Datos adicionales para la plantilla

        Returns:
            bool: True si se envió exitosamente
        """
        cls._initialize_firebase()

        if not cls._initialized:
            logger.error("Firebase no está inicializado")
            return False

        try:
            # Obtener plantilla de notificación
            try:
                template = NotificationTemplate.objects.get(
                    notification_type=notification_type,
                    is_active=True
                )
            except NotificationTemplate.DoesNotExist:
                logger.error(f"❌ Plantilla no encontrada: {notification_type}")
                return False

            # Renderizar mensaje
            context = context or {}
            title, body = template.render(**context)

            # Obtener tokens FCM del usuario
            tokens = FCMToken.objects.filter(user=user, is_active=True)

            if not tokens.exists():
                logger.warning(f"⚠️ Usuario {user.username} no tiene tokens FCM")
                return False

            success_count = 0

            for fcm_token in tokens:
                try:
                    # Crear mensaje
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data={
                            'type': notification_type,
                            'entity_id': str(context.get('entity_id', '')),
                            'user_id': str(user.id),
                        },
                        token=fcm_token.token
                    )

                    # Enviar mensaje
                    response = messaging.send(message)

                    # Crear registro de notificación
                    notification = Notification.objects.create(
                        user=user,
                        notification_type=notification_type,
                        title=title,
                        body=body,
                        data={
                            'type': notification_type,
                            'entity_id': context.get('entity_id'),
                        },
                        status='sent',
                        fcm_message_id=response
                    )

                    logger.info(f"✅ Notificación enviada a {user.username}: {response}")
                    success_count += 1

                except messaging.UnregisteredError:
                    # Token inválido, marcarlo como inactivo
                    fcm_token.is_active = False
                    fcm_token.save()
                    logger.warning(f"⚠️ Token FCM inválido para {user.username}, desactivado")

                except Exception as e:
                    # Crear registro de notificación fallida
                    Notification.objects.create(
                        user=user,
                        notification_type=notification_type,
                        title=title,
                        body=body,
                        data={
                            'type': notification_type,
                            'entity_id': context.get('entity_id'),
                        },
                        status='failed',
                        error_message=str(e)
                    )
                    logger.error(f"❌ Error enviando notificación a {user.username}: {e}")

            return success_count > 0

        except Exception as e:
            logger.error(f"❌ Error general enviando notificación: {e}")
            return False

    @classmethod
    def send_to_multiple_users(cls, users: List[User], notification_type: str, context: Dict[str, Any] = None) -> int:
        """
        Enviar notificación a múltiples usuarios

        Args:
            users: Lista de usuarios
            notification_type: Tipo de notificación
            context: Datos adicionales

        Returns:
            int: Número de notificaciones enviadas exitosamente
        """
        success_count = 0

        for user in users:
            if cls.send_notification(user, notification_type, context):
                success_count += 1

        return success_count

    @classmethod
    def send_to_topic(cls, topic: str, notification_type: str, context: Dict[str, Any] = None) -> bool:
        """
        Enviar notificación a un tópico

        Args:
            topic: Nombre del tópico
            notification_type: Tipo de notificación
            context: Datos adicionales

        Returns:
            bool: True si se envió exitosamente
        """
        cls._initialize_firebase()

        if not cls._initialized:
            return False

        try:
            # Obtener plantilla
            template = NotificationTemplate.objects.get(
                notification_type=notification_type,
                is_active=True
            )

            context = context or {}
            title, body = template.render(**context)

            # Crear mensaje para tópico
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data={
                    'type': notification_type,
                    'entity_id': str(context.get('entity_id', '')),
                },
                topic=topic
            )

            # Enviar mensaje
            response = messaging.send(message)
            logger.info(f"✅ Notificación enviada al tópico {topic}: {response}")
            return True

        except Exception as e:
            logger.error(f"❌ Error enviando notificación al tópico {topic}: {e}")
            return False


class NotificationHelper:
    """
    Helpers para notificaciones específicas del condominio
    """

    @staticmethod
    def notify_reservation_confirmed(reservation):
        """
        Notificar que una reserva fue confirmada
        """
        from areas_comunes.models import ReservaArea

        if not isinstance(reservation, ReservaArea):
            return False

        # Obtener el usuario propietario
        user = reservation.propietario.user

        context = {
            'name': user.get_full_name(),
            'area': reservation.area.nombre,
            'date': reservation.fecha_inicio.strftime('%d/%m/%Y'),
            'time': reservation.fecha_inicio.strftime('%H:%M'),
            'entity_id': reservation.id,
        }

        return FirebaseService.send_notification(
            user=user,
            notification_type='reservation_confirmed',
            context=context
        )

    @staticmethod
    def notify_reservation_reminder(reservation):
        """
        Notificar recordatorio de reserva (30 minutos antes)
        """
        from areas_comunes.models import ReservaArea

        if not isinstance(reservation, ReservaArea):
            return False

        user = reservation.propietario.user

        context = {
            'name': user.get_full_name(),
            'area': reservation.area.nombre,
            'time': reservation.fecha_inicio.strftime('%H:%M'),
            'entity_id': reservation.id,
        }

        return FirebaseService.send_notification(
            user=user,
            notification_type='reservation_reminder',
            context=context
        )

    @staticmethod
    def notify_new_charge(charge):
        """
        Notificar nuevo cargo asignado
        """
        from finances.models import Cargo

        if not isinstance(charge, Cargo):
            return False

        # Obtener usuario asociado al cargo
        user = charge.propietario.user

        context = {
            'name': user.get_full_name(),
            'amount': f"{charge.monto} {charge.moneda}",
            'description': charge.descripcion,
            'entity_id': charge.id,
        }

        return FirebaseService.send_notification(
            user=user,
            notification_type='new_charge',
            context=context
        )