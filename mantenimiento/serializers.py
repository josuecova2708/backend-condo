from rest_framework import serializers
from .models import TareaMantenimiento, EstadoTarea, TipoTarea


class TareaMantenimientoSerializer(serializers.ModelSerializer):
    """
    Serializer completo para tareas de mantenimiento
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    esta_completada = serializers.ReadOnlyField()
    puede_completar = serializers.ReadOnlyField()
    costo_formateado = serializers.ReadOnlyField()
    dias_desde_creacion = serializers.ReadOnlyField()

    class Meta:
        model = TareaMantenimiento
        fields = [
            'id', 'titulo', 'tipo', 'tipo_display', 'descripcion', 'estado', 'estado_display',
            'costo_estimado', 'costo_real', 'programada_para', 'tecnico_nombre',
            'fecha_creacion', 'fecha_actualizacion', 'esta_completada', 'puede_completar',
            'costo_formateado', 'dias_desde_creacion'
        ]

    def validate_costo_estimado(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El costo estimado no puede ser negativo")
        return value

    def validate_costo_real(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El costo real no puede ser negativo")
        return value


class TareaMantenimientoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear tareas de mantenimiento
    """
    class Meta:
        model = TareaMantenimiento
        fields = [
            'titulo', 'tipo', 'descripcion', 'costo_estimado',
            'programada_para', 'tecnico_nombre'
        ]

    def validate_titulo(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El título es requerido")
        return value.strip()

    def validate_descripcion(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("La descripción es requerida")
        return value.strip()


class EstadoUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar solo el estado de una tarea
    """
    estado = serializers.ChoiceField(choices=EstadoTarea.choices)
    costo_real = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    def validate_costo_real(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El costo real no puede ser negativo")
        return value


class TipoEstadoChoicesSerializer(serializers.Serializer):
    """
    Serializer para devolver las opciones de tipo y estado
    """
    tipos = serializers.SerializerMethodField()
    estados = serializers.SerializerMethodField()

    def get_tipos(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in TipoTarea.choices]

    def get_estados(self, obj):
        return [{'value': choice[0], 'label': choice[1]} for choice in EstadoTarea.choices]