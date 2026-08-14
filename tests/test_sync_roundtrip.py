#!/usr/bin/env python3
"""--sync must always be able to re-match what it just wrote.

scripts/check_readme.py has two jobs that pull against each other. It rewrites registered
figures from the derived data, and it fails if a registered fragment stops appearing. If a
value it writes cannot be matched by the pattern it writes with, the two jobs deadlock: the
rewrite lands, the next match fails, and main() takes the `not hits` branch — which errors
even under --sync. Nothing can then repair it but a hand edit.

That is not hypothetical and it is not one bug. It has happened twice:

    1. NUM accepted a leading minus and as_regex did not, so a sign flip wrote
       "moved **+-1.6%** on average" and then failed forever.
    2. The recovery window's end date was concatenated into the template as a literal,
       which re.escape froze into the matcher — while the date itself advances every
       calendar day by construction. The first rollover wedged the hourly job at the
       sync step, before the commit step, discarding that hour's specimen capture.

Both were found after shipping. This test is the general form: perturb the data behind
every registered template, sync, and assert the gate can still read its own output.

    python3 tests/test_sync_roundtrip.py
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COPY_DIRS = ("scripts", "catalog", "data", "docs", "site", "tests")
COPY_FILES = ("README.md", "RESEARCH.md")


def sandbox(td):
    """A full working copy — check_readme reads six files and writes to all of them."""
    for d in COPY_DIRS:
        shutil.copytree(ROOT / d, td / d, symlinks=True,
                        ignore=shutil.ignore_patterns("raw", "__pycache__"))
    for f in COPY_FILES:
        shutil.copy(ROOT / f, td / f)
    return td


def run(td, *args):
    r = subprocess.run([sys.executable, str(td / "scripts" / "check_readme.py"), *args],
                       capture_output=True, text=True, cwd=td)
    return r.returncode, r.stdout + r.stderr


def perturb(td, path, mutate):
    p = td / path
    d = json.loads(p.read_text())
    mutate(d)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))


CASES = [
    # The two failures that actually shipped, plus the shapes adjacent to them.
    ("a sign flip on the peer mean",
     "data/derived/peer_control.json",
     lambda d: d["comparison"].__setitem__("peer_mean_change_pct", -1.6)),
    ("the recovery window advancing a day",
     "data/derived/peer_control.json",
     lambda d: d["target"].__setitem__("recovery_window",
                                       [d["target"]["recovery_window"][0], "2026-09-30"])),
    ("a recovery rate that gains a digit",
     "data/derived/peer_control.json",
     lambda d: d["target"].__setitem__("latest_per_day", 1042.5)),
    ("a census that loses a thousands separator",
     "data/derived/convergence.json",
     lambda d: d["provenance_audit"].__setitem__("total_articles", 999)),
    ("a zero where a positive number was",
     "data/derived/source_diet.json",
     lambda d: d["recovery"].__setitem__("collapsed_set_rebound_per_day", 0.0)),
]


def main() -> int:
    results = []
    for name, path, mutate in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            td = sandbox(Path(tmp))
            perturb(td, path, mutate)
            rc_sync, out_sync = run(td, "--sync")
            rc_check, out_check = run(td)
            ok = rc_sync == 0 and rc_check == 0
            results.append(ok)
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            if not ok:
                tail = [l for l in (out_sync + out_check).splitlines()
                        if "no longer contains" in l or "FAIL" in l or "matches the" in l]
                for l in tail[:4]:
                    print(f"           {l.strip()}")

    print(f"sync round-trip: {sum(results)} of {len(results)} — "
          f"{'OK' if all(results) else 'FAIL'}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
