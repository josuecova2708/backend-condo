#!/usr/bin/env python3
"""
Script para crear el bucket S3 y las carpetas necesarias para el proyecto de cámaras.
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

def create_s3_bucket():
    """Crear el bucket S3 si no existe"""

    # Configurar cliente S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME
    region = settings.AWS_DEFAULT_REGION

    try:
        # Verificar si el bucket ya existe
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"El bucket '{bucket_name}' ya existe.")

    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            # El bucket no existe, crearlo
            try:
                if region == 'us-east-1':
                    # Para us-east-1, no se especifica LocationConstraint
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    # Para otras regiones, se especifica LocationConstraint
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )

                print(f"Bucket '{bucket_name}' creado exitosamente.")

                # Configurar el bucket como público
                bucket_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{bucket_name}/*"
                        }
                    ]
                }

                s3_client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=str(bucket_policy).replace("'", '"')
                )
                print(f"Politica de acceso publico configurada para '{bucket_name}'.")

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

            except ClientError as create_error:
                print(f"Error al crear el bucket: {create_error}")
                return False
        else:
            print(f"Error al verificar el bucket: {e}")
            return False

    return True

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

def main():
    """Función principal"""
    print("Configurando bucket S3 para el proyecto de camaras...")
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")
    print("-" * 50)

    # Crear bucket
    if not create_s3_bucket():
        print("Error en la configuracion del bucket.")
        return

    # Crear carpetas
    if not create_folders():
        print("Error al crear las carpetas.")
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

if __name__ == "__main__":
    main()