API tests
#########

Functional and safety tests against the API of a running instance.

These require the instance to be configured with AppArmor and sandboxing fully in effect. Tests must be run with environment variable ``API_TEST_SERVICE_BASE`` set to the base URL of the instance.

Example run, assuming a properly configured codejail-service is running on a local port::

  # activate Python 3.12 virtualenv, and then:
  make requirements
  export API_TEST_SERVICE_BASE=http://localhost:18030
  pytest --no-cov ./api_tests/
