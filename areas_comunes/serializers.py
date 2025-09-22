from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from .models import AreaComun, ReservaArea, EstadoAreaComun, EstadoReserva
from apps.users.serializers import UserBasicSerializer
from apps.properties.serializers import PropietarioSerializer


class AreaComunSerializer(serializers.ModelSerializer):
    """
    Serializer completo para áreas comunes
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    esta_disponible = serializers.ReadOnlyField()

    class Meta:
        model = AreaComun
        fields = [
            'id', 'nombre', 'estado', 'precio_base', 'moneda',
            'created_at', 'updated_at',
            # Campos calculados
            'estado_display', 'esta_disponible'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_precio_base(self, value):
        """Validar precio base"""
        if value < Decimal('0.00'):
            raise serializers.ValidationError("El precio base debe ser mayor o igual a 0")
        return value



class AreaComunListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de áreas comunes
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    esta_disponible = serializers.ReadOnlyField()

    class Meta:
        model = AreaComun
        fields = [
            'id', 'nombre', 'estado', 'precio_base', 'moneda',
            'estado_display', 'esta_disponible'
        ]


class ReservaAreaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para reservas de áreas
    """
    propietario_info = PropietarioSerializer(source='propietario', read_only=True)
    area_info = AreaComunListSerializer(source='area', read_only=True)

    # Campos calculados
    duracion_horas = serializers.ReadOnlyField()
    esta_activa = serializers.ReadOnlyField()
    puede_cancelar = serializers.ReadOnlyField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = ReservaArea
        fields = [
            'id', 'propietario', 'area', 'fecha_inicio', 'fecha_fin',
            'estado', 'precio_total', 'moneda', 'cargo',
            'created_at', 'updated_at',
            # Campos relacionados
            'propietario_info', 'area_info',
            # Campos calculados
            'duracion_horas', 'esta_activa', 'puede_cancelar', 'estado_display'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_fecha_inicio(self, value):
        """Validar fecha de inicio"""
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de inicio no puede ser en el pasado")
        return value

    def validate_fecha_fin(self, value):
        """Validar fecha de fin"""
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de fin no puede ser en el pasado")
        return value

    # def validate_numero_personas(self, value):
    #     """Validar número de personas"""
    #     if value <= 0:
    #         raise serializers.ValidationError("El número de personas debe ser mayor a 0")
    #     return value

    def validate(self, attrs):
        """Validaciones adicionales"""
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        area = attrs.get('area')

        # Validar que fecha_fin sea posterior a fecha_inicio
        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise serializers.ValidationError(
                    "La fecha de fin debe ser posterior a la fecha de inicio"
                )

            # Validar disponibilidad del área
            if area and not area.puede_reservar(fecha_inicio, fecha_fin):
                raise serializers.ValidationError(
                    "El área no está disponible para el periodo solicitado"
                )

        return attrs


class ReservaAreaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear reservas (campos mínimos)
    """
    class Meta:
        model = ReservaArea
        fields = [
            'propietario', 'area', 'fecha_inicio', 'fecha_fin', 'estado'
        ]

    def validate_fecha_inicio(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de inicio no puede ser en el pasado")
        return value

    def validate_fecha_fin(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de fin no puede ser en el pasado")
        return value

    def validate(self, attrs):
        """Validaciones específicas para creación"""
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        area = attrs.get('area')

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio"
            )

        if area and fecha_inicio and fecha_fin:
            if not area.puede_reservar(fecha_inicio, fecha_fin):
                raise serializers.ValidationError(
                    "El área no está disponible para el periodo solicitado"
                )

        return attrs


class ReservaAreaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de reservas
    """
    propietario_nombre = serializers.CharField(source='propietario.user.get_full_name', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    duracion_horas = serializers.ReadOnlyField()

    class Meta:
        model = ReservaArea
        fields = [
            'id', 'fecha_inicio', 'fecha_fin', 'estado', 'precio_total',
            'moneda', 'propietario_nombre', 'area_nombre',
            'estado_display', 'duracion_horas'
        ]


class EstadisticasAreasSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de áreas comunes
    """
    total_areas = serializers.IntegerField()
    areas_disponibles = serializers.IntegerField()
    areas_en_mantenimiento = serializers.IntegerField()
    areas_fuera_servicio = serializers.IntegerField()
    total_reservas = serializers.IntegerField()
    reservas_activas = serializers.IntegerField()
    ingresos_mes_actual = serializers.DecimalField(max_digits=10, decimal_places=2)


class DisponibilidadAreaSerializer(serializers.Serializer):
    """
    Serializer para consultar disponibilidad de un área
    """
    fecha_inicio = serializers.DateTimeField()
    fecha_fin = serializers.DateTimeField()

    def validate_fecha_inicio(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de inicio no puede ser en el pasado")
        return value

    def validate_fecha_fin(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha de fin no puede ser en el pasado")
        return value

    def validate(self, attrs):
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio"
            )

        return attrs