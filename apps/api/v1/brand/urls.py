"""
Brand API URL routing.
"""
from django.urls import path

from . import views

urlpatterns = [
    # License key management
    path('license-keys/', views.LicenseKeyListCreateView.as_view(), name='brand-license-keys'),
    path('license-keys/<str:key>/', views.LicenseKeyDetailView.as_view(), name='brand-license-key-detail'),
    
    # License management
    path('license-keys/<str:key>/licenses/', views.LicenseCreateView.as_view(), name='brand-license-create'),
    path('licenses/<uuid:license_id>/', views.LicenseDetailView.as_view(), name='brand-license-detail'),
    path('licenses/<uuid:license_id>/renew/', views.LicenseRenewView.as_view(), name='brand-license-renew'),
    path('licenses/<uuid:license_id>/suspend/', views.LicenseSuspendView.as_view(), name='brand-license-suspend'),
    path('licenses/<uuid:license_id>/resume/', views.LicenseResumeView.as_view(), name='brand-license-resume'),
    path('licenses/<uuid:license_id>/cancel/', views.LicenseCancelView.as_view(), name='brand-license-cancel'),
    
    # Customer lookup (US6)
    path('customers/', views.CustomerLicensesView.as_view(), name='brand-customer-licenses'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='brand-products'),
]
