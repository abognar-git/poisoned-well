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
import subprocess
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
# Paths the repo deliberately does not carry: they are fetched by scripts/fetch_pravda.py
# and gitignored, so a claim citing one is verifiable only after a fetch.
FETCHED_NOT_COMMITTED = ("data/raw/",)

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
                if (ROOT / ref).exists():
                    pass
                elif any(ref.startswith(p) for p in FETCHED_NOT_COMMITTED):
                    # data/raw is gitignored: it is fetched from CheckFirst, not carried
                    # in the repo. On a fresh clone these refs are legitimately absent,
                    # so this is a warning — but the path must still look like something
                    # fetch_pravda.py actually produces, or a typo would pass silently.
                    if not re.fullmatch(r"data/raw/pravda/(domains\.json|json/[\w.-]+_viz\.json)", ref):
                        errors.append(f"{cid}: data_ref is not a path fetch_pravda.py produces: {ref}")
                    else:
                        warnings.append(f"{cid}: data_ref not fetched yet ({ref}) "
                                        f"— run scripts/fetch_pravda.py")
                else:
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

    # No catalog entry may carry a URL pointing at propaganda infrastructure, and no
    # page may render one as a link. The key pattern used to be exactly `"url"`, which
    # matched neither `archive_url` nor anything else ending in url — and archive_url is
    # the one catalog field unambiguously rendered as an <a href>, eight of them today.
    # The invariant was enforced over one key name while the field that reaches an
    # anchor sat outside it.
    for name in CATALOGS_TO_SCAN:
        f = ROOT / "catalog" / name
        if not f.exists():
            continue
        for m in re.finditer(r'"[a-z_]*url"\s*:\s*"([^"]+)"', f.read_text()):
            if BLOCKED_HOSTS.search(m.group(1)):
                errors.append(f"{name}: cites propaganda infrastructure directly: {m.group(1)} "
                              f"— cite the researchers or our generated data instead")

    # The render side, which nothing checked. Only href= and src= — matching arbitrary
    # JS string literals would flag the page's own upstream feed URL and half a dozen
    # display strings, and redden the build on a clean tree.
    for page in PAGES:
        if not page.exists():
            continue
        for m in re.finditer(r'(?:href|src)="([^"]+)"', page.read_text()):
            if BLOCKED_HOSTS.search(m.group(1)):
                errors.append(f"{page.name}: renders a link to propaganda infrastructure: "
                              f"{m.group(1)}")

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

    # The research layer, same contract. Every data-research="<id>" must resolve to an
    # entry generated from RESEARCH.md, and every correction must be surfaced somewhere
    # on the page. A correction that quietly stops rendering is the exact failure this
    # project already had once, so it is an error rather than a warning.
    # The claim `fake-outlets-dark` asserts three domains no longer resolve. Domains come
    # back — a lapsed registration gets re-registered, a suspension is lifted — and if one
    # does, the page would go on asserting a dead site that is live again. Fail instead.
    dom_file = ROOT / "data" / "derived" / "domain_status.json"
    if dom_file.exists():
        dom = json.loads(dom_file.read_text())
        if not dom.get("controls_resolved"):
            warnings.append("domain_status.json: control domains failed, last run was inconclusive")
        else:
            back = [d["domain"] for d in dom["domains"] if d["resolves"]]
            if back:
                errors.append(
                    f"fake-outlets-dark says these do not resolve, but they now do: "
                    f"{', '.join(back)} — re-measure and revise the claim before shipping")
            print(f"{len(dom['domains'])} documented fake-outlet domains checked, "
                  f"{len(dom['domains']) - len(back)} still dark "
                  f"(measured {dom['measured_at'][:10]})")

    research_file = ROOT / "data" / "derived" / "research.json"
    if not research_file.exists():
        errors.append("data/derived/research.json missing — run scripts/derive_research.py")
    else:
        record = json.loads(research_file.read_text())
        r_entries = {e["id"]: e for e in record.get("entries", [])}
        r_used = set()
        for page in PAGES:
            if page.exists():
                r_used |= set(re.findall(r'data-research="([a-z0-9-]+)"', page.read_text()))
        for u in sorted(r_used - set(r_entries)):
            errors.append(f"page references unknown research entry: {u}")
        corrections = {i for i, e in r_entries.items() if e["kind"] == "correction"}
        for miss in sorted(corrections - r_used):
            errors.append(f"correction not surfaced on any page: {miss} "
                          f"— every withdrawn claim must be visible where it was made")
        kinds = {}
        for i in r_used & set(r_entries):
            k = r_entries[i]["kind"]
            kinds[k] = kinds.get(k, 0) + 1
        # Every correction is cited by commit, and four of the five cited a hash that
        # no longer exists: a history rewrite that changed the git identity orphaned
        # the originals, leaving the retraction record pointing at objects a clone
        # cannot resolve — and that github.com served only until its next GC, with the
        # author's personal email on the page. The correction record is this project's
        # central asset; a citation that does not resolve is not a citation.
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True, cwd=ROOT).stdout.strip()
        for e in r_entries.values():
            sha = e.get("commit")
            if not sha:
                continue
            if shallow == "true":
                print(f"  shallow clone — cannot verify {sha} is reachable")
                continue
            ok = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                                capture_output=True, cwd=ROOT).returncode == 0
            if not ok:
                errors.append(
                    f"{e['id']} cites commit {sha}, which is not an ancestor of HEAD. "
                    "A rewritten history orphans the hash a correction points at; "
                    "re-point it at the surviving commit with the same tree.")

        print(f"{len(r_entries)} research entries from RESEARCH.md | {len(r_used)} marked on pages "
              f"({', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))})")

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
