"""Critical inversion metadata for PCSF models.

A resistivity model can only be interpreted, compared or reviewed when
the reader knows how it was obtained: which data were inverted and with
which errors, which solver and regularization were used, how well the
data were fitted and whether the run converged, from which starting
model it began, how deep the data constrain it, and who may cite or
reuse it. :class:`InversionRecord` gathers this information in seven
sections and is stored in ``metadata["inversion"]`` of a PCSF model,
so it travels unchanged through both encodings.

Fields are *required* or *recommended* (``REQUIRED_FIELDS``,
``RECOMMENDED_FIELDS``). :func:`check_inversion_record` lists the
missing ones, so a writer or an archive can decide whether a file is
complete enough to be shared.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "RECOMMENDED_FIELDS",
    "REQUIRED_FIELDS",
    "TERMINATIONS",
    "InversionRecord",
    "attach_inversion_record",
    "check_inversion_record",
    "get_inversion_record",
]

#: Allowed values of ``misfit["termination"]``.
TERMINATIONS = (
    "target_reached",  # target misfit reached
    "iteration_limit",  # maximum number of iterations reached
    "time_limit",  # stopped by wall-clock limit
    "stalled",  # no further decrease (local minimum, step failure)
    "unknown",
)

REQUIRED_FIELDS = (
    "solver",
    "data.components",
    "data.frequency_range_hz",
    "data.n_stations",
    "data.errors",
    "regularization.type",
    "misfit.final_rms",
    "misfit.termination",
)

RECOMMENDED_FIELDS = (
    "solver_version",
    "data.n_frequencies",
    "data.sign_convention",
    "data.source",
    "forward.dimensionality",
    "forward.mesh",
    "regularization.trade_off",
    "regularization.start_model",
    "misfit.target_rms",
    "misfit.n_iterations",
    "reliability.method",
    "reliability.depth_of_investigation_m",
    "citation.authors",
    "citation.year",
    "citation.licence",
)


@dataclass
class InversionRecord:
    """How a resistivity model was obtained.

    Parameters
    ----------
    solver : str
        Inversion code, e.g. ``"Occam2D"``, ``"ModEM"``,
        ``"MARE2DEM"``.
    solver_version : str, optional
    data : dict
        ``components`` (e.g. ``["TE rho", "TE phase"]`` or
        ``["Zxy", "Zyx"]``), ``frequency_range_hz`` ``[f_min, f_max]``,
        ``n_frequencies``, ``n_stations``, ``errors`` (free text: error
        floors or the range of relative errors), ``sign_convention``
        (e.g. ``"exp(+i omega t)"``), ``source`` (data file, DOI or
        EMTF XML identifiers).
    forward : dict
        ``dimensionality`` (``"2D"``, ``"2.5D"``, ``"3D"``) and
        ``mesh`` (free text or cell counts).
    regularization : dict
        ``type`` (e.g. ``"smoothness (Occam)"``), ``trade_off`` (final
        Lagrange multiplier or damping), ``start_model``.
    misfit : dict
        ``final_rms``, ``target_rms``, ``n_iterations``,
        ``termination`` (one of :data:`TERMINATIONS`).
    reliability : dict
        ``method`` and ``depth_of_investigation_m`` (``{station:
        depth}``).
    citation : dict
        ``authors``, ``title``, ``year``, ``doi``, ``licence``.

    Raises
    ------
    ValueError
        If ``misfit["termination"]`` is not one of
        :data:`TERMINATIONS`.

    See Also
    --------
    check_inversion_record : List missing fields.
    attach_inversion_record : Store a record in a model.

    Examples
    --------
    >>> from pcsf.core.record import InversionRecord
    >>> rec = InversionRecord(
    ...     "Occam2D",
    ...     misfit={"final_rms": 1.0, "termination": "stalled"},
    ... )
    >>> InversionRecord.from_dict(rec.as_dict()) == rec
    True
    """

    solver: str
    solver_version: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    forward: dict[str, Any] = field(default_factory=dict)
    regularization: dict[str, Any] = field(default_factory=dict)
    misfit: dict[str, Any] = field(default_factory=dict)
    reliability: dict[str, Any] = field(default_factory=dict)
    citation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        term = self.misfit.get("termination")
        if term is not None and term not in TERMINATIONS:
            raise ValueError(
                f"misfit['termination'] must be one of "
                f"{TERMINATIONS}, got {term!r}"
            )

    def as_dict(self) -> dict[str, Any]:
        """Plain nested dictionary of the record.

        Returns
        -------
        dict
            Deep copy of every field, suitable for JSON.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> InversionRecord:
        """Build a record from a dictionary.

        Parameters
        ----------
        payload : dict
            As produced by :meth:`as_dict`. Unknown keys are ignored,
            so that records written by a newer version can be read.

        Returns
        -------
        InversionRecord

        Raises
        ------
        TypeError
            If ``solver`` is missing.
        ValueError
            If ``misfit["termination"]`` is not allowed.
        """
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in payload.items() if k in keys})


def _lookup(record: dict[str, Any], dotted: str) -> Any:
    """Value at a dotted path such as ``"misfit.final_rms"``."""
    node: Any = record
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def check_inversion_record(
    record: InversionRecord | dict[str, Any],
) -> dict[str, list[str]]:
    """List the missing required and recommended fields of a record.

    Parameters
    ----------
    record : InversionRecord or dict
        Record, or its dictionary form.

    Returns
    -------
    dict
        ``{"required": [...], "recommended": [...]}`` with the dotted
        names of the missing fields, in the order of
        :data:`REQUIRED_FIELDS` and :data:`RECOMMENDED_FIELDS`. A
        field set to ``None``, ``""``, ``[]`` or ``{}`` is missing.

    Examples
    --------
    >>> from pcsf.core.record import (InversionRecord,
    ...                               check_inversion_record)
    >>> rec = InversionRecord("ModEM", misfit={"final_rms": 1.1})
    >>> check_inversion_record(rec)["required"][:2]
    ['data.components', 'data.frequency_range_hz']
    """
    if isinstance(record, InversionRecord):
        payload = record.as_dict()
    else:
        payload = dict(record)

    def missing(names: tuple[str, ...]) -> list[str]:
        empty = (None, "", [], {})
        return [f for f in names if _lookup(payload, f) in empty]

    return {
        "required": missing(REQUIRED_FIELDS),
        "recommended": missing(RECOMMENDED_FIELDS),
    }


def attach_inversion_record(
    model: Any, record: InversionRecord
) -> Any:
    """Store a record in ``model.metadata["inversion"]``.

    Parameters
    ----------
    model : PCSFModel
        Model to annotate; its ``metadata`` is replaced by a new
        dictionary (the old one is not mutated).
    record : InversionRecord
        Record to store, as its dictionary form.

    Returns
    -------
    PCSFModel
        *model*, for chaining.

    See Also
    --------
    get_inversion_record : Read the record back.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.core.record import (InversionRecord,
    ...     attach_inversion_record, get_inversion_record)
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> _ = attach_inversion_record(model, InversionRecord("Occam2D"))
    >>> get_inversion_record(model).solver
    'Occam2D'
    """
    meta = dict(model.metadata or {})
    meta["inversion"] = record.as_dict()
    model.metadata = meta
    return model


def get_inversion_record(model: Any) -> InversionRecord | None:
    """Read the inversion record of a model.

    Parameters
    ----------
    model : PCSFModel
        Model whose ``metadata["inversion"]`` is read.

    Returns
    -------
    InversionRecord or None
        The record, or ``None`` when the model has none.

    See Also
    --------
    attach_inversion_record : Store a record.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.core.record import get_inversion_record
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0], z=[5.0]),
    ...     resistivity=[[100.0]],
    ... )
    >>> get_inversion_record(model) is None
    True
    """
    payload = (model.metadata or {}).get("inversion")
    if payload is None:
        return None
    return InversionRecord.from_dict(payload)
