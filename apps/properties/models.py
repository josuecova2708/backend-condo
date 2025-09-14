from django.db import models
from apps.core.models import TimeStampedModel, Bloque
from apps.users.models import User


class UnidadHabitacional(TimeStampedModel):
    """
    Modelo para representar una unidad habitacional (departamento/casa).
    """
    bloque = models.ForeignKey(Bloque, on_delete=models.CASCADE, related_name='unidades')
    numero = models.CharField(max_length=10)
    area_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    num_habitaciones = models.PositiveIntegerField(null=True, blank=True)
    num_banos = models.PositiveIntegerField(null=True, blank=True)
    tiene_parqueadero = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'unidades_habitacionales'
        verbose_name = 'Unidad Habitacional'
        verbose_name_plural = 'Unidades Habitacionales'
        unique_together = ['bloque', 'numero']

    def __str__(self):
        return f"{self.bloque.nombre} - {self.numero}"

    @property
    def direccion_completa(self):
        return f"{self.bloque.condominio.direccion}, Bloque {self.bloque.nombre}, Unidad {self.numero}"


class Propietario(TimeStampedModel):
    """
    Modelo para representar propietarios de unidades habitacionales.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='propiedades_owned')
    unidad = models.ForeignKey(UnidadHabitacional, on_delete=models.CASCADE, related_name='propietarios')
    porcentaje_propiedad = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    documento_propiedad = models.FileField(upload_to='propiedades/documentos/', blank=True, null=True)

    class Meta:
        db_table = 'propietarios'
        verbose_name = 'Propietario'
        verbose_name_plural = 'Propietarios'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.unidad}"


class Residente(TimeStampedModel):
    """
    Modelo para representar residentes que no necesariamente son propietarios.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='residencias')
    unidad = models.ForeignKey(UnidadHabitacional, on_delete=models.CASCADE, related_name='residentes')
    relacion = models.CharField(max_length=50, choices=[
        ('propietario', 'Propietario'),
        ('arrendatario', 'Arrendatario'),
        ('familiar', 'Familiar'),
        ('empleado_domestico', 'Empleado Doméstico'),
        ('otro', 'Otro'),
    ])
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'residentes'
        verbose_name = 'Residente'
        verbose_name_plural = 'Residentes'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.unidad} ({self.relacion})"


class HistorialPropietarios(TimeStampedModel):
    """
    Modelo para mantener un historial de cambios de propietarios.
    """
    unidad = models.ForeignKey(UnidadHabitacional, on_delete=models.CASCADE, related_name='historial_propietarios')
    propietario_anterior = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='historial_ventas')
    propietario_nuevo = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_compras')
    fecha_cambio = models.DateField()
    motivo = models.CharField(max_length=100, choices=[
        ('venta', 'Venta'),
        ('herencia', 'Herencia'),
        ('donacion', 'Donación'),
        ('permuta', 'Permuta'),
        ('otro', 'Otro'),
    ])
    observaciones = models.TextField(blank=True)
    documento_soporte = models.FileField(upload_to='propiedades/historiales/', blank=True, null=True)

    class Meta:
        db_table = 'historial_propietarios'
        verbose_name = 'Historial de Propietarios'
        verbose_name_plural = 'Historiales de Propietarios'

    def __str__(self):
        anterior = self.propietario_anterior.get_full_name() if self.propietario_anterior else "Sin propietario anterior"
        return f"{self.unidad} - {anterior} → {self.propietario_nuevo.get_full_name()}"
