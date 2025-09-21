from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Infraccion, Cargo, ConfiguracionMultas


@admin.register(Infraccion)
class InfraccionAdmin(admin.ModelAdmin):
    """
    Administración de infracciones en Django Admin
    """
    list_display = [
        'id', 'tipo_infraccion', 'propietario_nombre', 'unidad_info',
        'fecha_infraccion', 'estado', 'monto_multa', 'es_reincidente',
        'esta_vencida_display'
    ]
    list_filter = [
        'estado', 'tipo_infraccion', 'es_reincidente',
        'fecha_infraccion', 'fecha_limite_pago'
    ]
    search_fields = [
        'descripcion', 'propietario__user__first_name',
        'propietario__user__last_name', 'unidad__numero'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'es_reincidente',
        'puede_aplicar_multa', 'dias_para_pago', 'esta_vencida'
    ]
    fieldsets = (
        ('Información Básica', {
            'fields': ('propietario', 'unidad', 'tipo_infraccion', 'descripcion')
        }),
        ('Detalles de la Infracción', {
            'fields': ('fecha_infraccion', 'evidencia_url', 'reportado_por')
        }),
        ('Multa y Estado', {
            'fields': ('estado', 'monto_multa', 'fecha_limite_pago', 'observaciones_admin')
        }),
        ('Información Automática', {
            'fields': ('es_reincidente', 'puede_aplicar_multa', 'dias_para_pago', 'esta_vencida'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def propietario_nombre(self, obj):
        return obj.propietario.user.get_full_name()
    propietario_nombre.short_description = 'Propietario'

    def unidad_info(self, obj):
        return f"{obj.unidad.bloque.nombre} - {obj.unidad.numero}"
    unidad_info.short_description = 'Unidad'

    def esta_vencida_display(self, obj):
        if obj.esta_vencida:
            return format_html('<span style="color: red;">Vencida</span>')
        elif obj.fecha_limite_pago:
            return format_html('<span style="color: orange;">Vigente</span>')
        return '-'
    esta_vencida_display.short_description = 'Estado Pago'

    actions = ['confirmar_infracciones', 'rechazar_infracciones']

    def confirmar_infracciones(self, request, queryset):
        count = 0
        for infraccion in queryset:
            if infraccion.estado == 'registrada':
                infraccion.estado = 'confirmada'
                infraccion.save()
                count += 1
        self.message_user(request, f'{count} infracciones confirmadas.')
    confirmar_infracciones.short_description = "Confirmar infracciones seleccionadas"

    def rechazar_infracciones(self, request, queryset):
        count = 0
        for infraccion in queryset:
            if infraccion.estado in ['registrada', 'en_revision']:
                infraccion.estado = 'rechazada'
                infraccion.observaciones_admin = 'Rechazada desde administración'
                infraccion.save()
                count += 1
        self.message_user(request, f'{count} infracciones rechazadas.')
    rechazar_infracciones.short_description = "Rechazar infracciones seleccionadas"


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    """
    Administración de cargos en Django Admin
    """
    list_display = [
        'id', 'tipo_cargo', 'propietario_nombre', 'unidad_info',
        'monto', 'monto_pagado', 'saldo_pendiente_display',
        'fecha_vencimiento', 'estado', 'esta_vencido_display'
    ]
    list_filter = [
        'tipo_cargo', 'estado', 'es_recurrente', 'moneda',
        'fecha_emision', 'fecha_vencimiento'
    ]
    search_fields = [
        'concepto', 'propietario__user__first_name',
        'propietario__user__last_name', 'unidad__numero'
    ]
    readonly_fields = [
        'id', 'fecha_emision', 'created_at', 'updated_at',
        'saldo_pendiente', 'esta_vencido', 'dias_vencido',
        'interes_mora_calculado', 'monto_total_con_intereses'
    ]
    fieldsets = (
        ('Información Básica', {
            'fields': ('propietario', 'unidad', 'concepto', 'tipo_cargo')
        }),
        ('Montos y Fechas', {
            'fields': ('monto', 'moneda', 'fecha_vencimiento', 'monto_pagado')
        }),
        ('Configuración', {
            'fields': ('estado', 'es_recurrente', 'periodo', 'tasa_interes_mora')
        }),
        ('Relaciones', {
            'fields': ('infraccion', 'observaciones')
        }),
        ('Cálculos Automáticos', {
            'fields': (
                'saldo_pendiente', 'esta_vencido', 'dias_vencido',
                'interes_mora_calculado', 'monto_total_con_intereses'
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('id', 'fecha_emision', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def propietario_nombre(self, obj):
        return obj.propietario.user.get_full_name()
    propietario_nombre.short_description = 'Propietario'

    def unidad_info(self, obj):
        return f"{obj.unidad.bloque.nombre} - {obj.unidad.numero}"
    unidad_info.short_description = 'Unidad'

    def saldo_pendiente_display(self, obj):
        saldo = obj.saldo_pendiente
        if saldo > 0:
            color = 'red' if obj.esta_vencido else 'orange'
            return format_html(f'<span style="color: {color};">{saldo}</span>')
        return format_html('<span style="color: green;">0.00</span>')
    saldo_pendiente_display.short_description = 'Saldo Pendiente'

    def esta_vencido_display(self, obj):
        if obj.esta_vencido:
            return format_html(
                '<span style="color: red;">Vencido ({} días)</span>',
                obj.dias_vencido
            )
        return format_html('<span style="color: green;">Al día</span>')
    esta_vencido_display.short_description = 'Estado'

    actions = ['marcar_como_pagado', 'generar_interes_mora']

    def marcar_como_pagado(self, request, queryset):
        count = 0
        for cargo in queryset:
            if cargo.estado != 'pagado':
                cargo.monto_pagado = cargo.monto
                cargo.estado = 'pagado'
                cargo.save()
                count += 1
        self.message_user(request, f'{count} cargos marcados como pagados.')
    marcar_como_pagado.short_description = "Marcar como pagado"

    def generar_interes_mora(self, request, queryset):
        count = 0
        for cargo in queryset:
            if cargo.esta_vencido and cargo.interes_mora_calculado > 0:
                cargo_interes = cargo.generar_cargo_interes_mora()
                if cargo_interes:
                    count += 1
        self.message_user(request, f'{count} cargos por intereses de mora generados.')
    generar_interes_mora.short_description = "Generar intereses de mora"


@admin.register(ConfiguracionMultas)
class ConfiguracionMultasAdmin(admin.ModelAdmin):
    """
    Administración de configuraciones de multas
    """
    list_display = [
        'tipo_infraccion', 'monto_base', 'monto_reincidencia',
        'dias_para_pago', 'es_activa', 'diferencia_reincidencia'
    ]
    list_filter = ['es_activa', 'tipo_infraccion']
    search_fields = ['descripcion']
    readonly_fields = ['id', 'created_at', 'updated_at', 'diferencia_reincidencia']

    fieldsets = (
        ('Configuración de Multa', {
            'fields': ('tipo_infraccion', 'descripcion', 'es_activa')
        }),
        ('Montos', {
            'fields': ('monto_base', 'monto_reincidencia', 'diferencia_reincidencia')
        }),
        ('Términos', {
            'fields': ('dias_para_pago',)
        }),
        ('Auditoría', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def diferencia_reincidencia(self, obj):
        diferencia = obj.monto_reincidencia - obj.monto_base
        porcentaje = (diferencia / obj.monto_base * 100) if obj.monto_base > 0 else 0
        return f"{diferencia:.2f} ({porcentaje:.1f}% más)"
    diferencia_reincidencia.short_description = 'Diferencia Reincidencia'

    actions = ['activar_configuraciones', 'desactivar_configuraciones']

    def activar_configuraciones(self, request, queryset):
        count = queryset.update(es_activa=True)
        self.message_user(request, f'{count} configuraciones activadas.')
    activar_configuraciones.short_description = "Activar configuraciones"

    def desactivar_configuraciones(self, request, queryset):
        count = queryset.update(es_activa=False)
        self.message_user(request, f'{count} configuraciones desactivadas.')
    desactivar_configuraciones.short_description = "Desactivar configuraciones"
