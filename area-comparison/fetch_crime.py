# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""Compute neighborhood violent/property crime per 1,000 residents from the Fulton County / City of
Atlanta Crime Incidents dataset (Socrata 9w3w-ynjw, sharefulton.fultoncountyga.gov), year 2021.

Filters by the dataset's exact `neighborhood` field (precise per-neighborhood, unlike NPU filtering).
Prints an inline `crime` object per neighborhood; per-1k denominators = each neighborhood's
total_population (matching the existing neighborhoods' methodology). Paste output into index.html DATA.
"""

import httpx

DATASET = "https://sharefulton.fultoncountyga.gov/resource/9w3w-ynjw.json"
YEAR = 2021
# UCR Part 1 mapping (same as the existing VH+MS entry). Rape/Arson not present in this dataset's rows.
VIOLENT = {"AGG ASSAULT", "ROBBERY", "HOMICIDE", "RAPE"}
PROPERTY = {"LARCENY-FROM VEHICLE", "LARCENY-NON VEHICLE", "AUTO THEFT", "BURGLARY"}

# display name -> (list of Socrata `neighborhood` values, population denominator)
NEIGHBORHOODS = {
    "Inman Park": (["Inman Park"], 4220),
    "Cabbagetown": (["Cabbagetown"], 1300),
    "Reynoldstown": (["Reynoldstown"], 2450),
    "Sweet Auburn": (["Sweet Auburn"], 1827),
    # Refreshed to neighborhood-level (was NPU-F + NPU-N); paired mega, summed.
    "Virginia Highland + Morningside": (["Virginia Highland", "Morningside/Lenox Park"], 16090),
}


def ucr_counts(names: list[str]) -> dict[str, int]:
    """Return {ucrliteral: count} for the given neighborhood names in YEAR."""
    quoted = ",".join("'" + n.replace("'", "''") + "'" for n in names)
    where = (
        f"neighborhood in({quoted}) AND occurdate>='{YEAR}-01-01T00:00:00' AND occurdate<'{YEAR + 1}-01-01T00:00:00'"
    )
    resp = httpx.get(
        DATASET,
        params={"$select": "ucrliteral,count(*) as n", "$where": where, "$group": "ucrliteral"},
        timeout=60,
    )
    resp.raise_for_status()
    return {row["ucrliteral"]: int(row["n"]) for row in resp.json()}


def main() -> None:
    for name, (names, pop) in NEIGHBORHOODS.items():
        counts = ucr_counts(names)
        violent = sum(n for u, n in counts.items() if u in VIOLENT)
        prop = sum(n for u, n in counts.items() if u in PROPERTY)
        v1k = round(violent / pop * 1000, 1)
        p1k = round(prop / pop * 1000, 1)
        print(
            f"{name}: violent={violent} property={prop} pop={pop} -> "
            f'"crime":{{"violent_per_1k":{v1k},"property_per_1k":{p1k}}}'
        )


if __name__ == "__main__":
    main()
