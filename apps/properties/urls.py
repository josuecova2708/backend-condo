from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'properties'

router = DefaultRouter()
# TODO: Add viewsets here

urlpatterns = [
    path('', include(router.urls)),
]