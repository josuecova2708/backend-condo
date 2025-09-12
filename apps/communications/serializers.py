from rest_framework import serializers
from apps.communications.models import AvisoComunicado, LecturaAviso
from apps.core.models import Condominio
from apps.users.models import User


class AvisoComunicadoSerializer(serializers.ModelSerializer):
    autor_name = serializers.CharField(source='autor.get_full_name', read_only=True)
    condominio_nombre = serializers.CharField(source='condominio.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    is_expired = serializers.CharField(read_only=True)
    lecturas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AvisoComunicado
        fields = [
            'id', 'titulo', 'contenido', 'tipo', 'tipo_display',
            'prioridad', 'prioridad_display', 'condominio', 'condominio_nombre',
            'autor', 'autor_name', 'fecha_publicacion', 'fecha_expiracion',
            'is_active', 'is_published', 'archivo_adjunto', 'imagen',
            'is_expired', 'lecturas_count', 'created_at', 'updated_at'
        ]

    def get_lecturas_count(self, obj):
        """
        Obtener el número de lecturas del aviso
        """
        return obj.lecturas.count()


class AvisoComunicadoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvisoComunicado
        fields = [
            'titulo', 'contenido', 'tipo', 'prioridad', 'condominio',
            'fecha_publicacion', 'fecha_expiracion', 'is_active', 
            'is_published', 'archivo_adjunto', 'imagen'
        ]

    def validate(self, attrs):
        fecha_publicacion = attrs.get('fecha_publicacion')
        fecha_expiracion = attrs.get('fecha_expiracion')
        
        # Validar que fecha_expiracion sea posterior a fecha_publicacion si ambas están presentes
        if fecha_publicacion and fecha_expiracion and fecha_expiracion <= fecha_publicacion:
            raise serializers.ValidationError({
                'fecha_expiracion': 'La fecha de expiración debe ser posterior a la fecha de publicación'
            })
        
        return attrs

    def create(self, validated_data):
        # Asignar automáticamente el autor como el usuario actual
        validated_data['autor'] = self.context['request'].user
        return super().create(validated_data)


class LecturaAvisoSerializer(serializers.ModelSerializer):
    aviso_titulo = serializers.CharField(source='aviso.titulo', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LecturaAviso
        fields = [
            'id', 'aviso', 'aviso_titulo', 'user', 'user_name',
            'fecha_lectura', 'ip_address', 'created_at', 'updated_at'
        ]


class LecturaAvisoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaAviso
        fields = ['aviso']

    def validate_aviso(self, value):
        """
        Validar que el aviso esté activo y publicado
        """
        if not value.is_active or not value.is_published:
            raise serializers.ValidationError("El aviso no está disponible para lectura")
        
        # Validar que el usuario no haya leído ya este aviso
        user = self.context['request'].user
        if LecturaAviso.objects.filter(aviso=value, user=user).exists():
            raise serializers.ValidationError("Ya has leído este aviso")
        
        return value

    def create(self, validated_data):
        # Asignar automáticamente el usuario actual
        validated_data['user'] = self.context['request'].user
        
        # Obtener la IP del request
        request = self.context['request']
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        validated_data['ip_address'] = ip
        
        return super().create(validated_data)


class AvisoComunicadoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados (sin contenido completo)
    """
    autor_name = serializers.CharField(source='autor.get_full_name', read_only=True)
    condominio_nombre = serializers.CharField(source='condominio.nombre', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    is_expired = serializers.CharField(read_only=True)
    lecturas_count = serializers.SerializerMethodField()
    preview_contenido = serializers.SerializerMethodField()
    
    class Meta:
        model = AvisoComunicado
        fields = [
            'id', 'titulo', 'preview_contenido', 'tipo', 'tipo_display',
            'prioridad', 'prioridad_display', 'condominio_nombre',
            'autor_name', 'fecha_publicacion', 'fecha_expiracion',
            'is_active', 'is_published', 'is_expired', 'lecturas_count',
            'created_at'
        ]

    def get_lecturas_count(self, obj):
        """
        Obtener el número de lecturas del aviso
        """
        return obj.lecturas.count()

    def get_preview_contenido(self, obj):
        """
        Obtener un preview del contenido (primeros 150 caracteres)
        """
        if len(obj.contenido) > 150:
            return obj.contenido[:150] + "..."
        return obj.contenido