"""
Test codejail service views.
"""

import io
import json
import textwrap
from os import path
from unittest.mock import call, patch

import ddt
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from codejail_service import startup_check


@override_settings(
    ROOT_URLCONF='codejail_service.urls',
    CODEJAIL_ENABLED=True,
)
@ddt.ddt
class TestExecService(TestCase):
    """Test the v0 code exec view."""

    def setUp(self):
        super().setUp()
        # We can't configure apparmor for regular unit tests, so just
        # pretend startup was OK and the sandbox is working.
        #
        # This approach means we can't parallelize the tests, but it's concise.
        startup_check.STARTUP_SAFETY_CHECK_OK = True
        self.standard_params = {'code': 'retval = 3 + 4', 'globals_dict': {}}

    def tearDown(self):
        startup_check.STARTUP_SAFETY_CHECK_OK = None

    def test_missing_payload(self):
        """Handle missing payload param gracefully."""
        client = APIClient()
        resp = client.post('/api/v0/code-exec', {}, format='multipart')
        assert resp.status_code == 400
        assert json.loads(resp.content) == {'error': "Missing 'payload' parameter in POST body"}

    def test_malformed_payload(self):
        """Handle malformed payload param gracefully."""
        client = APIClient()
        resp = client.post('/api/v0/code-exec', {'payload': "Not JSON"}, format='multipart')
        assert resp.status_code == 400
        assert json.loads(resp.content) == {
            'error': "Unable to parse payload JSON: Expecting value: line 1 column 1 (char 0)",
        }

    def _test_codejail_api(self, *, params=None, files=None, exp_status, exp_body):
        """
        Call the view and make assertions.

        Args:
            params: Payload of codejail parameters, defaulting to a simple arithmetic check
            files: Files to include in the API call, as dict of filenames to file objects
            exp_status: Assert that the response HTTP status code is this value
            exp_body: Assert that the response body JSON is this value
        """
        client = APIClient()

        params = self.standard_params if params is None else params
        payload = json.dumps(params)
        req_body = {'payload': payload, **(files or {})}

        resp = client.post('/api/v0/code-exec', req_body, format='multipart')

        assert resp.status_code == exp_status
        assert json.loads(resp.content) == exp_body

    @override_settings(CODEJAIL_ENABLED=False)
    def test_feature_disabled(self):
        """Code-exec can be disabled."""
        self._test_codejail_api(
            exp_status=500, exp_body={'error': "Codejail service not enabled"},
        )

    @patch('codejail_service.apps.api.v0.views.is_exec_safe', return_value=None)
    def test_unhealthy(self, _mock_is_safe_exec):
        """Code-exec prevented by failing startup checks."""
        self._test_codejail_api(
            exp_status=500, exp_body={'error': "Codejail service is not correctly configured"},
        )

    @patch('codejail_service.apps.api.v0.views.set_custom_attribute')
    def test_success(self, mock_set_custom_attribute):
        """Regular successful call."""
        self._test_codejail_api(
            exp_status=200, exp_body={'globals_dict': {'retval': 7}},
        )
        assert mock_set_custom_attribute.call_args_list == [
            call('codejail.exec.python_path_len', 0),
            call('codejail.exec.files_count', 0),
            call('codejail.exec.status', 'executed.success'),
        ]

    def test_unsafely(self):
        """unsafely=true is rejected"""
        self._test_codejail_api(
            params={**self.standard_params, 'unsafely': True},
            exp_status=400, exp_body={'error': "Refusing codejail execution with unsafely=true"},
        )

    @ddt.unpack
    @ddt.data(
        ({'globals_dict': {}}, 'code'),
        ({'code': 'retval = 3 + 4'}, 'globals_dict'),
        ({}, 'code'),
    )
    def test_missing_params(self, params, missing):
        """Two code and globals_dict params are required."""
        self._test_codejail_api(
            params=params,
            exp_status=400, exp_body={
                'error': f"Payload JSON did not match schema: '{missing}' is a required property",
            },
        )

    def test_course_library(self):
        """Check that we can include a course library."""
        # "Course library" containing `course_library.triangular_number`.
        #
        # It's tempting to use zipfile to write to an io.BytesIO so
        # that the test library is in plaintext. Django's request
        # factory will indeed see that as a file to use in a multipart
        # upload, but it will see it as an empty bytestring. (read()
        # returns empty bytestring, while getvalue() returns the
        # desired data). So instead we just have a small zip file on
        # disk here.
        library_path = path.join(path.dirname(__file__), 'test_course_library.zip')

        with open(library_path, 'rb') as lib_zip:
            self._test_codejail_api(
                params={
                    'code': textwrap.dedent("""
                        from course_library import triangular_number

                        result = triangular_number(6)
                    """),
                    'globals_dict': {},
                    'python_path': ['python_lib.zip'],
                },
                files={'python_lib.zip': lib_zip},
                exp_status=200, exp_body={'globals_dict': {'result': 21}},
            )

    @patch('codejail_service.apps.api.v0.views.set_custom_attribute')
    def test_reject_unknown_python_path(self, mock_set_custom_attribute):
        """We need to reject unknown python_path for security reasons."""
        self._test_codejail_api(
            params={'code': "out = 1 + 1", 'globals_dict': {}, 'python_path': ['something']},
            exp_status=400,
            exp_body={'error': "Only allowed entry in 'python_path' is 'python_lib.zip'"},
        )
        mock_set_custom_attribute.assert_has_calls([
            call('codejail.exec.python_path_len', 1),
            call('codejail.exec.status', 'invalid.python_path'),
        ], any_order=True)

    @patch('codejail_service.apps.api.v0.views.set_custom_attribute')
    def test_reject_unknown_extra_files(self, mock_set_custom_attribute):
        """We need to reject unknown filenames for security reasons."""
        self._test_codejail_api(
            params={'code': "out = 1 + 1", 'globals_dict': {}},
            # Use a BytesIO to make requests treat this value as a file
            files={'unknown.zip': io.BytesIO(b'TESTING')},
            exp_status=400,
            exp_body={'error': "Only allowed name for uploaded file is 'python_lib.zip'"},
        )
        mock_set_custom_attribute.assert_has_calls([
            call('codejail.exec.files_count', 1),
            call('codejail.exec.status', 'invalid.files'),
        ], any_order=True)

    @patch('codejail_service.apps.api.v0.views.set_custom_attribute')
    def test_exception(self, mock_set_custom_attribute):
        """Report exceptions from jailed code."""
        self._test_codejail_api(
            params={'code': '1/0', 'globals_dict': {}},
            exp_status=200,
            exp_body={
                'globals_dict': {},
                'emsg': 'ZeroDivisionError: division by zero',
            },
        )
        mock_set_custom_attribute.assert_any_call('codejail.exec.status', 'executed.error')

    @patch('codejail_service.apps.api.v0.views.set_custom_attribute')
    def test_can_pass_limit_override(self, mock_set_custom_attribute):
        """Test that limit override is accepted."""
        self._test_codejail_api(
            params={
                'code': 'out = 1 + 1',
                'globals_dict': {},
                'limit_overrides_context': 'xxxxxxx some junk xxxxxxxx',
            },
            exp_status=200,
            exp_body={'globals_dict': {'out': 2}},
        )
        mock_set_custom_attribute.assert_any_call(
            'codejail.exec.limit_override', 'xxxxxxx some junk xxxxxxxx',
        )
