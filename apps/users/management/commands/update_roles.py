from django.core.management.base import BaseCommand
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Actualizar roles del sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Actualizando roles del sistema...'))

        # Primero, eliminar todos los roles existentes
        Role.objects.all().delete()
        self.stdout.write(self.style.WARNING('[INFO] Roles anteriores eliminados'))

        # Crear los nuevos roles
        nuevos_roles = [
            {
                'nombre': 'Administrador',
                'descripcion': 'Administrador del condominio con acceso completo al sistema'
            },
            {
                'nombre': 'Propietario',
                'descripcion': 'Propietario de una unidad habitacional'
            },
            {
                'nombre': 'Inquilino',
                'descripcion': 'Inquilino o arrendatario de una unidad habitacional'
            },
            {
                'nombre': 'Seguridad',
                'descripcion': 'Personal de seguridad y portería'
            }
        ]

        for role_data in nuevos_roles:
            role = Role.objects.create(
                nombre=role_data['nombre'],
                descripcion=role_data['descripcion'],
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'[OK] Rol creado: {role.nombre}'))

        self.stdout.write(self.style.SUCCESS('[SUCCESS] Roles actualizados exitosamente!'))
        self.stdout.write(self.style.SUCCESS(f'[INFO] Total de roles: {Role.objects.count()}'))
        
        # Mostrar todos los roles
        for role in Role.objects.all():
            self.stdout.write(self.style.SUCCESS(f'  - {role.nombre}: {role.descripcion}'))