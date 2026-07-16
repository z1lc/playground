# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""Compute 2025 Atlanta neighborhood violent/property crime per 1,000 residents.

Queries APD's current Axon RMS ArcGIS layer by exact neighborhood and occurrence date. Rows are
NIBRS offenses, so qualifying rows are deduplicated by IncidentNumber within each broad class to
match APD's incident-counting convention and the runtime metric labels. A mixed violent/property
incident may contribute once to each class.
"""

import httpx

DATASET = (
    "https://services3.arcgis.com/Et5Qfajgiyosiw4d/arcgis/rest/services/"
    "OpenDataWebsite_Crime_view/FeatureServer/0/query"
)
YEAR = 2025
PAGE_SIZE = 2000

# UCR-equivalent index categories used by the other neighborhood sources in the comparison.
VIOLENT = {"Aggravated Assault", "Robbery", "Homicide", "Rape"}
PROPERTY = {"All Other Larceny", "Auto Theft", "Burglary", "Shoplifting", "Theft From Auto", "Arson"}
# APD flags these as Part I, but they are outside the cross-city UCR-equivalent index measures.
EXCLUDED_PART_I = {"Human Trafficking", "Sex Offenses"}
KNOWN_PART_I = VIOLENT | PROPERTY | EXCLUDED_PART_I

# Display name -> (exact APD NhoodName values, 2020-2024 ACS population denominator).
NEIGHBORHOODS = {
    "Virginia Highland + Morningside": (["Virginia Highland", "Morningside/Lenox Park"], 19339),
    "Sweet Auburn": (["Sweet Auburn"], 3291),
    "Cabbagetown": (["Cabbagetown"], 1851),
    "Reynoldstown": (["Reynoldstown"], 4558),
    "Inman Park": (["Inman Park"], 5412),
    "Old Fourth Ward": (["Old Fourth Ward"], 14153),
    "Piedmont Heights": (["Piedmont Heights"], 2436),
}


def arcgis_json(client: httpx.Client, params: dict[str, str]) -> dict:
    """Fetch an ArcGIS query response and surface service errors."""
    response = client.get(DATASET, params=params)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"APD ArcGIS error: {data['error']}")
    return data


def source_rows(client: httpx.Client, neighborhood: str) -> list[dict]:
    """Fetch every Part I offense row for one exact APD neighborhood in YEAR."""
    escaped = neighborhood.replace("'", "''")
    where = (
        f"OccurredFromDate >= DATE '{YEAR}-01-01' AND "
        f"OccurredFromDate < DATE '{YEAR + 1}-01-01' AND "
        f"NhoodName = '{escaped}' AND Part = 'Part I'"
    )
    expected_count = arcgis_json(client, {"where": where, "returnCountOnly": "true", "f": "json"})["count"]
    if expected_count <= 0:
        raise RuntimeError(f"No {YEAR} Part I rows returned for {neighborhood}")

    rows = []
    offset = 0
    while len(rows) < expected_count:
        data = arcgis_json(
            client,
            {
                "where": where,
                "outFields": "OBJECTID,IncidentNumber,NIBRS_Bucket,NIBRS_Offense,Part,NhoodName",
                "returnGeometry": "false",
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(PAGE_SIZE),
                "f": "json",
            },
        )
        page = [feature["attributes"] for feature in data.get("features", [])]
        if not page:
            break
        rows.extend(page)
        offset += len(page)

    if len(rows) != expected_count:
        raise RuntimeError(
            f"APD response count mismatch for {neighborhood}: expected={expected_count} got={len(rows)}"
        )
    return rows


def incident_sets(client: httpx.Client, source_names: list[str]) -> tuple[set[str], set[str], int]:
    """Return unique violent/property incident IDs and the raw Part I row count."""
    violent_incidents = set()
    property_incidents = set()
    row_count = 0

    for source_name in source_names:
        rows = source_rows(client, source_name)
        row_count += len(rows)
        for row in rows:
            incident_number = row.get("IncidentNumber")
            bucket = row.get("NIBRS_Bucket")
            if not incident_number:
                raise RuntimeError(f"Missing IncidentNumber: {row}")
            if row.get("NhoodName") != source_name or row.get("Part") != "Part I":
                raise RuntimeError(f"Unexpected APD row classification: {row}")
            if bucket not in KNOWN_PART_I:
                raise RuntimeError(f"Unexpected APD Part I bucket {bucket!r}: {row}")
            if bucket in VIOLENT:
                violent_incidents.add(incident_number)
            if bucket in PROPERTY:
                property_incidents.add(incident_number)

    return violent_incidents, property_incidents, row_count


def main() -> None:
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for name, (source_names, population) in NEIGHBORHOODS.items():
            violent, property_, rows = incident_sets(client, source_names)
            violent_per_1k = round(len(violent) / population * 1000, 1)
            property_per_1k = round(len(property_) / population * 1000, 1)
            overlap = len(violent & property_)
            print(
                f"{name}: rows={rows} violent={len(violent)} property={len(property_)} "
                f"overlap={overlap} pop={population} -> "
                f'"crime":{{"violent_per_1k":{violent_per_1k},'
                f'"property_per_1k":{property_per_1k}}}'
            )


if __name__ == "__main__":
    main()
