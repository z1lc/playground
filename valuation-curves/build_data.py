# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx"]
# ///
"""Build the Valuation Curves dataset: valuation vs. years since founding.

    uv run build_data.py                # fetch (cached), validate, write data.json, inline
    uv run build_data.py --check        # validate the shards only, write nothing
    uv run build_data.py --refresh      # ignore the cache and re-download
    uv run build_data.py --only apple,sierra   # compute+validate a subset, write nothing
    uv run build_data.py --offline      # fail on cache miss instead of fetching
    uv run build_data.py --check-links  # HEAD every cited URL (slow, pre-publish)

Two kinds of data meet here.

PRIVATE valuations are hand-curated in `companies/<slug>.json` by researchers, because
funding rounds are narrative facts that no API serves. A large minority of them never
disclose a post-money valuation at all, and the share is strongly era-dependent -- see
`disclosure_stats`, which measures it rather than asserting it -- so a round carrying an
amount and `valuationUsd: null` is a complete record, not a broken one.

PUBLIC market caps are computed here, because hand-researching them does not work: the
source that ranks first in search (macrotrends.net) returns HTTP 402 and cannot be read,
and every figure recalled rather than fetched drifts. The computation is

    cap(q) = close(q) x shares(q) x F(q)

where `close` is split-adjusted to today's basis, `shares` is the SEC cover-page count
nearest in time to q, and F is the cumulative split ratio taking effect after that cover
was printed. F is DERIVED from clean N-fold jumps in the share series and then CHECKED
against an independent annual market-cap series -- so no split table is hand-asserted.

Sources, and why each one:
  * stockanalysis.com  quarterly closes, ~10 years back. Split-adjusted to today.
  * data.sec.gov       XBRL cover-page share counts, 2009+. Authoritative.
  * companiesmarketcap annual market cap, 1996+. Used directly before the quarterly
                       window starts, and as one of two cross-checks that validate F.
  * stockanalysis.com  annual market cap, as the second cross-check. A year only counts
                       against the pipeline when BOTH sources disagree with it. Rows
                       older than ~5 years are paywalled, so early years have one source.
  * fred.stlouisfed.org  US nominal GDP by quarter, for the GDP-adjusted toggle.
  * companies/*.json   everything before 1996, hand-entered with a source per figure.

Yahoo Finance would extend the quarterly window back to the IPO for every ticker, and the
code below will use it when it answers; at time of writing it returns HTTP 429 to this
host, so the pipeline runs on the sources above and degrades to annual before 2016.
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

HERE = Path(__file__).parent
COMPANIES_DIR = HERE / "companies"
CACHE = HERE / "raw_responses"
DATA_JSON = HERE / "data.json"
INDEX_HTML = HERE / "index.html"

TODAY = date.today()

# SEC asks for a contact address in the User-Agent and blocks requests without one.
SEC_UA = "rsanek playground rsanek@gmail.com"
WEB_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ── vocabulary ────────────────────────────────────────────────────────────────
# Kept as explicit allowlists so a typo in a hand-written shard fails the build
# instead of silently becoming a category of one.

STATUSES = ("private", "public")
PRECISIONS = ("day", "month", "year")
FOUNDED_BASES = ("partnership", "incorporation", "team-founding")
CONFIDENCES = ("confirmed", "soft")
VALUATION_BASES = ("post", "pre", "unspecified")
VALUATION_METHODS = ("reported", "s1-cap-table", "tender", "secondary", "estimate")
SOURCE_TYPES = ("filing", "press", "company", "database", "reference")
COHORTS = ("ai", "fintech", "marketplace", "mega-cap", "saas")

# Event kinds. Only PLOTTABLE_KINDS ever become vertices of a line; the rest are
# recorded so the research isn't lost and the methodology can explain the exclusion.
# A terminated acquisition in particular must never be a vertex: nobody ever
# transacted at that price, so plotting it asserts a mark-to-market that never was.
PLOTTABLE_KINDS = ("priced_round", "convertible_note", "tender_offer", "ipo")
KINDS = PLOTTABLE_KINDS + ("terminated_deal", "secondary_mark")

# Validated categorical palette (dataviz skill). Eight hues cannot identify 30+
# series, and they do not even separate cleanly among themselves: verify.mjs measures
# a closest deuteranopic pair of dE 5.2 in dark mode, under the dE 8 threshold. Dash
# patterns and always-on end labels carry identity; hue is wayfinding. The default
# companies sit on slots 0, 3, 4 and 5, which clear both thresholds in both modes
# as a set -- only slots 2 and 6 fail as a pair -- and verify.mjs holds them to it.
PALETTE_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#eda100", "#008300", "#e87ba4", "#e34948"]
PALETTE_DARK = ["#3987e5", "#d95926", "#199e70", "#9085e9", "#c98500", "#008300", "#d55181", "#e66767"]
DASHES = ["", "7 4", "2 3", "11 3 2 3", "9 3 2 3 2 3"]

DEFAULT_SELECTION = ["google", "nvidia", "anthropic", "openai"]

# Ratios worth testing when looking for a split in the share series. A real split
# lands within a per-cent of an integer ratio; ordinary issuance and buybacks move
# share counts by well under 5% a quarter, so the bands never overlap.
SPLIT_RATIOS = (1.5, 2, 3, 4, 5, 7, 10, 20)
SPLIT_TOL = 0.05

# A cover page is dated a few weeks after the period it describes, so the last cover
# filed BEFORE a quarter end is typically ~11 weeks stale. For a company retiring ~1%
# of its shares a quarter that is a systematic overstatement, and it is the most likely
# explanation whenever an aggregator's year-end sits a per cent or two off a filed
# count. Picking the nearest cover in either direction removes the bias; beyond this
# many days there is no nearby filing and the point is flagged.
MAX_SHARE_GAP_DAYS = 200

# How close the first public point must sit to the IPO date for the glyph to be drawn.
# A quarterly series lands within one quarter; a decade-late series is a data gap.
IPO_MARKER_WINDOW_DAYS = 400

GDP_SERIES = "GDP"  # US nominal GDP, $bn, seasonally adjusted annual rate, quarterly
# FRED drops the connection for browser-like and custom User-Agents but serves stock
# client strings, so its request goes out under httpx's own.
FRED_UA = f"python-httpx/{httpx.__version__}"


# ── small helpers ─────────────────────────────────────────────────────────────


def iso(d: date) -> str:
    return d.isoformat()


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def quarter_end(d: date) -> date:
    """The calendar quarter end that `d` falls in."""
    q = (d.month - 1) // 3
    return [date(d.year, 3, 31), date(d.year, 6, 30), date(d.year, 9, 30), date(d.year, 12, 31)][q]


def years_between(a: date, b: date) -> float:
    """Years from a to b. 365.2425 is the Gregorian mean year; using 365 would drift
    a full week over Apple's fifty-year span, which is visible at the left edge."""
    return round((b - a).days / 365.2425, 3)


def display_date(d: date, precision: str) -> str:
    """Formatted here, never in JS: `new Date('2024-02-13')` parses as UTC midnight
    and renders as the 12th in any timezone west of Greenwich."""
    if precision == "year":
        return str(d.year)
    if precision == "month":
        return d.strftime("%b %Y").replace(" 0", " ")
    return d.strftime("%b %-d, %Y")


def fmt_usd(n: float) -> str:
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(n) >= div:
            v = n / div
            return f"${v:.0f}{suf}" if v >= 100 else f"${v:.3g}{suf}"
    return f"${n:.0f}"


# ── network, all cached ───────────────────────────────────────────────────────


class Fetcher:
    """Every response is written to raw_responses/ verbatim so a rebuild reproduces
    from cache when an upstream starts rate-limiting -- which, for the price sources,
    is a matter of when rather than if."""

    def __init__(self, refresh: bool, offline: bool) -> None:
        self.refresh = refresh
        self.offline = offline
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)
        self._last_sec_call = 0.0

    def get(self, url: str, cache_path: Path, ua: str, sec: bool = False) -> str | None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists() and not self.refresh:
            return cache_path.read_text()
        if self.offline:
            raise SystemExit(f"--offline but no cache for {url} at {cache_path}")
        if sec:
            # SEC publishes a 10 req/s ceiling and bans hosts that ignore it.
            wait = 0.15 - (time.monotonic() - self._last_sec_call)
            if wait > 0:
                time.sleep(wait)
            self._last_sec_call = time.monotonic()
        try:
            r = self.client.get(url, headers={"User-Agent": ua})
        except Exception as exc:  # noqa: BLE001 - every transport failure is equivalent here
            print(f"    ! {type(exc).__name__} fetching {url}", file=sys.stderr)
            return None
        if r.status_code != 200:
            print(f"    ! HTTP {r.status_code} fetching {url}", file=sys.stderr)
            return None
        cache_path.write_text(r.text)
        return r.text

    def json(self, url: str, cache_path: Path, ua: str, sec: bool = False) -> Any | None:
        raw = self.get(url, cache_path, ua, sec=sec)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # A bot wall or an error page served with a 200. Don't keep it.
            cache_path.unlink(missing_ok=True)
            print(f"    ! non-JSON body from {url}", file=sys.stderr)
            return None


# ── shard loading and validation ──────────────────────────────────────────────
# The validators collect every problem and report them all at once, each prefixed
# with the file that owns it. Raising on the first error would mean a researcher
# fixes one typo per run.


def load_companies(only: set[str] | None) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    companies: list[dict[str, Any]] = []
    for path in sorted(COMPANIES_DIR.glob("*.json")):
        if only and path.stem not in only:
            continue
        try:
            c = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON - {exc}")
            continue
        c["_file"] = path.name
        if c.get("slug") != path.stem:
            errors.append(f"{path.name}: slug {c.get('slug')!r} does not match the filename")
        validate_company(c, errors, warnings)
        companies.append(c)
    validate_corpus(companies, errors, warnings)
    return companies, errors, warnings


def _req(c: dict[str, Any], key: str, allowed: tuple[str, ...] | None, errors: list[str], where: str) -> None:
    v = c.get(key)
    if v is None or v == "":
        errors.append(f"{where}: missing {key}")
    elif allowed and v not in allowed:
        errors.append(f"{where}: {key}={v!r} not one of {allowed}")


def validate_company(c: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    f = c["_file"]
    for key, allowed in (
        ("name", None),
        ("cohort", COHORTS),
        ("status", STATUSES),
        ("foundedPrecision", PRECISIONS),
        ("foundedBasis", FOUNDED_BASES),
    ):
        _req(c, key, allowed, errors, f)

    for key, hi in (("colorSlot", len(PALETTE_LIGHT)), ("dashSlot", len(DASHES))):
        v = c.get(key)
        if not isinstance(v, int) or not 0 <= v < hi:
            errors.append(f"{f}: {key} must be an int in 0..{hi - 1}, got {v!r}")

    founded = None
    try:
        founded = parse_date(c["founded"])
    except (KeyError, ValueError):
        errors.append(f"{f}: founded must be an ISO date")
    if founded:
        prec = c.get("foundedPrecision")
        if prec == "year" and (founded.month, founded.day) != (1, 1):
            errors.append(f"{f}: foundedPrecision=year requires founded to be YYYY-01-01")
        if prec == "month" and founded.day != 1:
            errors.append(f"{f}: foundedPrecision=month requires founded day 01")
        if founded > TODAY:
            errors.append(f"{f}: founded {founded} is in the future")

    sources = c.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{f}: needs at least one source")
        sources = []
    for i, s in enumerate(sources):
        if not str(s.get("url", "")).startswith("https://"):
            errors.append(f"{f}: sources[{i}] url must be https")
        if s.get("type") not in SOURCE_TYPES:
            errors.append(f"{f}: sources[{i}] type={s.get('type')!r} not one of {SOURCE_TYPES}")
        if not s.get("title"):
            errors.append(f"{f}: sources[{i}] missing title")

    pub = c.get("public")
    if c.get("status") == "public":
        if not isinstance(pub, dict):
            errors.append(f"{f}: status=public requires a `public` block")
        else:
            validate_public(c, pub, founded, errors, warnings)
    elif pub:
        errors.append(f"{f}: status=private must not carry a `public` block")

    prev: date | None = None
    for ev in c.get("events", []):
        d = validate_event(c, ev, founded, len(sources), errors, warnings)
        if d and prev and d < prev:
            errors.append(f"{f}/{ev.get('id')}: events must be in date order")
        prev = d or prev
    check_down_rounds(c, errors)


def validate_public(
    c: dict[str, Any], pub: dict[str, Any], founded: date | None, errors: list[str], warnings: list[str]
) -> None:
    f = c["_file"]
    for key in ("ticker", "cik", "ipoDate", "publicFrom"):
        _req(pub, key, None, errors, f"{f}/public")
    if not re.fullmatch(r"\d{10}", str(pub.get("cik", ""))):
        errors.append(f"{f}/public: cik must be a 10-digit zero-padded string")
    try:
        ipo = parse_date(pub["ipoDate"])
        if founded and ipo < founded:
            errors.append(f"{f}/public: ipoDate {ipo} precedes founded {founded}")
        if ipo > TODAY:
            errors.append(f"{f}/public: ipoDate {ipo} is in the future")
    except (KeyError, ValueError):
        pass
    for i, o in enumerate(pub.get("annualOverrides", [])):
        try:
            parse_date(o["date"])
        except (KeyError, ValueError):
            errors.append(f"{f}/public: annualOverrides[{i}] needs an ISO date")
        if not isinstance(o.get("capUsd"), int) or o.get("capUsd", 0) <= 0:
            errors.append(f"{f}/public: annualOverrides[{i}] capUsd must be a positive int")
        if not o.get("sourceRefs"):
            errors.append(f"{f}/public: annualOverrides[{i}] needs sourceRefs")
    if not pub.get("regressions"):
        warnings.append(f"{f}/public: no regression checkpoint - a wrong share tag would go unnoticed")


def validate_event(
    c: dict[str, Any], ev: dict[str, Any], founded: date | None, n_sources: int, errors: list[str], warnings: list[str]
) -> date | None:
    where = f"{c['_file']}/{ev.get('id', '?')}"
    _req(ev, "id", None, errors, where)
    _req(ev, "kind", KINDS, errors, where)
    _req(ev, "roundName", None, errors, where)
    _req(ev, "datePrecision", PRECISIONS, errors, where)

    d: date | None = None
    try:
        d = parse_date(ev["date"])
    except (KeyError, ValueError):
        errors.append(f"{where}: date must be an ISO date")
    if d:
        prec = ev.get("datePrecision")
        if prec == "year" and (d.month, d.day) != (1, 1):
            errors.append(f"{where}: datePrecision=year requires YYYY-01-01")
        if prec == "month" and d.day != 1:
            errors.append(f"{where}: datePrecision=month requires day 01")
        if founded and d < founded:
            errors.append(f"{where}: dated {d}, before founding {founded}")
        if d > TODAY + timedelta(days=30):
            errors.append(f"{where}: dated {d}, in the future")

    refs = ev.get("sourceRefs") or []
    if not refs:
        errors.append(f"{where}: needs at least one sourceRef")
    for r in refs:
        if not isinstance(r, int) or not 0 <= r < n_sources:
            errors.append(f"{where}: sourceRef {r!r} out of range")

    # The inclusion floor is mechanical: a named institutional lead. Series letters
    # are unusable for this -- outlets label the same round B, C, D and E, so the
    # charter letter, the press label and the database label routinely disagree.
    if ev.get("institutional") and not ev.get("lead"):
        errors.append(f"{where}: institutional rounds need a named `lead` - that IS the inclusion test")

    for money in ("amountRaisedUsd", "valuationUsd"):
        v = ev.get(money)
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v <= 0):
            errors.append(f"{where}: {money} must be a positive int of USD or null, got {v!r}")

    val = ev.get("valuationUsd")
    if val is not None:
        _req(ev, "valuationBasis", VALUATION_BASES, errors, where)
        _req(ev, "valuationConfidence", CONFIDENCES, errors, where)
        _req(ev, "valuationMethod", VALUATION_METHODS, errors, where)
        amt = ev.get("amountRaisedUsd")
        if amt and ev.get("valuationBasis") == "post" and val <= amt:
            errors.append(f"{where}: post-money {val:,} is not greater than the {amt:,} raised")
        if ev.get("valuationBasis") == "pre":
            # Adding the raise to reach post is only right for a single closing with
            # no secondary, which is unknowable. We plot the pre-money and label it.
            warnings.append(f"{where}: pre-money valuation, plotted as-is (never converted to post)")
    if ev.get("plot") and ev.get("kind") not in PLOTTABLE_KINDS:
        errors.append(f"{where}: kind={ev.get('kind')} may never be plotted")
    if ev.get("plot") and val is None:
        errors.append(f"{where}: plot=true requires a valuationUsd")
    return d


def check_down_rounds(c: dict[str, Any], errors: list[str]) -> None:
    """Down rounds are real (Stripe went $95B -> $50B), so this is not an error --
    but an unexplained one is far more likely to be a data-entry slip than history."""
    prev_val, prev_name = None, None
    for ev in c.get("events", []):
        v = ev.get("valuationUsd")
        if v is None or not ev.get("plot"):
            continue
        if prev_val is not None and v < prev_val and not ev.get("note"):
            errors.append(
                f"{c['_file']}/{ev['id']}: down round ({fmt_usd(prev_val)} at {prev_name} -> "
                f"{fmt_usd(v)}) needs a `note` explaining it"
            )
        prev_val, prev_name = v, ev.get("roundName")


def validate_corpus(companies: list[dict[str, Any]], errors: list[str], warnings: list[str]) -> None:
    seen: dict[tuple[int, int], str] = {}
    by_cohort: dict[str, dict[int, str]] = {}
    for c in companies:
        key = (c.get("colorSlot"), c.get("dashSlot"))
        if key in seen:
            errors.append(f"{c['_file']}: (colorSlot, dashSlot)={key} already used by {seen[key]}")
        seen[key] = c["_file"]
        cohort = by_cohort.setdefault(str(c.get("cohort")), {})
        slot = c.get("colorSlot")
        if slot in cohort:
            warnings.append(
                f"{c['_file']}: shares colorSlot {slot} with {cohort[slot]} inside cohort "
                f"{c.get('cohort')} - same-cohort companies are the ones most often compared"
            )
        else:
            cohort[slot] = c["_file"]

        # Four in five private rounds never disclose a post-money. A shard that beats
        # that by a wide margin is likelier to be an agent filling gaps than a company
        # with unusual disclosure habits.
        rounds = [e for e in c.get("events", []) if e.get("kind") == "priced_round"]
        valued = [e for e in rounds if e.get("valuationUsd") is not None]
        if len(rounds) >= 5 and len(valued) / len(rounds) > 0.8:
            warnings.append(
                f"{c['_file']}: {len(valued)}/{len(rounds)} rounds carry a valuation - "
                f"unusually complete, worth re-checking the sourcing"
            )


# ── price, shares, splits ─────────────────────────────────────────────────────


@dataclass
class ShareRow:
    """Two dates, because two different questions get asked of the same row.

    `at` is the period the count describes, and answers "which count was in force
    around this quarter?". `basis` is the date the number was printed, and answers
    "which split basis is it stated in?".

    Collapsing them breaks weighted-average rows badly. Square's 2015 quarters were
    first filed in May 2016, its first 10-Q as a public company -- so keying position
    in time off the filing date made a 152M pre-IPO share count the nearest match for
    December 2016, when the real figure was 367M. Market cap came out 57% light.
    """

    at: date  # period end: where the row sits in time
    basis: date  # print date: which split basis the value is stated in
    val: int
    tag: str
    period: bool  # True if this is an average over a span rather than a count on a day


SHARES_TAG_CASCADE = [
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ("us-gaap", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"),
]

# Multi-class filers (Meta, Alphabet, Block, Airbnb, Shopify, Dropbox) tag the cover
# count with a share-class axis, and the companyconcept API exposes only
# non-dimensional facts -- so the obvious `dei` tag 404s for them and the cascade
# falls through to a weighted average. That runs ~0.5-2% under period-end, which is
# 0.006 of a decade on a six-decade log axis; those points are marked soft.
SOFT_TAGS = {"WeightedAverageNumberOfSharesOutstandingBasic", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted"}


def fetch_shares(fetcher: Fetcher, cik: str, pin: str | None) -> tuple[list[ShareRow], str | None]:
    facts = fetcher.json(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        CACHE / "sec" / f"CIK{cik}.json",
        SEC_UA,
        sec=True,
    )
    if not facts:
        return [], None
    for taxonomy, tag in SHARES_TAG_CASCADE:
        if pin and pin != tag:
            continue
        unit = facts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {}).get("shares")
        if not unit:
            continue
        rows = _shares_from_unit(unit, tag)
        if len(rows) >= 8:
            return rows, tag
    return [], None


def _shares_from_unit(unit: list[dict[str, Any]], tag: str) -> list[ShareRow]:
    by_end: dict[date, dict[str, Any]] = {}
    for r in unit:
        if "end" not in r or "val" not in r:
            continue
        if "start" in r:
            # Weighted-average facts report annual and year-to-date spans alongside
            # quarterly ones. Letting a full-year average land in a quarterly slot
            # produces a series that looks fine and sawtooths invisibly.
            span = (parse_date(r["end"]) - parse_date(r["start"])).days
            if span > 100:
                continue
        end = parse_date(r["end"])
        prior = by_end.get(end)
        # Take the EARLIEST filing for a period, never SEC's `frame`-marked canonical
        # fact. A cover-page count is stated in whatever split basis was current when
        # it was printed, and `basis` below is exactly that -- but the canonical
        # fact is the most RECENT restatement, so after a split it carries the new
        # basis against the old period end. Alphabet's 2021-12-31 count is filed as
        # 662,121,000 (10-K, Feb 2022) and again as 13,242,000,000 (the CY2021Q4I
        # frame, restated after the July 2022 20:1 split); preferring the frame made
        # detect_splits see two 20:1 splits where there was one, inflating every
        # pre-2022 quarter twentyfold.
        if prior is None or r.get("filed", "9") < prior.get("filed", "9"):
            by_end[end] = r
    # An instant fact is stated as of `end`, so both dates are `end`. A weighted average
    # describes a period but is printed on the filing date, so it sits at `end` in time
    # while carrying the filing date's split basis.
    out = []
    for end, r in sorted(by_end.items()):
        is_period = "start" in r
        basis = parse_date(r["filed"]) if is_period else end
        out.append(ShareRow(at=end, basis=basis, val=int(r["val"]), tag=tag, period=is_period))
    return out


def detect_splits(rows: list[ShareRow]) -> list[tuple[date, float]]:
    """Splits show up as a clean N-fold jump between consecutive cover pages.

    Issuance and buybacks move a share count by well under 5% a quarter, so there is
    no overlap with the integer ratios a split produces. The effective date is only
    known to within one filing interval, which is fine: the factor is applied to the
    share row's own date, and both sides of the jump are unambiguous.
    """
    splits: list[tuple[date, float]] = []
    for a, b in zip(rows, rows[1:]):
        if a.val <= 0:
            continue
        ratio = b.val / a.val
        for n in SPLIT_RATIOS:
            if abs(ratio - n) / n < SPLIT_TOL:
                splits.append((b.basis, float(n)))
                break
    return splits


def find_basis_leak(rows: list[ShareRow]) -> tuple[date, float] | None:
    """A share count that DROPS by a clean 1/N is the signature of mixed split bases.

    Companies do not retire 95% of their stock in a quarter, so a fall of that shape
    means a split-restated value has landed among as-printed neighbours. It is worth
    its own check because of how it fails: the restated row reads as a split on the
    way in and another on the way out, the cumulative factor comes out squared, and
    every earlier quarter is inflated by a clean multiple that still looks like a
    plausible line on a log axis. Alphabet did exactly this and landed at $10.96T.
    """
    for a, b in zip(rows, rows[1:]):
        if a.val <= 0 or b.val <= 0:
            continue
        ratio = b.val / a.val
        for n in SPLIT_RATIOS:
            if abs(ratio - 1 / n) * n < SPLIT_TOL:
                return b.at, ratio
    return None


def split_factor_after(splits: list[tuple[date, float]], d: date) -> float:
    f = 1.0
    for eff, n in splits:
        if eff > d:
            f *= n
    return f


def fetch_quarterly_closes(fetcher: Fetcher, ticker: str) -> dict[date, float]:
    """Quarter-end closes, split-adjusted to today's basis.

    The API keys rows by quarter START and reports that quarter's closing price; the
    `range` parameter accepts a fixed enum, and 10Y is the deepest that works.
    """
    data = fetcher.json(
        f"https://stockanalysis.com/api/symbol/s/{ticker.lower()}/history?range=10Y&period=Quarterly",
        CACHE / "stockanalysis" / f"{ticker.upper()}_quarterly.json",
        WEB_UA,
    )
    out: dict[date, float] = {}
    for r in (data or {}).get("data", []):
        try:
            out[quarter_end(parse_date(r["t"]))] = float(r["c"])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def fetch_annual_caps(fetcher: Fetcher, slug: str) -> dict[int, float]:
    """Annual market cap, straight from the source -- no price, shares or splits
    involved, which is what makes it the right cross-check for the computed series."""
    html = fetcher.get(
        f"https://companiesmarketcap.com/{slug}/marketcap/",
        CACHE / "companiesmarketcap" / f"{slug}.html",
        WEB_UA,
    )
    if not html:
        return {}
    mult = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
    out: dict[int, float] = {}
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) >= 2 and re.fullmatch(r"\d{4}", cells[0]):
            m = re.match(r"\$([\d.]+)\s*([TBMK])", cells[1])
            if m:
                out[int(cells[0])] = float(m.group(1)) * mult[m.group(2)]
    return out


def fetch_stockanalysis_caps(fetcher: Fetcher, ticker: str) -> dict[int, float]:
    """A second independent annual market cap, for the same reason as the first: it is
    built without a price, a share count or a split factor, so agreeing with it says
    something the pipeline cannot say about itself.

    Two sources rather than one because a single one is not reliable enough to fail a
    build on. companiesmarketcap's 2025 rows disagree with both this source and the
    filed share counts for Tesla, Palantir and Shopify -- in Tesla's case by claiming a
    2024 gain of +75.42% against a +62.5% price move, which its own shares-outstanding
    page contradicts. A structural error shows up against both sources; a bad row in
    one shows up against only that one.
    """
    html = fetcher.get(
        f"https://stockanalysis.com/stocks/{ticker.lower()}/market-cap/",
        CACHE / "stockanalysis" / f"{ticker.upper()}_marketcap.html",
        WEB_UA,
    )
    if not html:
        return {}
    mult = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
    out: dict[int, float] = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 2:
            continue
        m = re.fullmatch(r"([A-Z][a-z]{2}) (\d+), (\d{4})", cells[0])
        v = re.fullmatch(r"([\d.]+)([TBMK])", cells[1])
        # Only December rows are year-end marks; the table also carries a spot row.
        if m and v and m.group(1) == "Dec":
            out[int(m.group(3))] = float(v.group(1)) * mult[v.group(2)]
    return out


def fetch_gdp(fetcher: Fetcher) -> dict[date, float]:
    """US nominal GDP by quarter, keyed by the quarter's first day as FRED dates it.

    GDP rather than CPI because the question the toggle answers is "how big was this
    company for its time". CPI only removes price changes; GDP also removes the economy
    itself growing, which is most of the gap between a 1980 dollar and a 2026 one.
    """
    body = fetcher.get(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={GDP_SERIES}",
        CACHE / "fred" / f"{GDP_SERIES}.csv",
        FRED_UA,
    )
    out: dict[date, float] = {}
    for line in (body or "").splitlines()[1:]:
        day, _, value = line.partition(",")
        try:
            out[parse_date(day)] = float(value)
        except ValueError:
            continue  # FRED writes "." for a missing observation
    return out


# ── the public series ─────────────────────────────────────────────────────────


@dataclass
class Point:
    d: date
    v: float
    kind: int  # 0 = private event, 1 = public quote
    soft: bool
    # Where the number came from. The cross-check needs this: comparing an annual
    # point against the annual table it was copied from is a tautology that would
    # report a perfect score while checking nothing.
    src: str = "computed"  # computed | annual | override | private
    label: str | None = None
    amount: int | None = None
    basis: str | None = None
    method: str | None = None
    lead: str | None = None
    note: str | None = None
    precision: str = "day"
    is_ipo: bool = False


def nearest_share_row(rows: list[ShareRow], d: date) -> ShareRow | None:
    """Which share count to price a quarter end with.

    Cover-page counts are instants and are printed a few weeks AFTER the period they
    describe, so the nearest one in either direction is the best estimate -- that is
    what removes the staleness bias.

    Weighted averages must never look forward. They average a whole quarter, so the
    row after a quarter end includes events that had not happened yet, and a calendar
    quarter end is always exactly two days closer to the NEXT quarter's end than to the
    previous one -- so a naive nearest match picks the future row every single time.
    Block issued ~80M shares for Afterpay in January 2022; letting December 2021 reach
    forward into Q1 2022 put its market cap 16% high.
    """
    if not rows:
        return None
    if rows[0].period:
        past = [r for r in rows if r.at <= d]
        if not past:
            return None
        best = max(past, key=lambda r: r.at)
    else:
        best = min(rows, key=lambda r: abs((r.at - d).days))
    return best if abs((best.at - d).days) <= MAX_SHARE_GAP_DAYS else None


def public_series(company: dict[str, Any], fetcher: Fetcher, errors: list[str], warnings: list[str]) -> list[Point]:
    pub = company["public"]
    f = company["_file"]
    ticker, cik = pub["ticker"], pub["cik"]
    public_from = parse_date(pub["publicFrom"])

    rows, tag = fetch_shares(fetcher, cik, pub.get("sharesTag") if pub.get("sharesTag") != "auto" else None)
    if not rows:
        warnings.append(f"{f}: no SEC share series for CIK {cik} - falling back to annual market cap only")
    leak = find_basis_leak(rows)
    if leak:
        errors.append(
            f"{f}: share count falls {leak[1]:.3f}x at {leak[0]} - a split-restated value has mixed "
            f"in among as-printed ones, which squares the split factor and inflates every earlier quarter"
        )
    splits = detect_splits(rows)
    # The preferred-to-common conversion at a listing is a clean multiple-fold jump in
    # the share count and looks exactly like a split to the detector. It is not one, and
    # every direct listing trips it. Quarters before publicFrom are never priced, so
    # dropping these is safe as well as correct.
    dropped = [s for s in splits if s[0] <= public_from]
    if dropped:
        print(f"    ignoring {len(dropped)} share-count jump(s) at or before listing (conversion, not a split)")
    splits = [s for s in splits if s[0] > public_from]
    if splits:
        print(f"    splits detected: {', '.join(f'{n:g}:1 by {d}' for d, n in splits)}")

    closes = fetch_quarterly_closes(fetcher, ticker)
    annual = fetch_annual_caps(fetcher, pub.get("cmcSlug", company["slug"]))
    annual2 = fetch_stockanalysis_caps(fetcher, ticker)

    points: dict[date, Point] = {}

    # 1. Hand-entered annual figures come first: they cover the years no free
    #    tabular source reaches, and are the only data before 1996.
    for o in pub.get("annualOverrides", []):
        d = parse_date(o["date"])
        if d >= public_from:
            points[d] = Point(d=d, v=float(o["capUsd"]), kind=1, soft=True, src="override")

    # 2. Annual market cap, straight from companiesmarketcap.
    for year, cap in sorted(annual.items()):
        d = min(date(year, 12, 31), TODAY)
        if d >= public_from and d not in points:
            points[d] = Point(d=d, v=cap, kind=1, soft=False, src="annual")

    # 3. Quarterly, computed -- overwrites the annual point in the same quarter,
    #    which is intended: it is the same quantity at higher resolution.
    soft_tag = tag in SOFT_TAGS
    stale = 0
    for d, close in sorted(closes.items()):
        if d < public_from or d > TODAY:
            continue
        row = nearest_share_row(rows, d)
        if row is None:
            stale += 1
            continue
        points[d] = Point(
            d=d,
            v=close * row.val * split_factor_after(splits, row.basis),
            kind=1,
            soft=soft_tag,
            src="computed",
        )
    if stale:
        warnings.append(f"{f}: {stale} quarter(s) had no cover-page count within {MAX_SHARE_GAP_DAYS} days")

    series = sorted(points.values(), key=lambda p: p.d)
    cross_check(company, series, annual, annual2, splits, errors, warnings)
    check_continuity(company, series, warnings)
    return series


def cross_check(
    company: dict[str, Any],
    series: list[Point],
    annual: dict[int, float],
    annual2: dict[int, float],
    splits: list[tuple[date, float]],
    errors: list[str],
    warnings: list[str],
) -> None:
    """The computed quarterly series against an annual series built with no price,
    no share count and no split factor. Agreement means all three inputs AND the
    derived split table are right; this is what replaces a hand-asserted split table.
    """
    f = company["_file"]
    by_date = {p.d: p for p in series}
    checked = worst = 0.0
    worst_year = None
    for year, cap in annual.items():
        p = by_date.get(date(year, 12, 31))
        # Only genuinely computed points are evidence. An annual point compared
        # against the annual table it was copied from always agrees perfectly and
        # would mask a broken share tag behind a flawless-looking score.
        if p is None or p.src != "computed" or cap <= 0:
            continue
        err = abs(p.v - cap) / cap
        # A year only counts against the pipeline if BOTH independent sources
        # disagree with it. Where they disagree with each other, the smaller gap is
        # the honest measure of "could the computation be right?" -- and it usually
        # can: Palantir's 2025 is 5.5% from companiesmarketcap and 0.3% from
        # stockanalysis, because companiesmarketcap implies 139M more shares than
        # Palantir has ever reported.
        cap2 = annual2.get(year)
        if cap2 and cap2 > 0:
            err = min(err, abs(p.v - cap2) / cap2)
        checked += 1
        if err > worst:
            worst, worst_year = err, year
    # 3% catches the structural failures -- a wrong share tag, a missed split, a
    # per-class count -- which all land at 20x, 4x or 40%, never at 3.5%. Small caps
    # that issue stock continuously can drift past it honestly, so a shard may raise
    # its own ceiling with a documented reason rather than the global bar dropping.
    tol = float(company["public"].get("crossCheckTolPct", 3.0)) / 100
    if not checked:
        warnings.append(f"{f}: no year where a computed point overlaps companiesmarketcap - split table unverified")
    elif worst > tol:
        errors.append(
            f"{f}: computed market cap diverges {worst * 100:.1f}% from companiesmarketcap in {worst_year}, "
            f"over its {tol * 100:.1f}% ceiling - a wrong share tag or a missed split"
        )
    else:
        print(f"    cross-check: {checked:.0f} year(s) vs companiesmarketcap, worst {worst * 100:.2f}% ({worst_year})")
    if splits:
        print("    split factors derived from the share series and confirmed by that cross-check")

    for r in company["public"].get("regressions", []):
        d, expect, tol = parse_date(r["date"]), float(r["capUsd"]), float(r.get("tolPct", 1.0)) / 100
        p = by_date.get(d)
        if p is None:
            warnings.append(f"{f}: regression date {d} has no computed point")
            continue
        got = p.v
        err = abs(got - expect) / expect
        if err > tol:
            errors.append(
                f"{f}: regression {d} computed {fmt_usd(got)}, expected {fmt_usd(expect)} ({err * 100:.2f}% off)"
            )
        else:
            print(f"    regression {d}: {fmt_usd(got)} vs {fmt_usd(expect)} ({err * 100:.2f}%) OK")


def check_continuity(company: dict[str, Any], series: list[Point], warnings: list[str]) -> None:
    """A quarter-over-quarter move outside [1/3, 3x] is the signature of a missed
    split, not a market event -- even 2008 and the dot-com bust stayed inside it."""
    quotes = [p for p in series if p.kind == 1]
    for a, b in zip(quotes, quotes[1:]):
        if (b.d - a.d).days > 200 or a.v <= 0:
            continue  # an annual gap can legitimately move further
        ratio = b.v / a.v
        if ratio > 3 or ratio < 1 / 3:
            warnings.append(f"{company['_file']}: {a.d} -> {b.d} moves {ratio:.2f}x - check for a missed split")


# ── the private series, and the join ──────────────────────────────────────────


def private_series(company: dict[str, Any]) -> list[Point]:
    out = []
    for ev in company.get("events", []):
        if not ev.get("plot") or ev.get("valuationUsd") is None:
            continue
        out.append(
            Point(
                d=parse_date(ev["date"]),
                v=float(ev["valuationUsd"]),
                kind=0,
                src="private",
                # Anything not company-confirmed or multi-source reads hollow: a single
                # press report, an unconfirmed figure and a derived estimate are all
                # "we are less sure of this number" and share one visual language.
                soft=ev.get("valuationConfidence") != "confirmed",
                label=ev.get("roundName"),
                amount=ev.get("amountRaisedUsd"),
                basis=ev.get("valuationBasis"),
                method=ev.get("valuationMethod"),
                lead=ev.get("lead"),
                note=ev.get("note"),
                precision=ev.get("datePrecision", "day"),
                is_ipo=ev.get("kind") == "ipo",
            )
        )
    return sorted(out, key=lambda p: p.d)


def join_series(company: dict[str, Any], priv: list[Point], pub: list[Point]) -> list[Point]:
    """One continuous line, private rounds into public market caps."""
    if not pub:
        return priv
    first_quote = pub[0].d
    # The last pre-IPO round and the IPO price are the same event seen twice; keeping
    # both draws a vertical jump that is an artefact of the calendar, not of value.
    kept = [p for p in priv if (first_quote - p.d).days > 45]
    merged = sorted(kept + pub, key=lambda p: p.d)
    # Mark the IPO only if the series actually reaches it. Microsoft listed in 1986 but
    # no free source publishes its market cap before 1996, so its first public point is
    # ten years late -- putting a diamond there would assert the company went public in
    # 1996. A missing marker is a gap in the data; a misplaced one is a false claim.
    ipo_date = parse_date(company["public"]["ipoDate"])
    for p in merged:
        if p.kind == 1 and p.d >= ipo_date:
            if (p.d - ipo_date).days <= IPO_MARKER_WINDOW_DAYS:
                p.is_ipo = True
            break
    return merged


# ── payload ───────────────────────────────────────────────────────────────────


def gdp_usd(nominal: float, d: date, gdp: dict[date, float], base: date) -> int:
    """`nominal` scaled to the size of the economy in the `base` quarter, i.e. the same
    share of GDP in dollars a reader can compare across fifty years. A date past the
    latest release uses that release, which is at most a quarter or two stale."""
    q = min(date(d.year, (d.month - 1) // 3 * 3 + 1, 1), base)
    return int(round(nominal * gdp[base] / gdp[q]))


def build_company_payload(
    company: dict[str, Any], points: list[Point], gdp: dict[date, float], base: date
) -> dict[str, Any]:
    founded = parse_date(company["founded"])
    t, v_nom, v_gdp, kinds, quality, dates = [], [], [], [], [], []
    labels, amounts, basis, method, leads, notes = {}, {}, {}, {}, {}, {}
    ipo_index = None

    for i, p in enumerate(points):
        t.append(years_between(founded, p.d))
        v_nom.append(int(round(p.v)))
        v_gdp.append(gdp_usd(p.v, p.d, gdp, base))
        kinds.append(p.kind)
        quality.append(1 if p.soft else 0)
        dates.append(iso(p.d))
        if p.is_ipo and ipo_index is None:
            ipo_index = i
        if p.kind == 0:
            k = str(i)
            labels[k] = p.label
            if p.amount is not None:
                amounts[k] = p.amount
            if p.basis:
                basis[k] = p.basis
            if p.method:
                method[k] = p.method
            if p.lead:
                leads[k] = p.lead
            if p.note:
                notes[k] = p.note

    last = points[-1] if points else None
    return {
        "slug": company["slug"],
        "name": company["name"],
        "cohort": company["cohort"],
        "status": company["status"],
        "colorSlot": company["colorSlot"],
        "dashSlot": company["dashSlot"],
        "founded": company["founded"],
        "foundedDisplay": display_date(founded, company["foundedPrecision"]),
        "foundedPrecision": company["foundedPrecision"],
        "foundedBasis": company["foundedBasis"],
        "foundedNote": company.get("foundedNote", ""),
        "ticker": company.get("public", {}).get("ticker"),
        # Shipped so the missing-IPO-marker case stays checkable rather than merely
        # tolerated: verify.mjs asserts that a public company without a marker really
        # does start its series long after it listed.
        "ipoDate": company.get("public", {}).get("ipoDate"),
        "ageYears": years_between(founded, last.d) if last else 0.0,
        "latest": (
            {
                "t": years_between(founded, last.d),
                "vNom": int(round(last.v)),
                "vGdp": gdp_usd(last.v, last.d, gdp, base),
                "dateDisplay": display_date(last.d, last.precision),
                "kind": last.kind,
            }
            if last
            else None
        ),
        "t": t,
        "vNom": v_nom,
        "vGdp": v_gdp,
        "kind": kinds,
        "quality": quality,
        "dates": dates,
        "ipoIndex": ipo_index,
        "labels": labels,
        "amounts": amounts,
        "basis": basis,
        "method": method,
        "leads": leads,
        "notes": notes,
        "unresolved": company.get("unresolved", []),
        "curatorNotes": company.get("curatorNotes", ""),
        "sources": company.get("sources", []),
    }


def disclosure_stats(companies: list[dict[str, Any]]) -> dict[str, Any]:
    """How often an institutional round comes with a post-money, overall and by decade.

    Derived rather than written down. An early draft of the methodology asserted "roughly
    four in five rounds never disclose a valuation", generalised from one company whose
    history happened to sit in a quiet era; across the full set it is nowhere near that.
    A page arguing for sourced numbers should not carry an unsourced one of its own.
    """
    total = valued = 0
    decades: dict[str, list[int]] = {}
    for c in companies:
        for ev in c.get("events", []):
            if ev.get("kind") != "priced_round" or not ev.get("institutional"):
                continue
            has = ev.get("valuationUsd") is not None
            total += 1
            valued += has
            row = decades.setdefault(f"{int(ev['date'][:4]) // 10 * 10}s", [0, 0])
            row[0] += 1
            row[1] += has
    return {
        "rounds": total,
        "valued": valued,
        # Only decades with enough rounds to mean anything -- one round is not a rate.
        "byDecade": {d: {"rounds": n, "valued": v} for d, (n, v) in sorted(decades.items()) if n >= 5},
    }


def build_payload(
    companies: list[dict[str, Any]], series: dict[str, list[Point]], gdp: dict[date, float]
) -> dict[str, Any]:
    base = max(gdp)
    out = [build_company_payload(c, series.get(c["slug"], []), gdp, base) for c in companies]
    out = [c for c in out if c["t"]]
    t_max = max((c["t"][-1] for c in out), default=0.0)
    v_all = [v for c in out for v in c["vNom"]]
    return {
        "meta": {
            "generated": iso(TODAY),
            "gdpBase": iso(base),
            "gdpBaseLabel": f"Q{(base.month - 1) // 3 + 1} {base.year}",
            "gdpSourceUrl": f"https://fred.stlouisfed.org/series/{GDP_SERIES}",
            # Shipped so the GDP-adjusted figures can be re-derived from the payload
            # alone -- verify.mjs recomputes every vGdp from this rather than
            # trusting the number next to it.
            "gdp": {iso(d): v for d, v in sorted(gdp.items())},
            "palette": {"light": PALETTE_LIGHT, "dark": PALETTE_DARK},
            "dashes": DASHES,
            "defaults": DEFAULT_SELECTION,
            "domain": {"tMax": t_max, "vMin": min(v_all, default=0), "vMax": max(v_all, default=0)},
            "counts": {"companies": len(out), "points": sum(len(c["t"]) for c in out)},
            # Derived so the methodology can state the disclosure rate without a
            # hand-written number going stale the next time a company is added.
            "disclosure": disclosure_stats(companies),
        },
        "companies": sorted(out, key=lambda c: -c["ageYears"]),
    }


_payload_warnings: list[str] = []


def validate_payload(payload: dict[str, Any], errors: list[str]) -> None:
    for c in payload["companies"]:
        f = c["slug"]
        n = len(c["t"])
        for key in ("vNom", "vGdp", "kind", "quality", "dates"):
            if len(c[key]) != n:
                errors.append(f"{f}: {key} has {len(c[key])} entries, expected {n}")
        for i in range(1, n):
            if c["t"][i] < c["t"][i - 1]:
                errors.append(f"{f}: t is not monotonic at index {i} ({c['dates'][i]})")
                break
        for i, v in enumerate(c["vNom"]):
            # A thousandfold units slip is the classic failure and is invisible on a
            # log axis without a bound like this.
            if not 1e5 <= v <= 1e13:
                errors.append(f"{f}: {c['dates'][i]} valuation {v:,} outside $100K..$10T")
                break
        if c["status"] == "private" and c["kind"] and c["kind"][-1] != 0:
            errors.append(f"{f}: a private company's last point must be a funding round")
        if c["status"] == "public" and c["ipoIndex"] is None:
            # Not an error: it means the series starts after the listing, which is a
            # sourcing limitation worth stating rather than papering over with a glyph.
            errors_note = f"{f}: no IPO marker - the public series starts after the listing date"
            if errors_note not in _payload_warnings:
                _payload_warnings.append(errors_note)


def inline_into_html(payload: dict[str, Any]) -> bool:
    if not INDEX_HTML.exists():
        print(f"  WARNING: {INDEX_HTML} does not exist yet - skipping inline", file=sys.stderr)
        return False
    text = INDEX_HTML.read_text()
    # Escaping `<` is mandatory rather than defensive: this dataset carries article
    # titles and URLs from arbitrary outlets, and one "</script>" substring inside any
    # of them would close the script tag and blank the page.
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")
    js = "    const DATA = " + blob + ";\n"
    pattern = re.compile(r"(// DATA_START\n)(.*?)(    // DATA_END)", re.DOTALL)
    if not pattern.search(text):
        print(f"  WARNING: no DATA_START/DATA_END sentinels in {INDEX_HTML}", file=sys.stderr)
        return False
    INDEX_HTML.write_text(pattern.sub(lambda m: m.group(1) + js + m.group(3), text))
    return True


def check_links(companies: list[dict[str, Any]], fetcher: Fetcher) -> None:
    """Many reputable outlets block scripted requests, so 401/403/429 is reported as
    inconclusive rather than treated as a dead link."""
    urls: dict[str, str] = {}
    for c in companies:
        for s in c.get("sources", []):
            urls.setdefault(s.get("url", ""), c["slug"])
    urls.pop("", None)
    print(f"\nChecking {len(urls)} unique URLs...")
    bad = 0
    for url, owner in sorted(urls.items()):
        # SEC blocks the browser UA outright and wants a contact address instead.
        # Sending the wrong one turns the most authoritative sources in the whole
        # dataset -- Form Ds, 10-K covers, S-1 exhibits -- into unverifiable 403s.
        ua = SEC_UA if ".sec.gov" in url else WEB_UA
        try:
            r = fetcher.client.head(url, headers={"User-Agent": ua})
            if r.status_code >= 400:
                r = fetcher.client.get(url, headers={"User-Agent": ua})
            code = r.status_code
        except Exception as exc:  # noqa: BLE001
            print(f"  ERR {type(exc).__name__} {url}  ({owner})")
            bad += 1
            continue
        # 503 belongs with the auth/rate-limit codes: several newswires answer scripted
        # requests with a tiny 503 stub rather than a 403, and an instant repeat of it
        # is a bot wall, not an outage. This checker exists to find dead citations, not
        # to monitor uptime, and calling a live page dead is the worse error.
        if code in (401, 403, 429, 503):
            print(f"  {code} (blocks scripts, inconclusive) {url}")
        elif code >= 400:
            print(f"  {code} {url}  ({owner})")
            bad += 1
    print(f"  {bad} URL(s) need attention")


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate the shards only, write nothing")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and re-download")
    ap.add_argument("--offline", action="store_true", help="fail on cache miss instead of fetching")
    ap.add_argument("--only", help="comma-separated slugs")
    ap.add_argument("--check-links", action="store_true", help="HEAD every cited URL (slow)")
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    companies, errors, warnings = load_companies(only)
    print(f"Loaded {len(companies)} company file(s) from {COMPANIES_DIR}")

    fetcher = Fetcher(refresh=args.refresh, offline=args.offline)

    if args.check:
        return report(errors, warnings)

    gdp = fetch_gdp(fetcher)
    if not gdp:
        return report([*errors, "no GDP series from FRED -- nothing to scale the GDP-adjusted view by"], warnings)
    print(f"GDP: {len(gdp)} quarters, {min(gdp)} to {max(gdp)}")

    series: dict[str, list[Point]] = {}
    for c in companies:
        print(f"\n  {c['name']} ({c['slug']})")
        priv = private_series(c)
        pub: list[Point] = []
        # Every company is computed regardless of what the ones before it did. Gating
        # this on `not errors` made one shard's failure silently skip the public series
        # for every shard after it alphabetically -- which then reported them all as
        # missing an IPO marker. Errors are collected and reported together, the same
        # way the shard validators work, so one bad file yields one message rather than
        # a cascade of unrelated ones.
        if c.get("status") == "public":
            pub = public_series(c, fetcher, errors, warnings)
        merged = join_series(c, priv, pub) if pub else priv
        series[c["slug"]] = merged
        print(f"    {len(merged)} point(s): {len(priv)} private, {len(pub)} public")

    if args.check_links:
        check_links(companies, fetcher)

    payload = build_payload(companies, series, gdp)
    validate_payload(payload, errors)
    warnings.extend(_payload_warnings)

    if errors:
        return report(errors, warnings)

    # --only is for iterating on one shard, so it must not touch the shipped
    # artifacts: writing a partial payload would leave data.json and the inlined
    # blob containing a single company until someone remembered to rebuild.
    if only:
        print(f"\n--only {','.join(sorted(only))}: computed and validated, wrote nothing.")
        print("Run `uv run build_data.py` with no --only to regenerate data.json and index.html.")
        return report(errors, warnings)

    DATA_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nWrote {DATA_JSON} ({DATA_JSON.stat().st_size:,} bytes)")
    if inline_into_html(payload):
        print(f"Inlined into {INDEX_HTML}")
    return report(errors, warnings)


def report(errors: list[str], warnings: list[str]) -> int:
    for w in warnings:
        print(f"  WARN  {w}", file=sys.stderr)
    for e in errors:
        print(f"  ERROR {e}", file=sys.stderr)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
