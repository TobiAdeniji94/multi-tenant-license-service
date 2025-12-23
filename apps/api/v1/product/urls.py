"""
Product API URL routing.
"""
from django.urls import path

from . import views

urlpatterns = [
    # License activation and validation
    path('activate/', views.ActivateLicenseView.as_view(), name='product-activate'),
    path('validate/', views.ValidateLicenseView.as_view(), name='product-validate'),
    path('deactivate/', views.DeactivateLicenseView.as_view(), name='product-deactivate'),
    path('status/', views.LicenseStatusView.as_view(), name='product-status'),
]
