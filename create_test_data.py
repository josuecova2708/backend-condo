import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_condo_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.core.models import Condominio, Bloque
from apps.properties.models import UnidadHabitacional

User = get_user_model()

def create_test_data():
    # Crear un condominio de prueba si no existe
    condominio, created = Condominio.objects.get_or_create(
        nombre="Condominio San Miguel",
        defaults={
            'direccion': "Av. San Martin 123, Santa Cruz",
            'telefono': "3456789",
            'email': "admin@sanmiguel.com",
            'nit': "123456789",
            'is_active': True
        }
    )
    
    if created:
        print(f"Condominio creado: {condominio.nombre}")
    else:
        print(f"Condominio ya existe: {condominio.nombre}")
    
    # Crear bloques de prueba
    bloques_data = [
        {'nombre': 'Bloque A', 'descripcion': 'Primer bloque del condominio', 'numero_pisos': 10},
        {'nombre': 'Bloque B', 'descripcion': 'Segundo bloque del condominio', 'numero_pisos': 8},
        {'nombre': 'Bloque C', 'descripcion': 'Tercer bloque del condominio', 'numero_pisos': 12},
    ]
    
    bloques = []
    for bloque_data in bloques_data:
        bloque, created = Bloque.objects.get_or_create(
            nombre=bloque_data['nombre'],
            condominio=condominio,
            defaults={
                'descripcion': bloque_data['descripcion'],
                'numero_pisos': bloque_data['numero_pisos'],
                'is_active': True
            }
        )
        bloques.append(bloque)
        
        if created:
            print(f"Bloque creado: {bloque.nombre}")
        else:
            print(f"Bloque ya existe: {bloque.nombre}")
    
    # Crear unidades habitacionales de prueba
    unidades_data = [
        # Bloque A
        {'bloque': bloques[0], 'numero': '101', 'piso': 1, 'tipo': 'departamento', 'area_m2': 85.5, 'num_habitaciones': 2, 'num_banos': 1, 'tiene_balcon': True, 'tiene_parqueadero': False},
        {'bloque': bloques[0], 'numero': '102', 'piso': 1, 'tipo': 'departamento', 'area_m2': 95.0, 'num_habitaciones': 3, 'num_banos': 2, 'tiene_balcon': True, 'tiene_parqueadero': True},
        {'bloque': bloques[0], 'numero': '201', 'piso': 2, 'tipo': 'departamento', 'area_m2': 85.5, 'num_habitaciones': 2, 'num_banos': 1, 'tiene_balcon': True, 'tiene_parqueadero': False},
        {'bloque': bloques[0], 'numero': '301', 'piso': 3, 'tipo': 'departamento', 'area_m2': 110.0, 'num_habitaciones': 3, 'num_banos': 2, 'tiene_balcon': True, 'tiene_parqueadero': True},
        
        # Bloque B
        {'bloque': bloques[1], 'numero': '101', 'piso': 1, 'tipo': 'departamento', 'area_m2': 75.0, 'num_habitaciones': 2, 'num_banos': 1, 'tiene_balcon': False, 'tiene_parqueadero': True},
        {'bloque': bloques[1], 'numero': '102', 'piso': 1, 'tipo': 'departamento', 'area_m2': 80.0, 'num_habitaciones': 2, 'num_banos': 1, 'tiene_balcon': True, 'tiene_parqueadero': False},
        {'bloque': bloques[1], 'numero': '201', 'piso': 2, 'tipo': 'departamento', 'area_m2': 75.0, 'num_habitaciones': 2, 'num_banos': 1, 'tiene_balcon': False, 'tiene_parqueadero': True},
        
        # Bloque C
        {'bloque': bloques[2], 'numero': 'A-1', 'piso': 1, 'tipo': 'casa', 'area_m2': 150.0, 'num_habitaciones': 4, 'num_banos': 3, 'tiene_balcon': False, 'tiene_parqueadero': True},
        {'bloque': bloques[2], 'numero': 'B-1', 'piso': 1, 'tipo': 'casa', 'area_m2': 140.0, 'num_habitaciones': 3, 'num_banos': 2, 'tiene_balcon': True, 'tiene_parqueadero': True},
        {'bloque': bloques[2], 'numero': '101', 'piso': 1, 'tipo': 'oficina', 'area_m2': 60.0, 'num_habitaciones': 1, 'num_banos': 1, 'tiene_balcon': False, 'tiene_parqueadero': False},
    ]
    
    for unidad_data in unidades_data:
        unidad, created = UnidadHabitacional.objects.get_or_create(
            bloque=unidad_data['bloque'],
            numero=unidad_data['numero'],
            defaults={
                'piso': unidad_data['piso'],
                'tipo': unidad_data['tipo'],
                'area_m2': unidad_data['area_m2'],
                'num_habitaciones': unidad_data['num_habitaciones'],
                'num_banos': unidad_data['num_banos'],
                'tiene_balcon': unidad_data['tiene_balcon'],
                'tiene_parqueadero': unidad_data['tiene_parqueadero'],
                'observaciones': f"Unidad de prueba {unidad_data['numero']}",
                'is_active': True
            }
        )
        
        if created:
            print(f"Unidad creada: {unidad.numero} - {unidad.bloque.nombre}")
        else:
            print(f"Unidad ya existe: {unidad.numero} - {unidad.bloque.nombre}")

    print(f"\nResumen:")
    print(f"- Condominios: {Condominio.objects.count()}")
    print(f"- Bloques: {Bloque.objects.count()}")
    print(f"- Unidades: {UnidadHabitacional.objects.count()}")

if __name__ == '__main__':
    create_test_data()