from rest_framework import serializers
from apps.core.models import Condominio, Bloque, ConfiguracionSistema


class CondominioSerializer(serializers.ModelSerializer):
    bloques_count = serializers.SerializerMethodField()
    usuarios_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Condominio
        fields = (
            'id', 'nombre', 'direccion', 'telefono', 'email', 'nit',
            'logo', 'is_active', 'bloques_count', 'usuarios_count',
            'created_at', 'updated_at'
        )

    def get_bloques_count(self, obj):
        return obj.bloques.filter(is_active=True).count()

    def get_usuarios_count(self, obj):
        return obj.usuarios.filter(is_active=True).count()


class BloqueSerializer(serializers.ModelSerializer):
    condominio_name = serializers.CharField(source='condominio.nombre', read_only=True)
    unidades_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Bloque
        fields = (
            'id', 'condominio', 'condominio_name', 'nombre', 'descripcion',
            'is_active', 'unidades_count', 'created_at', 'updated_at'
        )

    def get_unidades_count(self, obj):
        return obj.unidades.filter(is_active=True).count()


class ConfiguracionSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionSistema
        fields = '__all__'

    def validate_tipo(self, value):
        """
        Validar que el tipo sea uno de los valores permitidos
        """
        valid_types = ['string', 'integer', 'float', 'boolean', 'json']
        if value not in valid_types:
            raise serializers.ValidationError(f"Tipo debe ser uno de: {', '.join(valid_types)}")
        return value

    def validate(self, data):
        """
        Validar que el valor sea compatible con el tipo especificado
        """
        tipo = data.get('tipo', 'string')
        valor = data.get('valor', '')
        
        try:
            if tipo == 'integer':
                int(valor)
            elif tipo == 'float':
                float(valor)
            elif tipo == 'boolean':
                if valor.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    raise ValueError()
            elif tipo == 'json':
                import json
                json.loads(valor)
        except (ValueError, TypeError):
            raise serializers.ValidationError(f"El valor '{valor}' no es válido para el tipo '{tipo}'")
        
        return data