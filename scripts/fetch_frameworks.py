#!/usr/bin/env python3
"""Fetch the DISARM framework and Meta's CIB threat indicators.

Both repos are small, so they are shallow-cloned into data/raw/:

  - facebook/threat-research         (MIT)          -> data/raw/meta-threat-research
  - DISARMFoundation/DISARMframeworks (CC-BY-SA-4.0) -> data/raw/disarm
  - DISARM STIX 2.1 bundle (single JSON, fetched raw) -> data/raw/disarm-stix/DISARM.json
"""

import subprocess
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

CLONES = {
    "meta-threat-research": "https://github.com/facebook/threat-research.git",
    "disarm": "https://github.com/DISARMFoundation/DISARMframeworks.git",
}

STIX_URL = (
    "https://raw.githubusercontent.com/DISARMFoundation/DISARM-STIX2/main/output/DISARM.json"
)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in CLONES.items():
        dest = RAW_DIR / name
        if dest.exists():
            subprocess.run(["git", "-C", str(dest), "pull", "-q"], check=True)
            print(f"updated: {name}")
        else:
            subprocess.run(["git", "clone", "-q", "--depth", "1", url, str(dest)], check=True)
            print(f"cloned : {name}")

    stix_dir = RAW_DIR / "disarm-stix"
    stix_dir.mkdir(exist_ok=True)
    req = urllib.request.Request(STIX_URL, headers={"User-Agent": "poisoned-well-research"})
    with urllib.request.urlopen(req, timeout=120) as r:
        (stix_dir / "DISARM.json").write_bytes(r.read())
    print(f"fetched: DISARM.json ({(stix_dir / 'DISARM.json').stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
