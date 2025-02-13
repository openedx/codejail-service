"""
Tests for startup safety and function check.
"""

from unittest.mock import call, patch

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


def responses(math=DEFAULT, disk=DEFAULT, child=DEFAULT):
    """
    Return a list of the expected safe_exec responses, with optional overrides.

    This is intended to be used in mocking out safe_exec in the exact
    sequence of calls that the startup safety check function
    makes. Each value in the list must be a return value of
    safe_exec -- that is, a 2-tuple of the returned globals and an error
    message string. (Error message slot will be `None` on success.)

    The default list of responses will satisfy the startup checks and
    should result in a "we're healthy" state. The math/disk/child kwargs
    can be overridden with alternative responses to those individual
    checks (`_test_basic_function` etc.) in order to test whether those
    responses provoke an "unhealthy" determination.
    """
    if math is DEFAULT:
        math = ({'x': 17}, None)
    if disk is DEFAULT:
        disk = ({}, "... Permission denied ...")
    if child is DEFAULT:
        child = ({}, "... Permission denied ...")

    return [math, disk, child]


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
            '''Startup test 'Basic code execution' failed with: "Uncaught exception from test: Exception('oops')"'''
        )

    @ddt.data(
        # Baseline mocked values: Everything passes.
        (responses(), True),
        # Extraneous globals don't cause a check failure
        (responses(math=({'x': 17, 'unrelated': 'ignored'}, None)), True),

        # Wrong exception message
        (responses(disk=({}, "... Module not found ...")), False),
        (responses(child=({}, "... Module not found ...")), False),
        # Lack of an exception
        (responses(disk=({}, None)), False),
        (responses(child=({}, None)), False),
        # Wrong value for global
        (responses(math=({'x': 999}, None)), False),
        # Missing global
        (responses(math=({'y': 17}, None)), False),
        # Exception when expecting a value
        (responses(math=({}, "Divide by zero")), False),
    )
    @ddt.unpack
    @patch('codejail_service.startup_check.STARTUP_SAFETY_CHECK_OK', None)
    def test_success_and_failure_modes(self, safe_exec_responses, expected_status):
        """
        Test various unexpected safe_exec responses, via mocking.
        """
        with patch(
                'codejail_service.startup_check.safe_exec',
                side_effect=safe_exec_responses,
        ) as mock_safe_exec:
            run_startup_safety_check()
        assert startup_check.STARTUP_SAFETY_CHECK_OK is expected_status
        assert mock_safe_exec.call_count == 3

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
        ):
            run_startup_safety_check()

        assert startup_check.STARTUP_SAFETY_CHECK_OK is False

        assert mock_log_info.call_args_list == [
            call("Startup test 'Basic code execution' passed"),
        ]

        assert len(mock_log_error.call_args_list) == 2
        assert (
            "Startup test 'Block sandbox escape by disk access' failed with: "
            "\"Expected error, but code ran successfully. Globals: {'ret': ['"
        ) in mock_log_error.call_args_list[0][0][0]
        assert (
            "Startup test 'Block sandbox escape by child process' failed with: "
            r'''"Expected error, but code ran successfully. Globals: {'ret': '42\\n'}"'''
        ) == mock_log_error.call_args_list[1][0][0]

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
