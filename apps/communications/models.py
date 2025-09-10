from django.db import models
from apps.core.models import TimeStampedModel, Condominio
from apps.users.models import User


class AvisoComunicado(TimeStampedModel):
    """
    Modelo para avisos y comunicados del condominio.
    """
    titulo = models.CharField(max_length=255)
    contenido = models.TextField()
    tipo = models.CharField(max_length=50, choices=[
        ('aviso', 'Aviso'),
        ('comunicado', 'Comunicado'),
        ('noticia', 'Noticia'),
        ('urgente', 'Urgente'),
        ('mantenimiento', 'Mantenimiento'),
    ])
    prioridad = models.CharField(max_length=20, choices=[
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ], default='media')
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name='avisos')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avisos_creados')
    fecha_publicacion = models.DateTimeField()
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    archivo_adjunto = models.FileField(upload_to='avisos/adjuntos/', blank=True, null=True)
    imagen = models.ImageField(upload_to='avisos/imagenes/', blank=True, null=True)

    class Meta:
        db_table = 'avisos_comunicados'
        verbose_name = 'Aviso/Comunicado'
        verbose_name_plural = 'Avisos/Comunicados'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"{self.titulo} - {self.condominio.nombre}"

    @property
    def is_expired(self):
        """
        Verifica si el aviso ha expirado.
        """
        if not self.fecha_expiracion:
            return False
        from django.utils import timezone
        return timezone.now() > self.fecha_expiracion


class LecturaAviso(TimeStampedModel):
    """
    Modelo para registrar qué usuarios han leído cada aviso.
    """
    aviso = models.ForeignKey(AvisoComunicado, on_delete=models.CASCADE, related_name='lecturas')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avisos_leidos')
    fecha_lectura = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'lectura_avisos'
        unique_together = ['aviso', 'user']
        verbose_name = 'Lectura de Aviso'
        verbose_name_plural = 'Lecturas de Avisos'

    def __str__(self):
        return f"{self.user.username} leyó: {self.aviso.titulo}"
