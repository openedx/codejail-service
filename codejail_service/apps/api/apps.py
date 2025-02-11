"""
Config for main API.
"""

import logging

from codejail.django_integration_utils import apply_django_settings
from django.apps import AppConfig
from django.conf import settings

from codejail_service.startup_check import run_startup_safety_check

log = logging.getLogger(__name__)


class CodejailApiConfig(AppConfig):
    """
    AppConfig for API views.

    The only reason we need this to be an app is so that we can hook into the
    ready() callback at startup. Any other mechanism would be fine too.
    """
    name = "codejail_service.apps.api"

    def ready(self):
        # Codejail needs this at startup
        apply_django_settings(settings.CODE_JAIL)

        # Perform self-check and initialize status for healthcheck and
        # code-exec views to consult.
        run_startup_safety_check()
