#!/usr/bin/env python3
"""Generate data/derived/network_graph.json for the Act II 3D network scene.

Nodes and edges are derived mechanically from catalog/operations.json:
  sponsor --sponsors--> actor --runs--> operation --on--> platform
                                       operation --targets--> country

The only hand-authored piece is ACTOR_MAP below: a reviewable normalization of
each entry's attribution to canonical actor node(s) (the same operation is named
differently across entries — Storm-1516 = CopyCop etc., see catalog/glossary.json).
Layout is a seeded 3D Fruchterman-Reingold embedding, computed here so the site
ships no layout code. It is reproducible on one machine but NOT bit-for-bit across
architectures: 600 iterations of a chaotic force simulation amplify float
differences past the third decimal. So the coordinates are a rendering detail and
are excluded from any drift check — what must not drift is the structure, and
`--check` compares exactly that: the node set, their types, and the link set,
re-derived from the catalog against what is committed.

    python3 scripts/build_network.py            # regenerate
    python3 scripts/build_network.py --check    # structure only, for CI
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived"

# entry id -> canonical actor ids (see glossary for alias reasoning)
ACTOR_MAP = {
    "pravda-hungary": ["pravda-network"],
    "llm-grooming-measurement": ["pravda-network"],
    "storm-1516-hungary-2026": ["storm-1516"],
    "copycop-infrastructure": ["storm-1516"],
    "matryoshka-hungary-2026": ["matryoshka"],
    "sda-gru-hungary-2026": ["sda-structura", "gru"],
    "openai-doppelganger-ai-use": ["doppelganger"],
    "openai-bad-grammar": ["bad-grammar"],
    "fidesz-ai-campaign-2026": ["fidesz-megafon"],
    "tiktok-ai-network-hungary-2026": ["unknown-operator"],
    "slovakia-2023-deepfake": ["unknown-operator"],
    "romania-2024-2025-elections": ["romania-networks"],
    "apt-crossover-hungary": ["apt28", "apt29"],
    "newsfront-hungary": ["news-front"],
    "telegram-laundering-hungary-2026": ["telegram-network"],
    "effectiveness-evidence": [],
    "telex-ai-video-audit-2026": [],
    "tisza-volunteer-ai-songs": ["lone-volunteer"],
    "kesma-county-ai-image-line-2026": ["kesma-press"],
    "nem-ai-ad-blitz-2025": ["nem-movement"],
    "nem-a-mi-haborunk-ads-2026": ["unknown-operator"],
    "wellor-ai-music": ["unknown-operator"],
    "spottle-attache-briefings": ["gru"],
    # the convergence case links BOTH production lines — that is the finding,
    # and the graph should show two operators arriving at one frame independently
    "conscription-frame-convergence-2026": ["storm-1516", "nem-movement"],
}

ACTORS = {  # id -> (label, sponsor, glossary id or None)
    "pravda-network": ("Pravda network", "Russia", "pravda-network"),
    "storm-1516": ("Storm-1516 / CopyCop", "Russia", "storm-1516"),
    "matryoshka": ("Matryoshka / Overload", "Russia", "matryoshka"),
    "sda-structura": ("SDA / Structura", "Russia", "sda"),
    "doppelganger": ("Doppelgänger", "Russia", "doppelganger"),
    "gru": ("GRU", "Russia", None),
    "apt28": ("APT28", "Russia", None),
    "apt29": ("APT29", "Russia", None),
    "bad-grammar": ("Bad Grammar", "Russia", None),
    "fidesz-megafon": ("Fidesz-aligned machine", "domestic (HU)", "megafon"),
    "unknown-operator": ("Unattributed operators", "unattributed", None),
    "romania-networks": ("Romanian TikTok networks", "contested", None),
    "news-front": ("News Front", "Russia", "news-front"),
    "telegram-network": ("pro-Orbán Telegram network", "contested", None),
    "nem-movement": ("National Resistance Movement", "domestic (HU)", "nem"),
    "kesma-press": ("KESMA county press", "domestic (HU)", None),
    "lone-volunteer": ("Unfunded volunteer", "none", None),
}

# operated-by relations between canonical actors
ACTOR_LINKS = [("sda-structura", "doppelganger"), ("sda-structura", "matryoshka")]

PLATFORM_NORM = {
    "facebook ads": "Facebook", "facebook": "Facebook", "instagram": "Facebook",
    "fake news websites": "fake news sites", "fake sites": "fake news sites",
    "web": "open web", "wikipedia": "open web",
    "x": "X", "9gag": "X", "telegram": "Telegram", "vk": "Telegram",
    "tiktok": "TikTok", "youtube": "YouTube", "reddit": "X",
    "posters/print": None, "50+ platforms": None, "multiple": None,
}

# The scene is Hungary and its immediate neighbourhood. Kept case files may target
# more countries than this (CopyCop and Doppelganger both run far wider) and their
# dossiers still state the full scope — this only bounds what the graph draws, so a
# regional story doesn't render as a world map.
REGION = {"Hungary", "Austria", "Slovakia", "Ukraine", "Romania", "Serbia", "Croatia", "Slovenia"}


def spring_layout(nodes, links, iters=600, seed=42):
    rnd = random.Random(seed)
    pos = {n: [rnd.uniform(-1, 1) for _ in range(3)] for n in nodes}
    adj = [(l["s"], l["t"]) for l in links]
    k = 1.1 / math.sqrt(max(len(nodes), 1)) * 3.1
    for it in range(iters):
        temp = .12 * (1 - it / iters) + .005
        disp = {n: [0.0, 0.0, 0.0] for n in nodes}
        ids = list(nodes)
        for i, a in enumerate(ids):          # repulsion
            for b in ids[i + 1:]:
                d = [pos[a][x] - pos[b][x] for x in range(3)]
                dist = max(math.sqrt(sum(v * v for v in d)), .01)
                f = k * k / dist
                for x in range(3):
                    disp[a][x] += d[x] / dist * f
                    disp[b][x] -= d[x] / dist * f
        for a, b in adj:                     # attraction
            d = [pos[a][x] - pos[b][x] for x in range(3)]
            dist = max(math.sqrt(sum(v * v for v in d)), .01)
            f = dist * dist / k
            for x in range(3):
                disp[a][x] -= d[x] / dist * f
                disp[b][x] += d[x] / dist * f
        for n in nodes:
            dl = max(math.sqrt(sum(v * v for v in disp[n])), .001)
            for x in range(3):
                pos[n][x] += disp[n][x] / dl * min(dl, temp)
    # center, then scale by the 88th-percentile radius so a few outliers don't
    # shrink the whole cluster into the middle of the frame
    cen = [sum(pos[n][x] for n in nodes) / len(nodes) for x in range(3)]
    for n in nodes:
        for x in range(3):
            pos[n][x] -= cen[x]
    radii = sorted(math.sqrt(sum(v * v for v in pos[n])) for n in nodes)
    scale = radii[int(len(radii) * 0.88)] or 1
    return {n: [round(v / scale, 3) for v in pos[n]] for n in nodes}


def main(check: bool = False) -> int:
    cases = json.loads((ROOT / "catalog" / "operations.json").read_text())
    nodes, links = {}, []

    def add(nid, label, ntype, **extra):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": label, "type": ntype, **extra}

    for aid, (label, sponsor, gloss) in ACTORS.items():
        add(aid, label, "actor", gloss=gloss)
        sid = "sp-" + sponsor.replace(" ", "-")
        add(sid, sponsor, "sponsor")
        links.append({"s": sid, "t": aid, "kind": "sponsors"})
    for a, b in ACTOR_LINKS:
        links.append({"s": a, "t": b, "kind": "operates"})

    for c in cases:
        eid = c["id"]
        add(eid, c["name"] if len(c["name"]) < 42 else c["name"][:39] + "…",
            "operation", case=eid, category=c["category"])
        for aid in ACTOR_MAP.get(eid, []):
            links.append({"s": aid, "t": eid, "kind": "runs"})
        for p in c.get("platforms", []):
            norm = PLATFORM_NORM.get(p.lower().strip(), p if len(p) < 18 else None)
            if not norm:
                continue
            pid = "pl-" + norm.replace(" ", "-")
            add(pid, norm, "platform")
            links.append({"s": eid, "t": pid, "kind": "on"})
        for t in (c.get("target") or {}).get("countries", []):
            if t not in REGION:
                continue
            tid = "tg-" + t.replace(" ", "-")
            add(tid, t, "target")
            links.append({"s": eid, "t": tid, "kind": "targets"})

    # drop links whose ends were skipped
    links = [l for l in links if l["s"] in nodes and l["t"] in nodes]
    # dedupe
    seen, uniq = set(), []
    for l in links:
        key = (l["s"], l["t"], l["kind"])
        if key not in seen:
            seen.add(key)
            uniq.append(l)

    pos = spring_layout(list(nodes), uniq)
    for nid, n in nodes.items():
        n["x"], n["y"], n["z"] = pos[nid]

    out = {"nodes": list(nodes.values()), "links": uniq,
           "note": "generated from catalog/operations.json by build_network.py; ACTOR_MAP is the reviewed alias normalization"}
    dest = OUT / "network_graph.json"
    by_type = {}
    for n in nodes.values():
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    if check:
        if not dest.exists():
            print("network_graph.json missing — run build_network.py")
            return 1
        have = json.loads(dest.read_text())
        skel = lambda g: (sorted((n["id"], n["type"]) for n in g["nodes"]),
                          sorted((l["s"], l["t"], l.get("kind")) for l in g["links"]))
        if skel(have) != skel(out):
            hn, hl = skel(have)
            on, ol = skel(out)
            print("FAIL: network_graph.json structure differs from the catalog")
            for label, a, b in (("nodes", set(on), set(hn)), ("links", set(ol), set(hl))):
                for x in sorted(a - b):
                    print(f"  + {label[:-1]} in catalog, missing from committed graph: {x}")
                for x in sorted(b - a):
                    print(f"  - {label[:-1]} in committed graph, not in catalog: {x}")
            return 1
        print(f"network_graph.json: structure matches the catalog "
              f"({len(nodes)} nodes {by_type}, {len(uniq)} links); "
              f"layout coordinates not compared — see the module docstring")
        return 0

    dest.write_text(json.dumps(out))
    print(f"network_graph.json: {len(nodes)} nodes {by_type}, {len(uniq)} links")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="compare the committed graph's structure with the catalog "
                         "instead of rewriting it; coordinates are not compared")
    raise SystemExit(main(check=ap.parse_args().check))
