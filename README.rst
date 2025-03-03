codejail_service
################

|ci-badge| |codecov-badge| |doc-badge| |pyversions-badge|
|license-badge| |status-badge|

Purpose
*******

Run codejail (sandboxed Python execution) as a service. This implements the custom Python problems in courses, and is a thin wrapper around the `codejail library <https://github.com/openedx/codejail>`_.

Warnings
********

Developers
==========

This service is configured with an in-memory database simply to make Django happy. The service itself **effectively does not have a database**, and should not rely on any database-dependent features such as waffle-based toggles.

Operators
=========

This is intended to be run as a fully internal service with no database or admin frontend, with the LMS and CMS making calls to it unauthenticated. **It should not be callable directly from the internet.**

While the service uses AppArmor as a first (and really, only) line of defense, it should also be deployed in a way that does not allow direct connections to other IDAs or internal services within the Open edX deployment. In the ideal situation, networking would be set up to only allow outbound connections to a predetermined set of IPs or domains.

After any significant change to security settings, consider running the tests in ``./api_tests/``. These are run manually against a deployed service and can check for various sandbox weaknesses.

Getting Started with Development
********************************

Please see the Open edX documentation for `guidance on Python development`_ in this repo.

.. _guidance on Python development: https://docs.openedx.org/en/latest/developers/how-tos/get-ready-for-python-dev.html

Deploying
*********

The service may be started using gunicorn with a command like this::

  export DJANGO_SETTINGS_MODULE=codejail_service.settings.production
  gunicorn -c codejail_service/docker_gunicorn_configuration.py \
    --bind '0.0.0.0:8080' --workers=10 --max-requests=1000 --name codejail \
    codejail_service.wsgi:application

There is a healthcheck endpoint at ``/health/`` which responds to a
GET with ``200 OK`` if the service is running and healthy.

TODO (`<https://github.com/openedx/codejail-service/issues/3>`__)

Getting Help
************

Documentation
=============

TODO (`<https://github.com/openedx/codejail-service/issues/3>`__)

More Help
=========

If you're having trouble, we have discussion forums at
https://discuss.openedx.org where you can connect with others in the
community.

Our real-time conversations are on Slack. You can request a `Slack
invitation`_, then join our `community Slack workspace`_.

For anything non-trivial, the best path is to open an issue in this
repository with as many details about the issue you are facing as you
can provide.

https://github.com/openedx/codejail-service/issues

For more information about these options, see the `Getting Help <https://openedx.org/getting-help>`__ page.

.. _Slack invitation: https://openedx.org/slack
.. _community Slack workspace: https://openedx.slack.com/

License
*******

The code in this repository is licensed under the Apache Software License 2.0 unless
otherwise noted.

Please see `LICENSE.txt <LICENSE.txt>`_ for details.

Contributing
************

Contributions are very welcome.
Please read `How To Contribute <https://openedx.org/r/how-to-contribute>`_ for details.

This project is currently accepting all types of contributions, bug fixes,
security fixes, maintenance work, or new features.  However, please make sure
to discuss your new feature idea with the maintainers before beginning development
to maximize the chances of your change being accepted.
You can start a conversation by creating a new issue on this repo summarizing
your idea.

The Open edX Code of Conduct
****************************

All community members are expected to follow the `Open edX Code of Conduct`_.

.. _Open edX Code of Conduct: https://openedx.org/code-of-conduct/

People
******

The assigned maintainers for this component and other project details may be
found in `Backstage`_. Backstage pulls this data from the ``catalog-info.yaml``
file in this repo.

.. _Backstage: https://backstage.openedx.org/catalog/default/component/codejail-service

Reporting Security Issues
*************************

Please do not report security issues in public. Please email security@openedx.org.

.. |ci-badge| image:: https://github.com/openedx/codejail-service/workflows/Python%20CI/badge.svg?branch=main
    :target: https://github.com/openedx/codejail-service/actions
    :alt: CI

.. |codecov-badge| image:: https://codecov.io/github/openedx/codejail-service/coverage.svg?branch=main
    :target: https://codecov.io/github/openedx/codejail-service?branch=main
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/codejail-service/badge/?version=latest
    :target: https://docs.openedx.org/projects/codejail-service
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/codejail-service.svg
    :target: https://pypi.python.org/pypi/codejail-service/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/openedx/codejail-service.svg
    :target: https://github.com/openedx/codejail-service/blob/main/LICENSE.txt
    :alt: License

.. |status-badge| image:: https://img.shields.io/badge/Status-Experimental-yellow
