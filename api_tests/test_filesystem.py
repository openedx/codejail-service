"""
Tests of filesystem access, allowed and denied.

Mostly should be denied, but parts of sandbox should be allowed.
"""

from textwrap import dedent
from unittest import TestCase

import ddt

from api_tests.utils import call_api_code_error, call_api_success


def test_allow_list_in_own_sandbox():
    """
    We can list files in our own sandbox.
    """
    code = "import os; out = os.listdir('.')"
    listing = call_api_success(code, {})["out"]
    # A few things we should expect the codejail library to have created:
    assert "tmp" in listing
    assert "jailed_code" in listing


# Standard path we'll use for write tests. The ./tmp/ dir in the sandbox should
# always exist and should be writable, as long as FSIZE is set reasonably.
WRITE_PATH = "tmp/api-test.txt"


def test_allow_write_in_own_sandbox():
    """
    We can create files in our own sandbox.
    """
    code = dedent(f"""
      with open({WRITE_PATH!r}, 'w') as f:
          f.write("sample")

      with open({WRITE_PATH!r}, 'r') as f:
          out = f.read()
    """)
    assert {"out": "sample"} == call_api_success(code, {})


def test_allow_delete_from_own_sandbox():
    """
    We can delete files in our own sandbox.
    """
    code = dedent(f"""
      with open({WRITE_PATH!r}, 'w') as f:
          f.write("sample")

      import os
      os.remove({WRITE_PATH!r})
    """)
    call_api_success(code, {})


def test_deny_write_large_file():
    """
    We can't write excessive amounts of data to a file.
    """
    code = dedent(f"""
      with open({WRITE_PATH!r}, 'w') as f:
          f.seek(1024 * 1024 * 1024)  # sparse file, potentially
          f.write('x')
    """)
    (_, emsg) = call_api_code_error(code, {})
    # 27 = EFBIG: File too large
    assert "OSError: [Errno 27] File too large" in emsg


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
    def test_deny_read_os_files(self, file_path):
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
    def test_deny_list_os_dirs(self, dir_path):
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
    def test_deny_write_outside_sandbox(self, file_path):
        """
        We can't write to various places outside the sandbox.
        """
        code = dedent(f"""
          with open({file_path!r}, 'w') as f:
              f.write("test")
        """)
        (_, emsg) = call_api_code_error(code, {})
        assert f"PermissionError: [Errno 13] Permission denied: \\'{file_path}\\'" in emsg


def test_allow_python_path():
    """
    Everything that's added to sys.path by the safe_exec prefix code should be
    listable or readable (if it exists).
    """
    code = dedent("""
      import os, os.path, sys

      out = ""
      for p in sys.path:
          if os.path.isdir(p):
              result = len(os.listdir(p))
          elif os.path.isfile(p):
              with open(p, 'r') as f:
                  result = f.read(1)
          else:
              result = "missing or other type"

          out += f"{p}: {result!r}\\n"
    """)
    globals_out = call_api_success(code, {})
    assert ": " in globals_out['out']
