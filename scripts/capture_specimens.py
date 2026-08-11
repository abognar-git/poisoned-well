#!/usr/bin/env python3
"""Capture the most recent article specimens the Hungarian Pravda mirror emitted.

Run SERVER-SIDE ONLY (locally / in CI) — never from a visitor's browser — so the
site can show live evidence of ongoing output without any visitor's browser (or
referrer) touching the propaganda domain, and without feeding its inbound-link/SEO
signal. Output: data/derived/latest_specimens.json with a captured_at timestamp.

Editorial rules baked in:
  - specimens are shown as EVIDENCE, not endorsement; the site never hyperlinks them
  - SKIP any headline that reads as a personal smear (republishing defamation verbatim
    is off-limits) — those are documented in the case files as debunked evidence instead
  - titles come from the network's own English edition (/en/), i.e. its own translation
"""

import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MIRROR = "https://hungary.news-pravda.com/en/"
OUT = Path(__file__).resolve().parent.parent / "data" / "derived" / "latest_specimens.json"
N = 6

# headlines matching these (personal-accusation markers) are not republished verbatim
SMEAR = re.compile(r"\b(pedophil|paedophil|p[aä]edo|rapist|rape|molest|traffick|"
                   r"epstein|blackmail|corrupt(?:ion)? charges?)\b", re.I)

# Transparent, disclosed topic tags: a crude keyword match on the headline used to
# separate geopolitical PAYLOAD from mundane camouflage. First match (in this order)
# wins. This is a heuristic on topic — NOT a human judgement of an item's intent.
THEMES = [
    ("hungary",  r"hungar|orb[aá]n|budapest|magyar|fidesz|tisza"),
    ("ukraine",  r"ukrain|kyiv|kiev|zelensk|donbas|kharkiv|odes[sa]a?\b"),
    ("russia",   r"russia|putin|kremlin|moscow|lavrov|ria novosti|\btass\b|sputnik|gazprom|rosatom"),
    ("eu/nato",  r"\beu\b|europe|brussels|von der leyen|\bnato\b|sanction|baltic|migrant|migration"),
    ("energy",   r"\bgas\b|\boil\b|pipeline|nord stream|druzhba|turkstream|energy"),
]
PAYLOAD = {"hungary", "ukraine", "russia", "eu/nato", "energy"}


def classify(title: str, category: str) -> str:
    hay = f"{title} {category}".lower()
    for name, pat in THEMES:
        if re.search(pat, hay):
            return name
    return "filler"

LINK = re.compile(
    r'<a[^>]*href="(https://hungary\.news-pravda\.com/en/([a-z-]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html)"[^>]*>(.*?)</a>',
    re.S)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def main() -> int:
    page = fetch(MIRROR)
    seen, rows = set(), []
    for m in LINK.finditer(page):
        url, cat, y, mo, d, aid, inner = m.groups()
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
        if url in seen or len(title) < 15:
            continue
        seen.add(url)
        rows.append({
            "id": int(aid), "date": f"{y}-{mo}-{d}", "category": cat,
            "title": title[:180], "smear": bool(SMEAR.search(title)),
            "theme": classify(title, cat),
        })
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    specimens = [r for r in rows if not r["smear"]][:N]
    skipped = sum(1 for r in rows if r["smear"])
    payload_n = sum(1 for r in specimens if r["theme"] in PAYLOAD)

    out = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "hungary.news-pravda.com (English edition), captured server-side; not linked",
        "note": ("Unaltered headlines this Russia-attributed network published, shown as evidence of "
                 "ongoing output. Not endorsed, not linked. Personal-smear items are withheld here and "
                 "documented as debunked evidence in the case files."),
        "theme_note": ("Theme tags are a crude keyword match on the headline (see THEMES in "
                       "scripts/capture_specimens.py) used to separate geopolitical payload from mundane "
                       "camouflage — a heuristic on topic, not a human judgement of intent."),
        "smear_items_withheld": skipped,
        "payload_count": payload_n,
        "specimens": [{k: r[k] for k in ("id", "date", "category", "title", "theme")} for r in specimens],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"latest_specimens.json: {len(specimens)} specimens ({payload_n} payload / {len(specimens)-payload_n} filler; "
          f"latest id {specimens[0]['id']}, {specimens[0]['date']}), {skipped} smear withheld")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
