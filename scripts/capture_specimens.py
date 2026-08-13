#!/usr/bin/env python3
"""Capture recent specimens from documented Hungary-targeting pro-Kremlin sources,
modelled as a three-tier ecosystem, with the laundering source behind mirror items.

Run SERVER-SIDE ONLY (locally / in CI) — never from a visitor's browser — so the site
can show live evidence of ongoing output without any visitor's browser (or referrer)
touching a propaganda domain, and without feeding inbound-link/SEO signal. Output:
data/derived/latest_specimens.json with a captured_at timestamp.

Tiers (the documented laundering ecosystem):
  origin    — Telegram channels where content starts (via public t.me/s/ previews).
              These are the top feeders credited by the Pravda mirror's own articles.
  launderer — the Pravda / Portal Kombat network mirror, which republishes origins as "news".
  outlet    — primary propaganda sites (News Front: Crimea-based; US-sanctioned outlet, EU-sanctioned owner).

Editorial rules baked in:
  - EVIDENCE, not endorsement; the site never hyperlinks an article, post or source
  - SKIP any item that reads as a personal smear (defamation is not republished)
  - theme tags are a crude, disclosed keyword heuristic on TOPIC, not a judgement of intent
  - each source's attribution + tier is stated; on total fetch failure the last good file
    is left untouched (do not overwrite with garbage)
"""

import html
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived" / "latest_specimens.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
FEATURED = 9
MIN_PAYLOAD = 2
PER_SOURCE_CAP = 26   # keep any single source from dominating the corpus
CORPUS_CAP = 130
TRACE_CAP = 60        # max article pages fetched to trace laundering sources

# Personal-smear filter: these specimens are withheld from the site entirely and
# left to the case files. Stems are PREFIX matches (\w*) — an earlier version ended
# the group with \b, which meant "pedophil" failed to match "pedophilia"/"pedophile"
# and only the exact-word alternatives ever fired. Covers en/hu/ru because the
# origin and outlet tiers publish in Hungarian and Russian, which is exactly where
# fabricated personal defamation lands. See tests/test_smear.py.
SMEAR = re.compile(
    r"\b("
    r"p[ae]?edophil\w*|p[aä]?edo\w*|rapist\w*|rape[ds]?\b|molest\w*|traffick\w*|"
    r"epstein|blackmail\w*|corrupt(?:ion)?\s+charges?|"
    r"pedof[ií]l\w*|er[oő]szakol\w*|zsarol\w*|megront\w*|korrupci[oó]s\s+v[aá]d\w*|"
    r"педофил\w*|изнасил\w*|шантаж\w*|растлен\w*"
    r")", re.I)

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
        "label": "Pravda network", "tier": "launderer", "type": "pravda", "lang": "en",
        "attribution": "Russia — Portal Kombat / Pravda network (VIGINUM); a laundering mirror",
        "base": "https://hungary.news-pravda.com",
        "listings": ["/en/", "/en/hungary/", "/en/russia/", "/en/ukraine/", "/en/world/", "/en/eu/"],
        "link": re.compile(
            r'<a[^>]*href="(https://hungary\.news-pravda\.com/en/([a-z-]+)/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html)"[^>]*>(.*?)</a>',
            re.S),
    },
    # Four Russian-language outlets the mirror credits (2.6% of its articles between them).
    # Each carries a sourced glossary entry; the attribution strings below say exactly who or
    # what is designated, because owner, parent and outlet are different facts and the
    # registers distinguish them even when reporting does not.
    "rt-ru": {
        "label": "RT (Russian service)", "tier": "outlet", "type": "cards", "lang": "ru",
        "attribution": "Russia — RT, operated by ANO TV-Novosti: the operating entity is under EU, UK and US asset freezes; the EU's broadcasting suspension names other RT services, not this one",
        "base": "https://russian.rt.com", "listings": ["/"], "section": "rt",
        "link": re.compile(r'href="(/[a-z-]+/(?:article|news)/\d+-[a-z0-9-]+)"'),
    },
    "ukraina-ru": {
        "label": "Ukraina.ru", "tier": "outlet", "type": "cards", "lang": "ru",
        "attribution": "Russia — Ukraina.ru, a project of the state agency Rossiya Segodnya; the designations attach to the parent group, not to this outlet by name",
        "base": "https://ukraina.ru", "listings": ["/"], "section": "ukraina",
        "link": re.compile(r'href="(?:https://ukraina\.ru)?(/(\d{4})(\d{2})(\d{2})/[a-z0-9-]+\.html)"'),
        "date_from": lambda m: f"{m.group(2)}-{m.group(3)}-{m.group(4)}",
    },
    "zvezda-tv": {
        "label": "Zvezda", "tier": "outlet", "type": "cards", "lang": "ru",
        "attribution": "Russia — Zvezda, the Ministry of Defence television channel; its operating company is under an EU asset freeze and the outlet is in the EU broadcasting-suspension annex",
        "base": "https://tvzvezda.ru", "listings": ["/"], "section": "zvezda",
        "link": re.compile(r'href="(?:https://tvzvezda\.ru)?(/news/(\d{4})(\d{1,2})(\d{2})\d{4}-\w+\.html)"'),
        "date_from": lambda m: f"{m.group(2)}-{int(m.group(3)):02d}-{int(m.group(4)):02d}",
    },
    "tsargrad": {
        "label": "Tsargrad TV", "tier": "outlet", "type": "cards", "lang": "ru",
        "attribution": "Russia — Tsargrad TV: the channel itself is under an EU asset freeze, its operator and parent under US designations, and its owner Konstantin Malofeev separately designated",
        "base": "https://tsargrad.tv", "listings": ["/"], "section": "tsargrad",
        "link": re.compile(r'href="(?:https://tsargrad\.tv)?(/news/[a-z0-9-]+_\d+)"'),
    },
    # News Front's Hungarian subdomain has been timing out at network level while the
    # Russian-language root answers normally and uses the identical /YYYY/MM/DD/slug/
    # shape. Same entity, same sanctions record, and the mirror credits both — so the
    # root keeps the outlet tier represented while hu.* is unreachable, and hu.* stays
    # configured so the panel keeps reporting its absence rather than forgetting it.
    "newsfront-ru": {
        "label": "News Front", "tier": "outlet", "type": "newsfront", "lang": "ru",
        "attribution": "Russia — News Front, Crimea-based; the outlet is US-sanctioned and its owner EU/Canada/US-sanctioned; a primary outlet",
        "base": "https://news-front.su",
        "listings": ["/"],
        "link": re.compile(
            r'<a[^>]*href="(https://news-front\.su/(\d{4})/(\d{2})/(\d{2})/([^"/]+)/?)"[^>]*>(.*?)</a>',
            re.S),
    },
    "newsfront-hu": {
        "label": "News Front", "tier": "outlet", "type": "newsfront", "lang": "hu",
        "attribution": "Russia — News Front, Crimea-based; the outlet is US-sanctioned and its owner EU/Canada/US-sanctioned; a primary outlet",
        "base": "https://hu.news-front.su",
        "listings": ["/"],
        "link": re.compile(
            r'<a[^>]*href="(https://hu\.news-front\.su/(\d{4})/(\d{2})/(\d{2})/([^"/]+)/?)"[^>]*>(.*?)</a>',
            re.S),
    },
}
# Telegram origin channels — the Pravda mirror's own top-credited feeders, captured via
# the public t.me/s/ preview. Documented as pro-Kremlin laundering origins in our own data.
TELEGRAM = {
    "tg-oroszigazsag": ("oroszokazigazsagoldalan", "the Russians' truth side"),
    "tg-greatawaken":  ("greatawakeningmagyarok", "Great Awakening Magyars"),
    "tg-ebredes":      ("ebredes2017", "Awakening 2017"),
    "tg-rybar":        ("Rybar_HU", "Rybar — GRU-adjacent milblogger (HU)"),
    # The mirror's own credit counts decide what belongs here. Ranks are against the
    # 939 sources in its topSources list; the share is of all 139,623 articles.
    "tg-oroszkatonai": ("oroszspecialiskatonaihadmuvelet",
                        "\u201cRussian special military operation\u201d"),   # #4  5.1%
    "tg-infodef":      ("InfoDefMagyarok", "InfoDefense franchise, HU"),      # #6  4.8%
    "tg-vilaghelyzete": ("VilagHelyzeteBlog", "\u201cState of the world\u201d blog"),  # #8  2.2%
    # Network-level feeders rather than this mirror's: kept because they show the same
    # content arriving through the wider Pravda ecosystem, but they are minor here and
    # the labels should not imply otherwise — lomovkaa #13 (0.9%), baltnews #37 (0.3%),
    # zvezda_analytics #82 (0.1%).
    "tg-baltnews":     ("baltnews", "Baltnews — Baltic Rossiya Segodnya brand"),
    "tg-lomovka":      ("lomovkaa", "Lomovka"),
    "tg-zvezda":       ("zvezda_analytics", "Zvezda Analytics — MoD-linked"),
}
for sid, (chan, label) in TELEGRAM.items():
    SOURCES[sid] = {
        "label": label, "tier": "origin", "type": "telegram", "lang": "hu/ru", "channel": chan,
        "attribution": f"Russia-aligned Telegram channel (@{chan}) — a documented laundering origin",
        "base": "https://t.me", "listings": [f"/s/{chan}"],
    }

SRC = re.compile(r'data-source-url="([^"]+)"')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(inner: str) -> str:
    """Strip markup from captured HTML and normalise whitespace.

    Order matters and was wrong here. Stripping tags BEFORE unescaping means a source
    page containing &lt;img src=x onerror=...&gt; survives the strip as literal text and
    is then unescaped back into live markup. Unescape first, strip second, then remove
    any angle brackets that remain — everything this function touches is written by the
    operations we document, so it is hostile input by definition.
    """
    t = html.unescape(inner)
    t = re.sub(r"<[^>]*>", " ", t)          # markup, including anything unescaping revealed
    t = t.replace("<", " ").replace(">", " ")  # stray brackets from truncated tags
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^\d{1,2}:\d{2}\s+", "", t)


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


def harvest_web(sid, cfg):
    rows, seen, errs = [], set(), []
    for path in cfg["listings"]:
        try:
            page = fetch(cfg["base"] + path)
        except Exception as e:
            errs.append(f"{type(e).__name__}")
            continue
        for m in cfg["link"].finditer(page):
            g = m.groups()
            if cfg["type"] == "pravda":
                url, cat, y, mo, d, aid, inner = g
                aid = int(aid)
            else:
                url, y, mo, d, slug, inner = g
                cat, aid = "news-front", None
            title = clean(inner)
            if cfg["type"] == "newsfront":
                title = re.sub(r"^\d{1,2}:\d{2}\s*", "", title)   # listing rows lead with a clock
                if len(title) < 12 or title == title.lower():
                    title = title_from_slug(slug)
            if url in seen or len(title) < 12 or SMEAR.search(title):
                continue
            seen.add(url)
            rows.append({"site": sid, "id": aid, "date": f"{y}-{mo}-{d}", "category": cat,
                         "title": title[:190], "theme": classify(title), "url": url})
        time.sleep(0.3)
    if not rows:
        PROBLEMS[sid] = (f"unreachable ({'/'.join(sorted(set(errs)))})" if errs
                         else "reachable, but no article links matched")
    return rows


# ── outlets whose listing does not put the headline inside the anchor ──────────
# News Front hands us <a href=...>headline</a>. These four do not: the link and its
# headline sit in separate elements of a card, so the title is taken from the first
# Cyrillic run after the link. Measured coverage on the front page: RT 87/87,
# Ukraina.ru 52/57, Zvezda 45/48, Tsargrad 10/10.
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

CYRILLIC = re.compile(r"[А-ЯЁ]")
TEXT_NODE = re.compile(r">([^<>]{24,200})<")
# listing cards prefix the headline with a rubric and/or a date-time in several shapes:
# "13 Августа 15:34", "Августа 15:34", "Политика 13 Августа 13:43", "15:34"
LEAD_NOISE = re.compile(
    r"^(?:[А-ЯЁа-яё]{3,14}\s+)?(?:\d{1,2}\s+)?[А-ЯЁа-яё]{3,12}\s+\d{1,2}:\d{2}\s*"
    r"|^\d{1,2}\s+[А-ЯЁа-яё]{3,12}\s+\d{1,2}:\d{2}\s*"
    r"|^\d{1,2}:\d{2}\s*")


def harvest_cards(sid, cfg):
    """Link pattern for the URL, nearest following Cyrillic run for the headline."""
    rows, seen = [], set()
    try:
        page = fetch(cfg["base"] + cfg["listings"][0])
    except Exception as e:
        PROBLEMS[sid] = f"unreachable ({type(e).__name__})"
        return rows
    for m in cfg["link"].finditer(page):
        href = m.group(1)
        url = href if href.startswith("http") else cfg["base"] + href
        if url in seen:
            continue
        # Take the first suitable TEXT NODE after the link, not the first Cyrillic run in
        # the stripped window: stripping tags first merges adjacent headlines into one
        # string and lets markup residue through. Element boundaries are the whole point.
        title = None
        for node in TEXT_NODE.findall(page[m.end():m.end() + 900]):
            t = LEAD_NOISE.sub("", re.sub(r"\s+", " ", unescape(node))).strip(" \u2014-–·|,")
            if len(t) >= 24 and CYRILLIC.match(t) and "href=" not in t:
                title = t
                break
        if not title or SMEAR.search(title):
            continue
        seen.add(url)
        d = cfg["date_from"](m) if cfg.get("date_from") else None
        if d:
            try:                      # a malformed date sorts to the top and crowds the corpus
                datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                d = None
        rows.append({"site": sid, "id": None, "date": d or TODAY, "date_is_capture": not d,
                     "category": cfg.get("section", "news"), "title": title[:190],
                     "theme": classify(title), "url": url})
    return rows


def harvest_telegram(sid, cfg):
    """Parse the public t.me/s/<channel> preview: message text, date, post id."""
    rows, seen = [], set()
    try:
        page = fetch(cfg["base"] + cfg["listings"][0])
    except Exception as e:
        PROBLEMS[sid] = f"unreachable ({type(e).__name__})"
        return rows
    for block in re.split(r'tgme_widget_message_wrap', page)[1:]:
        tm = re.search(r'datetime="([^"]+)"', block)
        tx = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
        pid = re.search(r'data-post="([^"]+)"', block)
        if not (tm and tx and pid):
            continue
        title = clean(re.sub(r"https?://\S+", "", tx.group(1)))  # drop bare links
        if len(title) < 25 or SMEAR.search(title):
            continue
        url = "https://t.me/" + pid.group(1)
        if url in seen:
            continue
        seen.add(url)
        rows.append({"site": sid, "id": pid.group(1).split("/")[-1], "date": tm.group(1)[:10],
                     "category": cfg["channel"], "title": title[:190], "theme": classify(title), "url": url})
    return rows


PROBLEMS = {}   # sid -> why nothing came back; surfaced in the JSON and on the page


def harvest(sid, cfg):
    t = cfg["type"]
    rows = (harvest_telegram(sid, cfg) if t == "telegram"
            else harvest_cards(sid, cfg) if t == "cards"
            else harvest_web(sid, cfg))
    if not rows and sid not in PROBLEMS:
        PROBLEMS[sid] = "reachable, but nothing usable after filtering"
    rows.sort(key=lambda r: (r["date"], str(r["id"] or "")), reverse=True)
    return rows[:PER_SOURCE_CAP]


def main() -> int:
    all_rows, ok = [], []
    for sid, cfg in SOURCES.items():
        rows = harvest(sid, cfg)
        if rows:
            ok.append(sid)
            all_rows.extend(rows)
    if not all_rows:
        raise SystemExit("no source reachable — leaving last good file untouched")

    sortkey = lambda r: (r["date"], str(r["id"] or ""))
    all_rows.sort(key=sortkey, reverse=True)
    seen, corpus = set(), []
    for r in all_rows:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        corpus.append(r)
    # The cap used to be a straight truncation of a (date, id)-sorted list, which quietly
    # starved every source without numeric ids: at equal dates their empty id sorted last
    # and the busiest Telegram channels ate the whole allowance. Fill round-robin instead,
    # so the corpus represents the network rather than whichever source posts most.
    per_site = {}
    for r in corpus:
        per_site.setdefault(r["site"], []).append(r)
    balanced, rank = [], 0
    while len(balanced) < CORPUS_CAP and any(len(v) > rank for v in per_site.values()):
        for site in sorted(per_site, key=lambda x: sortkey(per_site[x][0]), reverse=True):
            if rank < len(per_site[site]) and len(balanced) < CORPUS_CAP:
                balanced.append(per_site[site][rank])
        rank += 1
    corpus = sorted(balanced, key=sortkey, reverse=True)

    # featured: round-robin the newest item per source (so one busy Telegram channel
    # can't flood the slate), then fill by recency; still guarantee each TIER and a
    # couple of payload items appear
    by_site = {}
    for r in corpus:
        by_site.setdefault(r["site"], []).append(r)   # corpus is newest-first per site
    featured, keys = [], set()
    rank = 0
    while len(featured) < FEATURED and any(by_site.values()):
        # order sources by the recency of their rank-th item for a stable, fresh slate
        for site in sorted(by_site, key=lambda s: sortkey(by_site[s][0]), reverse=True):
            rows = by_site[site]
            if rank < len(rows) and len(featured) < FEATURED:
                r = rows[rank]
                if r["url"] not in keys:
                    featured.append(r); keys.add(r["url"])
        rank += 1
        if rank > CORPUS_CAP:
            break
    for tier in ("origin", "launderer", "outlet"):
        if not any(SOURCES[r["site"]]["tier"] == tier for r in featured):
            extra = next((r for r in corpus if SOURCES[r["site"]]["tier"] == tier and r["url"] not in keys), None)
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

    # trace the credited laundering source for launderer items, bounded by TRACE_CAP
    traced = 0
    for r in featured + [r for r in corpus if r["url"] not in feat_urls]:
        if SOURCES[r["site"]]["type"] != "pravda" or traced >= TRACE_CAP:
            continue
        try:
            r["source"] = parse_source(fetch(r["url"]))
        except Exception:
            r["source"] = None
        traced += 1
        time.sleep(0.3)

    latest_day = corpus[0]["date"]
    today_live = sum(1 for r in corpus if r["date"] == latest_day)

    def strip(r):
        # date_is_capture must survive into the JSON: without it a row whose listing gave
        # no publication date is indistinguishable from one that did, and the page would
        # be presenting our capture time as the article's date.
        return {k: r.get(k) for k in ("site", "id", "date", "category", "title", "theme",
                                      "source", "date_is_capture") if r.get(k) is not None}

    out = {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Unaltered specimens from documented pro-Kremlin sources across three tiers — Telegram "
                 "origins, the Pravda laundering mirror, and a sanctioned outlet — shown as evidence of ongoing "
                 "output. Not endorsed, not linked. Personal-smear items are withheld and documented as debunked "
                 "evidence in the case files."),
        "theme_note": ("Theme tags are a crude keyword match on the headline (THEMES in "
                       "scripts/capture_specimens.py) separating geopolitical payload from mundane camouflage "
                       "— a heuristic on topic, not a judgement of intent."),
        "sources": {sid: {"label": SOURCES[sid]["label"], "tier": SOURCES[sid]["tier"],
                          "lang": SOURCES[sid]["lang"], "attribution": SOURCES[sid]["attribution"]}
                    for sid in ok},
        "tiers": {"origin": "Telegram channels where content starts",
                  "launderer": "mirror sites that republish origins as 'news'",
                  "outlet": "primary propaganda sites"},
        # A configured source that returns nothing used to disappear silently, which let
        # the panel claim three tiers while serving two. Name it instead: the reader is
        # told which source is missing and why, and tiers_live records what is actually
        # represented in this capture rather than what the design intends.
        "unreachable": {sid: {"label": SOURCES[sid]["label"], "tier": SOURCES[sid]["tier"],
                              "why": why}
                        for sid, why in sorted(PROBLEMS.items())},
        "tiers_live": sorted({SOURCES[sid]["tier"] for sid in ok}),
        "latest_day": latest_day,
        "today_live_count": today_live,
        "corpus_count": len(corpus),
        "featured": [strip(r) for r in featured],
        "corpus": [strip(r) for r in corpus if r["url"] not in feat_urls],
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    by = {sid: sum(1 for r in corpus if r["site"] == sid) for sid in ok}
    for sid, why in sorted(PROBLEMS.items()):
        print(f"  ! {sid} ({SOURCES[sid]['tier']} tier) returned nothing: {why}")
    print(f"latest_specimens.json: {len(corpus)} specimens across {len(ok)} sources {by}; "
          f"{len(featured)} featured; latest_day {latest_day} ({today_live} live)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
