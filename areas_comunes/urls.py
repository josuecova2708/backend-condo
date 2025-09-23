from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaComunViewSet, ReservaAreaViewSet
from . import reports_views

router = DefaultRouter()
router.register(r'areas', AreaComunViewSet, basename='area-comun')
router.register(r'reservas', ReservaAreaViewSet, basename='reserva-area')

urlpatterns = [
    path('', include(router.urls)),

    # Reportes
    path('reportes/ingresos-por-area/', reports_views.ingresos_por_area, name='ingresos-por-area'),
    path('reportes/ingresos-por-periodo/', reports_views.ingresos_por_periodo, name='ingresos-por-periodo'),
    path('reportes/ocupacion-por-area/', reports_views.ocupacion_por_area, name='ocupacion-por-area'),
    path('reportes/ranking-areas/', reports_views.ranking_areas_populares, name='ranking-areas'),
    path('reportes/horarios-peak/', reports_views.horarios_peak, name='horarios-peak'),
    path('reportes/estados-reservas/', reports_views.estados_reservas, name='estados-reservas'),
    path('reportes/resumen/', reports_views.resumen_reportes, name='resumen-reportes'),
]