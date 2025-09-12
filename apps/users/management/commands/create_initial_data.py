from django.core.management.base import BaseCommand
from apps.users.models import Role, Permission, RolePermission
from apps.core.models import Condominio


class Command(BaseCommand):
    help = 'Crear datos iniciales para roles, permisos y condominio'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando creación de datos iniciales...'))

        # Crear roles básicos
        roles_data = [
            {
                'nombre': 'Administrador',
                'descripcion': 'Administrador del sistema con acceso completo'
            },
            {
                'nombre': 'Portero',
                'descripcion': 'Personal de portería con acceso limitado'
            },
            {
                'nombre': 'Propietario',
                'descripcion': 'Propietario de una unidad habitacional'
            },
            {
                'nombre': 'Residente',
                'descripcion': 'Residente autorizado en una unidad habitacional'
            },
            {
                'nombre': 'Conserje',
                'descripcion': 'Personal de mantenimiento y servicios generales'
            }
        ]

        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                nombre=role_data['nombre'],
                defaults={
                    'descripcion': role_data['descripcion'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'[OK] Rol creado: {role.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'[INFO] Rol ya existe: {role.nombre}'))

        # Crear permisos básicos
        permisos_data = [
            {'nombre': 'Ver usuarios', 'codigo': 'view_users', 'descripcion': 'Puede ver lista de usuarios', 'modulo': 'usuarios'},
            {'nombre': 'Crear usuarios', 'codigo': 'create_users', 'descripcion': 'Puede crear nuevos usuarios', 'modulo': 'usuarios'},
            {'nombre': 'Editar usuarios', 'codigo': 'edit_users', 'descripcion': 'Puede editar usuarios existentes', 'modulo': 'usuarios'},
            {'nombre': 'Eliminar usuarios', 'codigo': 'delete_users', 'descripcion': 'Puede eliminar usuarios', 'modulo': 'usuarios'},
            
            {'nombre': 'Ver propiedades', 'codigo': 'view_properties', 'descripcion': 'Puede ver propiedades', 'modulo': 'propiedades'},
            {'nombre': 'Gestionar propiedades', 'codigo': 'manage_properties', 'descripcion': 'Puede gestionar propiedades', 'modulo': 'propiedades'},
            
            {'nombre': 'Ver comunicaciones', 'codigo': 'view_communications', 'descripcion': 'Puede ver comunicaciones', 'modulo': 'comunicaciones'},
            {'nombre': 'Crear comunicaciones', 'codigo': 'create_communications', 'descripcion': 'Puede crear comunicaciones', 'modulo': 'comunicaciones'},
            
            {'nombre': 'Administrar sistema', 'codigo': 'admin_system', 'descripcion': 'Acceso administrativo completo', 'modulo': 'sistema'},
        ]

        for permiso_data in permisos_data:
            permiso, created = Permission.objects.get_or_create(
                codigo=permiso_data['codigo'],
                defaults={
                    'nombre': permiso_data['nombre'],
                    'descripcion': permiso_data['descripcion'],
                    'modulo': permiso_data['modulo']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'[OK] Permiso creado: {permiso.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'[INFO] Permiso ya existe: {permiso.nombre}'))

        # Asignar permisos a roles
        try:
            admin_role = Role.objects.get(nombre='Administrador')
            all_permissions = Permission.objects.all()
            
            for permission in all_permissions:
                role_permission, created = RolePermission.objects.get_or_create(
                    role=admin_role,
                    permission=permission
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'[OK] Permiso {permission.nombre} asignado a Administrador'))

            # Asignar algunos permisos básicos a otros roles
            propietario_role = Role.objects.get(nombre='Propietario')
            basic_permissions = Permission.objects.filter(codigo__in=['view_communications', 'view_properties'])
            
            for permission in basic_permissions:
                RolePermission.objects.get_or_create(
                    role=propietario_role,
                    permission=permission
                )

        except Role.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error asignando permisos: {e}'))

        self.stdout.write(self.style.SUCCESS('[SUCCESS] Datos iniciales creados exitosamente!'))
        self.stdout.write(self.style.SUCCESS(f'[INFO] Roles creados: {Role.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'[INFO] Permisos creados: {Permission.objects.count()}'))