"""Conformance rules of the specification, checked on an in-memory model.

Each rule has an identifier, so that a report can be compared across
implementations (the same identifiers are used by the conformance suite
in ``conformance/``). :func:`check_conformance` returns a
:class:`ConformanceReport`; :meth:`ConformanceReport.raise_if_failed`
turns failures into a :class:`~pcsf.exceptions.ConformanceError`.

Rules
-----
``C1.kind``            geometry kind is one of the specified kinds
``C2.positive``        canonical resistivity is positive where defined
``C3.shape``           resistivity shape matches the geometry
``C4.encoding``        source values declare a known encoding
``C5.native``          source values reproduce the canonical values
``C6.multiline_root``  a multiline model has no root-level resistivity
``C7.synthesized``     a derived volume is labelled synthesized
``C8.lonlat``          station longitude and latitude are given together
``C9.uncertainty``     uncertainty and sensitivity have the resistivity shape
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..exceptions import ConformanceError
from .encodings import is_known_encoding, to_resistivity
from .schema import GEOMETRY_KINDS, PCSFModel

__all__ = ["ConformanceReport", "RuleResult", "check_conformance"]

_REL_TOL = 1e-12


@dataclass(frozen=True)
class RuleResult:
    """Outcome of one rule."""

    rule: str
    passed: bool
    message: str = ""


@dataclass
class ConformanceReport:
    """Results of all rules checked on one model."""

    results: list[RuleResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[RuleResult]:
        return [r for r in self.results if not r.passed]

    def add(self, rule: str, passed: bool, message: str = "") -> None:
        self.results.append(RuleResult(rule, bool(passed), message))

    def raise_if_failed(self) -> None:
        if self.failures:
            first = self.failures[0]
            raise ConformanceError(
                first.message + (f" (and {len(self.failures) - 1} more)"
                                 if len(self.failures) > 1 else ""),
                rule=first.rule)

    def __str__(self) -> str:
        lines = [f"{'PASS' if r.passed else 'FAIL'}  {r.rule:20s} {r.message}"
                 for r in self.results]
        return "\n".join(lines + [f"{sum(r.passed for r in self.results)}/{len(self.results)} rules passed"])


def _expected_shape(model: PCSFModel):
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


def check_conformance(model: PCSFModel) -> ConformanceReport:
    """Check every conformance rule on *model*."""
    rep = ConformanceReport()
    kind = model.kind
    rep.add("C1.kind", kind in GEOMETRY_KINDS, f"geometry kind {kind!r}")

    if kind == "multiline":
        rep.add("C6.multiline_root", model.resistivity is None,
                "multiline model must not have root-level resistivity")
        for line in model.geometry.lines:
            rho = np.asarray(line.resistivity, float)
            exp = (line.geometry.z.size, line.geometry.x.size)
            rep.add("C3.shape", rho.shape == exp, f"line {line.line_id}: {rho.shape} vs {exp}")
            finite = rho[np.isfinite(rho)]
            rep.add("C2.positive", bool(np.all(finite > 0)), f"line {line.line_id}")
        dv = getattr(model.geometry, "derived_volume", None)
        if dv is not None:
            rep.add("C7.synthesized", bool(dv.synthesized), "derived volume must be synthesized")
    else:
        rho = np.asarray(model.resistivity, float)
        shapes = _expected_shape(model)
        rep.add("C3.shape", rho.shape in shapes, f"resistivity {rho.shape}, expected one of {shapes}")
        finite = rho[np.isfinite(rho)]
        rep.add("C2.positive", bool(np.all(finite > 0)),
                f"{int(np.sum(finite <= 0))} non-positive values")
        if model.resistivity_native is not None:
            enc = model.resistivity_native_encoding
            ok = is_known_encoding(enc)
            rep.add("C4.encoding", ok, f"encoding {enc!r}")
            if ok:
                nat = to_resistivity(model.resistivity_native, enc)
                ref = rho
                if nat.shape != rho.shape and model.resistivity_by_node is not None:
                    ref = np.asarray(model.resistivity_by_node, float)
                if nat.shape == ref.shape:
                    m = np.isfinite(nat) & np.isfinite(ref)
                    rel = (np.abs(nat[m] - ref[m]) / np.abs(ref[m])).max(initial=0.0)
                    rep.add("C5.native", bool(rel <= _REL_TOL),
                            f"max relative difference {rel:.3g}")
                else:
                    rep.add("C5.native", False, f"source shape {nat.shape} vs {ref.shape}")
        for name in ("uncertainty", "sensitivity"):
            arr = getattr(model, name)
            if arr is not None:
                rep.add("C9.uncertainty", np.asarray(arr).shape == rho.shape,
                        f"{name} shape {np.asarray(arr).shape}")
    st = model.stations
    if st is not None:
        lon, lat = getattr(st, "lon", None), getattr(st, "lat", None)
        rep.add("C8.lonlat", (lon is None) == (lat is None),
                "longitude and latitude must be set together")
    return rep
