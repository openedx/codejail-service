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
        assert "Permission denied" in emsg
