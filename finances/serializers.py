from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from .models import Infraccion, Cargo, TipoInfraccion, EstadoInfraccion
from apps.users.serializers import UserBasicSerializer
from apps.properties.serializers import PropietarioSerializer, UnidadHabitacionalSerializer


class InfraccionSerializer(serializers.ModelSerializer):
    """
    Serializer completo para infracciones
    """
    propietario_info = PropietarioSerializer(source='propietario', read_only=True)
    unidad_info = UnidadHabitacionalSerializer(source='unidad', read_only=True)
    reportado_por_info = UserBasicSerializer(source='reportado_por', read_only=True)

    # Campos para la tabla (nombres planos)
    propietario_nombre = serializers.CharField(source='propietario.user.get_full_name', read_only=True)
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)

    # Campos calculados
    puede_aplicar_multa = serializers.ReadOnlyField()
    dias_para_pago = serializers.ReadOnlyField()
    esta_vencida = serializers.ReadOnlyField()
    tipo_infraccion_nombre = serializers.CharField(source='tipo_infraccion.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    # Monto calculado según tipo de infracción (campo del modelo)
    monto_calculado = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tipo_infraccion_monto_base = serializers.DecimalField(source='tipo_infraccion.monto_base', max_digits=10, decimal_places=2, read_only=True)
    tipo_infraccion_monto_reincidencia = serializers.DecimalField(source='tipo_infraccion.monto_reincidencia', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Infraccion
        fields = [
            'id', 'propietario', 'unidad', 'tipo_infraccion', 'descripcion',
            'fecha_infraccion', 'evidencia_url', 'reportado_por', 'monto_multa',
            'fecha_limite_pago', 'estado', 'observaciones_admin', 'es_reincidente',
            'created_at', 'updated_at',
            # Campos relacionados
            'propietario_info', 'unidad_info', 'reportado_por_info',
            # Campos para la tabla
            'propietario_nombre', 'unidad_numero', 'bloque_nombre',
            # Campos calculados
            'puede_aplicar_multa', 'dias_para_pago', 'esta_vencida',
            'tipo_infraccion_nombre', 'estado_display', 'monto_calculado',
            'tipo_infraccion_monto_base', 'tipo_infraccion_monto_reincidencia'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'es_reincidente']

    def validate_fecha_infraccion(self, value):
        """Validar que la fecha de infracción no sea futura"""
        if value > timezone.now():
            raise serializers.ValidationError("La fecha de infracción no puede ser futura")
        return value

    def validate_monto_multa(self, value):
        """Validar monto de multa"""
        if value is not None and value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto de la multa debe ser mayor a 0")
        return value



class InfraccionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear infracciones (campos mínimos)
    """
    class Meta:
        model = Infraccion
        fields = [
            'propietario', 'unidad', 'tipo_infraccion', 'descripcion',
            'fecha_infraccion', 'evidencia_url', 'reportado_por', 'observaciones_admin'
        ]

    def validate_fecha_infraccion(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("La fecha de infracción no puede ser futura")
        return value

    def validate(self, attrs):
        """Validar que el propietario corresponda a la unidad"""
        propietario = attrs.get('propietario')
        unidad = attrs.get('unidad')

        if propietario and unidad:
            if propietario.unidad != unidad:
                raise serializers.ValidationError("El propietario no corresponde a la unidad especificada")

        return attrs


class CargoSerializer(serializers.ModelSerializer):
    """
    Serializer completo para cargos
    """
    propietario_info = PropietarioSerializer(source='propietario', read_only=True)
    unidad_info = UnidadHabitacionalSerializer(source='unidad', read_only=True)
    infraccion_info = InfraccionSerializer(source='infraccion', read_only=True)

    # Campos calculados
    saldo_pendiente = serializers.ReadOnlyField()
    esta_vencido = serializers.ReadOnlyField()
    dias_vencido = serializers.ReadOnlyField()
    interes_mora_calculado = serializers.ReadOnlyField()
    monto_total_con_intereses = serializers.ReadOnlyField()
    tipo_cargo_display = serializers.CharField(source='get_tipo_cargo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Cargo
        fields = [
            'id', 'propietario', 'unidad', 'concepto', 'tipo_cargo', 'monto',
            'moneda', 'fecha_emision', 'fecha_vencimiento', 'estado',
            'es_recurrente', 'periodo', 'infraccion', 'monto_pagado',
            'tasa_interes_mora', 'observaciones', 'created_at', 'updated_at',
            # Campos relacionados
            'propietario_info', 'unidad_info', 'infraccion_info',
            # Campos calculados
            'saldo_pendiente', 'esta_vencido', 'dias_vencido',
            'interes_mora_calculado', 'monto_total_con_intereses',
            'tipo_cargo_display', 'estado_display'
        ]
        read_only_fields = ['id', 'fecha_emision', 'created_at', 'updated_at']

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        return value

    def validate_monto_pagado(self, value):
        if value < Decimal('0.00'):
            raise serializers.ValidationError("El monto pagado no puede ser negativo")
        return value

    def validate_fecha_vencimiento(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("La fecha de vencimiento no puede ser anterior a hoy")
        return value

    def validate_tasa_interes_mora(self, value):
        if value < Decimal('0.00') or value > Decimal('100.00'):
            raise serializers.ValidationError("La tasa de interés debe estar entre 0% y 100%")
        return value


class CargoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear cargos
    """
    class Meta:
        model = Cargo
        fields = [
            'propietario', 'unidad', 'concepto', 'tipo_cargo', 'monto',
            'moneda', 'fecha_vencimiento', 'es_recurrente', 'periodo',
            'tasa_interes_mora', 'observaciones'
        ]

    def validate_monto(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        return value

    def validate_fecha_vencimiento(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("La fecha de vencimiento no puede ser anterior a hoy")
        return value


class TipoInfraccionSerializer(serializers.ModelSerializer):
    """
    Serializer para tipos de infracciones dinámicos
    """
    diferencia_reincidencia = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TipoInfraccion
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'monto_base', 'monto_reincidencia',
            'dias_para_pago', 'es_activo', 'orden', 'created_at', 'updated_at',
            'diferencia_reincidencia'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_diferencia_reincidencia(self, obj):
        """Calcula la diferencia entre monto de reincidencia y base"""
        diferencia = obj.monto_reincidencia - obj.monto_base
        porcentaje = (diferencia / obj.monto_base * 100) if obj.monto_base > 0 else 0
        return {
            'diferencia': diferencia,
            'porcentaje': round(porcentaje, 1)
        }

    def validate_monto_base(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto base debe ser mayor a 0")
        return value

    def validate_monto_reincidencia(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto de reincidencia debe ser mayor a 0")
        return value

    def validate_dias_para_pago(self, value):
        if value <= 0:
            raise serializers.ValidationError("Los días para pago deben ser mayor a 0")
        return value

    def validate_codigo(self, value):
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("El código solo puede contener letras, números, guiones y guiones bajos")
        return value

    def validate(self, attrs):
        """Validar que el monto de reincidencia sea mayor o igual al base"""
        monto_base = attrs.get('monto_base')
        monto_reincidencia = attrs.get('monto_reincidencia')

        if monto_base and monto_reincidencia and monto_reincidencia < monto_base:
            raise serializers.ValidationError(
                "El monto de reincidencia debe ser mayor o igual al monto base"
            )

        return attrs


class AplicarMultaSerializer(serializers.Serializer):
    """
    Serializer para aplicar multa a una infracción
    """
    infraccion_id = serializers.IntegerField()
    monto_personalizado = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    observaciones_admin = serializers.CharField(required=False, allow_blank=True)

    def validate_monto_personalizado(self, value):
        if value is not None and value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto personalizado debe ser mayor a 0")
        return value

    def validate_infraccion_id(self, value):
        try:
            infraccion = Infraccion.objects.get(id=value)
            if infraccion.estado != EstadoInfraccion.CONFIRMADA:
                raise serializers.ValidationError("Solo se pueden aplicar multas a infracciones confirmadas")
            if infraccion.monto_multa:
                raise serializers.ValidationError("Esta infracción ya tiene una multa aplicada")
        except Infraccion.DoesNotExist:
            raise serializers.ValidationError("La infracción especificada no existe")
        return value


class ProcesarPagoSerializer(serializers.Serializer):
    """
    Serializer para procesar pagos de cargos
    """
    cargo_id = serializers.IntegerField()
    monto_pago = serializers.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = serializers.CharField(max_length=50, required=False, default='efectivo')
    observaciones = serializers.CharField(required=False, allow_blank=True)

    def validate_monto_pago(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto del pago debe ser mayor a 0")
        return value

    def validate_cargo_id(self, value):
        try:
            cargo = Cargo.objects.get(id=value)
            if cargo.estado == 'pagado':
                raise serializers.ValidationError("Este cargo ya está completamente pagado")
        except Cargo.DoesNotExist:
            raise serializers.ValidationError("El cargo especificado no existe")
        return value


class EstadisticasInfraccionesSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de infracciones
    """
    total_infracciones = serializers.IntegerField()
    registradas = serializers.IntegerField()
    confirmadas = serializers.IntegerField()
    rechazadas = serializers.IntegerField()
    multas_aplicadas = serializers.IntegerField()
    multas_pagadas = serializers.IntegerField()
    por_tipo = serializers.DictField()


class InfraccionListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de infracciones
    """
    propietario_nombre = serializers.CharField(source='propietario.user.get_full_name', read_only=True)
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)
    tipo_infraccion_nombre = serializers.CharField(source='tipo_infraccion.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    dias_para_pago = serializers.ReadOnlyField()
    monto_calculado = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Infraccion
        fields = [
            'id', 'tipo_infraccion', 'descripcion', 'fecha_infraccion', 'estado',
            'monto_multa', 'monto_calculado', 'fecha_limite_pago', 'es_reincidente',
            'propietario_nombre', 'unidad_numero', 'bloque_nombre',
            'tipo_infraccion_nombre', 'estado_display', 'dias_para_pago'
        ]


class CargoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de cargos
    """
    propietario_nombre = serializers.CharField(source='propietario.user.get_full_name', read_only=True)
    unidad_numero = serializers.CharField(source='unidad.numero', read_only=True)
    bloque_nombre = serializers.CharField(source='unidad.bloque.nombre', read_only=True)
    tipo_cargo_display = serializers.CharField(source='get_tipo_cargo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    saldo_pendiente = serializers.ReadOnlyField()
    esta_vencido = serializers.ReadOnlyField()
    dias_vencido = serializers.ReadOnlyField()

    class Meta:
        model = Cargo
        fields = [
            'id', 'concepto', 'tipo_cargo', 'monto', 'moneda',
            'fecha_emision', 'fecha_vencimiento', 'estado', 'monto_pagado',
            'propietario_nombre', 'unidad_numero', 'bloque_nombre',
            'tipo_cargo_display', 'estado_display', 'saldo_pendiente',
            'esta_vencido', 'dias_vencido'
        ]