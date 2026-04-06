# /// script
# dependencies = [
#   "httpx",
#   "anthropic",
#   "beautifulsoup4",
# ]
# ///

import json
import time
from pathlib import Path

import anthropic
import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://statisticalatlas.com"

# All individual areas to fetch (including separate neighborhoods before combining)
AREAS: dict[str, str] = {
    # States
    "California": "state/California",
    "New York": "state/New-York",
    "Georgia": "state/Georgia",
    # Cities
    "San Francisco": "place/California/San-Francisco",
    "New York City": "place/New-York/New-York",
    "Atlanta": "metro-area/Georgia/Atlanta",
    "Seattle": "metro-area/Washington/Seattle",
    # Neighborhoods (individual, combined later)
    "North Panhandle": "neighborhood/California/San-Francisco/North-Panhandle",
    "Anza Vista": "neighborhood/California/San-Francisco/Anza-Vista",
    "Greenwich Village": "neighborhood/New-York/New-York/Greenwich-Village",
    "Virginia Highland": "neighborhood/Georgia/Atlanta/Virginia-Highland",
    "Morningside-Lenox Park": "neighborhood/Georgia/Atlanta/Morningside---Lenox-Park",
    "Mercer Island": "place/Washington/Mercer-Island",
}

TOPICS = [
    "Population",
    "Race-and-Ethnicity",
    "Household-Income",
    "Educational-Attainment",
    "Employment-Status",
    "Age-and-Sex",
    "Marital-Status",
    "National-Origin",
]

# Which neighborhoods to combine: (mega_name, component1, component2)
MEGA_NEIGHBORHOODS: list[tuple[str, str, str]] = [
    ("North Panhandle + Anza Vista", "North Panhandle", "Anza Vista"),
    ("Virginia Highland + Morningside-Lenox Park", "Virginia Highland", "Morningside-Lenox Park"),
]

EXTRACTION_PROMPTS: dict[str, str] = {
    "Population": """Extract the population data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "total_population": <integer, the total population count>,
  "population_density_per_sq_mi": <float or null if not available>
}}
If a value is not found on the page, use null.""",
    "Race-and-Ethnicity": """Extract race/ethnicity data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "white_percent": <float>,
  "hispanic_percent": <float>,
  "black_percent": <float>,
  "asian_percent": <float>,
  "mixed_percent": <float>,
  "other_percent": <float>,
  "white_count": <int or null>,
  "hispanic_count": <int or null>,
  "black_count": <int or null>,
  "asian_count": <int or null>,
  "mixed_count": <int or null>,
  "other_count": <int or null>
}}
Use null for values not found. Percentages should sum to roughly 100.""",
    "Household-Income": """Extract household income data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "median_household_income": <integer, in dollars>,
  "mean_household_income": <integer, in dollars, or null if not available>
}}
Use null for values not found.""",
    "Educational-Attainment": """Extract educational attainment data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "bachelors_or_higher_percent": <float>,
  "graduate_degree_percent": <float>,
  "high_school_or_higher_percent": <float>,
  "no_hs_diploma_percent": <float>,
  "bachelors_or_higher_count": <int or null>,
  "total_population_25_plus": <int or null, the population 25 and over used as the denominator>
}}
Use null for values not found.""",
    "Employment-Status": """Extract employment status data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "employed_percent": <float>,
  "unemployed_percent": <float>,
  "not_in_labor_force_percent": <float>,
  "employed_count": <int or null>,
  "total_population_16_plus": <int or null, the population 16 and over used as the denominator>
}}
Use null for values not found.""",
    "Age-and-Sex": """Extract age distribution data for {area_name} from this page.
The page shows age cohorts. Return ONLY a JSON object with exactly these fields:
{{
  "senior_percent": <float, age 65+>,
  "older_adult_percent": <float, age 35-64>,
  "younger_adult_percent": <float, age 18-34>,
  "college_percent": <float, age 18-24>,
  "children_percent": <float, age 0-17>,
  "senior_count": <int or null>,
  "older_adult_count": <int or null>,
  "younger_adult_count": <int or null>,
  "college_count": <int or null>,
  "children_count": <int or null>
}}
Use null for values not found. Percentages should sum to roughly 100 (note: college is a subset of younger_adult, so exclude college from the sum).""",
    "Marital-Status": """Extract marital status data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "never_married_percent": <float>,
  "married_percent": <float>,
  "separated_percent": <float>,
  "divorced_percent": <float>,
  "widowed_percent": <float>
}}
Use null for values not found. Percentages should sum to roughly 100.""",
    "National-Origin": """Extract national origin / foreign-born data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "foreign_born_percent": <float, percentage of population that is foreign-born>,
  "foreign_born_count": <int or null>,
  "top_origins": [
    {{"name": "<country name>", "percent": <float>, "count": <int or null>}},
    ...
  ]
}}
Include up to 5 top countries of origin in top_origins, ordered by count/percent descending.
Use null for values not found.""",
    "Commute": """Extract commute and transportation data for {area_name} from this page.
Return ONLY a JSON object with exactly these fields:
{{
  "avg_commute_minutes": <float, average commute time in minutes>,
  "drive_alone_percent": <float, percentage who drive alone>,
  "carpool_percent": <float, percentage who carpool>,
  "public_transit_percent": <float, percentage who use public transit>,
  "walk_percent": <float, percentage who walk>,
  "bike_percent": <float, percentage who bike>,
  "work_from_home_percent": <float, percentage who work from home>
}}
Use null for values not found.""",
}

SCRIPT_DIR = Path(__file__).parent
RAW_HTML_DIR = SCRIPT_DIR / "raw_html"
EXTRACTED_DIR = SCRIPT_DIR / "extracted_json"


def fetch_page(url: str, cache_key: str) -> str:
    """Fetch HTML from URL, cache locally, return cleaned text."""
    cache_path = RAW_HTML_DIR / f"{cache_key}.html"
    if cache_path.exists():
        html = cache_path.read_text()
    else:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        html = resp.text
        cache_path.write_text(html)
        time.sleep(0.5)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_data(area_name: str, topic: str, page_text: str, client: anthropic.Anthropic) -> dict:
    """Use Claude to extract structured data from page text."""
    prompt = EXTRACTION_PROMPTS[topic].format(area_name=area_name)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"{prompt}\n\n--- PAGE CONTENT ---\n{page_text[:50000]}",
            }
        ],
    )
    response_text = message.content[0].text.strip()
    # Extract JSON object from response (handle markdown code blocks, preamble text, etc.)
    start = response_text.index("{")
    end = response_text.rindex("}") + 1
    return json.loads(response_text[start:end])


def load_extracted(area_name: str, topic: str) -> dict | None:
    """Load previously extracted data from cache, or return None."""
    cache_key = f"{area_name.replace(' ', '_').replace('+', '_')}_{topic}"
    cache_path = EXTRACTED_DIR / f"{cache_key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return None


def save_extracted(area_name: str, topic: str, data: dict) -> None:
    """Save extracted data to cache."""
    cache_key = f"{area_name.replace(' ', '_').replace('+', '_')}_{topic}"
    cache_path = EXTRACTED_DIR / f"{cache_key}.json"
    cache_path.write_text(json.dumps(data, indent=2))


def combine_neighborhoods(nb1: dict, nb2: dict) -> dict:
    """Combine two neighborhood data dicts using population-weighted averaging."""
    pop1 = (nb1.get("population") or {}).get("total_population") or 0
    pop2 = (nb2.get("population") or {}).get("total_population") or 0
    total_pop = pop1 + pop2

    combined: dict = {}
    for topic in TOPICS:
        topic_key = topic.lower().replace("-", "_")
        d1 = nb1.get(topic_key) or {}
        d2 = nb2.get(topic_key) or {}
        merged: dict = {}

        for key in set(list(d1.keys()) + list(d2.keys())):
            v1 = d1.get(key)
            v2 = d2.get(key)
            if v1 is None and v2 is None:
                merged[key] = None
                continue
            if v1 is None or v2 is None:
                merged[key] = v1 if v1 is not None else v2
                continue

            if "count" in key or "total_population" in key:
                # Additive fields
                merged[key] = v1 + v2
            elif "percent" in key:
                # Population-weighted average
                if total_pop > 0:
                    merged[key] = round((v1 * pop1 + v2 * pop2) / total_pop, 2)
                else:
                    merged[key] = round((v1 + v2) / 2, 2)
            elif "density" in key:
                # Weighted average by population (approximation)
                if total_pop > 0:
                    merged[key] = round((v1 * pop1 + v2 * pop2) / total_pop, 2)
                else:
                    merged[key] = round((v1 + v2) / 2, 2)
            elif "income" in key or "median" in key or "mean" in key:
                # Weighted average (approximation for medians)
                if total_pop > 0:
                    merged[key] = round((v1 * pop1 + v2 * pop2) / total_pop)
                else:
                    merged[key] = round((v1 + v2) / 2)
            else:
                merged[key] = v1  # fallback: take first

        combined[topic_key] = merged
    return combined


def categorize_area(area_name: str) -> str:
    """Return 'states', 'cities', or 'neighborhoods'."""
    states = {"California", "New York", "Georgia"}
    cities = {"San Francisco", "New York City", "Atlanta", "Seattle"}
    if area_name in states:
        return "states"
    if area_name in cities:
        return "cities"
    return "neighborhoods"


def main() -> None:
    RAW_HTML_DIR.mkdir(exist_ok=True)
    EXTRACTED_DIR.mkdir(exist_ok=True)

    client: anthropic.Anthropic | None = None  # lazy init, only if needed

    all_data: dict[str, dict] = {}

    for area_name, url_path in AREAS.items():
        print(f"\n=== {area_name} ===")
        area_result: dict = {}

        for topic in TOPICS:
            topic_key = topic.lower().replace("-", "_")

            # Check extracted JSON cache first
            cached = load_extracted(area_name, topic)
            if cached is not None:
                area_result[topic_key] = cached
                print(f"  {topic}: cached")
                continue

            # Need to fetch and extract
            url = f"{BASE_URL}/{url_path}/{topic}"
            cache_key = f"{url_path.replace('/', '_')}_{topic}"
            print(f"  {topic}: fetching...", end=" ", flush=True)

            try:
                page_text = fetch_page(url, cache_key)
                if client is None:
                    client = anthropic.Anthropic()
                data = extract_data(area_name, topic, page_text, client)
                area_result[topic_key] = data
                save_extracted(area_name, topic, data)
                print("OK")
            except Exception as e:
                print(f"ERROR: {e}")
                area_result[topic_key] = None

        all_data[area_name] = area_result

    # Build output structure
    output: dict = {
        "metadata": {
            "source": "statisticalatlas.com",
            "fetched_date": "2026-04-06",
            "topics": TOPICS,
        },
        "areas": {
            "states": {},
            "cities": {},
            "neighborhoods": {},
        },
    }

    # Place individual areas (non-mega-neighborhood components go into temp storage)
    mega_components = set()
    for mega_name, c1, c2 in MEGA_NEIGHBORHOODS:
        mega_components.add(c1)
        mega_components.add(c2)

    for area_name, data in all_data.items():
        if area_name in mega_components:
            continue  # handled below
        category = categorize_area(area_name)
        output["areas"][category][area_name] = data

    # Combine mega neighborhoods
    for mega_name, c1, c2 in MEGA_NEIGHBORHOODS:
        combined = combine_neighborhoods(all_data.get(c1, {}), all_data.get(c2, {}))
        combined["_components"] = [c1, c2]
        output["areas"]["neighborhoods"][mega_name] = combined

    # Write output
    output_path = SCRIPT_DIR / "data.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
