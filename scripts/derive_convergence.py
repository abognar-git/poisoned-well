#!/usr/bin/env python3
"""Generate data/derived/convergence.json — the domestic/Russian convergence bench.

The question this answers: how far did Hungary's domestic AI-propaganda machine run
the same playbook as the Russian operations aimed at Hungary — and is there any
evidence the two were actually connected?

Design rules, because this is the most over-claimable measurement on the site:

  * Buckets are READ from each entry's stored `side` field, never inferred here.
    An analyst's bucketing decision belongs in git, not in a heuristic.
  * Contested-sponsorship entries are counted in NEITHER technique bucket.
  * We publish share-of-domestic (|D n R| / |D|), not Jaccard. The editorial question
    is containment — how much of what the domestic machine did also appears in the
    Russian playbook — and with sets this unequal Jaccard cannot approach 1 even under
    perfect containment, so it reads as "low similarity" when it means "unequal sizes".
  * No composite score. No similarity index. A single number would be read as a
    coordination measure, which is exactly what this data cannot support.
  * The provenance audit is the strongest available test of an actual pipeline, and
    it is reported whatever it says. It currently says: no pipeline.

Outputs are all counts and named sets, so the page can render evidence rather than
a verdict.
"""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
RAW = ROOT / "data" / "raw" / "pravda" / "json"
OUT = ROOT / "data" / "derived" / "convergence.json"

MIRROR = "hungary.news-pravda.com"

# Hungarian domestic sources swept for in the mirror's credited sources.
#
# CORRECTION 2026-08-11: an earlier version swept the mainstream list for the string
# "megafon" and so missed `Telegram: deakdaniel` — a prominent pro-government
# commentator's personal channel, credited 76 times — which then fell through to the
# Russian-origin bucket and let the page claim the only Hungarian sources were fringe
# channels. Personal handles do not contain their affiliation, so named pro-government
# accounts are listed explicitly below and the press list is matched separately.
#
# Note on what is NOT here: greatawakeningmagyarok, ebredes2017, InfoDefMagyarok,
# VilagHelyzeteBlog and RusEmbHungary publish in Hungarian but are pro-Kremlin origins
# (InfoDefense franchise, Russian embassy) — this project's own three-tier model already
# classifies them as the Russian origin tier, and they stay there.
HU_FRINGE = ["magyarjelen", "vadhajtasok", "nemzeti_internetfigyelo", "hidfo",
             "magyarbtamas", "magyar325411km2", "matrixhungary", "magyarkultura"]
# named pro-government commentator / campaign accounts, matched on the exact handle
HU_PROGOV_ACCOUNTS = ["deakdaniel"]
# the pro-government press — the outlets the domestic AI machine actually runs through
HU_PROGOV_PRESS = ["origo", "magyar nemzet", "magyarnemzet", "ripost", "mandiner",
                   "hirado", "pestisracok", "pesti sracok", "tv2", "borsonline",
                   "megafon", "nemzeti ellenallas", "index.hu", "888", "mediaworks",
                   "vg.hu", "metropol", "lokal"]


def load(name):
    return json.loads((CATALOG / name).read_text())


def techniques(entry):
    out = set()
    for t in entry.get("disarm_techniques") or []:
        out.add(t["id"] if isinstance(t, dict) else t)
    return out


def technique_overlap(ops, disarm):
    """M1/M2: which techniques the domestic and Russian-attributed sides share.

    Reported as named techniques with document frequency, never as a bare percentage —
    at this n each tagged case moves the share by a double-digit amount.
    """
    dom = [e for e in ops if e.get("side") == "domestic" and techniques(e)]
    rus = [e for e in ops if e.get("side") == "russian-attributed" and techniques(e)]
    excluded = [e["id"] for e in ops if e.get("side") == "contested"]

    dset = set().union(*[techniques(e) for e in dom]) if dom else set()
    rset = set().union(*[techniques(e) for e in rus]) if rus else set()
    shared = sorted(dset & rset)
    tagged = dom + rus

    def name(tid):
        v = disarm.get(tid)
        return (v.get("name") if isinstance(v, dict) else v) or tid

    return {
        "domestic_cases": [e["id"] for e in dom],
        "domestic_n": len(dom),
        "russian_cases": [e["id"] for e in rus],
        "russian_n": len(rus),
        "excluded_contested": excluded,
        "domestic_technique_n": len(dset),
        "russian_union_n": len(rset),
        "shared": [
            {
                "id": t,
                "name": name(t),
                "document_frequency": sum(1 for e in tagged if t in techniques(e)),
                "df_total": len(tagged),
                "used_by": sorted(e["id"] for e in tagged if t in techniques(e)),
            }
            for t in shared
        ],
        "domestic_only": [{"id": t, "name": name(t)} for t in sorted(dset - rset)],
        "share_of_domestic": round(len(shared) / len(dset), 4) if dset else None,
        # how much one tag is worth — the honesty figure that must ship beside the share
        "points_per_technique": round(100 / len(dset), 1) if dset else None,
    }


def provenance_audit():
    """M4: does the Russian mirror aimed at Hungary actually consume domestic output?

    Strongest available test of a real pipeline, on the mirror's own credit labels.
    Returns None if the raw dataset is absent (it is gitignored).
    """
    f = RAW / f"{MIRROR}_viz.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    total = d["totalArticles"]
    srcs = d.get("topSources") or []

    def cnt(s):
        return s.get("count") or s.get("value") or s.get("articles") or 0

    def nm(s):
        return (s.get("name") or s.get("source") or s.get("label") or "")

    def handle(label):
        """'Telegram: deakdaniel' -> 'deakdaniel'; otherwise the bare label."""
        return label.split(":", 1)[-1].strip().lower()

    def bucket(label):
        low, h = label.lower(), handle(label)
        # named domestic accounts first: a personal handle carries no affiliation
        # string, so substring-matching an outlet list can never catch them
        if h in HU_PROGOV_ACCOUNTS:
            return "hungarian_progov_account"
        if any(x in low for x in HU_PROGOV_PRESS):
            return "hungarian_progov_press"
        if any(x in low for x in HU_FRINGE):
            return "hungarian_fringe"
        if "news-front" in low or "news front" in low:
            return "news_front"
        if low.startswith("telegram:"):
            return "telegram_russian_origin"
        return "other_russian_and_misc"

    tally = Counter()
    named = {"hungarian_fringe": [], "hungarian_progov_press": [], "hungarian_progov_account": []}
    for s in srcs:
        b = bucket(nm(s))
        tally[b] += cnt(s)
        if b in named:
            named[b].append({"source": nm(s), "articles": cnt(s)})

    counted = sum(tally.values())
    return {
        "mirror": MIRROR,
        "total_articles": total,
        "credited_sources": len(srcs),
        "coverage": round(counted / total, 4),
        "buckets": [
            {"bucket": k, "articles": v, "share": round(v / total, 6)}
            for k, v in sorted(tally.items(), key=lambda kv: -kv[1])
        ],
        "hungarian_fringe_sources": sorted(named["hungarian_fringe"],
                                           key=lambda x: -x["articles"]),
        "hungarian_progov_press_sources": named["hungarian_progov_press"],
        "hungarian_progov_account_sources": sorted(named["hungarian_progov_account"],
                                                   key=lambda x: -x["articles"]),
        "swept_for_press": HU_PROGOV_PRESS,
        "named_progov_accounts": HU_PROGOV_ACCOUNTS,
        "finding": (
            "The Russian laundering mirror aimed at Hungary does not run on the Hungarian "
            "pro-government press: across every article it credits, those outlets appear "
            "zero times. It is not a clean zero, though — one prominent pro-government "
            "commentator's personal Telegram channel is credited 76 times (0.05%), and "
            "Hungarian nationalist-fringe channels a further 130. The domestic machine is "
            "not this mirror's raw material; a thin thread does exist."
        ),
    }


def ai_modality(ai_incidents):
    """M6: which AI modalities each side is documented using. Counts only."""
    tally = {}
    for i in ai_incidents:
        side = i.get("side") or ("domestic" if "domestic" in json.dumps(i).lower()[:400] else "unspecified")
        tally.setdefault(side, Counter())[i.get("ai_type", "unknown")] += 1
    return {k: dict(v) for k, v in tally.items()}


def main() -> int:
    ops = load("operations.json")
    disarm = load("disarm_techniques.json")
    ai_inc = load("ai_incidents.json")

    out = {
        "note": ("Generated by scripts/derive_convergence.py. Convergence of technique is "
                 "not evidence of coordination. Every figure here is a count over a named, "
                 "sourced catalog; none is a similarity score."),
        "sides": dict(Counter(e.get("side", "unset") for e in ops)),
        "technique_overlap": technique_overlap(ops, disarm),
        "provenance_audit": provenance_audit(),
        "ai_modality": ai_modality(ai_inc),
        "not_computable": [
            {"question": "Did a frame appear on one side before the other?",
             "why_not": ("Our corpus is one-sided and undated at frame level: we capture the "
                         "Russian mirror live but hold no comparable timestamped corpus of "
                         "domestic output, so sequence — and therefore direction — cannot be "
                         "established.")},
            {"question": "How often do the same narrative frames co-occur across both sides?",
             "why_not": ("Same reason: co-occurrence needs two comparable corpora sampled the "
                         "same way. Coding one side and eyeballing the other would manufacture "
                         "a number, not measure one.")},
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    t = out["technique_overlap"]
    p = out["provenance_audit"]
    print(f"convergence.json: {t['domestic_n']} domestic vs {t['russian_n']} russian tagged cases; "
          f"{len(t['shared'])} shared techniques of {t['domestic_technique_n']} domestic "
          f"({t['share_of_domestic']}), {len(t['excluded_contested'])} contested excluded")
    if p:
        def b(k): return next((x for x in p["buckets"] if x["bucket"] == k), None)
        fr, ac = b("hungarian_fringe"), b("hungarian_progov_account")
        print(f"  provenance: {p['total_articles']:,} articles | progov PRESS = "
              f"{len(p['hungarian_progov_press_sources'])} sources | progov ACCOUNT = "
              f"{ac['articles'] if ac else 0} ({(ac['share']*100 if ac else 0):.3f}%) | "
              f"fringe = {fr['articles'] if fr else 0} ({(fr['share']*100 if fr else 0):.3f}%)")
    else:
        print("  provenance: raw Pravda dataset absent (gitignored) — section omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
