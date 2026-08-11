#!/usr/bin/env python3
"""Derive the committed summary datasets from raw fetched data.

Inputs  (data/raw/, gitignored, refreshed by the fetch scripts)
Outputs (data/derived/, committed — every number the site cites comes from here)

  pravda_summary.json       per-mirror activity: totals, date range, peak day,
                            recent daily rate, top laundering sources, languages
  pravda_network.json       the full 101-mirror manifest + cross-language edges
                            (mirror manifest; cited by evidence cards)
  doppelganger_summary.json Meta's Q2-2023 Doppelganger indicator set broken down
                            by kill-chain tactic and targeted country
  live_status.json          the "still running" counters per mirror (today / last
                            7 days / total, latest publication day, generated_at)
"""

import csv
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived"

TARGET_DOMAINS = [
    "hungary.news-pravda.com",
    "slovakia.news-pravda.com",
    "romania.news-pravda.com",
    "moldova.news-pravda.com",
    "czechia.news-pravda.com",
    "deutsch.news-pravda.com",
    "poland.news-pravda.com",
]


def pravda_summaries() -> None:
    summaries = {}
    for d in TARGET_DOMAINS:
        viz = json.loads((RAW / "pravda" / "json" / f"{d}_viz.json").read_text())
        days = [x for x in viz["articlesPerDay"] if x["count"] > 0]
        days.sort(key=lambda x: x["date"])
        peak = max(days, key=lambda x: x["count"])
        last30_cut = (date.fromisoformat(days[-1]["date"]) - timedelta(days=30)).isoformat()
        last30 = [x["count"] for x in days if x["date"] > last30_cut]
        summaries[d] = {
            "total_articles": viz["totalArticles"],
            "first_day": days[0]["date"],
            "last_day": days[-1]["date"],
            "active_days": len(days),
            "peak_day": peak,
            "avg_daily_last30": round(sum(last30) / max(len(last30), 1), 1),
            "top_sources": viz["topSources"][:10],
            "n_sources": len(viz["topSources"]),
            "n_languages": len(viz["languages"]),
            "avg_alternates_per_article": round(viz["alternatesStats"]["avgAlternatesPerArticle"], 2),
        }
    OUT.joinpath("pravda_summary.json").write_text(json.dumps(summaries, indent=2))
    print(f"pravda_summary.json: {len(summaries)} mirrors")

    hu = json.loads((RAW / "pravda" / "json" / "hungary.news-pravda.com_viz.json").read_text())
    network = {
        "domains": json.loads((RAW / "pravda" / "domains.json").read_text()),
        "language_connections": hu["languageConnections"],
        "domain_language_data": hu["domainLanguageData"],
    }
    OUT.joinpath("pravda_network.json").write_text(json.dumps(network, indent=2))
    print(f"pravda_network.json: {len(network['domains'])} domains, "
          f"{len(network['language_connections'])} language edges")


def pravda_timeline() -> None:
    """Full daily article series for the anchor mirror, with annotated events."""
    viz = json.loads((RAW / "pravda" / "json" / "hungary.news-pravda.com_viz.json").read_text())
    series = sorted(([x["date"], x["count"]] for x in viz["articlesPerDay"]),
                    key=lambda p: p[0])
    out = {
        "domain": "hungary.news-pravda.com",
        "series": series,
        "events": [
            {"date": "2024-03-20", "label": "pravda-hu.com registered (VIGINUM wave, 19 EU states)"},
            {"date": "2024-07-05", "label": "peak output: 712 articles in one day"},
            {"date": "2026-03-06", "label": "GRU 'election fixers' reported in Budapest (VSquare)"},
            {"date": "2026-04-12", "label": "Hungary votes — Tisza wins 141/199"},
            {"date": series[-1][0], "label": "still publishing"},
        ],
    }
    OUT.joinpath("pravda_timeline.json").write_text(json.dumps(out))
    print(f"pravda_timeline.json: {len(series)} days, {len(out['events'])} events")


def live_status() -> None:
    """The site's 'this is still happening' counters, refreshed on every run."""
    mirrors = {}
    for d in TARGET_DOMAINS:
        viz = json.loads((RAW / "pravda" / "json" / f"{d}_viz.json").read_text())
        days = sorted((x for x in viz["articlesPerDay"] if x["count"] > 0),
                      key=lambda x: x["date"])
        last_day = days[-1]["date"]
        week_cut = (date.fromisoformat(last_day) - timedelta(days=7)).isoformat()
        mirrors[d] = {
            "total": viz["totalArticles"],
            "latest_publication_day": last_day,
            "articles_latest_day": days[-1]["count"],
            "articles_last_7d": sum(x["count"] for x in days if x["date"] > week_cut),
        }
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "upstream": "https://github.com/CheckFirstHQ/pravda-network (updated hourly)",
        "mirrors": mirrors,
    }
    OUT.joinpath("live_status.json").write_text(json.dumps(out, indent=2))
    hu = mirrors["hungary.news-pravda.com"]
    print(f"live_status.json: hungary latest day {hu['latest_publication_day']} "
          f"({hu['articles_latest_day']} articles), last 7d {hu['articles_last_7d']}")


def doppelganger_summary() -> None:
    path = (RAW / "meta-threat-research" / "indicators" / "csv" / "Q2_2023 " /
            "Q2_2023_Doppelganger_Russia_based_CIB_network_updated.csv")
    tactics: Counter = Counter()
    countries: Counter = Counter()
    n = 0
    with path.open() as f:
        for row in csv.DictReader(f):
            n += 1
            tactics[row["Tactic"].strip()] += 1
            m = re.search(r"Country likely targeted:\s*([A-Za-z ]+)", row.get("Comments") or "")
            if m:
                countries[m.group(1).strip()] += 1
    out = {
        "source": "Meta threat-research GitHub (MIT), Q2 2023 Doppelganger indicator set",
        "total_indicators": n,
        "by_killchain_tactic": dict(tactics.most_common()),
        "by_targeted_country": dict(countries.most_common()),
        "hungary_indicators": countries.get("Hungary", 0),
    }
    OUT.joinpath("doppelganger_summary.json").write_text(json.dumps(out, indent=2))
    print(f"doppelganger_summary.json: {n} indicators, "
          f"{len(countries)} target countries, Hungary={out['hungary_indicators']}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pravda_summaries()
    pravda_timeline()
    live_status()
    doppelganger_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
