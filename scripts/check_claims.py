#!/usr/bin/env python3
"""Gate: every factual claim shown on the site must be backed by evidence.

Checks:
  - claims.json entries: unique ids, claim text, status in enum, >=1 support;
    source supports need a URL, data supports need an existing data_ref file
  - site/prototype/index.html: every data-claim="<id>" references a registry
    entry (error), and every registry entry is used on the page (warning)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "catalog" / "claims.json"
GLOSSARY = ROOT / "catalog" / "glossary.json"
INCIDENTS = ROOT / "catalog" / "incidents.json"
AI_INCIDENTS = ROOT / "catalog" / "ai_incidents.json"
CATALOG = ROOT / "catalog" / "operations.json"
AI_PHASES = {"campaign", "post-campaign", "ongoing"}
AI_TYPES = {"deepfake-video", "deepfake-audio", "ai-image", "ai-text", "ai-persona",
            "llm-grooming", "ai-tooling", "other"}
PAGES = [ROOT / "site" / "prototype" / "index.html",
         ROOT / "site" / "prototype" / "explorer.html"]
STATUSES = {"verified", "live-data", "assessment"}

# The site never hyperlinks propaganda infrastructure: a link leaks the reader's
# referrer to the adversary and feeds its inbound-link signal. Citing an operation
# means citing the researchers who documented it, or our own generated data — never
# the operation's own page. This gate exists because we broke the rule once.
BLOCKED_HOSTS = re.compile(
    r"://[^/]*\b("
    r"news-pravda\.com|pravda-[a-z]{2}\.com|news-front\.su|newsfront\.info|"
    r"rt\.com|sputnik(?:news)?\.[a-z]+|tass\.ru|ria\.ru|"
    r"southfront\.|strategic-culture\.|geopolitika\.ru|t\.me"
    r")", re.I)
CATALOGS_TO_SCAN = ["claims.json", "operations.json", "glossary.json",
                    "incidents.json", "ai_incidents.json"]


def main() -> int:
    claims = json.loads(CLAIMS.read_text())
    errors, warnings = [], []

    ids = [c.get("id", "?") for c in claims]
    if len(ids) != len(set(ids)):
        errors.append("duplicate claim ids")

    for c in claims:
        cid = c.get("id", "?")
        if not c.get("claim"):
            errors.append(f"{cid}: empty claim text")
        if c.get("status") not in STATUSES:
            errors.append(f"{cid}: bad status {c.get('status')!r}")
        supports = c.get("support", [])
        if not supports:
            errors.append(f"{cid}: no support")
        for s in supports:
            if s.get("type") == "source" and not s.get("url"):
                errors.append(f"{cid}: source support without url")
            elif s.get("type") == "data":
                ref = s.get("data_ref", "")
                if not (ROOT / ref).exists():
                    errors.append(f"{cid}: data_ref missing on disk: {ref}")
            elif s.get("type") not in {"source", "data"}:
                errors.append(f"{cid}: bad support type {s.get('type')!r}")

    if GLOSSARY.exists():
        gloss = json.loads(GLOSSARY.read_text())
        gids = [g.get("id", "?") for g in gloss]
        if len(gids) != len(set(gids)):
            errors.append("glossary: duplicate ids")
        for g in gloss:
            if not g.get("term") or not g.get("definition"):
                errors.append(f"glossary {g.get('id', '?')}: missing term or definition")
            if "source" in g and not g["source"].get("url"):
                errors.append(f"glossary {g.get('id', '?')}: source without url")
        print(f"{len(gloss)} glossary terms")

    if INCIDENTS.exists():
        incidents = json.loads(INCIDENTS.read_text())
        case_ids = {c["id"] for c in json.loads(CATALOG.read_text())}
        iids = [i.get("id", "?") for i in incidents]
        if len(iids) != len(set(iids)):
            errors.append("incidents: duplicate ids")
        for i in incidents:
            iid = i.get("id", "?")
            if not i.get("date") or not i.get("text"):
                errors.append(f"incident {iid}: missing date or text")
            if i.get("case") not in case_ids:
                errors.append(f"incident {iid}: case '{i.get('case')}' not in catalog")
            if not (i.get("source") or {}).get("url"):
                errors.append(f"incident {iid}: source without url")
        print(f"{len(incidents)} campaign incidents (all case-linked)")

    if AI_INCIDENTS.exists():
        ai = json.loads(AI_INCIDENTS.read_text())
        aids = [a.get("id", "?") for a in ai]
        if len(aids) != len(set(aids)):
            errors.append("ai_incidents: duplicate ids")
        for a in ai:
            aid = a.get("id", "?")
            if not a.get("date") or not a.get("title"):
                errors.append(f"ai_incident {aid}: missing date or title")
            if a.get("phase") not in AI_PHASES:
                errors.append(f"ai_incident {aid}: bad phase {a.get('phase')!r}")
            if a.get("ai_type") not in AI_TYPES:
                errors.append(f"ai_incident {aid}: bad ai_type {a.get('ai_type')!r}")
            if not (a.get("source") or {}).get("url"):
                errors.append(f"ai_incident {aid}: source without url")
        from collections import Counter
        ph = Counter(a["phase"] for a in ai)
        print(f"{len(ai)} AI-usage incidents ({dict(ph)})")

    # no catalog entry may carry a URL pointing at propaganda infrastructure
    for name in CATALOGS_TO_SCAN:
        f = ROOT / "catalog" / name
        if not f.exists():
            continue
        for m in re.finditer(r'"url"\s*:\s*"([^"]+)"', f.read_text()):
            if BLOCKED_HOSTS.search(m.group(1)):
                errors.append(f"{name}: cites propaganda infrastructure directly: {m.group(1)} "
                              f"— cite the researchers or our generated data instead")

    used = set()
    for page in PAGES:
        if not page.exists():
            continue
        html = page.read_text()
        used |= set(re.findall(r'data-claim="([a-z0-9-]+)"', html))
    # every inline term affordance must resolve to a glossary entry, or the reader gets
    # a dotted underline that explains nothing — same contract as data-claim
    gloss_ids = {t.get("id") for t in json.loads(GLOSSARY.read_text())}
    terms_used = set()
    for page in PAGES:
        if page.exists():
            terms_used |= set(re.findall(r'data-term="([a-z0-9-]+)"', page.read_text()))
    for t in sorted(terms_used - gloss_ids):
        errors.append(f"page references unknown glossary term: {t}")
    if terms_used:
        print(f"{len(terms_used)} inline term definitions, all resolving")

    unknown = used - set(ids)
    unused = set(ids) - used
    for u in sorted(unknown):
        errors.append(f"page references unknown claim id: {u}")
    for u in sorted(unused):
        warnings.append(f"registry claim not used on any page: {u}")

    print(f"{len(claims)} claims | {len(used)} used on pages | "
          f"{sum(1 for c in claims if c['status'] == 'verified')} verified, "
          f"{sum(1 for c in claims if c['status'] == 'live-data')} live-data, "
          f"{sum(1 for c in claims if c['status'] == 'assessment')} assessment")
    for w in warnings:
        print(f"  warn: {w}")
    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
