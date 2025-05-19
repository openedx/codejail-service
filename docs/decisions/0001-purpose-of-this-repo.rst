1. Purpose of This Repo
#######################

Status
******

**Accepted** 2025-01-13

Context
*******

(Written in hindsight May 2025, but generally accurate as to the state of things in January.)

Risks of codejail
=================

Codejail is an inherently hazardous feature, as by design it executes untrusted code. By default, this code is executed on the same host as the LMS and CMS, core services that generally hold the most critical data in the deployment—any confinement failure would be disastrous. Historically, this was less of a concern, as the original uses of codejail were for trusted partners. In fact, before February 2013, submitted code was simply run in-process via Python's ``exec`` call, with no confinement whatsoever. There is still a platform feature allowing operators to use this unsafe execution method for specified courses, likely a relic of this period. Over time, the feature was opened up to all course creators, but the architecture remained the same.

On top of the concern of colocating execution with sensitive data, the codejail library is also difficult to configure to be safe. If it is not configured, it defaults to running all code with no confinement. Even if codejail is configured correctly, it still relies on AppArmor to be configured properly; if the wrong file path is specified in the AppArmor profile, code will again run with minimal confinement (just what's provided by user permissions on Linux).

Besides these dangers, it is also simply difficult to configure codejail, and not amenable to the same sort of containerization that other services enjoy. When deploying to a Docker-based environment, codejail requires AppArmor to be configured on the edxapp hosts themselves, and the profile must be applied to the service container. This adds additional complication to deployment.

Movement towards remote codejail
================================

In 2021 eduNEXT had previously implemented a Flask-based remote codejail service at `eduNEXT/codejailservice`_ and a ``remote_exec.py`` interface in edx-platform to call it. This enabled deploying codejail on Tutor.

In 2025, 2U made a push to move its own deployment of edx-platform from the legacy Ansible and EC2 based build system to a Docker and Kubernetes system. In the process, 2U wanted to move to a remote codejail for both security and ease of deployment reasons. Engineers weighed the option of using eduNEXT's codejailservice against creating a new service, and opted for the latter.

Decision
********

We will create a repository at ``openedx/codejail-service``, implementing the ``xmodule.capa.safe_exec.remote_exec.send_safe_exec_request_v0`` remote exec API (same as eduNEXT/codejailservice). This is intended as the standard Open edX remote codejail option going forward.

The new service will be implemented as a Django service, allowing for the reuse of existing monitoring and configuration code and patterns that are already standard across the Open edX ecosystem. The total amount of code to write is small, since this is largely a wrapper around the codejail library itself, so a rewrite is acceptable instead of forking or updating the eduNEXT code.

The new code will come with an API test suite for evaluating security and functionality of a running instance.

Consequences
************

- It will be possible to run codejail with additional protections that are not possible in the current default configuration. This includes locking down disk and outbound network access at the container level so that an AppArmor confinement failure can be mitigated.
- There will be one more service to maintain, although one with fairly minimal requirements.
- The remote codejail option in edx-platform will have an official implementation.
- eduNEXT/codejailservice can eventually be deprecated, and `eduNEXT/tutor-contrib-codejail <https://github.com/eduNEXT/tutor-contrib-codejail/>`__ updated to use the new repo.

Rejected Alternatives
*********************

Use eduNEXT implementation
==========================

We considered using the existing eduNEXT/codejailservice implementation. The main issue was that it used Flask rather than Django, which meant losing out on various bits of Django-based tooling that we've built up over the years (toggles, telemetry, etc.) Rewriting it to use Django would not have been particularly onerous, but also not much less work than simply creating a new Django-based repo. (The core of the application is simply a translation layer between HTTP and a call to ``codejail.safe_exec.safe_exec``.)

Because the two services implement the same API, there should be a smooth migration path for users of the existing repo.

Creating a new repo also allows us to make breaking changes (including tightening down security) without interfering with users of the existing repo.

.. _eduNEXT/codejailservice: https://github.com/eduNEXT/codejailservice
