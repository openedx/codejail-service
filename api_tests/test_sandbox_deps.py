"""
Tests of availability of sandbox dependencies.
"""

from textwrap import dedent

from api_tests.utils import call_api_success


def test_support_basic_import():
    """
    We can load *any* part of *any* expected library.

    We use a library here that is unlikely to be in a generic virtualenv (such as
    the app's own virtualenv) but that also doesn't have complicated dependencies
    (especially C extensions, such as in numpy).
    """
    code = dedent("""
      import networkx
      out = networkx.__version__
    """)
    assert "out" in call_api_success(code, {})


def test_support_numpy():
    """
    We can use numpy arrays.

    numpy requires C extensions and is also a standard package to include
    in codejail.
    """
    code = dedent("""
      import numpy as np
      a = np.array([1, 2, 3, 4, 5])
      a = a * 2
      out = int(a[-1])
    """)
    assert {"out": 10} == call_api_success(code, {})
