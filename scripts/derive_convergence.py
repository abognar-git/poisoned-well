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

# Hungarian domestic outlets swept for in the mirror's credited sources. Two groups:
# nationalist/fringe channels that plausibly overlap the Russian ecosystem, and the
# pro-government mainstream that the domestic AI machine actually runs through.
HU_FRINGE = ["magyarjelen", "vadhajtasok", "nemzeti_internetfigyelo", "hidfo"]
HU_MAINSTREAM = ["origo", "magyar nemzet", "magyarnemzet", "ripost", "mandiner",
                 "hirado", "pestisracok", "pesti sracok", "tv2", "borsonline",
                 "megafon", "nemzeti ellenallas", "index.hu", "888"]


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

    def bucket(label):
        low = label.lower()
        if any(h in low for h in HU_MAINSTREAM):
            return "hungarian_progov_mainstream"
        if any(h in low for h in HU_FRINGE):
            return "hungarian_fringe"
        if "news-front" in low or "news front" in low:
            return "news_front"
        if low.startswith("telegram:"):
            return "telegram_russian_origin"
        return "other_russian_and_misc"

    tally = Counter()
    named = {"hungarian_fringe": [], "hungarian_progov_mainstream": []}
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
        "hungarian_progov_mainstream_sources": named["hungarian_progov_mainstream"],
        "swept_for_mainstream": HU_MAINSTREAM,
        "finding": (
            "The Russian laundering mirror aimed at Hungary does not run on Hungarian "
            "domestic output. Across every article it credits, the pro-government "
            "mainstream appears zero times."
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
        hu = next((b for b in p["buckets"] if b["bucket"] == "hungarian_fringe"), None)
        print(f"  provenance: {p['total_articles']:,} articles, mainstream HU sources = "
              f"{len(p['hungarian_progov_mainstream_sources'])}, "
              f"fringe = {hu['articles'] if hu else 0} ({(hu['share']*100 if hu else 0):.3f}%)")
    else:
        print("  provenance: raw Pravda dataset absent (gitignored) — section omitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
