#!/usr/bin/env python3
"""Peer-control analysis for a franchised propaganda network — generalised.

A network that runs one outlet per target country hands the analyst something rare: the
siblings are a control group. Same infrastructure, same upstream pool, same period, a
different target. That converts an n=1 case study into a panel.

This script is the instrument. It is not about Hungary; Hungary is one row.

TWO MODES, and the second matters more.

  --events   Test pre-specified events from catalog/events.json. Answers "did this outlet
             behave anomalously around this vote?" Requires knowing the date in advance,
             which means it can only confirm what you already suspected.

  --scan     Find the largest interruptions in every mirror WITHOUT being told where to
             look, then report their dates. This is the honest direction of inference: if
             detected interruptions cluster near national votes, that is a finding; if they
             land anywhere and everywhere, the measure is picking up ordinary volatility
             and no amount of event-testing will save it.

WHY THE NORMALISED RANK IS THE ONE THAT COUNTS
An unnormalised "most extreme window in the network" contest is partly won by whichever
outlet is noisiest. In this dataset Hungary is: sd 58.8% of two-month change against
Romania's 13.2%. Its 63.7% drop ranks 1/185 raw and 13/185 (p=0.070) once each window is
divided by its own mirror's historical volatility. Both are reported; lead with the second.

DESIGN, held identical across every row so the comparison means something:
  baseline = the two full calendar months before the event month
  event month itself is skipped
  after    = the two full calendar months following
Partial first/last months are excluded — a partial month's daily mean is not comparable
with a full one, and including them inflates the window count.

WHAT THIS CANNOT DO
Establish cause; distinguish an operator decision from an upstream supply failure or from a
change in what the collector sees; or say anything about content, reach or persuasion. It
measures publication volume and declared provenance, nothing else.
"""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pravda" / "json"
EVENTS = ROOT / "catalog" / "events.json"
OUT = ROOT / "data" / "derived" / "network_scan.json"


def load_mirrors():
    """Full-calendar-month daily means per mirror."""
    out = {}
    for f in sorted(RAW.glob("*_viz.json")):
        d = json.loads(f.read_text())
        key = d["domain"].split(".")[0]
        mon = defaultdict(list)
        for x in d["articlesPerDay"]:
            mon[x["date"][:7]].append(x["count"])
        days = sorted({x["date"] for x in d["articlesPerDay"]})
        partial = {days[0][:7], days[-1][:7]}
        out[key] = {
            "domain": d["domain"],
            "total": d["totalArticles"],
            "first_day": days[0],
            "last_day": days[-1],
            "monthly": {m: statistics.mean(v) for m, v in sorted(mon.items())
                        if m not in partial},
        }
    return out


def next_month(m):
    y, mm = map(int, m.split("-"))
    mm += 1
    return f"{y + 1:04d}-01" if mm == 13 else f"{y:04d}-{mm:02d}"


def windows_for(mirrors, key):
    """Every admissible (baseline, cut, after) triple for one mirror."""
    ms = sorted(mirrors[key]["monthly"])
    out = []
    for i in range(2, len(ms) - 2):
        w = ms[i - 2:i + 3]
        if all(w[j + 1] == next_month(w[j]) for j in range(4)):
            out.append((w[:2], w[2], w[3:]))
    return out


def change(mirrors, key, base_ms, after_ms):
    mm = mirrors[key]["monthly"]
    if not all(m in mm for m in base_ms + after_ms):
        return None
    b = statistics.mean([mm[m] for m in base_ms])
    a = statistics.mean([mm[m] for m in after_ms])
    return (a - b) / b * 100 if b else None


def all_windows(mirrors):
    rows = []
    for key in mirrors:
        for base_ms, cut, after_ms in windows_for(mirrors, key):
            c = change(mirrors, key, base_ms, after_ms)
            if c is not None:
                rows.append({"mirror": key, "cut": cut, "change_pct": round(c, 1)})
    return rows


def volatility(rows):
    """Each mirror's own sd of two-month change — the normaliser."""
    vol = {}
    for key in {r["mirror"] for r in rows}:
        ch = [r["change_pct"] for r in rows if r["mirror"] == key]
        vol[key] = statistics.pstdev(ch) if len(ch) > 1 else None
    return vol


def analyse(mirrors, key, cut, rows, vol):
    """One row of the panel: target change, peer behaviour, and both ranks."""
    ms = sorted(mirrors[key]["monthly"])
    if cut not in ms:
        return None
    i = ms.index(cut)
    if i < 2 or i > len(ms) - 3:
        return None
    base_ms, after_ms = ms[i - 2:i], ms[i + 1:i + 3]
    tgt = change(mirrors, key, base_ms, after_ms)
    if tgt is None:
        return None

    peers = {}
    for other in mirrors:
        if other == key:
            continue
        c = change(mirrors, other, base_ms, after_ms)
        if c is not None:
            peers[other] = round(c, 1)

    this = next((r for r in rows if r["mirror"] == key and r["cut"] == cut), None)
    z = tgt / vol[key] if vol.get(key) else None
    raw_rank = sorted(rows, key=lambda r: r["change_pct"]).index(this) + 1 if this else None
    z_rank = None
    if z is not None and all(vol.get(r["mirror"]) for r in rows):
        zs = sorted(rows, key=lambda r: r["change_pct"] / vol[r["mirror"]])
        z_rank = zs.index(this) + 1 if this else None

    return {
        "mirror": key,
        "cut_month": cut,
        "baseline_months": base_ms,
        "after_months": after_ms,
        "baseline_per_day": round(statistics.mean([mirrors[key]["monthly"][m] for m in base_ms]), 1),
        "after_per_day": round(statistics.mean([mirrors[key]["monthly"][m] for m in after_ms]), 1),
        "change_pct": round(tgt, 1),
        "peer_changes": peers,
        "peer_mean_pct": round(statistics.mean(peers.values()), 1) if peers else None,
        "peer_min_pct": min(peers.values()) if peers else None,
        "diff_vs_peer_mean_pp": round(tgt - statistics.mean(peers.values()), 1) if peers else None,
        "target_is_window_outlier": bool(peers) and tgt < min(peers.values()),
        "own_volatility_sd_pct": round(vol[key], 1) if vol.get(key) else None,
        "z_vs_own_history": round(z, 2) if z is not None else None,
        "raw_rank": raw_rank,
        "raw_p": round(raw_rank / len(rows), 4) if raw_rank else None,
        "normalised_rank": z_rank,
        "normalised_p": round(z_rank / len(rows), 4) if z_rank else None,
        "n_windows": len(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", action="store_true",
                    help="find the largest interruptions without pre-specified dates")
    ap.add_argument("--events", action="store_true",
                    help="test the pre-specified events in catalog/events.json")
    ap.add_argument("--top", type=int, default=12, help="how many scan hits to report")
    a = ap.parse_args()
    if not (a.scan or a.events):
        a.scan = a.events = True

    mirrors = load_mirrors()
    rows = all_windows(mirrors)
    vol = volatility(rows)

    out = {
        "note": ("Generated by scripts/analyse_network.py. The peer-control design applied "
                 "across a franchised network. Normalised ranks divide each window by its own "
                 "mirror's historical volatility and are the figures to lead with."),
        "mirrors": {k: {kk: v[kk] for kk in ("domain", "total", "first_day", "last_day")}
                    for k, v in mirrors.items()},
        "n_windows": len(rows),
        "volatility_sd_pct": {k: round(v, 1) for k, v in vol.items() if v},
    }

    if a.events:
        reg = json.loads(EVENTS.read_text())
        tested, skipped = [], []
        for ev in reg["events"]:
            res = analyse(mirrors, ev["mirror"], ev["date"][:7], rows, vol)
            if res:
                tested.append({**ev, "result": res})
            else:
                skipped.append({**ev, "why": "event month outside the analysable window"})
        out["events"] = {"tested": tested, "skipped": skipped,
                         "not_analysed": reg.get("needs_verification", [])}
        print(f"EVENTS — {len(tested)} tested, {len(skipped)} skipped, "
              f"{len(reg.get('needs_verification', []))} awaiting verified dates\n")
        print(f"{'event':34}{'change':>9}{'peer mean':>11}{'diff pp':>9}{'z':>7}{'norm rank':>11}")
        for t in tested:
            r = t["result"]
            print(f"  {t['id'][:32]:34}{r['change_pct']:+8.1f}%{r['peer_mean_pct']:+10.1f}%"
                  f"{r['diff_vs_peer_mean_pp']:+8.1f}{r['z_vs_own_history']:+7.2f}"
                  f"{str(r['normalised_rank']) + '/' + str(r['n_windows']):>11}")

    def episodes(scored, threshold=-0.75):
        """Collapse adjacent NOTABLE cut months into one episode.

        Windows slide month by month and share months with their neighbours, so a single
        sustained decline surfaces as four or five adjacent 'hits'. Reporting those as
        separate findings would manufacture a cluster out of one event.

        The threshold has to come FIRST. Grouping every adjacent window merges a mirror's
        entire series into one 'episode', because its months are of course consecutive —
        which is what an earlier version of this function did.
        """
        by = defaultdict(list)
        for r in scored:
            if r["z"] <= threshold:
                by[r["mirror"]].append(r)
        out = []
        for k, rs in by.items():
            rs.sort(key=lambda r: r["cut"])
            run = [rs[0]]
            for prev, cur in zip(rs, rs[1:]):
                if next_month(prev["cut"]) == cur["cut"]:
                    run.append(cur)
                else:
                    out.append(run); run = [cur]
            out.append(run)
        merged = []
        for run in out:
            peak = min(run, key=lambda r: r["z"])
            merged.append({"mirror": peak["mirror"], "peak_cut": peak["cut"],
                           "span": [run[0]["cut"], run[-1]["cut"]], "months": len(run),
                           "change_pct": peak["change_pct"], "z": peak["z"]})
        merged.sort(key=lambda r: r["z"])
        return merged

    if a.scan:
        scored = []
        for r in rows:
            if vol.get(r["mirror"]):
                scored.append({**r, "z": round(r["change_pct"] / vol[r["mirror"]], 2)})
        scored.sort(key=lambda r: r["z"])
        eps = episodes(scored)[:a.top]
        out["scan"] = {"episode_threshold_z": -0.75,
                       "windows_most_negative": scored[:a.top], "episodes": eps}
        print(f"\nSCAN — distinct interruption episodes, volatility-normalised, "
              f"no dates supplied\n")
        print(f"{'rank':>5}  {'mirror':10}{'peak':>9}{'span':>19}{'change':>9}{'z':>8}")
        for i, e in enumerate(eps, 1):
            span = f"{e['span'][0]}..{e['span'][1]}" if e["months"] > 1 else "-"
            print(f"  {i:3}  {e['mirror']:10}{e['peak_cut']:>9}{span:>19}"
                  f"{e['change_pct']:+8.1f}%{e['z']:+8.2f}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
