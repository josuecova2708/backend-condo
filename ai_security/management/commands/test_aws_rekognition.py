from django.core.management.base import BaseCommand
from ai_security.services.aws_facial_recognition import AWSFacialRecognitionService
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = 'Prueba la conexión con AWS Rekognition y crea la collection si es necesario'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Probando conexion con AWS Rekognition...')

            # Probar conexión básica usando credenciales por defecto
            rekognition = boto3.client('rekognition', region_name='us-east-1')

            # Probar que podemos hacer una llamada simple
            response = rekognition.list_collections()
            self.stdout.write(f'Conexion exitosa con AWS Rekognition')
            self.stdout.write(f'Collections existentes: {response.get("CollectionIds", [])}')

            # Intentar crear/verificar nuestra collection
            collection_id = 'smart-condominium-faces'

            try:
                # Intentar describir la collection
                collection_info = rekognition.describe_collection(CollectionId=collection_id)
                self.stdout.write(f'Collection "{collection_id}" ya existe')
                self.stdout.write(f'   Caras indexadas: {collection_info["FaceCount"]}')
                self.stdout.write(f'   Modelo version: {collection_info["FaceModelVersion"]}')

            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # La collection no existe, crearla
                    self.stdout.write(f'Collection "{collection_id}" no existe, creandola...')

                    create_response = rekognition.create_collection(CollectionId=collection_id)
                    self.stdout.write(f'Collection "{collection_id}" creada exitosamente')
                    self.stdout.write(f'   Status Code: {create_response["StatusCode"]}')
                    self.stdout.write(f'   Collection ARN: {create_response["CollectionArn"]}')
                    self.stdout.write(f'   Modelo version: {create_response["FaceModelVersion"]}')
                else:
                    self.stdout.write(f'Error verificando collection: {e}')
                    return

            # Ahora probar nuestro servicio
            self.stdout.write('\nProbando nuestro AWSFacialRecognitionService...')
            aws_service = AWSFacialRecognitionService()
            self.stdout.write('AWSFacialRecognitionService inicializado correctamente')

            # Mostrar configuración
            self.stdout.write('\nConfiguracion actual:')
            self.stdout.write(f'   Region: us-east-1')
            self.stdout.write(f'   Collection ID: {collection_id}')

            self.stdout.write(
                self.style.SUCCESS(
                    '\nAWS Rekognition esta listo para usar!\n'
                    'Puedes comenzar a registrar personas desde el frontend.'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error conectando con AWS Rekognition: {str(e)}')
            )
            self.stdout.write(
                self.style.WARNING(
                    'Verifica tus credenciales AWS y que tengas los permisos necesarios.'
                )
            )