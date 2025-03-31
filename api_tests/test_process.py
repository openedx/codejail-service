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

    This executes a pruned forkbomb. A goal is set, and the process recursively
    forks, creating a binary tree of processes. This runs until the desired
    number of processes has been reached. Because the processes don't coordinate
    with each other after forking, this is instead accomplished by halving a
    counter.

    Before each fork, the code calculates the subgoals for the parent and the
    child, and then takes on the appropriate goal for itself once it discovers
    which side of the fork it has ended up on. Once the goal value reaches 1,
    the code is finished, and moves on to the next phase.

    If forking raises an exception, it is printed to stderr, which is shared by
    all processes. The test will look at stderr in order to discover if any
    relevant exceptions were printed.

    After the forking phase, the code waits for a few seconds so that all other
    branches can complete their forking. (This is a shoddy version of a sync
    barrier.) Without this, it might be possible for the original process to
    exit before the full number of processes is created.

    Only one of the processes is marked as the original. This one raises an
    exception, which causes an emsg to be returned; this is the only way we can
    return the stderr that the various processes have been logging to.

    All of the other processes, knowing they were forks, perform an early
    exit. Otherwise, they would continue to the rest of the safe_exec wrapper
    code that tries to write globals information to the (shared) stdout. This
    would create garbled JSON and result in a JsonDecodeError instead of the
    SafeExecException (carrying emsg) that we need.

    There is probably a more elegant approach that involves shared memory
    between the processes, but this seems to work well enough.
    """
    (_, emsg) = call_api_code_error(dedent("""
      import os, sys, time, traceback

      # The desired total number of processes in the tree.
      goal = 1000

      def log(msg):
          # Flush immediately because otherwise we'll 1) lose buffered lines,
          # and 2) end up with the buffer shared between forks and printed
          # multiple times.
          print(msg, file=sys.stderr, flush=True)

      log(f"Starting @{time.time():.1f}")

      id = ""  # fork history used for debugging -- 0 = parent, 1 = child
      original = True

      # If goal is 1, the current process fulfills the goal.
      while goal > 1:
          # Split goal into roughly equal integer halves.
          # Each will be >= 1 if goal > 1.
          goal_parent = goal // 2
          goal_child = goal - goal_parent

          try:
              is_child = os.fork() == 0
              if is_child:
                  original = False
                  goal = goal_child
                  id = f"{id}1"
              else:
                  goal = goal_parent
                  id = f"{id}0"
          except BaseException as e:
              # Fork failed -- log this to stderr for discovery
              log(traceback.format_exc())
              break

      # Wait until all branches of tree have finished forking phase.
      # For reference, 1000 processes takes about half a second.
      log(f"Waiting @{time.time():.1f} ID={id}")
      time.sleep(2)

      if original:
          # We only get to look at stderr if the main process raises.
          raise Exception("Force return of stderr")
      else:
          # If we're a child, exit early to keep stdout clean.
          os._exit(0)
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
