from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.core.models import TimeStampedModel
from apps.properties.models import Propietario


class EstadoAreaComun(models.TextChoices):
    """Estados posibles para un área común"""
    DISPONIBLE = 'disponible', 'Disponible'
    MANTENIMIENTO = 'mantenimiento', 'En Mantenimiento'
    FUERA_DE_SERVICIO = 'fuera_de_servicio', 'Fuera de Servicio'
    RESERVADO = 'reservado', 'Reservado'


class EstadoReserva(models.TextChoices):
    """Estados posibles para una reserva"""
    PENDIENTE = 'pendiente', 'Pendiente'
    CONFIRMADA = 'confirmada', 'Confirmada'
    CANCELADA = 'cancelada', 'Cancelada'


class AreaComun(TimeStampedModel):
    """
    Modelo para áreas comunes del condominio
    """
    nombre = models.TextField(
        help_text="Nombre del área común"
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoAreaComun.choices,
        default=EstadoAreaComun.DISPONIBLE,
        help_text="Estado actual del área común"
    )
    precio_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text="Precio base por hora/uso del área"
    )
    moneda = models.CharField(
        max_length=3,
        default='BOB',  # Bolivianos
        help_text="Moneda del precio (BOB=Bolivianos, USD=Dólares)"
    )

    # Override TimeStampedModel fields to map to existing database columns
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        db_table = 'areas_comunes'
        verbose_name = 'Área Común'
        verbose_name_plural = 'Áreas Comunes'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"

    @property
    def esta_disponible(self):
        """Verifica si el área está disponible para reservas"""
        return self.estado == EstadoAreaComun.DISPONIBLE

    def puede_reservar(self, fecha_inicio, fecha_fin):
        """
        Verifica si el área puede ser reservada en el periodo especificado
        """
        if not self.esta_disponible:
            return False

        # Verificar que no hay reservas confirmadas en el mismo periodo
        reservas_conflictivas = ReservaArea.objects.filter(
            area=self,
            estado__in=[EstadoReserva.CONFIRMADA],
            fecha_inicio__lt=fecha_fin,
            fecha_fin__gt=fecha_inicio
        )

        return not reservas_conflictivas.exists()


class ReservaArea(TimeStampedModel):
    """
    Modelo para reservas de áreas comunes
    """
    propietario = models.ForeignKey(
        Propietario,
        on_delete=models.CASCADE,
        related_name='reservas_areas',
        db_column='id_propietario',
        help_text="Propietario que realiza la reserva"
    )
    area = models.ForeignKey(
        AreaComun,
        on_delete=models.CASCADE,
        related_name='reservas',
        db_column='id_area',
        help_text="Área común reservada"
    )
    fecha_inicio = models.DateTimeField(
        help_text="Fecha y hora de inicio de la reserva"
    )
    fecha_fin = models.DateTimeField(
        help_text="Fecha y hora de fin de la reserva"
    )
    estado = models.CharField(
        max_length=15,
        choices=EstadoReserva.choices,
        default=EstadoReserva.PENDIENTE,
        help_text="Estado actual de la reserva"
    )
    precio_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Precio total de la reserva"
    )
    moneda = models.CharField(
        max_length=3,
        default='BOB',
        help_text="Moneda del precio"
    )
    cargo = models.ForeignKey(
        'finances.Cargo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas_area',
        db_column='id_cargo',
        help_text="Cargo financiero asociado (si aplica)"
    )
    # observaciones = models.TextField(
    #     blank=True,
    #     help_text="Observaciones adicionales de la reserva"
    # )
    # numero_personas = models.PositiveIntegerField(
    #     default=1,
    #     help_text="Número de personas para la reserva"
    # )

    # Override TimeStampedModel fields to map to existing database columns
    created_at = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    updated_at = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        db_table = 'reservas_area'
        verbose_name = 'Reserva de Área'
        verbose_name_plural = 'Reservas de Áreas'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.area.nombre} - {self.propietario.user.get_full_name()} - {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')}"

    @property
    def duracion_horas(self):
        """Calcula la duración de la reserva en horas"""
        if self.fecha_inicio and self.fecha_fin:
            delta = self.fecha_fin - self.fecha_inicio
            return delta.total_seconds() / 3600
        return 0

    @property
    def esta_activa(self):
        """Verifica si la reserva está activa (confirmada)"""
        return self.estado == EstadoReserva.CONFIRMADA

    @property
    def puede_cancelar(self):
        """Verifica si la reserva puede ser cancelada"""
        return self.estado in [EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA]

    def calcular_precio_total(self):
        """
        Calcula el precio total basado en la duración y precio base del área
        """
        if self.area and self.fecha_inicio and self.fecha_fin:
            horas = self.duracion_horas
            return self.area.precio_base * Decimal(str(horas))
        return Decimal('0.00')

    def save(self, *args, **kwargs):
        # Auto-calcular precio si no está establecido
        if not self.precio_total:
            self.precio_total = self.calcular_precio_total()

        # Establecer moneda igual al área si no está establecida
        if not self.moneda and self.area:
            self.moneda = self.area.moneda

        super().save(*args, **kwargs)
