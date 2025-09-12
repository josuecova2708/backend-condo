from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet, RoleViewSet, PermissionViewSet

app_name = 'users'

# Router para usuarios (conflictúa con otras rutas)
user_router = DefaultRouter()
user_router.register(r'manage', UserViewSet, basename='user')

# Router para roles
role_router = DefaultRouter()  
role_router.register(r'', RoleViewSet, basename='role')

# Router para permisos
permission_router = DefaultRouter()
permission_router.register(r'', PermissionViewSet, basename='permission')

urlpatterns = [
    # Rutas específicas primero
    path('roles/', include(role_router.urls)),
    path('permissions/', include(permission_router.urls)),
    # Usuario management en ruta separada para evitar conflictos
    path('', include(user_router.urls)),
]