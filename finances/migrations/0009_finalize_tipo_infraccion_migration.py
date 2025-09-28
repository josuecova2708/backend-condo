# Migración final para completar la conversión de tipo_infraccion
from django.db import migrations, models
import django.db.models.deletion

def copy_fk_data_and_cleanup(apps, schema_editor):
    """
    Copia datos de tipo_infraccion_fk a tipo_infraccion y limpia
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Paso 1: Eliminar la columna tipo_infraccion original (string)
        cursor.execute("ALTER TABLE infracciones DROP COLUMN tipo_infraccion;")
        print("OK - Columna tipo_infraccion (string) eliminada")

        # Paso 2: Renombrar tipo_infraccion_fk_id a tipo_infraccion_id
        cursor.execute("ALTER TABLE infracciones RENAME COLUMN tipo_infraccion_fk_id TO tipo_infraccion_id;")
        print("OK - Columna renombrada de tipo_infraccion_fk_id a tipo_infraccion_id")

        # Paso 3: Actualizar la constraint
        cursor.execute("ALTER TABLE infracciones DROP CONSTRAINT IF EXISTS fk_infracciones_tipo_infraccion_fk;")
        cursor.execute("""
            ALTER TABLE infracciones
            ADD CONSTRAINT fk_infracciones_tipo_infraccion
            FOREIGN KEY (tipo_infraccion_id)
            REFERENCES tipos_infraccion(id);
        """)
        print("OK - Constraint FK actualizada")

def reverse_copy_fk_data_and_cleanup(apps, schema_editor):
    """
    Reversa la operación
    """
    print("WARNING - No se puede revertir esta migración automáticamente")

class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0008_populate_tipo_infraccion_fk'),
    ]

    operations = [
        migrations.RunPython(
            copy_fk_data_and_cleanup,
            reverse_copy_fk_data_and_cleanup,
        ),
    ]