# /// script
# dependencies = [
#   "httpx",
#   "pandas",
#   "lxml",
#   "beautifulsoup4",
# ]
# ///
"""Scrape Wikipedia's "List of largest mergers and acquisitions" and bucket the
deals by US presidential term. Each deal's size is expressed as a percentage of
US nominal GDP for the deal's year — that normalizes for both inflation and the
overall growth of the economy.

Outputs:
  - mergers/data.json
  - mergers/index.html (DATA block between // DATA_START and // DATA_END is
    rewritten in place if the file already exists)

Usage:
  uv run fetch_data.py            # fetch live, fall back to cached HTML
  uv run fetch_data.py --offline  # never hit the network
  uv run fetch_data.py --snapshot # also save a fresh raw HTML snapshot
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_largest_mergers_and_acquisitions"
HERE = Path(__file__).parent
RAW_HTML = HERE / "raw_html" / "wikipedia_largest_ma.html"
DATA_JSON = HERE / "data.json"
INDEX_HTML = HERE / "index.html"
TODAY = date(2026, 5, 2)

# 8 US presidential terms in scope, in chronological order. Clinton I is
# excluded because the Wikipedia source has only one US-relevant deal in that
# window (Bell Atlantic-NYNEX), making the bar misleading.
# Each term covers [start, end). Trump II is partial through TODAY.
TERMS: list[dict] = [
    {"id": "clinton-2", "label": "Clinton II", "president": "Bill Clinton",     "party": "D", "start": "1997-01-20", "end": "2001-01-20"},
    {"id": "bush-1",    "label": "Bush I",     "president": "George W. Bush",   "party": "R", "start": "2001-01-20", "end": "2005-01-20"},
    {"id": "bush-2",    "label": "Bush II",    "president": "George W. Bush",   "party": "R", "start": "2005-01-20", "end": "2009-01-20"},
    {"id": "obama-1",   "label": "Obama I",    "president": "Barack Obama",     "party": "D", "start": "2009-01-20", "end": "2013-01-20"},
    {"id": "obama-2",   "label": "Obama II",   "president": "Barack Obama",     "party": "D", "start": "2013-01-20", "end": "2017-01-20"},
    {"id": "trump-1",   "label": "Trump I",    "president": "Donald Trump",     "party": "R", "start": "2017-01-20", "end": "2021-01-20"},
    {"id": "biden",     "label": "Biden",      "president": "Joe Biden",        "party": "D", "start": "2021-01-20", "end": "2025-01-20"},
    {"id": "trump-2",   "label": "Trump II",   "president": "Donald Trump",     "party": "R", "start": "2025-01-20", "end": TODAY.isoformat(), "partial": True},
]

# In a transition year, default a deal to the *post*-inauguration term — most
# big-deal announcements happen mid-to-late year. Cases where a deal was
# actually announced before Jan 20 (typically Wikipedia is using the close year)
# are listed here as overrides.
OVERRIDES: dict[tuple[int, str, str], str] = {
    # (year, purchaser_substring, purchased_substring) -> term_id
    (2005, "Sprint", "Nextel"):                 "bush-1",   # announced 2004-12-15
    (2017, "British American Tobacco", "Reynolds"): "obama-2",  # binding offer 2017-01-17
}

# Deals to drop because neither party is a US-headquartered company. The bar
# chart is framed by US presidential terms, so a Vodafone–Mannesmann or
# Cheung-Kong–Hutchison or HM-Treasury–RBS deal is out of scope even though
# Wikipedia includes it on the same global list.
#
# Inclusion rule: at least one of acquirer or target is US-headquartered. Cases
# where one side is a global firm with major US revenues (e.g., Shire,
# SABMiller, Atlantia) but no US HQ are still excluded.
FOREIGN_ONLY_DEALS: list[tuple[int, str, str]] = [
    # (year, acquirer_substring, target_substring) — both case-insensitive substring matches
    (1995, "Mitsubishi Bank",         "Bank of Tokyo"),
    (1996, "Ciba-Geigy",              "Sandoz"),
    (1998, "Zeneca",                  "Astra"),
    (1999, "Vodafone",                "Mannesmann"),
    (1999, "TotalFina",               "Elf Aquitaine"),
    (2000, "Glaxo",                   "SmithKline"),
    (2001, "BHP Ltd",                 "Billiton"),
    (2001, "Allianz",                 "Dresdner"),
    (2003, "Olivetti",                "Telecom Italia"),
    (2004, "KBC",                     "Almanij"),
    (2004, "Royal Dutch",             "Shell Transport"),
    (2004, "Sanofi",                  "Aventis"),
    (2005, "Tokyo Mitsubishi",        "UFJ Holdings"),
    (2006, "Banca Intesa",            "Sanpaolo"),
    (2006, "América Móvil",           "América Telecom"),
    (2007, "Gaz de France",           "Suez"),
    (2007, "RFS",                     "ABN Amro"),
    (2007, "Rio Tinto",               "Alcan"),
    (2008, "Enel",                    "Endesa"),
    (2008, "Novartis",                "Alcon"),
    (2008, "HM Treasury",             "Royal Bank of Scotland"),
    (2008, "Lloyds",                  "HBOS"),
    (2010, "GDF Suez",                "International Power"),
    (2012, "Glencore",                "Xstrata"),
    (2013, "Rosneft",                 "TNK-BP"),
    (2014, "Holcim",                  "Lafarge"),
    (2015, "AB InBev",                "SABMiller"),
    (2015, "Cheung Kong",             "Hutchison"),
    (2016, "ChemChina",               "Syngenta"),
    (2017, "Essilor",                 "Luxottica"),
    (2018, "Takeda",                  "Shire"),
    (2019, "Saudi Aramco",            "SABIC"),
    (2020, "Nippon Telegraph",        "NTT Docomo"),
    (2020, "Unilever plc",            "Unilever N.V."),
    (2021, "BHP Group Limited",       "BHP Group plc"),
    (2021, "Royal Dutch Shell plc",   "Royal Dutch Shell N.V."),
    (2021, "Vonovia",                 "Deutsche Wohnen"),
    (2021, "Rogers Communications",   "Shaw Communications"),
    (2021, "Roche",                   "Novartis"),
    (2022, "HDFC Bank",               "Housing Development"),
    (2022, "Edizione",                "Atlantia"),
    (2025, "OMV",                     "Borouge"),
    (2025, "Anglo American",          "Teck Resources"),
    (2025, "Toyota Motor",            "Toyota Industries"),
]


def is_foreign_only(year: int, acquirer: str, target: str) -> bool:
    a, t = acquirer.lower(), target.lower()
    for fy, fa, ft in FOREIGN_ONLY_DEALS:
        if year == fy and fa.lower() in a and ft.lower() in t:
            return True
    return False


# Deals that are technically in Wikipedia's "largest M&A" list but aren't
# arm's-length market transactions: government bailouts, internal corporate
# restructurings between related parties, and asset/spectrum/division-only
# transfers (where there's no acquired company, just a piece of one).
NON_MARKET_DEALS: list[tuple[int, str, str, str]] = [
    # (year, acquirer_substring, target_substring, reason)
    # ----- US Treasury bailouts during the 2008 financial crisis -----
    (2008, "Department of the Treasury", "American International Group", "bailout"),
    (2008, "Department of the Treasury", "Citigroup",                    "bailout"),
    (2008, "Department of the Treasury", "Bank of America",              "bailout"),
    (2009, "Department of the Treasury", "General Motors",               "bailout"),
    # ----- Internal corporate restructurings between related entities -----
    (2013, "Verizon",                    "Vodafone Group (Remaining Verizon Wireless", "internal restructuring"),
    (2014, "Kinder Morgan",              "Kinder Morgan Energy Partners",              "internal MLP rollup"),
    (2018, "Energy Transfer Equity",     "Energy Transfer Partners",                   "internal MLP rollup"),
    (2026, "SpaceX",                     "xAI",                                        "internal Musk-companies reorg"),
    # ----- Asset/division-only deals (not a whole-company acquisition) -----
    (1999, "Bell Atlantic (Wireless",    "Vodafone Airtouch plc (US Wireless",         "asset JV (Verizon Wireless formation)"),
    (2019, "DuPont (Nutrition",          "International Flavors & Fragrances",         "division spin-merge"),
    (2019, "GlaxoSmithKline (Consumer",  "Pfizer (Consumer",                           "consumer-health JV (Haleon formation)"),
    (2025, "AT&T",                       "EchoStar (Various Wireless Spectrum",        "spectrum-license sale"),
]


def is_non_market(year: int, acquirer: str, target: str) -> str | None:
    a, t = acquirer.lower(), target.lower()
    for ny, na, nt, reason in NON_MARKET_DEALS:
        if year == ny and na.lower() in a and nt.lower() in t:
            return reason
    return None


# US nominal GDP in billions of current US dollars (BEA NIPA, annual).
# 2025 and 2026 are CBO/IMF projections (2026 is the partial-year baseline used
# for the few 2026 deals; this is fine because we're computing a ratio).
GDP_BILLIONS: dict[int, float] = {
    1993:  6859, 1994:  7287, 1995:  7640, 1996:  8073, 1997:  8578,
    1998:  9063, 1999:  9631, 2000: 10251, 2001: 10582, 2002: 10929,
    2003: 11456, 2004: 12217, 2005: 13039, 2006: 13816, 2007: 14474,
    2008: 14770, 2009: 14478, 2010: 15049, 2011: 15600, 2012: 16254,
    2013: 16843, 2014: 17551, 2015: 18206, 2016: 18695, 2017: 19477,
    2018: 20533, 2019: 21381, 2020: 21060, 2021: 23594, 2022: 26007,
    2023: 27361, 2024: 28833, 2025: 30500, 2026: 32000,
}

# Decade tables on the Wikipedia page (free-market-enterprises section).
# We exclude the state-owned-enterprises table and the failed-deals table.
DECADE_TABLE_INDICES = [11, 12, 13, 14, 16]  # 1980s, 1990s, 2000s, 2010s, 2020s


def fetch_html(offline: bool, snapshot: bool) -> str:
    if offline:
        if not RAW_HTML.exists():
            sys.exit(f"--offline given but {RAW_HTML} does not exist")
        return RAW_HTML.read_text()
    try:
        resp = httpx.get(WIKI_URL, headers={"User-Agent": "playground-mergers/1.0"}, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        if snapshot or not RAW_HTML.exists():
            RAW_HTML.parent.mkdir(parents=True, exist_ok=True)
            RAW_HTML.write_text(html)
        return html
    except httpx.HTTPError as e:
        if RAW_HTML.exists():
            print(f"warning: fetch failed ({e}); falling back to cached {RAW_HTML}", file=sys.stderr)
            return RAW_HTML.read_text()
        raise


def clean_year(v) -> int | None:
    m = re.match(r"(\d{4})", str(v))
    return int(m.group(1)) if m else None


def clean_value(v) -> float | None:
    s = re.sub(r"\[[^\]]+\]", "", str(v)).strip()
    try:
        return float(s)
    except ValueError:
        return None


def clean_text(v) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]+\]", "", str(v))).strip()


def parse_deals(html: str) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    frames = []
    for idx in DECADE_TABLE_INDICES:
        t = tables[idx].copy()
        rename = {}
        for c in t.columns:
            s = str(c).lower()
            if   "rank" in s:                                  rename[c] = "Rank"
            elif "year" in s:                                  rename[c] = "Year"
            elif "purchaser" in s:                             rename[c] = "Purchaser"
            elif "purchased" in s:                             rename[c] = "Purchased"
            elif "inflation" in s:                             rename[c] = "InflationAdj"
            elif "transaction value" in s or "asset value" in s: rename[c] = "Nominal"
        t = t.rename(columns=rename)
        frames.append(t[["Year", "Purchaser", "Purchased", "Nominal", "InflationAdj"]])
    df = pd.concat(frames, ignore_index=True)
    df["Year"] = df["Year"].apply(clean_year)
    df["Nominal"] = df["Nominal"].apply(clean_value)
    df["InflationAdj"] = df["InflationAdj"].apply(clean_value)
    df["Purchaser"] = df["Purchaser"].apply(clean_text)
    df["Purchased"] = df["Purchased"].apply(clean_text)
    df = df.dropna(subset=["Year", "InflationAdj"])
    df["Year"] = df["Year"].astype(int)
    return df


def assign_term(year: int, purchaser: str, purchased: str) -> str | None:
    # Manual overrides for transition-year edge cases.
    for (oy, op, ot), tid in OVERRIDES.items():
        if year == oy and op.lower() in purchaser.lower() and ot.lower() in purchased.lower():
            return tid
    # Default rule: a deal in year Y goes to the term that started Jan 20 of Y
    # if Y is itself a term-start year, otherwise to whichever term contains it.
    # The currently-in-progress (partial) term also catches deals from years
    # within or up to its end year.
    for term in TERMS:
        ty_start = int(term["start"][:4])
        ty_end = int(term["end"][:4])
        if ty_start <= year < ty_end:
            return term["id"]
        if year == ty_start:
            return term["id"]
        if term.get("partial") and ty_start <= year <= ty_end:
            return term["id"]
    return None


FULL_TERM_DAYS = 4 * 365 + 1  # 1461 — a 4-year US presidential term spans one leap year


def build_term_payload(df: pd.DataFrame) -> list[dict]:
    out = []
    df = df.copy()
    df["term_id"] = df.apply(lambda r: assign_term(r["Year"], r["Purchaser"], r["Purchased"]), axis=1)
    df = df[df["Nominal"].notna()].copy()
    df["pctGdp"] = df.apply(
        lambda r: round(float(r["Nominal"]) / GDP_BILLIONS[int(r["Year"])] * 100, 4),
        axis=1,
    )
    for term in TERMS:
        term_deals = df[df["term_id"] == term["id"]].copy()
        term_deals = term_deals.sort_values("pctGdp", ascending=False).head(10)
        deals = []
        for _, r in term_deals.iterrows():
            is_overridden = any(oy == r["Year"] and op.lower() in r["Purchaser"].lower() and ot.lower() in r["Purchased"].lower() for (oy, op, ot) in OVERRIDES)
            deals.append({
                "acquirer": r["Purchaser"],
                "target": r["Purchased"],
                "year": int(r["Year"]),
                "nominal": round(float(r["Nominal"]), 2),
                "gdpThatYear": GDP_BILLIONS[int(r["Year"])],
                "pctGdp": round(float(r["pctGdp"]), 4),
                "dateOverridden": is_overridden,
            })
        total_pct = round(sum(d["pctGdp"] for d in deals), 4)

        entry = {
            "id": term["id"],
            "label": term["label"],
            "president": term["president"],
            "party": term["party"],
            "start": term["start"],
            "end": term["end"],
            "partial": term.get("partial", False),
            "topDealsTotalPctGdp": total_pct,
            "deals": deals,
        }
        if term.get("partial"):
            start_date = date.fromisoformat(term["start"])
            end_date = date.fromisoformat(term["end"])
            days_elapsed = (end_date - start_date).days
            implied = round(total_pct * FULL_TERM_DAYS / days_elapsed, 4)
            entry["daysElapsed"] = days_elapsed
            entry["fullTermDays"] = FULL_TERM_DAYS
            entry["impliedFullTermPctGdp"] = implied
        out.append(entry)
    return out


def update_inline_data(payload: dict) -> bool:
    """Replace the const DATA = {...} block in index.html between the sentinels.
    Returns True if the file was found and updated, False if there is no
    index.html yet (fine on the first run)."""
    if not INDEX_HTML.exists():
        return False
    html = INDEX_HTML.read_text()
    js = "    const DATA = " + json.dumps(payload, indent=6) + ";\n"
    pattern = re.compile(r"(// DATA_START\n)(.*?)(    // DATA_END)", re.DOTALL)
    if not pattern.search(html):
        print(f"warning: {INDEX_HTML} has no DATA_START/DATA_END sentinels — skipping inline update", file=sys.stderr)
        return False
    new_html = pattern.sub(lambda m: m.group(1) + js + m.group(3), html)
    INDEX_HTML.write_text(new_html)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use cached HTML, never hit the network")
    ap.add_argument("--snapshot", action="store_true", help="save a fresh raw HTML snapshot")
    args = ap.parse_args()

    html = fetch_html(args.offline, args.snapshot)
    df = parse_deals(html)
    # Clinton II is the earliest term in scope, so we only need 1997+ data; we
    # keep 1993-1996 for visibility but the early terms are dropped from TERMS.
    print(f"parsed {len(df)} deals (1989-2026); filtering to 1993+")
    df = df[df["Year"] >= 1993]
    print(f"  -> {len(df)} deals in scope")
    before = len(df)
    df = df[~df.apply(lambda r: is_foreign_only(int(r["Year"]), r["Purchaser"], r["Purchased"]), axis=1)]
    print(f"  -> {len(df)} after dropping {before - len(df)} foreign-only deals")
    before = len(df)
    df = df[df.apply(lambda r: is_non_market(int(r["Year"]), r["Purchaser"], r["Purchased"]) is None, axis=1)]
    print(f"  -> {len(df)} after dropping {before - len(df)} non-market deals (bailouts / internal reorgs / asset-only)")

    terms_payload = build_term_payload(df)
    payload = {
        "generatedAt": TODAY.isoformat(),
        "metric": "pctGdp",
        "source": WIKI_URL,
        "notes": [
            "Top 10 US-relevant arm's-length deals per US presidential term, ranked by deal value as a percentage of US nominal GDP for the deal's year.",
            "US-relevant means at least one party (acquirer or target) is US-headquartered. Foreign-only deals (e.g., Vodafone-Mannesmann, Cheung Kong-Hutchison) are excluded.",
            "Non-market transactions are excluded: 2008 Treasury bailouts (AIG, Citigroup, BofA, GM), internal corporate reorgs (Verizon-VZ Wireless 45%, Kinder Morgan/ET MLP rollups, SpaceX-xAI Musk reorg), and asset/division-only deals (DuPont N&B-IFF, GSK/Pfizer Consumer Health Haleon JV, Bell Atlantic-Vodafone US Wireless JV, AT&T-EchoStar spectrum).",
            "GDP figures are BEA annual nominal GDP in current US dollars; 2025 and 2026 are projections.",
            "Failed/withdrawn megadeals (e.g., Pfizer-Allergan, Visa-Plaid) are excluded — only completed deals.",
            "State-owned-enterprise restructurings (e.g., Shenhua-China Guodian) are excluded.",
            "Clinton I (1993-01-20 to 1997-01-20) is omitted because Wikipedia's source list has only one US-relevant deal in that window (Bell Atlantic-NYNEX, 1996), making the bar misleading.",
            "For transition years, deals default to the post-inauguration term; manual overrides apply where Wikipedia uses close-year for a deal announced in the previous term.",
            f"Trump II is in progress; bar covers 2025-01-20 through {TODAY.isoformat()} only.",
        ],
        "terms": terms_payload,
    }
    DATA_JSON.write_text(json.dumps(payload, indent=2))
    print(f"wrote {DATA_JSON}")

    for t in terms_payload:
        suffix = ""
        if t.get("partial"):
            suffix = f"  (implied 4-yr: {t['impliedFullTermPctGdp']:.2f}% based on {t['daysElapsed']}/{t['fullTermDays']} days)"
        print(f"  {t['label']:11s} ({len(t['deals']):2d} deals)  total {t['topDealsTotalPctGdp']:.2f}% of GDP{suffix}")

    if update_inline_data(payload):
        print(f"updated DATA block in {INDEX_HTML}")


if __name__ == "__main__":
    main()
