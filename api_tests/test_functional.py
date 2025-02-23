"""
Tests of basic functionality (just running generic Python).
"""

from textwrap import dedent

from api_tests.utils import call_api_success


def test_support_globals_input_output():
    """
    We can use globals to pass inputs to the code and receive output.
    """
    assert {"input": 21, "out": 42} == call_api_success("out = input * 2", {"input": 21})


def test_support_define_function():
    """
    We can run multi-line code and define functions.
    """
    code = dedent("""
      def doubler(x):
          return x * 2

      out = doubler(input)
    """)
    assert {"input": 50, "out": 100} == call_api_success(code, {"input": 50})


def test_support_selective_serialization():
    """
    Only serializable globals are returned; others are simply omitted.
    """
    assert {"out2": "hi"} == call_api_success("out1 = object(); out2 = 'hi'", {})
