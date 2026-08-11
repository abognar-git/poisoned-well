# poisoned-well

**Working draft — data pipeline stage.** An interactive investigation into AI-enabled state influence operations in Central Europe: who builds propaganda for machines, what it did around Hungary's April 2026 election, and what the evidence honestly shows about whether any of it works.

> Working title from "poisoning the well": the campaigns documented here increasingly target
> AI training and retrieval systems rather than human readers.

## What this will be

A standalone editorial website (scrollytelling + two 3D scenes driven by live data) built on a
verified case catalog. Scope is the **AI layer only**: LLM-written fake-media networks, deepfake
incidents in CEE elections (Slovakia 2023 → Romania 2024/25 → Hungary 2026), AI-vendor takedown
evidence, and measured contamination of AI systems ("LLM grooming"). The Hungary 2026 election is
the anchor case; Chinese activity is covered honestly as capability-without-documented-Hungarian-deployment.

## Layout

```
scripts/
  fetch_pravda.py       pull CheckFirst's hourly Pravda-network dataset (manifest + CEE mirrors)
  fetch_frameworks.py   shallow-clone Meta threat-research (MIT) + DISARM (CC-BY-SA); fetch DISARM STIX
  derive_summaries.py   raw -> data/derived/*.json  (every number the site cites is generated here)
  check_catalog.py      gate: validate catalog/operations.json (required fields, enums, sources, data_refs)
  check_claims.py       gate: every data-claim on the site maps to a backed registry entry
catalog/
  schema.json           case-catalog entry schema
  operations.json       the sourced case catalog (21 entries, all sources adversarially re-verified)
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

1. **Scheduled refresh** (`.github/workflows/refresh-data.yml`): every 6 hours CI
   re-fetches upstream, regenerates `data/derived/`, and commits only real changes —
   the commit history becomes a monitoring log of the campaign.
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
