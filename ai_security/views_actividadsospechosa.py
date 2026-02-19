from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from .models import TipoActividad, AnalisisVideo, DeteccionActividad
from .serializers import (
    TipoActividadSerializer,
    AnalisisVideoSerializer,
    DeteccionActividadSerializer,
    IniciarAnalisisSerializer,
    EstadisticasAnalisisSerializer
)
from .services.video_analysis import VideoAnalysisService


class ActividadSospechosaViewSet(viewsets.ViewSet):
    """
    ViewSet para análisis de actividades sospechosas en videos.
    """
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.video_service = VideoAnalysisService()

    @action(detail=False, methods=['post'])
    def iniciar_analisis(self, request):
        """
        Iniciar análisis de video para detectar actividades sospechosas.
        """
        # Validar datos de entrada
        serializer = IniciarAnalisisSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            camera_id = serializer.validated_data['camera_id']
            video_name = serializer.validated_data['video_name']

            # Construir URL del video en S3
            video_url = f"s3://{settings.AWS_S3_BUCKET_NAME}/{camera_id}/{video_name}"

            # Iniciar análisis
            analisis = self.video_service.iniciar_analisis(
                camera_id=camera_id,
                video_name=video_name,
                video_url=video_url,
                usuario=request.user
            )

            serializer_response = AnalisisVideoSerializer(analisis)

            return Response({
                'success': True,
                'message': 'Análisis iniciado exitosamente',
                'analisis': serializer_response.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error iniciando análisis: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def mis_analisis(self, request):
        """
        Obtener análisis del usuario actual.
        """
        try:
            # Si es superuser, mostrar todos; si no, solo los suyos
            if request.user.is_superuser:
                analisis = AnalisisVideo.objects.all()
            else:
                analisis = AnalisisVideo.objects.filter(usuario=request.user)

            analisis = analisis.order_by('-iniciado_at')
            serializer = AnalisisVideoSerializer(analisis, many=True)

            return Response({
                'success': True,
                'analisis': serializer.data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def detalle_analisis(self, request, pk=None):
        """
        Obtener detalle de un análisis específico incluyendo todas sus detecciones.
        """
        try:
            # Verificar que el análisis existe y el usuario tiene permisos
            if request.user.is_superuser:
                analisis = AnalisisVideo.objects.get(pk=pk)
            else:
                analisis = AnalisisVideo.objects.get(pk=pk, usuario=request.user)

            serializer = AnalisisVideoSerializer(analisis)

            return Response({
                'success': True,
                'analisis': serializer.data
            })

        except AnalisisVideo.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Análisis no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def verificar_estado(self, request, pk=None):
        """
        Verificar el estado de un análisis y procesar resultados si está completo.
        """
        try:
            # Verificar que el análisis existe y el usuario tiene permisos
            if request.user.is_superuser:
                analisis = AnalisisVideo.objects.get(pk=pk)
            else:
                analisis = AnalisisVideo.objects.get(pk=pk, usuario=request.user)

            # Verificar estado con el servicio
            completado = self.video_service.verificar_estado_analisis(analisis)

            # Recargar el análisis para obtener datos actualizados
            analisis.refresh_from_db()
            serializer = AnalisisVideoSerializer(analisis)

            return Response({
                'success': True,
                'completado': completado,
                'analisis': serializer.data
            })

        except AnalisisVideo.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Análisis no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def verificar_pendientes(self, request):
        """
        Verificar todos los análisis pendientes y actualizar su estado.
        """
        try:
            analisis_pendientes = self.video_service.obtener_analisis_pendientes()
            resultados = []

            for analisis in analisis_pendientes:
                try:
                    completado = self.video_service.verificar_estado_analisis(analisis)
                    resultados.append({
                        'analisis_id': analisis.id,
                        'video_name': analisis.video_name,
                        'completado': completado,
                        'estado': analisis.estado
                    })
                except Exception as e:
                    resultados.append({
                        'analisis_id': analisis.id,
                        'video_name': analisis.video_name,
                        'error': str(e)
                    })

            return Response({
                'success': True,
                'total_verificados': len(analisis_pendientes),
                'resultados': resultados
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtener estadísticas generales del análisis de actividades.
        """
        try:
            # Estadísticas generales
            if request.user.is_superuser:
                analisis_qs = AnalisisVideo.objects.all()
                detecciones_qs = DeteccionActividad.objects.all()
            else:
                analisis_qs = AnalisisVideo.objects.filter(usuario=request.user)
                detecciones_qs = DeteccionActividad.objects.filter(analisis__usuario=request.user)

            total_analisis = analisis_qs.count()
            analisis_completados = analisis_qs.filter(estado='COMPLETADO').count()
            analisis_procesando = analisis_qs.filter(estado='PROCESANDO').count()

            total_detecciones = detecciones_qs.count()
            avisos_generados = detecciones_qs.filter(aviso_generado=True).count()

            # Detecciones por categoría
            detecciones_por_categoria = {}
            categorias = TipoActividad.objects.values_list('categoria', flat=True).distinct()

            for categoria in categorias:
                count = detecciones_qs.filter(tipo_actividad__categoria=categoria).count()
                detecciones_por_categoria[categoria] = count

            # Confianza promedio
            confianza_promedio = 0.0
            if analisis_completados > 0:
                analisis_con_confianza = analisis_qs.filter(
                    estado='COMPLETADO',
                    confianza_promedio__isnull=False
                )
                if analisis_con_confianza.exists():
                    confianza_promedio = analisis_con_confianza.aggregate(
                        promedio=models.Avg('confianza_promedio')
                    )['promedio'] or 0.0

            estadisticas = {
                'total_analisis': total_analisis,
                'analisis_completados': analisis_completados,
                'analisis_procesando': analisis_procesando,
                'total_detecciones': total_detecciones,
                'detecciones_por_categoria': detecciones_por_categoria,
                'confianza_promedio': round(confianza_promedio, 2),
                'avisos_generados': avisos_generados
            }

            serializer = EstadisticasAnalisisSerializer(estadisticas)

            return Response({
                'success': True,
                'estadisticas': serializer.data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def tipos_actividad(self, request):
        """
        Obtener tipos de actividades disponibles para detección.
        """
        try:
            tipos = TipoActividad.objects.filter(activo=True)
            serializer = TipoActividadSerializer(tipos, many=True)

            return Response({
                'success': True,
                'tipos_actividad': serializer.data
            })

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def generar_aviso(self, request, pk=None):
        """
        Generar aviso manual para una detección específica.
        """
        try:
            # Buscar la detección
            deteccion = DeteccionActividad.objects.get(pk=pk)

            # Verificar permisos
            if not request.user.is_superuser and deteccion.analisis.usuario != request.user:
                return Response({
                    'success': False,
                    'error': 'No tienes permisos para esta detección'
                }, status=status.HTTP_403_FORBIDDEN)

            # Verificar si ya tiene aviso
            if deteccion.aviso_generado:
                return Response({
                    'success': False,
                    'error': 'Esta detección ya tiene un aviso generado'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generar aviso
            aviso_id = self.video_service.generar_aviso_actividad(deteccion)

            if aviso_id:
                return Response({
                    'success': True,
                    'message': 'Aviso generado exitosamente',
                    'aviso_id': aviso_id
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Error generando aviso'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except DeteccionActividad.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Detección no encontrada'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)