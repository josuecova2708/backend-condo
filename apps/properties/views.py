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
    filterset_fields = ['bloque', 'is_active']
    ordering_fields = ['numero', 'area_m2', 'created_at']
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

    @action(detail=False, methods=['get'])
    def sin_propietario(self, request):
        """
        Obtener unidades que no tienen propietarios activos asignados
        """
        import logging
        logger = logging.getLogger(__name__)

        # Obtener unidades activas que NO tienen propietarios activos
        unidades_sin_propietario = self.get_queryset().filter(
            is_active=True
        ).exclude(
            propietarios__is_active=True
        ).distinct()

        logger.info(f"Total unidades sin propietario: {unidades_sin_propietario.count()}")

        serializer = self.get_serializer(unidades_sin_propietario, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def map_layout(self, request):
        """
        Obtener el layout del mapa con las unidades organizadas por bloques
        """
        unidades = self.get_queryset().select_related('bloque')

        # Organizar unidades por bloque
        bloques_data = {}
        for unidad in unidades:
            bloque_nombre = unidad.bloque.nombre if unidad.bloque else 'Sin Bloque'
            if bloque_nombre not in bloques_data:
                bloques_data[bloque_nombre] = {
                    'nombre': bloque_nombre,
                    'unidades': []
                }

            # Serializar unidad individual
            unidad_data = {
                'id': unidad.id,
                'numero': unidad.numero,
                'is_active': unidad.is_active,
                'area_m2': unidad.area_m2,
                'num_habitaciones': unidad.num_habitaciones,
                'num_banos': unidad.num_banos,
                'tiene_parqueadero': unidad.tiene_parqueadero,
            }
            bloques_data[bloque_nombre]['unidades'].append(unidad_data)

        # Configuración del mapa según las especificaciones
        map_config = {
            'bloques': {
                'A': {
                    'unidades_numeros': [9, 10],
                    'color': '#4CAF50',
                    'position': {'x': 950, 'y': 200}
                },
                'B': {
                    'unidades_numeros': [1, 2, 3, 4],
                    'color': '#2196F3',
                    'position': {'x': 50, 'y': 100}
                },
                'C': {
                    'unidades_numeros': [5, 6, 7, 8, 11, 12, 13, 14],
                    'color': '#FF9800',
                    'position': {'x': 400, 'y': 300}
                }
            },
            'areas_comunes': [
                {'nombre': 'Área Social', 'coordenadas': {'x': 400, 'y': 50}, 'width': 350, 'height': 80},
                {'nombre': 'Piscina', 'coordenadas': {'x': 400, 'y': 450}, 'width': 120, 'height': 80},
                {'nombre': 'Parque', 'coordenadas': {'x': 200, 'y': 450}, 'width': 100, 'height': 80},
                {'nombre': 'Parque', 'coordenadas': {'x': 600, 'y': 450}, 'width': 100, 'height': 80},
                {'nombre': 'Parqueo Visita', 'coordenadas': {'x': 900, 'y': 50}, 'width': 200, 'height': 120},
                {'nombre': 'Tienda', 'coordenadas': {'x': 100, 'y': 650}, 'width': 80, 'height': 40},
                {'nombre': 'Tienda', 'coordenadas': {'x': 800, 'y': 650}, 'width': 80, 'height': 40}
            ]
        }

        return Response({
            'map_config': map_config,
            'bloques_data': bloques_data
        })


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

    @action(detail=False, methods=['get'])
    def usuarios_sin_unidad(self, request):
        """
        Obtener usuarios con rol propietario que no tienen unidad asignada
        """
        from apps.users.models import User
        from apps.users.serializers import UserSerializer
        import logging

        logger = logging.getLogger(__name__)

        # Obtener TODOS los usuarios con rol de propietario activos
        todos_propietarios = User.objects.filter(
            role__nombre='Propietario',
            is_active=True
        )

        logger.info(f"Total usuarios con rol Propietario: {todos_propietarios.count()}")

        # Obtener usuarios que NO tienen asignación activa de propiedad
        usuarios_sin_unidad = todos_propietarios.exclude(
            propiedades_owned__is_active=True
        ).distinct()

        logger.info(f"Usuarios sin unidad asignada: {usuarios_sin_unidad.count()}")

        # Si no hay usuarios específicos, devolver todos los propietarios para debug
        if usuarios_sin_unidad.count() == 0:
            logger.warning("No se encontraron usuarios sin unidad, devolviendo todos los propietarios")
            usuarios_sin_unidad = todos_propietarios

        serializer = UserSerializer(usuarios_sin_unidad, many=True)
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
