#!/usr/bin/env python3
"""Assert that the markers actually RENDER, not merely that their ids resolve.

check_claims.py greps the pages for data-claim / data-research / data-term attributes and
diffs the id sets against the registries. That is a resolution check, and this project's
own published lesson is that resolution is not the property that matters:

    "A gate that checks provenance but not inference will pass a false finding every time."

The same gap exists one layer down. An id inside an HTML comment, a <template>, a
display:none element, or a JS string on a dead path all satisfy the regex identically. The
realistic version is not sabotage but a refactor slip: several markers are injected via
innerHTML and wired by explicit wireMarkers() calls, and deleting one line —

    wireMarkers(document.getElementById('peer-note').parentElement);

— leaves the attribute present in the source, the id resolving, all four gates green, and
the correction rendering with no ▲ on it. A reader sees a withdrawn claim with no
affordance to learn it was withdrawn, which is the one thing this project must never do.

So: serve the tree, render it in headless Chrome, and count what is in the DOM.

    python3 scripts/check_render.py

Chrome is a soft dependency. Without it the script prints why it could not run and exits
0 — a contributor should not be blocked by a browser they do not have — but CI runs on an
image that ships one, so the check is real where it counts.
"""
import json
import re
import shutil
import socket
import subprocess
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DER = ROOT / "data" / "derived"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(port, drop=None):
    """The pages are ES modules that fetch ../../data, so file:// cannot render them.

    `drop` 404s one path, which is how the degraded case gets exercised: three fetches on
    index.html were unguarded, and guarding them exposed a second unguarded line that took
    the whole provenance-census paragraph with it. That shipped because nothing rendered
    the failure path — the verification was a marker count, and the markers were fine."""
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):    # one request line per asset drowns the result
            pass

        def send_head(self):
            if drop and self.path.split("?")[0].endswith(drop):
                self.send_error(404)
                return None
            return super().send_head()
    handler = partial(Quiet, directory=str(ROOT))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def dom(chrome, url):
    out = subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--virtual-time-budget=15000", "--dump-dom", url],
        capture_output=True, text=True, timeout=120)
    return out.stdout


def main() -> int:
    chrome = find_chrome()
    if not chrome:
        print("check_render: no Chrome or Chromium found — skipping the render assertion.")
        print("  (CI runs on an image that has one; install Chrome to run this locally.)")
        return 0

    research = json.loads((DER / "research.json").read_text())["entries"]
    claims = json.loads((ROOT / "catalog" / "claims.json").read_text())
    glossary = json.loads((ROOT / "catalog" / "glossary.json").read_text())
    corrections = [e["id"] for e in research if e["kind"] == "correction"]

    port = free_port()
    httpd = serve(port)
    time.sleep(0.4)
    errors = []
    try:
        html = dom(chrome, f"http://127.0.0.1:{port}/site/prototype/index.html")
    finally:
        httpd.shutdown()

    if len(html) < 50_000:
        print(f"check_render: rendered DOM is only {len(html):,} bytes — the page did not "
              f"come up. Not asserting against a page that failed to load.")
        return 1

    # Strip comments and <template> contents: an id inside either satisfies a raw-text
    # regex and renders nothing, which is exactly the class this gate exists to catch.
    body = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    body = re.sub(r"<template[^>]*>.*?</template>", "", body, flags=re.S | re.I)

    def rendered_ids(attr):
        return re.findall(rf'{attr}="([a-z0-9-]+)"', body)

    # Per-id counts, not totals: a marker lost in one place and gained in another nets to
    # zero, and a raw total also picks up ids sitting inside script text.
    n_cite = body.count('class="cite"')
    n_rcite = len(re.findall(r'class="rcite[^"]*"', body))
    n_term = len(re.findall(r'class="term[^"]*"', body))

    claim_ids = {c["id"] for c in claims}
    gloss_ids = {g["id"] for g in glossary}
    research_ids = {e["id"] for e in research}

    for attr, known, label in (("data-claim", claim_ids, "claim"),
                               ("data-research", research_ids, "research"),
                               ("data-term", gloss_ids, "glossary")):
        for i in sorted(set(rendered_ids(attr)) - known):
            errors.append(f"rendered {label} id does not resolve to its registry: {i}")

    # The invariant this file exists for: every correction must be visible on the page.
    marked = set(rendered_ids("data-research"))
    for cid in corrections:
        if cid not in marked:
            errors.append(f"{cid} does not render on the page — a correction that stops "
                          f"being shown is the one failure this project must never have")

    # And the markers themselves must exist, not just their host elements. A correction
    # whose wireMarkers() call was deleted keeps its attribute and loses its affordance.
    n_correction_markers = len(re.findall(r'class="rcite correction"', body))
    if n_correction_markers < len(corrections):
        errors.append(f"{n_correction_markers} correction markers rendered for "
                      f"{len(corrections)} corrections — an attribute is present without "
                      f"its ▲; check that every innerHTML rebuild re-runs wireMarkers()")

    if not n_cite or not n_term:
        errors.append(f"markers missing entirely: {n_cite} §, {n_term} dotted terms — the "
                      f"evidence layer did not run")

    # ── the explorer, which this gate did not load at all. Both regressions that reached
    # main from the QA fix set were on surfaces nothing rendered in CI: the origin axis
    # returning zero for the links the page itself writes, and index.html printing
    # "undefined" into prose once a guarded fetch failed.
    port2 = free_port()
    httpd = serve(port2)
    time.sleep(0.3)
    try:
        base = f"http://127.0.0.1:{port2}/site/prototype/explorer.html"
        counts = {h: re.search(r"([\d,]+) SPECIMENS", dom(chrome, base + "#" + h))
                  for h in ("origin=News+Front+%28direct%29", "origin=news+front+%28direct%29",
                            "theme=ukraine", "theme=Ukraine")}
    finally:
        httpd.shutdown()
    got = {k: (m.group(1) if m else None) for k, m in counts.items()}
    for a, b, what in (("origin=News+Front+%28direct%29", "origin=news+front+%28direct%29", "origin"),
                       ("theme=ukraine", "theme=Ukraine", "theme")):
        if got[a] != got[b]:
            errors.append(f"explorer {what} filter is case-sensitive: {got[a]} vs {got[b]} — "
                          f"a link the page writes and the same link retyped must agree")
        elif got[a] in (None, "0"):
            errors.append(f"explorer {what} filter returns {got[a]} for a label that exists")

    # ── and the degraded path: one derived file missing must not print undefined/NaN into
    # prose or silently delete a section.
    # This dropped live_status.json and nothing else, and it passed while a missing
    # pravda_summary.json threw at module top-level and took 59% of the DOM with it — the
    # census paragraph included — leaving the hero on the 0 baked into the markup. Testing one
    # file is not testing the degraded path, it is testing one degraded path. Each file the
    # page fetches at load now gets its own run: four Chrome launches instead of one, which is
    # the price of the assertion actually meaning what it says.
    DEGRADE = ("live_status.json", "pravda_timeline.json", "pravda_summary.json",
               "latest_specimens.json")
    deg_cites = {}
    for drop in DEGRADE:
        port3 = free_port()
        httpd = serve(port3, drop=drop)
        time.sleep(0.3)
        try:
            deg = dom(chrome, f"http://127.0.0.1:{port3}/site/prototype/index.html")
        finally:
            httpd.shutdown()
        deg_body = re.sub(r"<script.*?</script>", "", deg, flags=re.S | re.I)
        for bad in ("undefined", "NaN"):
            if bad in deg_body:
                errors.append(f"with {drop} missing the page renders the literal "
                              f"{bad!r} into prose")
        if "zero times" not in deg_body:
            errors.append(f"with {drop} missing the provenance-census paragraph "
                          "disappears — the page must degrade to baked figures, not to silence")
        deg_cites[drop] = deg_body.count('class="cite"')
        if deg_cites[drop] < n_cite - 2:
            errors.append(f"with {drop} missing the evidence layer drops to "
                          f"{deg_cites[drop]} § from {n_cite}")
    deg_cite = min(deg_cites.values())

    print(f"check_render: {len(html):,} bytes of DOM | {n_cite} § · {n_rcite} ▲ "
          f"({n_correction_markers} corrections) · {n_term} dotted terms")
    print(f"  explorer axes case-insensitive · {len(DEGRADE)} degraded paths, worst "
          f"{deg_cite} § of {n_cite}, none printing undefined/NaN")
    if errors:
        print("FAIL:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
