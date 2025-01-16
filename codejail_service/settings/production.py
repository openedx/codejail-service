"""Settings for production use."""

from os import environ

import yaml

from codejail_service.settings.base import *  # pylint: disable=wildcard-import
from codejail_service.settings.utils import get_env_setting

DEBUG = False
TEMPLATE_DEBUG = DEBUG

LOGGING = get_logger_config()

# Keep track of the names of settings that represent dicts. Instead of overriding the values in base.py,
# the values read from disk should UPDATE the pre-configured dicts.
DICT_UPDATE_KEYS = ()

if 'CODEJAIL_SERVICE_CFG' in environ:
    CONFIG_FILE = get_env_setting('CODEJAIL_SERVICE_CFG')
    with open(CONFIG_FILE, encoding='utf-8') as f:
        config_from_yaml = yaml.safe_load(f)

        # Remove the items that should be used to update dicts, and apply them separately rather
        # than pumping them into the local vars.
        dict_updates = {key: config_from_yaml.pop(key, None) for key in DICT_UPDATE_KEYS}

        for key, value in dict_updates.items():
            if value:
                vars()[key].update(value)

        vars().update(config_from_yaml)
