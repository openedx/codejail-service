"""Settings for use in local deployments."""

from codejail_service.settings.base import *  # pylint: disable=wildcard-import

DEBUG = True

#####################################################################
# Lastly, see if the developer has any local overrides.
if os.path.isfile(join(dirname(abspath(__file__)), 'private.py')):
    from .private import *  # pylint: disable=import-error,wildcard-import
