#!/usr/bin/env python3
"""Verify the README's numbers against the data it describes.

A figure quoted in prose is correct on the day it is typed and wrong after the
next re-derive, and nothing complains. That gap is where a document like this
rots — and this project already shipped four claims that were sourced, gated and
false, so an unchecked number in the most-read file in the repository is not a
risk it can carry.

Each entry in CLAIMS is a fragment copied **verbatim from the README** together
with the value(s) recomputed from data/derived/ right now. The script pulls the
numeric literals out of the fragment and compares those to the recomputed values,
so the README's own text is what is being checked — not a second copy of the
number kept in this file, which would rot in exactly the same way.

    python3 scripts/check_readme.py
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DER = ROOT / "data" / "derived"

D = lambda name: json.loads((DER / f"{name}.json").read_text())
NUM = re.compile(r"-?−?\d[\d,]*(?:\.\d+)?")


def nums(fragment):
    """Every numeric literal in a README fragment, as floats. Handles thousands
    separators and the typographic minus the page uses."""
    out = []
    for m in NUM.findall(fragment):
        out.append(float(m.replace(",", "").replace("−", "-")))
    return out


def build():
    pc, cv, ns = D("peer_control"), D("convergence"), D("network_scan")
    dt, ps = D("source_diet"), D("pravda_summary")
    hu = ps["hungary.news-pravda.com"]
    P, T = cv["provenance_audit"], cv["technique_overlap"]
    C, PB, TI, TG = pc["comparison"], pc["placebo"], pc["timing"], pc["target"]
    R = dt["recovery"]
    ev = {e["id"]: e["result"] for e in ns["events"]["tested"]}
    HU, RO24, RO25 = (ev["hu-2026-parliamentary"], ev["ro-2024-presidential-annulled"],
                      ev["ro-2025-presidential-rerun"])
    span = (datetime.date.fromisoformat(hu["last_day"]) -
            datetime.date.fromisoformat(hu["first_day"])).days + 1
    mon = TG["monthly"]
    peak = max(mon.values())
    rise = lambda m: (m["2026-03"] - m["2026-02"]) / m["2026-02"] * 100
    peer_rise = sum(rise(q["monthly"]) for q in pc["peers"]) / len(pc["peers"])
    bucket = {b["bucket"]: b["articles"] for b in P["buckets"]}
    cat = lambda f: len(json.loads((ROOT / "catalog" / f).read_text()))

    # (verbatim README fragment, values it must equal, in order of appearance)
    return [
        ("**101 websites**", [len(ns["mirrors"])]),
        ("**17.7 million articles**", [round(sum(m["total"] for m in ns["mirrors"].values()) / 1e6, 1)]),
        ("**1,948 comparable windows**", [ns["n_windows"]]),
        ("**869 of the 872 days**", [hu["active_days"], span]),

        ("**139,376 articles**", [P["total_articles"]]),
        ("**938 sources**", [P["credited_sources"]]),
        ("938 of them, accounting for 100.00%", [P["credited_sources"], round(P["coverage"] * 100, 2)]),
        ("credited 76 times (0.05%)", [bucket["hungarian_progov_account"], 0.05]),
        ("a further 130 (0.09%)", [bucket["hungarian_fringe"], 0.09]),

        ("fell **63.7%**", [abs(C["target_change_pct"])]),
        ("from 243.6 to 88.5 articles a day", [TG["baseline_per_day"], TG["after_per_day"]]),
        ("moved **+1.6%** on average", [C["peer_mean_change_pct"]]),
        ("not one fell more than 16.3%", [abs(C["peer_min_change_pct"])]),

        ("**1st**, p = 0.0054", [PB["raw_rank"], PB["raw_p"]]),
        ("sd 58.8% against Romania's 13.2%", [PB["volatility_by_mirror"]["hungary"],
                                              PB["volatility_by_mirror"]["romania"]]),
        ("**−1.08 sd, 13th**, p = 0.0703", [PB["treated_z"], PB["volatility_normalised_rank"],
                                            PB["volatility_normalised_p"]]),
        ("**207th**, p = 0.1063", [HU["normalised_rank"], HU["normalised_p"]]),
        ("**≈27 April — 15 days late**", [27, TI["gap_days_after_election"]]),
        ("**highest single day at 356 articles**", [TI["day_after_election"]["count"]]),
        ("holds near 223/day", [TI["mean_13_to_24_april"]]),

        ("produced −5.6%", [RO24["change_pct"]]),
        ("**+16.5% rise**", [RO25["change_pct"]]),

        ("supply **101.8%** of the rebound", [round(R["collapsed_set_share_of_rebound"] * 100, 1)]),
        ("everything else nets **−1.3 articles/day**",
         [round(R["rebound_per_day"] - R["collapsed_set_rebound_per_day"], 1)]),
        ("67.5% → 32.6% → 62.6%", [round(R["collapsed_set_share_of_output"][k] * 100, 1)
                                   for k in ("baseline", "trough", "recovery")]),
        ("Observed overlap **4**", [len(T["shared"])]),
        ("expected by chance **5.00**", [T["chance_baseline"][0]["expected_overlap"]]),
        ("or 6.25 if you draw", [T["chance_baseline"][1]["expected_overlap"]]),
        ("at 269.6 articles/day", [peak]),
        ("+24.0% February-to-March rise against a +12.4% peer mean",
         [round(rise(mon), 1), round(peer_rise, 1)]),

        ("32 registered claims", [cat("claims.json")]),
        ("the 24 case files", [cat("operations.json")]),
    ]


def main() -> int:
    flat = re.sub(r"\s+", " ", README.read_text())
    errors, checked = [], 0

    for fragment, expected in build():
        probe = re.sub(r"\s+", " ", fragment)
        if probe not in flat:
            errors.append(f"README no longer contains: {probe!r}")
            continue
        got = nums(probe)
        want = [float(v) for v in expected]
        if got != want:
            errors.append(f"{probe!r}\n      README says {got}, data says {want}")
        else:
            checked += len(want)

    # the smear-fixture count quoted in the README must match the fixture file
    fx = (ROOT / "tests" / "test_smear.py").read_text()
    m = re.search(r"runs (\d+) fixtures", flat)
    if m:
        total = sum(len(re.findall(r'^\s+[fru]?["\']', block, re.M))
                    for block in re.findall(r"(?:MUST_BLOCK|MUST_PASS)\s*=\s*\[(.*?)\n\]", fx, re.S))
        if total and total != int(m.group(1)):
            errors.append(f"README says {m.group(1)} smear fixtures, tests/test_smear.py has {total}")
        elif total:
            checked += 1

    # every correction in the research record must be cited by commit in the README
    for e in D("research")["entries"]:
        if e["kind"] == "correction" and e["commit"] not in flat:
            errors.append(f"correction {e['id']}, fixed in {e['commit']}, is not cited in the README")

    print(f"README: {checked} figures re-checked against data/derived/")
    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
