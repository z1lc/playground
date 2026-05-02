# /// script
# dependencies = [
#   "httpx",
#   "beautifulsoup4",
#   "pyyaml",
#   "markdownify",
# ]
# ///
"""
Stage 1 of the FDE jobs pipeline: scrape job listings from a curated set of
companies and write nicely-formatted markdown files (max 2 per company), plus
a manifest.json index for downstream stages.

Run:
    source ../KEYS
    uv run fetch_listings.py [--refresh]

Output:
    listings/<company-slug>__<listing-slug>.md   (committed)
    manifest.json                                (committed)
    raw_responses/<slug>.json|.html              (gitignored cache)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify

SCRIPT_DIR = Path(__file__).parent
COMPANIES_PATH = SCRIPT_DIR / "companies.yaml"
RAW_DIR = SCRIPT_DIR / "raw_responses"
LISTINGS_DIR = SCRIPT_DIR / "listings"
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"

CACHE_TTL_SECONDS = 24 * 3600

INCLUDE_PATTERNS: list[tuple[str, str]] = [
    (r"forward[- ]deployed", "forward-deployed"),
    (r"implementation engineer", "implementation"),
    (r"deployment engineer", "deployment"),
    (r"solutions? engineer", "solutions"),
    (r"customer engineer", "customer"),
]
EXCLUDE_PATTERNS: list[str] = [
    r"sales engineer",
    r"manager|director|head of|\blead\b|principal|vp\b",
    r"intern\b",
    # Non-engineering "forward deployed *" roles (e.g., Hebbia's
    # "Forward Deployed Investor", Runway's "Forward Deployed Finance Partner",
    # Mistral's "AI Deployment Strategist").
    r"\b(investor|banker|finance|strategist|advisor|advocate|analyst|associate|consultant)\b",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "deepseek/deepseek-v4-pro:floor"

USER_AGENT = "fde-jobs-scraper/0.1 (rsanek@gmail.com)"


# ---------- caching ----------

def cache_path(slug: str, ext: str) -> Path:
    return RAW_DIR / f"{slug}.{ext}"

def cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) < CACHE_TTL_SECONDS

def load_json_cache(slug: str) -> Optional[Any]:
    p = cache_path(slug, "json")
    if cache_fresh(p):
        return json.loads(p.read_text())
    return None

def save_json_cache(slug: str, data: Any) -> None:
    cache_path(slug, "json").write_text(json.dumps(data, indent=2))

def load_html_cache(slug: str) -> Optional[str]:
    p = cache_path(slug, "html")
    if cache_fresh(p):
        return p.read_text()
    return None

def save_html_cache(slug: str, html: str) -> None:
    cache_path(slug, "html").write_text(html)


# ---------- ATS adapters: fetch raw, then normalize ----------

def fetch_greenhouse(board_id: str) -> dict:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs?content=true"
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.json()

def normalize_greenhouse(company: dict, raw: dict) -> list[dict]:
    out = []
    for j in raw.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        # Greenhouse content field is HTML-entity-escaped HTML.
        import html as html_mod
        body_html = html_mod.unescape(j.get("content", "") or "")
        out.append(make_listing_dict(
            company=company,
            title=j.get("title", ""),
            location=loc,
            url=j.get("absolute_url", ""),
            body_html=body_html,
            posted_at=j.get("updated_at") or j.get("first_published"),
            ats="greenhouse",
            compensation_raw=extract_comp_from_html(body_html),
        ))
    return out


def fetch_lever(board_id: str) -> list:
    url = f"https://api.lever.co/v0/postings/{board_id}?mode=json"
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.json()

def normalize_lever(company: dict, raw: list) -> list[dict]:
    out = []
    for j in raw:
        cats = j.get("categories", {}) or {}
        loc = cats.get("location") or ""
        # Lever splits the body across opening/description/lists/additional. Stitch them.
        parts = []
        if j.get("descriptionBody"): parts.append(j["descriptionBody"])
        if j.get("description") and not j.get("descriptionBody"):
            parts.append(j["description"])
        for lst in (j.get("lists") or []):
            heading = lst.get("text", "")
            content = lst.get("content", "")
            parts.append(f"<h3>{heading}</h3>{content}")
        if j.get("additional"): parts.append(j["additional"])
        body_html = "\n".join(parts)
        # Approximate posted_at — Lever exposes createdAt as ms epoch.
        ts = j.get("createdAt")
        posted_iso = (
            datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
            if isinstance(ts, (int, float)) else None
        )
        out.append(make_listing_dict(
            company=company,
            title=j.get("text", ""),
            location=loc,
            url=j.get("hostedUrl", ""),
            body_html=body_html,
            posted_at=posted_iso,
            ats="lever",
            team=cats.get("team"),
            compensation_raw=extract_comp_from_html(body_html),
        ))
    return out


def fetch_ashby(board_id: str) -> dict:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_id}?includeCompensation=true"
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.json()

def normalize_ashby(company: dict, raw: dict) -> list[dict]:
    out = []
    for j in raw.get("jobs", []):
        loc = j.get("locationName") or ""
        if not loc:
            addr = j.get("address") or {}
            postal = (addr.get("postalAddress") or {})
            loc = ", ".join(filter(None, [postal.get("addressLocality"), postal.get("addressRegion")]))
        if not loc and j.get("isRemote"):
            loc = "Remote"
        # Ashby compensation: if requested, comes back as `compensation` block.
        comp_raw = ""
        comp_block = j.get("compensation") or {}
        tiers = comp_block.get("compensationTierSummary") or comp_block.get("summary") or ""
        if tiers:
            comp_raw = tiers if isinstance(tiers, str) else json.dumps(tiers)
        body_html = j.get("descriptionHtml") or ""
        out.append(make_listing_dict(
            company=company,
            title=j.get("title", ""),
            location=loc,
            url=j.get("jobUrl", ""),
            body_html=body_html,
            posted_at=j.get("publishedAt"),
            ats="ashby",
            team=j.get("team") or j.get("department"),
            compensation_raw=comp_raw or extract_comp_from_html(body_html),
        ))
    return out


def fetch_custom(careers_url: str, slug: str, openrouter_key: str) -> list[dict]:
    """HTML fetch + LLM extraction. Returns list of listing dicts (pre-normalize)."""
    html = load_html_cache(slug)
    if html is None:
        r = httpx.get(careers_url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
        r.raise_for_status()
        html = r.text
        save_html_cache(slug, html)

    # Strip scripts/styles to keep prompt small.
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    cleaned = soup.get_text("\n", strip=True)
    # Cap to ~30k chars for the LLM call.
    cleaned = cleaned[:30000]

    prompt = f"""You are extracting job listings from a company careers page.

Return a JSON object with this exact shape:
{{
  "jobs": [
    {{"title": "<job title>", "location": "<office or remote>", "url": "<absolute URL to the job>", "body_html": "<the full job description HTML or text if visible on this page; otherwise empty string>"}}
  ]
}}

Rules:
- Only include listings whose title plausibly matches Forward Deployed Engineer / Implementation Engineer / Deployment Engineer / Solutions Engineer / Customer Engineer (engineering IC roles, not managers).
- Include the absolute URL — if links are relative, prefix with the careers page origin.
- If the careers page only lists titles + links (not full descriptions), set body_html to "".
- Return ONLY the JSON object. No prose.

Careers page text:
{cleaned}
"""
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    r = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    # Some models wrap in ```json fences; strip.
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    parsed = json.loads(content)
    return parsed.get("jobs", [])

def normalize_custom(company: dict, raw_jobs: list[dict]) -> list[dict]:
    out = []
    for j in raw_jobs:
        out.append(make_listing_dict(
            company=company,
            title=j.get("title", "") or "",
            location=j.get("location", "") or "",
            url=j.get("url", "") or "",
            body_html=j.get("body_html", "") or "",
            posted_at=None,
            ats="custom",
            compensation_raw=extract_comp_from_html(j.get("body_html", "")),
        ))
    return out


# ---------- shared helpers ----------

def make_listing_dict(*, company, title, location, url, body_html, posted_at,
                      ats, team=None, compensation_raw="") -> dict:
    return {
        "company_name": company["name"],
        "company_slug": company["slug"],
        "company_employee_estimate": company.get("employee_estimate"),
        "title": title.strip(),
        "location": (location or "").strip(),
        "url": (url or "").strip(),
        "body_html": body_html or "",
        "posted_at": posted_at,
        "ats": ats,
        "team": team or "",
        "compensation_raw": compensation_raw or "",
    }

def extract_comp_from_html(html: str) -> str:
    """Best-effort salary extraction from job body HTML."""
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    # Common patterns: "$120,000 - $180,000", "$120K-$180K", "USD 120,000–180,000"
    pat = re.compile(
        r"\$\s?\d{2,3}[\d,.]*\s?(?:K|,000)?\s*[-–—]\s*\$?\s?\d{2,3}[\d,.]*\s?(?:K|,000)?(?:\s*USD)?",
        re.I,
    )
    m = pat.search(text)
    return m.group(0) if m else ""


def match_title(title: str) -> Optional[str]:
    t = (title or "").lower()
    if any(re.search(p, t) for p in EXCLUDE_PATTERNS):
        return None
    for pattern, label in INCLUDE_PATTERNS:
        if re.search(pattern, t):
            return label
    return None


def make_slug(text: str, max_len: int = 70) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:max_len].strip("-") or "untitled"


def listing_id(company_slug: str, title: str, location: str) -> str:
    loc_part = (location or "").split(",")[0].split(";")[0].split("|")[0].strip()
    parts = [make_slug(title, 60)]
    if loc_part:
        parts.append(make_slug(loc_part, 20))
    return f"{company_slug}__{'-'.join(p for p in parts if p)}"


def remote_flag(location: str) -> str:
    loc = (location or "").lower()
    if "remote" in loc and ("hybrid" in loc or "office" in loc):
        return "hybrid"
    if "remote" in loc:
        return "remote"
    if "hybrid" in loc:
        return "hybrid"
    return "onsite"


def html_to_md(body_html: str) -> str:
    if not body_html or not body_html.strip():
        return ""
    md = markdownify(body_html, heading_style="ATX", strip=["script", "style"])
    # Collapse 3+ blank lines to 2.
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def yaml_str(value: Any) -> str:
    """Render a value safely as a YAML scalar for inline frontmatter."""
    if value is None or value == "":
        return '""'
    s = str(value)
    if any(c in s for c in [":", "#", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`", "{", "}", "[", "]", ","]) or s.strip() != s:
        return json.dumps(s)  # JSON-safe quote
    return s


def render_markdown(listing: dict, listing_id_str: str, title_match: str) -> str:
    body_md = html_to_md(listing["body_html"]) or "_No description body available._"
    fm_lines = [
        "---",
        f"id: {yaml_str(listing_id_str)}",
        f"company: {yaml_str(listing['company_name'])}",
        f"company_slug: {yaml_str(listing['company_slug'])}",
        f"company_employee_estimate: {listing['company_employee_estimate'] or 'null'}",
        f"title: {yaml_str(listing['title'])}",
        f"title_match: {yaml_str(title_match)}",
        f"location: {yaml_str(listing['location'])}",
        f"remote: {yaml_str(remote_flag(listing['location']))}",
        f"team: {yaml_str(listing['team'])}",
        f"posted_at: {yaml_str(listing['posted_at'])}",
        f"url: {yaml_str(listing['url'])}",
        f"ats: {yaml_str(listing['ats'])}",
        f"compensation_raw: {yaml_str(listing['compensation_raw'])}",
        "---",
        "",
        f"# {listing['title']} at {listing['company_name']}",
        "",
        body_md,
        "",
    ]
    return "\n".join(fm_lines)


# ---------- selection ----------

def parse_iso_ts(s: Optional[str]) -> float:
    if not s:
        return 0.0
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0

def selection_key(listing: dict) -> tuple:
    is_fde = 0 if listing.get("title_match") == "forward-deployed" else 1
    posted = parse_iso_ts(listing.get("posted_at"))
    loc = (listing.get("location") or "").lower()
    if any(c in loc for c in ["san francisco", "sf,", "new york", "nyc", "ny,"]):
        loc_pref = 0
    elif "remote" in loc:
        loc_pref = 1
    else:
        loc_pref = 2
    return (is_fde, -posted, loc_pref, listing["title"])

def pick_top_two(matches: list[dict]) -> list[dict]:
    return sorted(matches, key=selection_key)[:2]


# ---------- main ----------

def fetch_company(company: dict, openrouter_key: str, refresh: bool) -> tuple[list[dict], Optional[str]]:
    """Returns (normalized listings, error message or None)."""
    slug = company["slug"]
    ats = company["ats"]
    try:
        if ats in ("greenhouse", "lever", "ashby"):
            cached = None if refresh else load_json_cache(slug)
            if cached is None:
                if ats == "greenhouse":
                    cached = fetch_greenhouse(company["board_id"])
                elif ats == "lever":
                    cached = fetch_lever(company["board_id"])
                else:
                    cached = fetch_ashby(company["board_id"])
                save_json_cache(slug, cached)
            if ats == "greenhouse":
                return normalize_greenhouse(company, cached), None
            if ats == "lever":
                return normalize_lever(company, cached), None
            return normalize_ashby(company, cached), None

        if ats == "custom":
            cached = None if refresh else load_json_cache(slug)
            if cached is None:
                cached = fetch_custom(company["careers_url"], slug, openrouter_key)
                save_json_cache(slug, cached)
            return normalize_custom(company, cached), None

        return [], f"unknown ats: {ats}"
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Force refetch (ignore cache).")
    args = ap.parse_args()

    companies = yaml.safe_load(COMPANIES_PATH.read_text())["companies"]
    needs_llm = any(c.get("ats") == "custom" for c in companies)
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if needs_llm and not openrouter_key:
        sys.exit(
            "ERROR: OPENROUTER_API_KEY required (companies.yaml has 'custom' ATS entries).\n"
            "  Run:  source ../KEYS  (or remove custom entries from companies.yaml)."
        )

    RAW_DIR.mkdir(exist_ok=True)
    LISTINGS_DIR.mkdir(exist_ok=True)
    # Clean old listings (deterministic re-render).
    for f in LISTINGS_DIR.glob("*.md"):
        f.unlink()

    manifest_listings: list[dict] = []
    skipped: list[dict] = []
    n_with_listings = 0

    for company in companies:
        slug = company["slug"]
        print(f"=== {company['name']} ({company['ats']}) ===")
        all_jobs, err = fetch_company(company, openrouter_key, args.refresh)
        if err:
            print(f"  fetch failed: {err}")
            skipped.append({"slug": slug, "reason": f"fetch error: {err}"})
            continue

        matched = []
        for j in all_jobs:
            label = match_title(j["title"])
            if label:
                j["title_match"] = label
                matched.append(j)
        print(f"  {len(all_jobs)} jobs, {len(matched)} match FDE-archetype")

        if not matched:
            skipped.append({"slug": slug, "reason": "no FDE-matching listings found"})
            continue

        chosen = pick_top_two(matched)
        n_with_listings += 1

        for listing in chosen:
            lid = listing_id(slug, listing["title"], listing["location"])
            md_path = LISTINGS_DIR / f"{lid}.md"
            md_path.write_text(render_markdown(listing, lid, listing["title_match"]))
            manifest_listings.append({
                "id": lid,
                "company": company["name"],
                "company_slug": slug,
                "title": listing["title"],
                "location": listing["location"],
                "remote": remote_flag(listing["location"]),
                "team": listing["team"],
                "url": listing["url"],
                "title_match": listing["title_match"],
                "ats": listing["ats"],
                "compensation_raw": listing["compensation_raw"],
                "markdown_path": f"listings/{lid}.md",
            })
            print(f"  → {lid}")

    manifest_listings.sort(key=lambda m: m["id"])
    skipped.sort(key=lambda s: s["slug"])

    manifest = {
        "metadata": {
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stage": 1,
            "model_used_for_custom_ats": OPENROUTER_MODEL,
            "total_companies_attempted": len(companies),
            "total_companies_with_listings": n_with_listings,
            "total_listings_written": len(manifest_listings),
            "total_companies_skipped": len(skipped),
        },
        "listings": manifest_listings,
        "skipped_companies": skipped,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")

    print()
    print(f"Wrote {len(manifest_listings)} listings across {n_with_listings} companies.")
    print(f"Skipped: {len(skipped)} ({', '.join(s['slug'] for s in skipped) or 'none'})")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
