from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import User


class Vehicle(TimeStampedModel):
    """
    Modelo para vehículos registrados en el condominio.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vehiculos')
    placa = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=50, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'vehiculos'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'

    def __str__(self):
        return f"{self.placa} - {self.user.get_full_name()}"


class VehicleAccessLog(TimeStampedModel):
    """
    Modelo para registrar logs de acceso vehicular.
    """
    ACCESS_RESULT_CHOICES = [
        ('autorizado', 'Autorizado'),
        ('denegado', 'Denegado'),
        ('desconocido', 'Desconocido'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_logs')
    placa_detectada = models.CharField(max_length=20, blank=True, default='')
    confianza_ocr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    resultado = models.CharField(max_length=20, choices=ACCESS_RESULT_CHOICES)
    imagen = models.ImageField(upload_to='vehicle_images/', null=True, blank=True)
    timestamp_evento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicle_access_logs'
        verbose_name = 'Log de Acceso Vehicular'
        verbose_name_plural = 'Logs de Acceso Vehicular'
        ordering = ['-timestamp_evento']

    def __str__(self):
        return f"{self.placa_detectada} - {self.resultado} ({self.timestamp_evento})"


class VehicleOCRTrainingData(TimeStampedModel):
    """
    Modelo para almacenar datos de entrenamiento del OCR con correcciones manuales.
    """
    access_log = models.OneToOneField(VehicleAccessLog, on_delete=models.CASCADE, related_name='training_data')
    placa_detectada_original = models.CharField(max_length=20, blank=True, help_text="Placa que detectó el OCR originalmente")
    placa_correcta = models.CharField(max_length=20, help_text="Placa correcta según corrección manual")
    extracted_text_original = models.TextField(blank=True, help_text="Texto extraído por OCR")
    confianza_original = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    usuario_correccion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'vehicle_ocr_training_data'
        verbose_name = 'Dato de Entrenamiento OCR'
        verbose_name_plural = 'Datos de Entrenamiento OCR'
        ordering = ['-created_at']

    def __str__(self):
        return f"Training: {self.placa_detectada_original} -> {self.placa_correcta}"
