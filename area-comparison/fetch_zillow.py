# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""Fetch Zillow ZHVI neighborhood home-value data and print inline `housing` objects.

Prints one `housing` JSON object per neighborhood (compact, matching the inline DATA style in
index.html): typical home values by bedroom (mean of the trailing 12 monthly ZHVI values), a
home-price index (annual January values 2000-2025, normalized to 100 at 2000), and its CAGR.
Downloaded CSVs are cached in raw_zillow/ (gitignored). Paste the output into DATA.areas.neighborhoods.
"""

import csv
import json
from pathlib import Path

import httpx

SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR / "raw_zillow"
BASE_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi"

ALL_HOMES_CSV = "Neighborhood_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
BEDROOM_CSVS = {
    2: "Neighborhood_zhvi_bdrmcnt_2_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    3: "Neighborhood_zhvi_bdrmcnt_3_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    4: "Neighborhood_zhvi_bdrmcnt_4_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
}

# Zillow neighborhood RegionIDs (GA / Atlanta). Sweet Auburn (276600) is omitted: its ZHVI history
# starts in 2014 (no 2000 baseline for the index) and it has no bedroom-specific data.
REGION_IDS = {
    "Inman Park": "272817",
    "Reynoldstown": "269422",
    "Cabbagetown": "127516",
    "Old Fourth Ward": "269397",
    # Atlanta, GA (not same-named Piedmont Heights in Duluth, MN, RegionID 763862).
    "Piedmont Heights": "403427",
    # Atlanta, GA (not same-named Murphey Candler Park in Brookhaven, GA, RegionID 763163).
    "Candler Park": "269285",
}

INDEX_YEARS = list(range(2000, 2026))  # 2000..2025 -> 26 annual-January index values


def download_csv(filename: str) -> Path:
    """Download a Zillow CSV to the local cache (if not already present); return its path."""
    RAW_DIR.mkdir(exist_ok=True)
    path = RAW_DIR / filename
    if path.exists():
        return path
    print(f"  downloading {filename} ...")
    with httpx.stream("GET", f"{BASE_URL}/{filename}", timeout=180, follow_redirects=True) as resp:
        resp.raise_for_status()
        with path.open("wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return path


def load_rows_by_region(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    """Parse a ZHVI CSV; return (header, {RegionID: row})."""
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = {row[0]: row for row in reader if row}
    return header, rows


def date_columns(header: list[str]) -> list[int]:
    """Indices of the monthly-date columns (header cells like YYYY-MM-DD)."""
    return [i for i, h in enumerate(header) if len(h) >= 7 and h[:4].isdigit() and h[4] == "-"]


def trailing_12mo_mean(header: list[str], row: list[str]) -> int | None:
    """Mean of the last 12 non-empty monthly ZHVI values, rounded to a whole dollar."""
    vals = [float(row[i]) for i in date_columns(header) if i < len(row) and row[i].strip()]
    if not vals:
        return None
    last12 = vals[-12:]
    return round(sum(last12) / len(last12))


def home_price_index(header: list[str], row: list[str]) -> list[float | None] | None:
    """Annual-January ZHVI normalized to 100 at 2000, one value per INDEX_YEARS entry."""
    jan = {int(header[i][:4]): i for i in date_columns(header) if header[i][5:7] == "01"}
    if 2000 not in jan or not row[jan[2000]].strip():
        return None
    base = float(row[jan[2000]])
    index: list[float | None] = []
    for year in INDEX_YEARS:
        i = jan.get(year)
        present = i is not None and i < len(row) and row[i].strip()
        index.append(round(float(row[i]) / base * 100, 1) if present else None)
    return index


def cagr(index: list[float | None]) -> float:
    """CAGR (%) from the first to last index value over the elapsed years."""
    return round(((index[-1] / index[0]) ** (1 / (len(index) - 1)) - 1) * 100, 1)


def main() -> None:
    all_header, all_rows = load_rows_by_region(download_csv(ALL_HOMES_CSV))
    br_data = {br: load_rows_by_region(download_csv(fn)) for br, fn in BEDROOM_CSVS.items()}

    for name, rid in REGION_IDS.items():
        housing: dict = {}
        for br in (2, 3, 4):
            header, rows = br_data[br]
            row = rows.get(rid)
            value = trailing_12mo_mean(header, row) if row else None
            if value is not None:
                housing[f"median_home_value_{br}br"] = value
        index = home_price_index(all_header, all_rows[rid]) if rid in all_rows else None
        if index is not None:
            housing["home_price_index"] = index
            housing["home_price_cagr"] = cagr(index)
        print(f"{name}: {json.dumps({'housing': housing}, separators=(',', ':'))}")


if __name__ == "__main__":
    main()
