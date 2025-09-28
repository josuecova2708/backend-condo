# Generated manually on 2025-09-28

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0012_add_en_revision_status'),
    ]

    operations = [
        migrations.RunSQL(
            # Drop the old constraint if it exists
            "ALTER TABLE cargos DROP CONSTRAINT IF EXISTS cargos_estado_check;",
            # Reverse: Add the old constraint back (this is for rollback)
            ""
        ),
        migrations.RunSQL(
            # Add the new constraint with en_revision included
            """
            ALTER TABLE cargos ADD CONSTRAINT cargos_estado_check
            CHECK (estado IN ('pendiente', 'parcialmente_pagado', 'pagado', 'vencido', 'cancelado', 'en_revision'));
            """,
            # Reverse: Drop the constraint
            "ALTER TABLE cargos DROP CONSTRAINT IF EXISTS cargos_estado_check;"
        ),
    ]