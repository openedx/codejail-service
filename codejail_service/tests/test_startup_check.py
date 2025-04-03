"""
Tests for startup safety and function check.
"""

from unittest.mock import Mock, call, patch
from urllib.error import URLError

import ddt
from django.test import TestCase

from codejail_service import startup_check
from codejail_service.startup_check import is_exec_safe, run_startup_safety_check


class TestStateCheck(TestCase):

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_baseline(self):
        assert is_exec_safe() is False

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', "hello")
    def test_weird_value(self):
        assert is_exec_safe() is False

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', True)
    def test_healthy(self):
        assert is_exec_safe() is True


DEFAULT = object()


def responses(math=DEFAULT, disk=DEFAULT, child=DEFAULT, network=DEFAULT):
    """
    Return a list of the expected safe_exec responses, with optional overrides.

    This is intended to be used in mocking out safe_exec in the exact
    sequence of calls that the startup safety check function
    makes. Each value in the list must be a return value of
    safe_exec -- that is, a 2-tuple of the returned globals and an error
    message string. (Error message slot will be `None` on success.)

    The default list of responses will satisfy the startup checks and
    should result in a "we're healthy" state. The kwargs
    can be overridden with alternative responses to those individual
    checks (`_check_basic_function` etc.) in order to test whether those
    responses provoke an "unhealthy" determination.
    """
    if math is DEFAULT:
        math = ({'x': 17}, None)
    if disk is DEFAULT:
        disk = ({}, "... PermissionError: [Errno 13] Permission denied ...")
    if child is DEFAULT:
        child = ({}, "... PermissionError: [Errno 13] Permission denied ...")
    if network is DEFAULT:
        network = ({}, "... PermissionError: [Errno 13] Permission denied ...")

    return [math, disk, child, network]


@ddt.ddt
class TestInit(TestCase):

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_unsafe_tests_default(self):
        """
        The test environment is unconfined, so the safety checks should fail.
        """
        run_startup_safety_check()
        assert startup_check.STARTUP_SAFETY_CHECK_OK is False

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    @patch('codejail_service.startup_check.log.error')
    @patch('codejail_service.startup_check.safe_exec', side_effect=Exception("oops"))
    def test_check_throws(self, _mock_safe_exec, mock_log_error):
        """
        Exceptions raised by startup checks should be caught and turned into a failure.

        (The checks should catch any exceptions themselves; this is just a backstop.)
        """
        run_startup_safety_check()
        assert startup_check.STARTUP_SAFETY_CHECK_OK is False

        # Confirm log message for at least one of the checks
        assert mock_log_error.call_args_list[0] == call(
            '''Startup check 'Basic code execution' failed with: "Uncaught exception from check: Exception('oops')"'''
        )

    @ddt.data(
        # Baseline mocked values: Everything passes.
        (responses(), True),
        # Extraneous globals don't cause a check failure
        (responses(math=({'x': 17, 'unrelated': 'ignored'}, None)), True),

        # Wrong exception message
        (responses(disk=({}, "... Module not found ...")), False),
        (responses(child=({}, "... Module not found ...")), False),
        (responses(network=({}, "... Module not found ...")), False),
        # Lack of an exception
        (responses(disk=({}, None)), False),
        (responses(child=({}, None)), False),
        (responses(network=({}, None)), False),
        # Wrong value for global
        (responses(math=({'x': 999}, None)), False),
        # Missing global
        (responses(math=({'y': 17}, None)), False),
        # Exception when expecting a value
        (responses(math=({}, "Divide by zero")), False),

        # Some checkers may look for multiple possible exceptions
        (responses(child=({}, "... PermissionError: [Errno 13] Permission denied ...")), True),
        (responses(child=({}, "... BlockingIOError: [Errno 11] Resource temporarily unavailable ...")), True),
    )
    @ddt.unpack
    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_safe_exec_success_and_failure_modes(self, safe_exec_responses, expected_status):
        """
        Test various unexpected safe_exec responses, via mocking.
        """
        with (
                patch(
                    'codejail_service.startup_check.safe_exec',
                    side_effect=safe_exec_responses,
                ) as mock_safe_exec,
                # Mock out this check with an expected error so it will
                # pass. (It doesn't use safe_exec so we're not going to exercise
                # it in this test.)
                patch(
                    'codejail_service.startup_check.urllib.request.urlopen',
                    side_effect=URLError(PermissionError(13, 'Permission denied')),
                ) as mock_urlopen,
        ):
            run_startup_safety_check()

        assert startup_check.STARTUP_SAFETY_CHECK_OK is expected_status
        assert mock_safe_exec.call_count == 4
        mock_urlopen.assert_called_once()

    @ddt.data(
        # Example of an error that should be treated as a passing check
        ({'side_effect': URLError(PermissionError(13, 'Permission denied'))}, True),

        # Some unexpected error type
        ({'side_effect': Exception('Something else')}, False),
        # A successful HTTP call is a check failure
        ({'return_value': Mock(status=200)}, False),
    )
    @ddt.unpack
    @patch('codejail_service.startup_check.set_custom_attribute')
    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_egress_success_and_failure(self, mock_args, expected_status, mock_set_custom_attribute):
        """
        Test egress check pass/fail responses, via mocking.
        """
        with (
                patch('codejail_service.startup_check.urllib.request.urlopen', **mock_args) as mock_urlopen,
                # Mock out safe_exec with passing responses so they don't interfere with this test.
                patch('codejail_service.startup_check.safe_exec', side_effect=responses()),
        ):
            run_startup_safety_check()

        assert startup_check.STARTUP_SAFETY_CHECK_OK is expected_status
        mock_urlopen.assert_called_once()

        # Piggy-backing on this test to look at our monitoring calls as well
        expected_status_attr_value = 'pass' if expected_status else 'fail'
        assert mock_set_custom_attribute.call_args_list == [
            # The other checks
            call('codejail.startup_check.functionality', 'pass'),
            call('codejail.startup_check.disk', 'pass'),
            call('codejail.startup_check.exec', 'pass'),
            call('codejail.startup_check.network', 'pass'),
            # This check
            call('codejail.startup_check.webapp_egress', expected_status_attr_value),
            # Aggregate value
            call('codejail.startup_check.status', expected_status_attr_value),
        ]

    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_logging(self):
        """
        Check that we get useful log messages.

        This relies on safe_exec actually getting called, but in
        unsafe mode (because unit tests don't run under confinement.)
        """
        with (
                patch('codejail_service.startup_check.log.info') as mock_log_info,
                patch('codejail_service.startup_check.log.error') as mock_log_error,
                # Mock this out with a "bad" response so we don't have to be
                # online/have good internet to run tests.
                patch(
                    'codejail_service.startup_check.urllib.request.urlopen',
                    return_value=Mock(status=200)
                ) as mock_urlopen,
        ):
            run_startup_safety_check()

        assert startup_check.STARTUP_SAFETY_CHECK_OK is False

        assert mock_log_info.call_args_list == [
            call("Startup check 'Basic code execution' passed"),
        ]
        mock_urlopen.assert_called_once()

        expected_error_log_snippets = [
            "Startup check 'Block sandbox escape by disk access' failed with: "
            "\"Expected error, but code ran successfully. Globals: {'ret': ['",

            "Startup check 'Block sandbox escape by process execution' failed with: "
            r'''"Expected error, but code ran successfully. Globals: {'ret': '1970\\n'}"''',

            "Startup check 'Block network access' failed with: "
            "\"Expected error, but code ran successfully. Globals: {'filedesc': ",

            "Startup check 'Block egress from webapp' failed with: "
            "'Expected URLError, but received response (status code 200)'",
        ]
        assert len(mock_log_error.call_args_list) == len(expected_error_log_snippets)
        for call_args, snippet in zip(mock_log_error.call_args_list, expected_error_log_snippets):
            assert snippet in call_args[0][0]

    @ddt.data(True, False)
    def test_skip_reinit(self, starting_state):
        """
        If startup check has already run, don't run it again.
        """
        with (
                patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', starting_state),
                patch('codejail_service.startup_check.safe_exec') as mock_safe_exec,
        ):
            run_startup_safety_check()
            assert startup_check.STARTUP_SAFETY_CHECK_OK is starting_state

        mock_safe_exec.assert_not_called()
