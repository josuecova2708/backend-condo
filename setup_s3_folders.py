#!/usr/bin/env python3
"""
Script para crear solo las carpetas en el bucket S3 (sin políticas públicas).
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django para acceder a settings
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_condo_project.settings')
django.setup()

import boto3
from django.conf import settings
from botocore.exceptions import ClientError

def create_folders():
    """Crear las carpetas necesarias en el bucket"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME
    folders = ['camara1/', 'camara2/', 'camara3/', 'FotosPerfil/']

    for folder in folders:
        try:
            # Crear un objeto vacío para representar la carpeta
            s3_client.put_object(
                Bucket=bucket_name,
                Key=folder,
                Body=b''
            )
            print(f"Carpeta '{folder}' creada.")

        except ClientError as e:
            print(f"Error al crear carpeta '{folder}': {e}")
            return False

    return True

def configure_cors():
    """Configurar CORS del bucket"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME

    try:
        # Configurar CORS
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedOrigins': ['*'],
                    'AllowedMethods': ['GET', 'HEAD'],
                    'AllowedHeaders': ['*'],
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }

        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print(f"Configuracion CORS aplicada para '{bucket_name}'.")
        return True

    except ClientError as e:
        print(f"Error configurando CORS: {e}")
        return False

def main():
    """Función principal"""
    print("Configurando carpetas y CORS en bucket S3...")
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")
    print("-" * 50)

    # Crear carpetas
    if not create_folders():
        print("Error al crear las carpetas.")
        return

    # Configurar CORS
    if not configure_cors():
        print("Error al configurar CORS.")
        return

    print("-" * 50)
    print("Configuracion completada exitosamente!")
    print("\nEstructura creada:")
    print(f"  {settings.AWS_S3_BUCKET_NAME}/")
    print("    camara1/")
    print("    camara2/")
    print("    camara3/")
    print("    FotosPerfil/")

    print(f"\nURL del bucket: https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_DEFAULT_REGION}.amazonaws.com/")

    print("\nNOTA: El bucket usa URLs firmadas (presigned URLs) para acceso seguro.")
    print("No necesita ser publico para funcionar con la aplicacion.")

if __name__ == "__main__":
    main()