"""``pcsf`` command-line tool.

Commands::

    pcsf info FILE
    pcsf validate FILE [FILE ...]
    pcsf convert SRC DST [--log10-view]
    pcsf compare A B
    pcsf version

``compare`` needs two models of the same geometry kind and shape; to
compare different geometries, sample them first with
:func:`pcsf.algorithms.sample_log10`.

The exit status is 0 on success, 1 when a validation fails and 2 on
usage or read errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

import numpy as np

from .. import api
from .._version import FORMAT_VERSION, __version__
from ..exceptions import PCSFError
from ..plugins import load_plugins

__all__ = ["build_parser", "main"]


def _cmd_info(args: argparse.Namespace) -> int:
    print(json.dumps(api.info(args.file), indent=2, default=str))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    status = 0
    for path in args.files:
        report = api.validate(path)
        print(f"== {path}")
        print(report)
        status |= 0 if report.passed else 1
    return status


def _cmd_convert(args: argparse.Namespace) -> int:
    kwargs = {"log10_view": True} if args.log10_view else {}
    out = api.convert(args.src, args.dst, **kwargs)
    print(f"wrote {out}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from ..algorithms.comparison import compare_log10

    a, b = api.read(args.a), api.read(args.b)
    same_shape = np.shape(a.resistivity) == np.shape(b.resistivity)
    if a.kind != b.kind or not same_shape:
        print(
            "models differ in geometry kind or shape; resample "
            "them first (pcsf.algorithms.sample_log10)",
            file=sys.stderr,
        )
        return 2
    with np.errstate(divide="ignore", invalid="ignore"):
        log_a = np.log10(np.asarray(a.resistivity, dtype=float))
        log_b = np.log10(np.asarray(b.resistivity, dtype=float))
    res = compare_log10(log_a.ravel(), log_b.ravel())
    print(json.dumps(res.as_dict(), indent=2))
    return 0


def _cmd_version(args: argparse.Namespace) -> int:
    print(f"pcsf {__version__} (format {FORMAT_VERSION})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Argument parser of the ``pcsf`` command.

    Returns
    -------
    argparse.ArgumentParser
        Parser with one sub-command per command; each sets ``func``
        to its handler.

    Examples
    --------
    >>> from pcsf.cli.main import build_parser
    >>> parser = build_parser()
    >>> args = parser.parse_args(["convert", "a.pcsm", "b.pcsf"])
    >>> args.command, args.src, args.dst, args.log10_view
    ('convert', 'a.pcsm', 'b.pcsf', False)
    """
    p = argparse.ArgumentParser(
        prog="pcsf",
        description="Portable Common Subsurface Format tools",
    )
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("info", help="describe a PCSF or PCSM file")
    s.add_argument("file")
    s.set_defaults(func=_cmd_info)
    s = sub.add_parser("validate", help="check the conformance rules")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=_cmd_validate)
    s = sub.add_parser(
        "convert", help="convert between .pcsf, .pcsm and .pcsm.gz"
    )
    s.add_argument("src")
    s.add_argument("dst")
    s.add_argument(
        "--log10-view",
        action="store_true",
        help="add a log10 view in PCSM output",
    )
    s.set_defaults(func=_cmd_convert)
    s = sub.add_parser(
        "compare", help="compare two models on the same grid"
    )
    s.add_argument("a")
    s.add_argument("b")
    s.set_defaults(func=_cmd_compare)
    s = sub.add_parser("version", help="print versions")
    s.set_defaults(func=_cmd_version)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``pcsf`` command.

    Parameters
    ----------
    argv : sequence of str, optional
        Arguments without the program name; ``sys.argv[1:]`` when
        ``None``.

    Returns
    -------
    int
        Exit status: 0 on success, 1 when a validation fails, 2 on
        read errors. Usage errors exit through ``SystemExit(2)``
        raised by :mod:`argparse`.

    Notes
    -----
    Plugins are loaded before the command runs; a failing plugin
    emits a warning and does not stop the command.

    Examples
    --------
    >>> from pcsf.cli.main import main
    >>> main(["version"])  # doctest: +ELLIPSIS
    pcsf ... (format ...)
    0
    """
    args = build_parser().parse_args(argv)
    load_plugins(on_error="warn")
    try:
        return int(args.func(args))
    except (PCSFError, OSError) as exc:
        print(f"pcsf: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
