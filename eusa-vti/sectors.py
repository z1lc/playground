"""Map SEC Form N-PORT holding names to GICS sector via SEC company tickers
and yfinance.

Pipeline per holding:
    name -> normalized name -> ticker (via SEC company-tickers JSON files
    + a small manual override map) -> sector (via yfinance .info)

Caches are stored under raw_responses/:
    sec_company_tickers.json     -- raw SEC dump
    sec_company_tickers_ex.json  -- SEC exchange-listed dump
    ticker_sector.json           -- {ticker: {sector, longName, asOf}}
    name_skiplist.json           -- normalized names known to be non-equity
                                    (money funds etc.) so we don't keep
                                    re-trying them
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

CT_URL = "https://www.sec.gov/files/company_tickers.json"
CT_EX_URL = "https://www.sec.gov/files/company_tickers_exchange.json"

# Manual overrides for known mismatches (renames, inverted-name SEC entries,
# punctuation issues). Keep the keys in *normalized* form (output of normalize()).
MANUAL_OVERRIDES: dict[str, str] = {
    # Renames / corporate actions
    "MICROSTRATEGY": "MSTR",
    # Inverted "LAST FIRST" SEC entries
    "CHARLES SCHWAB": "SCHW",
    "ROWE PRICE": "TROW",       # SEC: "PRICE T ROWE GROUP"
    # Companies missing from SEC tickers files
    "HOLOGIC": "HOLX",
    "GAMING LEISURE PROPERTIES": "GLPI",
    "CRH": "CRH",
    "OREILLY AUTOMOTIVE": "ORLY",
    "WW GRAINGER": "GWW",
    "HESS": "HES",
    "DISCOVER FINANCIAL SERVICES": "DFS",
    "SCHLUMBERGER": "SLB",
    "DR HORTON": "DHI",
    "LIBERTY MEDIA FORMULA ONE": "FWONK",
}

# Names that should be skipped entirely (cash/money market, security-lending
# subsidiaries, future contracts).
SKIP_NAME_FRAGMENTS: tuple[str, ...] = (
    "MONEY MARKET",
    "LIQUIDITY FUND",
    "CASH FUND",
    "GOVERNMENT FUND",
    "BLACKROCK FUNDING",  # iShares securities-lending subsidiary
    "EMINI",              # S&P futures contracts
)

# yfinance returns "sector" for stocks; this is the GICS-aligned label.
#
# The narrow Information Technology sector excludes a lot of what people
# colloquially call "tech": META, GOOGL, NFLX live in Communication Services
# (since the 2018 GICS reorg), and AMZN/TSLA live in Consumer Cyclical. We
# expose a *broad* tech view that covers the full AI-bubble surface area:
#   - GICS Technology
#   - GICS Communication Services
#   - explicit additions: AMZN, TSLA
# This roughly approximates the pre-2018 Information Technology sector
# definition (with AMZN/TSLA layered in for the AI-narrative reading).
TECH_BROAD_SECTORS = {"Technology", "Communication Services"}
TECH_BROAD_TICKER_OVERRIDES = {"AMZN", "TSLA"}


def is_tech_broad(ticker: str | None, sector: str | None) -> bool:
    if sector in TECH_BROAD_SECTORS:
        return True
    if ticker and ticker in TECH_BROAD_TICKER_OVERRIDES:
        return True
    return False

CORP_SUFFIX_RE = re.compile(
    r"\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANIES|"
    r"COMPANY|COS|CO|LIMITED|LTD|LLC|PLC|HOLDINGS|HOLDING|GROUP|"
    r"TRUST|NV|SA|AB|AG|THE|AND|OF)\b"
)


def normalize_name(s: str) -> str:
    """Normalize a company name for lookup. See module docstring."""
    s = s.upper()
    s = s.replace("'", "")
    # Strip trailing state markers like "INC / MA", "/DE", "\DE\"
    s = re.sub(r"\\[A-Z]+\\", " ", s)
    s = re.sub(r"/\s*[A-Z]+\b", " ", s)
    # Punctuation -> space
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    # Multi-word legal suffixes
    s = re.sub(r"\bPUBLIC LIMITED COMPANY\b", " ", s)
    s = re.sub(r"\bLIMITED LIABILITY COMPANY\b", " ", s)
    # Class / Series markers
    s = re.sub(r"\bCLASS [A-Z]\b|\bCL [A-Z]\b|\bSERIES [A-Z]\b", " ", s)
    # Strip single-word suffixes (loop until stable so trailing "GROUP INC" → empty)
    prev = None
    while prev != s:
        prev = s
        s = CORP_SUFFIX_RE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
    # Drop standalone single letters (handles "U S BANCORP" → "BANCORP")
    s = re.sub(r"\b[A-Z]\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_skippable(name: str) -> bool:
    upper = name.upper()
    return any(frag in upper for frag in SKIP_NAME_FRAGMENTS)


def build_name_to_ticker_map(cache_dir: Path, headers: dict, offline: bool) -> dict[str, str]:
    """Return {normalized_name: ticker}.

    Loads from cache when available; only fetches if cache misses (or --offline
    is set and cache exists).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    ct_cache = cache_dir / "sec_company_tickers.json"
    ex_cache = cache_dir / "sec_company_tickers_ex.json"

    def fetch_or_cached(url: str, cache_path: Path) -> dict:
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        if offline:
            return {}
        resp = httpx.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        cache_path.write_text(resp.text)
        return resp.json()

    ct = fetch_or_cached(CT_URL, ct_cache)
    ex = fetch_or_cached(CT_EX_URL, ex_cache)

    out: dict[str, str] = {}
    # Load exchange-listed file first (more authoritative for active names)
    if isinstance(ex, dict) and "fields" in ex and "data" in ex:
        fields = ex["fields"]
        for row in ex["data"]:
            rec = dict(zip(fields, row))
            norm = normalize_name(rec.get("name", ""))
            if norm and norm not in out:
                out[norm] = rec.get("ticker", "")
    # Fold in company_tickers.json for extras
    if isinstance(ct, dict):
        for entry in ct.values():
            norm = normalize_name(entry.get("title", ""))
            if norm and norm not in out:
                out[norm] = entry.get("ticker", "")
    # Manual overrides win
    out.update(MANUAL_OVERRIDES)
    return out


def lookup_ticker(name: str, name_map: dict[str, str]) -> str | None:
    if is_skippable(name):
        return None
    norm = normalize_name(name)
    return name_map.get(norm)


def fetch_sectors_for_tickers(
    tickers: set[str],
    cache_path: Path,
    offline: bool,
    progress_label: str = "sectors",
    max_workers: int = 1,
) -> dict[str, str | None]:
    """For each ticker, return its yfinance sector (cached forever).

    Uses a thread pool because yfinance .info is I/O-bound and Yahoo handles
    moderate concurrency fine. The cache is persisted every save_every
    completions so a Ctrl-C / kill never loses much progress.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    todo = sorted(t for t in tickers if t and t not in cache)
    print(f"  {progress_label}: {len(cache)} cached, {len(todo)} new")

    if not todo:
        return {t: (cache.get(t) or {}).get("sector") for t in cache}
    if offline:
        print(f"  {progress_label}: --offline, skipping {len(todo)} unfetched tickers")
        return {t: (cache.get(t) or {}).get("sector") for t in cache}

    import yfinance as yf

    rate_limit_backoff = {"value": 1.0}  # mutable so the helper can grow it

    def fetch_one(ticker: str) -> tuple[str, dict]:
        for attempt in range(3):
            try:
                info = yf.Ticker(ticker).info or {}
                rate_limit_backoff["value"] = max(1.0, rate_limit_backoff["value"] * 0.95)
                return ticker, {
                    "sector": info.get("sector"),
                    "longName": info.get("longName") or info.get("shortName"),
                }
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                # Rate-limited / 401 invalid-crumb: back off and retry
                if "Rate limited" in msg or "Too Many Requests" in msg or "Invalid Crumb" in msg or "401" in msg:
                    sleep_for = rate_limit_backoff["value"]
                    rate_limit_backoff["value"] = min(60.0, rate_limit_backoff["value"] * 2)
                    time.sleep(sleep_for)
                    continue
                return ticker, {"sector": None, "longName": None, "error": msg[:120]}
        return ticker, {"sector": None, "longName": None, "error": "rate-limited after retries"}

    save_every = 50
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(fetch_one, t) for t in todo]
        for fut in as_completed(futures):
            ticker, info = fut.result()
            cache[ticker] = info
            completed += 1
            if completed % save_every == 0 or completed == len(todo):
                cache_path.write_text(json.dumps(cache))
                print(f"    {progress_label}: {completed}/{len(todo)} fetched (backoff={rate_limit_backoff['value']:.1f}s)")
    cache_path.write_text(json.dumps(cache))

    return {t: (cache.get(t) or {}).get("sector") for t in cache}


def ticker_is_tech(ticker: str, sector_map: dict[str, str | None]) -> bool:
    return sector_map.get(ticker) in TECH_SECTORS
