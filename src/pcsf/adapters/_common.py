"""Helpers shared by the adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ..core.schema import StationTable, TopographyPerStation

__all__ = ["station_table", "survey_dict"]


def survey_dict(survey: Any) -> dict[str, Any]:
    """Plain dictionary of survey metadata.

    Parameters
    ----------
    survey : mapping or object or None
        Mapping, object with ``to_dict()``, or ``None``.

    Returns
    -------
    dict
        Empty for ``None``.
    """
    if survey is None:
        return {}
    to_dict = getattr(survey, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    return dict(survey)


def station_table(
    names: Sequence[str],
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    *,
    station_lonlat: Mapping[str, tuple[float, float]] | None = None,
    station_elevations: Mapping[str, float] | None = None,
) -> tuple[StationTable, TopographyPerStation | None]:
    """Station table and optional topography from per-name values.

    Parameters
    ----------
    names : sequence of str
        Station names in file order.
    x, y, z : array_like of shape (n,)
        Model-frame coordinates, metres.
    station_lonlat : mapping of str to (lon, lat), optional
        WGS84 positions; stations missing from it get NaN.
    station_elevations : mapping of str to float, optional
        Elevations in metres; they replace *z* for the stations they
        name and define the topography.

    Returns
    -------
    stations : StationTable
    topography : TopographyPerStation or None
        Set only when *station_elevations* is given.
    """
    names = list(names)
    z = np.asarray(z, dtype=float).copy()
    topo = None
    if station_elevations:
        for i, name in enumerate(names):
            if name in station_elevations:
                z[i] = float(station_elevations[name])
        topo = TopographyPerStation(
            station_id=list(names), elevation=z
        )
    lon = lat = None
    if station_lonlat:
        pairs = np.array(
            [station_lonlat.get(n, (np.nan, np.nan)) for n in names],
            dtype=float,
        ).reshape(len(names), 2)
        if not np.all(np.isnan(pairs)):
            lon, lat = pairs[:, 0], pairs[:, 1]
    table = StationTable(
        name=names,
        x=np.asarray(x, dtype=float),
        y=np.asarray(y, dtype=float),
        z=z,
        lon=lon,
        lat=lat,
    )
    return table, topo
