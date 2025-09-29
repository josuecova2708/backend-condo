from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import logging

from .services import NotificationHelper

logger = logging.getLogger(__name__)


@receiver(post_save, sender='areas_comunes.ReservaArea')
def reservation_status_changed(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se crea o actualiza una reserva
    """
    try:
        if created:
            logger.info(f"🆕 Nueva reserva creada: {instance.id}")
            # No enviar notificación por crear reserva, solo cuando se confirme
            return

        # Verificar si la reserva fue confirmada
        if instance.estado == 'confirmada':
            # Verificar si el estado cambió a confirmada (no era confirmada antes)
            if hasattr(instance, '_previous_estado') and instance._previous_estado != 'confirmada':
                logger.info(f"✅ Reserva {instance.id} confirmada, enviando notificación...")

                success = NotificationHelper.notify_reservation_confirmed(instance)

                if success:
                    logger.info(f"📱 Notificación de confirmación enviada para reserva {instance.id}")
                else:
                    logger.error(f"❌ Error enviando notificación de confirmación para reserva {instance.id}")

    except Exception as e:
        logger.error(f"❌ Error en señal de reserva: {e}")


@receiver(pre_save, sender='areas_comunes.ReservaArea')
def store_previous_reservation_state(sender, instance, **kwargs):
    """
    Almacenar el estado anterior de la reserva antes de guardar
    """
    try:
        if instance.pk:  # Solo si la instancia ya existe
            previous_instance = sender.objects.get(pk=instance.pk)
            instance._previous_estado = previous_instance.estado
    except sender.DoesNotExist:
        instance._previous_estado = None


@receiver(post_save, sender='finances.Cargo')
def new_charge_assigned(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se crea un nuevo cargo
    """
    try:
        if created:
            logger.info(f"💰 Nuevo cargo creado: {instance.id} para {instance.propietario.user.username}")

            success = NotificationHelper.notify_new_charge(instance)

            if success:
                logger.info(f"📱 Notificación de nuevo cargo enviada para cargo {instance.id}")
            else:
                logger.error(f"❌ Error enviando notificación de nuevo cargo para cargo {instance.id}")

    except Exception as e:
        logger.error(f"❌ Error en señal de nuevo cargo: {e}")


# Función para recordatorios de reservas (se ejecutará con celery o cron)
def check_upcoming_reservations():
    """
    Verificar reservas que empiezan en 30 minutos y enviar recordatorios
    Esta función debe ser llamada por un task periódico
    """
    try:
        from areas_comunes.models import ReservaArea

        # Calcular el rango de tiempo (30 minutos desde ahora)
        now = timezone.now()
        reminder_time = now + timedelta(minutes=30)
        time_window = timedelta(minutes=5)  # Ventana de 5 minutos para evitar duplicados

        # Buscar reservas confirmadas que empiecen entre 25 y 35 minutos desde ahora
        upcoming_reservations = ReservaArea.objects.filter(
            estado='confirmada',
            fecha_inicio__gte=reminder_time - time_window,
            fecha_inicio__lte=reminder_time + time_window
        )

        logger.info(f"🔍 Verificando {upcoming_reservations.count()} reservas próximas...")

        for reservation in upcoming_reservations:
            try:
                # Verificar si ya se envió recordatorio para esta reserva
                from .models import Notification
                existing_reminder = Notification.objects.filter(
                    user=reservation.propietario.user,
                    notification_type='reservation_reminder',
                    data__entity_id=str(reservation.id),
                    status__in=['sent', 'pending']
                ).exists()

                if not existing_reminder:
                    success = NotificationHelper.notify_reservation_reminder(reservation)

                    if success:
                        logger.info(f"⏰ Recordatorio enviado para reserva {reservation.id}")
                    else:
                        logger.error(f"❌ Error enviando recordatorio para reserva {reservation.id}")
                else:
                    logger.info(f"⏭️ Recordatorio ya enviado para reserva {reservation.id}")

            except Exception as e:
                logger.error(f"❌ Error procesando recordatorio para reserva {reservation.id}: {e}")

    except Exception as e:
        logger.error(f"❌ Error verificando reservas próximas: {e}")


# Señal para infracciones (opcional)
@receiver(post_save, sender='finances.Infraccion')
def new_infraction_created(sender, instance, created, **kwargs):
    """
    Señal cuando se crea una nueva infracción
    """
    try:
        if created:
            logger.info(f"🚨 Nueva infracción creada: {instance.id}")
            # Aquí podrías enviar notificación de infracción si tienes esa plantilla

    except Exception as e:
        logger.error(f"❌ Error en señal de infracción: {e}")


# Señal para pagos vencidos (opcional)
def check_overdue_payments():
    """
    Verificar pagos vencidos y enviar notificaciones
    Esta función debe ser llamada por un task periódico
    """
    try:
        from finances.models import Cargo

        # Buscar cargos vencidos no pagados
        now = timezone.now().date()
        overdue_charges = Cargo.objects.filter(
            estado='pendiente',
            fecha_vencimiento__lt=now
        )

        logger.info(f"💸 Verificando {overdue_charges.count()} cargos vencidos...")

        for charge in overdue_charges:
            try:
                # Verificar si ya se envió notificación de vencimiento hoy
                from .models import Notification
                today_reminder = Notification.objects.filter(
                    user=charge.propietario.user,
                    notification_type='payment_due',
                    data__entity_id=str(charge.id),
                    created_at__date=now
                ).exists()

                if not today_reminder:
                    # Enviar notificación de pago vencido
                    context = {
                        'name': charge.propietario.user.get_full_name(),
                        'amount': f"{charge.monto} {charge.moneda}",
                        'description': charge.descripcion,
                        'due_date': charge.fecha_vencimiento.strftime('%d/%m/%Y'),
                        'entity_id': charge.id,
                    }

                    from .services import FirebaseService
                    success = FirebaseService.send_notification(
                        user=charge.propietario.user,
                        notification_type='payment_due',
                        context=context
                    )

                    if success:
                        logger.info(f"💳 Notificación de pago vencido enviada para cargo {charge.id}")
                    else:
                        logger.error(f"❌ Error enviando notificación de pago vencido para cargo {charge.id}")

            except Exception as e:
                logger.error(f"❌ Error procesando pago vencido para cargo {charge.id}: {e}")

    except Exception as e:
        logger.error(f"❌ Error verificando pagos vencidos: {e}")