import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_condo_project.settings')
django.setup()

from apps.core.models import Condominio, Bloque
from apps.users.models import Role, User

def check_data():
    print("=== Verificando datos ===")
    
    # Verificar condominios
    condominios = Condominio.objects.all()
    print(f"Condominios: {condominios.count()}")
    for c in condominios:
        print(f"  - {c.id}: {c.nombre} (activo: {c.is_active})")
    
    # Verificar roles
    roles = Role.objects.all()
    print(f"\nRoles: {roles.count()}")
    for r in roles:
        print(f"  - {r.id}: {r.nombre} (activo: {r.is_active})")
    
    # Crear roles básicos si no existen
    if roles.count() == 0:
        print("\nCreando roles básicos...")
        roles_to_create = [
            {'nombre': 'Administrador', 'descripcion': 'Administrador del sistema'},
            {'nombre': 'Propietario', 'descripcion': 'Propietario de unidad habitacional'},
            {'nombre': 'Residente', 'descripcion': 'Residente del condominio'},
            {'nombre': 'Conserje', 'descripcion': 'Personal de conserjería'},
        ]
        
        for role_data in roles_to_create:
            role = Role.objects.create(
                nombre=role_data['nombre'],
                descripcion=role_data['descripcion'],
                is_active=True
            )
            print(f"  Creado: {role.nombre}")
    
    # Verificar bloques
    bloques = Bloque.objects.all()
    print(f"\nBloques: {bloques.count()}")
    for b in bloques:
        print(f"  - {b.id}: {b.nombre} - {b.condominio.nombre} (activo: {b.is_active})")

if __name__ == '__main__':
    check_data()