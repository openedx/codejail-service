"""
Tests of attempts to access the process table.

These should all be denied. Accessing the process table could reveal the
directory in use for another active code execution, and we don't have any
protection against that other than unpredictable directory names.
"""

from api_tests.utils import call_api_code_error


def test_deny_list_proc():
    """
    Not allowed to list processes via /proc pseudo-filesystem.
    """
    (_, emsg) = call_api_code_error("import os; out = os.listdir('/proc')", {})
    assert "PermissionError: [Errno 13] Permission denied" in emsg


def test_deny_exec_ps():
    """
    Disallow execution of `ps` to reveal processes.
    """
    (_, emsg) = call_api_code_error("import subprocess; subprocess.run('ps')", {})

    # Exact error depends on the codejail NPROC settings
    expected_errors = [
        # Resource-limit-based denial, e.g. NPROC=1 (can't even fork in order to exec)
        "BlockingIOError: [Errno 11] Resource temporarily unavailable",
        # AppArmor-based denial (confinement doesn't permit executing other binaries)
        "PermissionError: [Errno 13] Permission denied",
    ]

    assert any(e in emsg for e in expected_errors), f"Error message was incorrect: {emsg}"
