from django.db import models
from django.utils import timezone


class EstadoTarea(models.TextChoices):
    PENDIENTE = 'pendiente', 'Pendiente'
    EN_PROGRESO = 'en_progreso', 'En Progreso'
    COMPLETADA = 'completada', 'Completada'
    CANCELADA = 'cancelada', 'Cancelada'


class TipoTarea(models.TextChoices):
    PREVENTIVO = 'preventivo', 'Preventivo'
    CORRECTIVO = 'correctivo', 'Correctivo'


class TareaMantenimiento(models.Model):
    """
    Modelo para tareas de mantenimiento del condominio
    """
    titulo = models.TextField()
    tipo = models.CharField(max_length=50, choices=TipoTarea.choices, default=TipoTarea.PREVENTIVO)
    descripcion = models.TextField()
    estado = models.CharField(max_length=50, choices=EstadoTarea.choices, default=EstadoTarea.PENDIENTE)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    costo_real = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    programada_para = models.DateTimeField(null=True, blank=True)
    tecnico_nombre = models.CharField(max_length=255, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    fecha_actualizacion = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        db_table = 'tareas_mantenimiento'
        ordering = ['-fecha_creacion']
        verbose_name = 'Tarea de Mantenimiento'
        verbose_name_plural = 'Tareas de Mantenimiento'

    def __str__(self):
        return f"{self.titulo} - {self.get_estado_display()}"

    @property
    def esta_completada(self):
        return self.estado == EstadoTarea.COMPLETADA

    @property
    def puede_completar(self):
        return self.estado in [EstadoTarea.PENDIENTE, EstadoTarea.EN_PROGRESO]

    @property
    def costo_formateado(self):
        if self.costo_real:
            return f"Bs. {self.costo_real:,.2f}"
        elif self.costo_estimado:
            return f"Bs. {self.costo_estimado:,.2f} (estimado)"
        return "Sin costo definido"

    @property
    def dias_desde_creacion(self):
        return (timezone.now() - self.fecha_creacion).days