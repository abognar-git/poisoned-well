# poisoned-well

**A Russian propaganda network runs one website per target country. That means
every claim you make about one of them can be checked against a hundred
siblings — including the claims you would rather keep.**

I built the instrument that does the checking and pointed it at the mirror aimed
at Hungary's April 2026 election. It took away four of my own published findings
and cut a fifth down to a fifteen-day gap it cannot explain. What survived is one
number: across **143,488 articles** and the **945 sources** that account for all
of them, the Hungarian pro-government press is credited **zero times**.

<sub>**How to read this.** The section below stands on its own — it is the whole
project in about five minutes, in plain language. Everything after it is the
evidence: how the instrument works, one finding followed from claim to
retraction, then the results for someone who wants to check the numbers, then
what went wrong and what this cannot show. Stopping after the first section is a
perfectly good way to read it.</sub>

> ### ▶ [Read the investigation](https://abognar-git.github.io/poisoned-well/)
>
> The findings here are also published as an evidence-first website: every
> rendered fact carries a `§` marker resolving to a claims registry, every
> withdrawn claim carries a `▲` marker showing the sentence as it ran and the
> data that killed it, and a build gate fails if either stops resolving.

---

## What this is, in one page

Russia runs a network called Pravda, or Portal Kombat. It is **101 websites**,
one per target country or language, publishing **17.7 million articles** between
them. They employ no journalists and write nothing. They republish fringe Telegram
channels and Russian state outlets as clean, crawlable news, and researchers who
have audited them assess that a design like that — enormous output, almost no
readers — is aimed less at the people of the country named on the domain than at
the machines that now answer questions about it.

One of those sites points at Hungary. It went up in March 2024 and has published
on **890 of the 893 days** since. Hungary held a national election on 12 April
2026; the government lost. That is the case this project started as.

**The thing that makes it a study rather than a story is the other hundred
sites.** A franchise that builds one mirror per country from one template, on
shared infrastructure, from a shared upstream pool, has accidentally built its
own control group. Whatever the Hungarian mirror did in April 2026, you can ask
what the Romanian, Polish, Slovak, Czech, Moldovan and German ones did in the
same weeks — and then what all 101 did across every two-month window they have.
That turns one case into **1,948 comparable windows**.

So I built that instrument. It has two modes, and only one of them can hurt you.
**Events** tests a date you already suspect, which at best confirms what you went
looking for. **Scan** ranks every window in the network without being told where
the election was.

**Then I pointed it at my own published findings, and it took four of them.**

| # | What I published | What the data says |
|---|---|---|
| 1 | The Russian institutional layer carries the recovery | The three *collapsed* channels supply **101.4%** of the rebound — more than all of it |
| 2 | The mirror changed what it eats | Invalid comparison — my capture reads only the `/en/` surface, the census counts every language |
| 3 | No surge for the election it was aimed at | March 2026 is the mirror's **highest month ever**; only the *difference* survives, +24.0% against a +12.4% peer mean |
| 4 | What the two sides share is a grammar | Observed overlap **4**, expected by chance **5.00**. At or below chance |

**All four were properly sourced.** Every one passed a validation gate that
checks that a rendered claim resolves to a registry entry with a live data
reference. That gate cannot check whether the entry is *true*, and claims 1 and 3
were never tested at all — the scripts computed two windows and the prose asserted
a third thing. **A gate that checks provenance but not inference will pass a false
finding every time.** That is the most portable thing in this repository.

A fifth finding did not die but lost most of its size, and how it shrank is worth
more than the finding was. Output from the Hungarian mirror fell **63.7%** after
the election, from 243.6 to 88.5 articles a day, while its six regional siblings
moved **+1.6%** on average and not one fell more than 16.3%. That is real,
large and correctly measured. Then:

| Test | What it asked | Result |
|---|---|---|
| Peer window | did the siblings do it too, in the same weeks? | **−63.7% vs +1.6%** |
| Placebo, raw | where does it rank among all 185 regional windows? | **1st**, p = 0.0054 |
| Volatility-normalised | is Hungary simply the noisiest mirror? (sd 58.8% against Romania's 13.2%) | **−1.08 sd, 13th**, p = 0.0703 |
| Blind scan, 101 mirrors | ranked against 1,948 windows, with nobody telling it where the election was | **207th**, p = 0.1063 |
| Onset date | when did it actually start? | **≈27 April — 15 days late** |

13 April, the day after the vote, is April's **highest single day at 356
articles**. Output holds near 223/day for a further twelve days before the step
appears. None of the fifteen largest interruptions in the whole network is
Hungary's, and Hungary's own series holds a second comparable collapse in
**August 2024** with no election near it. Of the other two national votes this
repository can date, Romania's annulled 2024 round produced −5.6% and its 2025
rerun produced a **+16.5% rise**.

**Interruptions in this network are common, and they are mostly not aligned to
elections.** The drop is real, it is the largest in its own window, it is
ordinary against the mirror's own history, it starts a fortnight after the event
it gets attributed to, and the recovery restores the original source mix to
within five points. I read those five facts as more consistent with an interrupted
supply than with a response to a result. **That reading did not survive.**
Back-paging the three channels the drop is concentrated in shows they went on
publishing straight through it, so whatever was interrupted was mostly not the
supply — finding 6 below. **I claim no cause for it either way.**

What is left standing is the census. Across every article the mirror has
published, and every source it credits — 945 of them, accounting for 100.00% of
its output — the Hungarian pro-government press appears **zero times**. It is not
a clean zero: one pro-government commentator's personal Telegram channel is
credited 96 times (0.07%), and nationalist-fringe channels a further 149 (0.10%).
A thread exists; a pipeline does not.

That matters because roughly **90%** of the disinformation in Hungary's 2026
election was domestic in origin. The loud foreign operations — deepfakes, fake
outlets, AI personas — were real, were debunked, and receded after the vote. The
domestic machine was the larger story, and this measurement says it was **not
this mirror's raw material.**

---

## What this cannot tell you

Stated here rather than at the bottom, because two of the four retractions above
happened by ignoring exactly this list.

**It cannot tell you that anyone was persuaded.** Nothing here measures reach,
belief or votes. No study has demonstrated that AI-enabled disinformation
measurably changed the result of any election, and this one does not either.

**It cannot tell you what the mirror actually ingests — only what it says it
does.** The census measures the operator's own credit labels, in one direction.
Laundering through an intermediate repost makes an original invisible to it by
construction. That limit belongs inside the claim sentence, not in a footnote.

**It contains no model-side measurement of any kind.** The framing that this
network is "written for machines" comes from other people's audits — NewsGuard,
DFRLab, the American Sunlight Project — and appears here only as an attributed
assessment, never as my result. A peer-reviewed test (Alyukov et al., *HKS
Misinformation Review*, October 2025) found far lower contamination rates on
data-void prompts and disputes how far the audit figures generalise. **Nobody,
here or elsewhere, has traced a specific article from this mirror into a specific
answer.**

**It cannot separate the operator from the collector.** A change in what
CheckFirst's scrape observes is observationally equivalent to a change in what the
mirror publishes.

**It cannot tell you why the mirror stopped crediting channels that were still
publishing.** The study's hinge has now been run: Telegram's public preview
back-paged for the three channels across February to August 2026, 55,597 posts,
ids and timestamps only. It settles the narrower question and it costs this
project a reading — the channels did not go quiet. What nothing here separates is
a block from a rebuild, a redirect or an instruction, so I claim no cause. Finding
6 below.

**Convergence is never coordination.** Where the Russian operation and Hungarian
domestic campaigns used the same techniques, that is measured, reported as a null,
and carries no implication whatsoever that domestic actors were directed by
anyone. The clearest overlapping case — a fabricated conscription claim built
twice — comes with the source's own conclusion attached: *no evidence that Fidesz
is behind the Russian campaign.*

---

## How the instrument works

The data is CheckFirst's public hourly scrape of the Pravda network: per-mirror
daily article counts and per-source credit totals. No article text, and **no
article-level timestamps** — which forecloses any claim about which side of a
narrative moved first, so this project does not make one.

```
scripts/fetch_pravda.py --all          101 domains, ~49 MB, hourly upstream
scripts/analyse_network.py --scan --events --donors all --top 15
```

**The panel.** Each mirror becomes a monthly series. First and last months are
partial, so they are excluded from every comparison. For a given cut month, the
two full months before it are the baseline and the two full months after it are
the outcome, and the change is measured against the same window in every other
mirror.

**Events mode** takes only dates this repository can source. They live in
`catalog/events.json`, and a date without a source sits in `needs_verification`
and is not analysed — five of the eight are there.

**Scan mode** ignores the event list entirely. It computes the same statistic for
every mirror in every window and ranks them, so the question becomes *where does
the Hungarian episode sit among all of them* rather than *is the Hungarian episode
big*.

**Two things it reports that I did not want it to report.** First, each estimate
is normalised by the mirror's own historical volatility, because an unnormalised
extremeness contest is partly won by being noisy and Hungary is the noisiest
mirror in the network. Second, the donor pool is stated explicitly, because the
101 domains are **not** 101 comparable country mirrors — they include language
mirrors (`francais`, `catalan`, `spanish`), sub-national ones (`wales`,
`scotland`), thematic ones (`trump`), apparent duplicates (`car` / `rca`) and
network roots. That pool is a defensible **volatility reference** and a poor
**like-for-like control group**, and the tool makes the analyst say which one a
claim rests on.

### The evidence layer

Everything rendered on the site carries a marker.

- **`§`** resolves to `catalog/claims.json` — 33 registered claims, each with
  status `verified`, `live-data` or `assessment`, its sources, and its caveat.
- **`▲`** resolves to `data/derived/research.json`, parsed from `RESEARCH.md` —
  the five corrections, the root cause, the limits on each contribution, the six
  pieces of framing cut from the paper, the two decisive tests not yet run.
- Dotted terms resolve to `catalog/glossary.json` at first use.

`.github/workflows/validate.yml` runs four gates on every push and pull request.
`check_catalog.py` validates the 24 case files and
runs 47 fixtures against the personal-smear filter. `check_claims.py` fails if a
`§` or `▲` marker does not resolve, if a catalog URL points at propaganda
infrastructure, **or if any correction in the research record stops being surfaced
anywhere on the page** — the one thing this project must never quietly do is stop
showing what it got wrong. `check_readme.py` re-checks the figures registered in
its `CLAIMS` list — in this file, in `RESEARCH.md`, in the claims registry and on
the page — and fails if a correction stops being cited by commit. The same job runs
`build_network.py --check` and re-derives `research.json` and the figures, failing
if either parted company with its generator.

The fourth is the one that matters most, and it is late. `check_readme.py` and
`check_claims.py` both verify that a marker's id *resolves* — and an id inside an HTML
comment, or one whose wiring call a refactor deleted, resolves perfectly and shows the
reader nothing. `check_render.py` serves the tree, renders it in headless Chrome and
counts what is in the DOM. Deleting one line of marker wiring drops a correction's ▲ and
leaves the other three gates green; this one fails.

### Two rules the code enforces

**Propaganda domains are never hyperlinked.** Citing them directly leaks referrers
and donates inbound-link signal to the thing being studied. A blocklist gate fails
the build if a catalog URL points at one; the site cites the researchers or the
generated data instead.

**Personal-smear specimens are withheld.** The live capture pulls real posts, and
some of them are sexual-abuse allegations against named private individuals. A
regex filter with 39 must-block and 8 must-pass fixtures keeps them out of the
page; they stay in the case files, described rather than reproduced.

---

## One finding, start to finish

The clearest way to show what this instrument is for is to follow the finding it
destroyed.

**What I published.** The Russian operation and the Hungarian domestic campaigns
share a grammar. Four DISARM techniques appear on both sides — targeted
advertising, invented personas, smears, AI-generated images. It read well. It was
sourced: every technique tag came from a case file, every case file from named
researchers.

**What was missing.** A null model. I had never asked what overlap *chance alone*
produces between a set of 9 techniques and a set of 25 drawn from the same
framework.

**What the answer is.** 5.00 if you draw from the 45-technique catalog pool, or 6.25 if you draw only from the 36 techniques any case actually used. **The
observed overlap is 4.** It is at or below chance in both universes.

**What that means for the claim.** There is no measurable shared method. Worse,
the claim could not have carried weight even had the number been higher: three
tagged domestic cases, a single coder, no inter-rater reliability check, and a
single tagging decision moves the share by roughly 11 points.

**What is on the site now.** The null, reported as a finding, with the chance
expectation drawn on the figure as a reference line so the reader can see the
observed value falling below it. The section heading that used to say *"The same
grammar"* now says *"What Hungary built itself"*, and the withdrawn sentence is
one click away behind a `▲` marker, struck through, above the data that killed it.

**What it cost.** The most quotable sentence in the project. It was also the only
one that implied the two machines were connected, which is the exact claim this
evidence cannot support and the exact claim that would do real damage if wrong.

---

## How to read the numbers

**The data are a census, not a sample.** Every article the mirror published in the
window is counted, so sampling error is not the relevant uncertainty and a
confidence interval would fabricate a sampling model that does not exist. The real
uncertainty is analytic-choice uncertainty: how much the estimate moves when you
move the window, the gap and the offset. Where that matters, the range is reported
rather than a point estimate.

**p-values here are placebo ranks, not tests.** The treated window was chosen after
the fact, so `p = 0.0703` means *this window sits 13th of 185 once each is
normalised by its own mirror's volatility* — a descriptive reference, not an exact
test. It is reported because it is the honest way to say "large, but not
unprecedented".

**Percentages on small bases are not reported as percentages.** A source moving
from 7.1 to 8.9 articles a day is +25%, and quoting that beside a 156-a-day
collapse is misleading. The site shows rates.

**`[V]` and `[R]`.** In `RESEARCH.md`, figures marked **[V]** were recomputed
directly from the raw data by me; **[R]** figures come from a referee pass and are
not yet independently reproduced. Nothing marked `[R]` appears in this README.

---

## Figures

Every figure is regenerated from `data/derived/` by `scripts/make_figures.py`, as
a light and dark pair. Colour never carries a distinction on its own — the site's
own amber-and-sage palette collapses under deuteranopia — a referee figure,
marked `[R]` in `RESEARCH.md` and not reproduced here, which is why the number
itself is not quoted — so the figures use one focal colour, neutral grey, and direct
end-labels, and survive greyscale.

![Monthly output of seven mirrors of one network; the Hungarian line falls 63.7% after April 2026 while the six others hold roughly flat](docs/figures/peer_event_study_dark.svg#gh-dark-mode-only)
![Monthly output of seven mirrors of one network; the Hungarian line falls 63.7% after April 2026 while the six others hold roughly flat](docs/figures/peer_event_study_light.svg#gh-light-mode-only)

<sub>**F1 — the lead result, and the thing that complicates it.** The election and
the estimated onset are drawn as separate rules, so the fifteen-day gap is visible
rather than argued.</sub>

![Sources the Hungarian mirror credits, by article count, with an explicit zero row for the Hungarian pro-government press](docs/figures/provenance_census_dark.svg#gh-dark-mode-only)
![Sources the Hungarian mirror credits, by article count, with an explicit zero row for the Hungarian pro-government press](docs/figures/provenance_census_light.svg#gh-light-mode-only)

<sub>**F5 — the zero.** Drawn as an explicit empty row rather than an absent bar,
because the absence is the finding and an empty chart looks like a rendering
failure.</sub>

![The two-month change of every donor mirror over the same window, with the Hungarian value marked at rank 207 of 1,948](docs/figures/placebo_distribution_dark.svg#gh-dark-mode-only)
![The two-month change of every donor mirror over the same window, with the Hungarian value marked at rank 207 of 1,948](docs/figures/placebo_distribution_light.svg#gh-light-mode-only)

<sub>**F3 — why the headline shrank.** Every donor mirror over the same two months.
Hungary is far left, and it is not alone there.</sub>

![Four DISARM techniques observed on both sides against a chance expectation of 5.00 to 6.25](docs/figures/technique_overlap_dark.svg#gh-dark-mode-only)
![Four DISARM techniques observed on both sides against a chance expectation of 5.00 to 6.25](docs/figures/technique_overlap_light.svg#gh-light-mode-only)

<sub>**F6 — a null, shown rather than described.** Chance is the dashed rule. The
observed value sits below it.</sub>

---

## What this all adds up to

**The contribution is the design and the census, not the drama.**

A franchised adversary network is a panel waiting to be used. One mirror per
target, built from one template, is the architecture that makes these operations
cheap to run — and it is the same architecture that hands an investigator a
control group. Almost every published study of an influence operation is n=1 by
construction: one country, one campaign, one direction of travel, and no way to
know whether the pattern is special or simply what this kind of network does
everywhere. It does not have to be.

**The census is the strongest claim here and the least exciting.** A full-coverage
negative result — 143,488 articles, 945 sources, coverage 1.0000, zero credits to
the domestic pro-government press — is a boring sentence that survived every test
I could put to it, while the interesting sentence about a post-election collapse
lost four fifths of its weight in five tests.

**And the failure mode generalises past Hungary.** I had a validation gate,
a claims registry, source verification on every case file, and a rule that no
number appears on the page unless a script generated it. All of that was working.
Four claims were still wrong, because every one of those mechanisms checks
*provenance* and none of them checks *inference*. The fix is not a better gate. It
is that **every headline number carries a stated null or comparison in the same
breath as the number** — in the claim itself, where a reader cannot take the figure
without also taking what it was measured against.

---

## What I got wrong, and what this does not show

Six, in the order they were found — plus a seventh, numbered 4b below because it
arrived after the others and is not a retraction. The first four are the
retractions; the fifth is the one I found while fixing them; the sixth retires a
reading the other five had all left standing.

**1 — I read a recovery off the wrong three channels.** I published that the
Russian institutional layer carried the mirror's rebound. I had summed the three
*most-captured* channels rather than the three that actually collapsed. Summing
the right ones: the collapsed set supplies **101.4%** of the rebound — more than all of it, so
everything else nets **−1.0 articles/day**. Their share of output runs
67.5% → 32.6% → 62.6%. The channels that fell are the channels that came back,
which is why "interrupted supply" became the reading and "editorial decision" did
not. Fixed in `53dec10`. What fell was the mirror's crediting of them, and reading
that as the channels themselves going quiet is the step finding 6 retires.

**2 — I compared a capture with a census.** I published that the mirror had changed
what it eats, on the strength of my own live capture. That capture requests only
the mirror's `/en/` pages; the census counts every language, and Hungarian is the
larger surface. On the days I captured, in August 2026, the census showed those
same channels credited in 60–77% of all articles. They had
never left. The claim is retired to the only thing it supports: these channels were
observably still publishing on the day I looked. Fixed in `53dec10`.

**3 — I asserted an absence I had never measured.** I published that there was no
campaign surge. The scripts computed a baseline window and an after window; the
prose asserted a third thing about the campaign period that neither of them
touched. March 2026, at 269.6 articles/day, is the **highest month in the mirror's
entire series**. What survives is only the comparison — a +24.0% February-to-March rise against a +12.4% peer mean, roughly double, though every sibling rose too.
Fixed in `53dec10`.

**4 — I called four a lot without asking what chance produces.** Covered in full
above. Fixed in `1a0a4d5`.

**4b — I labelled a language "filler".** The theme tags on captured specimens ran off a
single Latin-script lexicon, so **98.3% of Russian-language items came back `filler`** —
not because they were off-topic but because the classifier could not read them. I made it
worse before I found it, by adding five Russian-language outlets on the same day and
roughly doubling the Cyrillic share. Themes are now scored against a per-language lexicon,
items no lexicon covers read `unscored` rather than `filler`, and the coverage is published
as a table so the gap is visible rather than inferred. Fixed in `e085410`.

**5 — I let the noisiest unit win a contest about extremeness.** Having found the
four above, I re-ran the placebo inference and reproduced 1/185 at p = 0.0054
exactly. Then I checked the volatility of each mirror and found Hungary is the
most volatile in the network: its two-month swings have a standard deviation of
**58.8%**, against Romania's 13.2%. Normalising each window by its own mirror's
volatility — standard practice in synthetic-control work, for exactly this reason
— moves the treated window to **−1.08 sd, rank 13 of 185, p = 0.0703**. Extending
the donor pool to all 101 mirrors moves it to **207 of 1,948**. Nobody made me run
either check.

**6 — I called it an interrupted supply without ever checking the supply.** The
mirror's credits to three Hungarian aggregator channels collapsed after the
election, and finding 1 and the conclusion near the top both read that as the
channels having gone quiet. Everything this repository holds is the mirror's side
of that relationship, so the reading was never tested — it was the more
comfortable of two possibilities that fit the same data equally well. Back-paging
Telegram's public preview reconstructs the channels' own output independently of
the mirror, and it does not support it. Across the 65 days of the trough the three
channels published on **65, 65 and 61** of them; their own volume fell **15.5%** on
average while the mirror's credits to them fell **82.9%**; credits per post went
**0.62 → 0.16**, **0.50 → 0.09** and **0.33 → 0.06**. The channels never stopped.
Most of what was interrupted was the crediting, not the supply. Two things keep
this from being stronger than it reads. The decision rule sits **0.5 percentage
points** from concluding the interruption was entirely on the mirror's side, which
is close enough that the margin belongs in the finding and not just in the data;
and a post deleted before the walk is invisible to it, so the counts are lower
bounds and the bias runs toward exactly the conclusion drawn here. This is the
weaker version of it. Why the crediting stopped is past anything this project can
reach. Retired in `aae5df5` — the walk and the join, not a code fix.

**The pattern in all six.** Every one of them pointed the way I wanted it to
point. That is not a coincidence and it is not carelessness — it is what happens
when the analysis and the argument are written by the same person in the same
session, and the only defence I have found is to build the tool that can
contradict you before you need it to. Finding 6 is that defence working: the walk
was written to test a question the prose had already answered, and it came back
with the other answer.

### What this does not show

Beyond the limits stated near the top: the panel has seven units, one of them
treated, and the donors are not exchangeable — different launch dates,
different languages, different national news cycles. The DISARM coding is by a
single coder with no inter-rater check. The catalog's 24 case files carry stated
attribution confidence ranging from *confirmed* to *contested*, and the timeline
now prints that confidence rather than a bare sponsor name. And this repository
holds no domestic-output corpus at all, so every statement about the Hungarian
domestic machine is sourced to other people's measurement — chiefly Lakmusz,
Telex, Political Capital, EDMO — and not to mine.

---

## What else this repository publishes

Two datasets sit outside the analysis above and are the reason a researcher might
want this repo rather than its conclusions.

**`data/panel/` — the network's credit graph, all 101 mirrors.** Not the seven-unit
peer panel of the event study: mirror × day articles, mirror × day × credited-source
credits in monthly shards, and the transpose — one row per source, with how many
mirrors it feeds and how exclusively, which is the question an analyst usually
arrives with. Built by `scripts/derive_feeder_index.py` from CheckFirst's
`sourcesByDay` panels; current row counts and generation date are in
[`data/panel/MANIFEST.json`](data/panel/MANIFEST.json).

**Read [`data/DICTIONARY.md`](data/DICTIONARY.md) before computing on any of it.**
The daily panel carries only each mirror's top ten sources per day, so a
share-of-credits denominator changes underneath you unless you condition on that
set. Two of the three limits written down there have already produced a wrong number
in this project once. And a credit is the mirror's own claim about where it took an
item — never evidence that the credited channel participated, cooperated, or knows
the mirror exists.

**`data/archive/` — captured specimens.** An append-only, month-sharded JSONL record
of what the mirror and its credited channels actually published, accumulated hourly
since August 2026: headline or post excerpt, provenance, language, theme. It is an
accumulated observation, not something a clone can regenerate — running the capture
scripts extends it rather than reproducing it. It is a sample, and
`data/archive/coverage.json` says how much of one, computed as a set difference over
the ids each source issued. Browsable at
[the corpus explorer](https://abognar-git.github.io/poisoned-well/site/prototype/explorer.html).

---

## Running it yourself

Python 3.12, standard library only. No API keys, no build step, nothing to
install.

```bash
git clone https://github.com/abognar-git/poisoned-well
cd poisoned-well

# fetch the network. the seven regional mirrors are enough for the panel;
# --all pulls the full 101-domain manifest (~49 MB) for the blind scan
python3 scripts/fetch_pravda.py
python3 scripts/fetch_pravda.py --all --delay 0.5

# the DISARM framework and Meta's threat reports. derive_summaries.py reads the
# second one, so skipping this makes the next block fail on a clean clone
python3 scripts/fetch_frameworks.py

# the instrument. --events tests only dates catalog/events.json can source;
# --scan finds interruptions without being told where to look
# --top 15 because the text claims none of the fifteen largest interruptions is
# Hungary's; at the default of 12 the artifact cannot be checked against the claim
python3 scripts/analyse_network.py --events --scan --donors all --top 15

# regenerate every derived figure from the catalog and the raw data
python3 scripts/derive_summaries.py
python3 scripts/derive_peer_control.py     # the panel, timing and placebo
python3 scripts/derive_diet.py             # what the collapse was made of
python3 scripts/derive_convergence.py      # the census and the overlap null
python3 scripts/derive_research.py         # RESEARCH.md -> the site's ▲ layer
python3 scripts/make_figures.py            # light/dark SVG pairs for this README
python3 scripts/derive_feeder_index.py     # the 101-mirror credit graph -> data/panel/

# the gates. all three run in CI on every push, alongside a structural check on
# the network graph and a drift check on the derived files
python3 scripts/check_catalog.py           # schema, sources, smear fixtures
python3 scripts/check_claims.py            # markers, blocklist, corrections
python3 scripts/check_readme.py            # this file's registered figures vs data/derived
python3 scripts/check_render.py            # renders the page; asserts the markers are really there
```

Then serve the repo and open the prototype — `python3 -m http.server 8000` in the
repo root, then `http://localhost:8000/site/prototype/index.html`. Opening the file
directly does not work: the page is an ES module that reads `../../data/` and
`../../catalog/`, and browsers refuse both module imports and `fetch()` over
`file://`. Once served it needs no internet — with no network it falls back to the
committed figures rather than breaking.

**A note on the workflows.** `.github/workflows/refresh-data.yml` runs **hourly**:
it re-fetches the upstream feed, re-derives, re-captures the live specimens, merges
them into the archive, recomputes coverage, regenerates the figures, syncs this
file's registered numbers, re-runs the gates, and commits. (It commits every run: three generators stamp a time unconditionally.)
`rebuild-panel.yml` runs daily and is the only job that rebuilds `data/panel/` — the
credit graph needs the full 101-domain manifest, which is too much to pull hourly.
`validate.yml` runs the gates on every push. All three can also be run by hand from
the Actions tab, or with `gh workflow run <name>`.

That matters for the figures quoted above. They are correct as of the scrape
committed here, and the mirror keeps publishing — the pro-government
commentator's channel went from 76 credits to 78 during the session that wrote
this. `scripts/check_readme.py` is what catches the divergence: it re-checks the
figures registered in its `CLAIMS` list against `data/derived` and fails when they
part company. A number nobody registered is not checked — **including a second copy
of a registered figure**, which is how two of the numbers in this file went stale
under a green gate while it printed OK. It now refuses a registered fragment that
matches more than once, so a second copy has to be registered rather than silently
skipped, and it reaches beyond this file: the same census was restated in
`RESEARCH.md`, in `catalog/claims.json` and three times on the page, and had drifted
in every one of them.

---

## The other three

This is one of four projects asking the same question from different angles —
**what actually happens when AI meets an adversary, measured rather than
asserted.**

- **`poisoned-well`** (this one) — *the adversary at national scale.* The other
  three build an instrument and attack it. This one builds an instrument and turns
  it on its own conclusions, which is how four published findings became four
  retractions.

- **[`hunt`](https://github.com/abognar-git/model-abuse-hunt)** — *the platform
  hunting for misuse.* A criminal and a security researcher ask an AI the same
  question word for word, so the hard part is banning one and not the other, and
  getting it wrong means banning a real person.

- **[`triage`](https://github.com/abognar-git/alert-triage-copilot)** — *the
  defender's pipeline under attack.* An AI reads security alerts; the attacker
  wrote part of what it reads.

- **[`pyrite`](https://github.com/abognar-git/pyrite-assay)** — *what the refusal
  is worth.* How well can anyone tell a working answer from a plausible-looking
  broken one, without already knowing? All 448 attempts are browsable in an
  [interactive explorer](https://abognar-git.github.io/pyrite-assay/explorer.html).

They share a method more than a subject: build a measuring instrument rather than
a demo, put a number on every claim, attack your own result before anyone else
does, and write down the mistakes. Each of the four found a bug in its own
analysis that pointed the way its author wanted it to point. This one found four.

## License

Code — MIT, see [`LICENSE`](LICENSE).

Data — **not MIT.** See [`data/LICENSE`](data/LICENSE). Everything this project
computed — `data/derived/`, `data/panel/`, `data/DICTIONARY.md`, and the labels and
schema it assigned to the archive — is CC BY 4.0. The verbatim third-party text the
archive captured is not this project's to license and no rights over it are
granted; `data/LICENSE` gives the field-by-field split.

Data from [CheckFirst's Pravda Network collection](https://github.com/CheckFirstHQ/pravda-network),
[Meta's adversarial threat reports](https://github.com/facebook/threat-research), and the
[DISARM Foundation framework](https://github.com/DISARMFoundation/DISARMframeworks) (CC-BY-SA-4.0).
Full citations in the case catalog.
