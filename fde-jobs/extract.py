# /// script
# dependencies = [
#   "httpx",
# ]
# ///
"""
Stage 3 of the FDE jobs pipeline: for each listing, extract typed values for
every category in categories.json. Outputs one extracted/<id>.json per
listing plus a single data.json bundle for Stage 4.

Run:
    source ../KEYS
    uv run extract.py [--refresh] [--refresh-id <id>] [--concurrency N] [--only <glob>]

Output:
    extracted/<id>.json                          (committed)
    data.json                                    (committed bundle)
    raw_responses/extract_<id>.json              (gitignored cache)
"""

import argparse
import concurrent.futures
import fnmatch
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
CATEGORIES_PATH = SCRIPT_DIR / "categories.json"
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
LISTINGS_DIR = SCRIPT_DIR / "listings"
EXTRACTED_DIR = SCRIPT_DIR / "extracted"
DATA_PATH = SCRIPT_DIR / "data.json"
INDEX_HTML_PATH = SCRIPT_DIR / "index.html"

INDEX_DATA_BLOCK_RE = re.compile(
    r'(<script type="application/json" id="fde-data">)(.*?)(</script>)',
    re.DOTALL,
)
RAW_DIR = SCRIPT_DIR / "raw_responses"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "deepseek/deepseek-v4-pro:floor"

DEFAULT_CONCURRENCY = 25
MAX_CONCURRENCY = 25

# Bumping this version invalidates every per-listing cache, forcing a fresh
# LLM call. Bump on any prompt change.
PROMPT_VERSION = "v2-evidence"

VALID_TYPES = {"number", "string", "enum", "list[string]", "boolean"}

USER_AGENT = "fde-jobs-extractor/0.1 (rsanek@gmail.com)"


# ---------- prompts ----------

SYSTEM_PROMPT = """You are extracting structured values from a single Forward-Deployed-Engineer-archetype job listing. The schema and the listing are in the user message. Your job: for each category in the schema, return (a) a typed value for THIS listing and (b) a verbatim quote from the listing that justifies the value.

Output a SINGLE JSON object with exactly two top-level keys: `extracted` and `evidence`.

`extracted` rules:
1. Object whose keys are exactly the schema's `key` values. No extra keys.
2. Type coercion is strict — match the declared `type` exactly:
   - `boolean`: true or false. Default to false unless the listing EXPLICITLY states the condition.
   - `number`: integer or float, or null if not stated. Do not invent values.
   - `string`: a string, or null if not stated. Trim whitespace.
   - `enum`: MUST be one of the provided `enum_values` exactly, or null if no value clearly applies.
   - `list[string]`: an array of strings (possibly empty). When the description includes "You MUST only use values from this exact list: ...", items NOT in that list MUST be omitted.
3. Conservative bias: when the listing is ambiguous or doesn't say, prefer null/false/[] over guessing.

`evidence` rules — the supporting quote(s) for each classification:
4. Quotes MUST be VERBATIM substrings of the listing body. Do not paraphrase, summarize, or invent. Pick the SHORTEST sentence or fragment that justifies the classification (≤200 characters preferred). If no clear sentence supports the classification, use null.
5. Shape per category type:
   - `list[string]`: object whose keys are EXACTLY the values in the corresponding `extracted` array. Each value is the verbatim quote justifying THAT specific tag (or null). E.g., extracted=["agent_development","pre_sales"] → evidence={"agent_development":"...","pre_sales":"..."}.
   - `enum`: a single string (the quote justifying the chosen enum value), or null. If extracted is null, evidence is null.
   - `boolean`: a single string when extracted is true, or null. Omit (or null) when extracted is false.
   - `number` / `string`: a single string quote, or null.
6. Only include evidence keys for the schema's category keys. No extras.

Output ONLY the JSON object. No prose, no markdown fences."""

USER_PROMPT_TEMPLATE = """# Schema

{schema_json}

# Listing

{listing_md}

# Task

Return a single JSON object with `extracted` and `evidence` per the system rules. The body of the listing is the source of truth for both the typed values and the verbatim quotes.
"""


# ---------- hashing / cache ----------

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def cache_key(model: str, categories_text: str, listing_text: str) -> str:
    h = hashlib.sha256()
    h.update(f"prompt_version={PROMPT_VERSION}\n".encode())
    h.update(f"model={model}\n".encode())
    h.update(b"--- categories ---\n")
    h.update(categories_text.encode())
    h.update(b"\n--- listing ---\n")
    h.update(listing_text.encode())
    return h.hexdigest()


def cache_path(listing_id: str) -> Path:
    return RAW_DIR / f"extract_{listing_id}.json"

def load_cache(listing_id: str, expected_key: str) -> dict | None:
    p = cache_path(listing_id)
    if not p.exists():
        return None
    try:
        cached = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    if cached.get("cache_key") != expected_key:
        return None
    return cached

def save_cache(listing_id: str, cache_key_str: str, raw_content: str, parsed: dict, extracted_at: str) -> None:
    cache_path(listing_id).write_text(json.dumps({
        "cache_key": cache_key_str,
        "extracted_at": extracted_at,
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
            "User-Agent": USER_AGENT,
        },
        json=payload,
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def parse_llm_json(content: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(cleaned)


# ---------- value validation ----------

def controlled_vocab_from_description(desc: str) -> list[str] | None:
    """If the description includes 'You MUST only use values from this exact
    list: 'foo', 'bar', ...', return [foo, bar, ...]. Otherwise None."""
    m = re.search(r"only use values from this exact list:\s*(.+?)(?:\.\s|\.$|\n)", desc, re.IGNORECASE | re.DOTALL)
    if not m:
        # Try alternate phrasings the model sometimes uses.
        m = re.search(r"allowed values?:\s*(.+?)(?:\.\s|\.$|\n)", desc, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    items = re.findall(r"['\"]([^'\"]+)['\"]", raw)
    return items or None


def validate_value(value: Any, category: dict, warnings: list[str]) -> Any:
    key = category["key"]
    ctype = category["type"]

    if ctype == "boolean":
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        warnings.append(f"{key}: expected boolean, got {type(value).__name__} ({value!r}); coerced to false")
        return False

    if ctype == "number":
        if value is None:
            return None
        if isinstance(value, bool):  # bool is a subclass of int in Python; reject
            warnings.append(f"{key}: got boolean, expected number; coerced to null")
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                return float(value) if "." in value else int(value)
            except ValueError:
                pass
        warnings.append(f"{key}: expected number, got {type(value).__name__}; coerced to null")
        return None

    if ctype == "string":
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        warnings.append(f"{key}: expected string, got {type(value).__name__}; coerced to null")
        return None

    if ctype == "enum":
        allowed = list(category.get("enum_values") or [])
        if value is None:
            return None
        if isinstance(value, str) and value in allowed:
            return value
        warnings.append(f"{key}: value {value!r} not in enum {allowed}; coerced to null")
        return None

    if ctype == "list[string]":
        vocab = controlled_vocab_from_description(category.get("description", ""))
        if value is None:
            return []
        if not isinstance(value, list):
            warnings.append(f"{key}: expected list, got {type(value).__name__}; coerced to []")
            return []
        out: list[str] = []
        for item in value:
            if not isinstance(item, str):
                warnings.append(f"{key}: dropped non-string item {item!r}")
                continue
            item = item.strip()
            if vocab and item not in vocab:
                warnings.append(f"{key}: dropped {item!r} (not in controlled vocab)")
                continue
            if item not in out:  # dedupe
                out.append(item)
        return out

    warnings.append(f"{key}: unknown type {ctype}")
    return None


def validate_extraction(
    parsed: dict, categories: list[dict], listing_md: str | None = None,
) -> tuple[dict, dict, list[str]]:
    """Returns (extracted, evidence, warnings)."""
    warnings: list[str] = []
    extracted_out: dict[str, Any] = {}

    if not isinstance(parsed, dict):
        return (
            {c["key"]: type_default(c) for c in categories},
            {},
            [f"top-level: expected JSON object, got {type(parsed).__name__}"],
        )

    # The new prompt returns {"extracted": ..., "evidence": ...}. For
    # backward-compat with old responses, fall back to treating the whole
    # parsed dict as `extracted` if those wrapper keys aren't present.
    if "extracted" in parsed and isinstance(parsed["extracted"], dict):
        extracted_raw = parsed["extracted"]
        evidence_raw = parsed.get("evidence") if isinstance(parsed.get("evidence"), dict) else {}
    else:
        extracted_raw = parsed
        evidence_raw = {}

    schema_keys = {c["key"] for c in categories}
    for c in categories:
        if c["key"] in extracted_raw:
            extracted_out[c["key"]] = validate_value(extracted_raw[c["key"]], c, warnings)
        else:
            warnings.append(f"{c['key']}: missing from extracted, using default")
            extracted_out[c["key"]] = type_default(c)

    extra = set(extracted_raw.keys()) - schema_keys
    if extra:
        warnings.append(f"dropped {len(extra)} extra extracted keys: {sorted(extra)}")

    evidence_out = validate_evidence(evidence_raw, extracted_out, categories, listing_md, warnings)
    return extracted_out, evidence_out, warnings


def validate_evidence(
    raw: dict, extracted: dict, categories: list[dict],
    listing_md: str | None, warnings: list[str],
) -> dict:
    """Validate the evidence shape against extracted values + schema.

    Returns a dict whose keys are category keys.
    - For list[string] cats: value is a dict {tag: quote_or_null}
    - For enum cats with non-null extracted: value is a quote string or null.
    - For boolean cats with extracted=true: value is a quote string or null.
    - Otherwise: omitted.
    """
    if not isinstance(raw, dict):
        if raw is not None:
            warnings.append(f"evidence: expected object, got {type(raw).__name__}; ignoring")
        raw = {}

    schema_by_key = {c["key"]: c for c in categories}
    out: dict[str, Any] = {}

    # Whitespace-tolerant substring check for verbatim quotes.
    body_norm = _normalize_for_match(listing_md or "")

    def check_quote(key: str, q: Any) -> str | None:
        if q is None:
            return None
        if not isinstance(q, str):
            warnings.append(f"evidence[{key}]: expected string, got {type(q).__name__}")
            return None
        q = q.strip()
        if not q:
            return None
        if listing_md and _normalize_for_match(q) not in body_norm:
            warnings.append(f"evidence[{key}]: quote not found verbatim in listing body")
        return q

    for key, val in extracted.items():
        cat = schema_by_key.get(key)
        if cat is None:
            continue
        ctype = cat["type"]
        ev = raw.get(key)

        if ctype == "list[string]":
            sub: dict[str, str | None] = {}
            tags = val or []
            if isinstance(ev, dict):
                for tag in tags:
                    sub[tag] = check_quote(f"{key}.{tag}", ev.get(tag))
                extras = set(ev.keys()) - set(tags)
                if extras:
                    warnings.append(f"evidence[{key}]: dropped extra tag keys {sorted(extras)}")
            else:
                for tag in tags:
                    sub[tag] = None
                if ev is not None:
                    warnings.append(f"evidence[{key}]: expected object, got {type(ev).__name__}")
            if sub:
                out[key] = sub

        elif ctype == "enum":
            if val is None:
                continue
            out[key] = check_quote(key, ev)

        elif ctype == "boolean":
            if val is True:
                out[key] = check_quote(key, ev)

        else:  # number, string
            if val is not None and val != "":
                out[key] = check_quote(key, ev)

    extras = set(raw.keys()) - {c["key"] for c in categories}
    if extras:
        warnings.append(f"evidence: dropped extra keys not in schema: {sorted(extras)}")

    return out


def _normalize_for_match(s: str) -> str:
    """Collapse whitespace + lowercase for verbatim substring checks."""
    return re.sub(r"\s+", " ", s).strip().lower()


def type_default(category: dict) -> Any:
    ctype = category["type"]
    if ctype == "boolean":
        return False
    if ctype == "list[string]":
        return []
    return None


# ---------- per-listing extraction ----------

def build_user_prompt(categories: list[dict], listing_md: str) -> str:
    schema_blob = json.dumps(categories, indent=2)
    return USER_PROMPT_TEMPLATE.format(schema_json=schema_blob, listing_md=listing_md.strip())


def extract_one(
    listing_id: str,
    listing_md: str,
    categories: list[dict],
    categories_text: str,
    api_key: str,
    refresh: bool,
) -> tuple[dict, bool]:
    """Returns (extracted/<id>.json blob, used_cache)."""
    listing_hash = sha256_text(listing_md)
    categories_hash = sha256_text(categories_text)
    ck = cache_key(OPENROUTER_MODEL, categories_text, listing_md)

    cached = None if refresh else load_cache(listing_id, ck)
    if cached is not None:
        parsed = cached["parsed"]
        # Reuse the original extraction timestamp so cache-hit re-runs are
        # byte-identical. Fall back to "now" for legacy caches without it.
        extracted_at = cached.get("extracted_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")
        used_cache = True
    else:
        used_cache = False
        extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            raw_content = _call_with_retry(
                SYSTEM_PROMPT, build_user_prompt(categories, listing_md), api_key
            )
            parsed = parse_llm_json(raw_content)
        except Exception as e:
            return {
                "id": listing_id,
                "extracted": None,
                "evidence": {},
                "extraction_metadata": {
                    "model": OPENROUTER_MODEL,
                    "extracted_at": extracted_at,
                    "error": f"{type(e).__name__}: {e}",
                    "categories_hash": categories_hash,
                    "listing_hash": listing_hash,
                },
            }, False
        save_cache(listing_id, ck, raw_content, parsed, extracted_at)

    extracted, evidence, warnings = validate_extraction(parsed, categories, listing_md)

    return {
        "id": listing_id,
        "extracted": extracted,
        "evidence": evidence,
        "extraction_metadata": {
            "model": OPENROUTER_MODEL,
            "extracted_at": extracted_at,
            "categories_hash": categories_hash,
            "listing_hash": listing_hash,
            "validation_warnings": warnings,
        },
    }, used_cache


def _call_with_retry(system_msg: str, user_msg: str, api_key: str) -> str:
    """Single retry on transient failures."""
    try:
        return call_openrouter(system_msg, user_msg, api_key)
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        time.sleep(5)
        return call_openrouter(system_msg, user_msg, api_key)


# ---------- main ----------

def load_categories() -> tuple[list[dict], str]:
    if not CATEGORIES_PATH.exists():
        sys.exit(f"ERROR: {CATEGORIES_PATH} not found. Run categorize.py first.")
    text = CATEGORIES_PATH.read_text()
    cats = json.loads(text)["categories"]
    if not cats:
        sys.exit("ERROR: categories.json has no categories.")
    return cats, text


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        sys.exit(f"ERROR: {MANIFEST_PATH} not found. Run fetch_listings.py first.")
    return json.loads(MANIFEST_PATH.read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="Force re-extract all listings.")
    ap.add_argument("--refresh-id", action="append", default=[],
                    help="Force re-extract for this listing id (repeatable).")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                    help=f"Concurrent LLM calls (default {DEFAULT_CONCURRENCY}, max {MAX_CONCURRENCY}).")
    ap.add_argument("--only", default="",
                    help="Glob filter on listing id (e.g., 'anthropic*'). Default: all.")
    args = ap.parse_args()

    if not (1 <= args.concurrency <= MAX_CONCURRENCY):
        sys.exit(f"ERROR: --concurrency must be in [1, {MAX_CONCURRENCY}]")

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY required. Run: source ../KEYS")

    categories, categories_text = load_categories()
    manifest = load_manifest()
    RAW_DIR.mkdir(exist_ok=True)
    EXTRACTED_DIR.mkdir(exist_ok=True)

    # Filter listings.
    all_listings = manifest["listings"]
    if args.only:
        all_listings = [l for l in all_listings if fnmatch.fnmatch(l["id"], args.only)]
        if not all_listings:
            sys.exit(f"ERROR: --only {args.only!r} matched no listings.")

    refresh_ids = set(args.refresh_id)
    print(f"Stage 3: extracting {len(all_listings)} listings × {len(categories)} categories.")
    print(f"Model: {OPENROUTER_MODEL}, concurrency: {args.concurrency}")

    # Read all listing markdown into memory once.
    listing_md_by_id: dict[str, str] = {}
    for entry in all_listings:
        path = SCRIPT_DIR / entry["markdown_path"]
        if not path.exists():
            print(f"  WARN: missing {path}", file=sys.stderr)
            continue
        listing_md_by_id[entry["id"]] = path.read_text()

    def task(entry: dict) -> dict:
        lid = entry["id"]
        md = listing_md_by_id[lid]
        force = args.refresh or lid in refresh_ids
        result, used_cache = extract_one(lid, md, categories, categories_text, api_key, force)
        marker = "💾" if used_cache else ("❌" if result["extracted"] is None else "✓")
        nwarn = len(result["extraction_metadata"].get("validation_warnings", []) or [])
        warn_str = f" ({nwarn} warn)" if nwarn else ""
        print(f"  {marker} {lid}{warn_str}")
        return result

    results: list[dict] = []
    if args.concurrency == 1:
        for entry in all_listings:
            results.append(task(entry))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(task, entry): entry["id"] for entry in all_listings}
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

    # Write per-listing files (sorted for determinism).
    results.sort(key=lambda r: r["id"])
    for r in results:
        (EXTRACTED_DIR / f"{r['id']}.json").write_text(json.dumps(r, indent=2) + "\n")

    # If --only filter was applied, also load the rest of the previously-extracted
    # listings so data.json stays complete.
    by_id: dict[str, dict] = {r["id"]: r for r in results}
    for entry in manifest["listings"]:
        if entry["id"] in by_id:
            continue
        prior = EXTRACTED_DIR / f"{entry['id']}.json"
        if prior.exists():
            by_id[entry["id"]] = json.loads(prior.read_text())

    # Build data.json bundle.
    n_failed = sum(1 for r in by_id.values() if r["extracted"] is None)
    bundle_listings = []
    for entry in sorted(manifest["listings"], key=lambda e: e["id"]):
        extracted_blob = by_id.get(entry["id"])
        bundle_listings.append({
            **entry,
            "extracted": extracted_blob["extracted"] if extracted_blob else None,
            "evidence": (extracted_blob.get("evidence") if extracted_blob else {}) or {},
            "extraction_warnings": (
                (extracted_blob.get("extraction_metadata") or {}).get("validation_warnings", [])
                if extracted_blob else []
            ),
        })

    bundle = {
        "metadata": {
            "stage1_fetched_at": manifest.get("metadata", {}).get("fetched_at"),
            "stage2_generated_at": json.loads(categories_text).get("metadata", {}).get("generated_at"),
            "stage3_extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stage3_model": OPENROUTER_MODEL,
            "n_listings": len(bundle_listings),
            "n_listings_with_extraction": sum(1 for b in bundle_listings if b["extracted"] is not None),
            "n_listings_failed": n_failed,
        },
        "categories": categories,
        "listings": bundle_listings,
    }
    DATA_PATH.write_text(json.dumps(bundle, indent=2) + "\n")
    inject_data_into_index_html(bundle)

    n_warn_total = sum(len(b["extraction_warnings"]) for b in bundle_listings)
    print()
    print(f"Wrote {len(results)} extracted/*.json files.")
    print(f"Wrote data.json: {len(bundle_listings)} listings, "
          f"{bundle['metadata']['n_listings_with_extraction']} extracted, "
          f"{n_failed} failed, {n_warn_total} validation warnings.")
    print(f"Updated index.html inline data block.")


def inject_data_into_index_html(bundle: dict) -> None:
    """Replace the <script type='application/json' id='fde-data'> block in
    index.html with the freshly-built bundle so the page works on file://.
    """
    if not INDEX_HTML_PATH.exists():
        return
    html = INDEX_HTML_PATH.read_text()
    # Compact JSON; escape `</` to `<\/` so the JSON can't terminate the
    # surrounding <script> tag prematurely.
    payload = json.dumps(bundle, separators=(",", ":")).replace("</", r"<\/")
    new_html, n = INDEX_DATA_BLOCK_RE.subn(
        lambda m: m.group(1) + payload + m.group(3), html, count=1
    )
    if n == 0:
        print("WARN: index.html has no <script id='fde-data'> placeholder; data not injected.")
        return
    if new_html != html:
        INDEX_HTML_PATH.write_text(new_html)


if __name__ == "__main__":
    main()
