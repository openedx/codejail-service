""" Core views. """
import logging

from django.http import JsonResponse
from edx_django_utils.monitoring import ignore_transaction

logger = logging.getLogger(__name__)


def health(_):
    """Allows a load balancer to verify this service is up.

    Checks the status of the database connection on which this service relies.

    Returns:
        HttpResponse: 200 if the service is available, with JSON data indicating the health of each required service
        HttpResponse: 503 if the service is unavailable, with JSON data indicating the health of each required service

    Example:
        >>> response = requests.get('https://codejail-service.edx.org/health')
        >>> response.status_code
        200
        >>> response.content
        '{"overall_status": "OK", "detailed_status": {"database_status": "OK", "lms_status": "OK"}}'
    """

    # Ignores health check in performance monitoring so as to not artifically inflate our response time metrics
    ignore_transaction()

    # Always "healthy", for now -- no state to look at. Revisit later.
    return JsonResponse({'status': 'OK'})
