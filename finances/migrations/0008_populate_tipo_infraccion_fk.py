# Migración de datos para poblar tipo_infraccion_fk
from django.db import migrations

def populate_tipo_infraccion_fk(apps, schema_editor):
    """
    Popula el campo tipo_infraccion_fk basado en los valores string de tipo_infraccion
    """
    Infraccion = apps.get_model('finances', 'Infraccion')
    TipoInfraccion = apps.get_model('finances', 'TipoInfraccion')

    # Mapeo de valores string/ID a códigos de TipoInfraccion
    mapeo = {
        'ruido_excesivo': 'ruido_excesivo',
        'uso_inadecuado_areas': 'uso_inadecuado_areas_comunes',
        'mascotas_no_autorizadas': 'mascotas_no_autorizadas',
        'estacionamiento_indebido': 'estacionamiento_indebido',
        'alteracion_fachada': 'alteracion_fachada',
        'otros': 'otros',
        # Mapeo de IDs numéricos a códigos
        '1': 'ruido_excesivo',
        '2': 'mascotas_no_autorizadas',
        '3': 'uso_inadecuado_areas_comunes',
        '4': 'estacionamiento_indebido',
        '5': 'alteracion_fachada',
        '6': 'otros',
    }

    actualizadas = 0
    errores = 0

    for infraccion in Infraccion.objects.all():
        valor_actual = str(infraccion.tipo_infraccion)
        codigo_objetivo = mapeo.get(valor_actual)

        if codigo_objetivo:
            try:
                tipo_obj = TipoInfraccion.objects.get(codigo=codigo_objetivo)
                infraccion.tipo_infraccion_fk = tipo_obj
                infraccion.save()
                actualizadas += 1
                print(f"OK Infraccion {infraccion.id}: '{valor_actual}' -> {tipo_obj.nombre}")
            except TipoInfraccion.DoesNotExist:
                print(f"ERROR: No existe TipoInfraccion con codigo '{codigo_objetivo}'")
                errores += 1
        else:
            print(f"ERROR: No se puede mapear '{valor_actual}' para Infraccion {infraccion.id}")
            errores += 1

    print(f"Resumen: {actualizadas} infracciones actualizadas, {errores} errores")

def reverse_populate_tipo_infraccion_fk(apps, schema_editor):
    """
    Reversa la operación limpiando tipo_infraccion_fk
    """
    Infraccion = apps.get_model('finances', 'Infraccion')
    Infraccion.objects.all().update(tipo_infraccion_fk=None)

class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0007_tipoinfraccion_delete_configuracionmultas_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_tipo_infraccion_fk,
            reverse_populate_tipo_infraccion_fk,
        ),
    ]