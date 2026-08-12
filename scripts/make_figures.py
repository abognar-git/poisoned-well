#!/usr/bin/env python3
"""Regenerate every figure in the README from data/derived/, as light/dark SVG pairs.

Stdlib only, no plotting library: the figures are geometry emitted as text, so a
reviewer can diff them and a fresh clone can rebuild them.

The palette is cut to three roles — focal / neutral / annotation — for the reason
given in RESEARCH.md section 6: the site's amber-and-sage palette simulates to a
contrast ratio of 1.00 under deuteranopia, so on the figures colour never carries a
distinction on its own. Every series is redundantly encoded by line weight and
direct end-labels, and every figure survives greyscale.

    python3 scripts/make_figures.py

F1  peer event study      the lead result: Hungary against its six siblings
F3  placebo distribution  1,948 blind-scan windows, the treated one marked
F5  provenance census     the zero, drawn at true scale with an explicit zero row
F6  technique overlap     the null, with chance drawn as a reference line
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DER = ROOT / "data" / "derived"
OUT = ROOT / "docs" / "figures"

THEMES = {
    "light": dict(bg="#ffffff", ink="#12161d", mid="#6b7280", grid="#e4e7eb",
                  focal="#c0392b", neutral="#9aa3af", annot="#1f6feb", panel="#f7f8fa"),
    "dark":  dict(bg="#0b1018", ink="#e9e4da", mid="#8b93a3", grid="#1d2430",
                  focal="#ff6b57", neutral="#7c8698", annot="#6ea8d8", panel="#0f1520"),
}
MONO = "ui-monospace,'IBM Plex Mono',Menlo,monospace"
SERIF = "'Newsreader',Georgia,serif"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def svg(w, h, body, t, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title>'
            f'<rect width="{w}" height="{h}" fill="{t["bg"]}"/>{body}</svg>\n')


def txt(x, y, s, t, size=11, fill=None, anchor="start", family=MONO, weight=400, ls=0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" letter-spacing="{ls}" fill="{fill or t["mid"]}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def write(name, build, title):
    for theme, t in THEMES.items():
        (OUT / f"{name}_{theme}.svg").write_text(build(t, title))
    print(f"  {name}_light.svg / {name}_dark.svg")


# ── F1 · the peer event study ────────────────────────────────────────────────
def f1(t, title):
    pc = json.loads((DER / "peer_control.json").read_text())
    rows = [pc["target"]] + pc["peers"]
    months = [m for m in sorted(pc["target"]["monthly"]) if m >= "2025-09"]
    W, H, M = 980, 420, dict(l=64, r=132, tp=52, b=54)
    iw, ih = W - M["l"] - M["r"], H - M["tp"] - M["b"]
    hi = max(max(r["monthly"].get(m, 0) for m in months) for r in rows) * 1.08
    X = lambda i: M["l"] + i * iw / max(1, len(months) - 1)
    Y = lambda v: M["tp"] + ih - (v / hi) * ih
    b = [f'<rect x="{M["l"]}" y="{M["tp"]}" width="{iw}" height="{ih}" fill="{t["panel"]}"/>']
    for g in range(0, int(hi) + 1, 100):
        b.append(f'<line x1="{M["l"]}" y1="{Y(g):.1f}" x2="{M["l"]+iw}" y2="{Y(g):.1f}" '
                 f'stroke="{t["grid"]}" stroke-width="1"/>')
        b.append(txt(M["l"] - 8, Y(g) + 3.5, str(g), t, 10, anchor="end"))
    # election and estimated onset drawn as separate rules: the gap is the finding
    for mk, lab, dash in (("2026-04", "12 Apr · vote", "3 3"), ("2026-05", "≈27 Apr · onset", "1 4")):
        if mk in months:
            x = X(months.index(mk))
            b.append(f'<line x1="{x:.1f}" y1="{M["tp"]}" x2="{x:.1f}" y2="{M["tp"]+ih}" '
                     f'stroke="{t["annot"]}" stroke-width="1" stroke-dasharray="{dash}"/>')
            b.append(txt(x + 4, M["tp"] + 13, lab, t, 9.5, t["annot"]))
    for r in rows:
        tgt = r["is_target"]
        pts = " ".join(f"{X(i):.1f},{Y(r['monthly'].get(m, 0)):.1f}" for i, m in enumerate(months))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{t["focal"] if tgt else t["neutral"]}" '
                 f'stroke-width="{3.1 if tgt else 1.15}" stroke-opacity="{1 if tgt else .62}" '
                 f'stroke-linejoin="round"/>')
        lv = r["monthly"].get(months[-1], 0)
        b.append(txt(M["l"] + iw + 7, Y(lv) + 3.5, r["mirror"], t, 9.5,
                     t["focal"] if tgt else t["neutral"], weight=500 if tgt else 400))
    for i, m in enumerate(months):
        if i % 2 == 0:
            b.append(txt(X(i), M["tp"] + ih + 17, m, t, 9, anchor="middle"))
    b.append(txt(M["l"], 24, "ARTICLES PER DAY · MONTHLY MEAN · SEVEN MIRRORS OF ONE NETWORK",
                 t, 10.5, t["ink"], ls=1.6))
    b.append(txt(M["l"], 40, "Hungary falls 63.7% while the six siblings move +1.6% on average — "
                 "but the step lands 15 days after the vote", t, 10, t["mid"], family=SERIF))
    return svg(W, H, "".join(b), t, title)


# ── F3 · the placebo distribution ────────────────────────────────────────────
def f3(t, title):
    ns = json.loads((DER / "network_scan.json").read_text())
    ev = next(e for e in ns["events"]["tested"] if e["id"] == "hu-2026-parliamentary")["result"]
    ch = sorted(v for v in ev["peer_changes"].values())
    W, H, M = 980, 300, dict(l=64, r=40, tp=52, b=56)
    iw, ih = W - M["l"] - M["r"], H - M["tp"] - M["b"]
    lo, hi = -100, 140
    X = lambda v: M["l"] + (max(lo, min(hi, v)) - lo) / (hi - lo) * iw
    b = [f'<rect x="{M["l"]}" y="{M["tp"]}" width="{iw}" height="{ih}" fill="{t["panel"]}"/>']
    for g in range(lo, hi + 1, 20):
        b.append(f'<line x1="{X(g):.1f}" y1="{M["tp"]}" x2="{X(g):.1f}" y2="{M["tp"]+ih}" '
                 f'stroke="{t["grid"]}" stroke-width="1"/>')
        b.append(txt(X(g), M["tp"] + ih + 18, f"{g:+d}%", t, 9, anchor="middle"))
    # every donor mirror as one mark, jittered deterministically by index
    for i, v in enumerate(ch):
        y = M["tp"] + 14 + (i * 37 % (ih - 28))
        b.append(f'<circle cx="{X(v):.1f}" cy="{y:.1f}" r="2.4" fill="{t["neutral"]}" fill-opacity=".5"/>')
    x = X(ev["change_pct"])
    b.append(f'<line x1="{x:.1f}" y1="{M["tp"]-6}" x2="{x:.1f}" y2="{M["tp"]+ih+6}" '
             f'stroke="{t["focal"]}" stroke-width="2.4"/>')
    b.append(txt(x + 7, M["tp"] + 6, f"Hungary {ev['change_pct']}%", t, 10.5, t["focal"], weight=500))
    b.append(txt(x + 7, M["tp"] + 20,
                 f"rank {ev['normalised_rank']} of {ev['n_windows']} · p = {ev['normalised_p']}",
                 t, 9.5, t["focal"]))
    b.append(txt(M["l"], 24, "EVERY DONOR MIRROR'S CHANGE OVER THE SAME TWO MONTHS", t, 10.5,
                 t["ink"], ls=1.6))
    b.append(txt(M["l"], 40, f"{len(ch)} mirrors of the same network, none of them facing a Hungarian "
                 "election. The drop is real and it is not rare.", t, 10, t["mid"], family=SERIF))
    return svg(W, H, "".join(b), t, title)


# ── F5 · the provenance census ───────────────────────────────────────────────
def f5(t, title):
    cv = json.loads((DER / "convergence.json").read_text())
    P = cv["provenance_audit"]
    rows = [(b["bucket"].replace("_", " "), b["articles"], b["share"]) for b in P["buckets"]]
    rows.append(("hungarian pro-government press", 0, 0.0))
    W, M = 980, dict(l=250, r=110, tp=56, b=44)
    rh, gap = 30, 12
    H = M["tp"] + len(rows) * (rh + gap) + M["b"]
    iw = W - M["l"] - M["r"]
    mx = max(v for _, v, _ in rows) or 1
    b = []
    for i, (lab, v, sh) in enumerate(rows):
        y = M["tp"] + i * (rh + gap)
        zero = v == 0
        b.append(txt(M["l"] - 12, y + rh * .68, lab, t, 10.5,
                     t["focal"] if zero else t["ink"], anchor="end",
                     weight=500 if zero else 400))
        if zero:
            # an explicit zero row, not an absent bar — the point is that it is empty
            b.append(f'<rect x="{M["l"]}" y="{y}" width="{iw}" height="{rh}" fill="none" '
                     f'stroke="{t["focal"]}" stroke-width="1" stroke-dasharray="3 3"/>')
            b.append(txt(M["l"] + 10, y + rh * .68, "zero — across all 938 credited sources",
                         t, 10, t["focal"], weight=500))
        else:
            w = max(2, v / mx * iw)
            b.append(f'<rect x="{M["l"]}" y="{y}" width="{w:.1f}" height="{rh}" '
                     f'fill="{t["neutral"]}"/>')
            b.append(txt(M["l"] + w + 8, y + rh * .68, f"{v:,}  ({sh*100:.2f}%)", t, 10))
    b.append(txt(M["l"] - 250 + 250, 24, "WHAT THE HUNGARIAN MIRROR SAYS IT REPUBLISHES", t, 10.5,
                 t["ink"], ls=1.6))
    b.append(txt(M["l"] - 250 + 250, 40,
                 f"{P['total_articles']:,} articles · {P['credited_sources']} credited sources · "
                 f"coverage {P['coverage']:.4f} — this is declared provenance, not observed ingestion",
                 t, 10, t["mid"], family=SERIF))
    return svg(W, H, "".join(b), t, title)


# ── F6 · the technique overlap, against chance ───────────────────────────────
def f6(t, title):
    T = json.loads((DER / "convergence.json").read_text())["technique_overlap"]
    obs = len(T["shared"])
    W, H, M = 980, 250, dict(l=64, r=40, tp=52, b=52)
    iw, ih = W - M["l"] - M["r"], H - M["tp"] - M["b"]
    hi = 8.0
    X = lambda v: M["l"] + v / hi * iw
    b = [f'<rect x="{M["l"]}" y="{M["tp"]}" width="{iw}" height="{ih}" fill="{t["panel"]}"/>']
    for g in range(0, 9):
        b.append(f'<line x1="{X(g):.1f}" y1="{M["tp"]}" x2="{X(g):.1f}" y2="{M["tp"]+ih}" '
                 f'stroke="{t["grid"]}"/>')
        b.append(txt(X(g), M["tp"] + ih + 18, str(g), t, 9.5, anchor="middle"))
    b.append(f'<rect x="{M["l"]}" y="{M["tp"]+26}" width="{X(obs)-M["l"]:.1f}" height="34" '
             f'fill="{t["neutral"]}"/>')
    b.append(txt(X(obs) + 9, M["tp"] + 48, f"{obs} observed", t, 11, t["ink"], weight=500))
    for c in T["chance_baseline"]:
        x = X(c["expected_overlap"])
        b.append(f'<line x1="{x:.1f}" y1="{M["tp"]+8}" x2="{x:.1f}" y2="{M["tp"]+ih-8}" '
                 f'stroke="{t["focal"]}" stroke-width="2" stroke-dasharray="4 3"/>')
        b.append(txt(x + 6, M["tp"] + ih - 12,
                     f"{c['expected_overlap']} expected by chance ({c['size']} {c['universe']})",
                     t, 9.5, t["focal"]))
    b.append(txt(M["l"], 24, "SHARED DISARM TECHNIQUES, AGAINST WHAT CHANCE PRODUCES", t, 10.5,
                 t["ink"], ls=1.6))
    b.append(txt(M["l"], 40, "The observed overlap sits at or below chance. Reported as a null, "
                 "and it replaced a published claim that it was a finding.", t, 10, t["mid"],
                 family=SERIF))
    return svg(W, H, "".join(b), t, title)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("figures →", OUT.relative_to(ROOT))
    write("peer_event_study", f1, "Monthly output of seven mirrors of one network; the Hungarian "
          "line falls 63.7% after April 2026 while the six others hold roughly flat")
    write("placebo_distribution", f3, "The two-month change of every donor mirror over the same "
          "window, with the Hungarian value marked at rank 207 of 1,948")
    write("provenance_census", f5, "Sources the Hungarian mirror credits, by article count, with "
          "an explicit zero row for the Hungarian pro-government press")
    write("technique_overlap", f6, "Four DISARM techniques observed on both sides against a chance "
          "expectation of 5.00 to 6.25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
