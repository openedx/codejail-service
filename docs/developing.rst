Developing
##########

Setup
*****

Due to the complex needs of codejail itself, running a local instance of codejail-service for debugging can be difficult. One of the following is recommended:

- Write unit tests for the behavior of interest, mocking out calls to ``safe_exec``.
- Run codejail-service using the same Docker image you would use for deployment, and install the corresponding AppArmor profile on your development machine.

Special notes
*************

The service does not have a database (see ADR :ref:`adr2-no-db`), and so cannot use DB-dependent features such as waffle-based toggles.

(The base settings configure Django to use an ephemeral in-memory database, since Django demands *some* kind of DB. But it isn't used for anything.)

Debugging
*********

Segfaults and "resource temporarily unavailable"
================================================

In some cases, you might get the error message ``Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -11`` from a code execution. Status code ``-11`` is POSIX signal ``SIGSEGV``. If you encounter this, you're most likely running into process resource limits. Experiment with the ``CODE_JAIL.limits`` values until you discover which ``rlimit`` feature is the issue.

Examples where this has come up:

* Running ``import numpy`` with ``NPROC`` less than 4 (the default value of ``OPENBLAS_NUM_THREADS``)
* Running ``import matplotlib`` with only 100 MB of ``VMEM``

rlimit-related failures can also present as "Resource temporarily unavailable" rather than a segfault.

AppArmor
========

Generally, code-exec failures related to AppArmor will be reported as "permission denied" exceptions in the application, but only if the original exception is allowed to propagate unchanged. If you're unsure whether AppArmor is at fault in an unexpected failure, watching the kernel logs for the profile name may help identify whether it was involved::

  tail -F /var/log/kern.log | grep codejail

For example, this line indicates that Python was blocked from creating a network socket: ``2025-03-21T19:54:21.801657+00:00 myhostname kernel: audit: type=1400 audit(1742586861.800:384): apparmor="DENIED" operation="create" class="net" profile="openedx_codejail_service//codejail_sandbox" pid=19266 comm="python" family="inet" sock_type="stream" protocol=0 requested="create" denied="create"``. (Here, ``family="inet"`` designates IPv4, and ``sock_type="stream"`` designates TCP. The profile name will vary depending on your configuration.)
