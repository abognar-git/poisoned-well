#!/usr/bin/env python3
"""Capture the most recent article specimens the Hungarian Pravda mirror emitted,
with the laundering source behind each one.

Run SERVER-SIDE ONLY (locally / in CI) — never from a visitor's browser — so the
site can show live evidence of ongoing output without any visitor's browser (or
referrer) touching the propaganda domain, and without feeding its inbound-link/SEO
signal. Output: data/derived/latest_specimens.json with a captured_at timestamp.

Editorial rules baked in:
  - specimens are shown as EVIDENCE, not endorsement; the site never hyperlinks them
    (neither the article nor its laundered source)
  - SKIP any headline that reads as a personal smear (republishing defamation verbatim
    is off-limits) — those are documented in the case files as debunked evidence instead
  - titles come from the network's own English edition (/en/), i.e. its own translation
  - theme tags are a crude, disclosed keyword heuristic on TOPIC, not a judgement of intent
  - on a fetch failure the last good file is left untouched (do not overwrite with garbage)
"""

import html
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MIRROR = "https://hungary.news-pravda.com/en/"
ART = "https://hungary.news-pravda.com/en/{cat}/{date}/{id}.html"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived" / "latest_specimens.json"
N = 6              # newest specimens to show
MIN_PAYLOAD = 2    # guarantee at least this many recent payload items are visible
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

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

LINK = re.compile(
    r'<a[^>]*href="(https://hungary\.news-pravda\.com/en/([a-z-]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html)"[^>]*>(.*?)</a>',
    re.S)
SRC = re.compile(r'data-source-url="([^"]+)"')

# messengers/social nets: source is a CHANNEL (first path segment is meaningful)
SOCIAL = {"t.me": "Telegram", "telegram.me": "Telegram", "max.ru": "MAX",
          "vk.com": "VK", "ok.ru": "OK", "dzen.ru": "Dzen"}
# news outlets: source is the OUTLET itself (no channel)
OUTLETS = [(r"tass\.", "TASS"), (r"ria\.", "RIA Novosti"), (r"news-front", "News Front"),
           (r"topwar", "Topwar"), (r"sputnik", "Sputnik"), (r"\brt\.com", "RT"),
           (r"gazeta\.", "Gazeta.ru"), (r"telegra\.ph", "Telegraph"), (r"rbc\.", "RBC"),
           (r"lenta\.", "Lenta.ru"), (r"news-pravda", "another Pravda mirror")]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def classify(title: str) -> str:
    """Topic tag from the HEADLINE only (the mirror's own category is shown separately)."""
    hay = title.lower()
    for name, pat in THEMES:
        if re.search(pat, hay):
            return name
    return "filler"


def source_of(cat, date, aid):
    """Fetch the article page and extract its laundered source (platform + channel)."""
    try:
        page = fetch(ART.format(cat=cat, date=date.replace("-", "/"), id=aid))
    except Exception:
        return None
    m = SRC.search(page)
    if not m:
        return None
    url = m.group(1)
    host = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", url).lower()
    path = [p for p in re.sub(r"^https?://[^/]+", "", url).split("/") if p and not p.startswith("@")]
    social = next((v for k, v in SOCIAL.items() if host == k or host.endswith("." + k)), None)
    if social:
        chan = path[0].lstrip("@") if path else None
        return {"platform": social, "channel": chan}
    outlet = next((label for pat, label in OUTLETS if re.search(pat, host)), host)
    return {"platform": outlet, "channel": None}


def main() -> int:
    page = fetch(MIRROR)  # if this fails, we exit non-zero WITHOUT writing (keep last good)
    seen, rows = set(), []
    for m in LINK.finditer(page):
        url, cat, y, mo, d, aid, inner = m.groups()
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
        if url in seen or len(title) < 15 or SMEAR.search(title):
            continue
        seen.add(url)
        rows.append({"id": int(aid), "date": f"{y}-{mo}-{d}", "category": cat,
                     "title": title[:180], "theme": classify(title)})
    skipped = sum(1 for m in LINK.finditer(page)
                  if SMEAR.search(re.sub(r"<[^>]+>", " ", m.group(7))))
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)

    # feature #4: show newest N, but guarantee the most-recent payload items appear
    selected = list(rows[:N])
    have = {r["id"] for r in selected}
    payload_now = sum(1 for r in selected if r["theme"] in PAYLOAD)
    for r in rows:
        if payload_now >= MIN_PAYLOAD:
            break
        if r["id"] not in have and r["theme"] in PAYLOAD:
            selected.append(r); have.add(r["id"]); payload_now += 1
    selected.sort(key=lambda r: (r["date"], r["id"]), reverse=True)

    # feature #1: attach the laundering source to each selected specimen
    for r in selected:
        r["source"] = source_of(r["category"], r["date"], r["id"])
        time.sleep(0.3)  # be polite: one slow requester, not a hammer

    payload_n = sum(1 for r in selected if r["theme"] in PAYLOAD)
    laundered = sum(1 for r in selected if r.get("source"))
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
        "laundered_count": laundered,
        "specimens": [{k: r[k] for k in ("id", "date", "category", "title", "theme", "source")}
                      for r in selected],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"latest_specimens.json: {len(selected)} specimens ({payload_n} payload / "
          f"{len(selected) - payload_n} filler; {laundered} with a traced source), "
          f"{skipped} smear withheld; latest #{selected[0]['id']} {selected[0]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
