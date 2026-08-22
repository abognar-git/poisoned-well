# Publication plan

**Status:** pre-submission. Written 2026-08-12 after an adversarial review of the whole project.
**Verification convention:** figures marked **[V]** were recomputed directly from `data/raw/` by the
PI. Figures marked **[R]** come from the referee pass and are *not yet independently reproduced* —
they must be before they enter a draft.

---

## 1. Verdict

There is a paper. It is a **short empirical paper**, and it is much smaller than the story the website
tells. Its defensible core:

> The Pravda network's one-mirror-per-country architecture can be used as a **control group**. Applied
> to the mirror aimed at Hungary's April 2026 election, it yields (a) a full-coverage negative
> provenance census — zero credits to the Hungarian pro-government press across 141,808 articles — and
> (b) a demonstration that output interruptions in such a network are common and largely not
> election-aligned — including the Hungarian one, which is the largest in its own window but 6th of 12
> episodes network-wide and 15 days late to the event it is usually attributed to.

The contribution is **the design and the census**. The interruption is the demonstration case, and we
claim no cause for it.

Everything framed as "propaganda written for machines" leaves the paper entirely: **this repository
contains no model-side or retrieval-side measurement of any kind.** That framing is inherited from
other people's audits and belongs on the website, not in our results.

---

## 2. Corrections already applied

The review found four published claims that were wrong. All four were verified against our own
data and fixed before this plan was written. The fifth row is not one of them: the specimen
labelling defect was found by this project thirty-five hours later, after the review had closed,
and the `Found by` column says which is which. They are listed here because a reader of the repo
history deserves to see them, and because each one is a lesson about the pipeline.

| # | Claim as published | What the data says | Commit | Found by |
|---|---|---|---|---|
| 1 | "The Russian-institutional layer carries the recovery" | The three *collapsed* channels supply **101% of the rebound** (+69.4 of +68.4/day) — more than all of it, so everything else nets **−1.0/day**. Their share of output goes 68% → 33% → **63%** **[V]** | `53dec10` | adversarial review |
| 2 | "The mirror changed what it eats" (live cross-check) | Invalid comparison. Our capture harvests only the `/en/` surface; the census counts all languages (hu 98,110 > en 80,259). On the capture days the census shows those channels credited in **60–77%** of articles **[V]** | `53dec10` | adversarial review |
| 3 | "No surge for the election it was aimed at" | March 2026 (269.6/day) is the mirror's **highest month in its entire series**. Only the *difference* survives: +24.0% vs peer mean +12.4% **[V]** | `53dec10` | adversarial review |
| 5 | Theme tags on captured specimens ("payload" vs "filler") | The lexicon was Latin-script only, so **98.3% of Cyrillic items were labelled `filler`** — a label confounded with language, not a measurement of topic. Made worse on 2026-08-13 by adding five Russian-language outlets. Now scored per language with a published coverage matrix, and `unscored` is a third value **[V]** | `e085410` | this project, after the review closed |
| 4 | "What the two do share is a grammar" (technique overlap) | Observed overlap **4**; expected by chance **5.00** (45-technique pool) or **6.25** (36 used). At or *below* chance **[V]** | `1a0a4d5` | adversarial review |

**Root cause, and it is not carelessness.** `check_claims.py` verifies that a rendered claim *resolves
to a registry entry with a live data reference*. It does not verify that the entry is **true**. Claims
1 and 3 were never tested — the scripts computed two windows and the prose asserted a third thing.
Claim 4 had no null model. A validation gate that checks provenance but not inference will pass a false
finding every time.

**Consequence for the paper:** every headline number needs a *stated null or comparison* before it is
written, not after.

---

## 3. Contributions, stated for a referee

**C1 — A control-group design for adversary-network measurement.**
The network runs one mirror per target country on shared infrastructure with a shared upstream source
pool, converting an n=1 case into a seven-unit panel with 869–1141 daily observations each.
*Evidence:* seven `*_viz.json` files **[V]**; cross-mirror source overlap 758 of 938 shared with at
least one peer, pairwise Jaccard 0.325–0.467 **[R]**.
*Limit:* seven units is small; donors are not exchangeable (different launch dates, languages, target
news cycles); and the design cannot separate a change in operator behaviour from a change in what
CheckFirst's collector sees.

**C2 — A full-coverage negative provenance census.**
Across all 141,808 articles, the 941 credited sources sum to exactly 141,808 (coverage 1.0000). The
Hungarian pro-government press appears **zero** times. One pro-government commentator's personal
Telegram channel appears 76 times (0.05%); nationalist-fringe channels 130 (0.09%) **[V]**.
*Limit — must sit inside the claim sentence, not in a caveat:* this measures the mirror's **own credit
label**. It is a statement about *declared* provenance, in one direction only, and laundering through
an intermediate repost makes an original invisible by construction.

**C3 — A dated output interruption, network-largest in its window but not exceptional against the mirror's own history, with no cause claimed.**
Output fell 63.7% from the Feb–Mar 2026 baseline (243.6/day) to May–Jun (88.5/day), while six peers
moved +1.6% and none fell more than 16.3% **[V]**.
*The timing is the finding, and it cuts against the obvious reading:* **13 April — the day after the
vote — is April's highest day at 356 articles.** Output holds near 223/day for a further twelve days.
The step lands around **27 April**, a **15-day gap** **[V]**.
*Placebo inference, now reproduced independently* **[V]**: across all 185 admissible two-month windows
in the seven-mirror panel the treated window ranks **1st (p = 0.0054)**; within Hungary's own 24
windows, **1st (p = 0.0417)**.
*And the correction that matters* **[V]**: Hungary is the **noisiest mirror in the network** — its
two-month swings have sd 58.8%, against Romania's 13.2%. An unnormalised extremeness contest is partly
won by being noisy. Normalising each window by its own mirror's volatility puts the treated window at
**−1.08 sd, rank 13/185 (p = 0.0703)**. The drop is the largest in its window; it is **not exceptional
against this mirror's own history.** Report both, lead with the second.
*Still to reproduce:* log DiD −1.024 and the 136-specification sweep spanning −65.1% to −38.1% **[R]**.
*Limit:* the recovery restores the original source composition to within five points, which is more
consistent with an **interrupted supply** than an editorial response.

---

## 3b. The instrument, and what it did to C3

`scripts/analyse_network.py` generalises the design: any mirror, any event, plus a **blind scan**
that finds interruptions without being told where to look. Pointing an instrument at things you did
not choose in advance is the difference between a case study and a tool — and it cost us the finding.

**Pre-specified events** (only dates this repo can source; see `catalog/events.json`):

| event | change | z vs own history | normalised rank |
|---|---|---|---|
| Hungary 2026 parliamentary | −63.7% | −1.06 | 13/185 |
| Romania 2024 presidential (annulled) | −5.6% | −0.42 | 40/185 |
| Romania 2025 rerun | **+16.5%** | +1.25 | 161/185 |

**Blind scan, now on the full 101-mirror manifest** (49 MB, `fetch_pravda.py --all`): **1,948
two-month windows**. Hungary 2026-04 ranks **207th — the 11th percentile** — and none of the fifteen
largest episodes is Hungary's. Restricted to the seven regional country mirrors it is 13/185, the 7th
percentile. The estimate is stable across pools; what changes is that a 100-donor reference makes its
ordinariness unmistakable. Hungary's own series holds a second comparable episode in **August 2024,
with no election near it** **[V]**.

**Donor exchangeability, stated because it bounds the above:** the 101 domains are not 101 comparable
country mirrors. They include language mirrors (francais, catalan, spanish), sub-national ones (wales,
scotland), thematic ones (trump), apparent duplicates (car / rca) and network roots. That pool is a
defensible **volatility reference distribution** and a poor **like-for-like control group**. The tool
reports both and requires the analyst to say which a claim rests on.

**What this means.** Interruptions in this network are **common and mostly not election-aligned**. The
two other votes we can date produced a small dip and a *rise*. C3 therefore cannot carry an
election-related reading: the Hungarian episode is real, is the largest in its own window, and is
otherwise ordinary. Combined with the 15-day onset gap and the restored source composition, three
independent lines now point the same way — **an interrupted supply, not a response to a result.**

C2 (the census) is untouched by any of this and remains the paper's strongest claim.

---

## 4. What is cut

1. **All LLM-grooming / "written for machines" framing.** No model-side measurement exists here.
2. **The technique-overlap statistic.** At or below chance; n=3 domestic cases, single coder, no
   inter-rater reliability, no codebook. Survives only as a qualitative appendix, if at all.
3. **The live cross-check as evidence about consumption.** Retired to: *these channels were observably
   still publishing on the capture day.*
4. **Percentage framing for small-base sources.** News Front "+25%" is +1.8 articles/day on a base of
   7.1 against a 156.4/day decline. State rates.
5. **The 4.0% category figure as evidence about intended audience.** These are the mirror's own section
   labels, and own-country share is unremarkable in-network (Czechia 1.0%, Slovakia 4.0%, Moldova
   28.5%) **[R]**.
6. **All 3D scenes.** Editorial. They belong on the website and cannot appear in a paper.

---

## 5. Methods to strengthen, in priority order

| # | Analysis | Tests | Effort | Owner |
|---|---|---|---|---|
| M1 | Three-window decomposition (baseline/trough/recovery) | interruption vs diet change | done `53dec10` | — |
| M2 | Interrupted time series with **estimated** changepoint, all seven mirrors | when the break lands, one event or several | small | automatable |
| ~~M3~~ | ~~Randomisation inference + volatility-normalised rank~~ | **done** — pooled 1/185 (p=0.0054), within-unit 1/24, volatility-normalised **13/185 (p=0.070)** | done | `derive_peer_control.py` |
| M4 | Specification curve over window × gap × offset | is the estimate a property of the data or of window choice | small | automatable |
| M5 | Collector-artefact audit: network-wide single-day collapses | does the instrument manufacture drops (note 2026-04-25 = 28 articles) | small | automatable |
| M6 | **Telegram archive reconstruction** — back-page `t.me/s/` for the three channels, Feb–Aug 2026 | **the decisive question:** did the channels stop publishing, or did the mirror stop crediting them? | medium | **PI** go/no-go |
| M7 | Manual pass over all 941 sources for Hungarian markers | hardens the headline zero from "robust to my string list" to "exhaustively verified" | ~1 day | **PI** — this is the number that will be quoted |
| ~~M8~~ | ~~Extend donor pool to the full 101 mirrors~~ | **done** — 1,948 windows; Hungary at the 11th percentile. Next: classify the 101 into country / language / thematic so the control group is like-for-like | done | `fetch_pravda.py --all` |

**M6 is the study's hinge.** If the channels kept publishing through May–June, the interruption is on
the mirror's side. If they went quiet, it is upstream. Our current data cannot distinguish these, and
the paper must not pretend otherwise until this is run.

---

## 6. Figure programme

One shared generator (`scripts/figlib.py`, stdlib, SVG) emitting a print and a web variant from
identical geometry. Palette cut to three roles — focal / neutral grey / annotation — because the
current site palette collapses under deuteranopia (amber vs sage simulate to contrast 1.00) **[R]**.
Redundant encoding by line weight and direct end-labels so every figure survives greyscale.

| # | Figure | Purpose | Encoding | Grade |
|---|---|---|---|---|
| **F1** | Peer-normalised event study | the lead result | two panels: seven 7-day trailing means indexed to Feb–Mar = 100; below, Hungary ÷ peer *median* with a pre-period percentile band. Separate rules for election day and estimated onset so the 15-day gap is **visible, not argued** | research |
| **F2** | Specification curve | **this is how uncertainty is shown** | 136 estimates sorted, with an aligned dot-matrix of analytic choices | research |
| **F3** | Placebo distribution | is the drop extreme | dot strip of every unit-by-window estimate, Hungary marked, rank in caption | research |
| **F4** | Diet decomposition | interruption vs replacement | stacked daily area, three bands, showing collapse *and* restoration | research |
| **F5** | Provenance census | the zero | ranked source bars at true scale with an explicit zero row — **not** an empty chart | research |
| **F6** | Technique overlap | the null | presence/absence matrix with the chance expectation drawn as a reference line | research |
| — | 3D well, network graph, sediment | — | — | **website only** |

**On uncertainty:** the data are a **census, not a sample**. Sampling error is not the relevant
uncertainty and a confidence interval would fabricate a sampling model that does not exist. Analytic-
choice uncertainty is the real quantity — hence F2, and hence reporting the **range** (−65.1% to
−38.1%) rather than a point estimate in the abstract.

**On nulls:** F6 draws the chance expectation as a reference line so the reader sees the observed value
falling *below* it. A null is shown, not described.

---

## 7. Paper architecture

**Working title:** *A propaganda network as its own control group: provenance and disruption in the
Pravda mirror targeting Hungary's 2026 election*

**RQ1.** Does the mirror targeting Hungary credit Hungarian domestic media? *(census; answerable now)*
**RQ2.** Does its output behave anomalously around the election relative to its sibling mirrors?
*(panel; answerable now)*
**RQ3.** Is any anomaly attributable to the mirror or to its upstream supply? *(requires M6)*

| Section | Words |
|---|---|
| Introduction | 700 |
| Related work — IO measurement, Portal Kombat, control designs | 800 |
| Data — CheckFirst, coverage, what is *not* available (no article-level timestamps) | 700 |
| Method — panel construction, placebo inference, specification curve | 900 |
| Results — RQ1 census, RQ2 interruption, RQ3 or its impossibility | 1,400 |
| Limitations | 500 |
| Discussion | 600 |

**Supplementary:** full 938-source enumeration, specification-curve grid, placebo tables, the catalog
and its schema, the two validation gates, and the interactive site as a companion artefact.

**Limitations paragraph (draft, to ship substantially as written):**

> This study measures declared provenance and daily volume, not content, reach or effect. Source
> attributions are the operator's own metadata and cost nothing to omit or launder through an
> intermediate repost, so the provenance census bounds what the mirror *claims* to ingest, not what it
> ingests. No article-level timestamps exist in the public dataset, which forecloses finer-grained
> event studies and makes any sequence or direction claim uncomputable; we report that rather than
> approximate it. The panel has seven units and one treated unit, donors are not exchangeable, and the
> treated window was chosen ex post, so the placebo distribution is a descriptive reference rather than
> an exact test. We cannot separate operator behaviour from collector behaviour: a change in what
> CheckFirst observes is observationally equivalent to a change in what the mirror publishes. The
> DISARM coding is by a single coder without an inter-rater reliability check, and we report the
> resulting overlap as a null. Finally, the interruption's onset is fifteen days after the election it
> is temporally associated with; we describe that association and explicitly decline to claim cause.

---

## 8. Venue

Target a venue publishing empirical work on information operations and computational social science
with a strong data-availability norm; a web-science or misinformation-focused venue is the natural
first choice, with an HCI/visualisation venue as the backup route for the design-and-artefact framing.
**Do not** submit to an ML-security venue: without model-side measurement, the grooming angle has no
result to offer that audience. Confirm current scope and deadlines directly from each venue's site —
none are asserted here.

---

## 9. Ethics, data and reproducibility

- **Upstream data is third-party and moving** (CheckFirst updates hourly). Cite a **dated snapshot**
  with the retrieval date and archive the exact `*_viz.json` files used; do not cite a live URL alone.
- **`data/raw/` is gitignored.** The replication package ships `data/derived/` plus the scripts, and
  documents how to re-fetch. Redistribution of CheckFirst's data must follow their terms.
- **Named individuals.** The census identifies a named pro-government commentator by handle. Current
  handling is incoherent — the page pseudonymises while `convergence.json` publishes the handle.
  **Decide one way and make it consistent**, and ensure a non-inference sentence travels in the same
  object as the number.
- **LLM-assisted coding must be disclosed.** Catalog verification used LLM agents. In 2026 this
  requires an explicit methods declaration, including what was human-verified.
- **The smear filter is a research-ethics decision**, not a technical one: withheld content is a
  documented, fixture-tested exclusion criterion and belongs in the methods section.
- **Anticipate the quotation risk.** A negative provenance result is quotable by the actors documented.
  The mitigation is structural: state in the same paragraph that a null on *declared* provenance is not
  a null on influence, and that the domestic operation was the larger share throughout.

---

## 10. Work plan

1. **M7** — manual 938-source pass *(PI; gates C2)*
2. **M2–M5** — changepoint, placebo, specification curve, collector audit *(automatable; gates C3)*
3. **M6 pilot** — two weeks of Telegram back-paging, then go/no-go *(PI decision; gates RQ3)*
4. **F1–F6** via `figlib.py` *(automatable once 1–2 land)*
5. Draft in section order; limitations first, since it constrains every other claim
6. Replication package, snapshot archiving, disclosure statements *(PI)*

---

## 11. What we are not doing

- **No two-sided corpus, no sequence analysis.** Decided against and re-affirmed: a domestic clock
  starting in 2026 against a Russian record from 2024 measures our collection dates, not the actors.
- **No causal claim about the interruption.** The 15-day gap and the collector-artefact ambiguity both
  forbid it.
- **No effect claims.** Nothing here measures persuasion, and the campaign that used the most AI lost.
- **No expansion of the DISARM coding to rescue the overlap statistic.** More single-coder tags do not
  fix an absent codebook or a missing reliability check.
