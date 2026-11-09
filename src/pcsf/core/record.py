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
    "InversionRecord",
    "REQUIRED_FIELDS",
    "RECOMMENDED_FIELDS",
    "TERMINATIONS",
    "attach_inversion_record",
    "check_inversion_record",
    "get_inversion_record",
]

#: Allowed values of ``misfit["termination"]``.
TERMINATIONS = (
    "target_reached",   # target misfit reached
    "iteration_limit",  # maximum number of iterations reached
    "time_limit",       # stopped by wall-clock limit
    "stalled",          # no further decrease (local minimum, step failure)
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
        Inversion code, e.g. ``"Occam2D"``, ``"ModEM"``, ``"MARE2DEM"``.
    solver_version : str, optional
    data : dict
        ``components`` (e.g. ``["TE rho", "TE phase"]`` or
        ``["Zxy", "Zyx"]``), ``frequency_range_hz`` ``[f_min, f_max]``,
        ``n_frequencies``, ``n_stations``, ``errors`` (free text: error
        floors or the range of relative errors), ``sign_convention``
        (e.g. ``"exp(+i omega t)"``), ``source`` (data file, DOI or
        EMTF XML identifiers).
    forward : dict
        ``dimensionality`` (``"2D"``, ``"2.5D"``, ``"3D"``) and ``mesh``
        (free text or cell counts).
    regularization : dict
        ``type`` (e.g. ``"smoothness (Occam)"``), ``trade_off`` (final
        Lagrange multiplier or damping), ``start_model``.
    misfit : dict
        ``final_rms``, ``target_rms``, ``n_iterations``, ``termination``
        (one of :data:`TERMINATIONS`).
    reliability : dict
        ``method`` and ``depth_of_investigation_m`` (``{station: depth}``).
    citation : dict
        ``authors``, ``title``, ``year``, ``doi``, ``licence``.
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
                f"misfit['termination'] must be one of {TERMINATIONS}, got {term!r}")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InversionRecord":
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in payload.items() if k in keys})


def _lookup(record: dict[str, Any], dotted: str) -> Any:
    node: Any = record
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def check_inversion_record(record: InversionRecord | dict[str, Any]) -> dict[str, list[str]]:
    """Return the missing ``required`` and ``recommended`` fields."""
    payload = record.as_dict() if isinstance(record, InversionRecord) else dict(record)

    def missing(fields):
        return [f for f in fields if _lookup(payload, f) in (None, "", [], {})]

    return {"required": missing(REQUIRED_FIELDS),
            "recommended": missing(RECOMMENDED_FIELDS)}


def attach_inversion_record(model, record: InversionRecord):
    """Store *record* in ``model.metadata["inversion"]`` and return *model*."""
    meta = dict(model.metadata or {})
    meta["inversion"] = record.as_dict()
    model.metadata = meta
    return model


def get_inversion_record(model) -> InversionRecord | None:
    """Read the record back from a model, or ``None`` if absent."""
    payload = (model.metadata or {}).get("inversion")
    return None if payload is None else InversionRecord.from_dict(payload)
