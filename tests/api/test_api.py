"""Tests for the public facade, registry and foundation modules."""

import logging
import warnings

import numpy as np
import pytest

import pcsf
from pcsf import Grid2DGeometry, PCSFModel
from pcsf.api.property import MetadataMixin, PCSFObject
from pcsf.api.registry import (
    ENCODINGS,
    Registry,
    get_encoding,
    register_encoding,
)
from pcsf.compat.optional import import_optional, is_available
from pcsf.decorators import (
    deprecated,
    log_call,
    requires,
    validates_model,
)
from pcsf.exceptions import (
    EncodingError,
    FormatError,
    MissingDependencyError,
    PCSFError,
    RegistryError,
    VersionError,
)
from pcsf.utils.hashing import sha256_array
from pcsf.utils.text import format_float


def _model():
    native = np.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
    return PCSFModel(
        geometry=Grid2DGeometry(x=[0.0, 10.0, 20.0], z=[5.0, 15.0]),
        resistivity=10.0**native,
        resistivity_native=native,
        resistivity_native_encoding="log10",
    )


# ------------------------------------------------------------------
# facade
@pytest.mark.parametrize(
    "suffix,kind",
    [(".pcsf", "pcsf"), (".pcsm", "pcsm"), (".pcsm.gz", "pcsm.gz")],
)
def test_write_detect_read_roundtrip(tmp_path, suffix, kind):
    m = _model()
    p = pcsf.write(m, tmp_path / f"m{suffix}")
    assert pcsf.detect(p) == kind
    back = pcsf.read(p)
    assert np.array_equal(back.resistivity, m.resistivity)
    assert np.array_equal(
        back.resistivity_native, m.resistivity_native
    )


def test_detect_ignores_extension(tmp_path):
    p = pcsf.write(_model(), tmp_path / "m.pcsf")
    renamed = p.rename(tmp_path / "m.dat")
    assert pcsf.detect(renamed) == "pcsf"


def test_convert_chain_is_bit_exact(tmp_path):
    m = _model()
    a = pcsf.write(m, tmp_path / "a.pcsf")
    b = pcsf.convert(a, tmp_path / "b.pcsm")
    c = pcsf.convert(b, tmp_path / "c.pcsm.gz")
    d = pcsf.convert(c, tmp_path / "d.pcsf")
    assert np.array_equal(pcsf.read(d).resistivity, m.resistivity)


def test_validate_and_info(tmp_path):
    rep = pcsf.validate(_model())
    assert rep.passed, str(rep)
    info = pcsf.info(_model())
    assert info["kind"] == "grid2d" and info["shape"] == (2, 3)


def test_validate_detects_bad_native():
    m = _model()
    m.resistivity_native = m.resistivity_native + 0.1
    rep = pcsf.validate(m)
    assert not rep.passed and rep.failures[0].rule == "C5.native"
    with pytest.raises(pcsf.ConformanceError):
        rep.raise_if_failed()


def test_bad_suffix_and_not_a_file(tmp_path):
    with pytest.raises(FormatError):
        pcsf.write(_model(), tmp_path / "m.txt")
    junk = tmp_path / "junk.bin"
    junk.write_bytes(b"not a model")
    with pytest.raises(FormatError):
        pcsf.read(junk)


# ------------------------------------------------------------------
# exceptions
def test_exception_hierarchy():
    for cls in (
        FormatError,
        VersionError,
        EncodingError,
        RegistryError,
        MissingDependencyError,
    ):
        assert issubclass(cls, PCSFError)
    assert issubclass(VersionError, ValueError)
    assert issubclass(MissingDependencyError, ImportError)
    err = MissingDependencyError(
        "netCDF4", extra="emc", feature="EMC files"
    )
    assert 'pip install "pcsf[emc]"' in str(err)


# ------------------------------------------------------------------
# registry
def test_registry_refuses_overwrite():
    reg = Registry("thing")
    reg.register("a", 1)
    with pytest.raises(RegistryError):
        reg.register("a", 2)
    reg.register("a", 2, replace=True)
    assert reg.get("a") == 2
    with pytest.raises(RegistryError):
        reg.get("b")


def test_plugin_encoding_is_accepted_by_schema(tmp_path):
    name = "test_neg_log10"
    if name not in ENCODINGS:

        @register_encoding(name, description="test encoding")
        def _f(r):
            return 10.0 ** (-r)

    native = np.array([[-1.0, -2.0]])
    m = PCSFModel(
        geometry=Grid2DGeometry(x=[0.0, 1.0], z=[1.0]),
        resistivity=10.0 ** (-native),
        resistivity_native=native,
        resistivity_native_encoding=name,
    )
    m.validate()
    assert pcsf.validate(m).passed
    ENCODINGS.unregister(name)
    with pytest.raises(EncodingError):
        get_encoding(name)


# ------------------------------------------------------------------
# property
def test_pcsfobject_repr_clone_update():
    class Obj(PCSFObject, MetadataMixin):
        def __init__(self):
            self.name = "S001"
            self.values = [1, 2, 3]
            self.metadata = {}

        def validate(self):
            if self.name == "":
                raise ValueError("empty")

    o = Obj()
    assert repr(o).startswith("Obj(name='S001', values=list(len=3")
    c = o.clone(name="S002")
    assert c.name == "S002" and o.name == "S001"
    with pytest.raises(ValueError):
        o.update(name="")
    o.update_metadata(a=1)
    assert o.metadata_dict() == {"a": 1}


# ------------------------------------------------------------------
# decorators
def test_requires_reports_extra():
    @requires("definitely_not_a_module_xyz", feature="test")
    def f():
        return 1

    with pytest.raises(MissingDependencyError):
        f()
    assert requires("numpy")(lambda: 2)() == 2


def test_deprecated_warns():
    @deprecated(since="0.1", use="g")
    def f():
        return 3

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert f() == 3
    assert any(issubclass(x.category, DeprecationWarning) for x in w)


def test_validates_model_decorator():
    @validates_model(arg="model")
    def f(model):
        return model.kind

    assert f(_model()) == "grid2d"


def test_log_call(caplog):
    @log_call()
    def f():
        return 4

    with caplog.at_level(logging.DEBUG, logger="pcsf"):
        assert f() == 4


# ------------------------------------------------------------------
# compat and utils
def test_optional_imports():
    assert is_available("numpy")
    assert not is_available("definitely_not_a_module_xyz")
    with pytest.raises(MissingDependencyError):
        import_optional("definitely_not_a_module_xyz")


def test_format_float_roundtrips():
    for v in (0.1, 1 / 3, 1e-300, 123456789.123456789, -2.5e17):
        assert float(format_float(v)) == v
    assert format_float(float("nan")) == "nan"


def test_sha256_array_depends_on_dtype_and_shape():
    a = np.arange(6.0)
    assert sha256_array(a) != sha256_array(a.reshape(2, 3))
    assert sha256_array(a) != sha256_array(a.astype(np.float32))
