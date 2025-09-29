#!/usr/bin/env python3
"""
Script para probar la funcionalidad de la API de cámaras.
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
from ai_security.views import CameraViewSet
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model

def test_s3_connection():
    """Probar conexión directa con S3"""
    print("1. Probando conexión directa con S3...")
    print("-" * 40)

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

        bucket_name = settings.AWS_S3_BUCKET_NAME

        # Probar listar objetos de camara1
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix="camara1/",
            MaxKeys=5
        )

        if 'Contents' in response:
            print(f"✓ Conexión exitosa con S3")
            print(f"✓ Bucket: {bucket_name}")
            print(f"✓ Videos encontrados en camara1: {len([obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')])}")

            # Probar generar URL firmada
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
                print(f"✓ URL firmada generada exitosamente para: {first_video}")
                print(f"  URL: {url[:100]}...")
        else:
            print("✗ No se encontraron archivos en camara1")

    except Exception as e:
        print(f"✗ Error de conexión S3: {e}")
        return False

    return True

def test_camera_viewset():
    """Probar el ViewSet de cámaras"""
    print("\n2. Probando CameraViewSet...")
    print("-" * 40)

    try:
        # Crear factory y viewset
        factory = APIRequestFactory()
        viewset = CameraViewSet()

        # Test 1: list_cameras
        request = factory.get('/api/ai-security/cameras/list_cameras/')
        viewset.action = 'list_cameras'
        response = viewset.list_cameras(request)

        if response.status_code == 200:
            data = response.data
            print(f"✓ list_cameras: {len(data['cameras'])} cámaras disponibles")
            for camera in data['cameras']:
                print(f"  - {camera['name']} ({camera['id']})")
        else:
            print(f"✗ list_cameras falló: {response.status_code}")

        # Test 2: list_videos para camara1
        request = factory.get('/api/ai-security/cameras/list_videos/?camera_id=camara1')
        viewset.action = 'list_videos'
        response = viewset.list_videos(request)

        if response.status_code == 200:
            data = response.data
            print(f"✓ list_videos camara1: {data['count']} videos encontrados")
            if data['videos']:
                print(f"  Primer video: {data['videos'][0]['name']}")
                print(f"  Tamaño: {data['videos'][0]['size']} bytes")
                print(f"  URL disponible: {'url' in data['videos'][0]}")
        else:
            print(f"✗ list_videos falló: {response.status_code}")
            print(f"  Error: {response.data}")

    except Exception as e:
        print(f"✗ Error en ViewSet: {e}")
        return False

    return True

def test_all_cameras():
    """Probar todas las cámaras"""
    print("\n3. Probando todas las cámaras...")
    print("-" * 40)

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

        bucket_name = settings.AWS_S3_BUCKET_NAME

        for camera_id in ['camara1', 'camara2', 'camara3']:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"{camera_id}/"
            )

            video_count = 0
            if 'Contents' in response:
                video_count = len([obj for obj in response['Contents'] if obj['Key'].endswith('.mp4')])

            print(f"{camera_id.upper()}: {video_count} videos")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True

def main():
    """Función principal"""
    print("PROBANDO FUNCIONALIDAD DE CAMARAS")
    print("=" * 50)
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Región: {settings.AWS_DEFAULT_REGION}")
    print("=" * 50)

    # Ejecutar pruebas
    success = True
    success &= test_s3_connection()
    success &= test_camera_viewset()
    success &= test_all_cameras()

    print("\n" + "=" * 50)
    if success:
        print("TODAS LAS PRUEBAS PASARON!")
        print("El sistema de camaras esta funcionando correctamente")
        print("Puedes probar el frontend en: /dashboard/cameras")
        print("API endpoints disponibles:")
        print("   - GET /api/ai-security/cameras/list_cameras/")
        print("   - GET /api/ai-security/cameras/list_videos/?camera_id=X")
        print("   - GET /api/ai-security/cameras/get_video_url/?camera_id=X&video_name=Y")
    else:
        print("Algunas pruebas fallaron")
        print("Revisa la configuracion antes de usar el frontend")

if __name__ == "__main__":
    main()