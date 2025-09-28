from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import datetime, timedelta
from apps.core.models import TimeStampedModel
from apps.users.models import User
from apps.properties.models import UnidadHabitacional


class TipoInfraccion(TimeStampedModel):
    """
    Modelo dinámico para tipos de infracciones
    """
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único para el tipo de infracción (ej: 'ruido_excesivo')"
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo del tipo de infracción"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción detallada del tipo de infracción"
    )
    monto_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto base para primera infracción"
    )
    monto_reincidencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto para casos de reincidencia"
    )
    dias_para_pago = models.PositiveIntegerField(
        default=15,
        help_text="Días para pagar la multa desde su aplicación"
    )
    es_activo = models.BooleanField(
        default=True,
        help_text="Si este tipo de infracción está activo"
    )
    orden = models.PositiveIntegerField(
        default=0,
        help_text="Orden de visualización"
    )

    class Meta:
        db_table = 'tipos_infraccion'
        verbose_name = 'Tipo de Infracción'
        verbose_name_plural = 'Tipos de Infracción'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class EstadoInfraccion(models.TextChoices):
    REGISTRADA = 'registrada', 'Registrada'
    EN_REVISION = 'en_revision', 'En Revisión'
    CONFIRMADA = 'confirmada', 'Confirmada'
    RECHAZADA = 'rechazada', 'Rechazada'
    MULTA_APLICADA = 'multa_aplicada', 'Multa Aplicada'
    PAGADA = 'pagada', 'Pagada'


class TipoCargo(models.TextChoices):
    CUOTA_MENSUAL = 'cuota_mensual', 'Cuota Mensual'
    EXPENSA_EXTRAORDINARIA = 'expensa_extraordinaria', 'Expensa Extraordinaria'
    MULTA = 'multa', 'Multa'
    INTERES_MORA = 'interes_mora', 'Interés por Mora'
    OTROS = 'otros', 'Otros'


class EstadoCargo(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    PARCIALMENTE_PAGADO = 'parcialmente_pagado', 'Parcialmente Pagado'
    PAGADO = 'pagado', 'Pagado'
    VENCIDO = 'vencido', 'Vencido'
    CANCELADO = 'cancelado', 'Cancelado'


class Infraccion(TimeStampedModel):
    """
    Modelo extendido para infracciones con campos adicionales para CICLO 2
    """
    propietario = models.ForeignKey(
        'properties.Propietario',
        on_delete=models.CASCADE,
        related_name='infracciones',
        db_column='id_propietario',
        help_text="Propietario responsable de la infracción"
    )
    unidad = models.ForeignKey(
        UnidadHabitacional,
        on_delete=models.CASCADE,
        related_name='infracciones',
        db_column='unidad',
        help_text="Unidad habitacional donde ocurrió la infracción"
    )

    # Campo FK definitivo
    tipo_infraccion = models.ForeignKey(
        TipoInfraccion,
        on_delete=models.CASCADE,
        related_name='infracciones',
        help_text="Tipo de infracción"
    )
    descripcion = models.TextField(
        help_text="Descripción detallada de la infracción"
    )
    fecha_infraccion = models.DateTimeField(
        help_text="Fecha y hora cuando ocurrió la infracción"
    )
    evidencia_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL de evidencia (fotos, videos, documentos)"
    )

    # Campos nuevos para CICLO 2
    reportado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='infracciones_reportadas',
        db_column='reportado_por',
        help_text="Usuario que reportó la infracción"
    )
    monto_multa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Monto de la multa aplicada (si corresponde)"
    )
    fecha_limite_pago = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha límite para pagar la multa"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoInfraccion.choices,
        default=EstadoInfraccion.REGISTRADA,
        help_text="Estado actual de la infracción"
    )
    observaciones_admin = models.TextField(
        blank=True,
        help_text="Observaciones del administrador"
    )
    es_reincidente = models.BooleanField(
        default=False,
        help_text="Si el propietario es reincidente en este tipo de infracción"
    )
    monto_calculado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Monto calculado automáticamente según el tipo de infracción y reincidencia"
    )

    # Override TimeStampedModel fields to map to existing database columns
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        db_table = 'infracciones'
        verbose_name = 'Infracción'
        verbose_name_plural = 'Infracciones'
        ordering = ['-fecha_infraccion']

    def __str__(self):
        return f"{self.tipo_infraccion.nombre} - {self.propietario.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Auto-calcular reincidencia
        if not self.pk:
            infracciones_anteriores = Infraccion.objects.filter(
                propietario=self.propietario,
                tipo_infraccion=self.tipo_infraccion,
                estado__in=[EstadoInfraccion.CONFIRMADA, EstadoInfraccion.MULTA_APLICADA, EstadoInfraccion.PAGADA]
            ).count()
            self.es_reincidente = infracciones_anteriores > 0

        # Auto-calcular monto según tipo de infracción y reincidencia
        if self.tipo_infraccion and not self.monto_calculado:
            if self.es_reincidente:
                self.monto_calculado = self.tipo_infraccion.monto_reincidencia
            else:
                self.monto_calculado = self.tipo_infraccion.monto_base

        super().save(*args, **kwargs)

    @property
    def puede_aplicar_multa(self):
        """Verifica si se puede aplicar multa a esta infracción"""
        return self.estado == EstadoInfraccion.CONFIRMADA and not self.monto_multa

    @property
    def dias_para_pago(self):
        """Calcula días restantes para pago de multa"""
        if self.fecha_limite_pago:
            delta = self.fecha_limite_pago - datetime.now().date()
            return max(0, delta.days)
        return None

    @property
    def esta_vencida(self):
        """Verifica si la multa está vencida"""
        if self.fecha_limite_pago and self.estado == EstadoInfraccion.MULTA_APLICADA:
            return datetime.now().date() > self.fecha_limite_pago
        return False


class Cargo(models.Model):
    """
    Modelo extendido para cargos con campos adicionales para CICLO 2
    """
    # Campos de timestamp que coinciden con la base de datos existente
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    propietario = models.ForeignKey(
        'properties.Propietario',
        on_delete=models.CASCADE,
        related_name='cargos',
        db_column='id_propietario',
        help_text="Propietario al que se le aplica el cargo"
    )
    unidad = models.ForeignKey(
        UnidadHabitacional,
        on_delete=models.CASCADE,
        related_name='cargos',
        db_column='unidad_id',
        help_text="Unidad habitacional asociada al cargo"
    )

    # Campos existentes extendidos
    concepto = models.TextField(
        help_text="Descripción del concepto del cargo"
    )
    tipo_cargo = models.CharField(
        max_length=30,
        choices=TipoCargo.choices,
        default=TipoCargo.CUOTA_MENSUAL,
        help_text="Tipo específico de cargo"
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto del cargo"
    )
    moneda = models.CharField(
        max_length=3,
        default='BOB',
        help_text="Moneda del cargo (BOB, USD, etc.)"
    )
    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de emisión del cargo"
    )
    fecha_vencimiento = models.DateField(
        help_text="Fecha límite de pago"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoCargo.choices,
        default=EstadoCargo.PENDIENTE,
        help_text="Estado actual del cargo"
    )

    # Campos nuevos para CICLO 2
    es_recurrente = models.BooleanField(
        default=False,
        help_text="Si es un cargo que se repite mensualmente"
    )
    periodo = models.CharField(
        max_length=20,
        blank=True,
        help_text="Período al que corresponde (ej: 'Enero 2024')"
    )
    infraccion = models.ForeignKey(
        Infraccion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cargos_multa',
        help_text="Infracción que generó este cargo (si es una multa)"
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto total pagado"
    )
    tasa_interes_mora = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Tasa de interés por mora (% mensual)"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )

    class Meta:
        db_table = 'cargos'
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"{self.get_tipo_cargo_display()} - {self.propietario.user.get_full_name()} - {self.monto}"

    @property
    def saldo_pendiente(self):
        """Calcula el saldo pendiente de pago"""
        return self.monto - self.monto_pagado

    @property
    def esta_vencido(self):
        """Verifica si el cargo está vencido"""
        return datetime.now().date() > self.fecha_vencimiento and self.estado != EstadoCargo.PAGADO

    @property
    def dias_vencido(self):
        """Calcula días de vencimiento"""
        if self.esta_vencido:
            delta = datetime.now().date() - self.fecha_vencimiento
            return delta.days
        return 0

    @property
    def interes_mora_calculado(self):
        """Calcula el interés por mora acumulado"""
        if not self.esta_vencido or self.estado == EstadoCargo.PAGADO:
            return Decimal('0.00')

        dias_mora = self.dias_vencido
        if dias_mora <= 0:
            return Decimal('0.00')

        # Calcular interés mensual proporcional
        meses_mora = Decimal(dias_mora) / Decimal('30')
        interes = self.saldo_pendiente * (self.tasa_interes_mora / Decimal('100')) * meses_mora
        return round(interes, 2)

    @property
    def monto_total_con_intereses(self):
        """Calcula el monto total incluyendo intereses por mora"""
        return self.saldo_pendiente + self.interes_mora_calculado

    def aplicar_pago(self, monto_pago):
        """Aplica un pago al cargo y actualiza el estado"""
        if monto_pago <= 0:
            raise ValueError("El monto del pago debe ser mayor a 0")

        if monto_pago > self.monto_total_con_intereses:
            raise ValueError("El monto del pago no puede ser mayor al saldo total")

        self.monto_pagado += monto_pago

        if self.monto_pagado >= self.monto:
            self.estado = EstadoCargo.PAGADO
        else:
            self.estado = EstadoCargo.PARCIALMENTE_PAGADO

        self.save()

    def generar_cargo_interes_mora(self):
        """Genera un cargo adicional por intereses de mora si corresponde"""
        interes = self.interes_mora_calculado
        if interes > Decimal('0.00'):
            cargo_interes = Cargo.objects.create(
                propietario=self.propietario,
                unidad=self.unidad,
                concepto=f"Interés por mora - {self.concepto}",
                tipo_cargo=TipoCargo.INTERES_MORA,
                monto=interes,
                moneda=self.moneda,
                fecha_vencimiento=self.fecha_vencimiento + timedelta(days=30),
                observaciones=f"Cargo por mora generado automáticamente. Cargo original: {self.id}"
            )
            return cargo_interes
        return None


# NOTA: ConfiguracionMultas será reemplazado por TipoInfraccion
# Mantenemos temporalmente para migración
# class ConfiguracionMultas(TimeStampedModel):
#     """
#     Configuración global para el sistema de multas - DEPRECADO
#     """
#     pass
