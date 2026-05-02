"""SEC EDGAR N-PORT-P holdings fetcher for EUSA and VTI.

Two-pass design so we can attach sector classification without re-parsing
XML:

    pass 1: extract holdings from each cached XML filing
    -> collect the union of all (name, cusip) tuples
    pass 2: build name -> ticker map (SEC company tickers)
            ticker -> sector map (yfinance, cached)
            then re-aggregate each filing's holdings into:
              mag7Pct, aiBasketPct, techSectorPct
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

import httpx

import sectors  # local module

NPORT_NS = {"n": "http://www.sec.gov/edgar/nport"}


# Curated CUSIP / name mapping for the AI basket. CUSIP is the most reliable
# identifier in N-PORT (ticker isn't carried, ISIN often blank). Name fallback
# handles split shares and corporate actions that change CUSIP.
BASKET_CUSIPS: dict[str, set[str]] = {
    "AAPL":  {"037833100"},
    "MSFT":  {"594918104"},
    "GOOGL": {"02079K305"},
    "GOOG":  {"02079K107"},
    "AMZN":  {"023135106"},
    "NVDA":  {"67066G104"},
    "META":  {"30303M102"},
    "TSLA":  {"88160R101"},
    "AVGO":  {"11135F101"},
    "AMD":   {"007903107"},
    "ORCL":  {"68389X105"},
    "CRM":   {"79466L302"},
    "NFLX":  {"64110L106"},
    "PLTR":  {"69608A108"},
    "SMCI":  {"86800U104"},
    "DELL":  {"24703L202"},
    "ARM":   {"042068100"},
    "MU":    {"595112103"},
    "SNOW":  {"833445109"},
}

BASKET_NAME_FRAGMENTS: dict[str, list[str]] = {
    "AAPL":  ["APPLE INC"],
    "MSFT":  ["MICROSOFT"],
    "GOOGL": ["ALPHABET INC CL A", "ALPHABET INC. CLASS A", "ALPHABET CL A"],
    "GOOG":  ["ALPHABET INC CL C", "ALPHABET INC. CLASS C", "ALPHABET CL C"],
    "AMZN":  ["AMAZON.COM", "AMAZON COM"],
    "NVDA":  ["NVIDIA"],
    "META":  ["META PLATFORMS"],
    "TSLA":  ["TESLA"],
    "AVGO":  ["BROADCOM"],
    "AMD":   ["ADVANCED MICRO DEVICES"],
    "ORCL":  ["ORACLE CORP"],
    "CRM":   ["SALESFORCE"],
    "NFLX":  ["NETFLIX"],
    "PLTR":  ["PALANTIR"],
    "SMCI":  ["SUPER MICRO COMPUTER"],
    "DELL":  ["DELL TECHNOLOGIES"],
    "ARM":   ["ARM HOLDINGS"],
    "MU":    ["MICRON TECHNOLOGY"],
    "SNOW":  ["SNOWFLAKE"],
}

MAG7 = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"}
AI_BASKET = set(BASKET_CUSIPS.keys())


def classify_basket_holding(name: str, cusip: str) -> str | None:
    """Return basket-ticker for a holding, or None if not in the AI basket."""
    cusip = (cusip or "").strip()
    upper_name = (name or "").upper()
    for ticker, cusips in BASKET_CUSIPS.items():
        if cusip in cusips:
            return ticker
    for ticker, fragments in BASKET_NAME_FRAGMENTS.items():
        for frag in fragments:
            if frag in upper_name:
                return ticker
    return None


def http_get(url: str, headers: dict, attempts: int = 3, sleep_on_429: float = 1.0) -> httpx.Response:
    last = None
    for i in range(attempts):
        resp = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        if resp.status_code == 429:
            time.sleep(sleep_on_429 * (i + 1))
            last = resp
            continue
        resp.raise_for_status()
        return resp
    if last is not None:
        last.raise_for_status()
    raise RuntimeError(f"failed after {attempts} attempts: {url}")


def list_nport_filings(series_id: str, headers: dict) -> list[dict]:
    url = (
        "https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{series_id}%22&forms=NPORT-P"
        "&dateRange=custom&startdt=2019-01-01&enddt=2026-12-31"
    )
    resp = http_get(url, headers=headers)
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])
    out = []
    for h in hits:
        _id = h.get("_id", "")
        accession = _id.split(":")[0]
        src = h.get("_source", {})
        display = (src.get("display_names") or [""])[0]
        cik = ""
        if "CIK " in display:
            cik = display.rsplit("CIK ", 1)[-1].rstrip(")").strip().lstrip("0")
        out.append({
            "accession": accession,
            "filingDate": src.get("file_date"),
            "cik": cik,
        })
    return out


def fetch_filing_xml(cik: str, accession: str, headers: dict) -> str:
    accession_clean = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/primary_doc.xml"
    return http_get(url, headers=headers).text


def extract_holdings(xml_str: str, target_series_id: str) -> dict | None:
    """Return {repPdDate, holdings: [{name, cusip, pctVal}, ...]}.

    Returns None if the filing's series doesn't match target_series_id.
    """
    from lxml import etree
    root = etree.fromstring(xml_str.encode("utf-8"))
    series_ids = root.findall(".//n:seriesId", NPORT_NS)
    if not any((s.text or "").strip() == target_series_id for s in series_ids):
        return None
    rep_date = (root.findtext(".//n:genInfo/n:repPdDate", namespaces=NPORT_NS) or "").strip()
    if not rep_date:
        return None
    holdings = []
    for h in root.findall(".//n:invstOrSec", NPORT_NS):
        name = (h.findtext("n:name", namespaces=NPORT_NS) or "").strip()
        cusip = (h.findtext("n:cusip", namespaces=NPORT_NS) or "").strip()
        pct_text = h.findtext("n:pctVal", namespaces=NPORT_NS) or "0"
        try:
            pct = float(pct_text)
        except ValueError:
            continue
        holdings.append({"name": name, "cusip": cusip, "pctVal": pct})
    return {"repPdDate": rep_date, "holdings": holdings}


def aggregate(
    extracted: dict,
    name_to_ticker: dict[str, str],
    sector_map: dict[str, str | None],
) -> dict:
    """Compute per-filing metrics from extracted holdings."""
    mag7_total = 0.0
    ai_total = 0.0
    tech_broad_total = 0.0
    classified_w = 0.0
    skipped_w = 0.0
    for h in extracted["holdings"]:
        name = h["name"]
        cusip = h["cusip"]
        pct = h["pctVal"]

        # Mag 7 / AI basket via curated CUSIP/name list (same as before).
        basket_ticker = classify_basket_holding(name, cusip)
        if basket_ticker in MAG7:
            mag7_total += pct
        if basket_ticker in AI_BASKET:
            ai_total += pct

        # Sector classification: skip non-equity entries (cash funds, futures).
        if sectors.is_skippable(name):
            skipped_w += pct
            continue
        ticker = sectors.lookup_ticker(name, name_to_ticker)
        if ticker is None:
            continue
        sec = sector_map.get(ticker)
        if sec is None:
            continue
        classified_w += pct
        if sectors.is_tech_broad(ticker, sec):
            tech_broad_total += pct

    return {
        "repPdDate": extracted["repPdDate"],
        "mag7Pct": round(mag7_total, 4),
        "aiBasketPct": round(ai_total, 4),
        "techBroadPct": round(tech_broad_total, 4),
        "totalHoldings": len(extracted["holdings"]),
        "classifiedWeight": round(classified_w, 4),
        "skippedWeight": round(skipped_w, 4),
    }


def fetch_etf_holdings(
    etf: str,
    cik: str,
    series_id: str,
    cache_dir: Path,
    headers: dict,
    offline: bool,
) -> tuple[list[dict], list[dict]]:
    """Return (extracted_observations, filings_index).

    extracted_observations: list of {repPdDate, holdings} (one per filing).
    """
    index_cache = cache_dir / f"nport_{etf}_index.json"
    if offline:
        if not index_cache.exists():
            print(f"  [{etf}] no cached index — skipping holdings stage")
            return [], []
        filings = json.loads(index_cache.read_text())
    else:
        print(f"  [{etf}] listing NPORT-P filings via EDGAR full-text search ...")
        filings = list_nport_filings(series_id, headers)
        index_cache.write_text(json.dumps(filings, indent=2))
        print(f"  [{etf}] {len(filings)} filings indexed")

    observations: list[dict] = []
    for i, f in enumerate(filings):
        accession = f["accession"]
        f_cik = f.get("cik") or cik
        xml_cache = cache_dir / f"nport_{etf}_{accession}.xml"
        if xml_cache.exists():
            xml_str = xml_cache.read_text()
        elif offline:
            print(f"    [{etf}] missing cached filing {accession} — skipping")
            continue
        else:
            try:
                xml_str = fetch_filing_xml(f_cik, accession, headers)
            except httpx.HTTPError as e:
                print(f"    [{etf}] failed to fetch {accession}: {e}")
                continue
            xml_cache.write_text(xml_str)
            time.sleep(0.12)
        ext = extract_holdings(xml_str, series_id)
        if ext is None:
            continue
        observations.append(ext)
        if (i + 1) % 10 == 0 or i == len(filings) - 1:
            print(f"    [{etf}] extracted {i + 1}/{len(filings)} filings, {len(observations)} matched")

    # Deduplicate by repPdDate.
    seen: dict[str, dict] = {}
    for obs in observations:
        seen[obs["repPdDate"]] = obs
    out = sorted(seen.values(), key=lambda o: o["repPdDate"])
    return out, filings


def fetch_all_holdings(cache_dir: Path, headers: dict, offline: bool) -> dict[str, list[dict]]:
    """Top-level entry: fetch holdings for both ETFs and aggregate metrics."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    targets = [
        ("EUSA", "0000930667", "S000028709"),
        ("VTI",  "0000036405", "S000002848"),
    ]

    # Pass 1: extract holdings from cached XML for each ETF.
    extracted_per_etf: dict[str, list[dict]] = {}
    all_names: set[str] = set()
    for etf, cik, series_id in targets:
        cik_no_pad = cik.lstrip("0")
        obs, _ = fetch_etf_holdings(etf, cik_no_pad, series_id, cache_dir, headers, offline)
        extracted_per_etf[etf] = obs
        for o in obs:
            for h in o["holdings"]:
                if not sectors.is_skippable(h["name"]):
                    all_names.add(h["name"])
    print(f"  collected {len(all_names)} unique holding names across both ETFs")

    # Pass 2a: name -> ticker.
    name_to_ticker = sectors.build_name_to_ticker_map(cache_dir, headers, offline)
    print(f"  name->ticker map: {len(name_to_ticker)} entries")

    tickers_needed: set[str] = set()
    for name in all_names:
        t = sectors.lookup_ticker(name, name_to_ticker)
        if t:
            tickers_needed.add(t)
    print(f"  {len(tickers_needed)} unique tickers need sector classification")

    # Pass 2b: ticker -> sector via yfinance (cached).
    sector_cache_path = cache_dir / "ticker_sector.json"
    sector_map = sectors.fetch_sectors_for_tickers(
        tickers_needed, sector_cache_path, offline, progress_label="sectors"
    )

    # Pass 3: aggregate per filing.
    out: dict[str, list[dict]] = {}
    for etf, _, _ in targets:
        agg = []
        for ext in extracted_per_etf[etf]:
            row = aggregate(ext, name_to_ticker, sector_map)
            agg.append({
                "date": row["repPdDate"],
                "mag7Pct": row["mag7Pct"],
                "aiBasketPct": row["aiBasketPct"],
                "techBroadPct": row["techBroadPct"],
                "totalHoldings": row["totalHoldings"],
                "classifiedWeight": row["classifiedWeight"],
            })
        out[etf] = agg
    return out
