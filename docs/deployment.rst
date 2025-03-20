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

App user UID
============

The UID under which the webapp runs must be running as few other processes as possible, otherwise the ``NPROC`` setting will need to be elevated to the point of uselessness.

Recommendation
--------------

* Select a UID and GID for the webapp user: ``python3 -c 'import random; print(random.randrange(3000, 2 ** 31))'``.
* Create a user and group for the webapp user using this as its UID and GID.
* Do the same for the sandbox user, with a new value.
* In Kubernetes (or other orchestration system), consider limiting the number of codejail-service instances that are permitted to be scheduled on the same host as each other.

Context
-------

This issue is due to an interaction of several kernel features:

* The ``RLIMIT_NPROC`` mechanism that we use to limit the number of processes the sandbox process can create actually shares its usage pool with *all* of the processes owned by the same UID. If a process has ``NPROC`` set and needs to fork, that value must be higher than the *existing* number of processes (and threads) owned by the same UID.
* Docker cannot isolate UIDs in containers, just the *mapping* of usernames to UIDs. If the web service runs as ``app`` inside the container but has user ID 1000 (the most likely situation), the kernel doesn't see any distinction between that and a user on the host that also has UID 1000.

If the webapp runs with UID 1000, and there is also a user with UID 1000 on the host, then they participate in the same usage pool. On a typical Linux desktop, it is common for there to be ~1200 processes and threads already in use by the default user. Running codejail-service in a Docker container on that host with UID 1000 would require ``CODE_JAIL.limits.NPROC`` to be set to 2000 or so in order to ensure there is headroom. This is a much higher limit than we actually want for a sandbox.

On an actual deployment host with no regular users, just system users (with UID < 1000), and no other services running in other containers, this might work. However, the most likely deployment situation is in Kubernetes, where there may be a number of other pods; many of these pods will be using UID 1000. But even on a traditional host it creates a fragile situation, where starting unrelated processes as UID 1000 would cause codejail to mysteriously start breaking.

One solution is to select large, random values for the app and sandbox users. On a modern Linux kernel, UIDs and GIDs can be as high as ``2^31 - 1``. This will help avoid a situation where codejail-service has to share its usage pool with other, unrelated service. This is an incomplete solution, however, as two instances of codejail-service will interfere with each other, as will concurrent requests to the same instance. ``NPROC`` will need to be set high enough to account for this.

AppArmor
********

Again following the codejail library's instructions, create an AppArmor profile and load it into the host.

This profile will need to be customized according to your service's app user, sandbox setup, and other details. It will also look different if you are using Docker or running the service directly on the host. For reference, here is `2U's AppArmor profile <https://github.com/edx/public-dockerfiles/blob/main/apparmor/openedx_codejail_service.profile>`__; note that the inner profile is the one that actually applies the sandboxing.

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
