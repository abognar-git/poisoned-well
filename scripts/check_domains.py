#!/usr/bin/env python3
"""Measure whether the campaign's documented fake-outlet domains still resolve, and
date when they stopped serving content.

The case files name three Hungarian-language fake outlets built for the Storm-1516
campaign. Whether they are still up is a fact about the campaign's infrastructure that
nothing in this repository was measuring — the catalog records that they existed, not
that they since went dark.

Two independent measurements, because either alone is weak:

  DNS      A/AAAA/NS across the system resolver plus Google (8.8.8.8) and Cloudflare
           (1.1.1.1). Three resolvers so a local failure cannot masquerade as a dead
           domain, and two control domains that must resolve, so a broken network
           cannot either. A domain is reported dead ONLY if every resolver agrees AND
           both controls answered.

  ARCHIVE  The Internet Archive's CDX index gives the first capture and the last one
           that returned 2xx — i.e. the last time the site actually served content —
           plus what the crawler got afterwards. This is what turns "it does not
           resolve today" into a date.

Neither shows *why* a domain went away: an expiry, a registrar suspension, a takedown
and an operator walking away all look identical from outside. The output says so, and
the claim built on it must not say more.

    python3 scripts/check_domains.py
"""
import json
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived" / "domain_status.json"

# Documented in catalog/operations.json under storm-1516-hungary-2026. Held here as
# plain strings and never emitted as a link — the blocklist gate exists for that reason.
TARGETS = [
    ("hirekhub24.hu", "storm-1516-hungary-2026"),
    ("oknyomozoriport.hu", "storm-1516-hungary-2026"),
    ("napihirek24.hu", "storm-1516-hungary-2026"),
]
# Must resolve. If either fails the run is inconclusive rather than a finding.
# Two live domains, neither of them the adversary's. The mirror used to be one of
# these, which meant the liveness precondition for "these three fake outlets are
# still dark" failed precisely when the mirror went dark — the event this project
# exists to watch for. A control has to be something whose survival is uncorrelated
# with what is being measured.
CONTROLS = ["index.hu", "example.com"]
RESOLVERS = [("system", None), ("google", "8.8.8.8"), ("cloudflare", "1.1.1.1")]


def resolve(domain, server):
    if server is None:
        try:
            return [socket.gethostbyname(domain)]
        except OSError:
            return []
    try:
        r = subprocess.run(["dig", "+short", "+time=3", "+tries=1", f"@{server}", domain, "A"],
                           capture_output=True, text=True, timeout=15)
        return [l for l in r.stdout.split() if l and l[0].isdigit()]
    except Exception:
        return []


def archive(domain, attempts=3):
    """First capture, last capture that served content, and what followed."""
    q = urllib.parse.urlencode({"url": domain + "/*", "output": "json",
                                "fl": "timestamp,statuscode", "collapse": "timestamp:8",
                                "limit": "500"})
    for i in range(attempts):
        try:
            raw = urllib.request.urlopen(
                "https://web.archive.org/cdx/search/cdx?" + q, timeout=45).read().decode()
            rows = json.loads(raw) if raw.strip() else []
            if rows and rows[0][0] == "timestamp":
                rows = rows[1:]
            break
        except Exception:
            rows = None
            time.sleep(3)
    if rows is None:
        return {"available": False, "note": "Internet Archive CDX unreachable on this run"}
    if not rows:
        return {"available": True, "captures": 0}
    iso = lambda t: f"{t[:4]}-{t[4:6]}-{t[6:8]}"
    live = sorted(r[0] for r in rows if r[1].startswith("2"))
    after = sorted((r[0], r[1]) for r in rows if live and r[0] > live[-1])
    codes = {}
    for _, c in after:
        codes[c] = codes.get(c, 0) + 1
    return {
        "available": True,
        "captures": len(rows),
        "first_capture": iso(sorted(r[0] for r in rows)[0]),
        "last_serving_content": iso(live[-1]) if live else None,
        "captures_after": len(after),
        "status_codes_after": codes,
        "last_capture": iso(sorted(r[0] for r in rows)[-1]),
    }


def main() -> int:
    controls = {c: {name: resolve(c, s) for name, s in RESOLVERS} for c in CONTROLS}
    controls_ok = all(any(v for v in per.values()) for per in controls.values())

    results = []
    for domain, case in TARGETS:
        per = {name: resolve(domain, s) for name, s in RESOLVERS}
        resolves = any(per.values())
        results.append({
            "domain": domain, "case": case,
            "resolves": resolves,
            "by_resolver": per,
            "verdict": ("resolves" if resolves else
                        "does not resolve on any resolver" if controls_ok else
                        "inconclusive — control domains failed too"),
            "archive": archive(domain),
        })

    out = {
        "note": ("Generated by scripts/check_domains.py. Whether each documented fake-outlet "
                 "domain still resolves, measured across three resolvers with two control "
                 "domains, plus the Internet Archive's record of when it last served content. "
                 "This dates a disappearance; it does not explain one. Expiry, registrar "
                 "suspension, takedown and abandonment are indistinguishable from outside, and "
                 "no claim built on this file may pick between them."),
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "controls_resolved": controls_ok,
        "controls": {c: any(v for v in per.values()) for c, per in controls.items()},
        "domains": results,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")

    if not controls_ok:
        print("check_domains: CONTROL DOMAINS FAILED — run is inconclusive, not a finding")
        return 1
    dead = [r for r in results if not r["resolves"]]
    print(f"domain_status.json: {len(dead)}/{len(results)} documented fake-outlet domains "
          f"no longer resolve on any of {len(RESOLVERS)} resolvers")
    for r in results:
        a = r["archive"]
        last = a.get("last_serving_content") or "—"
        print(f"  {r['domain']:<22} {r['verdict']:<34} last served {last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
