from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet, RoleViewSet, PermissionViewSet

app_name = 'users'

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]