API tests
#########

Functional and safety tests against the API of a running instance.

These are not unit tests, and are not run automatically as part of any Open edX CI workflow. The intention is for these to be run manually against a deployment as a regression test after any significant changes to the security infrastructure (e.g. the AppArmor profile, sandboxing layout, etc.)

These require the instance to be configured with AppArmor and sandboxing fully in effect. Tests must be run with environment variable ``API_TEST_SERVICE_BASE`` set to the base URL of the instance.

Example run, assuming a properly configured codejail-service is running on a local port::

  # activate Python 3.12 virtualenv, and then:
  make requirements
  export API_TEST_SERVICE_BASE=http://localhost:18030
  pytest --no-cov ./api_tests/

Test names and sabotage testing
*******************************

Tests are named according to the following:

* ``test_deny_*`` to show that sandboxing forbids an action
* ``test_allow_*`` to show that an action is permitted by sandboxing, indicating a contrast to a deny action (e.g. writing to certain file paths is allowed, even though others are denied)
* ``test_support_*`` to exercise features of the API or the code execution environment that aren't related to sandboxing

This allows for a type of "sabotage testing": If the sandboxing mechanism is disabled and the codejail-service altered to allow code execution anyway, we should expect the ``test_deny_*`` tests to start failing and the remaining tests to continue passing. This can be done manually in a local development environment to ensure that all of the tests are written properly. This could catch a poorly written deny test that is expecting the wrong error, or isn't specific enough. For example, a syntax error could cause a deny even though the action would be allowed if the syntax error were repaired.

To perform this sabotage testing in a development environment:

1. Set ``STARTUP_SAFETY_CHECK_OK = True`` in ``startup_checks.py``
2. Remove the apparmor confinement (e.g. remove ``security_opt`` if using Docker Compose)
3. Run pytest with ``-v`` so that individual tests are always reported, and pipe the results into ``grep -P '(test_deny.*PASSED|test_(allow|support)_.*FAILED)|py::test_(?!deny|allow|support)'`` to find:

   * denial tests that are still passing (which should not happen, and likely indicates a badly written test)
   * allow/support tests that are now failing for some reason (which would be strange, and should be investigated)
   * tests that do not follow the naming scheme
