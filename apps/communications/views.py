from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Q
from apps.communications.models import AvisoComunicado, LecturaAviso
from apps.communications.serializers import (
    AvisoComunicadoSerializer,
    AvisoComunicadoCreateSerializer,
    AvisoComunicadoListSerializer,
    LecturaAvisoSerializer,
    LecturaAvisoCreateSerializer
)


class AvisoComunicadoViewSet(viewsets.ModelViewSet):
    queryset = AvisoComunicado.objects.select_related('autor', 'condominio').all()
    serializer_class = AvisoComunicadoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['titulo', 'contenido', 'autor__username', 'autor__first_name', 'autor__last_name']
    filterset_fields = ['tipo', 'prioridad', 'condominio', 'is_active', 'is_published']
    ordering_fields = ['fecha_publicacion', 'fecha_expiracion', 'created_at', 'titulo']
    ordering = ['-fecha_publicacion']

    def get_serializer_class(self):
        if self.action == 'list':
            return AvisoComunicadoListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return AvisoComunicadoCreateSerializer
        return AvisoComunicadoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros adicionales por query params
        user = self.request.user
        
        # Filtrar solo avisos publicados para usuarios no administradores
        if not user.is_superuser and (not user.role or user.role.nombre != 'Administrador'):
            queryset = queryset.filter(is_published=True, is_active=True)
        
        # Filtro por condominio del usuario
        if user.condominio:
            queryset = queryset.filter(condominio=user.condominio)
        
        # Filtros por query params
        activos_only = self.request.query_params.get('activos', None)
        if activos_only == 'true':
            queryset = queryset.filter(is_active=True)
        
        vigentes_only = self.request.query_params.get('vigentes', None)
        if vigentes_only == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gt=now)
            )
        
        no_leidos = self.request.query_params.get('no_leidos', None)
        if no_leidos == 'true':
            # Avisos no leídos por el usuario actual
            avisos_leidos_ids = LecturaAviso.objects.filter(
                user=user
            ).values_list('aviso_id', flat=True)
            queryset = queryset.exclude(id__in=avisos_leidos_ids)
        
        return queryset

    @action(detail=True, methods=['post'])
    def marcar_como_leido(self, request, pk=None):
        """
        Marcar un aviso como leído por el usuario actual
        """
        aviso = self.get_object()
        
        # Crear serializer para la lectura
        serializer = LecturaAvisoCreateSerializer(
            data={'aviso': aviso.id},
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Aviso marcado como leído'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def lecturas(self, request, pk=None):
        """
        Obtener las lecturas de un aviso específico
        """
        aviso = self.get_object()
        lecturas = LecturaAviso.objects.filter(
            aviso=aviso
        ).select_related('user').order_by('-fecha_lectura')
        
        serializer = LecturaAvisoSerializer(lecturas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """
        Cambiar el estado activo/inactivo de un aviso
        """
        aviso = self.get_object()
        aviso.is_active = not aviso.is_active
        aviso.save()
        
        serializer = self.get_serializer(aviso)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def toggle_published(self, request, pk=None):
        """
        Cambiar el estado publicado/no publicado de un aviso
        """
        aviso = self.get_object()
        aviso.is_published = not aviso.is_published
        aviso.save()
        
        serializer = self.get_serializer(aviso)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Obtener estadísticas de avisos
        """
        user = request.user
        queryset = self.get_queryset()
        
        total_avisos = queryset.count()
        avisos_activos = queryset.filter(is_active=True).count()
        avisos_publicados = queryset.filter(is_published=True).count()
        
        # Avisos no leídos por el usuario
        avisos_leidos_ids = LecturaAviso.objects.filter(
            user=user
        ).values_list('aviso_id', flat=True)
        avisos_no_leidos = queryset.exclude(id__in=avisos_leidos_ids).count()
        
        # Avisos por tipo
        avisos_por_tipo = {}
        for tipo, _ in AvisoComunicado._meta.get_field('tipo').choices:
            avisos_por_tipo[tipo] = queryset.filter(tipo=tipo).count()
        
        # Avisos por prioridad
        avisos_por_prioridad = {}
        for prioridad, _ in AvisoComunicado._meta.get_field('prioridad').choices:
            avisos_por_prioridad[prioridad] = queryset.filter(prioridad=prioridad).count()
        
        return Response({
            'total_avisos': total_avisos,
            'avisos_activos': avisos_activos,
            'avisos_publicados': avisos_publicados,
            'avisos_no_leidos': avisos_no_leidos,
            'avisos_por_tipo': avisos_por_tipo,
            'avisos_por_prioridad': avisos_por_prioridad,
        })


class LecturaAvisoViewSet(viewsets.ModelViewSet):
    queryset = LecturaAviso.objects.select_related('aviso', 'user').all()
    serializer_class = LecturaAvisoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['aviso__titulo', 'user__username', 'user__first_name', 'user__last_name']
    filterset_fields = ['aviso', 'user']
    ordering_fields = ['fecha_lectura', 'created_at']
    ordering = ['-fecha_lectura']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LecturaAvisoCreateSerializer
        return LecturaAvisoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Los usuarios normales solo pueden ver sus propias lecturas
        if not user.is_superuser and (not user.role or user.role.nombre != 'Administrador'):
            queryset = queryset.filter(user=user)
        
        return queryset
