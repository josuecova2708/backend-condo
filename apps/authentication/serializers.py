from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from apps.users.models import User, Role
from apps.core.models import Condominio


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para JWT que incluye información adicional del usuario.
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar información personalizada al token
        token['username'] = user.username
        token['email'] = user.email
        token['full_name'] = user.get_full_name()
        token['role'] = user.role.nombre if user.role else None
        token['condominio'] = user.condominio.nombre if user.condominio else None
        
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Agregar información del usuario a la respuesta
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role.nombre if self.user.role else None,
            'condominio': self.user.condominio.nombre if self.user.condominio else None,
            'is_verified': self.user.is_verified,
        }
        
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de nuevos usuarios.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'telefono', 'cedula',
            'fecha_nacimiento', 'condominio', 'role'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        """
        Validar que las contraseñas coincidan.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return attrs

    def validate_email(self, value):
        """
        Validar que el email sea único.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_cedula(self, value):
        """
        Validar que la cédula sea única si se proporciona.
        """
        if value and User.objects.filter(cedula=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con esta cédula.")
        return value

    def create(self, validated_data):
        """
        Crear un nuevo usuario.
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el perfil de usuario.
    """
    role_name = serializers.CharField(source='role.nombre', read_only=True)
    condominio_name = serializers.CharField(source='condominio.nombre', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'telefono', 'cedula', 'fecha_nacimiento', 'avatar',
            'is_verified', 'date_joined', 'last_login',
            'role', 'role_name', 'condominio', 'condominio_name',
            'full_name'
        )
        read_only_fields = (
            'id', 'username', 'date_joined', 'last_login',
            'is_verified', 'role_name', 'condominio_name', 'full_name'
        )

    def validate_email(self, value):
        """
        Validar que el email sea único (excluyendo el usuario actual).
        """
        if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_cedula(self, value):
        """
        Validar que la cédula sea única (excluyendo el usuario actual).
        """
        if value and User.objects.filter(cedula=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Ya existe un usuario con esta cédula.")
        return value


class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer para roles.
    """
    permissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ('id', 'nombre', 'descripcion', 'is_active', 'permissions_count')
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()


class CondominioSerializer(serializers.ModelSerializer):
    """
    Serializer básico para condominios.
    """
    class Meta:
        model = Condominio
        fields = ('id', 'nombre', 'direccion', 'telefono', 'email')