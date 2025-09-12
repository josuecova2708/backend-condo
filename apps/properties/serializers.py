from rest_framework import serializers
from apps.properties.models import UnidadHabitacional, Propietario, Residente, HistorialPropietarios
from apps.core.models import Bloque
from apps.users.models import User


class UnidadHabitacionalSerializer(serializers.ModelSerializer):
    bloque_nombre = serializers.CharField(source='bloque.nombre', read_only=True)
    condominio_nombre = serializers.CharField(source='bloque.condominio.nombre', read_only=True)
    direccion_completa = serializers.CharField(read_only=True)
    
    class Meta:
        model = UnidadHabitacional
        fields = [
            'id', 'bloque', 'bloque_nombre', 'condominio_nombre',
            'numero', 'piso', 'tipo', 'area_m2', 'num_habitaciones',
            'num_banos', 'tiene_balcon', 'tiene_parqueadero',
            'observaciones', 'is_active', 'direccion_completa',
            'created_at', 'updated_at'
        ]


class UnidadHabitacionalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadHabitacional
        fields = [
            'bloque', 'numero', 'piso', 'tipo', 'area_m2',
            'num_habitaciones', 'num_banos', 'tiene_balcon',
            'tiene_parqueadero', 'observaciones', 'is_active'
        ]

    def validate(self, attrs):
        # Validar que la combinación bloque-numero sea única
        bloque = attrs.get('bloque')
        numero = attrs.get('numero')
        
        if bloque and numero:
            queryset = UnidadHabitacional.objects.filter(
                bloque=bloque, 
                numero=numero
            )
            
            # Si estamos actualizando, excluir la instancia actual
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'numero': f'Ya existe una unidad con el número {numero} en el bloque {bloque.nombre}'
                })
        
        return attrs


class PropietarioSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_telefono = serializers.CharField(source='user.telefono', read_only=True)
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)
    
    class Meta:
        model = Propietario
        fields = [
            'id', 'user', 'user_full_name', 'user_email', 'user_telefono',
            'unidad', 'unidad_numero', 'bloque_nombre', 'porcentaje_propiedad',
            'fecha_inicio', 'fecha_fin', 'is_active', 'documento_propiedad',
            'created_at', 'updated_at'
        ]


class PropietarioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Propietario
        fields = [
            'user', 'unidad', 'porcentaje_propiedad', 'fecha_inicio',
            'fecha_fin', 'is_active', 'documento_propiedad'
        ]

    def validate_porcentaje_propiedad(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("El porcentaje de propiedad debe estar entre 0 y 100")
        return value

    def validate(self, attrs):
        user = attrs.get('user')
        unidad = attrs.get('unidad')
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        
        # Validar que fecha_fin sea posterior a fecha_inicio si ambas están presentes
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin debe ser posterior a la fecha de inicio'
            })
        
        # Validar que no exista otro propietario activo para la misma unidad y usuario
        if user and unidad:
            queryset = Propietario.objects.filter(
                user=user,
                unidad=unidad,
                is_active=True
            )
            
            # Si estamos actualizando, excluir la instancia actual
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'user': f'El usuario {user.get_full_name()} ya es propietario activo de esta unidad'
                })
        
        return attrs


class ResidenteSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_telefono = serializers.CharField(source='user.telefono', read_only=True)
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)
    relacion_display = serializers.CharField(source='get_relacion_display', read_only=True)
    
    class Meta:
        model = Residente
        fields = [
            'id', 'user', 'user_full_name', 'user_email', 'user_telefono',
            'unidad', 'unidad_numero', 'bloque_nombre', 'relacion',
            'relacion_display', 'fecha_inicio', 'fecha_fin', 'is_active',
            'observaciones', 'created_at', 'updated_at'
        ]


class ResidenteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Residente
        fields = [
            'user', 'unidad', 'relacion', 'fecha_inicio',
            'fecha_fin', 'is_active', 'observaciones'
        ]

    def validate(self, attrs):
        user = attrs.get('user')
        unidad = attrs.get('unidad')
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        
        # Validar que fecha_fin sea posterior a fecha_inicio si ambas están presentes
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': 'La fecha fin debe ser posterior a la fecha de inicio'
            })
        
        return attrs


class HistorialPropietariosSerializer(serializers.ModelSerializer):
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)
    propietario_anterior_name = serializers.CharField(
        source='propietario_anterior.get_full_name', 
        read_only=True
    )
    propietario_nuevo_name = serializers.CharField(
        source='propietario_nuevo.get_full_name', 
        read_only=True
    )
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)
    
    class Meta:
        model = HistorialPropietarios
        fields = [
            'id', 'unidad', 'unidad_numero', 'bloque_nombre',
            'propietario_anterior', 'propietario_anterior_name',
            'propietario_nuevo', 'propietario_nuevo_name',
            'fecha_cambio', 'motivo', 'motivo_display',
            'observaciones', 'documento_soporte',
            'created_at', 'updated_at'
        ]


class HistorialPropietariosCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPropietarios
        fields = [
            'unidad', 'propietario_anterior', 'propietario_nuevo',
            'fecha_cambio', 'motivo', 'observaciones', 'documento_soporte'
        ]

    def validate(self, attrs):
        propietario_anterior = attrs.get('propietario_anterior')
        propietario_nuevo = attrs.get('propietario_nuevo')
        
        # El propietario nuevo es obligatorio
        if not propietario_nuevo:
            raise serializers.ValidationError({
                'propietario_nuevo': 'El nuevo propietario es requerido'
            })
        
        # Validar que los propietarios sean diferentes (si hay propietario anterior)
        if propietario_anterior and propietario_anterior == propietario_nuevo:
            raise serializers.ValidationError({
                'propietario_nuevo': 'El nuevo propietario debe ser diferente al anterior'
            })
        
        return attrs