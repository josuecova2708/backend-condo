#!/usr/bin/env python3
"""
Script para intentar crear bucket S3 con nombre alternativo.
"""

import os
import sys
import django
from pathlib import Path
import uuid

# Configurar Django para acceder a settings
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_condo_project.settings')
django.setup()

import boto3
from django.conf import settings
from botocore.exceptions import ClientError

def try_create_bucket_with_alternative_name():
    """Intentar crear bucket con nombre alternativo"""

    # Configurar cliente S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    # Generar algunos nombres alternativos
    base_names = [
        'si2-examen-parcial-2024',
        'si2-examenparcial',
        'condo-cameras-si2',
        f'si2-cameras-{uuid.uuid4().hex[:8]}'
    ]

    for bucket_name in base_names:
        try:
            print(f"Intentando crear bucket: {bucket_name}")

            # Crear bucket en us-east-1
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' creado exitosamente!")

            # Crear carpetas
            folders = ['camara1/', 'camara2/', 'camara3/', 'FotosPerfil/']
            for folder in folders:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=folder,
                    Body=b''
                )
                print(f"Carpeta '{folder}' creada.")

            print(f"\nEXITO! Usa este nombre de bucket en tu configuracion:")
            print(f"AWS_S3_BUCKET_NAME={bucket_name}")

            return bucket_name

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyExists':
                print(f"  - El bucket '{bucket_name}' ya existe (pertenece a otra cuenta)")
            elif error_code == 'AccessDenied':
                print(f"  - Acceso denegado para '{bucket_name}'")
            else:
                print(f"  - Error: {e}")
            continue

    print("\nNo se pudo crear ningun bucket. Necesitas crearlo manualmente desde la consola.")
    return None

def main():
    """Función principal"""
    print("Intentando crear bucket S3 con nombres alternativos...")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")
    print("-" * 50)

    try_create_bucket_with_alternative_name()

if __name__ == "__main__":
    main()