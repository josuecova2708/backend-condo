from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.communications.views import AvisoComunicadoViewSet, LecturaAvisoViewSet

app_name = 'communications'

router = DefaultRouter()
router.register(r'avisos', AvisoComunicadoViewSet, basename='aviso')
router.register(r'lecturas', LecturaAvisoViewSet, basename='lectura')

urlpatterns = [
    path('', include(router.urls)),
]