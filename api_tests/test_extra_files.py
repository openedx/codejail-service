"""
Tests for uploading additional files and copying OS files into sandbox.
"""

import io
import zipfile
from textwrap import dedent

from api_tests.utils import call_api_success


def make_python_library_zip_bytes():
    """
    Make a simple course library ZIP file, returning the bytes.

    Contains one module, `course_library`, with a function `triangular_number`.
    """
    memfile = io.BytesIO()
    with zipfile.ZipFile(memfile, 'w') as z:
        z.writestr(
            'course_library.py',
            dedent("""
              def triangular_number(n):
                  return sum(range(n + 1))
            """),
        )

    memfile.seek(0)
    return memfile.read()


PYTHON_LIB_BYTES = make_python_library_zip_bytes()
# Code to exercise the uploaded library.
EXERCISE_LIBRARY = """
from course_library import triangular_number
out = triangular_number(6)
"""
# Expected globals output when the above code is run.
EXPECTED_OUT = {'out': 21}


def test_support_upload_file():
    """
    Can upload a python_lib.zip file and add it to the Python path.
    """
    globals_out = call_api_success(
        EXERCISE_LIBRARY, {},
        files={'python_lib.zip': PYTHON_LIB_BYTES}, python_path=['python_lib.zip'],
    )
    assert globals_out == EXPECTED_OUT
