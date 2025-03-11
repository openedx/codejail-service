.. _chapter-testing:

Testing
#######

codejail_service has an assortment of test cases and code quality
checks to catch potential problems during development.  To run them all in the
version of Python you chose for your virtualenv:

.. code-block:: bash

    $ make validate

To run just the unit tests:

.. code-block:: bash

    $ make test

To run just the code quality checks:

.. code-block:: bash

    $ make quality

To generate and open an HTML report of how much of the code is covered by
test cases:

.. code-block:: bash

    $ make coverage
