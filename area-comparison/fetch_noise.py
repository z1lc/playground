# /// script
# dependencies = [
#   "httpx",
#   "pyshp",
# ]
# ///
"""Compute neighborhood transportation-noise metrics from the Seto & Huang 2023 National
Transportation Noise Exposure Map (DOT/BTS-derived; deohs.washington.edu).

The dataset gives, per census tract, the number of persons exposed in each LAeq band
(ns4050n=45-50 dB, ns5060n=50-60, ns6070n=60-70, ns7080n=70-80, ns8090n=80-90, nois90n=>=90) plus the
ACS total population (`estimat`). Population below 45 dB = total - sum(bands), assigned midpoint 35 dB.
For each neighborhood's census tract(s) we compute a population-weighted average LAeq and the share of
population above the 50 dB (WHO) and 65 dB (FHWA) thresholds. Prints an inline `noise` object per
neighborhood. Downloaded zip is cached in raw_noise/ (gitignored).
"""

import zipfile
from pathlib import Path

import httpx
import shapefile

SCRIPT_DIR = Path(__file__).parent
RAW_DIR = SCRIPT_DIR / "raw_noise"
ZIP_URL = "https://www.edmundseto.com/NTNE_map/conus_shp.zip"
STATE = "GA"  # all target neighborhoods are in Georgia

BANDS = ["ns4050n", "ns5060n", "ns6070n", "ns7080n", "ns8090n", "nois90n"]
MIDPOINT = {"ns4050n": 47.5, "ns5060n": 55, "ns6070n": 65, "ns7080n": 75, "ns8090n": 85, "nois90n": 95}
ABOVE_50 = ["ns5060n", "ns6070n", "ns7080n", "ns8090n", "nois90n"]
BELOW_45_DB = 35

# neighborhood -> (census tract GEOIDs in Fulton County 13121, dominant_source_desc)
NEIGHBORHOODS = {
    "Sweet Auburn": (
        ["13121002802"],
        "Bordered on the west by the Downtown Connector (I-75/I-85); Auburn Ave, Edgewood Ave, and the "
        "downtown street grid add steady traffic noise — the noisiest of the extra Atlanta neighborhoods.",
    ),
    "Cabbagetown": (
        ["13121003200"],
        "Wedged against the CSX Hulsey rail yard and Memorial Dr, with I-20 just to the south adding "
        "highway noise; narrow interior streets are calmer.",
    ),
    "Reynoldstown": (
        ["13121003100"],
        "I-20 runs along the south edge and the CSX / BeltLine rail corridor along the west; Moreland Ave "
        "and Wylie St carry traffic.",
    ),
    "Inman Park": (
        ["13121003000"],
        "DeKalb Ave and the parallel CSX / MARTA rail corridor run along the south edge; Moreland Ave, "
        "Freedom Pkwy, and N. Highland Ave carry traffic, while interior Victorian blocks are quieter.",
    ),
    "Old Fourth Ward": (
        ["13121001701", "13121001702", "13121001801", "13121001802", "13121002900"],
        "Ponce de Leon Ave and North Ave carry east-west traffic; Boulevard and Piedmont Ave carry "
        "north-south traffic, with the Downtown Connector west of the neighborhood and the BeltLine "
        "Eastside Trail on its eastern edge.",
    ),
    "Piedmont Heights": (
        ["13121009202"],
        "I-85 borders the north, Piedmont Road carries traffic through the neighborhood, and the "
        "western BeltLine / Monroe corridor adds road and rail noise along the western edge.",
    ),
}


def load_state_records() -> dict:
    """Download+cache the CONUS zip, extract the Georgia shapefile, return {GEOID: attributes}."""
    RAW_DIR.mkdir(exist_ok=True)
    base = RAW_DIR / f"tractresult{STATE}"
    if not base.with_suffix(".dbf").exists():
        zpath = RAW_DIR / "conus_shp.zip"
        if not zpath.exists():
            print("  downloading conus_shp.zip ...")
            with httpx.stream("GET", ZIP_URL, timeout=300, follow_redirects=True) as resp:
                resp.raise_for_status()
                with zpath.open("wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
        with zipfile.ZipFile(zpath) as z:
            for ext in ("dbf", "shp", "shx", "prj"):
                z.extract(f"tractresult{STATE}.{ext}", RAW_DIR)
    reader = shapefile.Reader(str(base))
    fields = [f[0] for f in reader.fields[1:]]
    return {dict(zip(fields, rec))["GEOID"]: dict(zip(fields, rec)) for rec in reader.records()}


def compute(records: dict, tracts: list[str]) -> dict:
    agg = {b: 0.0 for b in BANDS}
    total = 0.0
    for geoid in tracts:
        rec = records[geoid]
        total += rec["estimat"]
        for b in BANDS:
            agg[b] += rec[b]
    below45 = total - sum(agg.values())
    avg_db = (below45 * BELOW_45_DB + sum(agg[b] * MIDPOINT[b] for b in BANDS)) / total
    pct_50 = sum(agg[b] for b in ABOVE_50) / total * 100
    pct_65 = (0.5 * agg["ns6070n"] + agg["ns7080n"] + agg["ns8090n"] + agg["nois90n"]) / total * 100
    return {
        "avg_db": round(avg_db, 1),
        "pct_above_50db": round(pct_50, 1),
        "pct_above_65db": round(pct_65, 1),
    }


def main() -> None:
    records = load_state_records()
    for name, (tracts, desc) in NEIGHBORHOODS.items():
        m = compute(records, tracts)
        print(
            f"{name}: tracts={tracts} pop={round(sum(records[t]['estimat'] for t in tracts))} -> "
            f'"noise":{{"avg_db":{m["avg_db"]},"pct_above_50db":{m["pct_above_50db"]},'
            f'"pct_above_65db":{m["pct_above_65db"]},"dominant_source":"road","dominant_source_desc":"{desc}"}}'
        )


if __name__ == "__main__":
    main()
