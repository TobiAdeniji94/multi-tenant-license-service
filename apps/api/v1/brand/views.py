"""
Brand API views for license management.
"""
import logging

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.api.authentication import BrandAPIKeyAuthentication
from apps.api.exceptions import (
    LicenseKeyNotFoundError,
    LicenseNotFoundError,
    ProductNotFoundError,
)
from apps.brands.models import Product
from apps.licenses.models import Activation, License, LicenseKey

from .serializers import (
    CustomerLicenseQuerySerializer,
    CustomerLicenseResponseSerializer,
    LicenseCreateSerializer,
    LicenseKeyCreateSerializer,
    LicenseKeySerializer,
    LicenseRenewSerializer,
    LicenseSerializer,
    ProductSerializer,
)

logger = logging.getLogger(__name__)


class BrandAPIView(APIView):
    """Base view for Brand API endpoints."""
    authentication_classes = [BrandAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_brand(self):
        """Get the authenticated brand."""
        return self.request.user  # Brand is set as user by authentication


class LicenseKeyListCreateView(BrandAPIView):
    """
    List and create license keys for the authenticated brand.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='List license keys',
        description='List all license keys for the authenticated brand.',
        responses={200: LicenseKeySerializer(many=True)}
    )
    def get(self, request):
        brand = self.get_brand()
        license_keys = LicenseKey.objects.filter(brand=brand).prefetch_related(
            Prefetch('licenses', queryset=License.objects.select_related('product')),
            Prefetch('licenses__activations', queryset=Activation.objects.filter(is_active=True))
        )
        serializer = LicenseKeySerializer(license_keys, many=True)
        return Response({'data': serializer.data})

    @extend_schema(
        tags=['Brand API'],
        summary='Create license key',
        description='Create a new license key for a customer.',
        request=LicenseKeyCreateSerializer,
        responses={201: LicenseKeySerializer}
    )
    def post(self, request):
        brand = self.get_brand()
        serializer = LicenseKeyCreateSerializer(data=request.data, context={'brand': brand})
        serializer.is_valid(raise_exception=True)
        license_key = serializer.save()
        
        logger.info(f"License key created: {license_key.key[:8]}... for {license_key.customer_email}")
        
        response_serializer = LicenseKeySerializer(license_key)
        return Response({'data': response_serializer.data}, status=status.HTTP_201_CREATED)


class LicenseKeyDetailView(BrandAPIView):
    """
    Retrieve a specific license key.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Get license key details',
        description='Retrieve details of a specific license key.',
        responses={200: LicenseKeySerializer}
    )
    def get(self, request, key):
        brand = self.get_brand()
        try:
            license_key = LicenseKey.objects.prefetch_related(
                Prefetch('licenses', queryset=License.objects.select_related('product')),
                Prefetch('licenses__activations', queryset=Activation.objects.filter(is_active=True))
            ).get(key=key, brand=brand)
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()
        
        serializer = LicenseKeySerializer(license_key)
        return Response({'data': serializer.data})


class LicenseCreateView(BrandAPIView):
    """
    Create a new license for an existing license key.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Create license',
        description='Create a new license and attach it to an existing license key.',
        request=LicenseCreateSerializer,
        responses={201: LicenseSerializer}
    )
    def post(self, request, key):
        brand = self.get_brand()
        
        try:
            license_key = LicenseKey.objects.get(key=key, brand=brand)
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()
        
        serializer = LicenseCreateSerializer(
            data=request.data,
            context={'brand': brand, 'license_key': license_key}
        )
        serializer.is_valid(raise_exception=True)
        license = serializer.save()
        
        logger.info(f"License created: {license.id} for product {license.product.name}")
        
        response_serializer = LicenseSerializer(license)
        return Response({'data': response_serializer.data}, status=status.HTTP_201_CREATED)


class LicenseDetailView(BrandAPIView):
    """
    Retrieve a specific license.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Get license details',
        description='Retrieve details of a specific license.',
        responses={200: LicenseSerializer}
    )
    def get(self, request, license_id):
        brand = self.get_brand()
        try:
            license = License.objects.select_related('product', 'license_key').prefetch_related(
                'activations'
            ).get(id=license_id, license_key__brand=brand)
        except License.DoesNotExist:
            raise LicenseNotFoundError()
        
        serializer = LicenseSerializer(license)
        return Response({'data': serializer.data})


class LicenseRenewView(BrandAPIView):
    """
    Renew (extend) a license.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Renew license',
        description='Extend the expiration date of a license.',
        request=LicenseRenewSerializer,
        responses={200: LicenseSerializer}
    )
    def post(self, request, license_id):
        brand = self.get_brand()
        try:
            license = License.objects.get(id=license_id, license_key__brand=brand)
        except License.DoesNotExist:
            raise LicenseNotFoundError()
        
        serializer = LicenseRenewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        license.renew(days=serializer.validated_data['days'])
        
        logger.info(f"License renewed: {license.id} for {serializer.validated_data['days']} days")
        
        response_serializer = LicenseSerializer(license)
        return Response({'data': response_serializer.data})


class LicenseSuspendView(BrandAPIView):
    """
    Suspend a license.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Suspend license',
        description='Suspend a license, preventing activation and validation.',
        responses={200: LicenseSerializer}
    )
    def post(self, request, license_id):
        brand = self.get_brand()
        try:
            license = License.objects.get(id=license_id, license_key__brand=brand)
        except License.DoesNotExist:
            raise LicenseNotFoundError()
        
        license.suspend()
        logger.info(f"License suspended: {license.id}")
        
        serializer = LicenseSerializer(license)
        return Response({'data': serializer.data})


class LicenseResumeView(BrandAPIView):
    """
    Resume a suspended license.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Resume license',
        description='Resume a suspended license.',
        responses={200: LicenseSerializer}
    )
    def post(self, request, license_id):
        brand = self.get_brand()
        try:
            license = License.objects.get(id=license_id, license_key__brand=brand)
        except License.DoesNotExist:
            raise LicenseNotFoundError()
        
        license.resume()
        logger.info(f"License resumed: {license.id}")
        
        serializer = LicenseSerializer(license)
        return Response({'data': serializer.data})


class LicenseCancelView(BrandAPIView):
    """
    Cancel a license.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='Cancel license',
        description='Cancel a license permanently.',
        responses={200: LicenseSerializer}
    )
    def post(self, request, license_id):
        brand = self.get_brand()
        try:
            license = License.objects.get(id=license_id, license_key__brand=brand)
        except License.DoesNotExist:
            raise LicenseNotFoundError()
        
        license.cancel()
        logger.info(f"License cancelled: {license.id}")
        
        serializer = LicenseSerializer(license)
        return Response({'data': serializer.data})


class CustomerLicensesView(BrandAPIView):
    """
    List all licenses for a customer email across ALL brands.
    This is US6 - cross-brand customer lookup.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='List customer licenses',
        description='List all licenses for a customer email across all brands in the ecosystem.',
        parameters=[
            OpenApiParameter(name='email', type=str, required=True, description='Customer email address')
        ],
        responses={200: CustomerLicenseResponseSerializer}
    )
    def get(self, request):
        serializer = CustomerLicenseQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Get all license keys for this email across ALL brands
        license_keys = LicenseKey.objects.filter(
            customer_email__iexact=email
        ).select_related('brand').prefetch_related(
            Prefetch('licenses', queryset=License.objects.select_related('product')),
            Prefetch('licenses__activations', queryset=Activation.objects.filter(is_active=True))
        )
        
        total_licenses = sum(lk.licenses.count() for lk in license_keys)
        
        response_data = {
            'email': email,
            'license_keys': LicenseKeySerializer(license_keys, many=True).data,
            'total_licenses': total_licenses
        }
        
        logger.info(f"Customer lookup: {email} - found {total_licenses} licenses")
        
        return Response({'data': response_data})


class ProductListView(BrandAPIView):
    """
    List products for the authenticated brand.
    """
    
    @extend_schema(
        tags=['Brand API'],
        summary='List products',
        description='List all products for the authenticated brand.',
        responses={200: ProductSerializer(many=True)}
    )
    def get(self, request):
        brand = self.get_brand()
        products = Product.objects.filter(brand=brand, is_active=True)
        serializer = ProductSerializer(products, many=True)
        return Response({'data': serializer.data})
