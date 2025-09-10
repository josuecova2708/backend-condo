from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.models import TimeStampedModel, Condominio


class Role(TimeStampedModel):
    """
    Modelo para roles de usuario.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class Permission(TimeStampedModel):
    """
    Modelo para permisos del sistema.
    """
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    modulo = models.CharField(max_length=100)

    class Meta:
        db_table = 'permisos'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return self.nombre


class RolePermission(models.Model):
    """
    Modelo para la relación muchos a muchos entre roles y permisos.
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='roles')
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rol_permisos'
        unique_together = ['role', 'permission']

    def __str__(self):
        return f"{self.role.nombre} - {self.permission.nombre}"


class User(AbstractUser):
    """
    Modelo de usuario extendido.
    """
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')
    telefono = models.CharField(max_length=20, blank=True)
    cedula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='users/avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_permission(self, permission_code):
        """
        Verifica si el usuario tiene un permiso específico.
        """
        if not self.role:
            return False
        return self.role.permissions.filter(permission__codigo=permission_code).exists()


class UserSession(TimeStampedModel):
    """
    Modelo para registrar sesiones de usuario.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sesiones')
    session_key = models.CharField(max_length=40)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'sesiones_usuario'
        verbose_name = 'Sesión de Usuario'
        verbose_name_plural = 'Sesiones de Usuario'

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
