# Migration to populate monto_calculado for existing infracciones

from django.db import migrations


def populate_monto_calculado(apps, schema_editor):
    """Populate monto_calculado field for existing infracciones"""
    Infraccion = apps.get_model('finances', 'Infraccion')
    TipoInfraccion = apps.get_model('finances', 'TipoInfraccion')

    # Use raw SQL to handle the column name issue
    from django.db import connection

    with connection.cursor() as cursor:
        # Check if infracciones table has any data and what columns exist
        cursor.execute("SELECT COUNT(*) FROM infracciones")
        count = cursor.fetchone()[0]

        if count > 0:
            # Try to update existing records using the actual column name
            try:
                cursor.execute("""
                    UPDATE infracciones
                    SET monto_calculado = CASE
                        WHEN es_reincidente THEN ti.monto_reincidencia
                        ELSE ti.monto_base
                    END
                    FROM tipos_infraccion ti
                    WHERE infracciones.tipo_infraccion_id = ti.id
                    AND monto_calculado IS NULL
                """)
            except Exception as e:
                # If the above fails, try using Django ORM with select_related
                for infraccion in Infraccion.objects.select_related('tipo_infraccion').all():
                    if hasattr(infraccion, 'tipo_infraccion_id') and infraccion.tipo_infraccion_id and not infraccion.monto_calculado:
                        try:
                            tipo = TipoInfraccion.objects.get(id=infraccion.tipo_infraccion_id)
                            if infraccion.es_reincidente:
                                infraccion.monto_calculado = tipo.monto_reincidencia
                            else:
                                infraccion.monto_calculado = tipo.monto_base
                            infraccion.save()
                        except TipoInfraccion.DoesNotExist:
                            continue


def reverse_populate_monto_calculado(apps, schema_editor):
    """Reverse operation - clear monto_calculado field"""
    Infraccion = apps.get_model('finances', 'Infraccion')
    Infraccion.objects.update(monto_calculado=None)


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0010_add_monto_calculado'),
    ]

    operations = [
        migrations.RunPython(
            populate_monto_calculado,
            reverse_populate_monto_calculado,
        ),
    ]