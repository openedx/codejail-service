"""
Tests for process creation.
"""

from textwrap import dedent
from unittest import TestCase

import ddt

from api_tests.utils import call_api_code_error


def test_deny_fork_excessively():
    """
    Test that we can't create an excessive number of processes.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import os, time

      # Pick something much higher than the environment would be configured
      # for. For reference, codejail defaults NPROC to 15.
      goal = 1000

      # Seconds to wait for all forks to be present concurrently. Starting 500
      # forks should take 0.1–0.3 seconds, for reference.
      wait_s = 2.0

      for _ in range(goal - 1):  # already have one process
          if os.fork() == 0:
              # Forks should stick around for the wait period and then abort.
              # A normal exit would allow the code suffix added by safe_exec
              # to write JSON to the (shared) stdout, which would cause a
              # JsonDecodeError.
              #
              # Forks should generally use `os._exit`, not `sys.exit`, since
              # the latter is mediated by raising an exception and does
              # unwinding, triggers atexit handlers, etc.
              time.sleep(wait_s)
              os._exit(0)

      time.sleep(wait_s)
    """), {})
    # 11 = EAGAIN: Resource temporarily unavailable (process limit, in this case)
    assert "BlockingIOError: [Errno 11] Resource temporarily unavailable" in emsg


@ddt.ddt
class TestExecProcess(TestCase):
    """
    Tests for exec'ing new processes (not forking).
    """

    @ddt.data(
        # Some harmless binary that will definitely exist and that would quickly exit 0
        repr("/usr/bin/true"),
        # Similar test, although we're assuming there's permission to list working dir
        repr("/usr/bin/ls"),
        # Evaluates to the Python executable the sandboxed code is running under
        "sys.executable",
        # Python 3.8, on the PATH
        repr("python3.8"),
    )
    def test_deny_subprocess(self, bin_path_expr):
        """
        Despite allowing multiple processes, we can't actually exec new ones.

        bin_path_expr: A Python expression code that evaluates (in sandbox) to a
          string, naming the path to a binary we will try to execute.
        """
        code = dedent(f"""
          import subprocess, sys
          subprocess.run({bin_path_expr})
        """)
        (_, emsg) = call_api_code_error(code, {})

        # Exact error depends on the codejail NPROC settings
        expected_errors = [
            # Resource-limit-based denial, e.g. NPROC=1 (can't even fork in order to exec)
            "BlockingIOError: [Errno 11] Resource temporarily unavailable",
            # AppArmor-based denial (confinement doesn't permit executing other binaries)
            "PermissionError: [Errno 13] Permission denied",
        ]

        assert any(e in emsg for e in expected_errors), f"Error message was incorrect: {emsg}"
