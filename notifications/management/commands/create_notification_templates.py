from django.core.management.base import BaseCommand
from notifications.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create initial notification templates'

    def handle(self, *args, **options):
        """
        Crear plantillas de notificaciones iniciales
        """
        templates = [
            {
                'notification_type': 'reservation_confirmed',
                'title_template': 'Reserva Confirmada',
                'body_template': 'Hola {name}, tu reserva del {area_name} para el {date} ha sido confirmada. ¡Disfruta!'
            },
            {
                'notification_type': 'reservation_reminder',
                'title_template': 'Recordatorio de Reserva',
                'body_template': 'Hola {name}, tu reserva del {area_name} comienza en 30 minutos. No olvides asistir.'
            },
            {
                'notification_type': 'new_charge',
                'title_template': 'Nuevo Cargo',
                'body_template': 'Hola {name}, se te ha asignado un nuevo cargo: {description} por {amount}. Vence el {due_date}.'
            },
            {
                'notification_type': 'payment_due',
                'title_template': 'Pago Vencido',
                'body_template': 'Hola {name}, tienes un pago vencido: {description} por {amount}. Vencía el {due_date}.'
            },
            {
                'notification_type': 'maintenance_request',
                'title_template': 'Solicitud de Mantenimiento',
                'body_template': 'Hola {name}, se ha creado una nueva solicitud de mantenimiento: {description}.'
            },
            {
                'notification_type': 'general_announcement',
                'title_template': 'Anuncio General',
                'body_template': 'Hola {name}, {message}'
            }
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                notification_type=template_data['notification_type'],
                defaults={
                    'title_template': template_data['title_template'],
                    'body_template': template_data['body_template'],
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Plantilla creada: {template_data["notification_type"]}'
                    )
                )
            else:
                # Actualizar si ya existe pero con diferentes valores
                if (template.title_template != template_data['title_template'] or
                    template.body_template != template_data['body_template']):
                    template.title_template = template_data['title_template']
                    template.body_template = template_data['body_template']
                    template.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Plantilla actualizada: {template_data["notification_type"]}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Plantilla ya existe: {template_data["notification_type"]}'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nResumen: {created_count} creadas, {updated_count} actualizadas'
            )
        )