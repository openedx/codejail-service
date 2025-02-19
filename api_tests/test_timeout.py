"""
Tests for execution time limits.
"""

import time
from textwrap import dedent

from api_tests.utils import call_api_code_error

# An unreasonable number of seconds for a code-exec to run, in seconds
DURATION_UNREASONABLE = 15.0
# We'll try to sleep for well beyond that amount, for unambiguous testing
DURATION_ATTEMPT = DURATION_UNREASONABLE * 2


def test_deny_long_running_code():
    """
    Don't allow an implausibly long-running execution.
    """
    start = time.monotonic()
    (_, emsg) = call_api_code_error(dedent(f"""
      import time
      time.sleep({DURATION_ATTEMPT!r})
    """), {})
    elapsed = time.monotonic() - start

    # Killed by SIG_KILL == -9 (or $? == 137 in shell)
    #
    # This status code is important because it indicates that SIG_KILL was used
    # by default, with no attempt at SIG_TERM or other "gentle" mechanism first.
    assert emsg == "Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -9"

    # We don't know what the actual configured proc limits are for this
    # deployment of codejail-service, so the best bound we can set for
    # assertions here is "we tried to sleep for much longer than X, and actually
    # slept for less than X", where X is chosen to be higher than expected for
    # any reasonable CPU or wall-clock limit.
    assert elapsed < DURATION_UNREASONABLE


def test_deny_prevent_kill():
    """
    Allowed to capture and ignore various signals, but it won't prevent kill.
    """
    start = time.monotonic()
    (_, emsg) = call_api_code_error(dedent(f"""
      import signal, time

      def ignore(_signum, _frame):
          pass

      # Catch and ignore the relevant signals we are able to (unlike SIGKILL)
      signal.signal(signal.SIGINT, ignore)
      signal.signal(signal.SIGTERM, ignore)

      time.sleep({DURATION_ATTEMPT!r})
    """), {})
    elapsed = time.monotonic() - start

    # Again, this shows SIG_KILL was used.
    assert emsg == "Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -9"
    # Same logic as other test
    assert elapsed < DURATION_UNREASONABLE
