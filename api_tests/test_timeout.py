"""
Tests for execution time limits.
"""

from textwrap import dedent

from api_tests.utils import call_api_code_error


def test_deny_long_running_task():
    """
    Don't allow an implausibly long-running task.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import time

      start = time.monotonic()
      time.sleep(30.0)
      elapsed = time.monotonic() - start
    """), {})
    # Killed by SIG_KILL == -9 (or $? == 137 in shell)
    #
    # This status code is important because it indicates that SIG_KILL was used
    # by default, with no attempt at SIG_TERM or other "gentle" mechanism first.
    assert emsg == "Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -9"


def test_deny_prevent_kill():
    """
    Allowed to capture and ignore various signals, but it won't prevent kill.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import signal, time

      def ignore(_signum, _frame):
          pass

      # Catch and ignore the relevant signals we are able to (unlike SIGKILL)
      signal.signal(signal.SIGINT, ignore)
      signal.signal(signal.SIGTERM, ignore)

      start = time.monotonic()
      time.sleep(30.0)
      elapsed = time.monotonic() - start
    """), {})
    # Again, this shows SIG_KILL was used.
    assert emsg == "Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -9"
