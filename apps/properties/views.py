from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from apps.properties.models import UnidadHabitacional, Propietario, Residente, HistorialPropietarios
from apps.properties.serializers import (
    UnidadHabitacionalSerializer, 
    UnidadHabitacionalCreateSerializer,
    PropietarioSerializer,
    PropietarioCreateSerializer,
    ResidenteSerializer,
    ResidenteCreateSerializer,
    HistorialPropietariosSerializer,
    HistorialPropietariosCreateSerializer
)


class UnidadHabitacionalViewSet(viewsets.ModelViewSet):
    queryset = UnidadHabitacional.objects.select_related('bloque', 'bloque__condominio').all()
    serializer_class = UnidadHabitacionalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['numero', 'bloque__nombre', 'bloque__condominio__nombre']
    filterset_fields = ['bloque', 'tipo', 'piso', 'is_active']
    ordering_fields = ['numero', 'piso', 'area_m2', 'created_at']
    ordering = ['bloque__nombre', 'numero']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UnidadHabitacionalCreateSerializer
        return UnidadHabitacionalSerializer

    @action(detail=True, methods=['get'])
    def propietarios(self, request, pk=None):
        """
        Obtener propietarios activos de una unidad
        """
        unidad = self.get_object()
        propietarios = Propietario.objects.filter(
            unidad=unidad,
            is_active=True
        ).select_related('user')
        
        serializer = PropietarioSerializer(propietarios, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def residentes(self, request, pk=None):
        """
        Obtener residentes activos de una unidad
        """
        unidad = self.get_object()
        residentes = Residente.objects.filter(
            unidad=unidad,
            is_active=True
        ).select_related('user')
        
        serializer = ResidenteSerializer(residentes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """
        Obtener historial de propietarios de una unidad
        """
        unidad = self.get_object()
        historial = HistorialPropietarios.objects.filter(
            unidad=unidad
        ).select_related('propietario_anterior', 'propietario_nuevo').order_by('-fecha_cambio')
        
        serializer = HistorialPropietariosSerializer(historial, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """
        Cambiar el estado activo/inactivo de una unidad
        """
        unidad = self.get_object()
        unidad.is_active = not unidad.is_active
        unidad.save()
        
        serializer = self.get_serializer(unidad)
        return Response(serializer.data)


class PropietarioViewSet(viewsets.ModelViewSet):
    queryset = Propietario.objects.select_related('user', 'unidad', 'unidad__bloque').all()
    serializer_class = PropietarioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'unidad__numero']
    filterset_fields = ['unidad', 'unidad__bloque', 'is_active']
    ordering_fields = ['fecha_inicio', 'porcentaje_propiedad', 'created_at']
    ordering = ['-fecha_inicio']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PropietarioCreateSerializer
        return PropietarioSerializer

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """
        Cambiar el estado activo/inactivo de un propietario
        """
        propietario = self.get_object()
        propietario.is_active = not propietario.is_active
        propietario.save()
        
        serializer = self.get_serializer(propietario)
        return Response(serializer.data)


class ResidenteViewSet(viewsets.ModelViewSet):
    queryset = Residente.objects.select_related('user', 'unidad', 'unidad__bloque').all()
    serializer_class = ResidenteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'unidad__numero']
    filterset_fields = ['unidad', 'unidad__bloque', 'relacion', 'is_active']
    ordering_fields = ['fecha_inicio', 'relacion', 'created_at']
    ordering = ['-fecha_inicio']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ResidenteCreateSerializer
        return ResidenteSerializer

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """
        Cambiar el estado activo/inactivo de un residente
        """
        residente = self.get_object()
        residente.is_active = not residente.is_active
        residente.save()
        
        serializer = self.get_serializer(residente)
        return Response(serializer.data)


class HistorialPropietariosViewSet(viewsets.ModelViewSet):
    queryset = HistorialPropietarios.objects.select_related(
        'unidad', 'unidad__bloque', 'propietario_anterior', 'propietario_nuevo'
    ).all()
    serializer_class = HistorialPropietariosSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        'unidad__numero', 
        'propietario_anterior__first_name', 
        'propietario_anterior__last_name',
        'propietario_nuevo__first_name', 
        'propietario_nuevo__last_name'
    ]
    filterset_fields = ['unidad', 'unidad__bloque', 'motivo']
    ordering_fields = ['fecha_cambio', 'created_at']
    ordering = ['-fecha_cambio']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return HistorialPropietariosCreateSerializer
        return HistorialPropietariosSerializer
