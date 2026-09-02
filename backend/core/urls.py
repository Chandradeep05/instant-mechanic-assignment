"""
Master URL configuration for Instant Mechanic LiveOps Dashboard.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Redirect root URL to Interactive Swagger API Docs
    path('', RedirectView.as_view(url='/api/docs/', permanent=False)),

    path('admin/', admin.site.urls),

    # API v1 routes
    path('api/v1/', include('apps.dashboard.urls')),
    path('api/v1/bookings/', include('apps.bookings.urls')),
    path('api/v1/mechanics/', include('apps.mechanics.urls')),
    path('api/v1/customers/', include('apps.customers.urls')),
    path('api/v1/', include('apps.demo.urls')),

    # OpenAPI Schema & Interactive Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
