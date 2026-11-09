"""Registries: how new encodings, adapters and companion formats plug in.

A registry maps a name to an object and refuses silent overwrites. Three
registries are public:

``ENCODINGS``
    name -> :class:`EncodingSpec` (conversion of source values to linear
    resistivity). Built-in: ``log10``, ``ln``, ``linear``,
    ``log10_conductivity``, ``conductivity``.
``ADAPTERS``
    name -> callable converting native solver output to a PCSF model.
``FORMATS``
    name -> companion-format descriptor (boreholes, geology, ...).

Third-party packages register through the decorators below, usually from
a function exposed as an entry point (see :mod:`pcsf.plugins`)::

    from pcsf.api.registry import register_encoding

    @register_encoding("log10_conductance", description="log10 of S")
    def _to_rho(values):
        ...
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
    "register_adapter",
    "register_encoding",
    "register_format",
]

_V = TypeVar("_V")


class Registry(Generic[_V]):
    """Name -> object mapping that refuses accidental overwrites."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, _V] = {}

    def register(self, name: str, item: _V, *, replace: bool = False) -> _V:
        if not replace and name in self._items:
            raise RegistryError(f"{self.kind} {name!r} is already registered "
                                "(pass replace=True to override)")
        self._items[name] = item
        return item

    def unregister(self, name: str) -> None:
        if name not in self._items:
            raise RegistryError(f"unknown {self.kind} {name!r}")
        del self._items[name]

    def get(self, name: str) -> _V:
        try:
            return self._items[name]
        except KeyError:
            known = ", ".join(sorted(self._items)) or "none"
            raise RegistryError(f"unknown {self.kind} {name!r}; known: {known}") from None

    def __contains__(self, name: object) -> bool:
        return name in self._items

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._items))

    def __len__(self) -> int:
        return len(self._items)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


# ------------------------------------------------------------------ encodings
@dataclass(frozen=True)
class EncodingSpec:
    """How source values of one encoding become linear resistivity.

    Attributes
    ----------
    name : str
        Encoding name stored in files (``model/resistivity_native@encoding``).
    to_resistivity : callable
        ``values -> rho`` in ohm m (array in, array out).
    from_resistivity : callable, optional
        Inverse, ``rho -> values``; used to write source values.
    quantity : str
        ``"resistivity"`` or ``"conductivity"``.
    description : str
        Human-readable description (used in PCSM comments and docs).
    """

    name: str
    to_resistivity: Callable[[np.ndarray], np.ndarray]
    from_resistivity: Callable[[np.ndarray], np.ndarray] | None = None
    quantity: str = "resistivity"
    description: str = ""

    def __call__(self, values: Any) -> np.ndarray:
        return self.to_resistivity(np.asarray(values, dtype=float))


ENCODINGS: Registry[EncodingSpec] = Registry("encoding")
ADAPTERS: Registry[Callable[..., Any]] = Registry("adapter")
FORMATS: Registry[Any] = Registry("format")


def register_encoding(name: str, *, inverse: Callable | None = None, quantity: str = "resistivity",
                      description: str = "", replace: bool = False):
    """Decorator registering a ``values -> rho`` conversion as encoding *name*."""
    def deco(func: Callable[[np.ndarray], np.ndarray]):
        ENCODINGS.register(name, EncodingSpec(name, func, inverse, quantity, description),
                           replace=replace)
        return func
    return deco


def register_adapter(name: str, *, replace: bool = False):
    """Decorator registering a native -> PCSF adapter under *name*."""
    def deco(func: Callable[..., Any]):
        ADAPTERS.register(name, func, replace=replace)
        return func
    return deco


def register_format(name: str, descriptor: Any, *, replace: bool = False) -> Any:
    """Register a companion format (boreholes, geology, ...)."""
    return FORMATS.register(name, descriptor, replace=replace)


def get_encoding(name: str) -> EncodingSpec:
    """Return the registered encoding *name* or raise :class:`EncodingError`."""
    try:
        return ENCODINGS.get(name)
    except RegistryError as exc:
        raise EncodingError(str(exc)) from None
