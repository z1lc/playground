# FDE Jobs

A multi-stage pipeline that aggregates Forward-Deployed-Engineer-archetype job
listings from prestigious smaller (<1k employees) tech companies, runs them
through an LLM to surface a comparison schema, extracts structured values per
listing, and renders a static HTML visualization.

## Pipeline overview

| Stage | Input | Output | Built? |
|---|---|---|---|
| 1. Scrape | `companies.yaml` | `listings/*.md` + `manifest.json` | ✅ |
| 2. Categorize | `manifest.json` + `listings/*.md` | `categories.json` | ✅ |
| 3. Extract | `categories.json` + `listings/*.md` | `extracted/*.json` + `data.json` | ✅ |
| 4. Visualize | `data.json` + `listings/*.md` | `index.html` (GitHub Pages) | ✅ |

Per-stage LLM model (all via OpenRouter):

| Stage | Model | Why |
|---|---|---|
| 1 (HTML fallback) | `deepseek/deepseek-v4-pro:floor` | cheap, simple extraction |
| 2 (categorize)    | `google/gemini-3.1-pro-preview` | one-shot schema design — worth a smarter model |
| 3 (extract)       | `deepseek/deepseek-v4-pro:floor` | per-listing, runs once per row — keep cost down |

## Stage 1: scraping

### How to run

```bash
source ../KEYS                  # exports OPENROUTER_API_KEY
uv run fetch_listings.py        # fetches new data; uses cache <24h
uv run fetch_listings.py --refresh   # ignore cache, re-fetch all
```

PEP 723 inline deps — `uv run` handles them.

### Inputs

- `companies.yaml` — curated list of companies. Each entry: `name`, `slug`,
  `employee_estimate`, `ats` (greenhouse / lever / ashby / custom), `board_id`,
  `careers_url`. Edit freely.
- `OPENROUTER_API_KEY` env var — required only if any company has `ats: custom`.

### How a company is fetched

| ATS | Endpoint | Returns |
|---|---|---|
| `greenhouse` | `boards-api.greenhouse.io/v1/boards/{id}/jobs?content=true` | JSON, full HTML body inline |
| `lever` | `api.lever.co/v0/postings/{id}?mode=json` | JSON, body split across `description`/`lists`/`additional` |
| `ashby` | `api.ashbyhq.com/posting-api/job-board/{id}?includeCompensation=true` | JSON, full HTML body inline + structured compensation |
| `custom` | HTTP GET on `careers_url` → OpenRouter LLM extraction | Best-effort extraction; lower quality than direct API |

The `custom` path uses model `deepseek/deepseek-v4-pro:floor` via OpenRouter's
OpenAI-compatible chat completions endpoint. The `:floor` suffix routes to
the cheapest provider for that model.

### Title filtering

Include patterns (case-insensitive regex on title):

- `forward[- ]deployed`
- `implementation engineer`
- `deployment engineer`
- `solutions? engineer`
- `customer engineer`

Exclude patterns (any match disqualifies):

- `sales engineer` (too sales-side)
- `manager | director | head of | lead | principal | vp` (IC roles only)
- `intern`
- `investor | banker | finance | strategist | advisor | advocate | analyst | associate | consultant`
  (drops gimmicky non-engineering "forward deployed *" titles like Hebbia's
  "Forward Deployed Investor" or Runway's "Forward Deployed Finance Partner")

Each match is tagged with which include pattern hit (`title_match` field) so
Stage 2/3 can subset by archetype.

### Selection (top 2 per company)

When more than 2 listings match for a company, sort by:

1. `forward-deployed` matches before adjacent variants
2. Most recently posted
3. SF/NYC > Remote > other locations
4. Title (alphabetical, for determinism)

### Output: `listings/<slug>.md`

YAML frontmatter + cleaned-markdown body. Frontmatter fields:

`id`, `company`, `company_slug`, `company_employee_estimate`, `title`,
`title_match`, `location`, `remote` (onsite/remote/hybrid), `team`,
`posted_at` (ISO 8601), `url`, `ats`, `compensation_raw`.

Body is `markdownify`'d from the source HTML. Headings, lists, and emphasis
are preserved; `script`/`style` tags stripped.

### Output: `manifest.json`

Single JSON file Stage 2/3/4 read instead of globbing `listings/`. Schema:

```json
{
  "metadata": {
    "fetched_at": "<ISO 8601, only field that changes across re-runs>",
    "stage": 1,
    "model_used_for_custom_ats": "deepseek/deepseek-v4-pro:floor",
    "total_companies_attempted": 24,
    "total_companies_with_listings": 15,
    "total_listings_written": 24,
    "total_companies_skipped": 9
  },
  "listings": [{"id": "...", "company": "...", "company_slug": "...",
                "title": "...", "location": "...", "remote": "...",
                "team": "...", "url": "...", "title_match": "...",
                "ats": "...", "compensation_raw": "...",
                "markdown_path": "listings/<id>.md"}, ...],
  "skipped_companies": [{"slug": "...", "reason": "..."}, ...]
}
```

Listings are sorted by `id`. Skipped reasons: `no FDE-matching listings found`,
`fetch error: <type>: <msg>`, `unknown ats: <value>`.

### Caching

`raw_responses/<slug>.json` (and `<slug>.html` for custom-ATS HTML) is the
cache. TTL is 24h. `--refresh` ignores cache. Markdown is rendered on every
run from the cached source, so reformatting changes don't need a refetch.
The directory is gitignored.

Re-running within TTL completes in ~2 seconds and produces byte-identical
`listings/*.md`. `manifest.json` differs only in `metadata.fetched_at`.

### Compensation extraction

Best-effort:

- Ashby returns a structured `compensation.compensationTierSummary` string when
  `includeCompensation=true` is passed (e.g., `"$200K – $325K • Offers Equity"`).
- Greenhouse / Lever / fallback: regex on body HTML for patterns like
  `$120,000 - $180,000` or `$120K-$180K`.

Empty if neither found. Stage 3 can re-extract from the body via LLM.

## Stage 2: categorize

A single OpenRouter call to `google/gemini-3.1-pro-preview` reads every
listing and proposes a comparison schema. The output is `categories.json`,
which Stage 3 will use to extract per-listing values and Stage 4 will use
to render columns / facets.

### How to run

```bash
source ../KEYS
uv run categorize.py                     # 7-day cache, hash-invalidated when listings change
uv run categorize.py --refresh           # ignore cache, re-run the LLM
uv run categorize.py --max-categories 18 # default 15
uv run categorize.py --hint "lean toward technical depth signals"
```

Hard cap on `--max-categories` is 25. Re-runs hit cache in ~2s and produce
byte-identical `categories.json`.

### What "good" looks like

The schema is judged on whether categories DIFFERENTIATE listings, not
just describe them accurately. The prompt enforces:

- **`required_skill_areas`** (list[string]) is mandatory — controlled-vocab
  skill tags drawn from the corpus, ~10–20 distinct values total, ~2–5 per
  role. This is the centerpiece of the comparison.
- **Boolean budget ≤ 3** (soft warning). Booleans only earn their slot if
  they split the corpus non-trivially.
- **Banned generic axes**: `min_years_experience`, `comp_*_usd`, plus
  baseline-expectation booleans like `requires_strong_communication` /
  `production_shipping_required` / `ai_ml_required` / `equity_offered` /
  per-language booleans when a language list[string] exists.
- **Differentiation rule**: any category predicted ≥80% one value is
  forbidden (the prompt asks the LLM to self-check before returning).

### Output: `categories.json`

```json
{
  "metadata": {
    "generated_at": "2026-05-02T07:34:19+00:00",
    "model": "google/gemini-3.1-pro-preview",
    "n_listings_seen": 26,
    "max_categories": 15,
    "hint": null,
    "n_categories_kept": 12,
    "n_booleans": 3,
    "input_hash": "<sha256 of listings + model + hint + max_categories>"
  },
  "categories": [
    {
      "key": "<snake_case>",
      "name": "<human label>",
      "description": "<self-contained extraction prompt for Stage 3>",
      "type": "number | string | enum | list[string] | boolean",
      "unit": "<optional, only on type=number>",
      "enum_values": ["<required if type=enum>"],
      "examples": [<1-3 sample values>]
    }
  ]
}
```

The fixed type vocabulary (`number`, `string`, `enum`, `list[string]`,
`boolean`) is the contract for Stages 3 and 4 — Stage 3 validates extracted
values against it; Stage 4 picks renderers from it.

### Caching

`raw_responses/categorize_response.json` (gitignored). TTL 7 days. The
cache key is a sha256 of: model name + max_categories + hint + every
listing's content. So any change to Stage 1's listings, the model, or the
flags forces a re-call automatically — no need for `--refresh` after most
upstream changes.

### `categories.json` is BUILD OUTPUT

Manual edits to `categories.json` do not survive a re-run — the file is
regenerated from the cached LLM response on every Stage 2 invocation.
To bias the schema, use `--hint "..."` and re-run with `--refresh`. To
hand-pin a custom schema permanently, stop running `categorize.py` and
maintain the file by hand.

## Stage 3: extract

For each listing, an LLM call to `deepseek/deepseek-v4-pro:floor` populates
every category from `categories.json` with a typed value. Outputs one
`extracted/<id>.json` per listing plus a single `data.json` bundle that
Stage 4 will consume directly.

### How to run

```bash
source ../KEYS
uv run extract.py                       # extract all; cache makes re-runs near-free
uv run extract.py --refresh             # ignore cache, re-extract everything
uv run extract.py --refresh-id <id>     # re-extract one listing (repeatable)
uv run extract.py --concurrency 4       # default 4; max 8
uv run extract.py --only "anthropic*"   # glob filter on listing id, for iteration
```

First run at concurrency 4: ~6 minutes for 26 listings. Cache-hit re-runs:
<1 second. `extracted/*.json` are byte-identical across cache-hit runs.

### Validation

The LLM response is type-checked per the schema. Coercion rules:

| type | Rule |
|---|---|
| `boolean` | Must be `true`/`false`. Missing/null → `false`. Non-bool → `false` + warning. |
| `number` | Int/float or null. String-numeric strings auto-parsed. |
| `string` | String or null. Whitespace trimmed; empty → null. |
| `enum` | Must match `enum_values` exactly. Out-of-vocab → null + warning. |
| `list[string]` | When the description embeds "You MUST only use values from this exact list: ...", items not in that vocab are dropped silently with a warning. Missing → `[]`. |

Extra keys (not in schema) are silently dropped. Missing keys default per
type. Validation warnings are recorded in
`extraction_metadata.validation_warnings` so we can see which listings the
model struggled with without crashing.

### Caching (per-listing)

`raw_responses/extract_<id>.json` (gitignored). One file per listing.
Cache key:
`sha256(model + categories.json content + listings/<id>.md content)`.

So:
- **New listing added** → no cache entry → fresh call.
- **Listing re-scraped (Stage 1) and content changed** → cache_key differs → fresh call for that listing only.
- **Schema changed (Stage 2 re-run)** → cache_key differs for *all* listings → all re-extracted automatically.
- **Nothing changed** → cache hit, byte-identical output, no API call.

The `extracted_at` timestamp is stored in the cache and reused on hit, so
cache-hit re-runs produce byte-identical `extracted/*.json`.

### Concurrency

Default 4 concurrent LLM calls via `concurrent.futures.ThreadPoolExecutor`.
Max 8. Single retry with 5s backoff on transient errors; second failure
yields a stub with `extracted: null` and an `error` field (run continues).

### Output: `data.json`

Single bundle Stage 4 fetches at page load. Joined from manifest +
categories + every `extracted/*.json`:

```json
{
  "metadata": {
    "stage1_fetched_at": "...",
    "stage2_generated_at": "...",
    "stage3_extracted_at": "...",
    "stage3_model": "deepseek/deepseek-v4-pro:floor",
    "n_listings": 26,
    "n_listings_with_extraction": 26,
    "n_listings_failed": 0
  },
  "categories": [/* copied verbatim from categories.json */],
  "listings": [
    {
      /* all manifest fields: id, company, title, location, url, ats, ... */
      "extracted": {/* one entry per category key */},
      "extraction_warnings": []
    }
  ]
}
```

Listings sorted by `id` for deterministic diffs.

### `extracted/*.json` and `data.json` are BUILD OUTPUT

Like `categories.json`, these are regenerated from cache on every run. Hand
edits don't survive. To pin a value, edit the corresponding cache file in
`raw_responses/extract_<id>.json` (its `parsed` field), or stop running
Stage 3 and hand-maintain.

## Stage 4: visualize (v2)

Single self-contained `index.html` — vanilla JS + inline CSS + the full
`data.json` payload baked in as a `<script type="application/json"
id="fde-data">` block. No framework, no external CDN, no fetch at
runtime. **Works directly via `file://`** without any local server.
Light theme.

The data block is refreshed automatically by `extract.py` at the end of
every Stage 3 run. If you edit `categories.json` by hand or change
`data.json` outside the pipeline, re-run `uv run extract.py` (cache hits
keep it fast) to regenerate the inline block.

A `fetch('data.json')` fallback runs only when the inline block is empty
— useful for local development if you blow away the data block.

**Framing.** This page is for *preparing for FDE jobs* — it answers
"what do FDE roles ask for?" by showing aggregate demand across the
26-listing corpus. It is **not** a listings browser. There are no
filters, no search, no sort, no detail drawer, no localStorage —
everything is a single read-only summary.

(v1 was a 16-column listings comparison table with chip filters,
sortable columns, and a markdown-rendering detail drawer. The framing
was wrong — see commit history if needed.)

### How to view

Locally: `cd fde-jobs && python3 -m http.server 8000`, open
`http://localhost:8000/`.

Deployed: pushed to GitHub Pages at the repo's `fde-jobs/` URL.
`git push` is the only deploy step.

### Layout

- **Header**: title + counts ("What 26 FDE-archetype roles ask for · 16
  companies · updated YYYY-MM-DD") + a short lede paragraph explaining
  the page.
- **One section per category**, in a fixed actionable order:
  1. Required Skill Areas (list[string])
  2. Programming Languages (list[string])
  3. Cloud & Infra Tools (list[string])
  4. AI/ML Frameworks (list[string])
  5. Primary Role Focus (enum)
  6. Target User Persona (enum)
  7. Target Customer Industry (enum)
  8. Deployment Environment (enum)
  9. Travel Expectation (enum)
  10. How often a role is… (booleans grouped, ordered by true%)
- **Footer**: extraction date + schema size.

### Section internals

Each section is a header + a stack of value rows, sorted by count desc.
A value row is a **single horizontal bar** with three layers:

- a colored fill that grows from the left, with **width = percentage of
  the denominator** (so 38% wide for 38%); color is hashed from the
  value name (12-color muted pastel palette).
- the value name overlaid on the bar (left-aligned, dark text — readable
  on both filled and unfilled portions).
- the `count · pct%` stats overlaid on the right edge.

Same width semantics across all sections — a 50% bar always looks the
same. "(unstated)" rows use gray fill + italic gray text.

### Per-type denominator semantics

| type | denominator | sum |
|---|---|---|
| `list[string]` | 26 | can exceed 100% — a role can match multiple values |
| `enum` | 26 | sums to 100%; null/missing rendered as a separate gray "(unstated)" row at the bottom (skipped for `travel_expectation`, which has its own `unstated` enum value) |
| `boolean` | 26 | only the *true* share is shown — false is implicit |

Section header includes a small italic hint with the appropriate
denominator semantics so readers don't have to guess.

### Color hashing

`hash(value) % 12` over a 12-color muted pastel palette. Same value
gets the same color on the page. Kept identical to v1.

### Mobile

Single-column layout works down to 320px. Long value names truncate
with ellipsis above 380px; below 380px, the bar drops below the value
name into its own row.

### `index.html` is build output in spirit

The HTML/CSS/JS is hand-written and committed, but the *data* shown
comes entirely from `data.json` — Stage 4 reads no other files. To
change what's shown, modify upstream stages, not the HTML.

## Architecture notes

- **`data.json` is the only file Stage 4 reads.** Stage 4 doesn't open
  individual `extracted/<id>.json`, `categories.json`, or `listings/*.md`.
- **Type vocabulary is fixed.** Stage 4 has renderers for `enum`,
  `list[string]`, and `boolean`. `number` and `string` types are not
  rendered in v2 (the current schema has none); future schema additions
  of those types would need a renderer added.
- **Section ordering is hardcoded** in `ORDER` at the top of the JS to
  prioritize actionable axes for someone preparing for FDE roles.
  Categories not in the explicit list are appended at the end of their
  type group.

## Known limitations

- Custom-ATS extraction quality depends on whether the careers page renders
  listings into the static HTML. JS-rendered SPAs (some Workday and many
  custom careers pages) may yield empty results — we don't run a headless
  browser.
- Some Ashby boards (e.g., Decagon) leave `locationName` empty; we fall back
  to `address.postalAddress` then `isRemote`, but a few listings end up with
  an empty `location`.
- `posted_at` semantics differ across ATSs: Greenhouse `updated_at` (most
  recent edit, not original post), Lever `createdAt` (original post), Ashby
  `publishedAt` (original post). All normalized to ISO 8601.
- Stage 2 output is non-deterministic across `--refresh` runs. Stage 3
  tolerates this — its per-listing cache key includes a hash of
  `categories.json`, so a category change automatically invalidates every
  listing's cache.
- Stage 3 extraction quality is bounded by the listing body's specificity.
  When a listing doesn't mention a dimension (e.g., never specifies
  `deployment_environment`), the LLM returns null, and `data.json` shows
  null for that cell. This is by design — null is more useful than a
  fabricated guess. Stage 4 surfaces nulls as a "(unstated)" row in
  enum sections.
- Stage 4 v2 deliberately removed all interactivity (no filters, search,
  sort, drawer, persistence). If a future use case needs cohort slicing
  ("what do AI lab FDEs need vs. fintech FDEs?"), that's a v3 question
  and warrants a separate design pass — don't bolt filters back onto
  the current page.
