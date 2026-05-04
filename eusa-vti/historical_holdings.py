"""SEC EDGAR Form N-Q (pre-2019 quarterly) holdings fetcher for EUSA and VTI.

This is the older sibling of `holdings.py` (which handles N-PORT-P, 2019+).
N-Q is the same regulatory disclosure — the issuer's full Schedule of
Investments — but at quarterly cadence and as HTML rather than XML, in a
multi-fund document.

Strategy per filing:
  1. Locate the target series's section by string-match on the fund name.
  2. Extract just the "Common Stocks" portion (skipping cash, futures,
     treasuries, securities lending collateral, etc.).
  3. Parse each holding row to (name, shares, value).
  4. Read the explicit "Net Assets (100%) <amount>" to use as the
     denominator for `% of net assets`.
  5. Convert each holding to {name, cusip='', pctVal} and emit observations
     in the same shape `holdings.aggregate()` already consumes.

Two parsers are needed (iShares vs Vanguard) because their HTML idioms differ
just enough that a single regex doesn't cleanly cover both.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path

import httpx


# Canonical month names for parsing report dates ("November 30, 2016", etc.)
_MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}


def http_get(url: str, headers: dict, attempts: int = 3, sleep_on_429: float = 1.0) -> httpx.Response:
    last = None
    for i in range(attempts):
        resp = httpx.get(url, headers=headers, timeout=60.0, follow_redirects=True)
        if resp.status_code == 429:
            time.sleep(sleep_on_429 * (i + 1))
            last = resp
            continue
        resp.raise_for_status()
        return resp
    if last is not None:
        last.raise_for_status()
    raise RuntimeError(f"failed after {attempts} attempts: {url}")


def list_nq_filings(cik: str, headers: dict) -> list[dict]:
    """List all N-Q filings for a CIK, walking both `recent` and the older
    `files/CIK*-submissions-NNN.json` chunks. Returns
    [{accession, filingDate, primaryDocument}, ...] sorted oldest-first."""
    cik_padded = cik.zfill(10)
    out: list[dict] = []

    def collect(forms, dates, accessions, primary_docs):
        for f, d, a, p in zip(forms, dates, accessions, primary_docs):
            if f == "N-Q":
                out.append({"accession": a, "filingDate": d, "primaryDocument": p})

    base = http_get(f"https://data.sec.gov/submissions/CIK{cik_padded}.json", headers=headers).json()
    recent = base["filings"]["recent"]
    collect(recent["form"], recent["filingDate"], recent["accessionNumber"], recent["primaryDocument"])

    for older in base["filings"].get("files", []):
        chunk = http_get(f"https://data.sec.gov/submissions/{older['name']}", headers=headers).json()
        collect(chunk["form"], chunk["filingDate"], chunk["accessionNumber"], chunk["primaryDocument"])

    out.sort(key=lambda x: x["filingDate"])
    return out


def fetch_nq_html(cik: str, accession: str, primary_doc: str, headers: dict) -> str:
    cik_no_pad = cik.lstrip("0")
    accession_clean = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_pad}/{accession_clean}/{primary_doc}"
    return http_get(url, headers=headers).text


def _normalize_visible(html: str) -> str:
    """Strip HTML tags, normalize whitespace, return one big text blob."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def _find_target_section_ishares(html: str, target_phrase: str = "MSCI USA EQUAL") -> tuple[str, str | None] | None:
    """For multi-fund iShares N-Q docs: locate the EUSA section by scanning
    the visible text for the heading, then bounding to the next non-EUSA
    iShares fund heading.

    Returns (section_visible_text, report_date_iso) or None if not found.
    """
    visible = _normalize_visible(html)
    upper = visible.upper()

    start = upper.find(target_phrase)
    if start < 0:
        return None

    # Find the next "iSHARES <NAME>" heading that isn't another mention of EUSA.
    cursor = start + 1000
    end = len(visible)
    pat = re.compile(r"\biSHARES\b[A-Za-z0-9\s\-\&\.\(\)/]{1,200}?\b(?:ETF|FUND)\b", re.IGNORECASE)
    while cursor < len(visible):
        m = pat.search(visible[cursor:])
        if not m:
            break
        candidate = visible[cursor + m.start(): cursor + m.end()].upper()
        if target_phrase not in candidate:
            end = cursor + m.start()
            break
        cursor = cursor + m.end()

    # Include some pre-heading context — the report date in 2018+ filings
    # appears in "Schedule of Investments (unaudited) <Date> iShares ..." just
    # before the fund name.
    pre = max(0, start - 200)
    section = visible[pre:end]

    # Report date — search the whole section. The first match is reliably the
    # period-end date. Both "November 30, 2016" (early) and other variants
    # are covered.
    rep_date = None
    m_date = re.search(
        r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2}),?\s+(\d{4})",
        section.upper(),
    )
    if m_date:
        mo, day, yr = _MONTHS[m_date.group(1)], int(m_date.group(2)), int(m_date.group(3))
        rep_date = date(yr, mo, day).isoformat()

    return section, rep_date


def _find_target_section_vanguard(html: str, target_phrase: str) -> tuple[str, str | None] | None:
    visible = _normalize_visible(html)
    upper = visible.upper()

    start = upper.find(target_phrase)
    if start < 0:
        return None

    cursor = start + 1000
    end = len(visible)
    # Vanguard fund headings are like "Vanguard <Name> Index Fund Schedule of Investments"
    pat = re.compile(
        r"\bVanguard\b[A-Za-z0-9\s'&\.\-]{1,120}?\bIndex\s+Fund\b\s+Schedule\s+of\s+Investments",
        re.IGNORECASE,
    )
    while cursor < len(visible):
        m = pat.search(visible[cursor:])
        if not m:
            break
        candidate = visible[cursor + m.start(): cursor + m.end()].upper()
        if target_phrase not in candidate:
            end = cursor + m.start()
            break
        cursor = cursor + m.end()

    section = visible[start:end]

    rep_date = None
    m_date = re.search(
        r"\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2}),?\s+(\d{4})",
        section[:2000].upper(),
    )
    if m_date:
        mo, day, yr = _MONTHS[m_date.group(1)], int(m_date.group(2)), int(m_date.group(3))
        rep_date = date(yr, mo, day).isoformat()

    return section, rep_date


# Common-Stocks section bounding regexes. iShares 2017-and-earlier puts the
# total percent inline ("COMMON STOCKS — 99.67%"); 2018+ drops the percent and
# just says "Common Stocks" with industry sub-headers carrying the numbers.
# Vanguard always uses "Common Stocks (99.5%)". Match all three.
_CS_START_RE = re.compile(r"\bCOMMON\s+STOCKS\b(?:\s*[—\-]?\s*\(?\s*[\d.]+\s*%\)?)?", re.IGNORECASE)
_CS_END_RE = re.compile(r"Total\s+Common\s+Stocks", re.IGNORECASE)
# Vanguard format: "Net Assets (100%) 620,519,270"
# iShares format:  "NET ASSETS — 100.00% $ 89,469,706"
_NET_ASSETS_RE = re.compile(
    r"Net\s+Assets\s*[\(—\-]\s*100[\.\d]*\s*%[\s\)]*\$?\s*([\d,]+)",
    re.IGNORECASE,
)


# A holding row is a name (starts with a capital letter; arbitrary words/punctuation)
# followed by two numeric tokens (shares, value), each with thousand separators.
# We require the next char to be a capital letter, '(', '*' (footnote) or end-of-line
# so we don't accidentally chain across number boundaries.
_HOLDING_RE = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9 .\&\(\)\-\+\'\,/]{1,79}?)\s+"
    r"(?:\*[\,\^]?\s*)?"
    r"(?P<shares>[\d,]+)\s+"
    r"(?P<value>[\d,]+)"
    r"(?=\s+[A-Z\(\*]|\s*$)"
)


def _parse_common_stocks(section: str) -> list[dict]:
    """Extract holdings from the visible text of a fund section.

    Bounds parsing to the "Common Stocks" portion only (excludes treasuries,
    money market, derivatives, etc.). Returns deduplicated [{name, value}].
    """
    m_start = _CS_START_RE.search(section)
    m_end = _CS_END_RE.search(section)
    if not m_start or not m_end:
        return []
    body = section[m_start.end(): m_end.start()]

    holdings = []
    seen = set()
    for m in _HOLDING_RE.finditer(body):
        name = m.group("name").strip(" ,*^.")
        # Reject "industry header" style matches: name shouldn't contain a percent sign
        # or end with a section delimiter.
        if not name or "%" in name:
            continue
        # Reject obvious non-equity placeholders.
        upper = name.upper()
        if upper.startswith("TOTAL") or upper.startswith("COMMON STOCK") or upper.startswith("SCHEDULE"):
            continue
        if len(name) < 3:
            continue
        try:
            shares = float(m.group("shares").replace(",", ""))
            value = float(m.group("value").replace(",", ""))
        except ValueError:
            continue
        if shares < 1 or value < 1:
            continue
        # Dedupe on (name, value) — different filings sometimes list the same
        # security in multiple share-class rows; we treat them as one unless
        # values differ.
        key = (name, int(value))
        if key in seen:
            continue
        seen.add(key)
        holdings.append({"name": name, "shares": shares, "value": value})

    return holdings


def _net_assets(section: str) -> float | None:
    m = _NET_ASSETS_RE.search(section)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_nq_for_etf(html: str, etf: str) -> dict | None:
    """Returns {repPdDate, holdings: [{name, cusip, pctVal}]} or None."""
    if etf == "EUSA":
        located = _find_target_section_ishares(html)
    elif etf == "VTI":
        located = _find_target_section_vanguard(html, "TOTAL STOCK MARKET INDEX FUND")
    elif etf == "VT":
        located = _find_target_section_vanguard(html, "TOTAL WORLD STOCK INDEX FUND")
    else:
        return None
    if located is None:
        return None
    section, rep_date = located
    if not rep_date:
        return None

    common_stocks = _parse_common_stocks(section)
    if not common_stocks:
        return None

    net_assets = _net_assets(section)
    if not net_assets or net_assets < 1:
        return None

    holdings = []
    for h in common_stocks:
        pct = (h["value"] / net_assets) * 100.0
        # Light sanity bound: any single holding above 50% is parsing noise.
        if pct > 50:
            continue
        holdings.append({"name": h["name"], "cusip": "", "pctVal": pct})
    return {"repPdDate": rep_date, "holdings": holdings, "source": "n-q"}


# CIK + target-phrase config per ETF.
ETF_CONFIG = {
    "EUSA": {"cik": "0000930667"},
    "VTI":  {"cik": "0000036405"},
    "VT":   {"cik": "0000857489"},
}


def fetch_etf_historical(
    etf: str,
    cache_dir: Path,
    headers: dict,
    offline: bool,
) -> list[dict]:
    """Pull every available N-Q for the ETF and return parsed observations.

    Mirrors the contract of `holdings.fetch_etf_holdings` so the rest of the
    pipeline can consume both seamlessly.
    """
    cfg = ETF_CONFIG[etf]
    cik = cfg["cik"]
    cik_padded = cik.zfill(10)

    index_cache = cache_dir / f"nq_{etf}_index.json"

    if offline:
        if not index_cache.exists():
            print(f"  [{etf}] no cached N-Q index — skipping pre-2019 stage")
            return []
        filings = json.loads(index_cache.read_text())
    else:
        print(f"  [{etf}] listing N-Q filings via EDGAR submissions index ...")
        filings = list_nq_filings(cik_padded, headers)
        index_cache.write_text(json.dumps(filings, indent=2))
        print(f"  [{etf}] {len(filings)} N-Q filings indexed")

    observations: list[dict] = []
    for i, f in enumerate(filings):
        accession = f["accession"]
        primary = f.get("primaryDocument") or "primary_doc.xml"
        cache = cache_dir / f"nq_{etf}_{accession}.html"
        if cache.exists():
            html = cache.read_text()
        elif offline:
            continue
        else:
            try:
                html = fetch_nq_html(cik, accession, primary, headers)
            except httpx.HTTPError as e:
                print(f"    [{etf}] failed to fetch {accession}: {e}")
                continue
            cache.write_text(html)
            time.sleep(0.12)
        obs = parse_nq_for_etf(html, etf)
        if obs is None:
            continue
        observations.append(obs)
        if (i + 1) % 10 == 0 or i == len(filings) - 1:
            print(f"    [{etf}] processed {i + 1}/{len(filings)} N-Q filings, {len(observations)} parsed")

    # Dedupe by repPdDate (rare; same date filed twice).
    seen: dict[str, dict] = {}
    for o in observations:
        seen[o["repPdDate"]] = o
    return sorted(seen.values(), key=lambda o: o["repPdDate"])
