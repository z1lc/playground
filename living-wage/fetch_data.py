# /// script
# dependencies = [
#   "requests",
#   "beautifulsoup4",
# ]
# ///
"""Fetch MIT Living Wage "Typical Expenses" tables for five locations and write data.json.

Each MIT page holds one `table.expense_table` whose rows are the expense/income
categories and whose 12 value columns are, in fixed order:
    cols 0-3  -> "1 Adult"                (0, 1, 2, 3 children)
    cols 4-7  -> "2 Adults (1 Working)"   (0, 1, 2, 3 children)
    cols 8-11 -> "2 Adults (Both Working)"(0, 1, 2, 3 children)

Run with: uv run fetch_data.py
"""

import json
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).parent
RAW_DIR = HERE / "raw_responses"
DATA_INSTANT = "2026-02-15"  # MIT "data last updated" date shown on the site

# label shown in the app -> (MIT display name, page URL, raw-cache slug)
LOCATIONS: list[tuple[str, str, str, str]] = [
    ("Atlanta", "Fulton County, GA", "https://livingwage.mit.edu/counties/13121", "13121"),
    ("Asheville", "Asheville, NC (metro)", "https://livingwage.mit.edu/metros/11700", "11700"),
    ("San Francisco", "San Francisco County, CA", "https://livingwage.mit.edu/counties/06075", "06075"),
    ("New York", "New York County, NY", "https://livingwage.mit.edu/counties/36061", "36061"),
    ("Huntsville", "Madison County, AL", "https://livingwage.mit.edu/counties/01089", "01089"),
]

HOUSEHOLDS: list[str] = ["1 Adult", "2 Adults (1 Working)", "2 Adults (Both Working)"]

# Expense category rows (the pie slices) in MIT's table order.
EXPENSE_CATEGORIES: list[str] = [
    "Food",
    "Child Care",
    "Medical",
    "Housing",
    "Transportation",
    "Civic",
    "Internet & Mobile",
    "Other",
]

# Income/tax rows -> output key.
INCOME_ROWS: dict[str, str] = {
    "Required annual income after taxes": "afterTax",
    "Annual taxes": "taxes",
    "Required annual income before taxes": "beforeTax",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) living-wage-playground/1.0"}


def get_html(url: str, slug: str) -> str:
    """Return page HTML, using a cached copy under raw_responses/ when available."""
    RAW_DIR.mkdir(exist_ok=True)
    cache = RAW_DIR / f"{slug}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text


def parse_dollars(text: str) -> Optional[int]:
    """Parse a cell like '$15,148' into 15148; return None if no number present."""
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else None


def parse_expense_table(html: str) -> dict[str, dict[str, dict[str, int]]]:
    """Parse one location's expense_table into {household: {childCount: {row: value}}}."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.expense_table")
    if table is None:
        raise ValueError("expense_table not found on page")

    # Seed the output structure: 3 households x 4 child counts.
    out: dict[str, dict[str, dict[str, int]]] = {h: {str(c): {} for c in range(4)} for h in HOUSEHOLDS}

    wanted = set(EXPENSE_CATEGORIES) | set(INCOME_ROWS)
    for tr in table.select("tbody tr"):
        label_cell = tr.find("td", class_="text")
        if label_cell is None:
            continue
        label = label_cell.get_text(strip=True).replace("\xa0", " ")
        if label not in wanted:
            continue
        value_cells = [td for td in tr.find_all("td") if td is not label_cell]
        if len(value_cells) != 12:
            raise ValueError(f"row '{label}' has {len(value_cells)} value cells, expected 12")
        key = INCOME_ROWS.get(label, label)
        for idx, cell in enumerate(value_cells):
            value = parse_dollars(cell.get_text())
            if value is None:
                raise ValueError(f"non-numeric cell in row '{label}' at column {idx}")
            household = HOUSEHOLDS[idx // 4]
            children = str(idx % 4)
            out[household][children][key] = value
    return out


def main() -> None:
    locations: dict[str, dict[str, object]] = {}
    for label, mit_name, url, slug in LOCATIONS:
        print(f"Fetching {label} ({mit_name}) ...")
        html = get_html(url, slug)
        households = parse_expense_table(html)
        locations[label] = {"mitName": mit_name, "url": url, "households": households}

    payload = {
        "meta": {
            "source": "MIT Living Wage Calculator",
            "sourceUrl": "https://livingwage.mit.edu/",
            "dataUpdated": DATA_INSTANT,
        },
        "categories": EXPENSE_CATEGORIES,
        "locations": locations,
    }
    out_path = HERE / "data.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
