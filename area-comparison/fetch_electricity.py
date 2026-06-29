# /// script
# dependencies = [
#   "httpx",
#   "openpyxl",
# ]
# ///
"""Fetch residential electricity bill + generation mix for states and cities.

Sources (primary, latest release):
  - State avg monthly bill + generation mix: EIA API v2 (api.eia.gov).
      bill  = residential revenue / residential customers / 12  (EIA-861 basis)
      mix   = net generation by fuel type, all sectors (sectorid 99), as % of total.
  - City avg monthly bill: EIA-861 "Sales to Ultimate Customers" detailed file,
      bundled residential (full service = generation + delivery), dominant utility.
  - City generation mix: each utility's published power-content label / fuel-mix
      disclosure (hardcoded below with citation + label year; not exposed via API).

Prints JSON snippets to paste into the inline DATA object in index.html.
Requires EIA_API_KEY in the environment (free key: https://api.eia.gov/register).
"""

import os
from pathlib import Path

import httpx
import openpyxl

SCRIPT_DIR = Path(__file__).parent
CACHE_DIR = SCRIPT_DIR / "raw_eia861"
EIA_KEY = os.environ["EIA_API_KEY"]
EIA_BASE = "https://api.eia.gov/v2"

EIA861_YEAR = 2024
EIA861_ZIP_URL = f"https://www.eia.gov/electricity/data/eia861/zip/f861{EIA861_YEAR}.zip"

STATES: dict[str, str] = {"California": "CA", "New York": "NY", "Georgia": "GA", "Washington": "WA"}

# Destination key -> EIA fueltypeids to sum. Buckets partition net generation (≈ ALL total).
GEN_BUCKETS: dict[str, list[str]] = {
    "natural_gas": ["NG"],
    "coal": ["COW"],
    "nuclear": ["NUC"],
    "hydro": ["HYC", "HPS"],
    "wind": ["WND"],
    "solar": ["SUN"],
    "geo_biomass": ["GEO", "BIO"],
    "other": ["PET", "OOG", "OTH"],
}

# City -> (EIA-861 utility name substring, state) for the dominant residential utility.
CITY_UTILITY: dict[str, tuple[str, str]] = {
    "San Francisco": ("pacific gas & electric", "CA"),
    "New York City": ("consolidated edison co-ny", "NY"),
    "Atlanta": ("georgia power", "GA"),
    "Seattle": ("city of seattle", "WA"),
}

# City generation mix from each utility's published power-content label (% delivered).
# Not available via API; transcribed from the latest official disclosure.
CITY_GEN_MIX: dict[str, dict[str, float]] = {
    # PG&E 2024 Power Content Label (CA Energy Commission). Nuclear is high because CCA
    # load migration shrank PG&E's bundled portfolio. Renewable 23% = solar 14 + wind 4
    # + biomass/biogas 3 + small hydro ~1; large hydro 12; gas 2.
    # https://www.pge.com/assets/pge/docs/account/billing-and-assistance/bill-inserts/1225-power-content-label.pdf
    "San Francisco": {
        "natural_gas": 2.0,
        "nuclear": 63.0,
        "hydro": 13.0,
        "solar": 14.0,
        "wind": 4.0,
        "geo_biomass": 3.0,
    },
    # Con Edison delivered fuel mix is allocated by the NYISO (based on EIA data) — i.e. the
    # NY statewide system mix. Mirrors the NY state figures from EIA below.
    # https://lite.conedison.com/ehs/2024-sustainability-report/our-commodities/electric/
    "New York City": {
        "natural_gas": 47.2,
        "nuclear": 21.6,
        "hydro": 19.2,
        "wind": 5.2,
        "solar": 4.0,
        "geo_biomass": 1.1,
        "other": 1.7,
    },
    # Georgia Power 2024 actual energy supplied (2025 Integrated Resource Plan / Facts & Figures).
    # Renewables (7%) are solar-dominant; "null/unspecified" energy -> other.
    # https://www.georgiapower.com/content/dam/georgia-power/pdfs/company-pdfs/2025-Integrated-Resource-Plan.pdf
    "Atlanta": {"natural_gas": 40.0, "nuclear": 29.0, "coal": 16.0, "solar": 7.0, "hydro": 2.0, "other": 6.0},
    # Seattle City Light 2024 fuel mix (seattle.gov). No coal/gas in portfolio.
    # https://www.seattle.gov/city-light/energy/power-supply-and-delivery
    "Seattle": {"hydro": 77.5, "wind": 10.5, "nuclear": 5.8, "other": 5.3, "geo_biomass": 0.8},
}

# Order metrics for readable output (matches SECTION_CONFIG row order).
MIX_ORDER = ["natural_gas", "coal", "nuclear", "hydro", "wind", "solar", "geo_biomass", "other"]


def eia_get(path: str, params: dict) -> dict:
    resp = httpx.get(EIA_BASE + path, params={**params, "api_key": EIA_KEY}, timeout=60)
    resp.raise_for_status()
    return resp.json()["response"]


def state_bill(stateid: str) -> tuple[int, str]:
    r = eia_get(
        "/electricity/retail-sales/data/",
        {
            "frequency": "annual",
            "data[0]": "revenue",
            "data[1]": "customers",
            "facets[stateid][]": stateid,
            "facets[sectorid][]": "RES",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": "1",
        },
    )
    d = r["data"][0]
    bill = float(d["revenue"]) * 1e6 / float(d["customers"]) / 12
    return round(bill), d["period"]


def state_mix(stateid: str) -> tuple[dict[str, float], str]:
    r = eia_get(
        "/electricity/electric-power-operational-data/data/",
        {
            "frequency": "annual",
            "data[0]": "generation",
            "facets[location][]": stateid,
            "facets[sectorid][]": "99",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": "60",
        },
    )
    period = r["data"][0]["period"]
    vals = {row["fueltypeid"]: float(row["generation"] or 0) for row in r["data"] if row["period"] == period}
    total = vals.get("ALL", 0)
    mix = {}
    for key in MIX_ORDER:
        pct = round(sum(vals.get(i, 0) for i in GEN_BUCKETS[key]) / total * 100, 1)
        if pct >= 0.1:
            mix[key] = pct
    return mix, period


def download_eia861() -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    zip_path = CACHE_DIR / f"f861{EIA861_YEAR}.zip"
    if not zip_path.exists():
        resp = httpx.get(EIA861_ZIP_URL, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        zip_path.write_bytes(resp.content)
    import zipfile

    xlsx_name = f"Sales_Ult_Cust_{EIA861_YEAR}.xlsx"
    xlsx_path = CACHE_DIR / xlsx_name
    if not xlsx_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extract(xlsx_name, CACHE_DIR)
    return xlsx_path


def city_bills() -> dict[str, int]:
    ws = openpyxl.load_workbook(download_eia861(), read_only=True, data_only=True)["States"]
    rows = list(ws.iter_rows(min_row=4, values_only=True))
    bills = {}
    for city, (needle, state) in CITY_UTILITY.items():
        for row in rows:
            name = (row[2] or "").lower()
            # Part 'A' + Service 'Bundled' = full-service residential (generation + delivery).
            if needle in name and row[6] == state and row[3] == "A" and row[4] == "Bundled":
                rev_k, cust = row[9] or 0, row[11] or 0
                bills[city] = round(rev_k * 1000 / cust / 12)
                break
    return bills


def emit(name: str, bill: int, mix: dict[str, float]) -> None:
    parts = [f'"avg_monthly_bill":{bill}'] + [f'"{k}":{mix[k]}' for k in MIX_ORDER if k in mix]
    print(f'  "{name}": "electricity":{{{", ".join(parts)}}}')


def main() -> None:
    print("=== STATES (EIA API; gen=net generation all sectors, bill=EIA-861 basis) ===\n")
    for name, sid in STATES.items():
        bill, byr = state_bill(sid)
        mix, gyr = state_mix(sid)
        emit(name, bill, mix)
        print(f"      bill {byr}, gen {gyr}, mix sum {sum(mix.values()):.1f}%\n")

    print(f"=== CITIES (bill=EIA-861 {EIA861_YEAR} bundled residential; mix=utility power-content label) ===\n")
    bills = city_bills()
    for city in CITY_UTILITY:
        emit(city, bills[city], CITY_GEN_MIX[city])
        print(f"      utility={CITY_UTILITY[city][0]}, mix sum {sum(CITY_GEN_MIX[city].values()):.1f}%\n")


if __name__ == "__main__":
    main()
