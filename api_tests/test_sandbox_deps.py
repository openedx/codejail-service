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
      # A prelude that's required for running numpy, otherwise it will segfault.
      # In practice, edxapp adds this to all submitted code.
      import os
      os.environ['OPENBLAS_NUM_THREADS'] = '1'

      import numpy as np
      a = np.array([1, 2, 3, 4, 5])
      a = a * 2
      out = int(a[-1])
    """)
    assert {"out": 10} == call_api_success(code, {})


def test_support_matplotlib():
    """
    We can load matplotlib.

    matplotlib requires a place to create temporary files. We don't allow any of
    the usual locations (because they're global directories and we can't do
    automated cleanup of created files after the sandbox finishes). Instead, we
    can tell it to use the ./tmp subdirectory in the sandbox.

    It will still complain on stderr about a missing MPLCONFIGDIR environment variable
    if it can't use its preferred location of ~/.config/matplotlib but just setting
    the TMPDIR is fine.
    """
    code = dedent("""
      # A prelude that's required for importing matplotlib, otherwise it will
      # raise an exception. In practice, edxapp adds something like this to all
      # submitted code.
      import os
      os.environ['TMPDIR'] = 'tmp'

      image_path = "tmp/output.png"

      # Just plot the demo image from the standard tutorial
      import matplotlib.pyplot as plt
      _fig, ax = plt.subplots()
      ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
      plt.savefig(image_path)

      # Read part of the file header; these bytes should be b"PNG".
      # This just helps demonstrate that an image was rendered to disk.
      with open(image_path, 'rb') as f:
          out = f.read()[1:4]

      del image_path  # clean up globals
    """)
    assert {"out": 'PNG'} == call_api_success(code, {})
