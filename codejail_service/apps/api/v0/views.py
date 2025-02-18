"""
Codejail service API.
"""

import json
import logging

from edx_toggles.toggles import SettingToggle
from jsonschema.exceptions import best_match as json_error_best_match
from jsonschema.validators import Draft202012Validator
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from codejail_service.codejail import safe_exec
from codejail_service.startup_check import is_exec_safe

log = logging.getLogger(__name__)

# Schema for the JSON passed in the v0 API's 'payload' field.
payload_schema = {
    'type': 'object',
    'properties': {
        'code': {'type': 'string'},
        'globals_dict': {'type': 'object'},
        # Some of these are configured as union types because
        # edx-platform appears to currently default to None for some
        # of them (rather than omitting the keys.)
        'python_path': {
            'anyOf': [
                {
                    'type': 'array',
                    'items': {'type': 'string'},
                },
                {'type': 'null'},
            ],
        },
        'limit_overrides_context': {
            'anyOf': [
                {'type': 'string'},
                {'type': 'null'},
            ],
        },
        'slug': {
            'anyOf': [
                {'type': 'string'},
                {'type': 'null'},
            ],
        },
        # We'll parse this but won't respect it.
        'unsafely': {'type': 'boolean'},
    },
    'required': ['code', 'globals_dict'],
}
# Use this rather than jsonschema.validate, since that would check the schema
# every time it is called. Best to do it just once at startup.
Draft202012Validator.check_schema(payload_schema)
payload_validator = Draft202012Validator(payload_schema)

# .. toggle_name: CODEJAIL_ENABLED
# .. toggle_implementation: SettingToggle
# .. toggle_default: False
# .. toggle_description: If True, codejail execution calls will be accepted over the network.
#   This is currently an opt_in while the feature is still undergoing security review. Once
#   the feature is fully developed and other safeguards are in place (such as config
#   validation at startup) then this should be changed to a circuit_breaker, defaulting to True.
# .. toggle_use_cases: opt_in
# .. toggle_creation_date: 2025-01-30
CODEJAIL_ENABLED = SettingToggle('CODEJAIL_ENABLED', default=False, module_name=__name__)


@api_view(['POST'])
@parser_classes([FormParser, MultiPartParser])
def code_exec(request):
    """
    Executes code in a codejail sandbox for a remote caller.

    This implements the API used by edxapp's xmodule.capa.safe_exec.remote_exec.
    It accepts a POST of a form containing a `payload` value and zero or more
    extra files.

    The payload is JSON and contains the parameters to be sent to codejail's
    safe_exec (aside from `extra_files`). See payload_schema for type information.

    This API does not permit `unsafely=true`.

    If the response is a 200, the codejail execution completed. The response
    will be JSON containing the key `globals_dict` (containing
    the global scope values at the end of a run to completion) and possibly `emsg`
    (an error message string) if the submitted code raised an exception.

    Other responses are errors, with a JSON body containing further details.
    """
    if not CODEJAIL_ENABLED.is_enabled():
        return Response({'error': "Codejail service not enabled"}, status=500)

    if not is_exec_safe():
        return Response({'error': "Codejail service is not correctly configured"}, status=500)

    params_json = request.data['payload']
    params = json.loads(params_json)

    if json_error := json_error_best_match(payload_validator.iter_errors(params)):
        return Response({'error': f"Payload JSON did not match schema: {json_error.message}"}, status=400)

    complete_code = params['code']  # includes standard prolog
    input_globals_dict = params['globals_dict']
    python_path = params.get('python_path') or []
    limit_overrides_context = params.get('limit_overrides_context')
    slug = params.get('slug')
    unsafely = params.get('unsafely')

    # Convert to a list of (string, bytestring) pairs. Any duplicated file names
    # are resolved as last-wins.
    extra_files = [(filename, file.read()) for filename, file in request.FILES.items()]

    # Far too dangerous to allow unsafe executions to come in over the
    # network, even if we were to authenticate them. The caller is the
    # one who has the context on safety.
    if unsafely:
        return Response({'error': "Refusing codejail execution with unsafely=true"}, status=400)

    # This wrapped version of safe_exec doesn't mutate the globals dict
    (globals_out, error_message) = safe_exec(
        complete_code,
        input_globals_dict,
        python_path=python_path,
        extra_files=extra_files,
        limit_overrides_context=limit_overrides_context,
        slug=slug,
    )

    if error_message is None:
        log.debug("Codejail execution succeeded for {slug=}, with globals={globals_out!r}")
        return Response({'globals_dict': globals_out})
    else:
        log.debug("Codejail execution failed for {slug=} with: {error_message}")
        return Response({'globals_dict': globals_out, 'emsg': error_message})
