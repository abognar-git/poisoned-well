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

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = "CheckFirstHQ/pravda-network"
RAW = f"https://raw.githubusercontent.com/{REPO}/main"
API = f"https://api.github.com/repos/{REPO}/contents"

# The CEE focus set: the anchor case (Hungary) plus the comparison elections
# covered on the site. Everything else is represented via the manifest only.
# The seven regional mirrors the narrative uses. --all fetches every domain in the
# manifest instead (~51 MB, 101 files), which is what the peer-control instrument wants:
# a 100-donor pool turns a 12-episode scan into an actual distribution.
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
    ap = argparse.ArgumentParser(description="Fetch CheckFirst's Pravda-network viz data.")
    ap.add_argument("--all", action="store_true",
                    help="fetch every domain in the manifest (~51 MB), not just the regional seven")
    ap.add_argument("--delay", type=float, default=0.4,
                    help="seconds between requests; be a polite client")
    a = ap.parse_args()

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

    targets = [d["domain"] for d in domains] if a.all else TARGET_DOMAINS
    print(f"fetching {len(targets)} domain(s)"
          f"{' — full manifest' if a.all else ' — regional subset'}")

    failures, got = 0, 0
    for i, d in enumerate(targets, 1):
        viz = OUT / "json" / f"{d}_viz.json"
        try:
            viz.write_bytes(get(f"{RAW}/json/{d}_viz.json"))
            got += 1
            if a.all and i % 20 == 0:
                print(f"  ...{i}/{len(targets)}")
            elif not a.all:
                print(f"viz  : {d} ({viz.stat().st_size:,} bytes)")
        except Exception as e:
            failures += 1
            print(f"viz  : {d} FAILED ({e})", file=sys.stderr)
        if a.delay:
            time.sleep(a.delay)

    print(f"fetched {got}/{len(targets)}; {failures} failed")
    # a partial fetch is usable — the instrument reports its own donor count — so only
    # fail hard if nothing landed at all
    return 1 if got == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
