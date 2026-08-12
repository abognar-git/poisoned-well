#!/usr/bin/env python3
"""Generate data/derived/source_diet.json — what the mirror stopped eating, and what it ate instead.

The peer control (scripts/derive_peer_control.py) establishes that the Hungarian mirror's
output collapsed after the election it was aimed at, uniquely among seven sibling mirrors.
This script asks what the collapse was made of.

The first answer is a warning about shares. Read as percentages, the post-election period
looks like a reshuffle — News Front and InfoDefense roughly double their share of the
mirror's diet. In absolute terms they did nothing of the kind: they held steady or grew
slightly while three Hungarian-language aggregator channels fell by 80-88%. The share
moved because the denominator collapsed underneath them. So we compute per-day rates and
report shares only alongside them.

The second answer needs two independent sources, which this project happens to have:

  * CheckFirst's aggregate data says the mirror stopped crediting three channels.
  * Our own live capture (scripts/capture_specimens.py) scrapes those same channels
    directly, and finds them still publishing.

Supply did not dry up. The mirror changed what it eats. That is a claim neither dataset
could support on its own.

Honest limits, all shipped with the output:
  * sourcesByDay carries the top 10 sources only — 80% of articles in the baseline window
    and 70% after, so the tail is invisible and the attribution is of the visible portion.
  * Our live capture is a snapshot of today, and it harvests only the mirror's ENGLISH
    surface (see SOURCES["pravda-hu"]["listings"] in capture_specimens.py), while CheckFirst
    counts every language version - the mirror publishes more in Hungarian (98,110) than in
    English (80,259). So the capture CANNOT be compared with the census to say what the
    mirror consumes; on the capture days the census shows it crediting these channels in
    60-77% of that day's articles. All the capture supports is that the channels were
    observably still publishing.
  * The cross-check is keyed to COLLAPSED_SITE_IDS, never to "the busiest channels" —
    see the note on that constant.
  * The count of mirror articles in a single capture is small (tens), so what the mirror
    currently credits is indicative, not a measured distribution.
"""

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pravda" / "json" / "hungary.news-pravda.com_viz.json"
SPECIMENS = ROOT / "data" / "derived" / "latest_specimens.json"
OUT = ROOT / "data" / "derived" / "source_diet.json"

BASELINE = ("2026-02-01", "2026-03-31")
AFTER = ("2026-05-01", "2026-06-30")
RECOVERY = ("2026-07-01", "2026-08-10")

# the three Hungarian-language aggregator channels that carried the mirror before the vote
COLLAPSED = ["Telegram: oroszokazigazsagoldalan",
             "Telegram: ebredes2017",
             "Telegram: greatawakeningmagyarok"]

# the same three channels as our own capture names them. The cross-check MUST be keyed
# to this set: an earlier version summed the three most-captured origin channels, which
# were Baltnews, Lomovka and Zvezda — the feeds that never went quiet — and so "proved"
# the abandoned channels were alive using the output of channels that never stopped.
COLLAPSED_SITE_IDS = {"tg-oroszigazsag", "tg-ebredes", "tg-greatawaken"}


def main() -> int:
    d = json.loads(RAW.read_text())
    names = d["topSourceNames"]
    rows = d["sourcesByDay"]
    daily = {x["date"]: x["count"] for x in d["articlesPerDay"]}

    def window(a, b):
        per = {n: [] for n in names}
        tot = []
        for r in rows:
            if a <= r["date"] <= b:
                for n in names:
                    per[n].append(r.get(n, 0))
                tot.append(daily.get(r["date"], 0))
        return ({n: statistics.mean(v) for n, v in per.items()},
                statistics.mean(tot), len(tot))

    base, base_tot, base_days = window(*BASELINE)
    post, post_tot, post_days = window(*AFTER)
    rec, rec_tot, rec_days = window(*RECOVERY)

    decline = base_tot - post_tot
    collapsed_decline = sum(base[n] - post[n] for n in COLLAPSED)

    sources = []
    for n in names:
        if base[n] == 0 and post[n] == 0:
            continue
        sources.append({
            "source": n,
            "baseline_per_day": round(base[n], 1),
            "after_per_day": round(post[n], 1),
            "change_pct": round((post[n] - base[n]) / base[n] * 100) if base[n] else None,
            "baseline_share": round(base[n] / base_tot * 100, 1),
            "after_share": round(post[n] / post_tot * 100, 1),
            "in_collapsed_set": n in COLLAPSED,
        })
    for entry in sources:
        entry["recovery_per_day"] = round(rec[entry["source"]], 1)
    sources.sort(key=lambda s: -s["baseline_per_day"])

    # Who carried the rebound? An earlier version of this script never asked, and asserted
    # that the Russian-institutional feeds carried it. They did not: the same three channels
    # that collapsed supply essentially all of it, and the institutional feeds are flat
    # across all three windows. The claim was live on the site before it was checked.
    coll_b = sum(base[n] for n in COLLAPSED)
    coll_a = sum(post[n] for n in COLLAPSED)
    coll_r = sum(rec[n] for n in COLLAPSED)
    rebound = rec_tot - post_tot
    recovery = {
        "window": list(RECOVERY),
        "days": rec_days,
        "per_day": round(rec_tot, 1),
        "pct_of_baseline": round(rec_tot / base_tot * 100, 1),
        "rebound_per_day": round(rebound, 1),
        "collapsed_set_rebound_per_day": round(coll_r - coll_a, 1),
        "collapsed_set_share_of_rebound": round((coll_r - coll_a) / rebound, 3) if rebound else None,
        "collapsed_set_share_of_output": {
            "baseline": round(coll_b / base_tot, 3),
            "trough": round(coll_a / post_tot, 3),
            "recovery": round(coll_r / rec_tot, 3),
        },
        "reading": ("The three channels did not stay gone. They supply essentially all of the "
                    "rebound, and the mirror's source composition returns to within a few points "
                    "of its pre-election mix. This was an interruption in the Hungarian-language "
                    "supply, not a change of diet."),
    }

    # independent cross-check against our own scraping of the same channels
    live = None
    if SPECIMENS.exists():
        sp = json.loads(SPECIMENS.read_text())
        items = sp.get("featured", []) + sp.get("corpus", [])
        by_site = Counter(x["site"] for x in items)
        origins = [{"site": k, "label": v.get("label", ""), "captured_now": by_site.get(k, 0)}
                   for k, v in sp.get("sources", {}).items() if v.get("tier") == "origin"]
        mirror_items = [x for x in items if x.get("site") == "pravda-hu"]
        credits = Counter()
        for r in mirror_items:
            s = r.get("source") or {}
            if s.get("channel"):
                credits[s["channel"]] += 1
        live = {
            "captured_at": sp.get("captured_at"),
            "origin_channels_we_scrape": sorted(origins, key=lambda x: -x["captured_now"]),
            "collapsed_set_site_ids": sorted(COLLAPSED_SITE_IDS),
            "collapsed_set_captured_now": sum(o["captured_now"] for o in origins
                                              if o["site"] in COLLAPSED_SITE_IDS),
            "collapsed_set_tracked": sorted(o["site"] for o in origins
                                            if o["site"] in COLLAPSED_SITE_IDS),
            "mirror_articles_in_snapshot": len(mirror_items),
            "mirror_currently_credits": [{"channel": c, "n": n} for c, n in credits.most_common()],
            "collapsed_set_credited_now": sum(
                n for c, n in credits.items()
                if any(c.lower() in x.lower() for x in COLLAPSED)),
        }

    out = {
        "note": ("Generated by scripts/derive_diet.py. Per-day rates first, shares second — the "
                 "post-election share shift is mostly a collapsing denominator, not sources "
                 "growing."),
        "windows": {"baseline": list(BASELINE), "after": list(AFTER),
                    "baseline_days": base_days, "after_days": post_days},
        "totals": {"baseline_per_day": round(base_tot, 1), "after_per_day": round(post_tot, 1),
                   "decline_per_day": round(decline, 1),
                   "top10_coverage_baseline": round(sum(base.values()) / base_tot, 3),
                   "top10_coverage_after": round(sum(post.values()) / post_tot, 3)},
        "sources": sources,
        "attribution": {
            "collapsed_set": COLLAPSED,
            "collapsed_decline_per_day": round(collapsed_decline, 1),
            "share_of_total_decline": round(collapsed_decline / decline, 3) if decline else None,
            "reading": ("Three Hungarian-language aggregator channels account for the great "
                        "majority of the entire decline. The Russian-institutional feeds — News "
                        "Front, InfoDefense, the war-blog channels — held steady or grew.")},
        "recovery": recovery,
        "live_cross_check": live,
        "finding": ("The decline was concentrated, not general: three Hungarian-language aggregator "
                    "channels account for the great majority of it, while the Russian-institutional "
                    "feeds stayed flat at 21-24 articles/day throughout. But the collapse was "
                    "temporary — those same three channels supply essentially all of the rebound, "
                    "and the source mix returns close to its pre-election composition. The "
                    "Hungarian-language supply was interrupted and then restored."),
        "cannot_show": ("why the supply was interrupted. And note the bounds: the per-source "
                        "series covers the top 10 credited sources only (80% of baseline articles, "
                        "70% at the trough); credit labels are the operator's own metadata, which "
                        "cost nothing to omit; and our live capture harvests only the mirror's "
                        "English surface while the census counts all languages, so it cannot be "
                        "compared with the census to say what the mirror consumes — all it shows is "
                        "that these channels were still publishing on the capture day."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    a = out["attribution"]
    print(f"source_diet.json: decline {out['totals']['decline_per_day']}/day; "
          f"3 Hungarian-language channels = {a['share_of_total_decline']*100:.0f}% of it")
    for s in sources[:3]:
        print(f"   {s['source'][:44]:46} {s['baseline_per_day']:6.1f} -> {s['after_per_day']:5.1f} "
              f"({s['change_pct']:+d}%)")
    r = out["recovery"]
    print(f"   recovery {r['window'][0]}..{r['window'][1]}: {r['per_day']}/day "
          f"({r['pct_of_baseline']}% of baseline); the collapsed set supplies "
          f"{r['collapsed_set_share_of_rebound']*100:.0f}% of the rebound")
    c = r["collapsed_set_share_of_output"]
    print(f"   their share of output: baseline {c['baseline']*100:.0f}% -> trough "
          f"{c['trough']*100:.0f}% -> recovery {c['recovery']*100:.0f}%")
    if live:
        print(f"   live capture (ENGLISH surface only — not comparable with the census): "
              f"{live['collapsed_set_captured_now']} items from the collapsed set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
