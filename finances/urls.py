from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InfraccionViewSet, CargoViewSet, ConfiguracionMultasViewSet

# Crear router para las APIs REST
router = DefaultRouter()
router.register(r'infracciones', InfraccionViewSet, basename='infracciones')
router.register(r'cargos', CargoViewSet, basename='cargos')
router.register(r'configuracion-multas', ConfiguracionMultasViewSet, basename='configuracion-multas')

app_name = 'finances'

urlpatterns = [
    # Incluir todas las rutas del router
    path('api/', include(router.urls)),
]

# Rutas disponibles:
#
# INFRACCIONES:
# GET    /api/infracciones/                     - Listar infracciones
# POST   /api/infracciones/                     - Crear infracción
# GET    /api/infracciones/{id}/                - Detalle de infracción
# PUT    /api/infracciones/{id}/                - Actualizar infracción
# PATCH  /api/infracciones/{id}/                - Actualización parcial
# DELETE /api/infracciones/{id}/                - Eliminar infracción
# POST   /api/infracciones/{id}/confirmar/      - Confirmar infracción
# POST   /api/infracciones/{id}/rechazar/       - Rechazar infracción
# POST   /api/infracciones/{id}/aplicar_multa/  - Aplicar multa
# GET    /api/infracciones/pendientes/          - Infracciones pendientes
# GET    /api/infracciones/estadisticas/        - Estadísticas de infracciones
#
# CARGOS:
# GET    /api/cargos/                           - Listar cargos
# POST   /api/cargos/                           - Crear cargo
# GET    /api/cargos/{id}/                      - Detalle de cargo
# PUT    /api/cargos/{id}/                      - Actualizar cargo
# PATCH  /api/cargos/{id}/                      - Actualización parcial
# DELETE /api/cargos/{id}/                      - Eliminar cargo
# POST   /api/cargos/{id}/procesar_pago/        - Procesar pago
# GET    /api/cargos/vencidos/                  - Cargos vencidos
# GET    /api/cargos/por_propietario/           - Resumen por propietario
# POST   /api/cargos/generar_intereses_mora/    - Generar intereses automáticos
#
# CONFIGURACIÓN MULTAS:
# GET    /api/configuracion-multas/             - Listar configuraciones
# POST   /api/configuracion-multas/             - Crear configuración
# GET    /api/configuracion-multas/{id}/        - Detalle de configuración
# PUT    /api/configuracion-multas/{id}/        - Actualizar configuración
# PATCH  /api/configuracion-multas/{id}/        - Actualización parcial
# DELETE /api/configuracion-multas/{id}/        - Eliminar configuración
# GET    /api/configuracion-multas/activas/     - Solo configuraciones activas
# POST   /api/configuracion-multas/{id}/activar/   - Activar configuración
# POST   /api/configuracion-multas/{id}/desactivar/ - Desactivar configuración