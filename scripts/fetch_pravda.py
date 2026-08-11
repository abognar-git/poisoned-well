#!/usr/bin/env python3
"""Fetch Pravda-network (Portal Kombat) data from CheckFirst's hourly-updated mirror.

The upstream repo (github.com/CheckFirstHQ/pravda-network, ~36 GB) is far too large
to clone, so this pulls only what the site needs:

  1. the domain manifest  -> data/raw/pravda/domains.json   (all mirrors + file sizes)
  2. per-domain viz JSONs -> data/raw/pravda/json/<domain>_viz.json  (TARGET_DOMAINS only)

Note: the per-domain CSVs described in the upstream README (data/<domain>.csv.gz)
no longer exist on main; the aggregated viz JSONs are the published artifact.

Cite: CheckFirst. Pravda Network Data Collection. https://github.com/CheckFirstHQ/pravda-network
"""

import json
import sys
import urllib.request
from pathlib import Path

REPO = "CheckFirstHQ/pravda-network"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
API = f"https://api.github.com/repos/{REPO}/contents"

# The CEE focus set: the anchor case (Hungary) plus the comparison elections
# covered on the site. Everything else is represented via the manifest only.
TARGET_DOMAINS = [
    "hungary.news-pravda.com",
    "slovakia.news-pravda.com",
    "romania.news-pravda.com",
    "moldova.news-pravda.com",
    "czechia.news-pravda.com",
    "deutsch.news-pravda.com",
    "poland.news-pravda.com",
]

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "pravda"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "poisoned-well-research"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "json").mkdir(exist_ok=True)
    (OUT / "csv").mkdir(exist_ok=True)

    manifest = json.loads(get(f"{API}/json"))
    domains = [
        {"file": it["name"], "domain": it["name"].replace("_viz.json", ""), "size": it["size"]}
        for it in manifest
        if it["name"].endswith("_viz.json")
    ]
    (OUT / "domains.json").write_text(json.dumps(domains, indent=2))
    print(f"manifest: {len(domains)} domains -> {OUT / 'domains.json'}")

    failures = 0
    for d in TARGET_DOMAINS:
        try:
            viz = OUT / "json" / f"{d}_viz.json"
            viz.write_bytes(get(f"{RAW}/json/{d}_viz.json"))
            print(f"viz  : {d} ({viz.stat().st_size:,} bytes)")
        except Exception as e:
            failures += 1
            print(f"viz  : {d} FAILED ({e})", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
