Configuration and deployment
############################

codejail-service has some unusual requirements due to its sensitive nature. **Please read all sections carefully.**

Before you begin
****************

Ensure your intended deployment environment meets the following prerequisites:

* Ubuntu, Debian, or another Linux distribution that supports AppArmor
* AppArmor 3 or newer (e.g. in Ubuntu 22.04 or newer)
* The ability to load an AppArmor profile into the host and (if using Docker) apply the profile to a Docker container

Network
*******

If at all possible, your codejail-service cluster should be run with the following networking restrictions:

* No inbound access from the public internet. codejail-service lacks authentication, rate-limiting, audit logs, and other protections, and its functionality should only be exposed via Custom Python-evaluated Input Problems in the LMS and CMS.
* No outbound connections, *especially* to other services within your deployment. This will help limit the impact if an attacker were to figure out how to escape the sandbox.

Host
****

The host or Docker image must be set up with a sandbox user, sandbox virtualenv, and sudoers file according to the documentation of the `codejail library <https://github.com/openedx/codejail>`__. This forms the foundation of the sandboxing, but does not provide much security by itself.

See `2U's Dockerfile <https://github.com/edx/public-dockerfiles/blob/main/dockerfiles/codejail-service.Dockerfile>`__ for an example of how you could set up your host or container. (As of March 2025, there is `not yet a Tutor plugin <https://github.com/openedx/codejail-service/issues/26>`__.)

AppArmor
********

Again following the codejail library's instructions, create an AppArmor profile and load it into the host.

This profile will need to be customized according to your service's app user, sandbox setup, and other details. It will also look different if you are using Docker or running the service dierctly on the host. For reference, here is `2U's AppArmor profile <https://github.com/edx/public-dockerfiles/blob/main/apparmor/openedx_codejail_service.profile>`__; note that the inner profile is the one that actually applies the sandboxing.

Django settings
***************

Now you can set your ``CODE_JAIL`` Django setting, which tells the codejail library where the sandboxed Python executable lives, and how to limit resource usage. See the codejail library's documentation for details. (Note: Leave the ``PROXY`` setting to its default of ``0``.)

Starting the service
********************

To run the service, activate a virtualenv, run ``make prod_requirements``, and start the service with ``gunicorn`` using a command like this::

  export DJANGO_SETTINGS_MODULE=codejail_service.settings.production
  gunicorn -c codejail_service/docker_gunicorn_configuration.py \
    --bind '0.0.0.0:8080' --workers=10 --max-requests=1000 --name codejail \
    codejail_service.wsgi:application

The service is now listening on port 8080.

There is a healthcheck endpoint at ``/health/`` which responds to a GET with ``200 OK`` if the service is running and healthy, or a ``503 Service Unavailable`` otherwise. The healthcheck is driven by a handful of security tests that the service performs. If the healthcheck is failing, this likely indicates that there is a misconfiguration that would allow unsandboxed code execution.

Enabling code execution
***********************

Once the healthcheck is passing (indicating that sandboxing is probably functional), the main code-exec endpoint can be enabled with a Django setting: ``CODEJAIL_ENABLED = True``. This should not be enabled until the healthcheck passes, and should be immediately followed with API tests (see next section), which include a more comprehensive set of tests than the healthcheck performs.

API tests
*********

After the first setup, and after any significant change to security settings, run the tests in ``./api_tests/`` (see README in that directory). This will probe the service for a variety of possible vulnerabilities.

These tests can also be incorporated into your deployment pipeline.
