from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from decimal import Decimal
from django.db.models import Q, Sum, Count
from django.utils import timezone

from .models import Infraccion, Cargo, ConfiguracionMultas, EstadoInfraccion, EstadoCargo, TipoCargo
from .serializers import (
    InfraccionSerializer, InfraccionCreateSerializer, InfraccionListSerializer,
    CargoSerializer, CargoCreateSerializer, CargoListSerializer,
    ConfiguracionMultasSerializer, AplicarMultaSerializer, ProcesarPagoSerializer,
    EstadisticasInfraccionesSerializer
)
from .services import MultasService, ConfiguracionMultasService


class InfraccionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar infracciones
    """
    queryset = Infraccion.objects.all().select_related(
        'propietario__user', 'unidad__bloque', 'reportado_por'
    ).order_by('-fecha_infraccion')

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'tipo_infraccion', 'propietario', 'unidad', 'es_reincidente']
    search_fields = ['descripcion', 'propietario__user__first_name', 'propietario__user__last_name']
    ordering_fields = ['fecha_infraccion', 'fecha_limite_pago', 'monto_multa']

    def get_serializer_class(self):
        """Usar diferentes serializers según la acción"""
        if self.action == 'create':
            return InfraccionCreateSerializer
        elif self.action == 'list':
            return InfraccionListSerializer
        return InfraccionSerializer

    def get_queryset(self):
        """Filtrar por propietario si el usuario no es admin"""
        queryset = super().get_queryset()
        user = self.request.user

        # Si el usuario tiene rol de propietario, solo ver sus infracciones
        if hasattr(user, 'propiedades_owned') and user.propiedades_owned.exists():
            if not user.is_staff and not user.has_permission('finances.view_all_infracciones'):
                queryset = queryset.filter(propietario__user=user)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirmar(self, request, pk=None):
        """Confirmar una infracción"""
        infraccion = self.get_object()
        observaciones = request.data.get('observaciones_admin', '')

        try:
            infraccion_confirmada = MultasService.confirmar_infraccion(
                infraccion.id, observaciones
            )
            serializer = InfraccionSerializer(infraccion_confirmada)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rechazar(self, request, pk=None):
        """Rechazar una infracción"""
        infraccion = self.get_object()
        observaciones = request.data.get('observaciones_admin', '')

        if not observaciones:
            return Response(
                {'error': 'Se requieren observaciones para rechazar una infracción'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            infraccion_rechazada = MultasService.rechazar_infraccion(
                infraccion.id, observaciones
            )
            serializer = InfraccionSerializer(infraccion_rechazada)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def aplicar_multa(self, request, pk=None):
        """Aplicar multa a una infracción confirmada"""
        serializer = AplicarMultaSerializer(data={
            'infraccion_id': pk,
            **request.data
        })

        if serializer.is_valid():
            try:
                cargo = MultasService.aplicar_multa(
                    infraccion_id=pk,
                    monto_personalizado=serializer.validated_data.get('monto_personalizado')
                )
                cargo_serializer = CargoSerializer(cargo)
                return Response(cargo_serializer.data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def pendientes(self, request):
        """Obtener infracciones pendientes de revisión"""
        infracciones = MultasService.obtener_infracciones_pendientes()
        serializer = InfraccionListSerializer(infracciones, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def estadisticas(self, request):
        """Obtener estadísticas de infracciones"""
        propietario_id = request.query_params.get('propietario_id')
        estadisticas = MultasService.calcular_estadisticas_infracciones(propietario_id)
        serializer = EstadisticasInfraccionesSerializer(estadisticas)
        return Response(serializer.data)


class CargoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cargos
    """
    queryset = Cargo.objects.all().select_related(
        'propietario__user', 'unidad__bloque', 'infraccion'
    ).order_by('-fecha_emision')

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'tipo_cargo', 'propietario', 'unidad', 'es_recurrente']
    search_fields = ['concepto', 'propietario__user__first_name', 'propietario__user__last_name']
    ordering_fields = ['fecha_emision', 'fecha_vencimiento', 'monto', 'monto_pagado']

    def get_serializer_class(self):
        """Usar diferentes serializers según la acción"""
        if self.action == 'create':
            return CargoCreateSerializer
        elif self.action == 'list':
            return CargoListSerializer
        return CargoSerializer

    def get_queryset(self):
        """Filtrar por propietario si el usuario no es admin"""
        queryset = super().get_queryset()
        user = self.request.user

        # Si el usuario tiene rol de propietario, solo ver sus cargos
        if hasattr(user, 'propiedades_owned') and user.propiedades_owned.exists():
            if not user.is_staff and not user.has_permission('finances.view_all_cargos'):
                queryset = queryset.filter(propietario__user=user)

        return queryset

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def procesar_pago(self, request, pk=None):
        """Procesar pago de un cargo"""
        serializer = ProcesarPagoSerializer(data={
            'cargo_id': pk,
            **request.data
        })

        if serializer.is_valid():
            try:
                resultado = MultasService.procesar_pago_multa(
                    cargo_id=pk,
                    monto_pago=serializer.validated_data['monto_pago']
                )

                response_data = {
                    'cargo': CargoSerializer(resultado['cargo']).data,
                    'saldo_restante': resultado['saldo_restante'],
                    'pago_completo': resultado['pago_completo'],
                    'mensaje': 'Pago procesado exitosamente'
                }

                if resultado['cargo_interes']:
                    response_data['cargo_interes'] = CargoSerializer(resultado['cargo_interes']).data
                    response_data['mensaje'] += ' (se generó cargo por intereses de mora)'

                return Response(response_data)
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def vencidos(self, request):
        """Obtener cargos vencidos"""
        cargos = MultasService.obtener_multas_vencidas()
        serializer = CargoListSerializer(cargos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def por_propietario(self, request):
        """Obtener cargos agrupados por propietario con totales"""
        propietario_id = request.query_params.get('propietario_id')
        queryset = self.get_queryset()

        if propietario_id:
            queryset = queryset.filter(propietario_id=propietario_id)

        # Calcular totales por propietario
        resumen = queryset.values(
            'propietario_id',
            'propietario__user__first_name',
            'propietario__user__last_name',
            'propietario__unidad__numero',
            'propietario__unidad__bloque__nombre'
        ).annotate(
            total_cargos=Count('id'),
            monto_total=Sum('monto'),
            monto_pagado_total=Sum('monto_pagado'),
            cargos_pendientes=Count('id', filter=Q(estado__in=[EstadoCargo.PENDIENTE, EstadoCargo.PARCIALMENTE_PAGADO])),
            cargos_vencidos=Count('id', filter=Q(
                estado__in=[EstadoCargo.PENDIENTE, EstadoCargo.PARCIALMENTE_PAGADO],
                fecha_vencimiento__lt=timezone.now().date()
            ))
        )

        return Response(resumen)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def generar_intereses_mora(self, request):
        """Generar automáticamente cargos por intereses de mora"""
        cargos_generados = MultasService.generar_intereses_mora_automaticos()

        if cargos_generados:
            serializer = CargoListSerializer(cargos_generados, many=True)
            return Response({
                'mensaje': f'Se generaron {len(cargos_generados)} cargos por intereses de mora',
                'cargos_generados': serializer.data
            })
        else:
            return Response({
                'mensaje': 'No se encontraron cargos elegibles para generar intereses de mora'
            })


class ConfiguracionMultasViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar configuraciones de multas
    """
    queryset = ConfiguracionMultas.objects.all().order_by('tipo_infraccion')
    serializer_class = ConfiguracionMultasSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['tipo_infraccion', 'es_activa']
    ordering_fields = ['tipo_infraccion', 'monto_base', 'monto_reincidencia']

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def activas(self, request):
        """Obtener solo configuraciones activas"""
        configuraciones = ConfiguracionMultasService.obtener_configuraciones_activas()
        serializer = ConfiguracionMultasSerializer(configuraciones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def activar(self, request, pk=None):
        """Activar una configuración de multa"""
        configuracion = self.get_object()
        configuracion.es_activa = True
        configuracion.save()
        serializer = ConfiguracionMultasSerializer(configuracion)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def desactivar(self, request, pk=None):
        """Desactivar una configuración de multa"""
        configuracion = self.get_object()
        configuracion.es_activa = False
        configuracion.save()
        serializer = ConfiguracionMultasSerializer(configuracion)
        return Response(serializer.data)
