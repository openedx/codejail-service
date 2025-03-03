"""
Check for environment leakage.
"""

from api_tests.utils import call_api_success


def test_deny_environment_leakage():
    """
    Test for environment variables that indicate an inadvertant leakage of the
    webapp's environment into the sandbox.

    We don't actually have any way of comprehensively checking the sandbox
    environment, nor a guaranteed way of discovering a leak. But we can check
    for a few variables that are very *plausibly* in the webapp environment.
    """
    globals_out = call_api_success("import os; out = {**os.environ}", {})
    found_env = globals_out['out']

    # Check that we actually did *get* the environment mapping
    assert 'PATH' in found_env

    # Commonly set in a Dockerfile during package installation, and
    # therefore present in the webapp's environment.
    assert "DEBIAN_FRONTEND" not in found_env
    # If deployed service is Django-based, this might be present.
    assert "DJANGO_SETTINGS_MODULE" not in found_env
