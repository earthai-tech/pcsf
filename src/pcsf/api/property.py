"""Base classes shared by every pcsf data object.

:class:`PCSFObject` gives every object the same behaviour: a compact,
readable ``repr``; ``to_dict``; ``update`` and ``clone`` that re-validate;
and a ``validate`` hook that subclasses override. :class:`MetadataMixin`
adds a free-form ``metadata`` dictionary.

New data classes should derive from :class:`PCSFObject` (and use
``@dataclass(repr=False)`` so that its ``repr`` is kept)::

    from dataclasses import dataclass
    from pcsf.api.property import PCSFObject

    @dataclass(repr=False)
    class Electrode(PCSFObject):
        name: str
        depth: float

        def validate(self) -> None:
            if self.depth < 0:
                raise ValueError("depth must be >= 0")
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import copy
from dataclasses import asdict, fields, is_dataclass
from typing import Any, ClassVar, TypeVar

__all__ = ["MetadataMixin", "PCSFObject"]

_T = TypeVar("_T", bound="PCSFObject")


class PCSFObject:
    """Root of all pcsf data objects.

    Class attributes control the automatic ``repr``:

    ``__repr_fields__``
        Explicit field order, or ``None`` to discover dataclass fields,
        instance attributes and slots.
    ``__repr_exclude__``
        Names never shown.
    ``__repr_max_fields__``
        Maximum number of fields shown.
    ``__repr_max_string__``
        Strings longer than this are shortened.

    Examples
    --------
    >>> class Obj(PCSFObject):
    ...     def __init__(self):
    ...         self.name = "S001"
    ...         self.values = [1, 2, 3]
    >>> repr(Obj())
    "Obj(name='S001', values=list(len=3, sample=[1, 2, 3]))"
    """

    __repr_fields__: ClassVar[Iterable[str] | None] = None
    __repr_exclude__: ClassVar[set[str]] = {"logger", "verbose"}
    __repr_max_fields__: ClassVar[int] = 8
    __repr_max_string__: ClassVar[int] = 48

    # ------------------------------------------------------------ display
    def __repr__(self) -> str:
        names = list(self._repr_fields())
        limit = int(self.__repr_max_fields__)
        items = []
        for name in names[:limit]:
            try:
                value = getattr(self, name)
            except Exception:
                continue
            items.append(f"{name}={self._short_value(value, max_string=int(self.__repr_max_string__))}")
        if len(names) > limit:
            items.append("...")
        return f"{type(self).__name__}({', '.join(items)})"

    def __str__(self) -> str:
        return self.summary()

    def summary(self, *, max_fields: int | None = None) -> str:
        """One-line summary; ``max_fields`` overrides the field limit."""
        if max_fields is None:
            return repr(self)
        old = self.__repr_max_fields__
        try:
            self.__repr_max_fields__ = int(max_fields)
            return repr(self)
        finally:
            self.__repr_max_fields__ = old

    # ------------------------------------------------------------ state
    def validate(self) -> None:
        """Check the object's state; subclasses override. Accepts everything here."""
        return None

    def update(self: _T, /, **values: Any) -> _T:
        """Set attributes, validate, and return ``self``."""
        for name, value in values.items():
            setattr(self, name, value)
        self.validate()
        return self

    def clone(self: _T, /, **overrides: Any) -> _T:
        """Shallow copy with optional attribute overrides, validated."""
        obj = copy(self)
        for name, value in overrides.items():
            setattr(obj, name, value)
        obj.validate()
        return obj

    def to_dict(self, *, public_only: bool = True, max_depth: int = 1) -> dict[str, Any]:
        """Shallow dictionary view (arrays are summarized by shape and dtype)."""
        return self._to_dict(self, public_only=public_only, depth=max_depth)

    # ------------------------------------------------------------ helpers
    def _repr_fields(self) -> Iterable[str]:
        explicit = self.__repr_fields__
        if explicit is not None:
            return self._filter(explicit)
        names: list[str] = []
        if is_dataclass(self):
            names.extend(f.name for f in fields(self))
        if hasattr(self, "__dict__"):
            names.extend(self.__dict__.keys())
        names.extend(self._slot_names())
        return self._filter(dict.fromkeys(names))

    def _filter(self, names: Iterable[str]) -> list[str]:
        exclude = set(self.__repr_exclude__)
        return [n for n in names if isinstance(n, str) and not n.startswith("_")
                and n not in exclude]

    @classmethod
    def _slot_names(cls) -> list[str]:
        names: list[str] = []
        for klass in reversed(cls.__mro__):
            slots = getattr(klass, "__slots__", ())
            if isinstance(slots, str):
                slots = (slots,)
            names.extend(s for s in slots if s not in {"__dict__", "__weakref__"})
        return names

    @classmethod
    def _short_value(cls, value: Any, *, max_string: int = 48) -> str:
        if value is None or isinstance(value, (bool, int, float, complex)):
            return repr(value)
        if isinstance(value, str):
            return repr(value if len(value) <= max_string else value[: max_string - 3] + "...")
        shape = getattr(value, "shape", None)
        dtype = getattr(value, "dtype", None)
        if shape is not None and dtype is not None:
            kind = "ndarray" if type(value).__name__ == "ndarray" else "array_like"
            return f"{kind}(shape={tuple(shape)}, dtype={dtype})"
        if isinstance(value, Mapping):
            keys = list(value.keys())
            sample = ", ".join(repr(k) for k in keys[:3]) + (", ..." if len(keys) > 3 else "")
            return f"dict(len={len(keys)}, keys=[{sample}])"
        if isinstance(value, (bytes, bytearray)):
            return f"{type(value).__name__}(len={len(value)})"
        if isinstance(value, (list, tuple, set, frozenset)):
            seq = list(value)
            sample = ", ".join(cls._short_value(v, max_string=max_string) for v in seq[:3])
            if len(seq) > 3:
                sample += ", ..."
            return f"{type(value).__name__}(len={len(seq)}, sample=[{sample}])"
        return repr(value)

    @classmethod
    def _to_dict(cls, obj: Any, *, public_only: bool, depth: int) -> Any:
        if depth < 0:
            return {"_": "max_depth"}
        if obj is None or isinstance(obj, (bool, int, float, complex, str)):
            return obj
        if type(obj).__name__ == "ndarray":
            return {"type": "ndarray", "shape": tuple(obj.shape), "dtype": str(obj.dtype)}
        if is_dataclass(obj) and not isinstance(obj, type):
            exclude = getattr(obj, "__repr_exclude__", set())
            try:
                return {k: v for k, v in asdict(obj).items() if k not in exclude}
            except Exception:
                return {f.name: cls._to_dict(getattr(obj, f.name, None), public_only=public_only,
                                             depth=depth - 1)
                        for f in fields(obj) if f.name not in exclude}
        if isinstance(obj, Mapping):
            return {str(k): cls._to_dict(v, public_only=public_only, depth=depth - 1)
                    for k, v in list(obj.items())[:32]}
        if isinstance(obj, (list, tuple, set, frozenset)):
            return [cls._to_dict(v, public_only=public_only, depth=depth - 1)
                    for v in list(obj)[:32]]
        out: dict[str, Any] = {}
        names = list(getattr(obj, "__dict__", {}).keys())
        if isinstance(obj, PCSFObject):
            names += obj._slot_names()
        exclude = getattr(obj, "__repr_exclude__", set())
        for name in dict.fromkeys(names):
            if (public_only and name.startswith("_")) or name in exclude:
                continue
            try:
                out[name] = cls._to_dict(getattr(obj, name), public_only=public_only,
                                         depth=depth - 1)
            except Exception:
                continue
        return out


class MetadataMixin:
    """Adds a free-form ``metadata`` dictionary."""

    metadata: dict[str, Any]

    def ensure_metadata(self) -> dict[str, Any]:
        """Return ``metadata``, creating an empty dictionary if needed."""
        current = getattr(self, "metadata", None)
        if not isinstance(current, dict):
            current = {}
            self.metadata = current
        return current

    def update_metadata(self, /, **values: Any):
        """Update ``metadata`` in place and return ``self``."""
        self.ensure_metadata().update(values)
        return self

    def metadata_dict(self) -> dict[str, Any]:
        """Shallow copy of ``metadata``."""
        return dict(self.ensure_metadata())
