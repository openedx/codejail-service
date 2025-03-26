"""
State and accessors for a safety check that is run at startup.
"""

import logging
import urllib.request
from textwrap import dedent
from urllib.error import URLError

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

    # These checks should be a subset of the full api_tests suite, with
    # the aim of providing *basic* coverage of the range of types of
    # sandbox failures we could reasonably anticipate. (And at least one
    # check to confirm that we can execute safe code successfully.)
    #
    # In general we should only focus on sandbox escapes here, not on
    # verifying resource limits.
    checks = [
        {
            "name": "Basic code execution",
            "fn": _check_basic_function,
        },
        {
            "name": "Block sandbox escape by disk access",
            "fn": _check_escape_disk,
        },
        {
            "name": "Block sandbox escape by child process",
            "fn": _check_escape_subprocess,
        },
        {
            "name": "Block network access",
            "fn": _check_network_access,
        },
        {
            "name": "Block egress from webapp",
            "fn": _check_webapp_egress,
        },
    ]

    any_failed = False
    for check in checks:
        try:
            result = check['fn']()
        except BaseException as e:
            result = f"Uncaught exception from check: {e!r}"

        if result is True:
            log.info(f"Startup check {check['name']!r} passed")
        else:
            any_failed = True
            log.error(f"Startup check {check['name']!r} failed with: {result!r}")

    STARTUP_SAFETY_CHECK_OK = not any_failed


def _check_basic_function():
    """
    Check for basic code execution (math).
    """
    (globals_out, error_message) = safe_exec("x = x + 1", {'x': 16})

    if error_message is not None:
        return f"Unexpected error: {error_message}"
    if 'x' not in globals_out:
        return "x not in returned globals"
    if globals_out['x'] != 17:
        return f"returned global x != 17 (was {globals_out['x']})"

    return True


def _check_escape_disk():
    """
    Check for sandbox escape by reading from files outside of sandbox.
    """
    (globals_out, error_message) = safe_exec("import os; ret = os.listdir('/')", {})

    if error_message is None:
        return f"Expected error, but code ran successfully. Globals: {globals_out!r}"
    if "PermissionError: [Errno 13] Permission denied" not in error_message:
        return f"Expected permission error, but got: {error_message}"

    return True


def _check_escape_subprocess():
    """
    Check for sandbox escape by creating a child process.
    """
    # Call the most innocuous possible command that generates output
    (globals_out, error_message) = safe_exec(
        "import subprocess;"
        "ret = subprocess.check_output(['date', '-u', '-d', '@0', '+%Y'])",
        {},
    )

    if error_message is None:
        return f"Expected error, but code ran successfully. Globals: {globals_out!r}"
    # Exact error depends on the codejail NPROC settings
    expected_errors = [
        # Resource-limit-based denial, e.g. NPROC=1 (can't even fork in order to exec)
        "BlockingIOError: [Errno 11] Resource temporarily unavailable",
        # AppArmor-based denial (confinement doesn't permit executing other binaries)
        "PermissionError: [Errno 13] Permission denied",
    ]
    if not any(error in error_message for error in expected_errors):
        return f"Expected permission or resource limit error, but got: {error_message}"

    return True


def _check_network_access():
    """
    Check for denial of network access.
    """
    # Even creating a socket should fail (before we even try to connect or
    # bind). Because this operation doesn't actually interact with the network,
    # it should avoid misleading errors while running unit tests under
    # unfavorable network conditions, and doesn't require any consideration of
    # properly tuned timeouts. (Attempting a DNS or HTTP request here would run
    # into those problems.)
    #
    # We go to the trouble of properly closing the socket (using the `with`
    # context manager) because there's a unit test where the socket is
    # successfully created, and if we don't close it then there's a
    # ResourceWarning, which causes a `__warningregistry__` global to be
    # created. This would interfere with checking the logged error message,
    # which includes a listing of globals.
    (globals_out, error_message) = safe_exec(
        dedent("""
          import socket
          with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
              filedesc = s.fileno()
        """),
        {},
    )

    if error_message is None:
        return f"Expected error, but code ran successfully. Globals: {globals_out!r}"
    if "PermissionError: [Errno 13] Permission denied" not in error_message:
        return f"Expected permission error, but got: {error_message}"

    return True


def _check_webapp_egress():
    """
    Check for denial of outbound connections from webapp as well.

    This is a second layer of protection in case the webapp itself is
    compromised via sandbox escape or exploit of a vulnerability in sandbox
    setup.
    """
    try:
        r = urllib.request.urlopen('https://www.example.net/', timeout=3.0)
        return f"Expected URLError, but received response (status code {r.status})"
    except URLError:
        # URLError *probably* means that confinement was effective. It could be
        # a false negative due to a temporary network glitch, but it's probably
        # not worth teasing apart all of the different possible exceptions (and
        # complicating the logic and tests) just to identify this situation. The
        # exact exceptions we encounter may also not be particularly stable.
        #
        # But for reference, these are the exceptions we would expect to see:
        #
        # * URLError(gaierror(-3, 'Temporary failure in name resolution')) is a
        #   name resolution (DNS lookup) failure. We can't tell if this is due
        #   to a permission error or a network blip. (Interestingly, calling
        #   `socket.gethostbyname` directly instead raises gaierror(-2, 'Name or
        #   service not known').)
        # * URLError(PermissionError(13, 'Permission denied')) is the error we
        #   see when the TCP connection can't be built. (This occurs if the host
        #   is specified by IP instead of domain name.)
        #
        # Exceptions we would want to treat as a failure:
        #
        # * URLError(OSError(101, 'Network is unreachable')) is what we see when
        #   a connection attempt was made, but the timeout was reached.
        return True
    except BaseException as e:
        return f"Expected URLError, but got: {e!r}"
