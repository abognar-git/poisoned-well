#!/usr/bin/env python3
"""Capture recent article specimens from documented Hungary-targeting pro-Kremlin
sources, with the laundering source behind each Pravda-mirror item.

Run SERVER-SIDE ONLY (locally / in CI) — never from a visitor's browser — so the
site can show live evidence of ongoing output without any visitor's browser (or
referrer) touching a propaganda domain, and without feeding its inbound-link/SEO
signal. Output: data/derived/latest_specimens.json with a captured_at timestamp.

Sources (a small, attributed registry — see SOURCES):
  - pravda-hu    : hungary.news-pravda.com  (Portal Kombat / Pravda network; launderer)
  - newsfront-hu : hu.news-front.su         (News Front, Crimea-based, EU/US-sanctioned; outlet)

Editorial rules baked in:
  - EVIDENCE, not endorsement; the site never hyperlinks the article or its source
  - SKIP any headline that reads as a personal smear (defamation is not republished)
  - theme tags are a crude, disclosed keyword heuristic on TOPIC, not a judgement of intent
  - a source's own attribution is stated per specimen; on fetch failure the last good
    file is left untouched (do not overwrite with garbage)
"""

import html
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived" / "latest_specimens.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
FEATURED = 8          # newest items shown on the story page
MIN_PAYLOAD = 2       # guarantee at least this many recent payload items among featured
CORPUS_CAP = 90       # cap on the searchable corpus
TRACE_CAP = 70        # max article pages fetched per run to trace laundering sources

SMEAR = re.compile(r"\b(pedophil|paedophil|p[aä]edo|rapist|rape|molest|traffick|"
                   r"epstein|blackmail|corrupt(?:ion)? charges?)\b", re.I)

THEMES = [
    ("hungary",  r"hungar|orb[aá]n|budapest|magyar|fidesz|tisza"),
    ("ukraine",  r"ukrain|kyiv|kiev|zelensk|donbas|kharkiv|odes[sa]a?\b|ukrajn"),
    ("russia",   r"russia|putin|kremlin|moscow|lavrov|ria novosti|\btass\b|sputnik|gazprom|rosatom|oroszorsz"),
    ("eu/nato",  r"\beu\b|europe|brussels|von der leyen|\bnato\b|sanction|baltic|migrant|migration|brusszel|eur[oó]pai"),
    ("energy",   r"\bgas\b|\boil\b|pipeline|nord stream|druzhba|turkstream|energy|energia|olaj|g[aá]z"),
]
PAYLOAD = {"hungary", "ukraine", "russia", "eu/nato", "energy"}

SOCIAL = {"t.me": "Telegram", "telegram.me": "Telegram", "max.ru": "MAX",
          "vk.com": "VK", "ok.ru": "OK", "dzen.ru": "Dzen"}
OUTLETS = [(r"tass\.", "TASS"), (r"ria\.", "RIA Novosti"), (r"news-front", "News Front"),
           (r"topwar", "Topwar"), (r"sputnik", "Sputnik"), (r"\brt\.com", "RT"),
           (r"gazeta\.", "Gazeta.ru"), (r"telegra\.ph", "Telegraph"), (r"rbc\.", "RBC"),
           (r"lenta\.", "Lenta.ru"), (r"news-pravda", "another Pravda mirror")]

SOURCES = {
    "pravda-hu": {
        "label": "Pravda network",
        "lang": "en",
        "attribution": "Russia — Portal Kombat / Pravda network (VIGINUM); a laundering mirror",
        "kind": "launderer",
        "base": "https://hungary.news-pravda.com",
        "listings": ["/en/", "/en/hungary/", "/en/russia/", "/en/ukraine/", "/en/world/", "/en/eu/"],
        "link": re.compile(
            r'<a[^>]*href="(https://hungary\.news-pravda\.com/en/([a-z-]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html)"[^>]*>(.*?)</a>',
            re.S),
    },
    "newsfront-hu": {
        "label": "News Front",
        "lang": "hu",
        "attribution": "Russia — News Front, Crimea-based, EU/US-sanctioned; a primary outlet",
        "kind": "outlet",
        "base": "https://hu.news-front.su",
        "listings": ["/"],
        "link": re.compile(
            r'<a[^>]*href="(https://hu\.news-front\.su/(\d{4})/(\d{2})/(\d{2})/([^"/]+)/?)"[^>]*>(.*?)</a>',
            re.S),
    },
}

SRC = re.compile(r'data-source-url="([^"]+)"')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(inner: str) -> str:
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", inner))).strip()
    t = re.sub(r"^\d{1,2}:\d{2}\s+", "", t)  # strip leading "HH:MM" timestamp artifacts
    return t


def title_from_slug(slug: str) -> str:
    t = slug.replace("-", " ").strip()
    return t[:1].upper() + t[1:] if t else t


def classify(title: str) -> str:
    hay = title.lower()
    for name, pat in THEMES:
        if re.search(pat, hay):
            return name
    return "filler"


def parse_source(page: str):
    m = SRC.search(page)
    if not m:
        return None
    url = m.group(1)
    host = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", url).lower()
    path = [p for p in re.sub(r"^https?://[^/]+", "", url).split("/") if p and not p.startswith("@")]
    social = next((v for k, v in SOCIAL.items() if host == k or host.endswith("." + k)), None)
    if social:
        return {"platform": social, "channel": path[0].lstrip("@") if path else None}
    outlet = next((label for pat, label in OUTLETS if re.search(pat, host)), host)
    return {"platform": outlet, "channel": None}


def harvest(sid: str, cfg: dict):
    rows, seen = [], set()
    for path in cfg["listings"]:
        try:
            page = fetch(cfg["base"] + path)
        except Exception:
            continue
        for m in cfg["link"].finditer(page):
            g = m.groups()
            if sid == "pravda-hu":
                url, cat, y, mo, d, aid, inner = g
                aid = int(aid)
            else:  # newsfront-hu: date + slug, no numeric id/category
                url, y, mo, d, slug, inner = g
                cat, aid = "news-front", None  # slugs carry no reliable numeric id
            title = clean(inner)
            if sid == "newsfront-hu" and (len(title) < 12 or title == title.lower()):
                title = title_from_slug(slug)  # fall back to the URL slug, capitalised
            if url in seen or len(title) < 12 or SMEAR.search(title):
                continue
            seen.add(url)
            rows.append({"site": sid, "id": aid, "date": f"{y}-{mo}-{d}", "category": cat,
                         "title": title[:190], "theme": classify(title), "url": url})
        time.sleep(0.3)
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return rows


def main() -> int:
    all_rows = []
    ok_sources = []
    for sid, cfg in SOURCES.items():
        rows = harvest(sid, cfg)
        if rows:
            ok_sources.append(sid)
            all_rows.extend(rows)
    if not all_rows:
        raise SystemExit("no source reachable — leaving last good file untouched")

    # sort by date, then Pravda's numeric id (News Front id is None -> 0) for stable recency
    sortkey = lambda r: (r["date"], r["id"] or 0)
    all_rows.sort(key=sortkey, reverse=True)

    # de-dup by URL (unique); News Front ids are not unique
    seen, corpus = set(), []
    for r in all_rows:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        corpus.append(r)
    corpus = corpus[:CORPUS_CAP]

    # featured: newest few, but guarantee each source AND a couple of payload items appear
    featured = list(corpus[:FEATURED])
    keys = {r["url"] for r in featured}
    for sid in ok_sources:  # source diversity: show every captured source
        if not any(r["site"] == sid for r in featured):
            extra = next((r for r in corpus if r["site"] == sid and r["url"] not in keys), None)
            if extra:
                featured.append(extra); keys.add(extra["url"])
    pcount = sum(1 for r in featured if r["theme"] in PAYLOAD)
    for r in corpus:
        if pcount >= MIN_PAYLOAD:
            break
        if r["url"] not in keys and r["theme"] in PAYLOAD:
            featured.append(r); keys.add(r["url"]); pcount += 1
    featured.sort(key=sortkey, reverse=True)
    feat_urls = {r["url"] for r in featured}

    # trace the laundering source for launderer items — featured first, then the rest
    # of the corpus, bounded by TRACE_CAP article fetches per run
    traced = 0
    for r in featured + [r for r in corpus if r["url"] not in feat_urls]:
        if SOURCES[r["site"]]["kind"] != "launderer" or traced >= TRACE_CAP:
            continue
        try:
            r["source"] = parse_source(fetch(r["url"]))
        except Exception:
            r["source"] = None
        traced += 1
        time.sleep(0.3)

    latest_day = corpus[0]["date"]
    today_live = sum(1 for r in corpus if r["date"] == latest_day)
    smear_skipped = 0  # counted implicitly (skipped in harvest); reported as best-effort

    def strip(r):
        return {k: r.get(k) for k in ("site", "id", "date", "category", "title", "theme", "source")}

    out = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Unaltered specimens from documented pro-Kremlin sources, shown as evidence of ongoing "
                 "output. Not endorsed, not linked. Personal-smear items are withheld and documented as "
                 "debunked evidence in the case files."),
        "theme_note": ("Theme tags are a crude keyword match on the headline (THEMES in "
                       "scripts/capture_specimens.py) separating geopolitical payload from mundane camouflage "
                       "— a heuristic on topic, not a judgement of intent."),
        "sources": {sid: {"label": SOURCES[sid]["label"], "lang": SOURCES[sid]["lang"],
                          "attribution": SOURCES[sid]["attribution"], "kind": SOURCES[sid]["kind"]}
                    for sid in ok_sources},
        "latest_day": latest_day,
        "today_live_count": today_live,
        "corpus_count": len(corpus),
        "featured": [strip(r) for r in featured],
        "corpus": [strip(r) for r in corpus if r["url"] not in feat_urls],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    by = {sid: sum(1 for r in corpus if r["site"] == sid) for sid in ok_sources}
    print(f"latest_specimens.json: {len(corpus)} specimens across {ok_sources} {by}; "
          f"{len(featured)} featured; latest_day {latest_day} ({today_live} live)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
