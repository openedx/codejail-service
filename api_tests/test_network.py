"""
Tests of network access, all should be denied.

This includes both high-level and low-level tests to ensure good coverage.
"""

from textwrap import dedent
from unittest import TestCase

import ddt

from api_tests.utils import call_api_code_error, call_api_success


def test_deny_make_http_call():
    """
    HTTP call involves both UDP and TCP outwards connections, so
    it will fail even if only one of those is blocked. But it's a good
    high-level test.
    """
    code = dedent("""
      import urllib.request
      urllib.request.urlopen('http://www.example.org/')
    """)
    (_, emsg) = call_api_code_error(code, {})
    assert "urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>" in emsg


def test_deny_resolve_dns():
    """
    No DNS lookups. This uses UDP.
    """
    code = "import socket; out = socket.gethostbyname('example.com')"
    (_, emsg) = call_api_code_error(code, {})
    assert "nsocket.gaierror: [Errno -2] Name or service not known" in emsg


@ddt.ddt
class TestSocketCreate(TestCase):
    """
    Tests on collections of socket configs. (Need class for ddt.)
    """

    @ddt.unpack
    @ddt.data(
        ('socket.AF_INET', 'socket.SOCK_STREAM'),
        ('socket.AF_INET', 'socket.SOCK_DGRAM'),
        ('socket.AF_INET6', 'socket.SOCK_STREAM'),
        ('socket.AF_INET6', 'socket.SOCK_DGRAM'),
        ('socket.AF_NETLINK', 'socket.SOCK_RAW'),
    )
    def test_deny_create_socket(self, address_family, socket_type):
        """
        Can't create a socket (even without calling bind or connect).
        """
        code = dedent(f"""
          import socket
          socket.socket({address_family}, {socket_type})
        """)
        (_, emsg) = call_api_code_error(code, {})
        assert "PermissionError: [Errno 13] Permission denied" in emsg


class TestUnixSocket(TestCase):
    """
    Unlike other socket types, Unix sockets are allowed (they're local files).

    This isn't something we specifically support, but it's not problematic as long as
    socket creation only happens within the sandbox.
    """

    def code_for_create_socket(self, path):
        return dedent(f"""
          import socket
          s = socket.socket(socket.AF_UNIX, socket.SOCK_RAW)
          s.bind("{path}.0.0")
          # Just proving we have created some kind of socket
          out = s.fileno()
        """)

    def test_allow_in_sandbox(self):
        """Allowed when in own sandbox's tmp dir."""
        code = self.code_for_create_socket("./tmp/test-socket")
        globals_out = call_api_success(code, {})
        # The actual value isn't strictly predictable
        assert isinstance(globals_out['out'], int)

    def test_deny_elsewhere(self):
        """Denied when in OS tmp dir."""
        code = self.code_for_create_socket("/tmp/test-socket")
        (_, emsg) = call_api_code_error(code, {})
        assert "PermissionError: [Errno 13] Permission denied" in emsg
