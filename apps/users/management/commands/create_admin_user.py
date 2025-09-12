from django.core.management.base import BaseCommand
from apps.users.models import User, Role
from apps.core.models import Condominio


class Command(BaseCommand):
    help = 'Crear usuario administrador con rol correcto'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creando usuario administrador...'))

        try:
            # Obtener el rol de Administrador
            admin_role = Role.objects.get(nombre='Administrador')
            self.stdout.write(self.style.SUCCESS(f'[OK] Rol encontrado: {admin_role.nombre}'))

            # Obtener o crear un condominio por defecto
            condominio, created = Condominio.objects.get_or_create(
                nombre='Condominio Principal',
                defaults={
                    'direccion': 'Dirección Principal',
                    'nit': '987654321',
                    'telefono': '123456789',
                    'email': 'admin@condominio.com',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'[OK] Condominio creado: {condominio.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'[INFO] Condominio ya existe: {condominio.nombre}'))

            # Verificar si ya existe el usuario admin
            username = 'admin'
            if User.objects.filter(username=username).exists():
                # Actualizar usuario existente
                admin_user = User.objects.get(username=username)
                admin_user.role = admin_role
                admin_user.condominio = condominio
                admin_user.is_active = True
                admin_user.save()
                self.stdout.write(self.style.WARNING(f'[INFO] Usuario admin actualizado con rol: {admin_role.nombre}'))
            else:
                # Crear nuevo usuario admin
                admin_user = User.objects.create_user(
                    username=username,
                    email='admin@condominio.com',
                    password='admin123',  # Cambiar en producción
                    first_name='Administrador',
                    last_name='Sistema',
                    role=admin_role,
                    condominio=condominio,
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
                self.stdout.write(self.style.SUCCESS(f'[OK] Usuario admin creado: {admin_user.username}'))

            self.stdout.write(self.style.SUCCESS('[SUCCESS] Usuario administrador configurado!'))
            self.stdout.write(self.style.SUCCESS('Credenciales:'))
            self.stdout.write(self.style.SUCCESS('  Username: admin'))
            self.stdout.write(self.style.SUCCESS('  Password: admin123'))
            self.stdout.write(self.style.SUCCESS(f'  Rol: {admin_user.role.nombre if admin_user.role else "Sin rol"}'))

        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('[ERROR] Rol "Administrador" no encontrado'))
            self.stdout.write(self.style.ERROR('Ejecuta primero: python manage.py update_roles'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error creando usuario: {e}'))