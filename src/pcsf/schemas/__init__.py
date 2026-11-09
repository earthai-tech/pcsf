"""JSON Schemas of the structured metadata of a PCSF model.

``inversion-record``
    ``metadata["inversion"]``; a record valid against it has every
    required field of :data:`pcsf.core.record.REQUIRED_FIELDS`.
``model-provenance``
    ``metadata["model_provenance"]``, the machine-learning model
    behind a result.

The schemas follow JSON Schema draft 2020-12 and are the reference
for implementations in other languages. Validation in Python needs
the ``jsonschema`` package.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..compat.optional import import_optional

__all__ = ["NAMES", "load", "validate"]

#: Names of the bundled schemas.
NAMES = ("inversion-record", "model-provenance")

_HERE = Path(__file__).resolve().parent


def load(name: str) -> dict[str, Any]:
    """Load a bundled schema.

    Parameters
    ----------
    name : str
        One of :data:`NAMES`.

    Returns
    -------
    dict
        The schema.

    Raises
    ------
    KeyError
        If *name* is not a bundled schema.

    Examples
    --------
    >>> from pcsf import schemas
    >>> schemas.load("inversion-record")["required"]
    ['solver', 'data', 'regularization', 'misfit']
    """
    if name not in NAMES:
        raise KeyError(f"unknown schema {name!r}; known: {NAMES}")
    text = (_HERE / f"{name}.schema.json").read_text("utf-8")
    return json.loads(text)


def validate(instance: Any, name: str) -> list[str]:
    """Check a JSON-like value against a bundled schema.

    Parameters
    ----------
    instance : object
        Value to check, such as ``record.as_dict()``.
    name : str
        One of :data:`NAMES`.

    Returns
    -------
    list of str
        One message per violation, as ``path: message``; empty when
        the value is valid.

    Raises
    ------
    MissingDependencyError
        If ``jsonschema`` is not installed.

    Examples
    --------
    >>> from pcsf import schemas
    >>> schemas.validate({"solver": "ModEM"},
    ...                  "inversion-record")  # doctest: +SKIP
    ["$: 'data' is a required property", ...]
    """
    jsonschema = import_optional("jsonschema", feature="JSON Schema")
    schema = load(name)
    cls = jsonschema.validators.validator_for(schema)
    errors = sorted(
        cls(schema).iter_errors(instance), key=lambda e: list(e.path)
    )
    out = []
    for err in errors:
        where = "$" + "".join(f"[{p!r}]" for p in err.path)
        out.append(f"{where}: {err.message}")
    return out
