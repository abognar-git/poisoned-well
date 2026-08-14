#!/usr/bin/env python3
"""Turn the capture log into a coverage statement: what fraction of what was published
this corpus actually holds.

Both captured tiers number sequentially — the mirror's article ids and Telegram's post
ids both increment — so consecutive runs bracket what a source issued in between. If a
channel's highest id was 264,306 at 07:00 and 264,331 at 08:00, it published 25 items in
that hour, and the number we captured out of those 25 is the coverage. Nothing about
that is an estimate.

Two numbers, and they answer different questions:

  within_window   of the ids present in a single run's harvest, how many we kept. The
                  gaps are our own filters — smear, minimum length, dedup — not missed
                  publications. This is filter attrition.
  between_runs    of the ids a source issued between one run and the next, how many we
                  captured. This is sampling coverage, and it is the one that bounds any
                  claim made on this corpus.

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


def main() -> int:
    if not FRAME.exists():
        print("no frame.csv yet — run scripts/capture_specimens.py")
        return 1
    rows = list(csv.DictReader(FRAME.open()))
    by_site = defaultdict(list)
    for r in rows:
        by_site[r["site"]].append(r)

    per_site, runs = {}, sorted({r["run_id"] for r in rows})
    for site, rs in by_site.items():
        rs.sort(key=lambda r: r["captured_at"])
        seq = [r for r in rs if r["max_id"]]
        within = [float(r["observed_fraction"]) for r in rs if r["observed_fraction"]]

        issued = captured = 0
        gaps = []
        for a, b in zip(seq, seq[1:]):
            hi_a, hi_b, lo_b = int(a["max_id"]), int(b["max_id"]), int(b["min_id"])
            if hi_b <= hi_a:
                continue                       # nothing new published between the runs
            new_ids = hi_b - hi_a              # what the source issued in the interval
            # what we could even see: our window starts at lo_b, so anything issued
            # before that and after the previous run is already outside the harvest
            seen = max(0, hi_b - max(hi_a, lo_b - 1))
            issued += new_ids
            captured += min(seen, int(b["items"]))
            if new_ids > seen:
                gaps.append(new_ids - seen)

        per_site[site] = {
            "runs": len(rs),
            "sequential_ids": bool(seq),
            "within_window": round(statistics.mean(within), 4) if within else None,
            "issued_between_runs": issued or None,
            "captured_of_those": captured or None,
            "between_runs": round(captured / issued, 4) if issued else None,
            "ids_past_the_window": sum(gaps) or 0,
            "empty_runs": sum(1 for r in rs if r["reason"]),
        }

    seqs = [v for v in per_site.values() if v["between_runs"] is not None]
    out = {
        "note": ("Coverage of this corpus, computed from the capture log rather than estimated. "
                 "`within_window` is filter attrition inside one harvest; `between_runs` is "
                 "sampling coverage across consecutive runs and is the number that bounds any "
                 "claim made on the archive. Sources whose ids are not sequential (the outlet "
                 "listings) cannot be measured this way and carry nulls."),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs_logged": len(runs),
        "first_run": runs[0] if runs else None,
        "last_run": runs[-1] if runs else None,
        "measurable_sources": len(seqs),
        "coverage_between_runs": (round(sum(v["captured_of_those"] for v in seqs)
                                        / sum(v["issued_between_runs"] for v in seqs), 4)
                                  if seqs else None),
        "by_source": dict(sorted(per_site.items())),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    n_seq = sum(1 for v in per_site.values() if v["sequential_ids"])
    print(f"coverage.json: {len(runs)} run(s) logged, {n_seq} sources with sequential ids")
    if seqs:
        print(f"  sampling coverage between runs: {out['coverage_between_runs']:.1%}")
    else:
        print("  no interval to measure yet — coverage needs two runs with new items "
              "between them, which the hourly schedule will produce")
    for s, v in sorted(per_site.items()):
        if v["between_runs"] is not None:
            print(f"  {s:<18} {v['captured_of_those']:>5} of {v['issued_between_runs']:>5} issued "
                  f"= {v['between_runs']:.0%}"
                  + (f"  ({v['ids_past_the_window']} past our window)" if v["ids_past_the_window"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
