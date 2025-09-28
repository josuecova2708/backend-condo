# Data migration to populate TipoInfraccion with initial data
from django.db import migrations
from decimal import Decimal


def populate_tipos_infraccion(apps, schema_editor):
    """
    Populate the tipos_infraccion table with initial data
    """
    db_alias = schema_editor.connection.alias

    # Insert initial infraction types based on common condominium infractions
    # These are based on the user's existing data and common infractions
    tipos_data = [
        {
            'codigo': 'ruido_excesivo',
            'nombre': 'Ruido Excesivo',
            'descripcion': 'Generación de ruidos molestos que perturban la tranquilidad del condominio',
            'monto_base': Decimal('100.00'),
            'monto_reincidencia': Decimal('200.00'),
            'dias_para_pago': 15,
            'orden': 1
        },
        {
            'codigo': 'mascotas_no_autorizadas',
            'nombre': 'Mascotas No Autorizadas',
            'descripcion': 'Tener mascotas sin autorización o sin cumplir con las normas establecidas',
            'monto_base': Decimal('150.00'),
            'monto_reincidencia': Decimal('300.00'),
            'dias_para_pago': 15,
            'orden': 2
        },
        {
            'codigo': 'uso_inadecuado_areas_comunes',
            'nombre': 'Uso Inadecuado de Áreas Comunes',
            'descripcion': 'Uso indebido de espacios comunes del condominio',
            'monto_base': Decimal('80.00'),
            'monto_reincidencia': Decimal('160.00'),
            'dias_para_pago': 15,
            'orden': 3
        },
        {
            'codigo': 'estacionamiento_indebido',
            'nombre': 'Estacionamiento Indebido',
            'descripcion': 'Estacionar en lugares no autorizados o impedir el paso',
            'monto_base': Decimal('50.00'),
            'monto_reincidencia': Decimal('100.00'),
            'dias_para_pago': 10,
            'orden': 4
        },
        {
            'codigo': 'alteracion_fachada',
            'nombre': 'Alteración de Fachada',
            'descripcion': 'Modificaciones no autorizadas en la fachada del edificio',
            'monto_base': Decimal('200.00'),
            'monto_reincidencia': Decimal('400.00'),
            'dias_para_pago': 30,
            'orden': 5
        },
        {
            'codigo': 'otros',
            'nombre': 'Otros',
            'descripcion': 'Otras infracciones no categorizadas específicamente',
            'monto_base': Decimal('75.00'),
            'monto_reincidencia': Decimal('150.00'),
            'dias_para_pago': 15,
            'orden': 10
        }
    ]

    # Insert data using raw SQL to avoid model dependencies
    for tipo in tipos_data:
        schema_editor.execute(
            """
            INSERT INTO tipos_infraccion
            (codigo, nombre, descripcion, monto_base, monto_reincidencia, dias_para_pago, es_activo, orden, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (codigo) DO NOTHING;
            """,
            [
                tipo['codigo'],
                tipo['nombre'],
                tipo['descripcion'],
                tipo['monto_base'],
                tipo['monto_reincidencia'],
                tipo['dias_para_pago'],
                True,  # es_activo
                tipo['orden']
            ]
        )


def reverse_populate_tipos_infraccion(apps, schema_editor):
    """
    Remove the populated data
    """
    schema_editor.execute("DELETE FROM tipos_infraccion;")


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0005_add_tipo_infraccion_table'),
    ]

    operations = [
        migrations.RunPython(
            populate_tipos_infraccion,
            reverse_populate_tipos_infraccion
        ),
    ]