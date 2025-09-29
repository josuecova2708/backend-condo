#!/usr/bin/env python3
"""
Script para verificar si el bucket S3 existe y sus contenidos.
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

def check_bucket_exists():
    """Verificar si el bucket S3 existe"""

    # Configurar cliente S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME

    try:
        # Verificar si el bucket existe
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"El bucket '{bucket_name}' existe.")
        return True

    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            print(f"El bucket '{bucket_name}' NO existe.")
            return False
        else:
            print(f"Error al verificar el bucket: {e}")
            return False

def list_bucket_contents():
    """Listar contenidos del bucket"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME

    try:
        # Listar todos los objetos
        response = s3_client.list_objects_v2(Bucket=bucket_name)

        if 'Contents' in response:
            print(f"\nContenidos del bucket '{bucket_name}':")
            print("-" * 50)
            for obj in response['Contents']:
                print(f"  {obj['Key']} ({obj['Size']} bytes, {obj['LastModified']})")
        else:
            print(f"\nEl bucket '{bucket_name}' esta vacio.")

    except ClientError as e:
        print(f"Error listando contenidos: {e}")

def main():
    """Función principal"""
    print("Verificando bucket S3...")
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")
    print("-" * 50)

    if check_bucket_exists():
        list_bucket_contents()
    else:
        print("\nEl bucket no existe. Necesitas crearlo manualmente o con permisos adecuados.")

if __name__ == "__main__":
    main()