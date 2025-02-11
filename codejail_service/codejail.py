"""
Wrappers and utilities for codejail library.
"""

from copy import deepcopy


def safe_exec(code, input_globals, **kwargs):
    """
    Call safe_exec and work around several of its problems.

    Returns new globals dictionary that results from execution.
    (Does not mutate input.)
    """
    # This needs to be a lazy import because as soon as codejail's
    # safe_exec module loads, it immediately makes a decision about
    # whether to run in always-unsafe mode.
    #
    # See https://github.com/openedx/codejail/issues/225 for maybe
    # fixing this.

    # pylint: disable=import-outside-toplevel
    from codejail.safe_exec import safe_exec as real_safe_exec

    # Prevent mutation of input
    output_globals = deepcopy(input_globals)
    real_safe_exec(code, output_globals, **kwargs)
    return output_globals
