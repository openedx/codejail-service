"""
Tests of basic functionality (just running generic Python).
"""

import re
from textwrap import dedent

from api_tests.utils import call_api_code_error, call_api_success


def test_support_globals_input_output():
    """
    We can use globals to pass inputs to the code and receive output.
    """
    globals_out = call_api_success(dedent("""
      # Top-level mutation of global bindings
      out = input * 2
      # Interior mutation of globals
      container.append(4)
    """), {"input": 21, "container": [1, 2, 3]})
    assert globals_out == {"input": 21, "out": 42, "container": [1, 2, 3, 4]}


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


def test_support_exception_traceback_stderr():
    """
    Exceptions from submitted code are serialized and returned, along with stderr.

    Globals aren't updated when there's an exception, even via mutation.
    """
    (globals_out, emsg) = call_api_code_error(dedent("""
      # Try updating some globals (won't show up in output globals, though)
      primitive = 22
      container.append(123)

      # stdout is suppressed by default (due to implementation detail -- codejail
      # delivers globals updates on stdout as JSON)
      print("some output to stdout --- suppressed")

      # stderr will be returned, though
      import sys
      print("other output to stderr", file=sys.stderr)

      # Raise an exception
      1/0
    """), {"primitive": 7, "container": []})

    # The codejail library isn't actually able to provide updated globals when
    # there's an exception. If we want to change that behavior, this test will need
    # to change too.
    #
    # This isn't a behavior we specifically want to *preserve*; this part of the
    # test just illustrates the effect.
    assert globals_out == {"primitive": 7, "container": []}
    # The emsg contains the stdout, stderr, and status code. In practice, the
    # stdout is going to be suppressed unless the submitted code specifically
    # works around the suppression (which is just there to prevent inadvertent
    # failures, not for security purposes). stderr is going to have the error
    # message embedded as part of a traceback printed to stderr.
    #
    # Here, we're converting line numbers to constants in order to make
    # string comparisons work.
    emsg_comparable = re.sub(r' line [0-9]+', ' line NN', emsg)
    assert emsg_comparable == (
        "Couldn't execute jailed code: stdout: b'', "
        r"stderr: b'other output to stderr\nTraceback (most recent call last):\n"
        r'  File "jailed_code", line NN, in <module>\n    exec(code, g_dict)\n'
        r'  File "<string>", line NN, in <module>\n'
        r"ZeroDivisionError: division by zero\n' with status code: 1"
    )
