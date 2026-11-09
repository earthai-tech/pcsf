"""Shared decorators.

Each decorator does one visible thing and never changes a function's
arguments or results silently.

``requires(*modules, feature=...)``
    Check that optional dependencies are installed before the call; raise
    :class:`~pcsf.exceptions.MissingDependencyError` with the pcsf extra
    to install otherwise.
``deprecated(since=, removed_in=, use=)``
    Emit one :class:`DeprecationWarning` per call site.
``validates_model(arg=..., result=...)``
    Run ``model.validate()`` on an argument and/or the returned model.
``log_call(level=...)``
    Log entry and duration at debug level (no effect unless enabled).
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


def requires(*modules: str, feature: str | None = None) -> Callable[[F], F]:
    """Require optional *modules* (import names) when the function is called."""
    def deco(func: F) -> F:
        what = feature or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for name in modules:
                import_optional(name, feature=what)
            return func(*args, **kwargs)
        wrapper.__pcsf_requires__ = modules  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]
    return deco


def deprecated(*, since: str, removed_in: str | None = None,
               use: str | None = None) -> Callable[[F], F]:
    """Mark a function as deprecated."""
    def deco(func: F) -> F:
        msg = f"{func.__qualname__} is deprecated since pcsf {since}"
        if removed_in:
            msg += f" and will be removed in {removed_in}"
        if use:
            msg += f"; use {use} instead"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        wrapper.__doc__ = f".. deprecated:: {since}\n   {msg}.\n\n{func.__doc__ or ''}"
        return wrapper  # type: ignore[return-value]
    return deco


def validates_model(*, arg: str | None = None, result: bool = False) -> Callable[[F], F]:
    """Validate the model passed as *arg* and/or the returned model."""
    def deco(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
    """Log the call and its duration at *level* through the pcsf logger."""
    def deco(func: F) -> F:
        logger = get_logger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not logger.isEnabledFor(level):
                return func(*args, **kwargs)
            t0 = time.perf_counter()
            out = func(*args, **kwargs)
            logger.log(level, "%s finished in %.3f s", func.__qualname__,
                       time.perf_counter() - t0)
            return out
        return wrapper  # type: ignore[return-value]
    return deco
