#!/usr/bin/env python3
"""Join the two series and answer the study's hinge question.

Everything else in this repository sees one side of the relationship. CheckFirst's scrape
records what the MIRROR published and what it credited; it cannot see whether the channels
themselves went quiet. So a 63.7% fall in output, 87% of it concentrated in three
Hungarian-language aggregator channels, has two readings that the data could not separate:

    the channels stopped posting   -> upstream supply interruption
    the channels kept posting      -> the mirror stopped crediting them

scripts/backpage_telegram.py reconstructs the channels' own posting history from Telegram's
public preview, independently of the mirror. This joins that to the mirror's per-day credit
counts from data/panel/ and states which reading the evidence supports.

HOW TO READ THE RATIO. `credits_per_post` is the mirror's credits for a channel on a day
over that channel's own posts that day. It is not a capture rate and can exceed 1: the
mirror republishes a single post as more than one article, and it credits a post on a day
after it was published. What matters is not its level but its MOVEMENT. If the channels
went quiet, credits and posts fall together and the ratio holds. If the mirror stopped
crediting a channel that kept working, posts hold and the ratio collapses.

WHAT IT STILL CANNOT SAY. Why. A mirror that stopped crediting could have been blocked,
rebuilt, redirected, or told to stop; nothing here distinguishes those, and the project
claims no cause. And the channel counts are lower bounds — see backpage_telegram.py — which
biases toward "the channels kept posting", so a result in the other direction is the
stronger one.

WHAT IT REFUSES TO DO. Answer from part of the evidence. Each channel contributes one change
to each mean, and a channel whose baseline or trough window is empty contributes nothing —
so an unfinished walk quietly shrinks the denominator while the output still lists every
channel. That is not hypothetical: walked back only to June, greatawakeningmagyarok loses its
whole baseline, the surviving two average -11.8, and -11.8 clears the -15 threshold into "the
interruption is on the MIRROR's side" — the largest claim here — on two channels of three. So
an empty window is a refusal, not a smaller sample. --force writes anyway and stamps the
shortfall into `reading`, `channels_in_mean` and `forced_past_gate`.

    python3 scripts/derive_supply_test.py
    python3 scripts/derive_supply_test.py --force   # verdict on a subset, labelled as one
"""
import csv
import glob
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACT = ROOT / "data" / "derived" / "channel_activity.json"
PANEL = ROOT / "data" / "panel" / "mirror_source_day"
OUT = ROOT / "data" / "derived" / "supply_test.json"
MIRROR = "hungary"

# The windows derive_diet.py already uses, so this is comparable with the published
# decomposition rather than a fresh set of dates chosen after seeing the answer.
WINDOWS = {"baseline": ("2026-02-01", "2026-04-11"),
           "trough":   ("2026-04-27", "2026-06-30"),
           "recovery": ("2026-07-01", "2026-08-10")}

# Above this, a fall in the channels' own posting is too small to carry the credit collapse
# and the verdict goes to the mirror's side. Named, and written into the output, because the
# README reports how close the result sits to it — and a threshold quoted in prose from a
# literal buried in a script is the drift this repository has already shipped twice.
MIRROR_SIDE_THRESHOLD = -15


def credit_series(channels):
    daily = {c: defaultdict(int) for c in channels}
    want = {f"Telegram: {c}": c for c in channels}
    for f in sorted(glob.glob(str(PANEL / "*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["mirror"] == MIRROR and r["source"] in want:
                daily[want[r["source"]]][r["date"]] += int(r["credits"])
    return daily


def mean_in(series, lo, hi):
    vals = [v for d, v in series.items() if lo <= d <= hi]
    return round(statistics.mean(vals), 1) if vals else None


def main(force=False) -> int:
    if not ACT.exists():
        print("no channel_activity.json — run scripts/backpage_telegram.py first")
        return 1
    act = json.loads(ACT.read_text())
    channels = list(act["channels"])
    credits = credit_series(channels)

    per_channel = {}
    for ch in channels:
        posts = {d: n for d, n in act["channels"][ch]["daily_posts"].items()}
        cred = credits[ch]
        w = {}
        for name, (lo, hi) in WINDOWS.items():
            p, c = mean_in(posts, lo, hi), mean_in(cred, lo, hi)
            w[name] = {"posts_per_day": p, "credits_per_day": c,
                       "credits_per_post": round(c / p, 2) if p else None}
        b, t = w["baseline"], w["trough"]
        per_channel[ch] = {
            "windows": w,
            "posts_change_pct": (round((t["posts_per_day"] - b["posts_per_day"])
                                       / b["posts_per_day"] * 100, 1)
                                 if b["posts_per_day"] else None),
            "credits_change_pct": (round((t["credits_per_day"] - b["credits_per_day"])
                                         / b["credits_per_day"] * 100, 1)
                                   if b["credits_per_day"] else None),
            "days_with_posts_in_trough": sum(1 for d, n in posts.items()
                                             if WINDOWS["trough"][0] <= d <= WINDOWS["trough"][1]
                                             and n > 0),
            "id_coverage": act["channels"][ch]["id_coverage"],
        }

    # A channel whose baseline or trough window is empty cannot contribute a change, and
    # averaging what is left would answer the hinge question from a subset while the output
    # still listed every channel. That is how a truncated walk produces a confident verdict:
    # with greatawakeningmagyarok walked back only to June, its baseline is empty, it drops
    # out silently, and the mean of the surviving two lands at -11.8 — past the -15 threshold
    # and into "the interruption is on the MIRROR's side", the largest claim this test can
    # make, on two thirds of the evidence. So the gate refuses rather than degrades.
    for ch, v in per_channel.items():
        gaps = [f"{name} {series}"
                for name in ("baseline", "trough")
                for series, key in (("posts", "posts_per_day"), ("credits", "credits_per_day"))
                if v["windows"][name][key] is None]
        v["in_mean"] = not gaps
        v["empty_windows"] = gaps

    excluded = {ch: v["empty_windows"] for ch, v in per_channel.items() if not v["in_mean"]}
    if excluded and not force:
        print("refusing to publish a verdict from a subset of the channels. These have no "
              "data in a window the comparison needs:", file=sys.stderr)
        for ch, gaps in excluded.items():
            print(f"  {ch}: empty {', '.join(gaps)}", file=sys.stderr)
        first, last = WINDOWS["baseline"][0], WINDOWS["recovery"][1]
        print(f"The walk must cover {first} to {last} for every channel. Run "
              f"scripts/backpage_telegram.py --since {first} to finish it, or pass --force "
              f"to write a verdict that rests on {len(per_channel) - len(excluded)} of "
              f"{len(per_channel)} channels and says so.", file=sys.stderr)
        return 1

    # The verdict is a comparison of two changes, not a threshold on one of them.
    pc = [v["posts_change_pct"] for v in per_channel.values() if v["posts_change_pct"] is not None]
    cc = [v["credits_change_pct"] for v in per_channel.values() if v["credits_change_pct"] is not None]
    posts_mean = round(statistics.mean(pc), 1) if pc else None
    credits_mean = round(statistics.mean(cc), 1) if cc else None

    if posts_mean is None or credits_mean is None:
        reading = "not computable — one of the series is empty"
    elif posts_mean <= credits_mean + 10:
        reading = ("The channels fell with the credits. On this evidence the interruption "
                   "is upstream of the mirror, in the channels' own output.")
    elif posts_mean > MIRROR_SIDE_THRESHOLD:
        reading = ("The channels kept posting through the trough while the mirror's credits "
                   "to them collapsed. On this evidence the interruption is on the MIRROR'S "
                   "side: it stopped crediting sources that were still working. This says "
                   "nothing about why.")
    else:
        reading = ("Both fell, but the channels fell substantially less than the credits. "
                   "Part of the interruption is upstream and part is on the mirror's side; "
                   "neither reading carries it alone.")

    if excluded:
        reading += (f" READ THIS FIRST: the mean behind it covers "
                    f"{len(per_channel) - len(excluded)} of {len(per_channel)} channels. "
                    f"{', '.join(excluded)} had no data in a window the comparison needs and "
                    f"was dropped. This verdict was forced past the gate and is not the "
                    f"study's answer.")

    out = {
        "note": ("The decisive test named in RESEARCH.md. Channel posting history comes from "
                 "Telegram's public preview, independently of the mirror; credits come from "
                 "CheckFirst's per-day panel. credits_per_post is a ratio between two "
                 "differently-collected series — read its movement, not its level."),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "windows": {k: list(v) for k, v in WINDOWS.items()},
        "channels": per_channel,
        # How much of the evidence the two means below actually rest on. A reader who sees
        # three channels listed above should not have to infer that the verdict used fewer.
        "channels_total": len(per_channel),
        "channels_in_mean": len(per_channel) - len(excluded),
        "channels_excluded": excluded,
        "forced_past_gate": bool(excluded),
        "posts_change_pct_mean": posts_mean,
        "credits_change_pct_mean": credits_mean,
        # The rule the reading came out of, and how close it was to the other side of it.
        "mirror_side_threshold": MIRROR_SIDE_THRESHOLD,
        "margin_to_mirror_side": (round(abs(posts_mean - MIRROR_SIDE_THRESHOLD), 2)
                                  if posts_mean is not None else None),
        "reading": reading,
        "cannot_show": ("Why the credits moved. A mirror that stopped crediting could have "
                        "been blocked, rebuilt, redirected or instructed; nothing here "
                        "separates those and this project claims no cause. Channel counts "
                        "are lower bounds — a post deleted before the walk is invisible — "
                        "which biases toward 'the channels kept posting'."),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    print("supply_test.json")
    for ch, v in per_channel.items():
        w = v["windows"]
        print(f"  {ch}")
        for name in ("baseline", "trough", "recovery"):
            x = w[name]
            print(f"    {name:<9} posts {str(x['posts_per_day']):>6}/day · "
                  f"credits {str(x['credits_per_day']):>6}/day · "
                  f"ratio {x['credits_per_post']}")
        print(f"    posts {v['posts_change_pct']}%  vs  credits {v['credits_change_pct']}%"
              f"   ({v['days_with_posts_in_trough']} days posting in the trough)")
    print(f"\n  mean: posts {posts_mean}% · credits {credits_mean}%")
    print(f"  {out['reading']}")
    return 0


if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser(description=__doc__)
    _ap.add_argument("--force", action="store_true",
                     help="write a verdict even though a channel has no data in a window "
                          "the comparison needs; the reading says so")
    raise SystemExit(main(force=_ap.parse_args().force))
