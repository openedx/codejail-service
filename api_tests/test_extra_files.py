"""
Tests for uploading additional files and copying OS files into sandbox.

Copying of python_path entries to the sandbox is performed by the webapp,
and so AppArmor is not in effect. This means we have to take extra care here.
"""

import io
import zipfile
from textwrap import dedent

from api_tests.utils import call_api_rejection, call_api_success


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

    This is the standard happy path. When a course has a `python_lib.zip` file,
    edxapp automatically includes it this way.
    """
    globals_out = call_api_success(
        EXERCISE_LIBRARY, {},
        files={'python_lib.zip': PYTHON_LIB_BYTES}, python_path=['python_lib.zip'],
    )
    assert globals_out == EXPECTED_OUT


def test_deny_python_path_arbitrary_read():
    """
    Can't add arbitrary path to python_path (which would allow copying into sandbox).
    """
    (status, error) = call_api_rejection("out = 1 + 1", {}, python_path=["/etc"])
    assert status == 400
    assert error == "Only allowed entry in 'python_path' is 'python_lib.zip'"


def test_deny_uploaded_filename_arbitrary_write():
    """
    Can't abuse filename of uploaded file to drop files outside of sandbox.
    """
    (status, error) = call_api_rejection("out = 1 + 1", {}, files={'/tmp/test.txt': b"TEST"})
    assert status == 400
    assert error == "Only allowed name for uploaded file is 'python_lib.zip'"
