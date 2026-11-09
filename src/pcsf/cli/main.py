"""``pcsf`` command-line tool.

Commands::

    pcsf info FILE
    pcsf validate FILE [FILE ...]
    pcsf convert SRC DST [--log10-view]
    pcsf compare A B          (same geometry kind and grid)
    pcsf version

Exit status: 0 on success, 1 when validation fails, 2 on usage or read errors.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from .. import api
from .._version import FORMAT_VERSION, __version__
from ..exceptions import PCSFError
from ..plugins import load_plugins

__all__ = ["main"]


def _cmd_info(args) -> int:
    print(json.dumps(api.info(args.file), indent=2, default=str))
    return 0


def _cmd_validate(args) -> int:
    status = 0
    for path in args.files:
        report = api.validate(path)
        print(f"== {path}")
        print(report)
        status |= 0 if report.passed else 1
    return status


def _cmd_convert(args) -> int:
    kwargs = {"log10_view": True} if args.log10_view else {}
    out = api.convert(args.src, args.dst, **kwargs)
    print(f"wrote {out}")
    return 0


def _cmd_compare(args) -> int:
    from ..algorithms.comparison import compare_log10

    a, b = api.read(args.a), api.read(args.b)
    if a.kind != b.kind or np.shape(a.resistivity) != np.shape(b.resistivity):
        print("models differ in geometry kind or shape; resample them first "
              "(pcsf.algorithms.sampling)", file=sys.stderr)
        return 2
    with np.errstate(divide="ignore", invalid="ignore"):
        res = compare_log10(np.log10(np.asarray(a.resistivity, float)).ravel(),
                            np.log10(np.asarray(b.resistivity, float)).ravel())
    print(json.dumps(res.as_dict(), indent=2))
    return 0


def _cmd_version(args) -> int:
    print(f"pcsf {__version__} (format {FORMAT_VERSION})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pcsf", description="Portable Common Subsurface Format tools")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("info", help="describe a PCSF or PCSM file")
    s.add_argument("file")
    s.set_defaults(func=_cmd_info)
    s = sub.add_parser("validate", help="check the conformance rules")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=_cmd_validate)
    s = sub.add_parser("convert", help="convert between .pcsf, .pcsm and .pcsm.gz")
    s.add_argument("src")
    s.add_argument("dst")
    s.add_argument("--log10-view", action="store_true", help="add a log10 view in PCSM output")
    s.set_defaults(func=_cmd_convert)
    s = sub.add_parser("compare", help="compare two models on the same grid")
    s.add_argument("a")
    s.add_argument("b")
    s.set_defaults(func=_cmd_compare)
    s = sub.add_parser("version", help="print versions")
    s.set_defaults(func=_cmd_version)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    load_plugins(on_error="warn")
    try:
        return int(args.func(args))
    except (PCSFError, OSError) as exc:
        print(f"pcsf: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
