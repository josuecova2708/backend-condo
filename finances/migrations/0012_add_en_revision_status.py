# Generated manually on 2025-09-28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0011_populate_monto_calculado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cargo',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('parcialmente_pagado', 'Parcialmente Pagado'),
                    ('pagado', 'Pagado'),
                    ('vencido', 'Vencido'),
                    ('cancelado', 'Cancelado'),
                    ('en_revision', 'En Revisión')
                ],
                default='pendiente',
                help_text='Estado actual del cargo',
                max_length=20
            ),
        ),
    ]