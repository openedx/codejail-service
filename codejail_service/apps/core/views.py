""" Core views. """
import logging

from django.http import JsonResponse
from edx_django_utils.monitoring import ignore_transaction

from codejail_service.startup_check import is_exec_safe

logger = logging.getLogger(__name__)


def health(_request):
    """
    Allows a load balancer to verify this service is up and healthy.

    Returns:
        HttpResponse: 200 if the service is available
        HttpResponse: 503 if the service is unavailable
    """

    # Ignores health check in performance monitoring so as to not artifically inflate our response time metrics
    ignore_transaction()

    if is_exec_safe():
        return JsonResponse({'status': 'OK'}, status=200)
    else:
        return JsonResponse({'status': 'UNAVAILABLE'}, status=503)
