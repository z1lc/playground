# Researching a company for Valuation Curves

One file per company: `companies/<slug>.json`. Read `companies/sierra.json` (private) and
`companies/apple.json` (public, with pre-1996 hand-entered figures) as worked examples —
they are the schema. `build_data.py` validates every field, so run

    uv run build_data.py --check --only <slug>

and fix everything it reports before you finish. A clean `--check` is the bar.

## What the chart plots

Valuation on a log Y axis against years since founding on a linear X axis. For public
companies the pipeline computes quarterly market cap itself from stockanalysis.com closes
and SEC cover-page share counts — **you do not research market caps for public companies.**
What you research is the private history: founding date, pre-IPO institutional rounds, and
the identifiers (ticker, CIK, IPO date) the pipeline needs.

## The inclusion floor

Include every round from the **first round led by a named venture capital firm** onward.
Exclude angel cheques, friends-and-family, and accelerator investments — but record them
with `"institutional": false` and `"plot": false` so the history survives without entering
the series. The floor test is mechanical: a named institutional lead.

Do **not** use series letters as the test. They are contested: the charter letter, the
press label, and the database label routinely disagree, and outlets have called the same
Sierra round both D and E. Put the label a reader will recognise in `roundName`, the
charter letter in `charterSeries` when an S-1 exposes it, and describe any disagreement in
`nameConflict`.

## The single most important rule

**`valuationUsd: null` is a normal, common outcome.** Across this dataset 38% of institutional
rounds disclose no post-money at all, and the rate is strongly era-dependent: half of 1990s and
2010s rounds, three quarters of 2020s rounds. For a company whose history is mostly pre-2015,
expect most rounds to have no valuation. Amount raised leaks — press releases, Form D, the
company's own marketing. Post-money almost never does; when it appears it is usually a
journalist's unnamed source, and the company may deny it.

A round carrying `amountRaisedUsd` with `valuationUsd: null` is a **correct, complete
record**. Set `"plot": false` on it — the round is real and shows in the tooltip, but it
is not a vertex, because inventing a Y coordinate is worse than an honest gap.

Never back-solve, extrapolate, or carry a valuation forward from a neighbouring round. If
you use a documented estimation heuristic, mark it `"valuationMethod": "estimate"`,
`"valuationConfidence": "soft"`, and state the heuristic in `note`.

## Where valuations actually come from, best first

1. **S-1 / F-1 preferred-stock note**, if the company ever listed. This gives the complete
   legal cap table — issue price per share and shares issued for every series — and
   reconstructs rounds nobody reported. Wealthfront's S-1 exposed a $25M round with zero
   public coverage anywhere. Use `"valuationMethod": "s1-cap-table"` and cite the filing.
   This is the highest-quality source available and it is systematically underused.
2. Company blog post or press release stating a post-money → `reported`, `confirmed`.
3. Two or more independent tier-1 outlets agreeing on a specific number → `reported`,
   `confirmed`.
4. A single outlet, or outlets that disagree → `reported`, **`soft`**.
5. Tender offer or secondary sale price → `tender` / `secondary`, `soft`, and say so in
   `note`. A secondary price is not a primary round valuation.

**Read the exhibits, not just the primary document.** Wealthfront's incorporation date, the
identity of its convertible-note counterparty, and an entire undisclosed round live only in
Exhibits 3.1, 3.2 and 4.2 — `grep -c UBS` on the S-1 body returns 0.

## Conflicts

A specific figure carried by several independent outlets beats a vague company statement.
Sierra's May 2026 round is recorded at $15.8B (Axios Pro, Quartz, Sacra) rather than the
company's "over $15 billion". When two well-sourced prices conflict, take the higher and
record the rejected figure in `note`.

## What counts as a point on the line

Plot (`"plot": true`): closed priced rounds, closed convertible notes, and company-run
tender offers — all of them events where money changed hands at a stated price.

Never plot: **terminated deals** (UBS's announced $1.4B acquisition of Wealthfront was
cancelled; nobody ever transacted at that price) and **secondary-market platform marks**
(Hiive, Forge, EquityZen publish indicative prices with no disclosed share count, so they
cannot be converted to a company valuation). Record both with `"plot": false` and the
appropriate `kind` so the research is preserved and the methodology can explain it.

## Founding date

`founded` is the **earliest formal founding** — a partnership counts. Apple is dated to the
1976-04-01 partnership, not the 1977-01-03 incorporation; Microsoft to the 1975 partnership,
not the 1981 incorporation. Where a company reincorporated in Delaware later, use the
original incorporation.

Set `foundedBasis` to `partnership`, `incorporation`, or `team-founding`, and put the
supporting detail in `foundedNote` — including the commonly-cited date when it differs.
**If you can only source a year, set `foundedPrecision: "year"` and `founded` to
`YYYY-01-01`.** Do not invent a month or a day.

## Known traps

- **Never cite macrotrends.net.** It ranks first in search for these queries and returns
  HTTP 402. Any citation of it is a page nobody read.
- **Annual market-cap aggregators disagree with each other, sometimes badly.** The pipeline
  cross-checks against both companiesmarketcap and stockanalysis and only fails when both
  disagree with it, because single rows are unreliable: companiesmarketcap's 2025 Palantir
  figure implies ~139M more shares than Palantir has ever reported, and its 2024 Tesla row
  contradicts its own shares-outstanding page. stockanalysis paywalls rows older than about
  five years. Treat either as a sanity check, never as a source — a filed share count from
  SEC beats both.
- **EDGAR's former-name metadata records filing-system dates, not charter dates.** It
  reports Wealthfront's rename as 2011-06-30; the legal rename was October 2010.
- **Aggregator pages without primary attribution are not sources.** If a claim appears only
  in Crunchbase, PitchBook, Tracxn or similar, put it in `note` as unverified — not in
  `valuationUsd`.
- Secondary sources near-universally report the *team* founding rather than any filing.

## Honesty requirements

- Every event needs at least one `sourceRefs` entry pointing at an https URL you actually
  fetched and read.
- Separate what you VERIFIED (you loaded the source) from what you RECALLED (training
  memory). A recalled figure may never be emitted as `confirmed`.
- Omit rather than guess. Anything you could not resolve goes in `unresolved[]`.
- Money fields are integers of USD or `null` — never strings, never floats, never "$1.5B".
- `datePrecision: "month"` requires day `01`; `"year"` requires `01-01`.
- A down round needs a `note` explaining it, or the build fails.
