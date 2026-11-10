"""Registries through which encodings, adapters and formats plug in.

A registry maps a name to an object and refuses silent overwrites.
Three registries are public:

``ENCODINGS``
    Name to :class:`EncodingSpec`, the conversion of source values to
    linear resistivity. Built in: ``log10``, ``ln``, ``linear``,
    ``log10_conductivity`` and ``conductivity``.
``ADAPTERS``
    Name to a callable that converts native solver output to a
    :class:`~pcsf.PCSFModel`.
``FORMATS``
    Name to a companion-format descriptor (boreholes, geology).

Third-party packages register through the decorators below, usually
from a function exposed as an entry point (see :mod:`pcsf.plugins`).

Examples
--------
>>> import numpy as np
>>> from pcsf.api.registry import ENCODINGS, register_encoding
>>> @register_encoding("log2", description="log2 of ohm m")
... def _from_log2(values):
...     return 2.0 ** values
>>> print(ENCODINGS.get("log2")([1.0, 10.0]))
[   2. 1024.]
>>> ENCODINGS.unregister("log2")
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import numpy as np

from ..exceptions import EncodingError, RegistryError

__all__ = [
    "ADAPTERS",
    "ENCODINGS",
    "FORMATS",
    "EncodingSpec",
    "Registry",
    "get_encoding",
    "register_adapter",
    "register_encoding",
    "register_format",
]

_V = TypeVar("_V")
_F = TypeVar("_F", bound=Callable[..., Any])


class Registry(Generic[_V]):
    """Mapping from names to objects that refuses overwrites.

    Parameters
    ----------
    kind : str
        Name of the kind of object held, used in error messages.

    Attributes
    ----------
    kind : str
        As given.

    See Also
    --------
    register_encoding, register_adapter, register_format

    Notes
    -----
    Iteration, :meth:`names` and the error messages list names in
    sorted order, so that output does not depend on import order.

    Examples
    --------
    >>> from pcsf.api.registry import Registry
    >>> reg = Registry("widget")
    >>> reg.register("a", 1)
    1
    >>> "a" in reg, len(reg), reg.names()
    (True, 1, ('a',))
    >>> reg.register("a", 2)
    Traceback (most recent call last):
    ...
    pcsf.exceptions.RegistryError: widget 'a' is already registered \
(pass replace=True to override)
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, _V] = {}

    def register(
        self, name: str, item: _V, *, replace: bool = False
    ) -> _V:
        """Register *item* under *name*.

        Parameters
        ----------
        name : str
            Key.
        item : object
            Object to store.
        replace : bool, default False
            Allow replacing an existing entry.

        Returns
        -------
        object
            *item*, so that the call can be used in an expression.

        Raises
        ------
        RegistryError
            If *name* exists and *replace* is False.
        """
        if not replace and name in self._items:
            raise RegistryError(
                f"{self.kind} {name!r} is already registered "
                "(pass replace=True to override)"
            )
        self._items[name] = item
        return item

    def unregister(self, name: str) -> None:
        """Remove the entry *name*.

        Parameters
        ----------
        name : str
            Key to remove.

        Raises
        ------
        RegistryError
            If *name* is not registered.
        """
        if name not in self._items:
            raise RegistryError(f"unknown {self.kind} {name!r}")
        del self._items[name]

    def get(self, name: str) -> _V:
        """Return the entry *name*.

        Parameters
        ----------
        name : str
            Key to look up.

        Returns
        -------
        object
            The registered object.

        Raises
        ------
        RegistryError
            If *name* is not registered; the message lists the known
            names.
        """
        try:
            return self._items[name]
        except KeyError:
            known = ", ".join(sorted(self._items)) or "none"
            raise RegistryError(
                f"unknown {self.kind} {name!r}; known: {known}"
            ) from None

    def __contains__(self, name: object) -> bool:
        return name in self._items

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._items))

    def __len__(self) -> int:
        return len(self._items)

    def names(self) -> tuple[str, ...]:
        """Registered names in sorted order.

        Returns
        -------
        tuple of str
            Sorted keys.
        """
        return tuple(sorted(self._items))


@dataclass(frozen=True)
class EncodingSpec:
    """How source values of one encoding become linear resistivity.

    Attributes
    ----------
    name : str
        Encoding name stored in files
        (``model/resistivity_native@encoding``).
    to_resistivity : callable
        Map ``values -> rho`` in ohm m, array in and array out.
    from_resistivity : callable or None, default None
        Inverse map ``rho -> values``, used to write source values.
    quantity : {"resistivity", "conductivity"}, default "resistivity"
        Physical quantity of the source values.
    description : str, default ""
        Human-readable description, used in PCSM comments and docs.

    See Also
    --------
    register_encoding : Register a new encoding.
    get_encoding : Look up an encoding.

    Examples
    --------
    >>> from pcsf.api.registry import get_encoding
    >>> spec = get_encoding("log10")
    >>> print(spec([0.0, 2.0]))
    [  1. 100.]
    """

    name: str
    to_resistivity: Callable[[np.ndarray], np.ndarray]
    from_resistivity: Callable[[np.ndarray], np.ndarray] | None = None
    quantity: str = "resistivity"
    description: str = ""

    def __call__(self, values: Any) -> np.ndarray:
        """Convert source values to resistivity in ohm m.

        Parameters
        ----------
        values : array_like
            Source values in this encoding.

        Returns
        -------
        ndarray of float
            Linear resistivity, same shape as *values*.
        """
        return self.to_resistivity(np.asarray(values, dtype=float))


#: Registered resistivity encodings.
ENCODINGS: Registry[EncodingSpec] = Registry("encoding")
#: Registered native-to-PCSF adapters.
ADAPTERS: Registry[Callable[..., Any]] = Registry("adapter")
#: Registered companion formats.
FORMATS: Registry[Any] = Registry("format")


def register_encoding(
    name: str,
    *,
    inverse: Callable[[np.ndarray], np.ndarray] | None = None,
    quantity: str = "resistivity",
    description: str = "",
    replace: bool = False,
) -> Callable[[_F], _F]:
    """Decorator registering a conversion as encoding *name*.

    Parameters
    ----------
    name : str
        Encoding name, as stored in files.
    inverse : callable, optional
        Map ``rho -> values``.
    quantity : {"resistivity", "conductivity"}, default "resistivity"
        Physical quantity of the source values.
    description : str, default ""
        Human-readable description.
    replace : bool, default False
        Allow replacing an existing encoding.

    Returns
    -------
    callable
        Decorator that registers a ``values -> rho`` function and
        returns it unchanged.

    Raises
    ------
    RegistryError
        When the decorator is applied, if *name* exists and
        *replace* is False.

    See Also
    --------
    EncodingSpec, get_encoding

    Examples
    --------
    >>> from pcsf.api.registry import ENCODINGS, register_encoding
    >>> @register_encoding("double", description="2 rho")
    ... def _half(values):
    ...     return values / 2.0
    >>> "double" in ENCODINGS
    True
    >>> ENCODINGS.unregister("double")
    """

    def deco(func: _F) -> _F:
        spec = EncodingSpec(name, func, inverse, quantity, description)
        ENCODINGS.register(name, spec, replace=replace)
        return func

    return deco


def register_adapter(
    name: str, *, replace: bool = False
) -> Callable[[_F], _F]:
    """Decorator registering a native-to-PCSF adapter under *name*.

    Parameters
    ----------
    name : str
        Adapter name, usually the solver name (``"modem"``).
    replace : bool, default False
        Allow replacing an existing adapter.

    Returns
    -------
    callable
        Decorator that registers the adapter and returns it
        unchanged.

    Raises
    ------
    RegistryError
        When the decorator is applied, if *name* exists and
        *replace* is False.

    Examples
    --------
    >>> from pcsf.api.registry import ADAPTERS, register_adapter
    >>> @register_adapter("toy")
    ... def _toy(path):
    ...     raise NotImplementedError
    >>> ADAPTERS.get("toy") is _toy
    True
    >>> ADAPTERS.unregister("toy")
    """

    def deco(func: _F) -> _F:
        ADAPTERS.register(name, func, replace=replace)
        return func

    return deco


def register_format(
    name: str, descriptor: Any, *, replace: bool = False
) -> Any:
    """Register a companion format such as boreholes or geology.

    Parameters
    ----------
    name : str
        Format name.
    descriptor : object
        Object describing the format. Its interface is defined by
        the plugin that consumes it, with one exception: when the
        format is stored in the ``boreholes`` group of a ``.pcsf``
        file, a ``from_dict`` attribute (a callable taking the
        stored dictionary) makes :func:`pcsf.read_pcsf` return
        its result instead of the dictionary.
    replace : bool, default False
        Allow replacing an existing format.

    Returns
    -------
    object
        *descriptor*.

    Raises
    ------
    RegistryError
        If *name* exists and *replace* is False.

    Examples
    --------
    >>> from pcsf.api.registry import FORMATS, register_format
    >>> register_format("toy-borehole", {"version": "0"})
    {'version': '0'}
    >>> FORMATS.unregister("toy-borehole")
    """
    return FORMATS.register(name, descriptor, replace=replace)


def get_encoding(name: str) -> EncodingSpec:
    """Return a registered encoding.

    Parameters
    ----------
    name : str
        Encoding name.

    Returns
    -------
    EncodingSpec
        The registered specification.

    Raises
    ------
    EncodingError
        If *name* is not registered.

    Examples
    --------
    >>> from pcsf.api.registry import get_encoding
    >>> get_encoding("ln").quantity
    'resistivity'
    """
    try:
        return ENCODINGS.get(name)
    except RegistryError as exc:
        raise EncodingError(str(exc)) from None
