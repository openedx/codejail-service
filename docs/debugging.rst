Debugging
#########

Segfaults and "resource temporarily unavailable"
************************************************

In some cases, you might get the error message ``Couldn't execute jailed code: stdout: b'', stderr: b'' with status code: -11`` from a code execution. Status code ``-11`` is POSIX signal ``SIGSEGV``. If you encounter this, you're most likely running into process resource limits. Experiment with the ``CODE_JAIL.limits`` values until you discover which ``rlimit`` feature is the issue.

Examples where this has come up:

* Running ``import numpy`` with ``NPROC`` less than 4 (the default value of ``OPENBLAS_NUM_THREADS``)
* Running ``import matplotlib`` with only 100 MB of ``VMEM``

rlimit-related failures can also present as "Resource temporarily unavailable" rather than a segfault.

AppArmor
********

Generally, code-exec failures related to AppArmor will be reported as "permission denied" exceptions in the application, but only if the original exception is allowed to propagate unchanged. If you're unsure whether AppArmor is at fault in an unexpected failure, watching the kernel logs for the profile name may help identify whether it was involved::

  tail -F /var/log/kern.log | grep codejail

For example, this line indicates that Python was blocked from creating a network socket: ``2025-03-21T19:54:21.801657+00:00 myhostname kernel: audit: type=1400 audit(1742586861.800:384): apparmor="DENIED" operation="create" class="net" profile="openedx_codejail_service//codejail_sandbox" pid=19266 comm="python" family="inet" sock_type="stream" protocol=0 requested="create" denied="create"``. (Here, ``family="inet"`` designates IPv4, and ``sock_type="stream"`` designates TCP. The profile name will vary depending on your configuration.)
