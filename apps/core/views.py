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
    ordering_fields = ['nombre', 'numero_pisos', 'created_at']
    ordering = ['condominio__nombre', 'nombre']


class ConfiguracionSistemaViewSet(viewsets.ModelViewSet):
    queryset = ConfiguracionSistema.objects.all()
    serializer_class = ConfiguracionSistemaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['clave', 'descripcion']
    filterset_fields = ['tipo']
    ordering_fields = ['clave', 'created_at']
    ordering = ['clave']
