"""Settings common to all configurations."""

import os
from os.path import abspath, dirname, join

from codejail_service.settings.utils import get_logger_config

# PATH vars
PROJECT_ROOT = join(abspath(dirname(__file__)), "..")


def root(*path_fragments):
    return join(abspath(PROJECT_ROOT), *path_fragments)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('CODEJAIL_SERVICE_SECRET_KEY', 'insecure-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
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

# Internationalization
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
