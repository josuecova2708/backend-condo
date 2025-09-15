from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.users.models import User, Role, Permission
from apps.users.serializers import UserSerializer, UserCreateSerializer, RoleSerializer, PermissionSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cedula']
    filterset_fields = ['is_active', 'role', 'condominio']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """
        Cambiar el estado activo/inactivo de un usuario
        """
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """
        Resetear la contraseña de un usuario
        """
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'La nueva contraseña es requerida'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Contraseña actualizada exitosamente'})


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.filter(is_active=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['nombre']

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """
        Obtener todos los permisos asignados a un rol específico
        """
        role = self.get_object()
        permissions = role.permissions.select_related('permission').order_by('permission__modulo', 'permission__nombre')
        serializer = PermissionSerializer([rp.permission for rp in permissions], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign_permission(self, request, pk=None):
        """
        Asignar un permiso a un rol
        """
        from apps.users.models import RolePermission

        role = self.get_object()
        permission_id = request.data.get('permission_id')

        if not permission_id:
            return Response(
                {'error': 'permission_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permission = Permission.objects.get(id=permission_id)
            # Crear la relación si no existe
            role_permission, created = RolePermission.objects.get_or_create(
                role=role,
                permission=permission
            )
            if created:
                return Response({'message': f'Permiso {permission.nombre} asignado al rol {role.nombre}'})
            else:
                return Response({'message': f'El permiso {permission.nombre} ya estaba asignado al rol {role.nombre}'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permiso no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """
        Remover un permiso de un rol
        """
        from apps.users.models import RolePermission

        role = self.get_object()
        permission_id = request.data.get('permission_id')

        if not permission_id:
            return Response(
                {'error': 'permission_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permission = Permission.objects.get(id=permission_id)
            # Eliminar la relación si existe
            deleted_count, _ = RolePermission.objects.filter(
                role=role,
                permission=permission
            ).delete()

            if deleted_count > 0:
                return Response({'message': f'Permiso {permission.nombre} removido del rol {role.nombre}'})
            else:
                return Response({'message': f'El permiso {permission.nombre} no estaba asignado al rol {role.nombre}'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permiso no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def sync_permissions(self, request, pk=None):
        """
        Sincronizar permisos de un rol (reemplazar todos los permisos)
        """
        from apps.users.models import RolePermission

        role = self.get_object()
        permission_ids = request.data.get('permission_ids', [])

        try:
            # Eliminar todas las relaciones existentes
            RolePermission.objects.filter(role=role).delete()

            # Crear las nuevas relaciones
            permissions = Permission.objects.filter(id__in=permission_ids)
            role_permissions = [
                RolePermission(role=role, permission=permission)
                for permission in permissions
            ]
            RolePermission.objects.bulk_create(role_permissions)

            return Response({
                'message': f'Permisos sincronizados para el rol {role.nombre}',
                'count': len(role_permissions)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['modulo']
    ordering = ['modulo', 'nombre']
