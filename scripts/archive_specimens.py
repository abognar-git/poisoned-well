#!/usr/bin/env python3
"""Accumulate every captured item into an append-only archive.

capture_specimens.py writes a snapshot of what is on the front pages right now, and
the next run overwrites it. That is correct for the live panel and wrong for everything
else: an hourly record of what this network published, kept over months, is the one
thing here that nobody else has. CheckFirst publishes counts; this publishes what the
headlines actually said.

So each capture is merged into month-sharded JSONL under data/archive/:

    data/archive/2026-08.jsonl     one JSON object per line, append-only
    data/archive/index.json        counts, date range and per-source totals

JSONL because a research dataset should be streamable, greppable and diffable without
a parser, and because appending must never rewrite what is already there.

Identity is most-stable-first: the publisher's own `id` where there is one, then `url`,
then `(date, title)`. The title is the last resort because it is the one field a repair
can change — re-truncating an excerpt once forked a single item into two. First-seen wins:
an archived item is not rewritten, and `first_seen` records when we observed it, which is
not when it was published.

    python3 scripts/archive_specimens.py                 # merge the current capture
    python3 scripts/archive_specimens.py --backfill-git  # recover snapshots from git history
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LATEST = ROOT / "data" / "derived" / "latest_specimens.json"
# Prefer the uncapped harvest. Merging from the capped file discarded roughly two thirds
# of every run before it reached the archive; LATEST stays the fallback for git backfill,
# where only the capped file exists.
FULL = ROOT / "data" / "derived" / "last_harvest.json"
ARCHIVE = ROOT / "data" / "archive"
FIELDS = ("site", "tier", "date", "published_at", "title", "theme", "lang", "unit",
          "category", "source", "url", "id", "date_is_capture", "first_seen")


def key(row):
    """Identity, most stable first. `id` is the publisher's own post/article number where
    one exists and is the only field a repair cannot change; falling straight to the title
    means any edit to the text — a re-truncation, a relabel — silently forks one item into
    two. That happened."""
    if row.get("id") not in (None, ""):
        return (row.get("site"), "id", str(row["id"]))
    if row.get("url"):
        return (row.get("site"), "url", row["url"])
    return (row.get("site"), "dt", row.get("date"), row.get("title"))


def load_archive():
    """Deduplicate on load, keeping the earliest sighting. Repairs change fields, and two
    rows that were distinct before an edit can become the same item after it — writing the
    shards back without collapsing them leaves the duplicate in the published file."""
    seen, shards, dropped = {}, {}, 0
    for f in sorted(ARCHIVE.glob("*.jsonl")):
        kept = []
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            k = key(r)
            if k in seen:
                dropped += 1
                if r.get("first_seen", "") < seen[k].get("first_seen", "9"):
                    seen[k].update({"first_seen": r["first_seen"]})
                continue
            seen[k] = r
            kept.append(r)
        shards[f.stem] = kept
    if dropped:
        print(f"  collapsed {dropped} duplicate row(s) on load")
    return seen, shards


def normalise(row, tiers, captured_at):
    out = {k: row.get(k) for k in FIELDS if row.get(k) is not None}
    out["tier"] = tiers.get(row.get("site"))
    out["first_seen"] = captured_at
    return {k: v for k, v in out.items() if v is not None}


def merge(snapshot, seen):
    """Return rows in the snapshot not already archived."""
    tiers = {sid: s.get("tier") for sid, s in (snapshot.get("sources") or {}).items()}
    captured = snapshot.get("captured_at", "")
    fresh = []
    for row in ((snapshot.get("items") or [])
                or (snapshot.get("featured") or []) + (snapshot.get("corpus") or [])):
        if not row.get("title"):
            continue
        r = normalise(row, tiers, captured)
        k = key(r)
        if k in seen:
            continue
        seen[k] = r
        fresh.append(r)
    return fresh


def write(shards):
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for month, rows in shards.items():
        rows.sort(key=lambda r: (r.get("date", ""), r.get("site", ""), r.get("title", "")))
        (ARCHIVE / f"{month}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))


def reindex(shards):
    rows = [r for v in shards.values() for r in v]
    if not rows:
        return
    dates = sorted(r["date"] for r in rows if r.get("date"))
    idx = {
        "note": ("Append-only archive of every item captured by scripts/capture_specimens.py. "
                 "Headlines and provenance only — no article body text is collected. Items are "
                 "never rewritten once archived; `first_seen` is when this project observed the "
                 "item, which is not necessarily when it was published."),
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "items": len(rows),
        # Publication dates, which reach back further than this project does: a front page
        # links to its own archive, so Zvezda alone contributes items from 2022. The
        # observation window is what says how long we have been collecting, and conflating
        # the two would present a two-week corpus as a four-year one.
        "first_date": dates[0], "last_date": dates[-1],
        "published_range": [dates[0], dates[-1]],
        "observed_range": [min(seen), max(seen)] if (seen := [r["first_seen"][:10]
                            for r in rows if r.get("first_seen")]) else None,
        "months": {m: len(v) for m, v in sorted(shards.items())},
        "by_source": dict(Counter(r["site"] for r in rows).most_common()),
        "by_tier": dict(Counter(r.get("tier") or "unknown" for r in rows).most_common()),
        "by_theme": dict(Counter(r.get("theme") or "unknown" for r in rows).most_common()),
        "by_lang": dict(Counter(r.get("lang") or "unknown" for r in rows).most_common()),
        "by_unit": dict(Counter(r.get("unit") or "unknown" for r in rows).most_common()),
        # The one table a reader needs before trusting any theme count: the lexicon has a
        # language scope, and this says where it reaches. Grey cells are not zero topics —
        # they are no terms.
        "theme_coverage": {
            lang: {
                "items": sum(1 for r in rows if r.get("lang") == lang),
                "scored": sum(1 for r in rows if r.get("lang") == lang and r.get("theme") != "unscored"),
                "matched_a_topic": sum(1 for r in rows if r.get("lang") == lang
                                       and r.get("theme") not in ("filler", "unscored")),
                "lexicon": "cyr" if lang == "cyr" else "lat",
            }
            for lang in sorted({r.get("lang") for r in rows if r.get("lang")})
        },
    }
    (ARCHIVE / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1) + "\n")
    return idx


def backfill_git(seen, shards):
    """Recover snapshots the archive predates. Every overwrite is still in git."""
    log = subprocess.run(["git", "log", "--format=%H", "--", str(LATEST.relative_to(ROOT))],
                         capture_output=True, text=True, cwd=ROOT).stdout.split()
    recovered = 0
    for sha in reversed(log):                       # oldest first, so first_seen is earliest
        blob = subprocess.run(["git", "show", f"{sha}:{LATEST.relative_to(ROOT)}"],
                              capture_output=True, text=True, cwd=ROOT).stdout
        if not blob.strip():
            continue
        try:
            snap = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for r in merge(snap, seen):
            shards.setdefault(r.get("date", "unknown")[:7], []).append(r)
            recovered += 1
    print(f"  backfill: recovered {recovered} items from {len(log)} git revisions")
    return recovered


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backfill-git", action="store_true",
                    help="also recover every snapshot still in git history")
    a = ap.parse_args()

    seen, shards = load_archive()
    before = len(seen)

    if a.backfill_git:
        backfill_git(seen, shards)

    src_file = FULL if FULL.exists() else LATEST
    if src_file.exists():
        snap = json.loads(src_file.read_text())
        for r in merge(snap, seen):
            shards.setdefault(r.get("date", "unknown")[:7], []).append(r)

    # The index is derived from the shards, not from what this run added — a repair or a
    # schema change touches the rows without adding any, and a short-circuit here left
    # index.json describing an archive that no longer existed.
    write(shards)
    idx = reindex(shards)
    if len(seen) == before and not a.backfill_git:
        print(f"archive: no new items ({before}); index rebuilt from {len(shards)} shard(s)")
        return 0
    print(f"archive: {idx['items']} items ({idx['items'] - before:+d}), "
          f"{idx['first_date']} to {idx['last_date']}, {len(idx['months'])} month shard(s)")
    for m, n in idx["months"].items():
        print(f"  {m}.jsonl  {n:>6} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
