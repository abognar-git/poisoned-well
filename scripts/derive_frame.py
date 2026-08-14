#!/usr/bin/env python3
"""Turn the capture log into a coverage statement: what fraction of what was published
this corpus actually holds.

Both captured tiers number sequentially — the mirror's article ids and Telegram's post
ids both increment — so consecutive runs bracket what a source issued in between. If a
channel's highest id was 264,306 at 07:00 and 264,331 at 08:00, it published 25 items in
that hour, and the number we captured out of those 25 is the coverage. Nothing about
that is an estimate.

Two numbers, and they answer different questions:

One number, computed as a set difference: the ids this archive actually holds, over the
ids the source issued across the whole span we have observed. A gap is an item that
exists and this corpus does not have — filtered out by our own rules, published and
replaced between two runs, or simply missed. The measure does not distinguish those, and
must not be read as if it did.

An earlier version of this script compared only each run's min and max id and reported
100% for every source. That was tautological: if the window spanned the gap it assumed
everything in the gap had been captured. Coverage is a question about sets.

    python3 scripts/derive_frame.py
"""
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAME = ROOT / "data" / "archive" / "frame.csv"
OUT = ROOT / "data" / "archive" / "coverage.json"


ARCHIVE = ROOT / "data" / "archive"


def captured_ids():
    """Every id this project actually holds, per source. The frame logs the window a run
    saw; only the archive knows which ids inside it survived."""
    have = defaultdict(set)
    for f in sorted(ARCHIVE.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("id") or "").isdigit():
                have[r["site"]].add(int(r["id"]))
    return have


def main() -> int:
    if not FRAME.exists():
        print("no frame.csv yet — run scripts/capture_specimens.py")
        return 1
    rows = list(csv.DictReader(FRAME.open()))
    by_site = defaultdict(list)
    for r in rows:
        by_site[r["site"]].append(r)
    have = captured_ids()

    per_site, runs = {}, sorted({r["run_id"] for r in rows})
    for site, rs in by_site.items():
        rs.sort(key=lambda r: r["captured_at"])
        seq = [r for r in rs if r["max_id"]]
        ids = have.get(site, set())

        # Coverage is a set question, not an arithmetic one. An earlier version compared
        # only the min and max of each run and therefore reported 100% by construction:
        # if the window spanned the gap it assumed everything in the gap was captured.
        # It is the ids we actually hold, over the ids the source issued across the whole
        # observed span, that says what fraction of its output this corpus contains.
        lo = min(ids) if ids else None
        hi = max(ids) if ids else None
        span = (hi - lo + 1) if ids and hi > lo else None
        missing = sorted(set(range(lo, hi + 1)) - ids)[:20] if span else []

        per_site[site] = {
            "runs": len(rs),
            "sequential_ids": bool(seq),
            "captured": len(ids) or None,
            "id_span_observed": span,
            "first_id": lo, "last_id": hi,
            "coverage": round(len(ids) / span, 4) if span else None,
            "missing_examples": missing,
            "empty_runs": sum(1 for r in rs if r["reason"]),
        }

    seqs = [v for v in per_site.values() if v["coverage"] is not None]
    out = {
        "note": ("Coverage of this corpus, computed by comparing the ids actually held in the "
                 "archive against the id span observed across every logged run. Both captured "
                 "tiers number sequentially, so a gap is an item the source issued and this "
                 "corpus does not contain — filtered out, published between runs, or missed. "
                 "This does not say which. Outlet listings expose no sequential ids and carry "
                 "nulls."),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_logged": len(runs),
        "first_run": runs[0] if runs else None,
        "last_run": runs[-1] if runs else None,
        "measurable_sources": len(seqs),
        "coverage_overall": (round(sum(v["captured"] for v in seqs)
                                   / sum(v["id_span_observed"] for v in seqs), 4)
                             if seqs else None),
        "by_source": dict(sorted(per_site.items())),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    n_seq = sum(1 for v in per_site.values() if v["sequential_ids"])
    print(f"coverage.json: {len(runs)} run(s) logged, {n_seq} sources with sequential ids")
    if seqs:
        print(f"  corpus holds {out['coverage_overall']:.1%} of the ids issued across the "
              f"observed span")
    for s, v in sorted(per_site.items()):
        if v["coverage"] is not None:
            print(f"  {s:<18} {v['captured']:>4} of {v['id_span_observed']:>5} issued "
                  f"= {v['coverage']:>6.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
