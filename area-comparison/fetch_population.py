# /// script
# dependencies = [
#   "httpx",
#   "shapely",
# ]
# ///
"""Estimate Atlanta neighborhood populations on official City boundaries.

The Census does not publish ACS estimates for City of Atlanta neighborhood polygons. This script
uses 2020 Census block population to allocate each 2020-2024 ACS block-group population estimate
to the official City neighborhood polygons. It prints the population and density objects used by
the runtime data, plus diagnostics for source verification.

Set CENSUS_API_KEY in the environment before running the script.
"""

import math
import os
from collections import defaultdict

import httpx
from shapely.geometry import Point, shape

CITY_NEIGHBORHOODS = (
    "https://gis.atlantaga.gov/dpcd/rest/services/AdministrativeArea/"
    "GeopoliticalArea/MapServer/1/query"
)
TIGER_BLOCKS = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "Tracts_Blocks/MapServer/12/query"
)
TIGER_BLOCK_GROUPS = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "Tracts_Blocks/MapServer/11/query"
)
ACS_API = "https://api.census.gov/data/2024/acs/acs5"

STATE_FIPS = "13"
# Virginia Highland and Morningside/Lenox Park cross the Fulton-DeKalb line.
COUNTY_FIPS = {"089": "DeKalb", "121": "Fulton"}
BOUNDING_BOX_BUFFER_DEGREES = 0.005

# Display name -> official City polygon names. The combined comparison column is the only pair.
NEIGHBORHOODS = {
    "Virginia Highland + Morningside": ("Virginia Highland", "Morningside/Lenox Park"),
    "Sweet Auburn": ("Sweet Auburn",),
    "Cabbagetown": ("Cabbagetown",),
    "Reynoldstown": ("Reynoldstown",),
    "Inman Park": ("Inman Park",),
    "Old Fourth Ward": ("Old Fourth Ward",),
    "Piedmont Heights": ("Piedmont Heights",),
    "Candler Park": ("Candler Park",),
}
COMPONENT_NAMES = tuple(dict.fromkeys(name for names in NEIGHBORHOODS.values() for name in names))


def arcgis_json(client: httpx.Client, url: str, params: dict[str, str]) -> dict:
    """Fetch an ArcGIS JSON response and surface service errors."""
    response = client.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error from {url}: {data['error']}")
    if data.get("exceededTransferLimit"):
        raise RuntimeError(f"ArcGIS response was truncated: {url}")
    return data


def city_polygons(client: httpx.Client) -> tuple[dict[str, object], dict[str, float]]:
    """Return official WGS84 polygons and acres for all component neighborhoods."""
    quoted = ",".join("'" + name.replace("'", "''") + "'" for name in COMPONENT_NAMES)
    response = client.get(
        CITY_NEIGHBORHOODS,
        params={
            "where": f"NAME IN ({quoted})",
            "outFields": "OBJECTID,NAME,ACRES,SQMILES,NPU",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"City GIS error: {data['error']}")

    features = data.get("features", [])
    polygons = {feature["properties"]["NAME"]: shape(feature["geometry"]) for feature in features}
    acres = {feature["properties"]["NAME"]: float(feature["properties"]["ACRES"]) for feature in features}
    expected = set(COMPONENT_NAMES)
    if set(polygons) != expected:
        raise RuntimeError(f"City polygon mismatch: expected={sorted(expected)} got={sorted(polygons)}")
    if any(value <= 0 for value in acres.values()):
        raise RuntimeError(f"Invalid City polygon acreage: {acres}")
    return polygons, acres


def census_blocks(client: httpx.Client, polygons: dict[str, object]) -> list[dict]:
    """Return 2020 Census blocks intersecting a buffered envelope around the neighborhoods."""
    minx = min(polygon.bounds[0] for polygon in polygons.values()) - BOUNDING_BOX_BUFFER_DEGREES
    miny = min(polygon.bounds[1] for polygon in polygons.values()) - BOUNDING_BOX_BUFFER_DEGREES
    maxx = max(polygon.bounds[2] for polygon in polygons.values()) + BOUNDING_BOX_BUFFER_DEGREES
    maxy = max(polygon.bounds[3] for polygon in polygons.values()) + BOUNDING_BOX_BUFFER_DEGREES
    spatial_params = {
        "geometry": f"{minx},{miny},{maxx},{maxy}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "f": "json",
    }
    expected_count = arcgis_json(
        client,
        TIGER_BLOCKS,
        {**spatial_params, "returnCountOnly": "true"},
    )["count"]
    data = arcgis_json(
        client,
        TIGER_BLOCKS,
        {
            **spatial_params,
            "outFields": "GEOID,STATE,COUNTY,TRACT,BLKGRP,POP100,INTPTLON,INTPTLAT",
            "returnGeometry": "false",
            "orderByFields": "OBJECTID",
            "resultRecordCount": str(expected_count),
        },
    )
    blocks = [feature["attributes"] for feature in data.get("features", [])]
    if not blocks:
        raise RuntimeError("No 2020 Census blocks returned")
    if len(blocks) != expected_count:
        raise RuntimeError(f"Census block response was truncated: expected={expected_count} got={len(blocks)}")
    return blocks


def classify_blocks(blocks: list[dict], polygons: dict[str, object]) -> dict[str, dict[str, float]]:
    """Sum 2020 block population by component neighborhood and block group."""
    inside: dict[str, dict[str, float]] = {name: defaultdict(float) for name in COMPONENT_NAMES}
    for block in blocks:
        if block["STATE"] != STATE_FIPS:
            continue
        point = Point(float(block["INTPTLON"]), float(block["INTPTLAT"]))
        matches = [name for name, polygon in polygons.items() if polygon.covers(point)]
        if len(matches) > 1:
            raise RuntimeError(f"Census block {block['GEOID']} matched multiple neighborhoods: {matches}")
        if matches:
            if block["COUNTY"] not in COUNTY_FIPS:
                raise RuntimeError(
                    f"Census block {block['GEOID']} in {matches[0]} has unexpected county {block['COUNTY']}"
                )
            block_group = block["GEOID"][:12]
            inside[matches[0]][block_group] += float(block["POP100"] or 0)

    for name, groups in inside.items():
        if not groups or sum(groups.values()) <= 0:
            raise RuntimeError(f"No populated 2020 Census blocks classified into {name}")
    return inside


def block_group_populations_2020(client: httpx.Client, geoids: set[str]) -> dict[str, float]:
    """Return authoritative 2020 population totals for the referenced block groups."""
    quoted = ",".join(f"'{geoid}'" for geoid in sorted(geoids))
    data = arcgis_json(
        client,
        TIGER_BLOCK_GROUPS,
        {
            "where": f"GEOID IN ({quoted})",
            "outFields": "GEOID,STATE,COUNTY,TRACT,BLKGRP,POP100",
            "returnGeometry": "false",
            "f": "json",
        },
    )
    populations = {
        feature["attributes"]["GEOID"]: float(feature["attributes"]["POP100"] or 0)
        for feature in data.get("features", [])
    }
    if set(populations) != geoids:
        missing = sorted(geoids - set(populations))
        raise RuntimeError(f"Missing 2020 block-group totals: {missing}")
    return populations


def block_group_populations_acs(
    client: httpx.Client, api_key: str, county_fips: set[str]
) -> dict[str, tuple[float, float]]:
    """Return 2020-2024 ACS estimates and margins of error for the referenced counties."""
    populations = {}
    for county in sorted(county_fips):
        response = client.get(
            ACS_API,
            params=[
                ("get", "NAME,B01003_001E,B01003_001M"),
                ("for", "block group:*"),
                ("in", f"state:{STATE_FIPS} county:{county}"),
                ("in", "tract:*"),
                ("key", api_key),
            ],
        )
        response.raise_for_status()
        rows = response.json()
        if not rows or len(rows) == 1:
            raise RuntimeError(f"No ACS block-group population rows returned for county {county}")
        header = rows[0]
        required = {"B01003_001E", "B01003_001M", "state", "county", "tract", "block group"}
        if not required.issubset(header):
            raise RuntimeError(f"Unexpected ACS response fields: {header}")
        positions = {name: header.index(name) for name in required}

        for row in rows[1:]:
            geoid = "".join(row[positions[field]] for field in ("state", "county", "tract", "block group"))
            populations[geoid] = (
                float(row[positions["B01003_001E"]]),
                float(row[positions["B01003_001M"]]),
            )
    return populations


def component_estimates(
    inside: dict[str, dict[str, float]],
    block_group_2020: dict[str, float],
    block_group_acs: dict[str, tuple[float, float]],
    acres: dict[str, float],
) -> dict[str, dict[str, float | int]]:
    """Allocate ACS block-group estimates to each official neighborhood polygon."""
    results = {}
    for name, local_groups in inside.items():
        estimate = 0.0
        moe_squared = 0.0
        for geoid, local_population_2020 in local_groups.items():
            total_population_2020 = block_group_2020[geoid]
            if total_population_2020 <= 0:
                raise RuntimeError(f"Zero 2020 population for referenced block group {geoid}")
            if geoid not in block_group_acs:
                raise RuntimeError(f"Missing ACS population for block group {geoid}")
            share = local_population_2020 / total_population_2020
            if not 0 <= share <= 1:
                raise RuntimeError(f"Invalid allocation share for {name}, {geoid}: {share}")
            acs_estimate, acs_moe = block_group_acs[geoid]
            estimate += share * acs_estimate
            moe_squared += (share * acs_moe) ** 2

        population = int(estimate + 0.5)
        results[name] = {
            "population": population,
            "population_2020": round(sum(local_groups.values())),
            "density": round(population / (acres[name] / 640), 2),
            # Diagnostic only: block-group ACS covariances are unavailable, so this is approximate.
            "moe_approx": round(math.sqrt(moe_squared)),
            "block_groups": len(local_groups),
        }
    return results


def display_estimates(
    components: dict[str, dict[str, float | int]], acres: dict[str, float]
) -> dict[str, dict[str, float | int]]:
    """Combine component results into the seven displayed comparison columns."""
    results = {}
    for display_name, component_names in NEIGHBORHOODS.items():
        population = sum(int(components[name]["population"]) for name in component_names)
        total_acres = sum(acres[name] for name in component_names)
        results[display_name] = {
            "population": population,
            "density": round(population / (total_acres / 640), 2),
            "population_2020": sum(int(components[name]["population_2020"]) for name in component_names),
            "moe_approx": round(
                math.sqrt(sum(float(components[name]["moe_approx"]) ** 2 for name in component_names))
            ),
        }
    return results


def main() -> None:
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise RuntimeError("CENSUS_API_KEY must be set; the key is never stored or printed")

    with httpx.Client(follow_redirects=True, timeout=180) as client:
        polygons, acres = city_polygons(client)
        blocks = census_blocks(client, polygons)
        inside = classify_blocks(blocks, polygons)
        geoids = {geoid for groups in inside.values() for geoid in groups}
        block_group_2020 = block_group_populations_2020(client, geoids)
        counties = {geoid[2:5] for geoid in geoids}
        block_group_acs = block_group_populations_acs(client, api_key, counties)
        components = component_estimates(inside, block_group_2020, block_group_acs, acres)
        displays = display_estimates(components, acres)

    print("Component diagnostics:")
    for name in COMPONENT_NAMES:
        result = components[name]
        print(
            f"  {name}: 2020={result['population_2020']} ACS={result['population']} "
            f"approx_moe=±{result['moe_approx']} block_groups={result['block_groups']}"
        )

    print("\nRuntime population objects:")
    for name, result in displays.items():
        print(
            f'{name}: "population":{{"total_population":{result["population"]},'
            f'"population_density_per_sq_mi":{result["density"]}}}'
        )


if __name__ == "__main__":
    main()
