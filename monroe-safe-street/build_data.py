# /// script
# dependencies = [
#   "requests",
# ]
# ///
"""Build data.json for the Monroe Dr Safe Streets map tool.

Fetches the real Monroe Drive NE corridor geometry from the OpenStreetMap
Overpass API and resolves each PDF-described feature to a real coordinate by
looking up its intersection with Monroe Dr (Overpass shared-node), falling back
to Nominatim, then to a manual override. All PDF-derived semantics (titles,
descriptions, source quotes) live in FEATURES below; coordinates are fetched.

Source: "Monroe Drive Safe Streets Project Meeting - April 14, 2026" Q&A
(City of Atlanta DOT). Project page: https://atldot.atlantaga.gov/projects/monroe-dr-safe-street
"""

import json
import time
from pathlib import Path
from typing import Optional

import requests

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "playground-monroe-safe-street/1.0 (rsanek@gmail.com)"}

# Corridor bounding box (S, W, N, E) around Monroe Dr NE, Atlanta.
BBOX = (33.770, -84.375, 33.815, -84.355)
MONROE_NAME_RE = "^Monroe Drive"

OUT_PATH = Path(__file__).with_name("data.json")

# Each feature: PDF-derived semantics. `cross` = OSM cross-street to intersect
# with Monroe Dr; `nominatim` = free-text landmark query; `manual` = [lat, lng]
# fallback. Resolution order: cross-street intersection -> nominatim -> manual.
FEATURES = [
    # --- Full traffic signals (upgraded) -- Section 8 ---
    {
        "id": "sig-virginia",
        "type": "signal",
        "name": "Virginia Ave",
        "phase": "II",
        "title": "Full traffic signal — Virginia Ave",
        "cross": "Virginia Avenue",
        "description": "Upgraded full traffic signal. Phase II intersection improvement; right-of-way acquisition here.",
        "section": 8,
        "quote": "Full traffic signals are located at: Virginia Ave, Amsterdam Ave, Worchester Dr, Dutch Valley Rd, Ansley Mall Driveway, and Montgomery Ferry Dr.",
    },
    {
        "id": "sig-amsterdam",
        "type": "signal",
        "name": "Amsterdam Ave",
        "phase": "I",
        "title": "Full traffic signal — Amsterdam Ave",
        "cross": "Amsterdam Avenue",
        "description": "Upgraded full traffic signal.",
        "section": 8,
        "quote": "Full traffic signals are located at: Virginia Ave, Amsterdam Ave, Worchester Dr, Dutch Valley Rd, Ansley Mall Driveway, and Montgomery Ferry Dr.",
    },
    {
        "id": "sig-worcester",
        "type": "signal",
        "name": "Worcester Dr",
        "phase": "I",
        "title": "Full traffic signal — Worcester Dr",
        "cross": "Worcester Drive",
        "description": "Upgraded full traffic signal.",
        "section": 8,
        "quote": "Full traffic signals are located at: Virginia Ave, Amsterdam Ave, Worchester Dr, Dutch Valley Rd, Ansley Mall Driveway, and Montgomery Ferry Dr.",
    },
    {
        "id": "sig-dutchvalley",
        "type": "signal",
        "name": "Dutch Valley Rd",
        "phase": "I",
        "title": "Full traffic signal — Dutch Valley Rd",
        "cross": "Dutch Valley Road",
        "description": "Upgraded full traffic signal.",
        "section": 8,
        "quote": "Full traffic signals are located at: Virginia Ave, Amsterdam Ave, Worchester Dr, Dutch Valley Rd, Ansley Mall Driveway, and Montgomery Ferry Dr.",
    },
    {
        "id": "sig-ansleymall",
        "type": "signal",
        "name": "Ansley Mall Driveway",
        "phase": "I",
        "title": "Full traffic signal — Ansley Mall Driveway",
        "manual": [33.8005321, -84.3716312],
        "description": "Upgraded full traffic signal at the Ansley Mall driveway. Within the segment that retains four lanes.",
        "section": 8,
        "quote": "Full traffic signals are located at: ... Ansley Mall Driveway, and Montgomery Ferry Dr.",
    },
    {
        "id": "sig-montgomeryferry",
        "type": "signal",
        "name": "Montgomery Ferry Dr",
        "phase": "II",
        "title": "Full signal + safety rebuild — Montgomery Ferry Dr",
        "cross": "Montgomery Ferry Drive",
        "description": "Left-turn signals and congestion relief. Raised center median island on the north leg, upgraded ADA ramps and crosswalks, and up to 4 ft of pavement widening north of the intersection to reduce the northbound skew and run-off-road crashes. Right-of-way acquisition here.",
        "section": 4,
        "quote": "The proposed safety improvements ... maintaining an 11-foot northbound travel lane: minor widening of the edge of pavement ... up to four feet north of the intersection to provide a less severe skew ... upgraded ADA ramps and crosswalks, and installation of a center raised median on the northern leg of the intersection.",
    },
    # --- New roundabout -- Sections 2 & 5 ---
    {
        "id": "roundabout-park",
        "type": "roundabout",
        "name": "Roundabout (~Park Dr)",
        "phase": "II",
        "title": "New roundabout (replaces a signal)",
        "cross": "Park Drive Northeast",
        "manual": [33.785694, -84.36745],
        "description": "One of the 10 existing signals along the corridor is replaced with a roundabout, within the Phase II segment (8th St through Park Dr).",
        "section": 5,
        "quote": "One of the 10 existing signals will be replaced with a roundabout...",
    },
    # --- Pedestrian Hybrid Beacons (PHB) -- Sections 4, 6, 8 ---
    {
        "id": "phb-westminster",
        "type": "phb",
        "name": "Westminster Dr",
        "phase": "I",
        "title": "Pedestrian Hybrid Beacon — Westminster Dr",
        "cross": "Westminster Drive",
        "description": "New Pedestrian Hybrid Beacon (PHB) — pedestrian-actuated signal that stops traffic for crossings.",
        "section": 8,
        "quote": "PHBs are located at: Westminster Dr and the Publix property.",
    },
    {
        "id": "phb-publix",
        "type": "phb",
        "name": "Publix property",
        "phase": "I",
        "title": "Pedestrian Hybrid Beacon — Publix property",
        "manual": [33.80013, -84.3713],
        "description": "New Pedestrian Hybrid Beacon (PHB) at a mid-block crossing in front of Ansley Mall (the Publix property), with a center median island. One of two new signalized crossings added between Montgomery Ferry Dr and Piedmont Rd for transit users; provides an accessible pedestrian connection between Ansley Mall and the Atlanta BeltLine via Montgomery Ferry Dr.",
        "section": 8,
        "quote": "PHBs are located at: Westminster Dr and the Publix property. ... a Pedestrian Hybrid Beacon at new mid-block crossing with a center median island in front of Ansley Mall will provide connectivity ... to the Atlanta BeltLine.",
    },
    # NOTE: The PDF's §4 "mid-block PHB in front of Ansley Mall" and §6 "PHB between
    # Ansley Circle and Piedmont Rd" are the SAME device as the §8 "Publix property"
    # PHB (§5 caps new PHBs at two: Westminster + Publix). Merged into phb-publix above.
    # --- Rectangular Rapid Flashing Beacons (RRFB) -- Sections 6 & 8 ---
    {
        "id": "rrfb-cresthill",
        "type": "rrfb",
        "name": "Cresthill Ave",
        "phase": "II",
        "title": "RRFB — Cresthill Ave",
        "cross": "Cresthill Avenue",
        "description": "New Rectangular Rapid Flashing Beacon (RRFB) — pedestrian-actuated flashing warning at a marked crosswalk.",
        "section": 8,
        "quote": "RRFBs are located at: Cresthill Ave, Elmwood Dr, Orme Cir, Yorkshire Dr, Kroger property, and Rock Springs Rd.",
    },
    {
        "id": "rrfb-elmwood",
        "type": "rrfb",
        "name": "Elmwood Dr",
        "phase": "II",
        "title": "RRFB — Elmwood Dr",
        "cross": "Elmwood Drive",
        "description": "New Rectangular Rapid Flashing Beacon (RRFB).",
        "section": 8,
        "quote": "RRFBs are located at: Cresthill Ave, Elmwood Dr, Orme Cir, Yorkshire Dr, Kroger property, and Rock Springs Rd.",
    },
    {
        "id": "rrfb-orme",
        "type": "rrfb",
        "name": "Orme Cir",
        "phase": "I",
        "title": "RRFB — Orme Cir",
        "cross": "Orme Circle",
        "description": "New Rectangular Rapid Flashing Beacon (RRFB).",
        "section": 8,
        "quote": "RRFBs are located at: Cresthill Ave, Elmwood Dr, Orme Cir, Yorkshire Dr, Kroger property, and Rock Springs Rd.",
    },
    {
        "id": "rrfb-yorkshire",
        "type": "rrfb",
        "name": "Yorkshire Rd",
        "phase": "I",
        "title": "RRFB + permitted left turn — Yorkshire Rd",
        "cross": "Yorkshire Road",
        "description": "New RRFB. A left turn from Yorkshire Rd onto Monroe Dr will remain permitted.",
        "section": 8,
        "quote": "RRFBs are located at: ... Yorkshire Dr ...  Yes, a left from Yorkshire Rd onto Monroe Dr will be permitted.",
    },
    {
        "id": "rrfb-kroger",
        "type": "rrfb",
        "name": "Kroger property",
        "phase": "I",
        "title": "RRFB — Kroger property",
        "manual": [33.801129, -84.371926],
        "description": "New Rectangular Rapid Flashing Beacon (RRFB) at the Kroger property (1700 Monroe Dr), on Monroe Dr between Ansley Circle and Montgomery Ferry Dr — one of two new signalized crossings added in this stretch for transit users.",
        "section": 8,
        "quote": "RRFBs are located at: ... Kroger property, and Rock Springs Rd. ... a Reflective Rapid Flashing Beacon will be installed between Ansley Circle and Montgomery Ferry Dr.",
    },
    {
        "id": "rrfb-rocksprings",
        "type": "rrfb",
        "name": "Rock Springs Rd",
        "phase": "I",
        "title": "RRFB — Rock Springs Rd",
        "cross": "Rock Springs Road",
        "description": "New Rectangular Rapid Flashing Beacon (RRFB).",
        "section": 8,
        "quote": "RRFBs are located at: ... and Rock Springs Rd.",
    },
    # NOTE: The PDF's §6 "RRFB between Ansley Circle and Montgomery Ferry Dr" is the
    # SAME device as the §8 "Kroger property" RRFB (§5 caps new RRFBs at six, all listed
    # in §8). Merged into rrfb-kroger above.
    # --- Geometry / alignment fixes & medians -- Sections 4, 5 ---
    {
        "id": "align-cumberland",
        "type": "median",
        "name": "Cumberland Rd",
        "phase": "I",
        "title": "Intersection realignment — Cumberland Rd",
        "cross": "Cumberland Road",
        "description": "Alignment adjusted to shorten the pedestrian crossing across Cumberland Rd by ~30 ft, improve sight lines, simplify movements, and slow right-turning vehicles onto Monroe Dr.",
        "section": 4,
        "quote": "The alignment of the intersection has been adjusted to reduce the length for the pedestrian crossing across Cumberland Rd by approximately 30-feet...",
    },
    {
        "id": "align-sherwood",
        "type": "median",
        "name": "Sherwood Rd",
        "phase": "I",
        "title": "Intersection realignment — Sherwood Rd",
        "cross": "Sherwood Road",
        "description": "Alignment adjusted to shorten the pedestrian crossing across Sherwood Rd by ~40 ft, improve sight lines, and slow right-turning vehicles onto Sherwood Rd.",
        "section": 5,
        "quote": "The alignment of the intersection has been adjusted to reduce the length for the pedestrian crossing across Sherwood Rd by approximately 40 feet...",
    },
    # --- Curb / ADA / crossing upgrades -- Sections 1, 5 ---
    {
        "id": "curb-piedmont",
        "type": "curb",
        "name": "Piedmont Ave & Monroe",
        "phase": "I",
        "title": "Curb & ADA upgrades — Piedmont Ave",
        "cross": "Piedmont Avenue",
        "description": "Each corner receives upgraded curb lines and ADA ramps to better define the vehicle travel path and shorten pedestrian crossings. Northern end of the segment that retains four lanes.",
        "section": 5,
        "quote": "Each corner of the intersection will receive upgraded curb lines and ADA ramps to better define the vehicle travel path and provide shorter pedestrian crossings.",
    },
    {
        "id": "recon-kanuga",
        "type": "curb",
        "name": "Kanuga St",
        "phase": "II",
        "title": "Intersection reconfiguration — Kanuga St",
        "cross": "Kanuga Street",
        "description": "Reconfigured concurrently with the 10th St & Monroe Dr intersection to incorporate roadway and BeltLine improvements.",
        "section": 1,
        "quote": "The present intersection reconfiguration at Kanuga St and Monroe Dr and the intersection at 10th St and Monroe Dr were concurrently designed...",
    },
    # --- BeltLine / bike crossings -- Sections 1, 5, 6 ---
    {
        "id": "beltline-10th",
        "type": "beltline",
        "name": "10th St & BeltLine",
        "phase": "II",
        "title": "BeltLine crossing + all-stop ped phase — 10th St",
        "cross": "10th Street",
        "description": "Key Atlanta BeltLine access point. Existing all-stop (pedestrian scramble) phase; safe bicycle crossing of Monroe Dr incorporated. Excluded from the 22 side-street count and treated as a signature crossing.",
        "section": 6,
        "quote": "There is already an all-stop phase for pedestrian crossings at the 10th St intersection... Opportunities for safe bicycle crossing of Monroe Dr at the BeltLine/10th St intersection ... have been incorporated.",
    },
    {
        "id": "bike-parkdr",
        "type": "beltline",
        "name": "Park Dr SE bike crossing",
        "phase": "II",
        "title": "Bicycle crossing — Park Dr SE",
        "manual": [33.785694, -84.36745],
        "description": "Safe bicycle crossing of Monroe Dr incorporated at Park Dr SE (bike lanes are not included along Monroe itself).",
        "section": 1,
        "quote": "Opportunities for safe bicycle crossing of Monroe Dr at the BeltLine/10th St intersection and Park Dr SE have been incorporated...",
    },
]

# Ordered points used by the frontend to color the corridor line. Resolved the
# same way as features (cross-street intersection preferred).
BOUNDARIES = [
    {"id": "b-8th", "name": "8th St (south limit / Phase II start)", "cross": "8th Street"},
    {
        "id": "b-park",
        "name": "Park Dr (Phase I / II split)",
        "cross": "Park Drive Northeast",
        "manual": [33.785694, -84.36745],
    },
    {"id": "b-piedmont", "name": "Piedmont Ave (4-lane segment start)", "cross": "Piedmont Avenue"},
    {"id": "b-ansley", "name": "Ansley Mall frontage (4-lane segment end)", "manual": [33.80184, -84.37230]},
    {"id": "b-armour", "name": "Armour Dr (north limit)", "cross": "Armour Drive"},
]


def overpass(query: str) -> dict:
    """POST to Overpass, retrying across mirrors with backoff on 429/504/timeout."""
    last_exc: Optional[Exception] = None
    for attempt in range(6):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=180)
            if resp.status_code in (429, 502, 503, 504):
                raise requests.HTTPError(f"{resp.status_code} from {url}")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            wait = 5 * (attempt + 1)
            print(f"    overpass attempt {attempt + 1} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Overpass failed after retries: {last_exc}")


def fetch_monroe() -> tuple[list[list[list[float]]], dict[int, list[float]]]:
    """Fetch Monroe Dr NE ways: return (list of coord-segments, {node_id: coord})."""
    s, w, n, e = BBOX
    query = f"""
    [out:json][timeout:120];
    way["name"~"{MONROE_NAME_RE}"]["highway"]({s},{w},{n},{e});
    out geom;
    """
    data = overpass(query)
    segments: list[list[list[float]]] = []
    node_coords: dict[int, list[float]] = {}
    for el in data.get("elements", []):
        geom = el.get("geometry")
        node_ids = el.get("nodes", [])
        if not geom:
            continue
        seg = [[round(p["lat"], 7), round(p["lon"], 7)] for p in geom]
        segments.append(seg)
        for nid, coord in zip(node_ids, seg):
            node_coords[nid] = coord
    print(f"  corridor: {len(segments)} Monroe Dr way segment(s), {len(node_coords)} nodes")
    return segments, node_coords


def fetch_intersections(monroe_nodes: dict[int, list[float]]) -> dict[str, list[float]]:
    """One query for all named roads in the bbox; find those sharing a Monroe node."""
    s, w, n, e = BBOX
    query = f"""
    [out:json][timeout:120];
    way["highway"]["name"]({s},{w},{n},{e});
    out body;
    """
    data = overpass(query)
    table: dict[str, list[float]] = {}
    for el in data.get("elements", []):
        name = el.get("tags", {}).get("name")
        if not name:
            continue
        for nid in el.get("nodes", []):
            if nid in monroe_nodes:
                table.setdefault(name.lower(), monroe_nodes[nid])
                break
    print(f"  intersections: {len(table)} streets cross Monroe Dr")
    return table


def stitch(segments: list[list[list[float]]]) -> tuple[list[list[float]], list[list[list[float]]]]:
    """Join way segments into one path; return (longest_path, leftover_segments)."""
    if not segments:
        return [], []
    segs = [list(s) for s in segments]
    path = segs.pop(0)
    changed = True
    while segs and changed:
        changed = False
        for i, seg in enumerate(segs):
            if seg[0] == path[-1]:
                path.extend(seg[1:])
            elif seg[-1] == path[-1]:
                path.extend(list(reversed(seg))[1:])
            elif seg[-1] == path[0]:
                path[:0] = seg[:-1]
            elif seg[0] == path[0]:
                path[:0] = list(reversed(seg))[:-1]
            else:
                continue
            segs.pop(i)
            changed = True
            break
    if segs:
        print(f"  corridor: {len(segs)} segment(s) not stitched into the main path (kept as leftovers)")
    return path, segs


def nominatim_coord(query: str) -> Optional[list[float]]:
    params = {"q": query, "format": "json", "limit": 1}
    resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return [round(float(results[0]["lat"]), 7), round(float(results[0]["lon"]), 7)]


def resolve(spec: dict, table: dict[str, list[float]]) -> tuple[Optional[list[float]], str]:
    """Resolve a feature/boundary spec to (coord, method)."""
    cross = spec.get("cross")
    if cross:
        key = cross.lower()
        for name, coord in table.items():
            if name.startswith(key):
                return coord, "overpass-intersection"
    if spec.get("nominatim"):
        try:
            coord = nominatim_coord(spec["nominatim"])
            time.sleep(1.2)
            if coord:
                return coord, "nominatim"
        except requests.RequestException as exc:
            print(f"    nominatim error for {spec['name']}: {exc}")
    if spec.get("manual"):
        return list(spec["manual"]), "manual"
    return None, "unresolved"


def main() -> None:
    print("Fetching Monroe Dr corridor geometry...")
    segments, monroe_nodes = fetch_monroe()
    corridor, leftovers = stitch(segments)
    print("Computing cross-street intersections...")
    table = fetch_intersections(monroe_nodes)

    print("Resolving boundary points...")
    boundaries = {}
    for spec in BOUNDARIES:
        coord, method = resolve(spec, table)
        boundaries[spec["id"]] = {"name": spec["name"], "coord": coord}
        print(f"  {spec['name']:45s} {method:22s} {coord}")

    print("Resolving feature coordinates...")
    features = []
    for spec in FEATURES:
        coord, method = resolve(spec, table)
        feat = {k: spec[k] for k in ("id", "type", "name", "title", "description", "section", "quote", "phase")}
        feat["lat"] = coord[0] if coord else None
        feat["lng"] = coord[1] if coord else None
        feat["geocode_method"] = method
        features.append(feat)
        flag = "" if coord else "  <-- UNRESOLVED"
        print(f"  {spec['name']:30s} {method:22s} {coord}{flag}")

    out = {
        "project": "Monroe Drive Safe Streets Project",
        "source": "City of Atlanta DOT — Project Meeting Q&A, April 14, 2026",
        "project_url": "https://atldot.atlantaga.gov/projects/monroe-dr-safe-street",
        "corridor": corridor,
        "corridor_leftovers": leftovers,
        "boundaries": boundaries,
        "features": features,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    resolved = sum(1 for f in features if f["lat"] is not None)
    print(f"\nWrote {OUT_PATH} — corridor points: {len(corridor)}, features: {resolved}/{len(features)} resolved")


if __name__ == "__main__":
    main()
