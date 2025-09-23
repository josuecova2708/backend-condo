from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import TareaMantenimiento, EstadoTarea
from .serializers import (
    TareaMantenimientoSerializer,
    TareaMantenimientoCreateSerializer,
    EstadoUpdateSerializer,
    TipoEstadoChoicesSerializer
)


class TareaMantenimientoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de tareas de mantenimiento
    """
    queryset = TareaMantenimiento.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'tipo']
    search_fields = ['titulo', 'descripcion']
    ordering_fields = ['fecha_creacion', 'programada_para', 'costo_estimado', 'costo_real']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'create':
            return TareaMantenimientoCreateSerializer
        elif self.action == 'actualizar_estado':
            return EstadoUpdateSerializer
        return TareaMantenimientoSerializer

    @action(detail=True, methods=['patch'])
    def actualizar_estado(self, request, pk=None):
        """
        Actualizar solo el estado de una tarea
        """
        tarea = self.get_object()
        serializer = EstadoUpdateSerializer(data=request.data)

        if serializer.is_valid():
            nuevo_estado = serializer.validated_data['estado']
            costo_real = serializer.validated_data.get('costo_real')

            tarea.estado = nuevo_estado
            if costo_real is not None:
                tarea.costo_real = costo_real

            tarea.save()

            # Devolver la tarea actualizada
            response_serializer = TareaMantenimientoSerializer(tarea)
            return Response({
                'message': f'Estado actualizado a {tarea.get_estado_display()}',
                'tarea': response_serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def completar(self, request, pk=None):
        """
        Marcar una tarea como realizada
        """
        tarea = self.get_object()

        if not tarea.puede_completar:
            return Response(
                {'error': 'Esta tarea no puede ser completada en su estado actual'},
                status=status.HTTP_400_BAD_REQUEST
            )

        costo_real = request.data.get('costo_real')
        tarea.estado = EstadoTarea.COMPLETADA

        if costo_real is not None:
            try:
                tarea.costo_real = float(costo_real)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'El costo real debe ser un número válido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        tarea.save()

        response_serializer = TareaMantenimientoSerializer(tarea)
        return Response({
            'message': 'Tarea marcada como completada',
            'tarea': response_serializer.data
        })

    @action(detail=False, methods=['get'])
    def opciones(self, request):
        """
        Obtener opciones para tipos y estados
        """
        serializer = TipoEstadoChoicesSerializer({})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtener estadísticas básicas de tareas
        """
        total = self.get_queryset().count()
        pendientes = self.get_queryset().filter(estado=EstadoTarea.PENDIENTE).count()
        en_progreso = self.get_queryset().filter(estado=EstadoTarea.EN_PROGRESO).count()
        realizadas = self.get_queryset().filter(estado=EstadoTarea.COMPLETADA).count()

        return Response({
            'total': total,
            'pendientes': pendientes,
            'en_progreso': en_progreso,
            'realizadas': realizadas,
            'porcentaje_completadas': round((realizadas / total * 100) if total > 0 else 0, 1)
        })

    def perform_destroy(self, instance):
        """
        Personalizar eliminación si es necesario
        """
        if instance.estado == EstadoTarea.EN_PROGRESO:
            # Opcional: Prevenir eliminación de tareas en progreso
            pass
        super().perform_destroy(instance)