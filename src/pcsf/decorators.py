"""Shared decorators.

Each decorator does one visible thing and never changes a function's
arguments or results.

``requires``
    Check that optional dependencies are installed before the call.
``deprecated``
    Emit a :class:`DeprecationWarning` at each call.
``validates_model``
    Run ``model.validate()`` on an argument, the result, or both.
``log_call``
    Log the duration of a call when debug logging is enabled.
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
import warnings
from collections.abc import Callable
from typing import Any, TypeVar

from ._logging import get_logger
from .compat.optional import import_optional

__all__ = ["deprecated", "log_call", "requires", "validates_model"]

F = TypeVar("F", bound=Callable[..., Any])


def requires(
    *modules: str, feature: str | None = None
) -> Callable[[F], F]:
    """Require optional modules when the decorated function is called.

    Parameters
    ----------
    *modules : str
        Import names of the optional dependencies.
    feature : str, optional
        What needs them, for the error message; defaults to the
        function's qualified name.

    Returns
    -------
    callable
        Decorator. The wrapped function has the attribute
        ``__pcsf_requires__`` listing *modules*.

    Raises
    ------
    MissingDependencyError
        At call time, if a module cannot be imported; the message
        names the pcsf extra that installs it.

    See Also
    --------
    pcsf.compat.optional.import_optional : The check used here.

    Notes
    -----
    The check runs at call time, not at import time, so that a module
    using an optional dependency can always be imported.

    Examples
    --------
    >>> from pcsf.decorators import requires
    >>> @requires("not_a_real_module_xyz", feature="the demo")
    ... def demo():
    ...     return 1
    >>> demo.__pcsf_requires__
    ('not_a_real_module_xyz',)
    >>> demo()  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    pcsf.exceptions.MissingDependencyError: 'not_a_real_module_xyz' ...
    """

    def deco(func: F) -> F:
        what = feature or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for name in modules:
                import_optional(name, feature=what)
            return func(*args, **kwargs)

        # Lets tools list the optional imports of a function.
        wrapper.__pcsf_requires__ = modules
        return wrapper  # type: ignore[return-value]

    return deco


def deprecated(
    *,
    since: str,
    removed_in: str | None = None,
    use: str | None = None,
) -> Callable[[F], F]:
    """Mark a function as deprecated.

    Parameters
    ----------
    since : str
        pcsf version that deprecated the function.
    removed_in : str, optional
        Version that will remove it.
    use : str, optional
        Replacement to recommend.

    Returns
    -------
    callable
        Decorator. The wrapped function's docstring starts with a
        ``.. deprecated::`` directive.

    Warns
    -----
    DeprecationWarning
        At each call, attributed to the caller.

    Examples
    --------
    >>> import warnings
    >>> from pcsf.decorators import deprecated
    >>> @deprecated(since="0.1", use="new_f")
    ... def old_f():
    ...     return 1
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter("always")
    ...     value = old_f()
    >>> value, caught[0].category.__name__
    (1, 'DeprecationWarning')
    """

    def deco(func: F) -> F:
        msg = f"{func.__qualname__} is deprecated since pcsf {since}"
        if removed_in:
            msg += f" and will be removed in {removed_in}"
        if use:
            msg += f"; use {use} instead"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        header = f".. deprecated:: {since}\n   {msg}.\n\n"
        wrapper.__doc__ = header + (func.__doc__ or "")
        return wrapper  # type: ignore[return-value]

    return deco


def validates_model(
    *, arg: str | None = None, result: bool = False
) -> Callable[[F], F]:
    """Validate the model passed as an argument and/or returned.

    Parameters
    ----------
    arg : str, optional
        Name of the parameter holding a model to validate before the
        call; ``None`` skips the check. A ``None`` argument value is
        not validated.
    result : bool, default False
        Validate the returned model, unless it is ``None``.

    Returns
    -------
    callable
        Decorator.

    Raises
    ------
    Exception
        Whatever the model's ``validate`` method raises, usually a
        :class:`~pcsf.exceptions.GeometryError` or
        :class:`~pcsf.exceptions.ConformanceError`.

    Examples
    --------
    >>> from pcsf.decorators import validates_model
    >>> class Model:
    ...     def validate(self):
    ...         raise ValueError("invalid")
    >>> @validates_model(arg="m")
    ... def use(m):
    ...     return m
    >>> use(Model())
    Traceback (most recent call last):
    ...
    ValueError: invalid
    """

    def deco(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if arg is not None:
                bound = sig.bind_partial(*args, **kwargs)
                model = bound.arguments.get(arg)
                if model is not None:
                    model.validate()
            out = func(*args, **kwargs)
            if result and out is not None:
                out.validate()
            return out

        return wrapper  # type: ignore[return-value]

    return deco


def log_call(level: int = logging.DEBUG) -> Callable[[F], F]:
    """Log the duration of each call through the pcsf logger.

    Parameters
    ----------
    level : int, default logging.DEBUG
        Logging level of the message.

    Returns
    -------
    callable
        Decorator. When the logger is not enabled for *level*, the
        wrapper calls the function directly, without timing.

    Examples
    --------
    >>> from pcsf.decorators import log_call
    >>> @log_call()
    ... def add(a, b):
    ...     return a + b
    >>> add(1, 2)
    3
    """

    def deco(func: F) -> F:
        logger = get_logger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not logger.isEnabledFor(level):
                return func(*args, **kwargs)
            t0 = time.perf_counter()
            out = func(*args, **kwargs)
            logger.log(
                level,
                "%s finished in %.3f s",
                func.__qualname__,
                time.perf_counter() - t0,
            )
            return out

        return wrapper  # type: ignore[return-value]

    return deco
