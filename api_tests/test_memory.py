"""
Tests for memory allocation.
"""

from textwrap import dedent

from api_tests.utils import call_api_code_error


def test_deny_large_allocate():
    """
    Can't allocate large amounts of memory.
    """
    # Try to allocate 1 GiB. This is a reasonable amount to allocate on a normal
    # system, but an unreasonable amount within a sandbox. (We don't know what
    # limit has actually been configured in the deployment.)
    code = dedent("""
      # Spread the allocation across a number of more reasonably sized objects
      arr = [bytearray(1024 * 32) for _ in range(32 * 1024)]
      out = len(arr)
    """)
    (_, emsg) = call_api_code_error(code, {})
    assert "MemoryError" in emsg
