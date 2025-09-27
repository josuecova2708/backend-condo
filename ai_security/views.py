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

from .models import Vehicle, VehicleAccessLog, VehicleOCRTrainingData
from .serializers import (
    VehicleSerializer,
    VehicleAccessLogSerializer,
    VehicleOCRRequestSerializer,
    VehicleOCRResponseSerializer,
    VehicleOCRTrainingSerializer
)
from .services.vehicle_ocr import VehicleOCRService


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
