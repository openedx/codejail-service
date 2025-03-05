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

Limitations
***********

Some aspects of the sandbox can't be readily tested in an automated fashion, or can't be tested thoroughly.

* The sandboxed code should not have access to the environment variables that are set in the webapp's environment; these may contain sensitive information. The ``sudo`` call that codejail makes should have a side effect of creating a new environment mapping.  However, it's not clear exactly what we should look for if we wanted to test this properly.

  * The tests check for a few likely env vars, but it is not certain that they have been set, so the test might provide a false negative.
  * The API tests will check for the presence of ``CJS_TEST_ENV_LEAKAGE``, an optional variable that can be used for testing. Deployers are encouraged to set ``export CJS_TEST_ENV_LEAKAGE=yes`` in their webapp's environment so that this test can reliably detect leakage.

* Process limits are configurable, and these tests aren't aware of what configuration has been performed in the deployment. It's difficult to write tests that will pass for all working deployments.

  * Tests have been added for excessive runtime, memory allocation, file size, and process forking. The tests use truly excessive inputs (e.g. 1 GB of memory) to ensure that any general-purpose deployment's reasonable limits are passed. Deployments that have occasion to allow more extreme resource use may need to adjust these tests.
  * CPU time is not tested, as it can't meaningfully be tested independently of wall clock time (at least without knowing in advance the forking limit).
  * Only single-file size limit is tested, as codejail's process-limit mechanism cannot limit totalled filesystem writes.
  * Deployers could augment the existing API tests using knowledge of their own configured limits. However, the codejail library has unit tests for process limits, and it may be better to rely on those tests to ensure that the configuration mechanism works properly. (Process limits are configured in-process, and are therefore less fragile and less in need of API tests than the AppArmor-based confinement mechanism.)
