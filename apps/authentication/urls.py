from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from apps.authentication.views import (
    CustomTokenObtainPairView,
    register,
    logout,
    profile,
    update_profile,
    change_password
)

app_name = 'authentication'

urlpatterns = [
    # JWT Authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout, name='logout'),
    
    # User Management
    path('register/', register, name='register'),
    path('profile/', profile, name='profile'),
    path('profile/update/', update_profile, name='update_profile'),
    path('change-password/', change_password, name='change_password'),
]