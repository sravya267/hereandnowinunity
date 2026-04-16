"""Download Swiss Ephemeris data files from the official repository.

Files are pulled from the public astrodienst/aloistr swisseph GitHub
mirror. By default we grab the planetary, lunar, and asteroid files for
1800–2399 CE plus Chiron — enough for any currently-living person.

Usage:
    python scripts/download_ephemeris.py

To pick a different range or add files, edit the FILES list below.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


BASE_URL = "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"

# 1800–2399 CE covers everyone currently alive. Add _12, _24, etc. for
# earlier or later ranges; see https://github.com/aloistr/swisseph/tree/master/ephe
FILES: list[str] = [
    "sepl_18.se1",   # planets 1800–2399
    "semo_18.se1",   # moon 1800–2399
    "seas_18.se1",   # main asteroids 1800–2399
    "seasnam.txt",   # asteroid name index
    "sefstars.txt",  # fixed stars
    "seleapsec.txt", # leap seconds
    # Chiron lives in its own asteroid file
    "ast0/se02060.se1",
]


def download(file_path: str, target_dir: Path) -> Path:
    """Download a single file, skipping if it already exists."""
    url = f"{BASE_URL}/{file_path}"
    dest = target_dir / file_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {file_path} (already present)")
        return dest

    print(f"  [get ] {file_path}")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as exc:  # noqa: BLE001
        print(f"  [fail] {file_path}: {exc}", file=sys.stderr)
        if dest.exists():
            dest.unlink()
        raise
    return dest


def main() -> int:
    target = Path(__file__).resolve().parent.parent / "ephe"
    target.mkdir(exist_ok=True)

    print(f"Downloading Swiss Ephemeris files to {target}")
    print(f"Source: {BASE_URL}\n")

    failed: list[str] = []
    for f in FILES:
        try:
            download(f, target)
        except Exception:  # noqa: BLE001
            failed.append(f)

    print()
    if failed:
        print(f"Failed: {len(failed)} file(s)")
        for f in failed:
            print(f"  - {f}")
        return 1
    print(f"Done. {len(FILES)} file(s) in {target}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
