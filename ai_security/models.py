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


class PersonProfile(TimeStampedModel):
    """
    Modelo para perfiles de personas registradas para reconocimiento facial.
    """
    PERSON_TYPE_CHOICES = [
        ('resident', 'Residente'),
        ('visitor', 'Visitante'),
        ('employee', 'Empleado'),
        ('delivery', 'Delivery'),
        ('unknown', 'Desconocido'),
    ]

    name = models.CharField(max_length=100)
    person_type = models.CharField(max_length=20, choices=PERSON_TYPE_CHOICES)
    face_encoding = models.TextField(help_text="JSON con encoding facial", null=True, blank=True)
    aws_face_id = models.CharField(max_length=100, help_text="AWS Rekognition Face ID", null=True, blank=True)
    photo = models.ImageField(upload_to='faces/')
    is_authorized = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='person_profiles')

    class Meta:
        db_table = 'person_profiles'
        verbose_name = 'Perfil de Persona'
        verbose_name_plural = 'Perfiles de Personas'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_person_type_display()}"


class FacialAccessLog(TimeStampedModel):
    """
    Modelo para registrar logs de acceso facial.
    """
    ACCESS_RESULT_CHOICES = [
        ('autorizado', 'Autorizado'),
        ('denegado', 'Denegado'),
        ('desconocido', 'Desconocido'),
    ]

    person_profile = models.ForeignKey(PersonProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_logs')
    photo = models.ImageField(upload_to='access_logs/')
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    access_granted = models.BooleanField(default=False)
    location = models.CharField(max_length=100, blank=True, default='Entrada Principal')
    timestamp_evento = models.DateTimeField(auto_now_add=True)
    detected_name = models.CharField(max_length=100, blank=True, help_text="Nombre detectado por el sistema")

    class Meta:
        db_table = 'facial_access_logs'
        verbose_name = 'Log de Acceso Facial'
        verbose_name_plural = 'Logs de Acceso Facial'
        ordering = ['-timestamp_evento']

    def __str__(self):
        name = self.detected_name if self.detected_name else 'Desconocido'
        return f"{name} - {self.get_access_result_display()} ({self.timestamp_evento})"

    def get_access_result_display(self):
        if self.access_granted:
            return 'Autorizado'
        elif self.person_profile:
            return 'Denegado'
        else:
            return 'Desconocido'


# ==========================================
# MODELOS PARA DETECCIÓN DE ACTIVIDADES SOSPECHOSAS
# ==========================================

class TipoActividad(models.Model):
    """Tipos de actividades que se pueden detectar"""

    CATEGORIA_CHOICES = [
        ('SOSPECHOSA', 'Actividad Sospechosa'),
        ('ACCIDENTE', 'Accidente Vehicular'),
        ('ANIMAL', 'Animal Suelto'),
    ]

    nombre = models.CharField(max_length=100, unique=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    descripcion = models.TextField(blank=True)
    palabras_clave = models.TextField(
        help_text="Palabras clave separadas por comas para detección en Rekognition"
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tipos_actividad'
        verbose_name = 'Tipo de Actividad'
        verbose_name_plural = 'Tipos de Actividad'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"{self.get_categoria_display()}: {self.nombre}"


class AnalisisVideo(models.Model):
    """Análisis de video realizado con Amazon Rekognition"""

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('COMPLETADO', 'Completado'),
        ('ERROR', 'Error'),
    ]

    # Información del video
    camera_id = models.CharField(max_length=20)
    video_name = models.CharField(max_length=255)
    video_url = models.URLField()

    # Análisis
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')
    job_id = models.CharField(max_length=255, blank=True, help_text="ID del job en Rekognition")

    # Timestamps
    iniciado_at = models.DateTimeField(auto_now_add=True)
    completado_at = models.DateTimeField(null=True, blank=True)

    # Usuario que inició el análisis
    usuario = models.ForeignKey('users.User', on_delete=models.CASCADE)

    # Resultados
    actividades_detectadas = models.IntegerField(default=0)
    confianza_promedio = models.FloatField(null=True, blank=True)

    # Errores
    error_mensaje = models.TextField(blank=True)

    class Meta:
        db_table = 'analisis_videos'
        verbose_name = 'Análisis de Video'
        verbose_name_plural = 'Análisis de Videos'
        ordering = ['-iniciado_at']

    def __str__(self):
        return f"{self.camera_id}/{self.video_name} - {self.get_estado_display()}"


class DeteccionActividad(models.Model):
    """Detección específica de una actividad en un video"""

    analisis = models.ForeignKey(AnalisisVideo, on_delete=models.CASCADE, related_name='detecciones')
    tipo_actividad = models.ForeignKey(TipoActividad, on_delete=models.CASCADE)

    # Detalles de la detección
    timestamp_inicio = models.FloatField(help_text="Segundo del video donde inicia la actividad")
    timestamp_fin = models.FloatField(help_text="Segundo del video donde termina la actividad")
    confianza = models.FloatField(help_text="Nivel de confianza de 0 a 100")

    # Objetos detectados
    objetos_detectados = models.JSONField(default=list, help_text="Lista de objetos detectados")
    bounding_boxes = models.JSONField(default=list, help_text="Coordenadas de los objetos")

    # Estado del aviso
    aviso_generado = models.BooleanField(default=False)
    aviso_id = models.IntegerField(null=True, blank=True, help_text="ID del aviso generado")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'detecciones_actividad'
        verbose_name = 'Detección de Actividad'
        verbose_name_plural = 'Detecciones de Actividad'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tipo_actividad.nombre} - {self.confianza:.1f}% confianza"

    @property
    def duracion_segundos(self):
        """Duración de la actividad detectada en segundos"""
        return self.timestamp_fin - self.timestamp_inicio
