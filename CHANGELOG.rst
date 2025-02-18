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
