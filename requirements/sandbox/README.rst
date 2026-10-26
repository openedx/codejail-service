============================
CodeJail Sandbox environment
============================

The requirements in this directory describe all the dependencies and libraries
available in the Sandbox runtime used to execute instructor-authored code by
openedx-platform.

They are an independent uv project, separate from the service's own
dependencies, mirroring openedx-platform's `requirements/edx-sandbox
<https://github.com/openedx/openedx-platform/tree/master/requirements/edx-sandbox>`__.

Files in this directory
=======================

pyproject.toml
**************

The current set of requirements for the sandbox environment, plus the
constraints applied to them.

uv.lock
*******

The latest pins for the sandbox environment. They are regularly updated with
the latest compatible versions of each package by ``make upgrade``.

Installing the sandbox environment
==================================

Sync the lockfile into the sandbox virtualenv::

  UV_PROJECT_ENVIRONMENT=/path/to/sandbox/venv \
    uv sync --locked --project requirements/sandbox
