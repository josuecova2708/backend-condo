# Generated manually to add monto_calculado field

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0009_finalize_tipo_infraccion_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='infraccion',
            name='monto_calculado',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Monto calculado automáticamente según el tipo de infracción y reincidencia',
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]
            ),
        ),
    ]