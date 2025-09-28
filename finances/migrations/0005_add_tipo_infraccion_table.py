# Manual migration to add TipoInfraccion table
from django.db import migrations, models
from decimal import Decimal
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0004_update_cargo_tipo_choices'),
    ]

    operations = [
        # Create the tipos_infraccion table manually
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS tipos_infraccion (
                id BIGSERIAL PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT DEFAULT '',
                monto_base NUMERIC(10, 2) NOT NULL CHECK (monto_base >= 0.00),
                monto_reincidencia NUMERIC(10, 2) NOT NULL CHECK (monto_reincidencia >= 0.00),
                dias_para_pago INTEGER DEFAULT 15 NOT NULL CHECK (dias_para_pago >= 0),
                es_activo BOOLEAN DEFAULT true NOT NULL,
                orden INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );

            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS tipos_infraccion_codigo_idx ON tipos_infraccion(codigo);
            CREATE INDEX IF NOT EXISTS tipos_infraccion_activo_idx ON tipos_infraccion(es_activo);
            CREATE INDEX IF NOT EXISTS tipos_infraccion_orden_idx ON tipos_infraccion(orden);
            """,
            reverse_sql="DROP TABLE IF EXISTS tipos_infraccion CASCADE;"
        ),
    ]