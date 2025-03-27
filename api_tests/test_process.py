"""
Tests for process creation.
"""

from textwrap import dedent
from unittest import TestCase

import ddt

from api_tests.utils import call_api_code_error


def test_deny_fork_excessively():
    """
    Can't fork own process excessively.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import os, sys, time

      level = 1
      isfork = False
      while level <= 9:  # 2^n processes -- above level=12 not recommended!
          try:
              if os.fork() == 0 or isfork:
                  isfork = True
              level += 1
          except BaseException as e:
              print(repr(e), file=sys.stderr)
              break

      if isfork:
          # Wait a bit so that there are a lot of concurrent forks
          time.sleep(2)
          # If we're the child, exit early. Otherwise the code suffix
          # added by safe_exec to bundle up globals into a JSON response
          # on stdout will run on *both* processes. Since they share a stdout,
          # this would create garbled JSON and a JsonDecodeError rather than
          # the more useful SafeExecException.
          sys.exit(0)
      else:
          # One last fork attempt on the main process so that we can check on
          # whether we've exceeded the limit.
          pid = os.fork()
          if pid == 0:
              sys.exit(0)  # clean up fork
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
