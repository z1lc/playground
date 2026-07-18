# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""Compute neighborhood tree-canopy % from the American Forests / USDA block-group ArcGIS service
(Census_Block_Groups_Land_Cover_and_Tree_Canopy_Analysis).

For each neighborhood, area-weight the `To_TC_Pct` field (Total Tree Canopy %) by block-group land
area (`Land_Ac`) across the census BLOCK GROUPS intersecting the neighborhood's bounding box. Block
groups (~1/3 the size of tracts) give per-neighborhood resolution for these small intown neighborhoods.
Prints an inline `parks` object per neighborhood; also lists the block groups used (for CLAUDE.md).
"""

import httpx

SVC = (
    "https://services.arcgis.com/hO5ZdGshYvEANBop/arcgis/rest/services/"
    "Census_Block_Groups_Land_Cover_and_Tree_Canopy_Analysis/FeatureServer/0/query"
)

# Tight WGS84 bounding boxes (xmin, ymin, xmax, ymax) over each neighborhood core.
NEIGHBORHOODS = {
    "Inman Park": (-84.360, 33.759, -84.351, 33.764),
    "Cabbagetown": (-84.365, 33.747, -84.360, 33.751),
    "Reynoldstown": (-84.357, 33.745, -84.350, 33.751),
    "Sweet Auburn": (-84.380, 33.753, -84.369, 33.758),
    # City of Atlanta Neighborhood layer (Old Fourth Ward, OBJECTID 201) extent.
    "Old Fourth Ward": (-84.382106, 33.751321, -84.359621, 33.773862),
    # City of Atlanta Neighborhood layer (Piedmont Heights, OBJECTID 35) extent.
    "Piedmont Heights": (-84.3776781, 33.7951677, -84.3658086, 33.8134788),
    # City of Atlanta Neighborhood layer (Candler Park, OBJECTID 20) extent; in DeKalb County.
    "Candler Park": (-84.349228, 33.759942, -84.332985, 33.771812),
}


def block_groups_in_bbox(bbox: tuple[float, float, float, float]) -> list[dict]:
    """Block groups (GEOID, To_TC_Pct, Land_Ac) intersecting the bounding box."""
    xmin, ymin, xmax, ymax = bbox
    resp = httpx.get(
        SVC,
        params={
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "GEOID,To_TC_Pct,Land_Ac",
            "returnGeometry": "false",
            "f": "json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return [f["attributes"] for f in data.get("features", [])]


def main() -> None:
    for name, bbox in NEIGHBORHOODS.items():
        bgs = block_groups_in_bbox(bbox)
        wsum = sum(a["To_TC_Pct"] * a["Land_Ac"] for a in bgs)
        asum = sum(a["Land_Ac"] for a in bgs)
        pct = round(wsum / asum, 1)
        geoids = ",".join(sorted(a["GEOID"] for a in bgs))
        print(f'{name}: bgs=[{geoids}] -> "parks":{{"tree_canopy_pct":{pct}}}')


if __name__ == "__main__":
    main()
