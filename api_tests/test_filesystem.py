"""
Tests of filesystem access, allowed and denied.

Mostly should be denied, but parts of sandbox should be allowed.
"""

from textwrap import dedent

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


def test_cannot_read_os_files():
    """
    We can't read most files out in the broader OS.
    """
    # Some file that's fairly harmless and that wouldn't have been
    # *specifically* blocked.
    code = dedent("""
      with open("/etc/hosts", 'r') as f:
          f.read()
    """)
    (_, emsg) = call_api_code_error(code, {})
    assert "PermissionError: [Errno 13] Permission denied: \\'/etc/hosts\\'" in emsg
