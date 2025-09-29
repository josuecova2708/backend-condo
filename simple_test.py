#!/usr/bin/env python3
"""
Test simple de la funcionalidad de camaras.
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

def test_s3_basic():
    """Test basico de S3"""
    print("Probando S3...")

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

        bucket_name = settings.AWS_S3_BUCKET_NAME

        # Contar videos en cada camara
        for camera in ['camara1', 'camara2', 'camara3']:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"{camera}/"
            )

            video_count = 0
            if 'Contents' in response:
                video_count = len([obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')])

            print(f"{camera}: {video_count} videos")

            # Probar URL firmada para el primer video
            if video_count > 0:
                first_video = None
                for obj in response['Contents']:
                    if obj['Key'].endswith('.mp4'):
                        first_video = obj['Key']
                        break

                if first_video:
                    url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket_name, 'Key': first_video},
                        ExpiresIn=3600
                    )
                    print(f"  URL generada para: {first_video.split('/')[-1]}")

        print("\nPrueba S3 EXITOSA")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("="*50)
    print("TEST SIMPLE - FUNCIONALIDAD DE CAMARAS")
    print("="*50)
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")
    print("-"*50)

    if test_s3_basic():
        print("\n" + "="*50)
        print("TODAS LAS PRUEBAS PASARON!")
        print("El sistema de camaras funciona correctamente")
        print("Puedes probar el frontend en: /dashboard/cameras")
        print("="*50)
    else:
        print("\nERROR en las pruebas")

if __name__ == "__main__":
    main()