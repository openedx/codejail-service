"""
Wrappers and utilities for codejail library.
"""

import logging
from copy import deepcopy

log = logging.getLogger(__name__)


def safe_exec(code, input_globals, **kwargs):
    """
    Call safe_exec and work around several of its problems.

    input_globals is not mutated, unlike in the codejail library.

    Returns a tuple of (globals dict, error message).

    - globals dict: The globals dictionary that resulted from execution,
      whether or not an error was raised
    - error message: An error message string, or None if execution succeeded

    This approach allows us to return the new globals dictionary even if
    an error is raised, without requiring us to mutate the input. (And this
    approach is much better for unit testing than the mutation option is.)
    """
    # This needs to be a lazy import because as soon as codejail's
    # safe_exec module loads, it immediately makes a decision about
    # whether to run in always-unsafe mode.
    #
    # See https://github.com/openedx/codejail/issues/16 for maybe
    # fixing this.

    # pylint: disable=import-outside-toplevel
    from codejail.safe_exec import SafeExecException
    from codejail.safe_exec import safe_exec as real_safe_exec

    # Prevent mutation of input
    output_globals = deepcopy(input_globals)
    try:
        real_safe_exec(code, output_globals, **kwargs)
        return (output_globals, None)
    except SafeExecException as e:
        # These exception messages can be safely returned to the user, as they
        # indicate an error encountered by the jailed subprocess.
        return (output_globals, str(e))
    except BaseException as e:
        # Don't give details of unexpected exception, as it may indicate a bug
        # in the codejail service rather than the jailed code.
        log.warning(f"Unexpected error type from safe_exec: {e!r}", exc_info=True)
        return (output_globals, "Couldn't execute jailed code: See logs.")
