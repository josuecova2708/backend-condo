from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Base model that provides created_at and updated_at timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Condominio(TimeStampedModel):
    """
    Modelo para representar un condominio.
    """
    nombre = models.CharField(max_length=255)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nit = models.CharField(max_length=20, unique=True)
    logo = models.ImageField(upload_to='condominios/logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'condominios'
        verbose_name = 'Condominio'
        verbose_name_plural = 'Condominios'

    def __str__(self):
        return self.nombre


class Bloque(TimeStampedModel):
    """
    Modelo para representar los bloques dentro de un condominio.
    """
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='bloques')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'bloques'
        verbose_name = 'Bloque'
        verbose_name_plural = 'Bloques'
        unique_together = ['condominio', 'nombre']

    def __str__(self):
        return f"{self.condominio.nombre} - {self.nombre}"


class ConfiguracionSistema(TimeStampedModel):
    """
    Modelo para configuraciones del sistema.
    """
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=50, choices=[
        ('string', 'Texto'),
        ('integer', 'Número entero'),
        ('float', 'Número decimal'),
        ('boolean', 'Booleano'),
        ('json', 'JSON'),
    ], default='string')

    class Meta:
        db_table = 'configuraciones_sistema'
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuraciones del Sistema'

    def __str__(self):
        return f"{self.clave}: {self.valor}"

