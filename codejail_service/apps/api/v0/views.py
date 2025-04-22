"""
Codejail service API.
"""

import json
import logging

from edx_django_utils.monitoring import set_custom_attribute
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

    Special note: The JSON format used by this endpoint permits floating point
    special values such as `NaN` and `Infinity`, which standards-compliant JSON
    implementations will not accept or produce. Python's `json` module allows
    them by default, but other implementations may need to be configured
    specially.
    """
    if not CODEJAIL_ENABLED.is_enabled():
        # .. custom_attribute_name: codejail.exec.status
        # .. custom_attribute_description: Type of response from code execution request.
        #   Value is dot-delimited string where the first segment is one of "disabled" (the
        #   API is refusing all requests), "invalid" (this particular request was refused),
        #   or "executed" (the request was executed). Further segments give additional
        #   information. Of particular note are the values "executed.success" and
        #   "executed.error", which distinguish between executions that completed normally
        #   and those that raised an error or were killed.
        set_custom_attribute('codejail.exec.status', 'disabled.feature_switch')
        return Response({'error': "Codejail service not enabled"}, status=500)

    if not is_exec_safe():
        set_custom_attribute('codejail.exec.status', 'disabled.safety_checks_failed')
        return Response({'error': "Codejail service is not correctly configured"}, status=500)

    params_json = request.data.get('payload')
    if params_json is None:
        set_custom_attribute('codejail.exec.status', 'invalid.payload.missing')
        return Response({'error': "Missing 'payload' parameter in POST body"}, status=400)

    try:
        params = json.loads(params_json)
    except json.decoder.JSONDecodeError as e:
        log.error(f"Payload was not valid JSON: {e}")
        set_custom_attribute('codejail.exec.status', 'invalid.payload.bad_json')
        return Response({'error': f"Unable to parse payload JSON: {e}"}, status=400)

    if json_error := json_error_best_match(payload_validator.iter_errors(params)):
        error_msg = (
            "Payload JSON did not match schema "
            f"at path {json_error.json_path}: {json_error.message}"
        )
        log.error(error_msg)
        set_custom_attribute('codejail.exec.status', 'invalid.payload.schema_mismatch')
        return Response({'error': error_msg}, status=400)

    # These first two are required params, but schema check has
    # already ensured they are present.
    complete_code = params['code']  # includes standard prolog
    input_globals_dict = params['globals_dict']
    python_path = params.get('python_path') or []
    limit_overrides_context = params.get('limit_overrides_context')
    slug = params.get('slug')
    unsafely = params.get('unsafely')

    # Help detect unusual traffic or filter out activity from certain sources
    if limit_overrides_context:
        # .. custom_attribute_name: codejail.exec.limit_override
        # .. custom_attribute_description: If present, contains the value of the ``limit_overrides_context``
        #   parameter in a codejail execution request. This indicates a request to use a different
        #   set of resource limits that have been pre-configured on the server, possibly
        #   considerably higher ones.
        set_custom_attribute('codejail.exec.limit_override', limit_overrides_context)
    # .. custom_attribute_name: codejail.exec.python_path_len
    # .. custom_attribute_description: The number of entries in the ``python_path`` parameter
    #   to a codejail execution request. Normally there should be zero or one entries.
    set_custom_attribute('codejail.exec.python_path_len', len(python_path))
    # .. custom_attribute_name: codejail.exec.files_count
    # .. custom_attribute_description: The number of files the request included in a
    #   codejail execution request. Normally there should be zero or one entries.
    set_custom_attribute('codejail.exec.files_count', len(request.FILES))
    # .. custom_attribute_name: codejail.exec.slug
    # .. custom_attribute_description: "Slug" ID passed in the request. This is
    #   usually going to be a problem ID, and may help identify what XBlock was
    #   involved.
    set_custom_attribute('codejail.exec.slug', slug)

    # Convert to a list of (string, bytestring) pairs. Any duplicated file names
    # are resolved as last-wins.
    extra_files = [(filename, file.read()) for filename, file in request.FILES.items()]

    # The following checks protect against vulnerabilities that would be
    # introduced by exposing `safe_exec` directly. edxapp contains protections
    # against these features being abused, but those protections are outside of
    # the codejail-service security boundary and may be subject to change.
    # Direct calls to the codejail-service API, bypassing edxapp, would
    # not benefit from this protection.

    # Only allow a known safe value for `python_path` (the only value that edxapp
    # would ever send, in practice). Unrestricted `python_path` would allow
    # *arbitrary file reads* in the broader filesystem by sandboxed code
    # regardless of AppArmor settings. These reads would happen with the
    # privilege level of the webapp user, not the sandbox user.
    if unexpected := set(python_path) - {'python_lib.zip'}:
        log.error(f"Unexpected python_path entries in request: {unexpected!r}")
        set_custom_attribute('codejail.exec.status', 'invalid.python_path')
        return Response({'error': "Only allowed entry in 'python_path' is 'python_lib.zip'"}, status=400)

    # Only allow a known safe name for uploaded files. (In practice, edxapp
    # only ever sends a file called python_lib.zip). Due to a lack of checks in
    # codejail, unrestricted filenames allow *arbitrary file writes* in the
    # broader filesystem regardless of AppArmor settings. These writes would
    # happen with the privilege level of the webapp user, not the sandbox user.
    if unexpected := {name for (name, _bytes) in extra_files} - {'python_lib.zip'}:
        log.error(f"Unexpected filenames in request: {unexpected!r}")
        set_custom_attribute('codejail.exec.status', 'invalid.files')
        return Response({'error': "Only allowed name for uploaded file is 'python_lib.zip'"}, status=400)

    # Far too dangerous to allow unsafe executions to come in over the
    # network, even if we were to authenticate them. The caller is the
    # one who has the context on safety.
    if unsafely:
        set_custom_attribute('codejail.exec.status', 'invalid.unsafely')
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
        set_custom_attribute('codejail.exec.status', 'executed.success')
        return Response({'globals_dict': globals_out})
    else:
        log.debug("Codejail execution failed for {slug=} with: {error_message}")
        # Nothing in edxapp actually *uses* the returned globals when there's an
        # emsg, but it does demand that the key is present in the response. The
        # globals also aren't updated when codejail encountered an error. We
        # could just as well return {} here, but the service returns the "updated"
        # globals for backward-compatibility, just in case anything actually does
        # care.
        set_custom_attribute('codejail.exec.status', 'executed.error')
        return Response({'globals_dict': globals_out, 'emsg': error_message})
