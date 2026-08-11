# poisoned-well

**Working draft — data pipeline stage.** An interactive investigation into AI-enabled state influence operations in Central Europe: who builds propaganda for machines, what it did around Hungary's April 2026 election, and what the evidence honestly shows about whether any of it works.

> Working title from "poisoning the well": the campaigns documented here increasingly target
> AI training and retrieval systems rather than human readers.

## What this will be

A standalone editorial website (scrollytelling + five 3D scenes driven by live data) built on a
verified case catalog. Scope is the **AI layer only**: LLM-written fake-media networks, deepfake
incidents in CEE elections (Slovakia 2023 → Romania 2024/25 → Hungary 2026), AI-vendor takedown
evidence, and measured contamination of AI systems ("LLM grooming"). The Hungary 2026 election is
the anchor case.

**Regional scope.** The catalog holds only operations with documented activity against Hungary or
its immediate neighbours (Austria, Slovakia, Ukraine, Romania, Serbia, Croatia, Slovenia). Cases
documented solely elsewhere — the PRC networks (Spamouflage, GoLaxy), the German and Moldovan
operations, the non-regional AI-vendor takedowns — were removed rather than carried as context,
so every entry on the site answers "what reached this region". Mechanism evidence about the AI
layer itself (LLM-grooming measurement, effectiveness null results, the Pravda/Portal Kombat
network that runs the Hungarian mirror) is kept regardless of where it was measured.

## Layout

```
scripts/
  fetch_pravda.py       pull CheckFirst's hourly Pravda-network dataset (manifest + CEE mirrors)
  fetch_frameworks.py   shallow-clone Meta threat-research (MIT) + DISARM (CC-BY-SA); fetch DISARM STIX
  derive_summaries.py   raw -> data/derived/*.json  (every number the site cites is generated here)
  capture_specimens.py  server-side capture of the mirror's latest real headlines (evidence, not linked)
  check_catalog.py      gate: validate catalog/operations.json (required fields, enums, sources, data_refs)
  check_claims.py       gate: every data-claim on the site maps to a backed registry entry
  derive_convergence.py how far the domestic AI machine ran the Russian playbook — and the pipeline test
catalog/
  schema.json           case-catalog entry schema
  operations.json       the sourced case catalog (24 entries, all sources adversarially re-verified);
                        each entry stores `side` (domestic / russian-attributed / contested / n/a) and
                        `evidence_class` so the convergence bucketing is a recorded decision, not a heuristic
  claims.json           claims registry: every fact rendered on the site, with its evidence
data/
  raw/                  gitignored; refreshed by fetch scripts
  derived/              committed summaries the site renders
```

## Reproduce

```
python3 scripts/fetch_pravda.py
python3 scripts/fetch_frameworks.py
python3 scripts/derive_summaries.py
python3 scripts/check_catalog.py
python3 scripts/check_claims.py
```

Python 3.11+, stdlib only. `git` required for the two shallow clones.

## Live data

The campaign this site documents is ongoing — the Hungarian Pravda mirror publishes
continuously (CheckFirst's upstream dataset updates hourly). Two mechanisms keep the
site current:

1. **Scheduled refresh** (`.github/workflows/refresh-data.yml`): hourly, CI
   re-fetches upstream, regenerates `data/derived/`, captures the latest article
   specimens, and commits only real changes — the commit history becomes a
   monitoring log of the campaign.

**Live specimens** (`scripts/capture_specimens.py` → `data/derived/latest_specimens.json`):
the "What it published today" panel shows the network's most recent real headlines as
evidence of ongoing output. Captured **server-side only** (never from a visitor's browser,
so no visitor traffic/referrer reaches the propaganda domain and its inbound-link signal is
not fed); shown as labeled evidence, **not hyperlinked**; personal-smear headlines are
withheld from the panel and documented as debunked evidence in the case files instead.
2. **Client-side refresh** (site, planned): the deployed page reads
   `data/derived/live_status.json` at load and additionally attempts a direct fetch of
   the upstream per-mirror JSON (raw.githubusercontent.com serves CORS) to show
   "articles published today"; if the upstream fetch fails or its schema drifts, the
   page falls back to the committed baked values. The site must never break because
   the adversary's infrastructure — or its monitor — changed.

## Data sources and licenses

- CheckFirst, Pravda Network Data Collection (cite per repo README) — hourly article metadata per mirror
- Meta threat-research (MIT) — CIB threat indicators, kill-chain tagged
- DISARM Foundation (CC-BY-SA-4.0) — Red/Blue framework CSV + STIX 2.1
- Case catalog sources: per-entry citations in `catalog/operations.json`

## Honesty rules (carried from the assay family)

- Generated, not typed: site figures come from `data/derived/`, produced by scripts from raw data.
- Claim-level evidence: every fact rendered on the site carries a visible § marker resolving to
  `catalog/claims.json` — sources re-checked against the claim, or generated data. `check_claims.py`
  fails the build if a rendered claim lacks backing.
- Attribution confidence is stated per case; contested and unattributed stay labelled as such.
- Null results are load-bearing: no research demonstrates AI disinformation swung any election,
  and the AI-heaviest campaign in EU history (Hungary 2026) lost. The site says so.
- Smear content appears only as debunked evidence, never republished at face value.
