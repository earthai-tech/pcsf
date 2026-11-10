"""Download and check the data archive of the paper.

The archive (``pcsf-paper-data-<version>.zip``) holds the models,
the native solver runs, the processed EDI files and the EMC files the
reproduction reads. This script downloads it from the Zenodo record
in ``data_source.json`` (or takes a local copy), checks the archive's
SHA-256, unpacks it into ``paper/data`` and checks every file against
``data/SHA256SUMS``.

    python paper/fetch_data.py                  # download from Zenodo
    python paper/fetch_data.py --file X.zip     # use a local copy
    python paper/fetch_data.py --check          # only re-check files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
DATA = PAPER / "data"
SOURCE = PAPER / "data_source.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check(data: Path = DATA) -> int:
    """Check every file listed in SHA256SUMS; return the failures."""
    sums = data / "SHA256SUMS"
    if not sums.exists():
        print(f"{sums} not found")
        return 1
    bad = 0
    lines = sums.read_text(encoding="utf-8").splitlines()
    for line in lines:
        digest, rel = line.split(None, 1)
        f = data / rel
        if not f.exists():
            print(f"missing  {rel}")
            bad += 1
        elif sha256(f) != digest:
            print(f"changed  {rel}")
            bad += 1
    print(f"{len(lines) - bad} of {len(lines)} files verified")
    return bad


def download(url: str, dst: Path) -> None:
    print(f"downloading {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "pcsf-paper-fetch"})
    with urllib.request.urlopen(req) as r, dst.open("wb") as fh:
        shutil.copyfileobj(r, fh)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--file", type=Path,
                   help="local copy of the archive")
    p.add_argument("--check", action="store_true",
                   help="only check the unpacked files")
    args = p.parse_args(argv)
    if args.check:
        return 1 if check() else 0
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        archive = args.file
        if archive is None:
            if not src.get("url"):
                print("The Zenodo record is not published yet; pass a "
                      "local copy with --file.")
                return 2
            archive = Path(tmp) / src["file"]
            download(src["url"], archive)
        digest = sha256(archive)
        if src.get("sha256") and digest != src["sha256"]:
            print(f"archive SHA-256 {digest} does not match "
                  f"{src['sha256']} in data_source.json")
            return 1
        with zipfile.ZipFile(archive) as zf:
            for name in zf.namelist():
                if not name.startswith("data/") or ".." in name:
                    print(f"unexpected entry {name!r}; stopping")
                    return 1
            zf.extractall(PAPER)
    return 1 if check() else 0


if __name__ == "__main__":
    sys.exit(main())
