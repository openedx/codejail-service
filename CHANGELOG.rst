Change Log
##########

..
   All enhancements and patches to codejail_service will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

0.6.0 - 2025-03-17
******************
Changed
=======
* Startup safety checks now include a check that network access is denied; subprocess check is also updated to attempt executing ``date`` instead of a shell.

Fixed
=====
* Tolerate ``NPROC: 1`` in startup checks and API tests

0.5.0 - 2025-03-10
******************
Changed
=======
* The only file that can be uploaded and used in ``python_path`` is now ``python_lib.zip``. This is necessary for security but should be aligned with existing usage by edxapp.

0.4.2 - 2025-03-03
******************
Fixed
=====
* Add proper error handling to code-exec endpoint when ``payload`` param is missing or malformed
* Log unexpected exceptions instead of returning them as an ``emsg``

0.4.1 - 2025-02-18
******************
Fixed
=====
* Return ``globals_dict`` even when also returning an ``emsg`` error

0.4.0 - 2025-02-11
******************
Changed
=======
* Codejail is now properly configured at startup
* Service will refuse to execute code if basic smoke tests fail at startup. Also, healthcheck endpoint will remain unhealthy.

0.3.0 - 2025-01-30
******************

Changed
=======
* Require enabling Django setting ``CODEJAIL_ENABLED`` for code-exec endpoint to work, until it has been secured to our satisfaction.

0.2.0 - 2025-01-29
******************

Added
=====
* Implemented v0 API of code-exec endpoint

0.1.0 - 2025-01-28
******************

Added
=====
* First version (just has healthcheck)
