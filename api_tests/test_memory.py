"""
Tests for memory allocation.
"""

from api_tests.utils import call_api_code_error


def test_deny_large_allocate():
    call_api_code_error("out = len(bytearray(1000000000000))", {})
