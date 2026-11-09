"""Conformance rules of the specification, checked on a model.

Each rule has an identifier, so that reports can be compared across
implementations; the conformance suite in ``conformance/`` uses the
same identifiers.

===================== =============================================
Rule                  Requirement
===================== =============================================
``C1.kind``           geometry kind is one of the specified kinds
``C2.positive``       resistivity is positive where defined
``C3.shape``          resistivity shape matches the geometry
``C4.encoding``       source values declare a known encoding
``C5.native``         source values reproduce the canonical values
``C6.multiline_root`` a multiline model has no root resistivity
``C7.synthesized``    a derived volume is labelled synthesized
``C8.lonlat``         station longitude and latitude come together
``C9.uncertainty``    uncertainty and sensitivity match resistivity
===================== =============================================
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..exceptions import ConformanceError
from .encodings import is_known_encoding, to_resistivity
from .schema import GEOMETRY_KINDS, PCSFModel

__all__ = ["ConformanceReport", "RuleResult", "check_conformance"]

#: Relative tolerance of rule C5 (source values reproduce rho).
_REL_TOL = 1e-12


@dataclass(frozen=True)
class RuleResult:
    """Outcome of one rule.

    Attributes
    ----------
    rule : str
        Rule identifier, such as ``"C2.positive"``.
    passed : bool
        Whether the rule holds.
    message : str, default ""
        Detail of the check.
    """

    rule: str
    passed: bool
    message: str = ""


@dataclass
class ConformanceReport:
    """Results of the rules checked on one model.

    Attributes
    ----------
    results : list of RuleResult
        One entry per check, in the order they ran; a rule checked
        on several lines appears several times.

    See Also
    --------
    check_conformance : Build a report.

    Examples
    --------
    >>> from pcsf.core.conformance import ConformanceReport
    >>> rep = ConformanceReport()
    >>> rep.add("C1.kind", True, "geometry kind 'grid2d'")
    >>> rep.add("C2.positive", False, "1 non-positive values")
    >>> rep.passed, [r.rule for r in rep.failures]
    (False, ['C2.positive'])
    """

    results: list[RuleResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when every check passed (also when none ran)."""
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[RuleResult]:
        """Checks that failed, in order."""
        return [r for r in self.results if not r.passed]

    def add(self, rule: str, passed: bool, message: str = "") -> None:
        """Append the result of one check.

        Parameters
        ----------
        rule : str
            Rule identifier.
        passed : bool
            Outcome; converted with ``bool``.
        message : str, default ""
            Detail of the check.
        """
        self.results.append(RuleResult(rule, bool(passed), message))

    def raise_if_failed(self) -> None:
        """Raise on the first failure.

        Raises
        ------
        ConformanceError
            If any check failed; carries the first failed rule and
            counts the others in its message.
        """
        failures = self.failures
        if not failures:
            return
        first = failures[0]
        message = first.message
        if len(failures) > 1:
            message += f" (and {len(failures) - 1} more)"
        raise ConformanceError(message, rule=first.rule)

    def __str__(self) -> str:
        lines = []
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"{status}  {r.rule:20s} {r.message}")
        n_pass = sum(r.passed for r in self.results)
        lines.append(f"{n_pass}/{len(self.results)} rules passed")
        return "\n".join(lines)


def _expected_shape(model: PCSFModel) -> list[tuple[int, ...]]:
    """Resistivity shapes allowed by the geometry of *model*."""
    g = model.geometry
    if model.kind == "grid2d":
        return [(g.z.size, g.x.size)]
    if model.kind == "grid3d":
        return [(g.z.size, g.y.size, g.x.size)]
    if model.kind == "mesh_unstructured":
        n_tri = np.asarray(g.connectivity).shape[0]
        ids = np.asarray(g.region_ids)
        n_reg = int(ids.max()) + 1 if ids.size else 0
        return [(n_tri,), (n_reg,)]
    return []


def _check_native(
    rep: ConformanceReport, model: PCSFModel, rho: np.ndarray
) -> None:
    """Rules C4 and C5 on the source values of *model*."""
    enc = model.resistivity_native_encoding
    ok = is_known_encoding(enc)
    rep.add("C4.encoding", ok, f"encoding {enc!r}")
    if not ok:
        return
    nat = to_resistivity(model.resistivity_native, enc)
    ref = rho
    # Per-node source values are checked against per-node rho.
    if (
        nat.shape != rho.shape
        and model.resistivity_by_node is not None
    ):
        ref = np.asarray(model.resistivity_by_node, dtype=float)
    if nat.shape != ref.shape:
        rep.add(
            "C5.native",
            False,
            f"source shape {nat.shape} vs {ref.shape}",
        )
        return
    m = np.isfinite(nat) & np.isfinite(ref)
    rel = np.abs(nat[m] - ref[m]) / np.abs(ref[m])
    worst = rel.max(initial=0.0)
    rep.add(
        "C5.native",
        bool(worst <= _REL_TOL),
        f"max relative difference {worst:.3g}",
    )


def check_conformance(model: PCSFModel) -> ConformanceReport:
    """Check every conformance rule on a model.

    Parameters
    ----------
    model : PCSFModel
        Model to check; it is not modified.

    Returns
    -------
    ConformanceReport
        One result per check.

    See Also
    --------
    pcsf.validate : Same check on a model or a file.

    Notes
    -----
    Rule C5 requires
    :math:`\\max_k |C_e(r_k) - \\rho_k| / |\\rho_k| \\le 10^{-12}`
    over the cells where both values are finite, with :math:`C_e` the
    conversion of :mod:`pcsf.core.encodings`. NaN marks undefined
    cells (air, padding) and is exempt from C2 and C5.

    Examples
    --------
    >>> import pcsf
    >>> from pcsf.core.conformance import check_conformance
    >>> model = pcsf.PCSFModel(
    ...     geometry=pcsf.Grid2DGeometry(x=[0.0, 10.0], z=[5.0]),
    ...     resistivity=[[10.0, 100.0]],
    ... )
    >>> rep = check_conformance(model)
    >>> rep.passed, [r.rule for r in rep.results]
    (True, ['C1.kind', 'C3.shape', 'C2.positive'])
    >>> print(str(rep).splitlines()[-1])
    3/3 rules passed
    """
    rep = ConformanceReport()
    kind = model.kind
    rep.add(
        "C1.kind", kind in GEOMETRY_KINDS, f"geometry kind {kind!r}"
    )
    if kind == "multiline":
        rep.add(
            "C6.multiline_root",
            model.resistivity is None,
            "multiline model must not have root-level resistivity",
        )
        for line in model.geometry.lines:
            rho = np.asarray(line.resistivity, dtype=float)
            exp = (line.geometry.z.size, line.geometry.x.size)
            rep.add(
                "C3.shape",
                rho.shape == exp,
                f"line {line.line_id}: {rho.shape} vs {exp}",
            )
            finite = rho[np.isfinite(rho)]
            rep.add(
                "C2.positive",
                bool(np.all(finite > 0)),
                f"line {line.line_id}",
            )
        dv = getattr(model.geometry, "derived_volume", None)
        if dv is not None:
            rep.add(
                "C7.synthesized",
                bool(dv.synthesized),
                "derived volume must be synthesized",
            )
    else:
        rho = np.asarray(model.resistivity, dtype=float)
        shapes = _expected_shape(model)
        rep.add(
            "C3.shape",
            rho.shape in shapes,
            f"resistivity {rho.shape}, expected one of {shapes}",
        )
        finite = rho[np.isfinite(rho)]
        rep.add(
            "C2.positive",
            bool(np.all(finite > 0)),
            f"{int(np.sum(finite <= 0))} non-positive values",
        )
        if model.resistivity_native is not None:
            _check_native(rep, model, rho)
        for name in ("uncertainty", "sensitivity"):
            arr = getattr(model, name)
            if arr is not None:
                shape = np.asarray(arr).shape
                rep.add(
                    "C9.uncertainty",
                    shape == rho.shape,
                    f"{name} shape {shape}",
                )
    st = model.stations
    if st is not None:
        lon = getattr(st, "lon", None)
        lat = getattr(st, "lat", None)
        rep.add(
            "C8.lonlat",
            (lon is None) == (lat is None),
            "longitude and latitude must be set together",
        )
    return rep
