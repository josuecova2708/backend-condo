from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.core.models import Condominio, Bloque, ConfiguracionSistema
from apps.core.serializers import CondominioSerializer, BloqueSerializer, ConfiguracionSistemaSerializer


class CondominioViewSet(viewsets.ModelViewSet):
    queryset = Condominio.objects.all()
    serializer_class = CondominioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'direccion', 'nit']
    filterset_fields = ['is_active']
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']


class BloqueViewSet(viewsets.ModelViewSet):
    queryset = Bloque.objects.all()
    serializer_class = BloqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    filterset_fields = ['condominio', 'is_active']
    ordering_fields = ['nombre', 'created_at']
    ordering = ['condominio__nombre', 'nombre']


class ConfiguracionSistemaViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionSistema.objects.all()
    serializer_class = ConfiguracionSistemaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['clave', 'descripcion', 'categoria']
    filterset_fields = ['tipo', 'categoria']
    ordering_fields = ['clave', 'categoria', 'created_at']
    ordering = ['categoria', 'clave']

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Solo permite GET (list, retrieve) y DELETE (destroy)
        """
        if self.action in ['create', 'update', 'partial_update']:
            # Denegamos acceso a CREATE, UPDATE, PATCH
            self.permission_classes = []
            return [permission() for permission in self.permission_classes]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        from rest_framework.response import Response
        from rest_framework import status
        return Response(
            {'detail': 'Operación no permitida. Solo se permite consultar y eliminar configuraciones.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        from rest_framework.response import Response
        from rest_framework import status
        return Response(
            {'detail': 'Operación no permitida. Solo se permite consultar y eliminar configuraciones.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        from rest_framework.response import Response
        from rest_framework import status
        return Response(
            {'detail': 'Operación no permitida. Solo se permite consultar y eliminar configuraciones.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
