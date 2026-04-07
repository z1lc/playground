# /// script
# dependencies = [
#   "httpx",
# ]
# ///

import json
import httpx

NRI_API = "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0/query"

FIELDS = "STCOFIPS,COUNTY,STATE,ALR_NPCTL"

# City county FIPS
CITY_FIPS: dict[str, list[str]] = {
    "San Francisco": ["06075"],
    "New York City": ["36061", "36047", "36081", "36005", "36085"],
    "Atlanta": ["13121"],
    "Seattle": ["53033"],
}

# State FIPS prefixes
STATE_FIPS: dict[str, str] = {
    "California": "06",
    "New York": "36",
    "Georgia": "13",
    "Washington": "53",
}


def query(where: str) -> list[dict]:
    resp = httpx.get(
        NRI_API,
        params={
            "where": where,
            "outFields": FIELDS,
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": "2000",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"API error: {data['error']}")
    return [f["attributes"] for f in data["features"]]


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 1)


def main():
    print("=== City-level (county) data ===\n")
    for city, fips_list in CITY_FIPS.items():
        where = "STCOFIPS IN (" + ",".join(f"'{f}'" for f in fips_list) + ")"
        rows = query(where)
        vals = [r["ALR_NPCTL"] for r in rows if r["ALR_NPCTL"] is not None]
        score = avg(vals) if len(vals) > 1 else round(vals[0], 1)
        counties = ", ".join(f"{r['COUNTY']} ({r['STCOFIPS']}): {r['ALR_NPCTL']:.1f}" for r in rows)
        print(f"{city}: {score}  [{counties}]")
        print(f'  "natural_hazards":{{"ealr_score":{score}}}')
        print()

    print("=== State-level (county average) data ===\n")
    for state, fips_prefix in STATE_FIPS.items():
        where = f"STCOFIPS LIKE '{fips_prefix}%'"
        rows = query(where)
        vals = [r["ALR_NPCTL"] for r in rows if r["ALR_NPCTL"] is not None]
        score = avg(vals)
        print(f"{state}: {score}  ({len(vals)} counties)")
        print(f'  "natural_hazards":{{"ealr_score":{score}}}')
        print()


if __name__ == "__main__":
    main()
