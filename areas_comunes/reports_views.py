from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import Extract, TruncDate, TruncMonth, TruncWeek
from django.utils import timezone
from datetime import datetime, timedelta
from .models import ReservaArea, AreaComun, EstadoReserva


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ingresos_por_area(request):
    """
    Reporte de ingresos por área común - Total y promedio
    """
    # Solo reservas confirmadas para calcular ingresos reales
    reservas_confirmadas = ReservaArea.objects.filter(estado=EstadoReserva.CONFIRMADA)

    ingresos_por_area = reservas_confirmadas.values(
        'area__id', 'area__nombre'
    ).annotate(
        total_ingresos=Sum('precio_total'),
        total_reservas=Count('id'),
        promedio_por_reserva=Avg('precio_total')
    ).order_by('-total_ingresos')

    # Calcular totales generales
    total_general = reservas_confirmadas.aggregate(
        total=Sum('precio_total'),
        reservas=Count('id')
    )

    return Response({
        'ingresos_por_area': list(ingresos_por_area),
        'total_general': total_general['total'] or 0,
        'total_reservas': total_general['reservas'] or 0,
        'promedio_general': total_general['total'] / total_general['reservas'] if total_general['reservas'] else 0
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ingresos_por_periodo(request):
    """
    Reporte de ingresos por período con comparaciones temporales
    """
    periodo = request.GET.get('periodo', 'mes')  # mes, semana, dia
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # Filtros de fecha
    queryset = ReservaArea.objects.filter(estado=EstadoReserva.CONFIRMADA)

    if fecha_inicio:
        queryset = queryset.filter(fecha_inicio__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_inicio__lte=fecha_fin)

    # Agrupar según el período seleccionado
    if periodo == 'mes':
        agrupacion = queryset.annotate(
            periodo=TruncMonth('fecha_inicio')
        ).values('periodo').annotate(
            total_ingresos=Sum('precio_total'),
            total_reservas=Count('id')
        ).order_by('periodo')
    elif periodo == 'semana':
        agrupacion = queryset.annotate(
            periodo=TruncWeek('fecha_inicio')
        ).values('periodo').annotate(
            total_ingresos=Sum('precio_total'),
            total_reservas=Count('id')
        ).order_by('periodo')
    else:  # día
        agrupacion = queryset.annotate(
            periodo=TruncDate('fecha_inicio')
        ).values('periodo').annotate(
            total_ingresos=Sum('precio_total'),
            total_reservas=Count('id')
        ).order_by('periodo')

    return Response({
        'periodo': periodo,
        'datos': list(agrupacion),
        'total_periodos': len(agrupacion)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ocupacion_por_area(request):
    """
    Reporte de ocupación por área - Horas de uso y tasas de ocupación
    """
    # Obtener todas las áreas con sus reservas
    areas = AreaComun.objects.all()
    resultado = []

    for area in areas:
        # Obtener reservas confirmadas de esta área
        reservas_area = ReservaArea.objects.filter(
            area=area,
            estado=EstadoReserva.CONFIRMADA
        )

        total_reservas = reservas_area.count()

        # Calcular horas totales manualmente
        horas_totales = 0
        for reserva in reservas_area:
            if reserva.fecha_inicio and reserva.fecha_fin:
                delta = reserva.fecha_fin - reserva.fecha_inicio
                horas_totales += delta.total_seconds() / 3600

        # Calcular promedio de horas por reserva
        promedio_horas = horas_totales / total_reservas if total_reservas > 0 else 0

        if total_reservas > 0:  # Solo incluir áreas con reservas
            resultado.append({
                'area_id': area.id,
                'area_nombre': area.nombre,
                'total_reservas': total_reservas,
                'horas_totales': round(horas_totales, 2),
                'promedio_horas_por_reserva': round(promedio_horas, 2)
            })

    # Ordenar por horas totales descendente
    resultado.sort(key=lambda x: x['horas_totales'], reverse=True)

    return Response({
        'ocupacion_por_area': resultado
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ranking_areas_populares(request):
    """
    Ranking de áreas populares - Score combinado de popularidad
    """
    # Obtener todas las áreas
    areas = AreaComun.objects.all()
    resultado = []
    max_reservas = 1
    max_ingresos = 1

    # Primero calcular estadísticas para cada área
    areas_stats = []
    for area in areas:
        reservas_totales = ReservaArea.objects.filter(area=area).count()

        if reservas_totales > 0:
            reservas_confirmadas = ReservaArea.objects.filter(
                area=area,
                estado=EstadoReserva.CONFIRMADA
            ).count()

            ingresos_totales = ReservaArea.objects.filter(
                area=area,
                estado=EstadoReserva.CONFIRMADA
            ).aggregate(total=Sum('precio_total'))['total'] or 0

            promedio_precio = ReservaArea.objects.filter(
                area=area,
                estado=EstadoReserva.CONFIRMADA
            ).aggregate(promedio=Avg('precio_total'))['promedio'] or 0

            area_data = {
                'area_id': area.id,
                'area_nombre': area.nombre,
                'total_reservas': reservas_totales,
                'reservas_confirmadas': reservas_confirmadas,
                'total_ingresos': float(ingresos_totales),
                'promedio_precio': float(promedio_precio)
            }
            areas_stats.append(area_data)

            # Actualizar máximos para normalización
            max_reservas = max(max_reservas, reservas_totales)
            max_ingresos = max(max_ingresos, float(ingresos_totales))

    # Calcular score combinado para cada área
    for area in areas_stats:
        # Score normalizado (0-100)
        score_reservas = (area['total_reservas'] / max_reservas) * 50
        score_ingresos = (area['total_ingresos'] / max_ingresos) * 50
        score_total = score_reservas + score_ingresos

        # Tasa de confirmación
        tasa_confirmacion = (area['reservas_confirmadas'] / area['total_reservas'] * 100) if area['total_reservas'] else 0

        resultado.append({
            'area_id': area['area_id'],
            'area_nombre': area['area_nombre'],
            'score_popularidad': round(score_total, 1),
            'total_reservas': area['total_reservas'],
            'reservas_confirmadas': area['reservas_confirmadas'],
            'tasa_confirmacion': round(tasa_confirmacion, 1),
            'total_ingresos': area['total_ingresos'],
            'promedio_precio': area['promedio_precio']
        })

    # Ordenar por score de popularidad
    resultado.sort(key=lambda x: x['score_popularidad'], reverse=True)

    return Response({
        'ranking_areas': resultado
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def horarios_peak(request):
    """
    Análisis de horarios peak - Por hora del día
    """
    # Obtener reservas confirmadas con hora de inicio
    reservas = ReservaArea.objects.filter(
        estado=EstadoReserva.CONFIRMADA
    ).annotate(
        hora=Extract('fecha_inicio', 'hour')
    ).values('hora').annotate(
        total_reservas=Count('id'),
        total_ingresos=Sum('precio_total')
    ).order_by('hora')

    # También analizar por día de la semana
    reservas_por_dia = ReservaArea.objects.filter(
        estado=EstadoReserva.CONFIRMADA
    ).annotate(
        dia_semana=Extract('fecha_inicio', 'week_day')
    ).values('dia_semana').annotate(
        total_reservas=Count('id'),
        total_ingresos=Sum('precio_total')
    ).order_by('dia_semana')

    # Mapear días de la semana a nombres
    dias_nombres = {
        1: 'Domingo', 2: 'Lunes', 3: 'Martes', 4: 'Miércoles',
        5: 'Jueves', 6: 'Viernes', 7: 'Sábado'
    }

    reservas_por_dia_nombres = [
        {
            **dia,
            'dia_nombre': dias_nombres.get(dia['dia_semana'], 'Desconocido')
        }
        for dia in reservas_por_dia
    ]

    return Response({
        'horarios_peak': list(reservas),
        'dias_semana': reservas_por_dia_nombres
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estados_reservas(request):
    """
    Estados de reservas - Porcentajes de confirmadas/pendientes/canceladas
    """
    # Contar reservas por estado
    estados_count = ReservaArea.objects.values('estado').annotate(
        total=Count('id'),
        total_ingresos=Sum('precio_total')
    )

    # Calcular totales
    total_reservas = ReservaArea.objects.count()

    # Calcular porcentajes
    resultado = []
    for estado in estados_count:
        porcentaje = (estado['total'] / total_reservas * 100) if total_reservas else 0
        resultado.append({
            'estado': estado['estado'],
            'estado_display': dict(EstadoReserva.choices)[estado['estado']],
            'total': estado['total'],
            'porcentaje': round(porcentaje, 1),
            'total_ingresos': estado['total_ingresos'] or 0
        })

    # Estadísticas adicionales por período reciente (últimos 30 días)
    fecha_limite = timezone.now() - timedelta(days=30)
    estados_recientes = ReservaArea.objects.filter(
        created_at__gte=fecha_limite
    ).values('estado').annotate(
        total=Count('id')
    )

    total_recientes = ReservaArea.objects.filter(created_at__gte=fecha_limite).count()

    estados_recientes_porcentaje = []
    for estado in estados_recientes:
        porcentaje = (estado['total'] / total_recientes * 100) if total_recientes else 0
        estados_recientes_porcentaje.append({
            'estado': estado['estado'],
            'estado_display': dict(EstadoReserva.choices)[estado['estado']],
            'total': estado['total'],
            'porcentaje': round(porcentaje, 1)
        })

    return Response({
        'estados_general': resultado,
        'estados_ultimos_30_dias': estados_recientes_porcentaje,
        'total_reservas': total_reservas,
        'total_reservas_recientes': total_recientes
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_reportes(request):
    """
    Resumen general de todos los reportes
    """
    # KPIs principales
    total_areas = AreaComun.objects.count()
    total_reservas = ReservaArea.objects.count()
    reservas_confirmadas = ReservaArea.objects.filter(estado=EstadoReserva.CONFIRMADA).count()
    ingresos_totales = ReservaArea.objects.filter(estado=EstadoReserva.CONFIRMADA).aggregate(
        total=Sum('precio_total')
    )['total'] or 0

    # Área más popular
    area_popular = ReservaArea.objects.values(
        'area__nombre'
    ).annotate(
        total=Count('id')
    ).order_by('-total').first()

    # Estadísticas del mes actual
    mes_actual = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stats_mes = ReservaArea.objects.filter(
        fecha_inicio__gte=mes_actual,
        estado=EstadoReserva.CONFIRMADA
    ).aggregate(
        reservas=Count('id'),
        ingresos=Sum('precio_total')
    )

    return Response({
        'kpis': {
            'total_areas': total_areas,
            'total_reservas': total_reservas,
            'reservas_confirmadas': reservas_confirmadas,
            'tasa_confirmacion': round((reservas_confirmadas / total_reservas * 100) if total_reservas else 0, 1),
            'ingresos_totales': ingresos_totales,
            'area_mas_popular': area_popular['area__nombre'] if area_popular else 'N/A'
        },
        'mes_actual': {
            'reservas': stats_mes['reservas'] or 0,
            'ingresos': stats_mes['ingresos'] or 0
        }
    })