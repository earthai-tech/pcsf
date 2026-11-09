"""Tests for the JSON Schemas and their agreement with the code."""

import pytest

from pcsf import schemas
from pcsf.core.provenance import ModelProvenance
from pcsf.core.record import (
    RECOMMENDED_FIELDS,
    REQUIRED_FIELDS,
    TERMINATIONS,
    InversionRecord,
    check_inversion_record,
)


def _paths(schema, prefix=""):
    """Dotted paths of every property and of the required ones."""
    props, required = set(), set()
    for name, sub in schema.get("properties", {}).items():
        path = f"{prefix}{name}"
        props.add(path)
        if (
            name in schema.get("required", [])
            and "properties" not in sub
        ):
            required.add(path)
        sub_props, sub_req = _paths(sub, path + ".")
        props |= sub_props
        if name in schema.get("required", []):
            required |= sub_req
    return props, required


def _complete():
    return InversionRecord(
        "Occam2D",
        data={
            "components": ["TE rho"],
            "frequency_range_hz": [1.0, 100.0],
            "n_stations": 5,
            "errors": "10 %",
        },
        regularization={"type": "smoothness"},
        misfit={"final_rms": 1.1, "termination": "target_reached"},
    )


def test_schema_required_fields_match_code():
    props, required = _paths(schemas.load("inversion-record"))
    assert required == set(REQUIRED_FIELDS)
    assert set(RECOMMENDED_FIELDS) <= props


def test_schema_termination_values_match_code():
    schema = schemas.load("inversion-record")
    enum = schema["properties"]["misfit"]["properties"]["termination"]
    assert tuple(enum["enum"]) == TERMINATIONS


def test_complete_record_is_valid_both_ways():
    pytest.importorskip("jsonschema")
    rec = _complete()
    assert check_inversion_record(rec)["required"] == []
    assert schemas.validate(rec.as_dict(), "inversion-record") == []


def test_incomplete_record_is_invalid():
    pytest.importorskip("jsonschema")
    payload = _complete().as_dict()
    del payload["misfit"]["termination"]
    errors = schemas.validate(payload, "inversion-record")
    assert len(errors) == 1 and "termination" in errors[0]


def test_provenance_schema():
    pytest.importorskip("jsonschema")
    prov = ModelProvenance(architecture="UNet", random_seed=3)
    assert schemas.validate(prov.to_dict(), "model-provenance") == []
    bad = dict(prov.to_dict(), checkpoint_sha256="xyz", colour="red")
    assert len(schemas.validate(bad, "model-provenance")) == 2


def test_unknown_schema():
    with pytest.raises(KeyError):
        schemas.load("borehole")
