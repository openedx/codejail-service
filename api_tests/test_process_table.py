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
    assert "Permission denied" in emsg


def test_deny_exec_ps():
    """
    Disallow execution of `ps` to reveal processes.
    """
    (_, emsg) = call_api_code_error("import subprocess; subprocess.run('ps')", {})
    assert "Permission denied" in emsg
