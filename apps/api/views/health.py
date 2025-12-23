"""
Health check endpoint for monitoring.
"""
from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Health check endpoint for load balancers and monitoring systems.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """
        Returns health status of the service.
        """
        health_status = {
            'status': 'healthy',
            'checks': {
                'database': self._check_database(),
            }
        }
        
        # Determine overall status
        all_healthy = all(
            check['status'] == 'healthy' 
            for check in health_status['checks'].values()
        )
        
        if not all_healthy:
            health_status['status'] = 'unhealthy'
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        return Response(health_status, status=status.HTTP_200_OK)

    @staticmethod
    def _check_database() -> dict:
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return {'status': 'healthy'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
