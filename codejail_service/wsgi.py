"""
WSGI config for codejail-service.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""
import os
from os.path import abspath, dirname
from sys import path

from django.conf import settings
from django.core.wsgi import get_wsgi_application

SITE_ROOT = dirname(dirname(abspath(__file__)))
path.append(SITE_ROOT)

application = get_wsgi_application()  # pylint: disable=invalid-name
