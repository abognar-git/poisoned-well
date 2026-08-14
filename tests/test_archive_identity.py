#!/usr/bin/env python3
"""The archive is append-only, and the thing append-only stores cannot survive is an
identity that changes shape underneath them.

scripts/archive_specimens.py keys a row most-stable-first: the publisher's own `id`,
else `url`, else `(date, title)`. That ladder is right, and it has one failure mode
that is invisible to the dedupe it feeds: when a source starts exposing an id or a url
it did not expose before, the same item comes back on a HIGHER rung than the row
already holding it. The two keys cannot collide, so nothing notices, and one item is
filed twice — permanently, in a store that never rewrites.

It happened twice and published 218 duplicate rows out of 1,163, inflating every count
in index.json by 19% and showing affected specimens twice in the browsable corpus.

These fixtures are the two halves of the repair:

    collapse_forks()  finds pairs already on disk and merges them
    merge()           upgrades a bare row in place instead of appending a second one

and the third case, which is the one a careless fix breaks: two rows that share
(site, date, title) but carry genuinely DIFFERENT ids are different items — a source
can and does publish the same headline twice — and must be left alone.

    python3 tests/test_archive_identity.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def run_case(name, archived, incoming, expect_rows, expect_check):
    """Drive the real script over a throwaway archive directory."""
    import archive_specimens as A

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "2026-08.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in archived))
        A.ARCHIVE = td
        seen, shards = A.load_archive()
        if incoming:
            snap = {"captured_at": "2026-08-20T00:00:00+00:00",
                    "sources": {"s": {"tier": "origin"}}, "items": incoming}
            for r in A.merge(snap, seen):
                shards.setdefault(r.get("date", "unknown")[:7], []).append(r)
        rows = [r for v in shards.values() for r in v]

        ok = len(rows) == expect_rows and expect_check(rows)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {len(rows)} row(s), expected {expect_rows}")
        if not ok:
            for r in rows:
                print(f"          {json.dumps(r, sort_keys=True)}")
        return ok


BARE = {"site": "s", "date": "2026-08-01", "title": "A headline",
        "first_seen": "2026-08-01T00:00:00+00:00", "theme": "filler"}
RICH = {"site": "s", "date": "2026-08-01", "title": "A headline", "id": "1001",
        "url": "https://example.invalid/1001", "theme": "hungary"}


def main() -> int:
    print("archive identity — the fork the key() ladder cannot see")
    results = [
        # A row archived before its source exposed an id, meeting the same item after.
        # One row out, carrying the id, the LATER theme, and the EARLIER first_seen.
        run_case("bare row upgraded in place by an incoming id",
                 [BARE], [RICH], 1,
                 lambda rows: (rows[0].get("id") == "1001"
                               and rows[0]["first_seen"] == BARE["first_seen"]
                               and rows[0]["theme"] == "hungary")),

        # Both already on disk from before the repair: collapse on load.
        run_case("fork already on disk collapses on load",
                 [BARE, {**RICH, "first_seen": "2026-08-05T00:00:00+00:00"}], [], 1,
                 lambda rows: (rows[0].get("id") == "1001"
                               and rows[0]["first_seen"] == BARE["first_seen"])),

        # The case a naive alias-union breaks: same headline, same day, different ids.
        # A source republishing a headline is not a duplicate. Both must survive.
        run_case("same (site,date,title) with different ids is NOT a fork",
                 [{**RICH, "id": "1001", "url": "https://example.invalid/1001",
                   "first_seen": "2026-08-01T00:00:00+00:00"},
                  {**RICH, "id": "2002", "url": "https://example.invalid/2002",
                   "first_seen": "2026-08-02T00:00:00+00:00"}], [], 2,
                 lambda rows: {r["id"] for r in rows} == {"1001", "2002"}),

        # An unchanged item arriving again is still just a no-op.
        run_case("re-seeing an identical row adds nothing",
                 [{**RICH, "first_seen": "2026-08-01T00:00:00+00:00"}], [RICH], 1,
                 lambda rows: rows[0]["first_seen"] == "2026-08-01T00:00:00+00:00"),
    ]
    print(f"archive identity: {sum(results)} of {len(results)} — "
          f"{'OK' if all(results) else 'FAIL'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
