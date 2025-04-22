Changelog
#########

..
   All enhancements and patches to codejail_service will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

2025-04-18
**********
Fixed
=====
* Allow float specials like NaN and Infinity in globals_dict. (Was causing HTTP
  error due to JSON de/serialization.)

2025-04-18
**********
Added
=====
* Add logging for several client error situations
* Add custom attribute for slug

2025-04-04
**********
Added
=====
* Added span attributes to telemetry:

  * ``codejail.exec.status`` with outcome of code execution
  * ``codejail.exec.{limit_override,python_path_len,files_count}`` with additional details of code execution requests
  * ``codejail.startup_check.<CHECK_ID>`` and ``codejail.startup_check.status`` for individual and aggregate information on startup safety checks

2025-03-26
**********

This is now version 1.x to reflect the maturity of the codebase.

Added
=====
* Add safety check that attempts an outbound network connection from the webapp (not from inside the sandbox).

2025-03-17
**********
Changed
=======
* Startup safety checks now include a check that network access is denied; subprocess check is also updated to attempt executing ``date`` instead of a shell.

Fixed
=====
* Tolerate ``NPROC: 1`` in startup checks and API tests

2025-03-10
**********
Changed
=======
* The only file that can be uploaded and used in ``python_path`` is now ``python_lib.zip``. This is necessary for security but should be aligned with existing usage by edxapp.

2025-03-03
**********
Fixed
=====
* Add proper error handling to code-exec endpoint when ``payload`` param is missing or malformed
* Log unexpected exceptions instead of returning them as an ``emsg``

2025-02-18
**********
Fixed
=====
* Return ``globals_dict`` even when also returning an ``emsg`` error

2025-02-11
**********
Changed
=======
* Codejail is now properly configured at startup
* Service will refuse to execute code if basic smoke tests fail at startup. Also, healthcheck endpoint will remain unhealthy.

2025-01-30
**********

Changed
=======
* Require enabling Django setting ``CODEJAIL_ENABLED`` for code-exec endpoint to work, until it has been secured to our satisfaction.

2025-01-29
**********

Added
=====
* Implemented v0 API of code-exec endpoint

2025-01-28
**********

Added
=====
* First version (just has healthcheck)
