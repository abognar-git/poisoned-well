#!/usr/bin/env python3
"""Publish the network's credit graph as citable, analysable tables.

CheckFirst's per-mirror files carry a `sourcesByDay` panel — mirror x date x credited
source — for all 101 mirrors, ~871 days deep. Until now one script read one mirror of it.
The rest, the other hundred, sat unread. It is the largest analysable object in this
repository and it is nobody's secret: the value is not the data, it is publishing it in a
shape a researcher can regress on, with its censoring written down.

Two aggregations of one job:

  panel/mirror_day.csv            mirror x date x articles                  (~88k rows)
  panel/mirror_source_day/*.csv   mirror x date x source x credits, monthly (large)
  panel/source_index.csv          THE TRANSPOSE — source-first, one row per source
  panel/mirror_meta.csv           per-mirror totals, span, language mix

The transpose is the part that does not exist anywhere else. It answers "which mirrors
does this channel feed, and how exclusively" for every source in the network, which is
the question an analyst actually arrives with.

CENSORING, and it is not a footnote. `sourcesByDay` carries only each mirror's TOP-10
sources per day. The panel is therefore right-censored in a way that varies by mirror and
by month, and any "share of credits" computed from it has a denominator that silently
changes. DICTIONARY.md states this and every consumer must condition on the top-10 set.
Daily counts are collection-side: a fall is jointly a publishing decision and a collector
artefact, and this file cannot separate them.

A credit is the MIRROR'S OWN CLAIM about where it got something. It is not evidence that
the credited channel participated, cooperated, or knows the mirror exists. Every row says
so in `relationship`.

    python3 scripts/derive_feeder_index.py
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pravda" / "json"
OUT = ROOT / "data" / "panel"
REL = "credited-by-mirror"   # the mirror's own provenance label. Nothing more.


def source_type(name):
    if name.startswith("Telegram:"):
        return "telegram"
    if name.startswith("MAX "):
        return "max"
    return "domain" if "." in name else "other"


def handle(name):
    return name.split(": ", 1)[1] if ": " in name else name


def main(force: bool = False) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mirror_source_day").mkdir(exist_ok=True)

    files = sorted(RAW.glob("*_viz.json"))
    if not files:
        print("no mirror files — run scripts/fetch_pravda.py --all first")
        return 1

    # This script publishes whatever is in data/raw, and data/raw holds whatever the last
    # fetch pulled. An hourly job that fetches only the seven regional mirrors therefore
    # republished a seven-mirror panel over the hundred-and-one-mirror one — 9,905 sources
    # down to 2,803 — with nothing to notice it. Refuse to shrink the published panel.
    prev = OUT / "MANIFEST.json"
    if prev.exists() and not force:
        had = json.loads(prev.read_text()).get("mirrors", 0)
        if len(files) < had:
            print(f"refusing to shrink the panel: data/raw has {len(files)} mirrors, the "
                  f"published panel covers {had}. Run scripts/fetch_pravda.py --all, or pass "
                  f"--force if the smaller panel is what you want.")
            return 1

    mirror_day, meta, edges = [], [], []
    by_month = defaultdict(list)
    # Two views of the same graph, and they disagree by design. `sourcesByDay` is the time
    # series but carries only each mirror's TOP-10 per day; `topSources` is the mirror's
    # full credit tally with no dates. The index is built from topSources so it is complete,
    # and records separately whether a source ever surfaced in the censored daily panel —
    # which is what tells a consumer whether a time series exists for it at all.
    src = defaultdict(lambda: {"credits": 0, "mirrors": set(), "first": None, "last": None,
                               "in_daily": set()})

    for f in files:
        d = json.loads(f.read_text())
        mirror = d["domain"].split(".")[0]
        days = d.get("articlesPerDay", [])
        for x in days:
            mirror_day.append((mirror, x["date"], x["count"]))

        for t in d.get("topSources", []):
            name, n = t.get("source"), t.get("count", 0)
            if not name:
                continue
            s = src[name]
            s["credits"] += n
            s["mirrors"].add(mirror)
            edges.append((name, mirror, n))

        for row in d.get("sourcesByDay", []):
            date = row.get("date")
            if not date:
                continue
            for name, n in row.items():
                if name == "date" or not n:
                    continue
                by_month[date[:7]].append((mirror, date, name, source_type(name), n))
                s = src[name]
                s["in_daily"].add(mirror)
                s["first"] = date if not s["first"] else min(s["first"], date)
                s["last"] = date if not s["last"] else max(s["last"], date)

        langs = d.get("languages") or {}
        meta.append((
            mirror, d["domain"], d.get("totalArticles", 0),
            days[0]["date"] if days else "", days[-1]["date"] if days else "",
            len(d.get("topSources", [])),
            round(d.get("avgAlternatesPerArticle", 0) or 0, 2),
            "|".join(sorted(langs)[:6]) if isinstance(langs, dict) else "",
        ))

    def dump(path, header, rows):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
        return len(rows)

    n_md = dump(OUT / "mirror_day.csv", ["mirror", "date", "articles"], sorted(mirror_day))
    n_meta = dump(OUT / "mirror_meta.csv",
                  ["mirror", "domain", "total_articles", "first_day", "last_day",
                   "sources_listed", "avg_alternates", "languages"], sorted(meta))

    n_msd = 0
    for month, rows in sorted(by_month.items()):
        n_msd += dump(OUT / "mirror_source_day" / f"{month}.csv",
                      ["mirror", "date", "source", "source_type", "credits", "relationship"],
                      [(*r, REL) for r in sorted(rows)])

    # the transpose: one row per source, which is the view that does not exist elsewhere
    index_rows = []
    for name, s in sorted(src.items(), key=lambda kv: -kv[1]["credits"]):
        m = sorted(s["mirrors"])
        index_rows.append((
            name, handle(name), source_type(name), s["credits"], len(m),
            "exclusive" if len(m) == 1 else "shared" if len(m) < 5 else "network-wide",
            m[0] if len(m) == 1 else "",
            s["first"] or "", s["last"] or "", len(s["in_daily"]),
            "|".join(m[:12]) + ("|..." if len(m) > 12 else ""), REL,
        ))
    n_src = dump(OUT / "source_index.csv",
                 ["source", "handle", "source_type", "total_credits", "mirrors_fed",
                  "exclusivity", "exclusive_to", "first_seen_daily", "last_seen_daily",
                  "mirrors_with_daily_series", "mirrors_preview", "relationship"], index_rows)

    # The complete source->mirror graph. `mirrors_preview` above stops at 12 names, which is
    # fine to read and wrong to compute on; this is the file to join against.
    n_edge = dump(OUT / "source_mirror_edges.csv",
                  ["source", "mirror", "credits", "relationship"],
                  [(*e, REL) for e in sorted(edges)])

    excl = Counter(r[6] for r in index_rows if r[5] == "exclusive")
    manifest = {
        "note": ("Credit graph of the Pravda network, derived from CheckFirst's per-mirror "
                 "sourcesByDay panels. A credit is the mirror's own claim about where it took "
                 "an item; it is not evidence that the credited channel participated or "
                 "cooperated. See DICTIONARY.md for the top-10 censoring, which makes any "
                 "share-of-credits denominator wrong unless conditioned on the top-10 set."),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mirrors": len(files),
        "rows": {"mirror_day": n_md, "mirror_source_day": n_msd,
                 "source_index": n_src, "source_mirror_edges": n_edge, "mirror_meta": n_meta},
        "sources_total": len(src),
        "sources_exclusive_to_one_mirror": sum(1 for r in index_rows if r[5] == "exclusive"),
        "exclusive_by_mirror": dict(excl.most_common(15)),
        "hungary_exclusive_sources": excl.get("hungary", 0),
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")

    print(f"panel/: {len(files)} mirrors")
    print(f"  mirror_day.csv          {n_md:>8,} rows")
    print(f"  mirror_source_day/*.csv {n_msd:>8,} rows in {len(by_month)} monthly files")
    print(f"  source_index.csv        {n_src:>8,} sources")
    print(f"  source_mirror_edges.csv {n_edge:>8,} edges")
    print(f"  exclusive to one mirror {manifest['sources_exclusive_to_one_mirror']:>8,}"
          f"  (Hungary: {manifest['hungary_exclusive_sources']})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="publish even if it covers fewer mirrors than the current panel")
    raise SystemExit(main(force=ap.parse_args().force))
