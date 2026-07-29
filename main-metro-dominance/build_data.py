# /// script
# dependencies = [
#   "httpx",
#   "pandas",
#   "openpyxl",
# ]
# ///
"""Build the main-metro-dominance dataset.

For every state, find the metro area holding the largest share of that state's
population, and express it as a percentage of the state total.

Sources (both are plain static files — no Census API key required):
  - County population estimates, Vintage 2025  -> census.gov popest
  - OMB CBSA delineations, July 2023           -> census.gov metro-micro reference files

Method. Counties are joined to metros on 5-digit FIPS, then grouped by
(state, metro) and summed. That means a metro straddling a state line is counted
only for the part inside each state, so a share can never exceed 100% and
multi-state metros (New York, Kansas City, Washington) land correctly on both
sides of the border. The denominator is the state total summed from the same
county file, so numerator and denominator always agree.

Two definitions are computed and shipped side by side:
  msa  Metropolitan Statistical Areas only; micropolitan areas excluded.
  csa  Combined Statistical Areas where one exists, else the bare MSA. CSA groups
       include their micropolitan member counties, since that is what a CSA is.

Usage:
  uv run build_data.py            # use cache, only fetch missing
  uv run build_data.py --refresh  # force re-download both sources
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

HERE = Path(__file__).parent
CACHE = HERE / "raw_responses"
DATA_JSON = HERE / "data.json"

POP_VINTAGE = 2025
DELINEATION_YEAR = 2023

COUNTY_POP_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    f"2020-{POP_VINTAGE}/counties/totals/co-est{POP_VINTAGE}-alldata.csv"
)
DELINEATION_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/"
    f"{DELINEATION_YEAR}/delineation-files/list1_{DELINEATION_YEAR}.xlsx"
)

POP_COL = f"POPESTIMATE{POP_VINTAGE}"

# The 50 states, and only the 50 states — this mapping is also the filter. D.C. is
# left out because it sits entirely inside its own metro, so its 100% is a definitional
# artifact rather than a fact about urban concentration; Puerto Rico has no state
# population to compare against in this framing.
STATE_CODES = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}


def fetch(url: str, filename: str, refresh: bool) -> Path:
    """Download url into the cache directory, reusing the cached copy unless refreshing."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / filename
    if path.exists() and not refresh:
        print(f"  cached  {filename} ({path.stat().st_size / 1024:.0f} KB)")
        return path
    print(f"  fetching {url}")
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        resp = client.get(url)
        resp.raise_for_status()
        path.write_bytes(resp.content)
    print(f"  wrote   {filename} ({path.stat().st_size / 1024:.0f} KB)")
    return path


def load_counties(path: Path) -> pd.DataFrame:
    """County-level rows with a 5-digit FIPS key. SUMLEV 50 is county, 40 is state total."""
    df = pd.read_csv(path, encoding="latin-1")
    df = df[df.SUMLEV == 50].copy()
    df["fips"] = df.STATE.map("{:02d}".format) + df.COUNTY.map("{:03d}".format)
    return df[["fips", "STNAME", "CTYNAME", POP_COL]].rename(
        columns={"STNAME": "state", "CTYNAME": "county", POP_COL: "pop"}
    )


def load_delineation(path: Path) -> pd.DataFrame:
    """CBSA/CSA membership by county. Two header rows precede the table, footnotes follow it."""
    df = pd.read_excel(path, skiprows=2)
    df = df[df["FIPS County Code"].notna()].copy()  # drops trailing footnote rows
    df["fips"] = df["FIPS State Code"].astype(int).map("{:02d}".format) + df["FIPS County Code"].astype(int).map(
        "{:03d}".format
    )
    df["is_metro"] = df["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metro")
    return df[["fips", "CBSA Title", "CSA Title", "is_metro"]].rename(
        columns={"CBSA Title": "msa_name", "CSA Title": "csa_name"}
    )


def short_name(full: str) -> str:
    """Census metro titles list every principal city; the ranking only has room for one.

    "Las Vegas-Henderson-North Las Vegas, NV" -> "Las Vegas, NV"
    "Atlanta--Athens-Clarke County--Sandy Springs, GA-AL" -> "Atlanta, GA-AL"
    The untruncated title is still shipped as `name` and shown in the detail card.
    """
    cities, _, states = full.rpartition(", ")
    if not cities:  # no comma, nothing to trim
        return full
    lead = cities.split("--")[0].split("-")[0].split("/")[0]
    return f"{lead}, {states}"


def top_metro_by_state(members: pd.DataFrame, state_pop: pd.Series) -> dict:
    """For each state, the metro group with the largest in-state population.

    `members` needs columns: state, group, pop. Grouping by (state, group) before
    taking the max is what restricts a multi-state metro to its in-state portion.
    """
    by_state_group = members.groupby(["state", "group"], as_index=False)["pop"].sum()
    nationwide = members.groupby("group")["pop"].sum()
    # states each group spans, largest share first, so the UI can name the neighbours
    spans = by_state_group.sort_values("pop", ascending=False).groupby("group")["state"].apply(list).to_dict()

    top = by_state_group.sort_values("pop", ascending=False).groupby("state").head(1)
    out = {}
    for row in top.itertuples():
        total = int(nationwide[row.group])
        in_state = int(row.pop)
        member_states = [STATE_CODES[s] for s in spans[row.group] if s in STATE_CODES]
        out[row.state] = {
            "name": row.group,
            "short": short_name(row.group),
            "inState": in_state,
            "metroTotal": total,
            "share": round(in_state / state_pop[row.state] * 100, 1),
            # a metro is "shared" when a meaningful slice of it sits in another state
            "shared": in_state < total * 0.999,
            "spans": member_states,
        }
    return out


def build_payload(counties: pd.DataFrame, delin: pd.DataFrame) -> dict:
    merged = delin.merge(counties, on="fips", how="inner")
    state_pop = counties.groupby("state")["pop"].sum()

    # MSA mode: metropolitan CBSAs only.
    msa_members = merged[merged.is_metro].copy()
    msa_members["group"] = msa_members["msa_name"]

    # CSA mode: the CSA where one exists, else the metro on its own. A county that is
    # micropolitan and not in any CSA belongs to neither grouping and drops out.
    csa_members = merged[merged.is_metro | merged.csa_name.notna()].copy()
    csa_members["group"] = csa_members["csa_name"].fillna(csa_members["msa_name"])
    csa_members = csa_members[csa_members.is_metro | csa_members.csa_name.notna()]

    msa = top_metro_by_state(msa_members, state_pop)
    csa = top_metro_by_state(csa_members, state_pop)

    real_csas = set(merged.csa_name.dropna().unique())
    states = []
    for name, code in sorted(STATE_CODES.items()):
        entry = dict(csa[name])
        entry["isFallback"] = entry["name"] not in real_csas
        states.append(
            {
                "code": code,
                "name": name,
                "pop": int(state_pop[name]),
                "msa": msa[name],
                "csa": entry,
            }
        )

    fallbacks = [s["code"] for s in states if s["csa"]["isFallback"]]
    return {
        "meta": {
            "popVintage": POP_VINTAGE,
            "delineation": DELINEATION_YEAR,
            "generated": date.today().isoformat(),
            "countyPopUrl": COUNTY_POP_URL,
            "delineationUrl": DELINEATION_URL,
            "csaFallbacks": fallbacks,
        },
        "states": states,
    }


def validate(payload: dict, counties: pd.DataFrame) -> None:
    """Fail loudly rather than shipping a subtly wrong ranking."""
    states = payload["states"]
    assert len(states) == 50, f"expected 50 states, got {len(states)}"
    state_pop = counties.groupby("state")["pop"].sum()

    for s in states:
        assert s["pop"] == int(state_pop[s["name"]]), f"{s['code']} population mismatch"
        for mode in ("msa", "csa"):
            m = s[mode]
            assert 0 < m["share"] <= 100, f"{s['code']} {mode} share out of range: {m['share']}"
            assert m["inState"] <= s["pop"], f"{s['code']} {mode} metro exceeds state population"
            assert m["inState"] <= m["metroTotal"], f"{s['code']} {mode} in-state exceeds metro total"
            if m["shared"]:
                assert len(m["spans"]) > 1, f"{s['code']} {mode} flagged shared but spans one state"

    ri = next(s for s in states if s["code"] == "RI")
    assert ri["msa"]["share"] == 100.0, f"Rhode Island should be 100% under MSA, got {ri['msa']['share']}"
    print(f"  validated {len(states)} states, both modes")


def main() -> None:
    refresh = "--refresh" in sys.argv

    print("Stage 1: fetch sources")
    pop_path = fetch(COUNTY_POP_URL, f"co-est{POP_VINTAGE}-alldata.csv", refresh)
    delin_path = fetch(DELINEATION_URL, f"list1_{DELINEATION_YEAR}.xlsx", refresh)

    print("Stage 2: load and join")
    counties = load_counties(pop_path)
    delin = load_delineation(delin_path)
    matched = delin.fips.isin(set(counties.fips))
    # The only expected misses are Puerto Rico municipios, which we do not rank.
    print(f"  {len(counties)} counties, {len(delin)} delineation rows, {(~matched).sum()} unmatched (Puerto Rico)")

    print("Stage 3: compute both modes")
    payload = build_payload(counties, delin)

    print("Stage 4: validate")
    validate(payload, counties)

    print("Stage 5: write data.json + inline into index.html")
    DATA_JSON.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"  wrote {DATA_JSON} ({DATA_JSON.stat().st_size / 1024:.1f} KB)")

    index_html = HERE / "index.html"
    if index_html.exists():
        html_text = index_html.read_text()
        js = "    const DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n"
        pattern = re.compile(r"(// DATA_START\n)(.*?)(    // DATA_END)", re.DOTALL)
        if pattern.search(html_text):
            index_html.write_text(pattern.sub(lambda m: m.group(1) + js + m.group(3), html_text))
            print(f"  inlined DATA into {index_html}")
        else:
            print(f"  WARNING: no DATA_START/DATA_END sentinels in {index_html}", file=sys.stderr)

    ranked = sorted(payload["states"], key=lambda s: -s["msa"]["share"])
    print("Top 5 (MSA):")
    for s in ranked[:5]:
        print(f"  {s['code']}  {s['msa']['share']:5.1f}%  {s['msa']['name']}")
    print("Bottom 3 (MSA):")
    for s in ranked[-3:]:
        print(f"  {s['code']}  {s['msa']['share']:5.1f}%  {s['msa']['name']}")
    print(f"CSA fallbacks (no CSA exists): {', '.join(payload['meta']['csaFallbacks'])}")


if __name__ == "__main__":
    main()
