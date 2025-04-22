"""Settings common to all configurations."""

import os
from os.path import abspath, dirname, join

from codejail_service.settings.utils import get_logger_config

# PATH vars
PROJECT_ROOT = join(abspath(dirname(__file__)), "..")


def root(*path_fragments):
    return join(abspath(PROJECT_ROOT), *path_fragments)


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    # The service doesn't use authentication, but DRF relies on this app
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',

    'codejail_service.apps.core',
    'codejail_service.apps.api',
)

MIDDLEWARE = (
    'edx_django_utils.monitoring.DeploymentMonitoringMiddleware',  # python and django version
    'edx_django_utils.monitoring.CachedCustomMonitoringMiddleware',  # support accumulate & increment

    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
)

REST_FRAMEWORK = {
    # We need to accept and return special floats like NaN and Infinity in
    # globals_dict, despite these not being legal JSON according to the
    # RFC. Python's json module allows these by default, so we don't get errors
    # at the safe_exec JSON de/serialization level, but we also need to
    # de/serialize across the network. That's up to DRF, which uses a strict
    # mode by default. We need to turn that off.
    'STRICT_JSON': False,
}

ROOT_URLCONF = 'codejail_service.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'codejail_service.wsgi.application'

# Django *really* wants a database. So we give it a blank in-memory one.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Not a user-facing service, but these are standard internationalization settings.
# https://docs.djangoproject.com/en/dev/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (
    root('conf', 'locale'),
)

# Set up logging for development use (logging to stdout)
LOGGING = get_logger_config(debug=DEBUG)
