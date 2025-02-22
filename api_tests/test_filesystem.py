"""
Tests of filesystem access, allowed and denied.

Mostly should be denied, but parts of sandbox should be allowed.
"""

from textwrap import dedent
from unittest import TestCase

import ddt

from api_tests.utils import call_api_code_error, call_api_success


def test_can_list_in_own_sandbox():
    """
    We can list files in our own sandbox.
    """
    code = "import os; out = os.listdir('.')"
    listing = call_api_success(code, {})["out"]
    # A few things we should expect the codejail library to have created:
    assert "tmp" in listing
    assert "jailed_code" in listing


def test_can_write_in_own_sandbox():
    """
    We can create files in our own sandbox.
    """
    code = dedent("""
      with open("tmp/api-test.txt", 'w') as f:
          f.write("sample")

      with open("tmp/api-test.txt", 'r') as f:
          out = f.read()
    """)
    assert {"out": "sample"} == call_api_success(code, {})


@ddt.ddt
class TestFilesystemDenial(TestCase):
    """
    Various wider-OS filesystem operations denied to us.
    """

    @ddt.data(
        # Some file that's fairly harmless and that wouldn't have been
        # *specifically* blocked.
        "/etc/hosts",
        # Another quasi-harmless area of the filesystem
        "/proc/1/cmdline",
    )
    def test_cannot_read_os_files(self, file_path):
        """
        We can't read most files out in the broader OS.
        """
        code = dedent(f"""
          with open({file_path!r}, 'r') as f:
              f.read()
        """)
        (_, emsg) = call_api_code_error(code, {})
        assert f"PermissionError: [Errno 13] Permission denied: \\'{file_path}\\'" in emsg

    @ddt.data(
        # Generic OS paths
        "/sys",
        "/",
        "/tmp",
        # Parent directory contains other users' codejails
        "../",
    )
    def test_cannot_list_os_dirs(self, dir_path):
        """
        We can't list various directories.
        """
        code = dedent(f"""
          import os
          out = os.listdir({dir_path!r})
        """)
        (_, emsg) = call_api_code_error(code, {})
        assert f"PermissionError: [Errno 13] Permission denied: \\'{dir_path}\\'" in emsg

    @ddt.data(
        "/tmp/apitest.txt",
        "../apitest.txt",
    )
    def test_cannot_write_outside_sandbox(self, file_path):
        """
        We can't write to various places outside the sandbox.
        """
        code = dedent(f"""
          with open({file_path!r}, 'w') as f:
              f.write("test")
        """)
        (_, emsg) = call_api_code_error(code, {})
        assert f"PermissionError: [Errno 13] Permission denied: \\'{file_path}\\'" in emsg
