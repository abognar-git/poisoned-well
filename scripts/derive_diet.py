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
  * Our live capture is a snapshot of today. It shows the channels are active NOW; it
    cannot show whether they were active during the May-June trough.
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

# the three Hungarian-language aggregator channels that carried the mirror before the vote
COLLAPSED = ["Telegram: oroszokazigazsagoldalan",
             "Telegram: ebredes2017",
             "Telegram: greatawakeningmagyarok"]


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
    sources.sort(key=lambda s: -s["baseline_per_day"])

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
        "live_cross_check": live,
        "finding": ("What fell away was the Hungarian-language amplifier layer. What carried on, "
                    "and now carries the mirror's recovery, is the Russian-origin institutional "
                    "layer. Our own scraping finds the abandoned channels still publishing, so "
                    "this is not a supply failure — the mirror's diet changed."),
        "cannot_show": ("Why. And note the limits: the per-source series covers the top 10 sources "
                        "only (80% of baseline articles, 70% after), our live capture proves those "
                        "channels are active today but not that they were active during the trough, "
                        "and the mirror articles in a single snapshot number only tens."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    a = out["attribution"]
    print(f"source_diet.json: decline {out['totals']['decline_per_day']}/day; "
          f"3 Hungarian-language channels = {a['share_of_total_decline']*100:.0f}% of it")
    for s in sources[:3]:
        print(f"   {s['source'][:44]:46} {s['baseline_per_day']:6.1f} -> {s['after_per_day']:5.1f} "
              f"({s['change_pct']:+d}%)")
    if live:
        print(f"   live: those channels captured {sum(o['captured_now'] for o in live['origin_channels_we_scrape'][:3])} "
              f"posts today; mirror credited them {live['collapsed_set_credited_now']}× "
              f"in {live['mirror_articles_in_snapshot']} sampled articles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
