"""
Shared utils for API tests.
"""

import functools
import json
import os

import pytest
import requests


@functools.lru_cache
def _get_exec_url():
    """
    Get the code-exec URL.
    """
    base_url = os.getenv("API_TEST_SERVICE_BASE")
    if base_url is None:
        raise Exception("API_TEST_SERVICE_BASE environment variable missing; see api_tests/README.rst.")
    return f"{base_url}/api/v0/code-exec"


def call_api(code, globals_dict, /, *, files=None, python_path=None):
    """
    Call the code-exec API.

    Args:
      code: Python code being submitted for execution
      globals_dict: Dict containing additional global scope
      files: Dict of file names to bytestrings of their contents
      python_path: List of paths to copy into sandbox and put on Python path

    Returns a requests.Response object.
    """
    url = _get_exec_url()
    payload = json.dumps({
        "code": code,
        "globals_dict": globals_dict,
        "python_path": python_path,
        # Help operators detect that weird/broken calls they're seeing in
        # codejail-service might actually be from the API tests, not a broken
        # client.
        "slug": "codejail-service-api-tests",
    })
    return requests.post(url, data={"payload": payload}, files=files, timeout=50.0)


def get_success_globals(resp):
    """
    Assert that this response object was a success, and return the globals_dict.

    This is both an assertion and a response parser.
    """
    if resp.status_code != 200:
        pytest.fail(f"Expected response code 200, but was {resp.status_code}")

    ct = resp.headers.get('content-type')
    if ct != 'application/json':
        pytest.fail(f"Expected JSON content type, but was {ct}")
    json_out = resp.json()

    if 'globals_dict' not in json_out:
        pytest.fail(f"globals_dict missing from output: {json_out}")
    if 'emsg' in json_out:
        pytest.fail(f"Unexpected error message (emsg): {json_out['emsg']!r}")

    return json_out['globals_dict']


def get_code_error(resp):
    """
    Assert error message (emsg) in response and return a tuple of (globals_dict, emsg).

    This is for errors arising from code execution, rather than from
    generic client or server errors.

    This is both an assertion and a response parser.
    """
    if resp.status_code != 200:
        pytest.fail(f"Expected response code 200, but was {resp.status_code}")

    ct = resp.headers.get('content-type')
    if ct != 'application/json':
        pytest.fail(f"Expected JSON content type, but was {ct}")
    json_out = resp.json()

    if 'globals_dict' not in json_out:
        pytest.fail(f"globals_dict missing from output: {json_out}")
    if 'emsg' not in json_out:
        pytest.fail(f"emsg missing from output: {json_out}")

    return (json_out['globals_dict'], json_out['emsg'])


def get_api_rejection(resp):
    """
    Assert 4XX or 5XX error and return a tuple of (status, error message).

    This is for generic client or server errors, not code execution failure.

    This is both an assertion and a response parser.
    """
    if resp.status_code < 400:
        pytest.fail(f"Expected response code 4XX or 5XX, but was {resp.status_code}")

    ct = resp.headers.get('content-type')
    if ct != 'application/json':
        pytest.fail(f"Expected JSON content type, but was {ct}")
    json_out = resp.json()

    if 'error' not in json_out:
        pytest.fail(f"error missing from output: {json_out}")

    return (resp.status_code, json_out['error'])


def call_api_success(*args, **kwargs):
    """
    Call `call_api` and `get_success_globals`, chained.
    """
    return get_success_globals(call_api(*args, **kwargs))


def call_api_code_error(*args, **kwargs):
    """
    Call `call_api` and `get_code_error`, chained.
    """
    return get_code_error(call_api(*args, **kwargs))


def call_api_rejection(*args, **kwargs):
    """
    Call `call_api` and `get_api_rejection`, chained.
    """
    return get_api_rejection(call_api(*args, **kwargs))
