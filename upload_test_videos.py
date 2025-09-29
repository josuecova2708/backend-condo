#!/usr/bin/env python3
"""
Script para subir videos de prueba al bucket S3.
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

def create_dummy_video_file(filename, size_mb=1):
    """Crear un archivo de video dummy para pruebas"""
    # Crear archivo dummy con datos aleatorios
    dummy_data = b'0' * (size_mb * 1024 * 1024)  # size_mb MB de datos

    with open(filename, 'wb') as f:
        f.write(dummy_data)

    print(f"Archivo dummy creado: {filename} ({size_mb}MB)")

def upload_test_videos():
    """Subir videos de prueba a cada carpeta de cámara"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME

    # Definir videos de prueba para cada cámara
    test_videos = {
        'camara1': [
            'entrada_principal_001.mp4',
            'entrada_principal_002.mp4',
            'acceso_vehicular_001.mp4'
        ],
        'camara2': [
            'garaje_entrada_001.mp4',
            'garaje_salida_002.mp4',
            'parqueadero_003.mp4'
        ],
        'camara3': [
            'area_comun_001.mp4',
            'piscina_002.mp4',
            'salon_social_003.mp4'
        ]
    }

    temp_dir = Path('./temp_videos')
    temp_dir.mkdir(exist_ok=True)

    try:
        for camera_id, video_files in test_videos.items():
            print(f"\nSubiendo videos para {camera_id}:")
            print("-" * 30)

            for video_file in video_files:
                # Crear archivo dummy
                local_file = temp_dir / video_file
                create_dummy_video_file(local_file, size_mb=2)  # 2MB cada video

                # Subir a S3
                s3_key = f"{camera_id}/{video_file}"

                try:
                    s3_client.upload_file(
                        str(local_file),
                        bucket_name,
                        s3_key,
                        ExtraArgs={
                            'ContentType': 'video/mp4',
                            'Metadata': {
                                'camera': camera_id,
                                'original_name': video_file
                            }
                        }
                    )
                    print(f"  ✓ {video_file} subido exitosamente")

                except ClientError as e:
                    print(f"  ✗ Error subiendo {video_file}: {e}")

        print(f"\n{'='*50}")
        print("Videos de prueba subidos exitosamente!")
        print(f"{'='*50}")

    finally:
        # Limpiar archivos temporales
        if temp_dir.exists():
            for file in temp_dir.iterdir():
                file.unlink()
            temp_dir.rmdir()
            print("\nArchivos temporales eliminados.")

def list_uploaded_videos():
    """Listar videos subidos para verificación"""

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    bucket_name = settings.AWS_S3_BUCKET_NAME

    print(f"\nVideos en el bucket '{bucket_name}':")
    print("="*60)

    for camera in ['camara1', 'camara2', 'camara3']:
        print(f"\n📹 {camera.upper()}:")

        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=f"{camera}/"
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'] != f"{camera}/" and obj['Key'].endswith('.mp4'):
                        size_mb = obj['Size'] / (1024 * 1024)
                        print(f"  • {obj['Key']} ({size_mb:.1f}MB)")
            else:
                print(f"  (Sin videos)")

        except ClientError as e:
            print(f"  Error: {e}")

def main():
    """Función principal"""
    print("Subiendo videos de prueba al bucket S3...")
    print(f"Bucket: {settings.AWS_S3_BUCKET_NAME}")
    print(f"Region: {settings.AWS_DEFAULT_REGION}")

    # Subir videos de prueba
    upload_test_videos()

    # Verificar que se subieron correctamente
    list_uploaded_videos()

    print(f"\n🎉 ¡Todo listo! Ahora puedes probar la funcionalidad de cámaras en el frontend.")
    print(f"URL: /dashboard/cameras")

if __name__ == "__main__":
    main()