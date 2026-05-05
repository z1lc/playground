# /// script
# dependencies = [
#   "httpx",
#   "pandas",
#   "lxml",
#   "beautifulsoup4",
#   "html5lib",
# ]
# ///
"""Build the country-freedom comparison dataset.

Sources:
  - Freedom House Freedom in the World    -> Our World in Data CSV (score + regime)
  - EIU Democracy Index                   -> Our World in Data CSV
  - Heritage Index of Economic Freedom    -> Wikipedia (List_of_countries_by_economic_freedom)
  - Fraser Economic Freedom of the World  -> Wikipedia (Economic_Freedom_of_the_World)
  - Population & GDP                      -> World Bank API

For each country we compute compound percentile ranks: gov_pct = mean of FH+EIU
percentile ranks; econ_pct = mean of Heritage+Fraser percentile ranks. Missing
indices reduce to single-source percentiles (gov_partial / econ_partial flags).

Usage:
  uv run build_data.py            # use cache, only fetch missing
  uv run build_data.py --refresh  # force re-download all sources
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw_responses"
DATA_JSON = HERE / "data.json"
TODAY = date(2026, 5, 5)

USER_AGENT = "playground-country-freedom/1.0 (rsanek@gmail.com)"
HTTP_TIMEOUT = 60.0
MIN_COUNTRIES = 100  # sanity threshold per source

# Manual name → ISO-3 aliases for sources that publish names instead of ISO codes.
# Keep keys lowercase, stripped, no parenthetical clauses.
NAME_ALIASES = {
    "united states": "USA",
    "united states of america": "USA",
    "us": "USA",
    "usa": "USA",
    "united kingdom": "GBR",
    "uk": "GBR",
    "great britain": "GBR",
    "russia": "RUS",
    "russian federation": "RUS",
    "south korea": "KOR",
    "korea, south": "KOR",
    "korea, rep.": "KOR",
    "republic of korea": "KOR",
    "north korea": "PRK",
    "korea, north": "PRK",
    "korea, dem. people's rep.": "PRK",
    "democratic people's republic of korea": "PRK",
    "iran": "IRN",
    "iran, islamic rep.": "IRN",
    "syria": "SYR",
    "syrian arab republic": "SYR",
    "venezuela": "VEN",
    "venezuela, rb": "VEN",
    "egypt": "EGY",
    "egypt, arab rep.": "EGY",
    "yemen": "YEM",
    "yemen, rep.": "YEM",
    "vietnam": "VNM",
    "viet nam": "VNM",
    "laos": "LAO",
    "lao pdr": "LAO",
    "lao people's democratic republic": "LAO",
    "brunei": "BRN",
    "brunei darussalam": "BRN",
    "myanmar": "MMR",
    "burma": "MMR",
    "east timor": "TLS",
    "timor-leste": "TLS",
    "timor leste": "TLS",
    "czechia": "CZE",
    "czech republic": "CZE",
    "slovakia": "SVK",
    "slovak republic": "SVK",
    "moldova": "MDA",
    "republic of moldova": "MDA",
    "macedonia": "MKD",
    "north macedonia": "MKD",
    "the former yugoslav republic of macedonia": "MKD",
    "turkey": "TUR",
    "türkiye": "TUR",
    "turkiye": "TUR",
    "kyrgyz republic": "KGZ",
    "kyrgyzstan": "KGZ",
    "ivory coast": "CIV",
    "cote d'ivoire": "CIV",
    "côte d'ivoire": "CIV",
    "cape verde": "CPV",
    "cabo verde": "CPV",
    "eswatini": "SWZ",
    "swaziland": "SWZ",
    "gambia": "GMB",
    "gambia, the": "GMB",
    "the gambia": "GMB",
    "republic of the gambia": "GMB",
    "democratic republic of the congo": "COD",
    "democratic republic of congo": "COD",
    "congo, dem. rep.": "COD",
    "dr congo": "COD",
    "congo (kinshasa)": "COD",
    "republic of the congo": "COG",
    "republic of congo": "COG",
    "congo, rep.": "COG",
    "congo (brazzaville)": "COG",
    "congo": "COG",
    "tanzania": "TZA",
    "united republic of tanzania": "TZA",
    "bahamas": "BHS",
    "bahamas, the": "BHS",
    "the bahamas": "BHS",
    "saint kitts and nevis": "KNA",
    "st. kitts and nevis": "KNA",
    "st kitts and nevis": "KNA",
    "saint lucia": "LCA",
    "st. lucia": "LCA",
    "saint vincent and the grenadines": "VCT",
    "st. vincent and the grenadines": "VCT",
    "st vincent and the grenadines": "VCT",
    "trinidad and tobago": "TTO",
    "antigua and barbuda": "ATG",
    "bosnia and herzegovina": "BIH",
    "bosnia": "BIH",
    "hong kong": "HKG",
    "hong kong sar": "HKG",
    "hong kong sar, china": "HKG",
    "hong kong (china)": "HKG",
    "macau": "MAC",
    "macao": "MAC",
    "macao sar, china": "MAC",
    "taiwan": "TWN",
    "taiwan, china": "TWN",
    "republic of china": "TWN",
    "palestine": "PSE",
    "west bank and gaza": "PSE",
    "occupied palestinian territory": "PSE",
    "palestinian authority": "PSE",
    "kosovo": "XKX",
    "central african republic": "CAF",
    "dominican republic": "DOM",
    "equatorial guinea": "GNQ",
    "guinea-bissau": "GNB",
    "papua new guinea": "PNG",
    "sao tome and principe": "STP",
    "são tomé and príncipe": "STP",
    "solomon islands": "SLB",
    "marshall islands": "MHL",
    "sri lanka": "LKA",
    "saudi arabia": "SAU",
    "south sudan": "SSD",
    "south africa": "ZAF",
    "sierra leone": "SLE",
    "burkina faso": "BFA",
    "el salvador": "SLV",
    "costa rica": "CRI",
    "puerto rico": "PRI",
    "new zealand": "NZL",
    "new caledonia": "NCL",
    "united arab emirates": "ARE",
    "uae": "ARE",
    "uzbekistan": "UZB",
    "kazakhstan": "KAZ",
    "tajikistan": "TJK",
    "turkmenistan": "TKM",
    "azerbaijan": "AZE",
    "belarus": "BLR",
    "mauritius": "MUS",
    "madagascar": "MDG",
    "mozambique": "MOZ",
    "mauritania": "MRT",
    "burundi": "BDI",
    "djibouti": "DJI",
    "rwanda": "RWA",
    "comoros": "COM",
    "lesotho": "LSO",
    "botswana": "BWA",
    "namibia": "NAM",
    "zimbabwe": "ZWE",
    "zambia": "ZMB",
    "malawi": "MWI",
    "ethiopia": "ETH",
    "eritrea": "ERI",
    "somalia": "SOM",
    "sudan": "SDN",
    "libya": "LBY",
    "tunisia": "TUN",
    "morocco": "MAR",
    "algeria": "DZA",
    "nigeria": "NGA",
    "ghana": "GHA",
    "togo": "TGO",
    "benin": "BEN",
    "niger": "NER",
    "chad": "TCD",
    "cameroon": "CMR",
    "gabon": "GAB",
    "guinea": "GIN",
    "kenya": "KEN",
    "uganda": "UGA",
    "senegal": "SEN",
    "mali": "MLI",
    "liberia": "LBR",
    "afghanistan": "AFG",
    "bangladesh": "BGD",
    "bhutan": "BTN",
    "cambodia": "KHM",
    "fiji": "FJI",
    "india": "IND",
    "indonesia": "IDN",
    "malaysia": "MYS",
    "maldives": "MDV",
    "mongolia": "MNG",
    "nepal": "NPL",
    "pakistan": "PAK",
    "philippines": "PHL",
    "singapore": "SGP",
    "thailand": "THA",
    "japan": "JPN",
    "china": "CHN",
    "australia": "AUS",
    "albania": "ALB",
    "armenia": "ARM",
    "austria": "AUT",
    "belgium": "BEL",
    "bulgaria": "BGR",
    "croatia": "HRV",
    "cyprus": "CYP",
    "denmark": "DNK",
    "estonia": "EST",
    "finland": "FIN",
    "france": "FRA",
    "georgia": "GEO",
    "germany": "DEU",
    "greece": "GRC",
    "hungary": "HUN",
    "iceland": "ISL",
    "ireland": "IRL",
    "israel": "ISR",
    "italy": "ITA",
    "jordan": "JOR",
    "kuwait": "KWT",
    "latvia": "LVA",
    "lebanon": "LBN",
    "liechtenstein": "LIE",
    "lithuania": "LTU",
    "luxembourg": "LUX",
    "malta": "MLT",
    "monaco": "MCO",
    "montenegro": "MNE",
    "netherlands": "NLD",
    "norway": "NOR",
    "oman": "OMN",
    "poland": "POL",
    "portugal": "PRT",
    "qatar": "QAT",
    "romania": "ROU",
    "san marino": "SMR",
    "serbia": "SRB",
    "slovenia": "SVN",
    "spain": "ESP",
    "sweden": "SWE",
    "switzerland": "CHE",
    "ukraine": "UKR",
    "andorra": "AND",
    "argentina": "ARG",
    "barbados": "BRB",
    "belize": "BLZ",
    "bolivia": "BOL",
    "brazil": "BRA",
    "canada": "CAN",
    "chile": "CHL",
    "colombia": "COL",
    "cuba": "CUB",
    "dominica": "DMA",
    "ecuador": "ECU",
    "grenada": "GRD",
    "guatemala": "GTM",
    "guyana": "GUY",
    "haiti": "HTI",
    "honduras": "HND",
    "iraq": "IRQ",
    "jamaica": "JAM",
    "mexico": "MEX",
    "nicaragua": "NIC",
    "panama": "PAN",
    "paraguay": "PRY",
    "peru": "PER",
    "samoa": "WSM",
    "seychelles": "SYC",
    "suriname": "SUR",
    "tonga": "TON",
    "tuvalu": "TUV",
    "uruguay": "URY",
    "vanuatu": "VUT",
    "kiribati": "KIR",
    "nauru": "NRU",
    "palau": "PLW",
    "micronesia": "FSM",
    "micronesia, fed. sts.": "FSM",
    "federated states of micronesia": "FSM",
    "angola": "AGO",
    "bahrain": "BHR",
    "kingdom of bahrain": "BHR",
}

# Friendly display names — overrides WB master where it uses awkward formal names.
DISPLAY_NAMES = {
    "PRK": "North Korea",
    "KOR": "South Korea",
    "SYR": "Syria",
    "HKG": "Hong Kong",
    "MAC": "Macau",
    "COD": "DR Congo",
    "COG": "Republic of the Congo",
    "EGY": "Egypt",
    "IRN": "Iran",
    "VEN": "Venezuela",
    "YEM": "Yemen",
    "LAO": "Laos",
    "RUS": "Russia",
    "GMB": "The Gambia",
    "BHS": "The Bahamas",
    "FSM": "Micronesia",
    "BRN": "Brunei",
    "PSE": "Palestine",
    "TWN": "Taiwan",
    "VNM": "Vietnam",
    "SVK": "Slovakia",
    "MDA": "Moldova",
    "KGZ": "Kyrgyzstan",
    "USA": "United States",
    "GBR": "United Kingdom",
    "ARE": "United Arab Emirates",
    "TZA": "Tanzania",
    "STP": "São Tomé and Príncipe",
    "CPV": "Cabo Verde",
    "CIV": "Côte d'Ivoire",
    "TUR": "Türkiye",
    "SOM": "Somalia",
    "ESH": "Western Sahara",
    "PRI": "Puerto Rico",
}

# Hardcoded population/GDP for jurisdictions World Bank doesn't cover.
# Refresh annually from authoritative sources.
EXTRA_DEMOGRAPHICS = {
    # Taiwan: WB excludes per UN/PRC policy. Population from DGBAS year-end 2024
    # (stat.gov.tw); GDP from IMF World Economic Outlook 2024.
    "TWN": {"population": 23420000, "gdp_usd": 782440000000, "year": 2024},
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Lowercase, trim, strip parenthetical clauses, normalize whitespace."""
    if not isinstance(name, str):
        return ""
    s = name.strip().lower()
    # Strip wikipedia footnote markers like [a], [1]
    s = re.sub(r"\[[^\]]*\]", "", s)
    # Strip parenthetical clauses
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Strip trailing punctuation
    s = s.strip(".,*†‡§¶")
    return s


def name_to_iso3(name: str) -> str | None:
    """Map a country name to ISO-3 using NAME_ALIASES."""
    norm = normalize_name(name)
    if not norm:
        return None
    return NAME_ALIASES.get(norm)


def http_get(url: str, *, cache: Path, refresh: bool, binary: bool = False, accept: str | None = None) -> bytes:
    """GET with disk caching."""
    if cache.exists() and not refresh:
        return cache.read_bytes()
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    with httpx.Client(headers=headers, timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(r.content)
        return r.content


# -----------------------------------------------------------------------------
# Fetchers
# -----------------------------------------------------------------------------

def fetch_freedom_house(refresh: bool) -> tuple[pd.DataFrame, int]:
    """OWID's freedom-score-fh CSV. Returns (df[iso3, score, label], year)."""
    url = "https://ourworldindata.org/grapher/freedom-score-fh.csv?v=1&csvType=full&useColumnShortNames=true"
    raw = http_get(url, cache=RAW / "fh.csv", refresh=refresh)
    df = pd.read_csv(pd.io.common.BytesIO(raw))
    # Keep only ISO-3 entries (drop OWID_* and unknown)
    df = df[df["code"].str.match(r"^[A-Z]{3}$", na=False)]
    # Latest year per country
    df = df.sort_values("year").groupby("code", as_index=False).last()
    df = df[["code", "entity", "year", "total_score"]].rename(columns={
        "code": "iso3", "entity": "name", "total_score": "score"
    })
    df = df.dropna(subset=["score"])
    # FH-published mapping (Total Score 0-100 -> Status):
    #   Free: 70-100, Partly Free: 40-69, Not Free: 0-39
    # These map closely to PR+CL average cutoffs in practice.
    def label(s: float) -> str:
        if s >= 70: return "Free"
        if s >= 40: return "Partly Free"
        return "Not Free"
    df["label"] = df["score"].apply(label)
    year = int(df["year"].max())
    return df[["iso3", "score", "label"]], year


def fetch_eiu(refresh: bool) -> tuple[pd.DataFrame, int]:
    """OWID's democracy-index-eiu CSV. Returns (df[iso3, score, label], year)."""
    url = "https://ourworldindata.org/grapher/democracy-index-eiu.csv?v=1&csvType=full&useColumnShortNames=true"
    raw = http_get(url, cache=RAW / "eiu.csv", refresh=refresh)
    df = pd.read_csv(pd.io.common.BytesIO(raw))
    df = df[df["code"].str.match(r"^[A-Z]{3}$", na=False)]
    df = df.sort_values("year").groupby("code", as_index=False).last()
    df = df[["code", "year", "democracy_eiu"]].rename(columns={
        "code": "iso3", "democracy_eiu": "score"
    })
    df = df.dropna(subset=["score"])
    # EIU-published cutoffs:
    #   Full democracy >8.0, Flawed democracy 6-8, Hybrid 4-6, Authoritarian <=4
    def label(s: float) -> str:
        if s > 8.0: return "Full democracy"
        if s > 6.0: return "Flawed democracy"
        if s > 4.0: return "Hybrid regime"
        return "Authoritarian"
    df["label"] = df["score"].apply(label)
    year = int(df["year"].max())
    return df[["iso3", "score", "label"]], year


def _parse_wiki_table(html: bytes, table_index: int, country_col: str, score_col: str) -> pd.DataFrame:
    """Parse a Wikipedia page's nth wikitable, extracting country names and scores."""
    tables = pd.read_html(io.BytesIO(html), flavor="bs4")
    if table_index >= len(tables):
        raise ValueError(f"only {len(tables)} tables in page, requested index {table_index}")
    df = tables[table_index].copy()
    # Flatten multi-level columns if any
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(c) for c in col if c and str(c) != "nan").strip() for col in df.columns]
    # Find the columns by case-insensitive substring match
    def find_col(target: str) -> str | None:
        for c in df.columns:
            if target.lower() in str(c).lower():
                return c
        return None
    name_col = find_col(country_col)
    val_col = find_col(score_col)
    if not name_col or not val_col:
        raise ValueError(f"couldn't find columns {country_col!r}/{score_col!r} in {list(df.columns)}")
    df = df[[name_col, val_col]].copy()
    df.columns = ["name", "score"]
    # Coerce score to float (wikipedia tables can have refs/footnotes inline)
    df["score"] = (
        df["score"]
        .astype(str)
        .str.replace(r"\[[^\]]*\]", "", regex=True)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", pd.NA)
        .astype("Float64")
    )
    df = df.dropna(subset=["score"])
    df["name"] = df["name"].astype(str).str.replace(r"\[[^\]]*\]", "", regex=True).str.strip()
    return df


def fetch_heritage(refresh: bool) -> tuple[pd.DataFrame, int]:
    """Wikipedia: List_of_countries_by_economic_freedom — 2026 table."""
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_economic_freedom"
    raw = http_get(url, cache=RAW / "heritage_wiki.html", refresh=refresh, accept="text/html")
    # Inspect to find the right table — the 2026 caption is on Table 1 typically
    tables = pd.read_html(io.BytesIO(raw), flavor="bs4", match="Country")
    chosen = None
    chosen_year = 2026
    # Prefer the most recent year. Read raw HTML to find captions.
    html = raw.decode("utf-8", errors="replace")
    # Find caption-year for each table-with-Country
    captions = re.findall(r"<caption[^>]*>([^<]*)</caption>", html)
    # Heuristic: pick the table whose caption mentions a 4-digit year and is largest
    best_year = 0
    for i, t in enumerate(tables):
        cols = [str(c).lower() for c in t.columns]
        if not any("country" in c for c in cols) or not any("score" in c for c in cols):
            continue
        # Try to associate a year — fall back to checking the table content
        if i < len(captions):
            m = re.search(r"\b(20\d\d)\b", captions[i])
            year = int(m.group(1)) if m else 0
        else:
            year = 0
        if year > best_year:
            best_year = year
            chosen = t
    if chosen is None:
        # Fallback: use _parse_wiki_table heuristically
        df = _parse_wiki_table(raw, 1, "country", "score")
        chosen_year = 2026
    else:
        df = chosen.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [" ".join(str(c) for c in col if c and str(c) != "nan").strip() for col in df.columns]
        name_col = next(c for c in df.columns if "country" in str(c).lower())
        score_col = next(c for c in df.columns if "score" in str(c).lower())
        df = df[[name_col, score_col]].copy()
        df.columns = ["name", "score"]
        df["score"] = (
            df["score"].astype(str)
            .str.replace(r"\[[^\]]*\]", "", regex=True)
            .str.replace(r"[^0-9.\-]", "", regex=True)
            .replace("", pd.NA)
            .astype("Float64")
        )
        df["name"] = df["name"].astype(str).str.replace(r"\[[^\]]*\]", "", regex=True).str.strip()
        df = df.dropna(subset=["score"])
        chosen_year = best_year or 2026
    df["iso3"] = df["name"].apply(name_to_iso3)
    missing = df[df["iso3"].isna()]["name"].tolist()
    if missing:
        print(f"  [heritage] {len(missing)} unmapped names: {missing[:8]}", file=sys.stderr)
    df = df.dropna(subset=["iso3"])
    # Heritage-published cutoffs: 80-100 Free, 70-79.9 Mostly Free, 60-69.9 Moderately,
    # 50-59.9 Mostly Unfree, 0-49.9 Repressed.
    def label(s: float) -> str:
        if s >= 80: return "Free"
        if s >= 70: return "Mostly Free"
        if s >= 60: return "Moderately Free"
        if s >= 50: return "Mostly Unfree"
        return "Repressed"
    df["score"] = df["score"].astype(float)
    df["label"] = df["score"].apply(label)
    return df[["iso3", "score", "label"]], chosen_year


def fetch_fraser(refresh: bool) -> tuple[pd.DataFrame, int]:
    """Wikipedia: Economic_Freedom_of_the_World — most recent EFW table."""
    url = "https://en.wikipedia.org/wiki/Economic_Freedom_of_the_World"
    raw = http_get(url, cache=RAW / "fraser_wiki.html", refresh=refresh, accept="text/html")
    tables = pd.read_html(io.BytesIO(raw), flavor="bs4")
    # Find a table with columns containing "Country" + ("Summary" or "Index" or "EFW")
    chosen = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if any("country" in c for c in cols) and any(
            "summary" in c or "score" in c or "efw" in c or "index" in c for c in cols
        ):
            # Reasonable candidate — pick the largest one
            if chosen is None or len(t) > len(chosen):
                chosen = t
    if chosen is None:
        raise RuntimeError("no Fraser EFW table found on Wikipedia")
    df = chosen.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(str(c) for c in col if c and str(c) != "nan").strip() for col in df.columns]
    name_col = next(c for c in df.columns if "country" in str(c).lower())
    score_col = next(
        (c for c in df.columns if "summary" in str(c).lower() or "efw" in str(c).lower() or "index" in str(c).lower()),
        None,
    )
    if not score_col:
        score_col = next(c for c in df.columns if "score" in str(c).lower())
    df = df[[name_col, score_col]].copy()
    df.columns = ["name", "score"]
    df["score"] = (
        df["score"].astype(str)
        .str.replace(r"\[[^\]]*\]", "", regex=True)
        .str.replace(r"[^0-9.\-]", "", regex=True)
        .replace("", pd.NA)
        .astype("Float64")
    )
    df["name"] = df["name"].astype(str).str.replace(r"\[[^\]]*\]", "", regex=True).str.strip()
    df = df.dropna(subset=["score"])
    df["score"] = df["score"].astype(float)
    df["iso3"] = df["name"].apply(name_to_iso3)
    missing = df[df["iso3"].isna()]["name"].tolist()
    if missing:
        print(f"  [fraser] {len(missing)} unmapped names: {missing[:8]}", file=sys.stderr)
    df = df.dropna(subset=["iso3"])
    # Fraser doesn't publish canonical labels — assign quartile labels by rank.
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    n = len(df)
    def quartile(idx: int) -> str:
        # idx is rank from top (0-based)
        if idx < n / 4: return "1st quartile"
        if idx < n / 2: return "2nd quartile"
        if idx < 3 * n / 4: return "3rd quartile"
        return "4th quartile"
    df["label"] = [quartile(i) for i in range(n)]
    # Fraser EFW year is the data year, lagging the report year. Use 2023 as
    # canonical (report 2025 reflects 2023 data).
    return df[["iso3", "score", "label"]], 2023


def fetch_worldbank_indicator(indicator: str, slug: str, refresh: bool) -> tuple[pd.DataFrame, int]:
    """Fetch a World Bank indicator — latest non-null value per country."""
    url = (
        f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
        f"?format=json&per_page=20000&date=2018:2025"
    )
    raw = http_get(url, cache=RAW / f"wb_{slug}.json", refresh=refresh, accept="application/json")
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        raise RuntimeError(f"World Bank returned no data for {indicator}")
    rows = data[1]
    df = pd.DataFrame(rows)
    df["iso3"] = df["countryiso3code"]
    df["year"] = df["date"].astype(int)
    df = df.dropna(subset=["value"])
    df = df[df["iso3"].str.match(r"^[A-Z]{3}$", na=False)]
    # Take latest year with a value per country
    df = df.sort_values("year").groupby("iso3", as_index=False).last()
    year = int(df["year"].max())
    return df[["iso3", "year", "value"]], year


def fetch_wb_population(refresh: bool):
    df, year = fetch_worldbank_indicator("SP.POP.TOTL", "pop", refresh)
    df = df.rename(columns={"value": "population"})
    df["population"] = df["population"].astype("Int64")
    return df[["iso3", "population"]], year


def fetch_wb_gdp(refresh: bool):
    df, year = fetch_worldbank_indicator("NY.GDP.MKTP.CD", "gdp", refresh)
    df = df.rename(columns={"value": "gdp_usd"})
    df["gdp_usd"] = df["gdp_usd"].astype(float)
    return df[["iso3", "gdp_usd"]], year


def fetch_country_master(refresh: bool) -> pd.DataFrame:
    """Get country names + ISO-2 codes from World Bank country list."""
    url = "https://api.worldbank.org/v2/country?format=json&per_page=400"
    raw = http_get(url, cache=RAW / "wb_countries.json", refresh=refresh, accept="application/json")
    data = json.loads(raw)
    rows = data[1] if isinstance(data, list) and len(data) > 1 else []
    out = []
    for c in rows:
        iso3 = c.get("id")
        iso2 = c.get("iso2Code")
        name = c.get("name")
        region = (c.get("region") or {}).get("value") or ""
        # Skip aggregates (region == "Aggregates")
        if region == "Aggregates":
            continue
        if not iso3 or not iso2 or not name:
            continue
        if not re.match(r"^[A-Z]{3}$", iso3) or not re.match(r"^[A-Z]{2}$", iso2):
            continue
        out.append({"iso3": iso3, "iso2": iso2, "name": name})
    return pd.DataFrame(out)


# -----------------------------------------------------------------------------
# Percentile + assembly
# -----------------------------------------------------------------------------

def percentile_ranks(scores: pd.Series) -> pd.Series:
    """Average-rank percentile (0-100). Higher score = higher percentile."""
    # rank with method='average' resolves ties.
    ranks = scores.rank(method="average", ascending=True)
    n = scores.notna().sum()
    return (ranks - 0.5) / n * 100.0


def compute_band_cutoffs(score_to_label, all_scores: list[float]) -> list[dict]:
    """For label boundaries, find percentile of each band's max score.

    Returns ordered list `[{label, max_pct}, ...]` from lowest band to highest.
    """
    if not all_scores:
        return []
    s = pd.Series(all_scores).dropna().astype(float)
    if s.empty:
        return []
    # Find unique labels in the order they appear by score
    items = []
    for v in sorted(s.unique()):
        items.append((v, score_to_label(v)))
    # Group consecutive same-labels; record the max score per label
    bands = []
    cur_label = None
    cur_max = None
    for v, lbl in items:
        if cur_label is None:
            cur_label, cur_max = lbl, v
        elif lbl == cur_label:
            cur_max = v
        else:
            bands.append((cur_label, cur_max))
            cur_label, cur_max = lbl, v
    bands.append((cur_label, cur_max))
    # Compute percentile for each max score
    out = []
    n = len(s)
    sorted_s = s.sort_values().reset_index(drop=True)
    for label, mx in bands:
        # Percentile = fraction of values <= mx
        pct = ((sorted_s <= mx).sum() / n) * 100.0
        out.append({"label": label, "max_pct": round(pct, 2)})
    return out


def merge_all(fh, eiu, heritage, fraser, pop, gdp, master):
    """Outer-join all sources on iso3, computing percentiles."""
    base = master.set_index("iso3")[["iso2", "name"]]
    # Per-source scores
    fh_s = fh.set_index("iso3").rename(columns=lambda c: f"fh_{c}")
    eiu_s = eiu.set_index("iso3").rename(columns=lambda c: f"eiu_{c}")
    heritage_s = heritage.set_index("iso3").rename(columns=lambda c: f"heritage_{c}")
    fraser_s = fraser.set_index("iso3").rename(columns=lambda c: f"fraser_{c}")
    pop_s = pop.set_index("iso3")
    gdp_s = gdp.set_index("iso3")

    # Outer-join all scores so any country in any source is included
    union_idx = (
        fh_s.index.union(eiu_s.index)
        .union(heritage_s.index)
        .union(fraser_s.index)
    )
    df = pd.DataFrame(index=union_idx)
    for src in (fh_s, eiu_s, heritage_s, fraser_s, pop_s, gdp_s, base):
        df = df.join(src, how="left")

    # Drop rows missing both gov sources AND both econ sources entirely
    has_any = (
        df["fh_score"].notna() | df["eiu_score"].notna()
        | df["heritage_score"].notna() | df["fraser_score"].notna()
    )
    df = df[has_any].copy()

    # Fill population/GDP for jurisdictions WB doesn't cover (e.g. Taiwan).
    for iso3, extra in EXTRA_DEMOGRAPHICS.items():
        if iso3 in df.index:
            if pd.isna(df.at[iso3, "population"]):
                df.at[iso3, "population"] = extra["population"]
            if pd.isna(df.at[iso3, "gdp_usd"]):
                df.at[iso3, "gdp_usd"] = extra["gdp_usd"]

    # If a country has scores but no master row (e.g. Taiwan, Kosovo), fill name from sources.
    # Apply DISPLAY_NAMES overrides for friendlier labels than WB's formal names.
    df["name"] = df["name"].fillna(df.index.to_series())  # iso3 placeholder
    df["name"] = df.index.to_series().map(DISPLAY_NAMES).fillna(df["name"])
    # Derive iso2 from iso3 for entries missing it (Taiwan, Kosovo, etc.)
    ISO3_TO_ISO2 = {"TWN": "TW", "XKX": "XK", "PSE": "PS", "ESH": "EH"}
    df["iso2"] = df["iso2"].fillna(df.index.to_series().map(ISO3_TO_ISO2)).fillna("")

    # Percentile ranks per index
    df["fh_pct"] = percentile_ranks(df["fh_score"])
    df["eiu_pct"] = percentile_ranks(df["eiu_score"])
    df["heritage_pct"] = percentile_ranks(df["heritage_score"])
    df["fraser_pct"] = percentile_ranks(df["fraser_score"])

    # Compound government / economy percentiles
    gov_cols = ["fh_pct", "eiu_pct"]
    econ_cols = ["heritage_pct", "fraser_pct"]
    df["gov_pct"] = df[gov_cols].mean(axis=1, skipna=True)
    df["econ_pct"] = df[econ_cols].mean(axis=1, skipna=True)
    df["gov_partial"] = df[gov_cols].notna().sum(axis=1) < 2
    df["econ_partial"] = df[econ_cols].notna().sum(axis=1) < 2

    return df.reset_index().rename(columns={"index": "iso3"})


def build_payload(merged: pd.DataFrame, years: dict, bands: dict) -> dict:
    countries = []
    for _, r in merged.iterrows():
        c = {
            "iso2": r.get("iso2") or "",
            "iso3": r["iso3"],
            "name": r["name"],
        }
        if pd.notna(r.get("population")):
            c["population"] = int(r["population"])
        else:
            c["population"] = None
        if pd.notna(r.get("gdp_usd")):
            c["gdp_usd"] = float(r["gdp_usd"])
        else:
            c["gdp_usd"] = None
        for src, prefix in (("fh", "fh"), ("eiu", "eiu"), ("heritage", "heritage"), ("fraser", "fraser")):
            score = r.get(f"{prefix}_score")
            label = r.get(f"{prefix}_label")
            if pd.notna(score):
                c[src] = {"score": round(float(score), 2), "label": str(label) if pd.notna(label) else None}
            else:
                c[src] = None
        c["gov_pct"] = round(float(r["gov_pct"]), 2) if pd.notna(r["gov_pct"]) else None
        c["econ_pct"] = round(float(r["econ_pct"]), 2) if pd.notna(r["econ_pct"]) else None
        c["gov_partial"] = bool(r["gov_partial"])
        c["econ_partial"] = bool(r["econ_partial"])
        countries.append(c)
    # Sort by gov_pct desc, then econ_pct desc, putting Nones last
    countries.sort(key=lambda c: (c["gov_pct"] is None, -(c["gov_pct"] or 0), -(c["econ_pct"] or 0)))
    return {
        "meta": {
            **years,
            "built_at": TODAY.isoformat(),
            "gov_bands": bands["gov"],
            "econ_bands": bands["econ"],
            "n_countries": len(countries),
        },
        "countries": countries,
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="force re-download all sources")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    print("Stage 1: country master")
    master = fetch_country_master(args.refresh)
    print(f"  WB master: {len(master)} countries")

    sources = {}
    print("Stage 2: indices")
    for name, fn in [
        ("fh", fetch_freedom_house),
        ("eiu", fetch_eiu),
        ("heritage", fetch_heritage),
        ("fraser", fetch_fraser),
    ]:
        try:
            df, year = fn(args.refresh)
            print(f"  [{name}] {len(df)} countries, vintage {year}")
            if len(df) < MIN_COUNTRIES:
                print(f"  [{name}] WARNING: only {len(df)} countries (< {MIN_COUNTRIES})", file=sys.stderr)
            sources[name] = (df, year)
        except Exception as e:
            print(f"  [{name}] FAILED: {e}", file=sys.stderr)
            sources[name] = (pd.DataFrame(columns=["iso3", "score", "label"]), None)

    print("Stage 3: World Bank pop + GDP")
    pop, pop_year = fetch_wb_population(args.refresh)
    print(f"  pop: {len(pop)} countries, vintage {pop_year}")
    gdp, gdp_year = fetch_wb_gdp(args.refresh)
    print(f"  gdp: {len(gdp)} countries, vintage {gdp_year}")

    print("Stage 4: merge + percentiles")
    merged = merge_all(
        sources["fh"][0], sources["eiu"][0],
        sources["heritage"][0], sources["fraser"][0],
        pop, gdp, master,
    )
    print(f"  merged: {len(merged)} countries")

    # Compute band cutoffs as percentiles
    def fh_label(s):
        if s >= 70: return "Free"
        if s >= 40: return "Partly Free"
        return "Not Free"
    def eiu_label(s):
        if s > 8.0: return "Full democracy"
        if s > 6.0: return "Flawed democracy"
        if s > 4.0: return "Hybrid regime"
        return "Authoritarian"
    def heritage_label(s):
        if s >= 80: return "Free"
        if s >= 70: return "Mostly Free"
        if s >= 60: return "Moderately Free"
        if s >= 50: return "Mostly Unfree"
        return "Repressed"

    bands = {
        "gov": {
            "fh": compute_band_cutoffs(fh_label, sources["fh"][0]["score"].tolist()),
            "eiu": compute_band_cutoffs(eiu_label, sources["eiu"][0]["score"].tolist()),
        },
        "econ": {
            "heritage": compute_band_cutoffs(heritage_label, sources["heritage"][0]["score"].tolist()),
            # Fraser is quartiles by definition: 25/50/75/100
            "fraser": [
                {"label": "4th quartile", "max_pct": 25.0},
                {"label": "3rd quartile", "max_pct": 50.0},
                {"label": "2nd quartile", "max_pct": 75.0},
                {"label": "1st quartile", "max_pct": 100.0},
            ],
        },
    }

    years = {
        "fh_year": sources["fh"][1],
        "eiu_year": sources["eiu"][1],
        "heritage_year": sources["heritage"][1],
        "fraser_year": sources["fraser"][1],
        "pop_year": pop_year,
        "gdp_year": gdp_year,
    }

    print("Stage 5: write data.json + inline into index.html")
    payload = build_payload(merged, years, bands)
    DATA_JSON.write_text(json.dumps(payload, separators=(",", ":")))
    size_kb = DATA_JSON.stat().st_size / 1024
    print(f"  wrote {DATA_JSON} ({size_kb:.1f} KB, {payload['meta']['n_countries']} countries)")

    index_html = HERE / "index.html"
    if index_html.exists():
        html_text = index_html.read_text()
        js = "    const DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n"
        pattern = re.compile(r"(// DATA_START\n)(.*?)(    // DATA_END)", re.DOTALL)
        if pattern.search(html_text):
            new_html = pattern.sub(lambda m: m.group(1) + js + m.group(3), html_text)
            index_html.write_text(new_html)
            print(f"  inlined DATA into {index_html}")
        else:
            print(f"  WARNING: no DATA_START/DATA_END sentinels in {index_html}; skipping inline", file=sys.stderr)

    # Sanity ping
    sample = [c for c in payload["countries"] if c["name"] in ("Norway", "United States", "China", "Singapore", "North Korea")]
    print("Sample:")
    for c in sample:
        print(f"  {c['name']:20s}  gov={c['gov_pct']}  econ={c['econ_pct']}")


if __name__ == "__main__":
    main()
