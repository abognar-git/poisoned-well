#!/usr/bin/env python3
"""Generate data/derived/peer_control.json — the mirror's response to losing its election.

The Pravda network runs one mirror per target country. That gives this project something
it otherwise could not buy: a natural control group. Six sibling mirrors — Slovakia,
Czechia, Poland, Romania, Moldova and the German-language one — share the network's
infrastructure, its upstream sources and its operating period, and differ from the
Hungarian mirror in exactly one relevant way: no Hungarian election.

So when the Hungarian mirror does something, we can ask whether the network did it too.

What the comparison shows, and it is not what we expected:

  * NO CAMPAIGN SURGE *RELATIVE TO ITS PEERS*. The mirror did rise into the campaign —
    March 2026 is in fact the highest month in its whole series — but so did the rest of
    the network, and by more than the gap between them: Hungary +24.0% Feb->Mar against a
    peer mean of +12.4%. The excess is real but small, and nothing like the step change
    the mirror underwent in early 2025. Stated as a raw "it ran flat", this is simply
    false, and a hostile reader finds that in ten minutes.
  * A COLLAPSE AFTER THE VOTE. In the two months after the government it favoured lost,
    output fell about 64% against its own February-March baseline, while the six peers
    moved +1.6% on average and not one fell by more than 17%.
  * AND A RECOVERY. It has climbed back month by month and is now near where it started.

Causation is not available here. Temporal coincidence plus a six-mirror control makes
"unrelated coincidence" a strain, but the data cannot distinguish a decision from a
disrupted supply of upstream material, and we say so rather than choose.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pravda" / "json"
OUT = ROOT / "data" / "derived" / "peer_control.json"

TARGET = "hungary"
ELECTION = "2026-04-12"
BASELINE = ["2026-02", "2026-03"]   # the two full months before the vote
AFTER = ["2026-05", "2026-06"]      # the two full months after it


def main() -> int:
    series, monthly = {}, {}
    for f in sorted(RAW.glob("*_viz.json")):
        d = json.loads(f.read_text())
        key = d["domain"].split(".")[0]
        mon = defaultdict(list)
        for x in d["articlesPerDay"]:
            mon[x["date"][:7]].append(x["count"])
        monthly[key] = {m: round(statistics.mean(v), 1) for m, v in sorted(mon.items())}
        series[key] = {"domain": d["domain"], "total": d["totalArticles"]}

    def mean_of(key, months):
        vals = [monthly[key][m] for m in months if m in monthly[key]]
        return statistics.mean(vals) if vals else None

    rows = []
    for key in sorted(monthly):
        base, after = mean_of(key, BASELINE), mean_of(key, AFTER)
        latest_month = max(monthly[key])
        rows.append({
            "mirror": key,
            "domain": series[key]["domain"],
            "is_target": key == TARGET,
            "baseline_per_day": round(base, 1) if base else None,
            "after_per_day": round(after, 1) if after else None,
            "change_pct": round((after - base) / base * 100, 1) if base else None,
            "latest_month": latest_month,
            "latest_per_day": monthly[key][latest_month],
            "recovery_pct_of_baseline": round(monthly[key][latest_month] / base * 100, 1) if base else None,
            "monthly": monthly[key],
        })

    # When did the break actually land? Not at the election: the day AFTER the vote is
    # April's highest day, and output holds for another twelve days. Juxtaposing "after the
    # election" with the fall implies a response the timing does not support.
    tdaily = {}
    for f in sorted(RAW.glob(f"{TARGET}*_viz.json")):
        tdaily = {x["date"]: x["count"] for x in json.loads(f.read_text())["articlesPerDay"]}
    after_vote = {k: v for k, v in tdaily.items() if ELECTION < k <= "2026-04-24"}
    onset = {k: v for k, v in tdaily.items() if "2026-04-27" <= k <= "2026-05-10"}
    timing = {
        "election": ELECTION,
        "day_after_election": {"date": "2026-04-13", "count": tdaily.get("2026-04-13")},
        "highest_april_day": max(((k, v) for k, v in tdaily.items() if k.startswith("2026-04")),
                                 key=lambda kv: kv[1]),
        "mean_13_to_24_april": round(statistics.mean(after_vote.values()), 1) if after_vote else None,
        "mean_27_april_to_10_may": round(statistics.mean(onset.values()), 1) if onset else None,
        "estimated_onset": "2026-04-27",
        "gap_days_after_election": 15,
        "reading": ("The fall does not begin at the election. The day after the vote is the "
                    "month's highest day, output holds near its baseline for a further twelve "
                    "days, and the step lands around 27 April. Any account that reads this as a "
                    "reaction to the result has to explain the fifteen-day gap."),
    }

    tgt = next(r for r in rows if r["is_target"])
    peers = [r for r in rows if not r["is_target"]]
    peer_changes = [r["change_pct"] for r in peers]

    out = {
        "note": ("Generated by scripts/derive_peer_control.py from CheckFirst's per-mirror daily "
                 "counts. The six non-Hungarian mirrors are used as a control group: same network, "
                 "same period, no Hungarian election."),
        "election": ELECTION,
        "baseline_months": BASELINE,
        "after_months": AFTER,
        "timing": timing,
        "target": tgt,
        "peers": peers,
        "comparison": {
            "target_change_pct": tgt["change_pct"],
            "peer_mean_change_pct": round(statistics.mean(peer_changes), 1),
            "peer_min_change_pct": min(peer_changes),
            "peer_max_change_pct": max(peer_changes),
            "target_is_outlier": tgt["change_pct"] < min(peer_changes),
            "peer_n": len(peers),
        },
        "reading": (
            "Against its six siblings the Hungarian mirror shows no disproportionate campaign "
            "surge — it rose into March 2026 as the network did — and then fell by about two "
            "thirds in the two months after the election was lost, a move no sibling made. It "
            "has since recovered most of the way back."),
        "cannot_show": (
            "Cause. The control rules out a network-wide or seasonal effect, but it cannot "
            "distinguish an operational decision from a disruption in the upstream Telegram "
            "channels this mirror republishes, or from a change in what the collector sees. "
            "We report the shape and the control, not a motive."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    c = out["comparison"]
    print(f"peer_control.json: {TARGET} {c['target_change_pct']:+.1f}% after the vote vs "
          f"{c['peer_n']} peers mean {c['peer_mean_change_pct']:+.1f}% "
          f"(range {c['peer_min_change_pct']:+.1f}%..{c['peer_max_change_pct']:+.1f}%), "
          f"outlier={c['target_is_outlier']}")
    print(f"  recovery: {tgt['latest_month']} at {tgt['latest_per_day']}/day = "
          f"{tgt['recovery_pct_of_baseline']}% of its pre-election baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
