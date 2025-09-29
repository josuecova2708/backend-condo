import os
from datetime import timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import boto3
from botocore.exceptions import ClientError

from .models import Vehicle, VehicleAccessLog, VehicleOCRTrainingData, PersonProfile, FacialAccessLog
from .serializers import (
    VehicleSerializer,
    VehicleAccessLogSerializer,
    VehicleOCRRequestSerializer,
    VehicleOCRResponseSerializer,
    VehicleOCRTrainingSerializer,
    PersonProfileSerializer,
    FacialAccessLogSerializer,
    FacialRecognitionRequestSerializer,
    PersonRegistrationSerializer
)
from .services.vehicle_ocr import VehicleOCRService
from .services.aws_facial_recognition import AWSFacialRecognitionService


class VehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de vehículos registrados.
    """
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar vehículos por usuario actual si no es admin.
        """
        queryset = Vehicle.objects.all()

        # Si no es superuser, solo mostrar sus vehículos
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        return queryset.order_by('-created_at')

    # perform_create removido - ahora el user se envía explícitamente desde el frontend

    @action(detail=False, methods=['get'])
    def my_vehicles(self, request):
        """
        Obtener vehículos del usuario actual.
        """
        vehicles = Vehicle.objects.filter(user=request.user, is_active=True)
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)


class VehicleAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de acceso vehicular (solo lectura).
    """
    queryset = VehicleAccessLog.objects.all()
    serializer_class = VehicleAccessLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar logs según permisos del usuario.
        """
        queryset = VehicleAccessLog.objects.all()

        # Si no es superuser, solo mostrar logs de sus vehículos
        if not self.request.user.is_superuser:
            queryset = queryset.filter(vehicle__user=self.request.user)

        return queryset.order_by('-timestamp_evento')


class VehicleOCRViewSet(viewsets.GenericViewSet):
    """
    ViewSet para procesamiento OCR de placas vehiculares.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def recognize_plate(self, request):
        """
        Procesar imagen de vehículo y reconocer placa.
        """
        # Validar datos de entrada
        request_serializer = VehicleOCRRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Obtener imagen del request
            imagen = request_serializer.validated_data['imagen']

            # Guardar imagen temporalmente
            temp_path = default_storage.save(
                f'temp/vehicle_ocr/{imagen.name}',
                ContentFile(imagen.read())
            )
            full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            # Procesar imagen con OCR
            ocr_result = VehicleOCRService.process_vehicle_image(full_temp_path)

            # Buscar vehículo registrado si se detectó placa
            vehicle_info = None
            resultado = 'desconocido'
            message = 'No se detectó placa válida'

            detected_plate = ocr_result.get('plate') or ''  # Asegurar que nunca sea None

            if ocr_result['success'] and detected_plate:
                try:
                    vehicle = Vehicle.objects.get(
                        placa=detected_plate,
                        is_active=True
                    )
                    vehicle_info = VehicleSerializer(vehicle).data
                    resultado = 'autorizado'
                    message = f"Vehículo autorizado - {vehicle.user.get_full_name()}"
                except Vehicle.DoesNotExist:
                    resultado = 'denegado'
                    message = f"Vehículo no autorizado - Placa: {detected_plate}"

            # Crear log de acceso
            access_log = VehicleAccessLog.objects.create(
                vehicle=Vehicle.objects.filter(placa=detected_plate).first() if detected_plate else None,
                placa_detectada=detected_plate,
                confianza_ocr=ocr_result.get('confidence', 0.0),
                resultado=resultado,
                imagen=temp_path
            )

            # Preparar respuesta
            response_data = {
                'success': ocr_result['success'],
                'plate': detected_plate or None,  # Mantener None para la respuesta API
                'confidence': ocr_result.get('confidence', 0.0),
                'resultado': resultado,
                'message': message,
                'vehicle_info': vehicle_info,
                'extracted_text': ocr_result.get('extracted_text'),
                'access_log_id': access_log.id
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Error procesando imagen: {str(e)}',
                    'plate': None,
                    'confidence': 0.0
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            # Limpiar archivo temporal
            try:
                if 'full_temp_path' in locals() and os.path.exists(full_temp_path):
                    os.remove(full_temp_path)
            except:
                pass

    @action(detail=False, methods=['post'])
    def train_ocr(self, request):
        """
        Corregir manualmente el resultado del OCR para entrenar el modelo.
        """
        training_serializer = VehicleOCRTrainingSerializer(data=request.data)
        if not training_serializer.is_valid():
            return Response(
                training_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            access_log_id = training_serializer.validated_data['access_log_id']
            placa_correcta = training_serializer.validated_data['placa_correcta']

            # Obtener el log de acceso
            try:
                access_log = VehicleAccessLog.objects.get(id=access_log_id)
            except VehicleAccessLog.DoesNotExist:
                return Response(
                    {'error': 'Log de acceso no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Verificar si ya existe datos de entrenamiento para este log
            training_data, created = VehicleOCRTrainingData.objects.get_or_create(
                access_log=access_log,
                defaults={
                    'placa_detectada_original': access_log.placa_detectada,
                    'placa_correcta': placa_correcta,
                    'confianza_original': access_log.confianza_ocr,
                    'usuario_correccion': request.user
                }
            )

            if not created:
                # Actualizar si ya existe
                training_data.placa_correcta = placa_correcta
                training_data.usuario_correccion = request.user
                training_data.save()

            return Response({
                'success': True,
                'message': 'Datos de entrenamiento guardados exitosamente',
                'training_data_id': training_data.id,
                'placa_original': training_data.placa_detectada_original,
                'placa_correcta': training_data.placa_correcta
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Error guardando datos de entrenamiento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def training_stats(self, request):
        """
        Obtener estadísticas de datos de entrenamiento.
        """
        training_data = VehicleOCRTrainingData.objects.all()

        stats = {
            'total_corrections': training_data.count(),
            'unique_plates': training_data.values('placa_correcta').distinct().count(),
            'recent_corrections': training_data.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
        }

        # Mostrar ejemplos recientes para entrenar
        recent_examples = training_data.order_by('-created_at')[:10].values(
            'placa_detectada_original', 'placa_correcta', 'created_at'
        )

        return Response({
            'stats': stats,
            'recent_examples': list(recent_examples)
        })

    @action(detail=False, methods=['get'])
    def test_service(self, request):
        """
        Endpoint de prueba para verificar que el servicio OCR funciona.
        """
        return Response({
            'message': 'Servicio OCR de placas vehiculares funcionando',
            'version': '1.0.0',
            'supported_formats': ['JPEG', 'PNG', 'BMP'],
            'max_file_size': '10MB'
        })


class PersonProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de perfiles de personas para reconocimiento facial.
    """
    queryset = PersonProfile.objects.all()
    serializer_class = PersonProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar perfiles según permisos del usuario.
        """
        queryset = PersonProfile.objects.all()

        # Si no es superuser, solo mostrar sus perfiles asociados
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        return queryset.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def authorized_profiles(self, request):
        """
        Obtener solo perfiles autorizados.
        """
        profiles = self.get_queryset().filter(is_authorized=True)
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_authorization(self, request, pk=None):
        """
        Autorizar/desautorizar un perfil.
        """
        try:
            profile = self.get_object()
            profile.is_authorized = not profile.is_authorized
            profile.save()

            action = "autorizado" if profile.is_authorized else "desautorizado"
            return Response({
                'success': True,
                'message': f'Perfil {action} exitosamente',
                'is_authorized': profile.is_authorized
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar perfil de persona incluyendo su Face ID en AWS Rekognition.
        """
        try:
            profile = self.get_object()
            aws_service = AWSFacialRecognitionService()

            # Eliminar usando el servicio AWS
            success = aws_service.delete_person_profile(profile)

            if success:
                return Response({
                    'success': True,
                    'message': f'Perfil {profile.name} eliminado exitosamente'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Error eliminando perfil de AWS Rekognition'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FacialAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para logs de acceso facial (solo lectura).
    """
    queryset = FacialAccessLog.objects.all()
    serializer_class = FacialAccessLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtrar logs según permisos del usuario.
        """
        queryset = FacialAccessLog.objects.all()

        # Si no es superuser, solo mostrar logs relacionados a sus perfiles
        if not self.request.user.is_superuser:
            queryset = queryset.filter(person_profile__user=self.request.user)

        return queryset.order_by('-timestamp_evento')

    @action(detail=False, methods=['get'])
    def recent_access(self, request):
        """
        Obtener accesos recientes (últimas 24 horas).
        """
        recent_logs = self.get_queryset().filter(
            timestamp_evento__gte=timezone.now() - timedelta(hours=24)
        )
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)


class FacialRecognitionViewSet(viewsets.GenericViewSet):
    """
    ViewSet para procesamiento de reconocimiento facial.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def identify_person(self, request):
        """
        Identificar persona en una imagen.
        """
        # Validar datos de entrada
        request_serializer = FacialRecognitionRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Obtener imagen del request
            imagen = request_serializer.validated_data['imagen']
            location = request_serializer.validated_data.get('location', 'Entrada Principal')

            # Guardar imagen temporalmente
            temp_path = default_storage.save(
                f'temp/facial_recognition/{imagen.name}',
                ContentFile(imagen.read())
            )
            full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            # Procesar imagen con reconocimiento facial usando AWS Rekognition
            aws_service = AWSFacialRecognitionService()
            recognition_result = aws_service.process_access_request(
                full_temp_path, location
            )

            if recognition_result['success']:
                person_profile = recognition_result.get('person_profile')

                # Preparar información del perfil si existe
                person_info = None
                if person_profile:
                    person_info = PersonProfileSerializer(person_profile).data

                response_data = {
                    'success': True,
                    'person_profile': person_info,
                    'confidence': recognition_result.get('confidence', 0.0),
                    'access_granted': recognition_result.get('access_granted', False),
                    'message': recognition_result.get('message', 'Procesamiento completado'),
                    'access_log_id': recognition_result['access_log'].id if recognition_result.get('access_log') else None
                }
            else:
                response_data = {
                    'success': False,
                    'error': recognition_result.get('error', 'Error desconocido'),
                    'confidence': 0.0,
                    'access_granted': False
                }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Error procesando imagen: {str(e)}',
                    'confidence': 0.0,
                    'access_granted': False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            # Limpiar archivo temporal
            try:
                if 'full_temp_path' in locals() and os.path.exists(full_temp_path):
                    os.remove(full_temp_path)
            except:
                pass

    @action(detail=False, methods=['post'])
    def register_person(self, request):
        """
        Registrar nueva persona en el sistema.
        """
        # Validar datos de entrada
        registration_serializer = PersonRegistrationSerializer(data=request.data)
        if not registration_serializer.is_valid():
            return Response(
                registration_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Obtener datos del request
            imagen = registration_serializer.validated_data['imagen']
            name = registration_serializer.validated_data['name']
            person_type = registration_serializer.validated_data['person_type']
            is_authorized = registration_serializer.validated_data.get('is_authorized', False)
            user_id = registration_serializer.validated_data.get('user')

            # Obtener usuario si se especificó
            user_instance = None
            if user_id:
                from apps.users.models import User
                try:
                    user_instance = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Usuario no encontrado'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Guardar imagen temporalmente
            temp_path = default_storage.save(
                f'temp/facial_registration/{imagen.name}',
                ContentFile(imagen.read())
            )
            full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            # Registrar nueva persona usando AWS Rekognition
            aws_service = AWSFacialRecognitionService()
            registration_result = aws_service.register_new_person(
                image_path=full_temp_path,
                name=name,
                person_type=person_type,
                is_authorized=is_authorized,
                user=user_instance
            )

            if registration_result['success']:
                person_profile = registration_result['person_profile']
                person_info = PersonProfileSerializer(person_profile).data

                response_data = {
                    'success': True,
                    'person_profile': person_info,
                    'message': registration_result.get('message', 'Persona registrada exitosamente')
                }
            else:
                response_data = {
                    'success': False,
                    'error': registration_result.get('error', 'Error registrando persona')
                }

            return Response(response_data, status=status.HTTP_201_CREATED if registration_result['success'] else status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Error registrando persona: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            # Limpiar archivo temporal
            try:
                if 'full_temp_path' in locals() and os.path.exists(full_temp_path):
                    os.remove(full_temp_path)
            except:
                pass

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Obtener estadísticas de reconocimiento facial.
        """
        try:
            # Estadísticas generales
            total_profiles = PersonProfile.objects.count()
            authorized_profiles = PersonProfile.objects.filter(is_authorized=True).count()
            total_access_logs = FacialAccessLog.objects.count()

            # Accesos recientes (últimas 24 horas)
            recent_access = FacialAccessLog.objects.filter(
                timestamp_evento__gte=timezone.now() - timedelta(hours=24)
            ).count()

            # Accesos autorizados vs denegados (último mes)
            last_month = timezone.now() - timedelta(days=30)
            monthly_logs = FacialAccessLog.objects.filter(timestamp_evento__gte=last_month)
            authorized_access = monthly_logs.filter(access_granted=True).count()
            denied_access = monthly_logs.filter(access_granted=False).count()

            stats = {
                'total_profiles': total_profiles,
                'authorized_profiles': authorized_profiles,
                'total_access_logs': total_access_logs,
                'recent_access_24h': recent_access,
                'monthly_stats': {
                    'authorized_access': authorized_access,
                    'denied_access': denied_access,
                    'total_attempts': authorized_access + denied_access
                }
            }

            return Response({
                'success': True,
                'stats': stats
            })

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def test_service(self, request):
        """
        Endpoint de prueba para verificar que el servicio de reconocimiento facial funciona.
        """
        return Response({
            'message': 'Servicio de reconocimiento facial funcionando',
            'version': '1.0.0',
            'supported_formats': ['JPEG', 'PNG', 'BMP'],
            'max_file_size': '10MB',
            'features': [
                'Identificación de personas',
                'Registro de nuevos perfiles',
                'Control de acceso automatizado',
                'Logs de acceso detallados'
            ]
        })


class CameraViewSet(viewsets.ViewSet):
    """
    ViewSet para gestión de cámaras y videos desde S3.
    """
    permission_classes = [IsAuthenticated]

    def get_s3_client(self):
        """
        Crear cliente S3 configurado.
        """
        return boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

    @action(detail=False, methods=['get'])
    def list_cameras(self, request):
        """
        Listar las cámaras disponibles.
        """
        try:
            cameras = [
                {
                    'id': 'camara1',
                    'name': 'Cámara 1',
                    'description': 'Cámara de entrada principal',
                    'location': 'Entrada Principal'
                },
                {
                    'id': 'camara2',
                    'name': 'Cámara 2',
                    'description': 'Cámara de garaje',
                    'location': 'Garaje'
                },
                {
                    'id': 'camara3',
                    'name': 'Cámara 3',
                    'description': 'Cámara de área común',
                    'location': 'Área Común'
                }
            ]

            return Response({
                'success': True,
                'cameras': cameras
            })

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def list_videos(self, request):
        """
        Listar videos de una cámara específica desde S3.
        """
        try:
            camera_id = request.query_params.get('camera_id')
            if not camera_id:
                return Response(
                    {
                        'success': False,
                        'error': 'camera_id es requerido'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validar que la cámara existe
            valid_cameras = ['camara1', 'camara2', 'camara3']
            if camera_id not in valid_cameras:
                return Response(
                    {
                        'success': False,
                        'error': f'Cámara inválida. Debe ser una de: {valid_cameras}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            s3_client = self.get_s3_client()
            bucket_name = settings.AWS_S3_BUCKET_NAME
            prefix = f"{camera_id}/"

            # Listar objetos en la carpeta de la cámara
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )

            videos = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']

                    # Solo incluir archivos de video (no carpetas vacías)
                    if key != prefix and (key.endswith('.mp4') or key.endswith('.avi') or key.endswith('.mov')):
                        # Generar URL firmada válida por 1 hora
                        try:
                            presigned_url = s3_client.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': bucket_name, 'Key': key},
                                ExpiresIn=3600  # 1 hora
                            )

                            videos.append({
                                'key': key,
                                'name': key.split('/')[-1],  # Solo el nombre del archivo
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat(),
                                'url': presigned_url
                            })
                        except ClientError as e:
                            print(f"Error generando URL para {key}: {e}")

            return Response({
                'success': True,
                'camera_id': camera_id,
                'videos': videos,
                'count': len(videos)
            })

        except ClientError as e:
            return Response(
                {
                    'success': False,
                    'error': f'Error de AWS S3: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def get_video_url(self, request):
        """
        Obtener URL firmada para un video específico.
        """
        try:
            camera_id = request.query_params.get('camera_id')
            video_name = request.query_params.get('video_name')

            if not camera_id or not video_name:
                return Response(
                    {
                        'success': False,
                        'error': 'camera_id y video_name son requeridos'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            s3_client = self.get_s3_client()
            bucket_name = settings.AWS_S3_BUCKET_NAME
            key = f"{camera_id}/{video_name}"

            # Verificar que el archivo existe
            try:
                s3_client.head_object(Bucket=bucket_name, Key=key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return Response(
                        {
                            'success': False,
                            'error': 'Video no encontrado'
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                raise

            # Generar URL firmada válida por 1 hora
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key},
                ExpiresIn=3600
            )

            return Response({
                'success': True,
                'camera_id': camera_id,
                'video_name': video_name,
                'url': presigned_url,
                'expires_in': 3600
            })

        except ClientError as e:
            return Response(
                {
                    'success': False,
                    'error': f'Error de AWS S3: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
