"""
API URL routing for v1.
"""
from django.urls import include, path

from .views import health

urlpatterns = [
    # Health check
    path('health/', health.HealthCheckView.as_view(), name='health-check'),
    
    # Brand API - for brand systems to manage licenses
    path('brand/', include('apps.api.v1.brand.urls')),
    
    # Product API - for end-user products to activate/validate
    path('product/', include('apps.api.v1.product.urls')),
]
