from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import AreaComun, ReservaArea, EstadoAreaComun, EstadoReserva
from .serializers import (
    AreaComunSerializer, AreaComunListSerializer,
    ReservaAreaSerializer, ReservaAreaCreateSerializer, ReservaAreaListSerializer,
    EstadisticasAreasSerializer, DisponibilidadAreaSerializer
)


class AreaComunViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de áreas comunes
    """
    queryset = AreaComun.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'moneda']
    search_fields = ['nombre']
    ordering_fields = ['nombre', 'precio_base', 'created_at']
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return AreaComunListSerializer
        return AreaComunSerializer

    def get_permissions(self):
        """
        Admin/Conserje puede crear, actualizar, eliminar
        Propietarios solo pueden ver
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def verificar_disponibilidad(self, request, pk=None):
        """
        Verifica disponibilidad de un área en fechas específicas
        """
        area = self.get_object()
        serializer = DisponibilidadAreaSerializer(data=request.data)

        if serializer.is_valid():
            fecha_inicio = serializer.validated_data['fecha_inicio']
            fecha_fin = serializer.validated_data['fecha_fin']

            disponible = area.puede_reservar(fecha_inicio, fecha_fin)

            return Response({
                'disponible': disponible,
                'area': area.nombre,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'mensaje': 'Área disponible' if disponible else 'Área no disponible para el periodo solicitado'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtiene estadísticas generales de las áreas comunes
        """
        areas = AreaComun.objects.all()
        reservas = ReservaArea.objects.all()

        # Calcular estadísticas
        stats = {
            'total_areas': areas.count(),
            'areas_disponibles': areas.filter(estado=EstadoAreaComun.DISPONIBLE).count(),
            'areas_en_mantenimiento': areas.filter(estado=EstadoAreaComun.MANTENIMIENTO).count(),
            'areas_fuera_servicio': areas.filter(estado=EstadoAreaComun.FUERA_DE_SERVICIO).count(),
            'total_reservas': reservas.count(),
            'reservas_activas': reservas.filter(
                estado__in=[EstadoReserva.CONFIRMADA]
            ).count(),
            'ingresos_mes_actual': reservas.filter(
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year,
                estado__in=[EstadoReserva.CONFIRMADA]
            ).aggregate(total=Sum('precio_total'))['total'] or 0
        }

        serializer = EstadisticasAreasSerializer(stats)
        return Response(serializer.data)


class ReservaAreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de reservas de áreas
    """
    queryset = ReservaArea.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'area', 'moneda']
    search_fields = ['area__nombre', 'propietario__user__first_name', 'propietario__user__last_name']
    ordering_fields = ['fecha_inicio', 'fecha_fin', 'precio_total', 'created_at']
    ordering = ['-fecha_inicio']

    def get_serializer_class(self):
        if self.action == 'list':
            return ReservaAreaListSerializer
        elif self.action == 'create':
            return ReservaAreaCreateSerializer
        return ReservaAreaSerializer

    def get_queryset(self):
        """
        Filtrar reservas según el tipo de usuario
        """
        user = self.request.user

        # TEMPORAL: Mostrar todas las reservas para testing
        return ReservaArea.objects.all()

        # # Admin y conserje ven todas las reservas
        # if hasattr(user, 'user_condominio') and user.user_condominio.es_administrador_o_conserje:
        #     return ReservaArea.objects.all()

        # # Propietarios solo ven sus propias reservas
        # if hasattr(user, 'propietario'):
        #     return ReservaArea.objects.filter(propietario=user.propietario)

        # return ReservaArea.objects.none()

    def get_permissions(self):
        """
        Propietarios pueden crear reservas
        Admin/Conserje pueden hacer todo
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        Asignar propietario automáticamente al crear reserva
        """
        if hasattr(self.request.user, 'propietario'):
            serializer.save(propietario=self.request.user.propietario)
        else:
            # Si es admin/conserje, debe especificar el propietario
            serializer.save()

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """
        Confirmar una reserva pendiente
        """
        reserva = self.get_object()

        if reserva.estado != EstadoReserva.PENDIENTE:
            return Response(
                {'error': 'Solo se pueden confirmar reservas pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar disponibilidad una vez más
        if not reserva.area.puede_reservar(reserva.fecha_inicio, reserva.fecha_fin):
            return Response(
                {'error': 'El área ya no está disponible para este periodo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reserva.estado = EstadoReserva.CONFIRMADA
        reserva.save()

        return Response({
            'mensaje': 'Reserva confirmada exitosamente',
            'reserva': ReservaAreaSerializer(reserva).data
        })

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar una reserva
        """
        reserva = self.get_object()

        if not reserva.puede_cancelar:
            return Response(
                {'error': 'Esta reserva no puede ser cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reserva.estado = EstadoReserva.CANCELADA
        reserva.save()

        return Response({
            'mensaje': 'Reserva cancelada exitosamente',
            'reserva': ReservaAreaSerializer(reserva).data
        })

    # @action(detail=True, methods=['post'])
    # def marcar_en_uso(self, request, pk=None):
    #     """
    #     Marcar reserva como en uso (cuando comienza)
    #     """
    #     reserva = self.get_object()

    #     if reserva.estado != EstadoReserva.CONFIRMADA:
    #         return Response(
    #             {'error': 'Solo se pueden marcar en uso reservas confirmadas'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     # Verificar que estamos en el tiempo de la reserva
    #     ahora = timezone.now()
    #     if ahora < reserva.fecha_inicio:
    #         return Response(
    #             {'error': 'La reserva aún no ha comenzado'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     reserva.estado = EstadoReserva.EN_USO
    #     reserva.save()

    #     return Response({
    #         'mensaje': 'Reserva marcada como en uso',
    #         'reserva': ReservaAreaSerializer(reserva).data
    #     })

    # @action(detail=True, methods=['post'])
    # def completar(self, request, pk=None):
    #     """
    #     Completar una reserva confirmada
    #     """
    #     reserva = self.get_object()

    #     if reserva.estado != EstadoReserva.CONFIRMADA:
    #         return Response(
    #             {'error': 'Solo se pueden completar reservas confirmadas'},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     reserva.estado = EstadoReserva.COMPLETADA
    #     reserva.save()

    #     return Response({
    #         'mensaje': 'Reserva completada exitosamente',
    #         'reserva': ReservaAreaSerializer(reserva).data
    #     })

    @action(detail=False, methods=['get'])
    def mis_reservas(self, request):
        """
        Obtener reservas del propietario autenticado
        """
        if not hasattr(request.user, 'propietario'):
            return Response(
                {'error': 'Usuario no es propietario'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservas = ReservaArea.objects.filter(
            propietario=request.user.propietario
        ).order_by('-fecha_inicio')

        serializer = ReservaAreaListSerializer(reservas, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def proximas(self, request):
        """
        Obtener próximas reservas confirmadas
        """
        ahora = timezone.now()
        reservas = self.get_queryset().filter(
            estado__in=[EstadoReserva.CONFIRMADA],
            fecha_inicio__gte=ahora
        ).order_by('fecha_inicio')[:10]

        serializer = ReservaAreaListSerializer(reservas, many=True)
        return Response(serializer.data)
