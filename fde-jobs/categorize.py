# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""
Stage 2 of the FDE jobs pipeline: read all listings produced by Stage 1 and
ask an LLM to identify ~15 useful comparison categories. Output is the
schema Stage 3 will use to extract per-listing values.

Run:
    source ../KEYS
    uv run categorize.py [--refresh] [--max-categories N] [--hint "..."]

Output:
    categories.json                              (committed)
    raw_responses/categorize_response.json       (gitignored cache)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
LISTINGS_DIR = SCRIPT_DIR / "listings"
CATEGORIES_PATH = SCRIPT_DIR / "categories.json"
RAW_DIR = SCRIPT_DIR / "raw_responses"
CACHE_PATH = RAW_DIR / "categorize_response.json"

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-3.1-pro-preview"

# Soft cap on booleans. Booleans are the weakest comparison type — list[string],
# enum, and number all carry more signal. Validator warns (does not drop) above this.
SOFT_BOOLEAN_BUDGET = 3

VALID_TYPES = {"number", "string", "enum", "list[string]", "boolean"}
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

# Frontmatter keys that are already structured — categories should not duplicate them
# (though structured derivations like comp_min_usd from compensation_raw ARE allowed).
RESERVED_FRONTMATTER_KEYS = {
    "id", "company", "company_slug", "title", "title_match",
    "location", "remote", "url", "ats", "posted_at", "team",
    "compensation_raw", "company_employee_estimate",
}


# ---------- prompt assembly ----------

SYSTEM_PROMPT_TEMPLATE = """You are designing a comparison schema for a corpus of "Forward Deployed Engineer"-archetype job listings from prestigious smaller (<1k employees) tech companies. The schema will be used downstream to extract structured values from each listing and render a side-by-side comparison.

The single most important property of a good schema here: **the categories must DIFFERENTIATE listings from each other**. Categories that describe what every FDE role has in common (good communication, AI/ML exposure, production experience, etc.) carry zero comparison signal. Your job is to find the dimensions on which these roles actually differ.

# Hard rules

1. **DIFFERENTIATION (top priority).** A category is forbidden if you predict its value would be the same for ≥80% of the listings — even if the description is technically accurate. Drop it and find something more discriminating.

2. **Lead with `required_skill_areas` (list[string]).** This category is mandatory and central. It captures specific technical skill domains the role demands — what *actually* differs between an FDE at a model lab vs. an FDE at a fintech vs. an infrastructure deployment role. Pick a controlled vocabulary of ~10–20 specific skill tags drawn from what appears across the corpus, in lowercase snake_case. Examples of good values: `networking`, `kubernetes`, `gpu_programming`, `llm_inference`, `model_training`, `distributed_systems`, `data_engineering`, `frontend`, `mobile`, `security`, `compliance`, `physical_infrastructure`, `databases`, `observability`, `prompt_engineering`, `agent_development`, `pre_sales`, `government_clearance`. Each role should plausibly receive 2–5 tags.

3. **Boolean budget: AT MOST {soft_boolean_budget} booleans across the entire output.** Booleans are the weakest comparison type. Use `enum`, `number`, or `list[string]` whenever possible. Each boolean you do include must split the corpus non-trivially (not 0/26 or 26/0).

4. **Anti-redundancy.** If you propose a `list[string]` (e.g., `programming_languages`, `required_skill_areas`), do NOT also propose per-item booleans for any of its members (e.g., no `python_required`, `kubernetes_required`).

5. **Forbidden generic axes.** Do NOT propose any of these — they were tried before and are weak:
   - `min_years_experience`, `required_years_experience` — too noisy, often unstated, and similar roles ask for similar ranges.
   - `comp_min_usd`, `comp_max_usd`, or any compensation number — most listings don't publish, currencies vary, the dollar amount is not what makes a role interesting.
   - `requires_strong_communication`, `production_shipping_required`, `ai_ml_required`, `equity_offered`, `requires_python` — baseline expectations or redundant; not differentiators.

6. **Output budget.** AT MOST {max_categories} categories. Aim for {target_low}–{target_high}. Quality over quantity.

7. **Frontmatter is off-limits as a verbatim category** (already structured): company, company_slug, title, title_match, location, remote, url, ats, posted_at, team, compensation_raw, company_employee_estimate. Structured *derivations* are fine (e.g., `seniority_level` from title) when they add real comparability.

8. **Description must be SELF-CONTAINED.** A different LLM in Stage 3 will read your description verbatim to extract values from a single listing with no other context. Be precise about what counts and what doesn't. State explicitly when to use null/empty.

9. **Identifiers.** `key` is snake_case, ≤40 chars, lowercase letters/digits/underscores, unique.

# Self-check before answering

For each candidate category, mentally simulate its values across the 26 listings:
- If a boolean would be ≥80% one value: replace it.
- If an enum has one value taking ≥80%: refine the enum or drop the category.
- If a number is unstated in ≥50% of listings: drop it.
- If a list[string] would have <5 distinct values total across the corpus: it's not a useful axis.

Output ONLY the final, post-self-check set. Do not include reasoning.

# Worked examples

GOOD:
- `required_skill_areas` (list[string]) — values like `["networking","kubernetes","gpu_programming"]`. Each role gets 2–5; the corpus exhibits ~15 distinct values total. High signal.
- `customer_engagement_depth` (enum: `deep_embed` / `regular_touch` / `light_advisory`) — splits FDE roles meaningfully; some embed for months, others advise lightly.
- `industry_focus` (enum: `ai_labs` / `enterprise_saas` / `fintech` / `infrastructure` / `government`) — actually varies across the corpus.

BAD (do not propose):
- `min_years_experience` (number) — banned per rule 5.
- `comp_min_usd` (number) — banned per rule 5.
- `requires_strong_communication` (boolean) — ~100% true.
- `python_required` (boolean) when `programming_languages` (list[string]) exists — redundant per rule 4.
- `ai_ml_required` (boolean) — most FDE roles touch AI/ML; near-universal.

# Output format

Return a single JSON object with this exact shape (no prose, no markdown fences):

{{
  "categories": [
    {{
      "key": "<snake_case identifier>",
      "name": "<short human label>",
      "description": "<1-2 sentences directing Stage 3 extraction>",
      "type": "<number | string | enum | list[string] | boolean>",
      "unit": "<optional, only for type=number>",
      "enum_values": ["<required iff type=enum>"],
      "examples": [<1-3 sample values matching the declared type>]
    }}
  ]
}}{hint_section}"""

HINT_SECTION_TEMPLATE = "\n\nADDITIONAL STEERING (provided by user, treat as soft guidance):\n{hint}"


def build_user_message(listings_md: list[tuple[str, str]]) -> str:
    parts = [
        f"Here are {len(listings_md)} job listings. Each is wrapped in <<<LISTING id=...>>> ... <<</LISTING>>> markers. The block before the first heading is YAML frontmatter; everything after is the description body.",
        "",
    ]
    for lid, content in listings_md:
        parts.append(f"<<<LISTING id={lid}>>>")
        parts.append(content.rstrip())
        parts.append("<<</LISTING>>>")
        parts.append("")
    return "\n".join(parts)


# ---------- caching ----------

def listings_input_hash(listings_md: list[tuple[str, str]], max_categories: int, hint: str) -> str:
    h = hashlib.sha256()
    h.update(f"max_categories={max_categories}\n".encode())
    h.update(f"hint={hint or ''}\n".encode())
    h.update(f"model={OPENROUTER_MODEL}\n".encode())
    for lid, content in sorted(listings_md):
        h.update(f"=== {lid} ===\n".encode())
        h.update(content.encode())
    return h.hexdigest()


def load_cache(input_hash: str) -> dict | None:
    if not CACHE_PATH.exists():
        return None
    age = time.time() - CACHE_PATH.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        return None
    try:
        cached = json.loads(CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return None
    if cached.get("input_hash") != input_hash:
        return None
    return cached


def save_cache(input_hash: str, raw_content: str, parsed: dict) -> None:
    CACHE_PATH.write_text(json.dumps({
        "input_hash": input_hash,
        "model": OPENROUTER_MODEL,
        "raw_content": raw_content,
        "parsed": parsed,
    }, indent=2))


# ---------- LLM call ----------

def call_openrouter(system_msg: str, user_msg: str, api_key: str) -> str:
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "response_format": {"type": "json_object"},
    }
    r = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def parse_llm_json(content: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(cleaned)


# ---------- validation ----------

def validate_categories(raw: list[dict], max_cats: int) -> tuple[list[dict], list[str]]:
    """Return (kept, error_messages). Drops invalid categories, keeps the rest."""
    kept: list[dict] = []
    errors: list[str] = []
    seen_keys: set[str] = set()

    for i, c in enumerate(raw):
        prefix = f"category[{i}]"
        if not isinstance(c, dict):
            errors.append(f"{prefix}: not a JSON object")
            continue
        key = c.get("key")
        name = c.get("name")
        desc = c.get("description")
        ctype = c.get("type")

        if not isinstance(key, str) or not KEY_RE.match(key):
            errors.append(f"{prefix} key={key!r}: must be snake_case, ≤40 chars, lowercase-letters/digits/underscores")
            continue
        if key in seen_keys:
            errors.append(f"{prefix} key={key!r}: duplicate")
            continue
        if key in RESERVED_FRONTMATTER_KEYS:
            errors.append(f"{prefix} key={key!r}: collides with reserved frontmatter key")
            continue
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix} key={key}: name must be a non-empty string")
            continue
        if not isinstance(desc, str) or len(desc.strip()) < 20:
            errors.append(f"{prefix} key={key}: description too short or missing (need ≥20 chars)")
            continue
        if ctype not in VALID_TYPES:
            errors.append(f"{prefix} key={key}: invalid type {ctype!r} (allowed: {sorted(VALID_TYPES)})")
            continue
        if ctype == "enum":
            ev = c.get("enum_values")
            if not isinstance(ev, list) or not ev or not all(isinstance(v, str) for v in ev):
                errors.append(f"{prefix} key={key}: enum requires non-empty enum_values list of strings")
                continue

        # Normalize the kept entry — only well-known fields, in stable order.
        out: dict[str, Any] = {
            "key": key,
            "name": name.strip(),
            "description": desc.strip(),
            "type": ctype,
        }
        if ctype == "number" and isinstance(c.get("unit"), str) and c["unit"].strip():
            out["unit"] = c["unit"].strip()
        if ctype == "enum":
            out["enum_values"] = list(c["enum_values"])
        if isinstance(c.get("examples"), list) and c["examples"]:
            out["examples"] = c["examples"]

        kept.append(out)
        seen_keys.add(key)

    if len(kept) > max_cats:
        errors.append(f"LLM returned {len(kept)} valid categories, truncating to max_categories={max_cats}")
        kept = kept[:max_cats]

    return kept, errors


# ---------- main ----------

def load_listings() -> list[tuple[str, str]]:
    if not MANIFEST_PATH.exists():
        sys.exit(f"ERROR: {MANIFEST_PATH} not found. Run fetch_listings.py first.")
    manifest = json.loads(MANIFEST_PATH.read_text())
    out: list[tuple[str, str]] = []
    for entry in manifest["listings"]:
        path = SCRIPT_DIR / entry["markdown_path"]
        if not path.exists():
            print(f"  WARN: missing {path}", file=sys.stderr)
            continue
        out.append((entry["id"], path.read_text()))
    out.sort(key=lambda x: x[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Force re-run the LLM call.")
    ap.add_argument("--max-categories", type=int, default=15,
                    help="Hard upper bound on number of categories (default 15).")
    ap.add_argument("--hint", default="", help="Optional steering text added to the system prompt.")
    args = ap.parse_args()

    if not (1 <= args.max_categories <= 25):
        sys.exit("ERROR: --max-categories must be in [1, 25]")

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY required. Run: source ../KEYS")

    RAW_DIR.mkdir(exist_ok=True)
    listings_md = load_listings()
    if not listings_md:
        sys.exit("ERROR: no listings to categorize.")
    print(f"Loaded {len(listings_md)} listings.")

    input_hash = listings_input_hash(listings_md, args.max_categories, args.hint)

    cached = None if args.refresh else load_cache(input_hash)
    if cached:
        print("Cache hit — reusing previous LLM response.")
        raw_content = cached["raw_content"]
        parsed = cached["parsed"]
    else:
        if CACHE_PATH.exists() and not args.refresh:
            print("Cache stale (input changed or TTL expired) — calling LLM.")
        else:
            print("Calling LLM (this may take 30–90s)...")
        target_low = max(1, args.max_categories - 3)
        target_high = args.max_categories
        system_msg = SYSTEM_PROMPT_TEMPLATE.format(
            max_categories=args.max_categories,
            target_low=target_low,
            target_high=target_high,
            soft_boolean_budget=SOFT_BOOLEAN_BUDGET,
            hint_section=HINT_SECTION_TEMPLATE.format(hint=args.hint) if args.hint else "",
        )
        user_msg = build_user_message(listings_md)
        raw_content = call_openrouter(system_msg, user_msg, api_key)
        parsed = parse_llm_json(raw_content)
        save_cache(input_hash, raw_content, parsed)

    raw_categories = parsed.get("categories", [])
    if not isinstance(raw_categories, list):
        sys.exit(f"ERROR: LLM response 'categories' is not a list: {type(raw_categories).__name__}")

    kept, errors = validate_categories(raw_categories, args.max_categories)
    for e in errors:
        print(f"  validation: {e}")

    if not kept:
        sys.exit("ERROR: no valid categories after validation.")

    n_bool = sum(1 for c in kept if c["type"] == "boolean")
    quality_warnings: list[str] = []
    if n_bool > SOFT_BOOLEAN_BUDGET:
        quality_warnings.append(
            f"boolean count {n_bool} exceeds soft budget {SOFT_BOOLEAN_BUDGET} — "
            "consider re-running with --refresh, or hand-edit categories.json"
        )
    has_skill_axis = any(
        c["type"] == "list[string]" and "skill" in c["key"] for c in kept
    )
    if not has_skill_axis:
        quality_warnings.append(
            "no list[string] skill axis found (expected `required_skill_areas` or similar)"
        )

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": OPENROUTER_MODEL,
            "n_listings_seen": len(listings_md),
            "max_categories": args.max_categories,
            "hint": args.hint or None,
            "n_categories_generated": len(raw_categories),
            "n_categories_kept": len(kept),
            "n_validation_errors": len(errors),
            "n_booleans": n_bool,
            "input_hash": input_hash,
        },
        "categories": kept,
    }
    CATEGORIES_PATH.write_text(json.dumps(output, indent=2) + "\n")

    print()
    print(f"Wrote {len(kept)} categories to {CATEGORIES_PATH.name}.")
    print(f"  by type: " + ", ".join(
        f"{t}={sum(1 for c in kept if c['type'] == t)}"
        for t in sorted(VALID_TYPES) if any(c["type"] == t for c in kept)
    ))
    for w in quality_warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    main()
