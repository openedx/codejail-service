"""
State and accessors for a safety check that is run at startup.
"""

import logging

from codejail_service.codejail import safe_exec

log = logging.getLogger(__name__)

# Results of the safety check that was performed at startup.
#
# Expected values:
#
# - None: The check has not yet been performed
# - True: No issues were detected
# - False: A fundamental safety or function issue was detected
#
# Any other value indicates that the safety check failed in an
# unexpected way, perhaps raising an exception.
#
# The *only value* that indicates that it is safe to receive code-exec
# calls is `True`.
STARTUP_SAFETY_CHECK_OK = None


def is_exec_safe():
    """
    Return True if and only if it is safe to accept code-exec calls.
    """
    return STARTUP_SAFETY_CHECK_OK is True


def run_startup_safety_check():
    """
    Perform a sandboxing safety check.

    Determines if the service is running with an acceptable configuration.
    This is *not* a full test suite, just a basic check that codejail
    is actually configured in sandboxing mode.

    This just initializes state. Afterwards, is_exec_safe can be called.
    """
    global STARTUP_SAFETY_CHECK_OK

    # App initialization can happen multiple times; just run checks once.
    if STARTUP_SAFETY_CHECK_OK is not None:
        return

    tests = [
        {
            "name": "Basic code execution",
            "fn": _test_basic_function,
        },
        {
            "name": "Block sandbox escape by disk access",
            "fn": _test_escape_disk,
        },
        {
            "name": "Block sandbox escape by child process",
            "fn": _test_escape_subprocess,
        },
    ]

    any_failed = False
    for test in tests:
        try:
            result = test['fn']()
        except BaseException as e:
            result = f"Uncaught exception from test: {e!r}"

        if result is True:
            log.info(f"Startup test {test['name']!r} passed")
        else:
            any_failed = True
            log.error(f"Startup test {test['name']!r} failed with: {result!r}")

    STARTUP_SAFETY_CHECK_OK = not any_failed


def _test_basic_function():
    """
    Test for basic code execution (math).
    """
    (globals_out, error_message) = safe_exec("x = x + 1", {'x': 16})

    if error_message is not None:
        return f"Unexpected error: {error_message}"
    if 'x' not in globals_out:
        return "x not in returned globals"
    if globals_out['x'] != 17:
        return f"returned global x != 17 (was {globals_out['x']})"

    return True


def _test_escape_disk():
    """
    Test for sandbox escape by reading from files outside of sandbox.
    """
    (globals_out, error_message) = safe_exec("import os; ret = os.listdir('/')", {})

    if error_message is None:
        return f"Expected error, but code ran successfully. Globals: {globals_out!r}"
    if "Permission denied" not in error_message:
        return f"Expected permission error, but got: {error_message}"

    return True


def _test_escape_subprocess():
    """
    Test for sandbox escape by creating a child process.
    """
    (globals_out, error_message) = safe_exec(
        "import subprocess;"
        "ret = subprocess.check_output('echo $((6 * 7))', shell=True)",
        {},
    )

    if error_message is None:
        return f"Expected error, but code ran successfully. Globals: {globals_out!r}"
    if "Permission denied" not in error_message:
        return f"Expected permission error, but got: {error_message}"

    return True
