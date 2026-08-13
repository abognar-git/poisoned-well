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

    python3 scripts/check_readme.py           # verify
    python3 scripts/check_readme.py --sync     # rewrite the registered figures in place

--sync exists because the data refreshes hourly and these figures move with it: the
census grows as the mirror publishes. Hand-editing the README every hour is not a
plan, and leaving it stale is worse. So the refresh workflow syncs the registered
numbers and commits them with the data.

That does not make the gate ornamental. It only rewrites figures registered in
CLAIMS; a number typed into the prose that nobody registered still fails the check,
a fragment that stops appearing still fails, and every correction must still be
cited by commit. What --sync removes is rot, not scrutiny.
"""
import argparse
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

    # (README template, values). {…} are format specs — the same string both matches
    # the README (with the numbers replaced by a number pattern) and rewrites it under
    # --sync, so a fragment can never orphan its own matcher the way a literal would.
    return [
        ("**{:,.0f} websites**", [len(ns["mirrors"])]),
        ("**{:.1f} million articles**", [sum(m["total"] for m in ns["mirrors"].values()) / 1e6]),
        ("**{:,.0f} comparable windows**", [ns["n_windows"]]),
        ("**{:,.0f} of the {:,.0f} days**", [hu["active_days"], span]),

        ("**{:,.0f} articles**", [P["total_articles"]]),
        ("**{:,.0f} sources**", [P["credited_sources"]]),
        ("{:,.0f} of them, accounting for {:.2f}%", [P["credited_sources"], P["coverage"] * 100]),
        ("credited {:,.0f} times ({:.2f}%)", [bucket["hungarian_progov_account"],
                                              bucket["hungarian_progov_account"] / P["total_articles"] * 100]),
        ("a further {:,.0f} ({:.2f}%)", [bucket["hungarian_fringe"],
                                         bucket["hungarian_fringe"] / P["total_articles"] * 100]),

        ("fell **{:.1f}%**", [abs(C["target_change_pct"])]),
        ("from {:.1f} to {:.1f} articles a day", [TG["baseline_per_day"], TG["after_per_day"]]),
        ("moved **+{:.1f}%** on average", [C["peer_mean_change_pct"]]),
        ("not one fell more than {:.1f}%", [abs(C["peer_min_change_pct"])]),

        ("**{:,.0f}st**, p = {:.4f}", [PB["raw_rank"], PB["raw_p"]]),
        ("sd {:.1f}% against Romania's {:.1f}%", [PB["volatility_by_mirror"]["hungary"],
                                                  PB["volatility_by_mirror"]["romania"]]),
        ("**−{:.2f} sd, {:,.0f}th**, p = {:.4f}", [abs(PB["treated_z"]),
                                                   PB["volatility_normalised_rank"],
                                                   PB["volatility_normalised_p"]]),
        ("**{:,.0f}th**, p = {:.4f}", [HU["normalised_rank"], HU["normalised_p"]]),
        ("**≈{:.0f} April — {:.0f} days late**", [27, TI["gap_days_after_election"]]),
        ("**highest single day at {:,.0f} articles**", [TI["day_after_election"]["count"]]),
        ("holds near {:,.0f}/day", [TI["mean_13_to_24_april"]]),

        ("produced −{:.1f}%", [abs(RO24["change_pct"])]),
        ("**+{:.1f}% rise**", [RO25["change_pct"]]),

        ("supply **{:.1f}%** of the rebound", [R["collapsed_set_share_of_rebound"] * 100]),
        ("everything else nets **−{:.1f} articles/day**",
         [abs(R["rebound_per_day"] - R["collapsed_set_rebound_per_day"])]),
        ("{:.1f}% → {:.1f}% → {:.1f}%", [R["collapsed_set_share_of_output"][k] * 100
                                         for k in ("baseline", "trough", "recovery")]),
        ("Observed overlap **{:,.0f}**", [len(T["shared"])]),
        ("expected by chance **{:.2f}**", [T["chance_baseline"][0]["expected_overlap"]]),
        ("or {:.2f} if you draw", [T["chance_baseline"][1]["expected_overlap"]]),
        ("at {:.1f} articles/day", [peak]),
        ("+{:.1f}% February-to-March rise against a +{:.1f}% peer mean",
         [rise(mon), peer_rise]),

        ("{:,.0f} registered claims", [cat("claims.json")]),
        ("the {:,.0f} case files", [cat("operations.json")]),
    ]


SPEC = re.compile(r"\{[^}]*\}")


def as_regex(template):
    """A template becomes a whitespace-tolerant regex with a number pattern wherever a
    format spec sits, so it matches the README no matter what the current values are."""
    parts = [re.escape(p) for p in SPEC.split(template)]
    rx = r"[\d,]+(?:\.\d+)?".join(parts)
    # re.escape renders a space as an escaped space on older Pythons and bare on newer
    # ones; normalise both to \s+ so a template still matches text wrapped across lines
    return re.compile(re.sub(r"(?:\\ | )+", r"\\s+", rx))


def main(sync: bool = False) -> int:
    text = README.read_text()
    errors, checked, synced = [], 0, []

    for template, values in build():
        rx = as_regex(template)
        m = rx.search(text)
        if not m:
            errors.append(f"README no longer contains: {template!r}")
            continue
        want = template.format(*values)
        have = re.sub(r"\s+", " ", m.group(0))
        if have != re.sub(r"\s+", " ", want):
            if sync:
                text = text[:m.start()] + want + text[m.end():]
                synced.append(f"{have}  ->  {want}")
                checked += len(values)
                continue
            errors.append(f"{template!r}\n      README: {have}\n      data:   {want}")
        else:
            checked += len(values)

    if sync and synced:
        README.write_text(text)
        print(f"README: synced {len(synced)} figures to data/derived/")
        for line in synced:
            print(f"  {line}")

    flat = re.sub(r"\s+", " ", README.read_text())

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
    ap = argparse.ArgumentParser(description="Verify the README against data/derived.")
    ap.add_argument("--sync", action="store_true",
                    help="rewrite registered figures in place instead of failing on them")
    raise SystemExit(main(sync=ap.parse_args().sync))
