# /// script
# dependencies = [
#   "httpx",
#   "beautifulsoup4",
# ]
# ///

import json
import re
import time
from pathlib import Path

import httpx

BASE_URL = "https://www.levels.fyi/companies"

# Job family → company → level mapping
JOB_FAMILIES: dict[str, dict[str, dict[str, str]]] = {
    "software-engineer": {
        "google": {"level_slug": "l5", "level_name": "L5"},
        "meta": {"level_slug": "e5", "level_name": "E5"},
        "amazon": {"level_slug": "sde-iii", "level_name": "SDE III (L6)"},
        "apple": {"level_slug": "ict4", "level_name": "ICT4"},
        "microsoft": {"level_slug": "senior-sde", "level_name": "Senior SDE (63)"},
        "stripe": {"level_slug": "l3", "level_name": "L3"},
        "netflix": {"level_slug": "l5", "level_name": "L5"},
        "uber": {"level_slug": "senior-software-engineer", "level_name": "Senior (5a)"},
        "airbnb": {"level_slug": "g9", "level_name": "G9"},
    },
    "product-manager": {
        "google": {"level_slug": "product-manager-2", "level_name": "PM2 (L5)"},
        "meta": {"level_slug": "l5-product-manager", "level_name": "L5 PM"},
        "amazon": {"level_slug": "senior-product-manager", "level_name": "Senior PM (L6)"},
        "apple": {"level_slug": "ict4", "level_name": "ICT4"},
        "microsoft": {"level_slug": "63", "level_name": "63"},
        "stripe": {"level_slug": "l3", "level_name": "L3"},
        "netflix": {"level_slug": "senior-product-manager", "level_name": "Senior PM"},
        "uber": {"level_slug": "senior-product-manager", "level_name": "Senior PM (5a)"},
        "airbnb": {"level_slug": "l5", "level_name": "L5"},
    },
}

LOCATIONS: dict[str, str] = {
    "San Francisco": "san-francisco-bay-area",
    "New York City": "new-york-city-area",
    "Atlanta": "atlanta-area",
    "Seattle": "greater-seattle-area",
}

SCRIPT_DIR = Path(__file__).parent
RAW_HTML_DIR = SCRIPT_DIR / "raw_html_levels"
EXTRACTED_DIR = SCRIPT_DIR / "extracted_json_levels"


def fetch_page(url: str, cache_key: str) -> str:
    """Fetch HTML from URL, cache locally, return raw HTML."""
    cache_path = RAW_HTML_DIR / f"{cache_key}.html"
    if cache_path.exists():
        return cache_path.read_text()

    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    resp = httpx.get(url, follow_redirects=True, timeout=60, headers=headers)
    resp.raise_for_status()
    html = resp.text
    cache_path.write_text(html)
    time.sleep(1)
    return html


def extract_from_next_data(html: str) -> dict | None:
    """Extract compensation stats from Next.js __NEXT_DATA__ embedded JSON."""
    match = re.search(r'__NEXT_DATA__.*?>(.*?)</script>', html)
    if not match:
        return None

    data = json.loads(match.group(1))
    stats = data.get("props", {}).get("pageProps", {}).get("companyJobFamilyLevelLocationStats")
    if not stats:
        return None

    tc = stats.get("totalCompensation", {})
    base = stats.get("baseSalary", {})
    stock = stats.get("stockGrant", {})
    bonus = stats.get("bonus", {})

    return {
        "median_total_comp": tc.get("p50"),
        "median_base": base.get("p50"),
        "median_stock": stock.get("p50"),
        "median_bonus": bonus.get("p50"),
        "p10_total_comp": tc.get("p10"),
        "p90_total_comp": tc.get("p90"),
        "sample_size": stats.get("count"),
    }


def load_extracted(job_family: str, company: str, location: str) -> dict | None:
    """Load previously extracted data from cache."""
    cache_key = f"{job_family}_{company}_{location.replace(' ', '_')}"
    cache_path = EXTRACTED_DIR / f"{cache_key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return None


def save_extracted(job_family: str, company: str, location: str, data: dict) -> None:
    """Save extracted data to cache."""
    cache_key = f"{job_family}_{company}_{location.replace(' ', '_')}"
    cache_path = EXTRACTED_DIR / f"{cache_key}.json"
    cache_path.write_text(json.dumps(data, indent=2))


def main() -> None:
    RAW_HTML_DIR.mkdir(exist_ok=True)
    EXTRACTED_DIR.mkdir(exist_ok=True)

    output: dict = {}

    for job_family, companies in JOB_FAMILIES.items():
        print(f"\n{'='*60}")
        print(f"  JOB FAMILY: {job_family}")
        print(f"{'='*60}")

        family_output: dict = {"companies": {}}

        for company_slug, config in companies.items():
            print(f"\n--- {company_slug} ({config['level_name']}) ---")
            company_data: dict = {"level": config["level_name"]}

            for loc_name, loc_slug in LOCATIONS.items():
                # Check extracted cache
                cached = load_extracted(job_family, company_slug, loc_name)
                if cached is not None:
                    company_data[loc_name] = cached
                    tc = cached.get("median_total_comp")
                    print(f"  {loc_name}: cached" + (f" (${tc:,})" if tc else " (no data)"))
                    continue

                # Build URL
                url = f"{BASE_URL}/{company_slug}/salaries/{job_family}/levels/{config['level_slug']}/locations/{loc_slug}"
                cache_key = f"{company_slug}_{job_family}_{config['level_slug']}_{loc_slug}"
                print(f"  {loc_name}: fetching...", end=" ", flush=True)

                try:
                    html = fetch_page(url, cache_key)
                    data = extract_from_next_data(html)
                    if data and data.get("median_total_comp"):
                        company_data[loc_name] = data
                        save_extracted(job_family, company_slug, loc_name, data)
                        print(f"OK (${data['median_total_comp']:,}, n={data.get('sample_size', '?')})")
                    else:
                        company_data[loc_name] = None
                        save_extracted(job_family, company_slug, loc_name, {"median_total_comp": None, "note": "insufficient data on levels.fyi"})
                        print("no data available")
                except Exception as e:
                    print(f"ERROR: {e}")
                    company_data[loc_name] = None

            family_output["companies"][company_slug] = company_data

        output[job_family] = family_output

    # Write output
    output_path = SCRIPT_DIR / "levels_data.json"
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
