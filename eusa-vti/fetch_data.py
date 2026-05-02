# /// script
# dependencies = [
#   "httpx",
#   "pandas",
#   "yfinance",
#   "lxml",
#   "beautifulsoup4",
# ]
# ///
"""Build the EUSA-vs-VTI comparison dataset.

Pipeline:
  1. Daily total-return prices for EUSA and VTI from yfinance -> drawdown +
     cumulative return timeseries.
  2. Monthly holdings from SEC EDGAR N-PORT filings (2019+) -> Mag 7 weight,
     broader AI basket weight, and Tech & Communication Services sector
     weight per ETF.

Each non-daily metric is forward-filled to daily so they share one daily
timeseries axis in the chart.

Outputs:
  - eusa-vti/data.json
  - eusa-vti/index.html (DATA block between // DATA_START and // DATA_END is
    rewritten in place if the file already exists)

Usage:
  uv run fetch_data.py            # fetch live, fall back to cached responses
  uv run fetch_data.py --offline  # never hit the network
  uv run fetch_data.py --snapshot # save fresh raw response snapshots
  uv run fetch_data.py --skip-holdings  # skip slow N-PORT stage
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import httpx
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw_responses"
DATA_JSON = HERE / "data.json"
INDEX_HTML = HERE / "index.html"
TODAY = date(2026, 5, 2)

ETFS = ["EUSA", "VTI"]
PRICE_START = "2010-05-07"  # EUSA inception

# Mag 7: cap-weighted AI mega-caps. GOOGL and GOOG counted together (same
# economics, different share class).
MAG7 = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"}

# Broader AI bubble basket: Mag 7 + chip / infra / AI-narrative names.
AI_BASKET_EXTRA = {"AVGO", "AMD", "ORCL", "CRM", "NFLX", "PLTR", "SMCI", "DELL", "ARM", "MU", "SNOW"}
AI_BASKET = MAG7 | AI_BASKET_EXTRA

USER_AGENT = "playground-eusa-vti/1.0 (rsanek@gmail.com)"


# -----------------------------------------------------------------------------
# Stage 1: prices, drawdown, cumulative return
# -----------------------------------------------------------------------------

def fetch_prices(offline: bool, snapshot: bool) -> pd.DataFrame:
    """Return a DataFrame indexed by date with one column per ETF (adjusted close).

    Cache-first: if prices.csv exists, use it unless --snapshot is set. The
    daily price series is large and rarely changes intra-day, so re-running
    the script shouldn't re-download by default.
    """
    cache = RAW / "prices.csv"
    if cache.exists() and not snapshot:
        return pd.read_csv(cache, index_col=0, parse_dates=True)
    if offline:
        sys.exit(f"--offline given but {cache} does not exist")

    import yfinance as yf
    print(f"yfinance: downloading {ETFS} from {PRICE_START} ...")
    raw = yf.download(ETFS, start=PRICE_START, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        sys.exit("yfinance returned no data")
    closes = raw["Close"].dropna(how="all")
    closes.columns = [str(c) for c in closes.columns]
    closes = closes[ETFS]
    cache.parent.mkdir(parents=True, exist_ok=True)
    closes.to_csv(cache)
    return closes


def compute_drawdown_and_return(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drawdown from running peak (in %, signed negative); cumulative return indexed to 100."""
    drawdown = (prices / prices.cummax() - 1.0) * 100.0
    cum_return = prices / prices.iloc[0] * 100.0
    return drawdown, cum_return


# -----------------------------------------------------------------------------
# Stage 2: holdings from SEC EDGAR N-PORT (deferred — see fetch_holdings.py)
# -----------------------------------------------------------------------------

# Series IDs are the SEC's identifier for each individual ETF inside a trust.
# Filings come from the trust's CIK; each filing covers one series.
EUSA_SERIES_ID = "S000038205"  # iShares MSCI USA Equal Weighted ETF
EUSA_TRUST_CIK = "0001100663"  # iShares Trust
VTI_SERIES_ID = "S000003091"   # Vanguard Total Stock Market Index Fund
VTI_TRUST_CIK = "0000036405"   # Vanguard Index Funds


def fetch_holdings_snapshots(offline: bool, snapshot: bool) -> dict:
    """Return {etf: [{date, mag7Pct, aiBasketPct, totalHoldings}]}.

    Each entry is one quarterly observation parsed from an N-PORT-P filing
    (the report-period date is the as-of date for those holdings).
    """
    from holdings import fetch_all_holdings
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    return fetch_all_holdings(RAW, headers, offline)



# -----------------------------------------------------------------------------
# Assembly
# -----------------------------------------------------------------------------

def series_to_pairs(s: pd.Series) -> list[list]:
    """Convert a date-indexed series to [[YYYY-MM-DD, rounded_value], ...].

    Drops NaNs. Rounds to 4 decimals to keep JSON small.
    """
    out = []
    for ts, v in s.dropna().items():
        if isinstance(ts, pd.Timestamp):
            d = ts.strftime("%Y-%m-%d")
        else:
            d = str(ts)[:10]
        out.append([d, round(float(v), 4)])
    return out


def build_payload(prices, drawdown, cum_return, holdings) -> dict:
    metrics = []

    # 1. Drawdown
    metrics.append({
        "id": "drawdown",
        "label": "Drawdown from peak",
        "unit": "%",
        "format": "percent",
        "axisDomain": [-50, 0],
        "series": {etf: series_to_pairs(drawdown[etf]) for etf in ETFS},
    })

    # 2. Cumulative total return
    metrics.append({
        "id": "cumReturn",
        "label": "Cumulative total return (start = 100)",
        "unit": "",
        "format": "index",
        "axisDomain": None,
        "series": {etf: series_to_pairs(cum_return[etf]) for etf in ETFS},
    })

    # 3-5. Holdings-derived metrics. Each ETF entry in `holdings` is a list of
    # monthly observations with {date, mag7Pct, aiBasketPct, techSectorPct}.
    def holdings_series(field: str) -> dict:
        out = {}
        for etf in ETFS:
            obs = holdings.get(etf, [])
            out[etf] = [[o["date"], round(o[field], 4)] for o in obs if o.get(field) is not None]
        return out

    metrics.append({
        "id": "mag7",
        "label": "Mag 7 weight",
        "unit": "%",
        "format": "percent",
        "axisDomain": None,
        "series": holdings_series("mag7Pct"),
    })
    metrics.append({
        "id": "aiBasket",
        "label": "Broader AI basket weight",
        "unit": "%",
        "format": "percent",
        "axisDomain": None,
        "series": holdings_series("aiBasketPct"),
    })
    metrics.append({
        "id": "techSector",
        "label": "Tech & Communication Services weight",
        "unit": "%",
        "format": "percent",
        "axisDomain": None,
        "series": holdings_series("techBroadPct"),
    })

    return {
        "generatedAt": TODAY.isoformat(),
        "etfs": ETFS,
        "metrics": metrics,
        "metadata": {
            "mag7Constituents": sorted(MAG7),
            "aiBasketConstituents": sorted(AI_BASKET),
            "priceStart": PRICE_START,
            "testfolioReference": "https://testfol.io/?s=1Q1EK9qneMy",
            "sources": {
                "prices": "yfinance (Yahoo Finance) auto-adjusted close",
                "holdings": "SEC EDGAR Form N-PORT filings",
            },
        },
    }


def update_inline_data(payload: dict) -> bool:
    if not INDEX_HTML.exists():
        return False
    html = INDEX_HTML.read_text()
    js = "    const DATA = " + json.dumps(payload) + ";\n"
    pattern = re.compile(r"(// DATA_START\n)(.*?)(    // DATA_END)", re.DOTALL)
    if not pattern.search(html):
        print(f"warning: {INDEX_HTML} has no DATA_START/DATA_END sentinels — skipping inline update", file=sys.stderr)
        return False
    new_html = pattern.sub(lambda m: m.group(1) + js + m.group(3), html)
    INDEX_HTML.write_text(new_html)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use cached responses, never hit the network")
    ap.add_argument("--snapshot", action="store_true", help="save fresh raw response snapshots")
    ap.add_argument("--skip-holdings", action="store_true", help="skip the N-PORT holdings stage")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    print("Stage 1: prices")
    prices = fetch_prices(args.offline, args.snapshot)
    drawdown, cum_return = compute_drawdown_and_return(prices)
    for etf in ETFS:
        max_dd = drawdown[etf].min()
        cagr_years = (prices.index[-1] - prices.index[0]).days / 365.25
        cagr = (cum_return[etf].iloc[-1] / 100) ** (1 / cagr_years) - 1
        print(f"  {etf}: {len(prices)} daily obs, max DD {max_dd:.2f}%, CAGR {cagr*100:.2f}%")

    print("Stage 2: holdings")
    if args.skip_holdings:
        print("  (skipped via --skip-holdings)")
        holdings = {etf: [] for etf in ETFS}
    else:
        holdings = fetch_holdings_snapshots(args.offline, args.snapshot)
        for etf in ETFS:
            print(f"  {etf}: {len(holdings.get(etf, []))} monthly observations")

    payload = build_payload(prices, drawdown, cum_return, holdings)
    DATA_JSON.write_text(json.dumps(payload, separators=(",", ":")))
    size_kb = DATA_JSON.stat().st_size / 1024
    print(f"wrote {DATA_JSON} ({size_kb:.0f} KB)")

    if update_inline_data(payload):
        print(f"updated DATA block in {INDEX_HTML}")


if __name__ == "__main__":
    main()
