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
CLAIMS; a fragment that stops appearing still fails, a fragment that appears twice
now fails too, and every correction must still be cited by commit. What --sync
removes is rot, not scrutiny.

What it does NOT do, stated plainly because this docstring used to claim otherwise:
a number typed into the prose that nobody registered is not checked at all. Two
figures drifted for exactly that reason — a second, unregistered copy of a
registered number, which the old first-match-only search never reached.
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


MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")


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
    onset = datetime.date.fromisoformat(TI["estimated_onset"])
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

        # One fragment, not two: "from {} to {} articles a day" also matched the
        # illustrative 7.1 -> 8.9 further down, and --sync runs unattended on an hourly
        # cron. A copy-edit to the real sentence would have sent --sync to the decoy and
        # published a 63.7% collapse labelled +25%, with the gate still printing OK.
        ("fell **{:.1f}%** after the election, from {:.1f} to {:.1f} articles a day",
         [-C["target_change_pct"], TG["baseline_per_day"], TG["after_per_day"]]),
        ("moved **+{:.1f}%** on average", [C["peer_mean_change_pct"]]),
        # negation, not abs(): abs() throws away the sign the verb "fell" asserts, so a
        # series that turned upward would still format as a fall and still pass.
        ("not one fell more than {:.1f}%", [-C["peer_min_change_pct"]]),

        ("**{:,.0f}st**, p = {:.4f}", [PB["raw_rank"], PB["raw_p"]]),
        ("sd {:.1f}% against Romania's {:.1f}%", [PB["volatility_by_mirror"]["hungary"],
                                                  PB["volatility_by_mirror"]["romania"]]),
        ("**−{:.2f} sd, {:,.0f}th**, p = {:.4f}", [abs(PB["treated_z"]),
                                                   PB["volatility_normalised_rank"],
                                                   PB["volatility_normalised_p"]]),
        ("**{:,.0f}th**, p = {:.4f}", [HU["normalised_rank"], HU["normalised_p"]]),
        ("**≈{:.0f} " + MONTHS[onset.month - 1] + " — {:.0f} days late**",
         [onset.day, TI["gap_days_after_election"]]),
        ("**highest single day at {:,.0f} articles**", [TI["day_after_election"]["count"]]),
        ("holds near {:,.0f}/day", [TI["mean_13_to_24_april"]]),

        ("produced −{:.1f}%", [-RO24["change_pct"]]),
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

        # Both of these restate a figure registered above. They went stale under a green
        # gate because rx.search stops at the first match, so the restatement was never
        # reached — 139,376/938 against 139,974/939, and 101.8% against 101.4%.
        ("negative result — {:,.0f} articles, {:,.0f} sources, coverage {:.4f}",
         [P["total_articles"], P["credited_sources"], P["coverage"]]),
        ("collapsed set supplies **{:.1f}%** of the rebound",
         [R["collapsed_set_share_of_rebound"] * 100]),

        ("{:,.0f} registered claims", [cat("claims.json")]),
        ("the {:,.0f} case files", [cat("operations.json")]),
    ]


def cross_file():
    """The census is restated in prose in four other documents, and it drifted in all of
    them at once — 139,376 articles and 938 sources against a derived 139,974 and 939 —
    because this gate read only the README. Same machinery, same uniqueness rule, wider
    reach. Only figures that restate a derived value belong here; a figure stamped with
    an as-of date is a snapshot, not drift, and stays out."""
    import statistics
    P = D("convergence")["provenance_audit"]
    b = {x["bucket"]: x["articles"] for x in P["buckets"]}
    hu = D("pravda_summary")["hungary.news-pravda.com"]
    cats = D("mirror_clock")["categories"]
    cat = {x["category"]: x for x in cats["buckets"]}
    tgt = D("peer_control")["target"]
    rec = D("source_diet")["recovery"]
    live = [c for _, c in D("pravda_timeline")["series"] if c > 0]
    T, S, C = P["total_articles"], P["credited_sources"], P["coverage"]
    acct, fringe = b["hungarian_progov_account"], b["hungarian_fringe"]
    return [
        ("RESEARCH.md",
         "pro-government press across {:,.0f} articles", [T]),
        ("RESEARCH.md",
         "Across all {:,.0f} articles, the {:,.0f} credited sources sum to exactly "
         "{:,.0f} (coverage {:.4f})", [T, S, T, C]),
        ("RESEARCH.md", "Manual pass over all {:,.0f} sources", [S]),
        ("catalog/claims.json",
         "Across all {:,.0f} articles the Hungarian Pravda mirror has published, and all "
         "{:,.0f} sources it credits", [T, S]),
        ("catalog/claims.json",
         "is credited {:,.0f} times ({:.2f}%), and Hungarian nationalist-fringe channels "
         "a further {:,.0f} ({:.2f}%)", [acct, acct / T * 100, fringe, fringe / T * 100]),
        # Three separate bakings on the page. JS overwrites them when the fetch succeeds,
        # so these are what a reader sees when it does not — a stale census is worse there,
        # not better, because nothing signals that it is a fallback.
        ("site/prototype/index.html",
         'id="pipe-total">{:,.0f}</span> articles', [T]),
        ("site/prototype/index.html",
         'The pipeline test · <span class="prov-n">{:,.0f}</span> articles', [T]),
        ("site/prototype/index.html",
         'across its <span class="prov-n">{:,.0f}</span> articles', [T]),

        # The § evidence cards. Nothing read their prose: check_claims verifies that a
        # marker RESOLVES, never that the card it opens agrees with the sentence it is
        # evidence for. Five of them had drifted — one said "recovered to 200/day, 82%"
        # over a paragraph rendering 187/day — on the project's own proof-of-rigour
        # surface. Registered figure by figure rather than by a blanket numeral scan,
        # because claim prose legitimately carries seat counts, external audit figures
        # and dates that have no derived counterpart.
        ("catalog/claims.json",
         "'oroszokazigazsagoldalan' ({:,.0f} articles)", [hu["top_sources"][0]["count"]]),
        ("catalog/claims.json",
         "It has since recovered to {:,.0f}/day, {:.1f}% of its pre-election baseline",
         [tgt["latest_per_day"], tgt["recovery_pct_of_baseline"]]),
        ("catalog/claims.json",
         "100+ articles on {:,.0f} of its {:,.0f} active days (median {:,.0f}/day)",
         [sum(1 for c in live if c >= 100), len(live), statistics.median(live)]),
        ("catalog/claims.json",
         "only {:.1f}% of its {:,.0f} articles are filed under 'hungary' ({:,.0f})",
         [cat["hungary"]["share"] * 100, cats["total"], cat["hungary"]["count"]]),
        ("catalog/claims.json",
         "'world' {:.1f}% ({:,.0f}) and 'russia' {:.1f}% ({:,.0f})",
         [cat["world"]["share"] * 100, cat["world"]["count"],
          cat["russia"]["share"] * 100, cat["russia"]["count"]]),
        # Deliberately stops before "the institutional feeds contributing −0.1": that is
        # a different set from the three collapsed channels, derive_diet.py computes no
        # aggregate for it, and it was independently corroborated. Registering it would
        # fail the gate on a figure that is not drifting.
        ("catalog/claims.json",
         "supply {:.0f}% of the rebound (+{:.1f} of +{:.1f} articles/day",
         [rec["collapsed_set_share_of_rebound"] * 100,
          rec["collapsed_set_rebound_per_day"], rec["rebound_per_day"]]),

        # docs/figures: a published SVG asserted 938 and 939 credited sources in one
        # image, 42 px apart — one literal, one computed. validate.yml's figure check is
        # a regeneration diff, which a hardcoded literal passes forever.
        ("docs/figures/provenance_census_dark.svg",
         "zero — across all {:,.0f} credited sources", [S]),
        ("docs/figures/provenance_census_light.svg",
         "zero — across all {:,.0f} credited sources", [S]),
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
        hits = list(rx.finditer(text))
        if len(hits) > 1:
            errors.append(f"{template!r} matches the README {len(hits)} times. A registered "
                          "fragment must be unique: --sync rewrites the first match and the "
                          "others rot behind a green gate.")
            continue
        if not hits:
            errors.append(f"README no longer contains: {template!r}")
            continue
        m = hits[0]
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

    for rel, template, values in cross_file():
        f = ROOT / rel
        body = f.read_text()
        hits = list(as_regex(template).finditer(body))
        if len(hits) > 1:
            errors.append(f"{rel}: {template!r} matches {len(hits)} times; must be unique")
            continue
        if not hits:
            errors.append(f"{rel} no longer contains: {template!r}")
            continue
        have = re.sub(r"\s+", " ", hits[0].group(0))
        want = re.sub(r"\s+", " ", template.format(*values))
        if have != want:
            if sync:
                f.write_text(body[:hits[0].start()] + template.format(*values) + body[hits[0].end():])
                synced.append(f"{rel}: {have}  ->  {want}")
            else:
                errors.append(f"{rel}: {template!r}\n      file: {have}\n      data: {want}")
        checked += len(values)

    if sync and synced:
        print(f"synced {len(synced)} figure(s) to data/derived/")
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
