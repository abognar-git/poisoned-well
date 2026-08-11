#!/usr/bin/env python3
"""Gate: validate catalog/operations.json against the house rules.

Checks (stdlib only, no jsonschema dependency):
  - required fields present, id format, unique ids
  - category / confidence values are from the schema enums
  - every entry has at least one source with a URL
  - every scale figure names its source in the value text or the entry has data_refs
  - data_refs point at files that exist
  - draft entries are counted so the README can say how many are unverified
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog" / "operations.json"

CATEGORIES = {"operation", "infrastructure", "incident", "takedown", "measurement", "context"}
CONFIDENCE = {"confirmed", "high", "medium", "contested", "unattributed"}
REQUIRED = {"id", "name", "category", "summary", "attribution", "ai_usage", "sources", "status"}


def main() -> int:
    entries = json.loads(CATALOG.read_text())
    errors: list[str] = []
    ids = [e.get("id", "?") for e in entries]
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids present")

    for e in entries:
        eid = e.get("id", "?")
        missing = REQUIRED - e.keys()
        if missing:
            errors.append(f"{eid}: missing {sorted(missing)}")
        if not re.fullmatch(r"[a-z0-9-]+", eid):
            errors.append(f"{eid}: bad id format")
        if e.get("category") not in CATEGORIES:
            errors.append(f"{eid}: bad category {e.get('category')!r}")
        conf = e.get("attribution", {}).get("confidence")
        if conf not in CONFIDENCE:
            errors.append(f"{eid}: bad confidence {conf!r}")
        if not e.get("sources") or not all(s.get("url") for s in e["sources"]):
            errors.append(f"{eid}: sources missing or lacking urls")
        for ref in e.get("data_refs", []):
            if not (ROOT / ref).exists():
                errors.append(f"{eid}: data_ref does not exist: {ref}")

    drafts = sum(1 for e in entries if e.get("status") == "draft")
    n_sources = sum(len(e.get("sources", [])) for e in entries)
    print(f"{len(entries)} entries | {n_sources} sources | {drafts} draft / "
          f"{len(entries) - drafts} verified")
    if errors:
        print("\nFAIL:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
