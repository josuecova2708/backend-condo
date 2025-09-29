"""
URL configuration for smart_condo_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

def health_check(request):
    """Health check endpoint optimizado para Railway"""
    from django.http import HttpResponse

    # Para Railway health check, usar HttpResponse simple y rápido
    if request.META.get('HTTP_USER_AGENT', '').startswith('RailwayHealthCheck'):
        return HttpResponse('OK', status=200, content_type='text/plain')

    # Para otros casos, usar JsonResponse
    return JsonResponse({
        'status': 'ok',
        'message': 'Backend is running',
        'cors_enabled': True
    })

urlpatterns = [
    # Health checks - Railway busca en raíz
    path('', health_check, name='root_health_check'),
    path('health/', health_check, name='health_check_alt'),
    path('api/health/', health_check, name='health_check'),
    path('api/debug/', health_check, name='api_debug'),  # Diagnóstico para API paths

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/properties/', include('apps.properties.urls')),
    path('api/communications/', include('apps.communications.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/ai-security/', include('ai_security.urls')),
    path('api/finances/', include('finances.urls')),
    path('api/areas-comunes/', include('areas_comunes.urls')),
    path('api/mantenimiento/', include('mantenimiento.urls')),
    path('api/notifications/', include('notifications.urls')),
]

# Media files (for development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
