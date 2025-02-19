"""
Tests for process creation.
"""

from textwrap import dedent

from api_tests.utils import call_api_code_error


def test_deny_fork():
    """
    Can't fork own process excessively.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import os, sys

      # codejail defaults NPROC to 15; pick something much higher
      for _ in range(100):
          pid = os.fork()

          # If we're the child, die right away, otherwise the code suffix
          # added by safe_exec to bundle up globals into a JSON response
          # on stdout will run on *both* processes. Since they share a stdout,
          # this would create garbled JSON and a JsonDecodeError rather than
          # the more useful SafeExecException.
          if pid == 0:
              sys.exit(0)
    """), {})
    # 11 = EAGAIN: Resource temporarily unavailable (process limit, in this case)
    assert "BlockingIOError: [Errno 11] Resource temporarily unavailable" in emsg
