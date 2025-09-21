from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.users.models import User, Role, Permission, RolePermission
from apps.core.models import Condominio


class RoleSerializer(serializers.ModelSerializer):
    permissions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ('id', 'nombre', 'descripcion', 'is_active', 'permissions_count', 'created_at', 'updated_at')
    
    def get_permissions_count(self, obj):
        return obj.permissions.count()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'nombre', 'codigo', 'descripcion', 'modulo')


class CondominioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominio
        fields = ('id', 'nombre', 'direccion', 'telefono', 'email')


class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.nombre', read_only=True)
    condominio_name = serializers.CharField(source='condominio.nombre', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'telefono', 'cedula', 'fecha_nacimiento', 'avatar',
            'is_verified', 'is_active', 'date_joined', 'last_login',
            'role', 'role_name', 'condominio', 'condominio_name',
            'full_name', 'password'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'date_joined': {'read_only': True},
            'last_login': {'read_only': True},
            'is_verified': {'read_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance

    def validate_email(self, value):
        if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_cedula(self, value):
        if value and User.objects.filter(cedula=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("Ya existe un usuario con esta cédula.")
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'first_name', 'last_name',
            'telefono', 'cedula', 'fecha_nacimiento', 'role', 'condominio'
        )
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_cedula(self, value):
        if value and User.objects.filter(cedula=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con esta cédula.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Serializer básico para información de usuario en relaciones
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']