from django.contrib import admin
from .models import AreaComun, ReservaArea


@admin.register(AreaComun)
class AreaComunAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'estado', 'precio_base', 'moneda', 'created_at'
    ]
    list_filter = ['estado', 'moneda', 'created_at']
    search_fields = ['nombre']
    ordering = ['nombre']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'estado')
        }),
        ('Configuración de Precios', {
            'fields': ('precio_base', 'moneda')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReservaArea)
class ReservaAreaAdmin(admin.ModelAdmin):
    list_display = [
        'area', 'propietario', 'fecha_inicio', 'fecha_fin',
        'estado', 'precio_total', 'created_at'
    ]
    list_filter = ['estado', 'area', 'moneda', 'created_at']
    search_fields = [
        'area__nombre',
        'propietario__user__first_name',
        'propietario__user__last_name'
    ]
    ordering = ['-fecha_inicio']
    readonly_fields = ['created_at', 'updated_at', 'duracion_horas']

    fieldsets = (
        ('Información de la Reserva', {
            'fields': ('area', 'propietario', 'estado')
        }),
        ('Fechas y Duración', {
            'fields': (
                'fecha_inicio',
                'fecha_fin',
                'duracion_horas'
            )
        }),
        # ('Detalles de la Reserva', {
        #     'fields': (
        #         'numero_personas',
        #         'observaciones'
        #     )
        # }),
        ('Información Financiera', {
            'fields': ('precio_total', 'moneda', 'cargo')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def duracion_horas(self, obj):
        """Muestra la duración en horas en el admin"""
        return f"{obj.duracion_horas:.2f} horas"
    duracion_horas.short_description = "Duración"
