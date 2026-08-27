#!/usr/bin/env python3
"""Parse RESEARCH.md into data/derived/research.json so the page can render it.

RESEARCH.md is the single source. The site never retypes its corrections, limits,
cuts or open questions — it renders them from here, the same way every figure on the
page is generated rather than typed. If a section stops parsing, this script FAILS
rather than emitting a smaller file: a silently-empty research layer would let the
page quietly stop showing what the project got wrong, which is the one thing it must
never do.

Entry ids are stable and are what the page references via data-research="<id>":

    correction-N                   the published claims that were falsified
    root-cause                     why the validation gate passed them
    limit-c1 / limit-c2 / limit-c3 what each contribution cannot show
    cut-1 .. cut-6                 framing removed from the paper
    open-m7                        the decisive test not yet run (m6 ran; see correction-6)
    limitations                    the limitations paragraph, as drafted for the paper
    rq1 / rq2 / rq3                the research questions
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "RESEARCH.md"
OUT = ROOT / "data" / "derived" / "research.json"


def md(text: str) -> str:
    """Markdown emphasis -> HTML, escaping first. RESEARCH.md is ours, but the page
    inserts this as innerHTML, so nothing may pass through unescaped."""
    t = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+?)`", r"<code>\1</code>", t)
    t = re.sub(r"~~(.+?)~~", r"<s>\1</s>", t)
    return re.sub(r"\s+", " ", t).strip()


def section(doc: str, heading: str) -> str:
    """Everything between a '## <heading>' and the next '## '."""
    m = re.search(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)", doc, re.M | re.S)
    if not m:
        sys.exit(f"derive_research: section '{heading}' not found in RESEARCH.md")
    return m.group(1)


def main() -> int:
    doc = SRC.read_text()
    entries = []

    # ── §2 the corrections ────────────────────────────────────────────────
    corr = section(doc, "2. Corrections already applied")
    # The fifth column says who found the correction. The card used to assert "one of
    # four claims an adversarial review found wrong" for every correction, including the
    # one the project found itself — overstating the external review and understating its
    # own work, on the section that is this project's central asset.
    rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+?) \| `(\w+)` \| (.+?) \|$", corr, re.M)
    if not rows:
        sys.exit("derive_research: no correction rows parsed")
    # Titles are per-correction labels for the cards. The count is not fixed — the whole
    # point of this table is that it can grow — so an unnamed row gets a generic label
    # rather than failing the build and tempting someone to leave the correction out.
    titles = {"1": "The recovery", "2": "The diet", "3": "The campaign surge",
              "4": "The shared grammar", "5": "The theme labels"}
    for n, published, says, commit, found_by in rows:
        title = titles.get(n, f"Correction {n}")
        entries.append({
            "id": f"correction-{n}", "kind": "correction", "title": title,
            # the table quotes the withdrawn sentence; the card's own styling says it is
            # a quotation, so the stray marks would only render as debris
            "published": md(published.strip()).replace('"', '').strip(),
            "data_says": md(re.sub(r"\s*\*\*\[[VR]\]\*\*", "", says)),
            "commit": commit,
            "found_by": found_by.strip(),
        })

    m = re.search(r"\*\*Root cause.*?\*\*(.+?)(?=\n\*\*Consequence)", corr, re.S)
    if not m:
        sys.exit("derive_research: root-cause paragraph not found")
    entries.append({
        "id": "root-cause", "kind": "root-cause",
        "title": "Why the gate passed four false claims",
        "text": md(m.group(1)),
    })

    # ── §3 what each contribution cannot show ─────────────────────────────────
    contrib = section(doc, "3. Contributions, stated for a referee")
    limits = re.findall(r"\*\*(C[123]) — (.+?)\.?\*\*(.*?)(?=\n\*\*C[123] —|\Z)", contrib, re.S)
    if len(limits) != 3:
        sys.exit(f"derive_research: expected 3 contributions, parsed {len(limits)}")
    for cid, cname, body in limits:
        lm = re.search(r"\*Limit[^:]*:\*(.+?)(?=\n\*|\n\n|\Z)", body, re.S)
        if not lm:
            sys.exit(f"derive_research: no *Limit:* line under {cid}")
        entries.append({
            "id": f"limit-{cid.lower()}", "kind": "limit",
            "title": md(cname), "text": md(lm.group(1)),
        })

    # ── §4 framing removed from the paper ─────────────────────────────────────
    cuts = re.findall(r"^\d+\. \*\*(.+?)\*\*(.*?)(?=^\d+\. \*\*|\Z)",
                      section(doc, "4. What is cut"), re.M | re.S)
    if len(cuts) < 5:
        sys.exit(f"derive_research: expected at least 5 cuts, parsed {len(cuts)}")
    for i, (title, body) in enumerate(cuts, 1):
        entries.append({
            "id": f"cut-{i}", "kind": "cut",
            "title": md(title.rstrip(".")),
            "text": md(re.sub(r"\s*\*\*\[[VR]\]\*\*", "", body)) or "Removed.",
        })

    # ── §5 the tests that would settle it, not yet run ────────────────────────
    meth = section(doc, "5. Methods to strengthen, in priority order")
    # M6 sat here until the Telegram walk answered it. A method that has been run is struck
    # through in the table and leaves this registry the way M3 and M8 did; its result moves to
    # §2 as a correction. Retiring one means deleting its id from this tuple as well — a struck
    # row still listed here exits the build, which is the direction the failure should point.
    for mid, title in (("M7", "Hardening the headline zero"),):
        row = re.search(rf"^\|\s*{mid}\s*\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$", meth, re.M)
        if not row:
            sys.exit(f"derive_research: method row {mid} not found")
        entries.append({
            "id": f"open-{mid.lower()}", "kind": "open", "title": title,
            "text": md(row.group(1)) + " — " + md(row.group(2)),
        })

    # ── §7 the limitations paragraph and the research questions ───────────────
    arch = section(doc, "7. Paper architecture")
    quote = re.search(r"^> (.+?)(?=\n\n|\n---|\Z)", arch, re.M | re.S)
    if not quote:
        sys.exit("derive_research: limitations blockquote not found")
    entries.append({
        "id": "limitations", "kind": "limitations",
        "title": "The limitations paragraph, as drafted for the paper",
        "text": md(re.sub(r"^> ?", "", quote.group(1), flags=re.M)),
    })
    rqs = re.findall(r"\*\*RQ(\d)\.\*\* (.+?)\s*\*\((.+?)\)\*", arch, re.S)
    if len(rqs) != 3:
        sys.exit(f"derive_research: expected 3 research questions, parsed {len(rqs)}")
    for rq, body, note in re.findall(r"\*\*RQ(\d)\.\*\* (.+?)\s*\*\((.+?)\)\*", arch, re.S):
        entries.append({
            "id": f"rq{rq}", "kind": "question",
            "title": f"Research question {rq}", "text": md(body),
            "note": md(note),
        })

    out = {
        "note": ("Generated by scripts/derive_research.py from RESEARCH.md. The site renders "
                 "this rather than restating it, so the page cannot drift from the research "
                 "record. Every data-research=\"<id>\" on the page resolves to an entry here."),
        "source": "RESEARCH.md",
        "entries": entries,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    kinds = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"research.json: {len(entries)} entries " +
          " ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
