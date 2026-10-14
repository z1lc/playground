# /// script
# dependencies = [
#   "requests",
# ]
# ///
"""Snapshot prediction-market odds for the Georgia 2026 ballot guide into markets.json.

Each contest is charted as the chance that the candidate listed FIRST on the ballot wins
(or that an amendment passes). Prices from each platform are normalized as a / (a + b) so
the two sides always sum to 100%.

Re-run any time before Election Day to refresh:  uv run ga-ballot-2026/build_markets.py
"""

import datetime as dt
import json
from pathlib import Path
from typing import Any

import requests

OUT = Path(__file__).with_name("markets.json")
START = dt.date(2026, 6, 17)  # day after the primary runoffs, once every matchup was set
THIN_USD = 1000  # real-money markets below this volume are flagged thin
THIN_TRADERS = 10  # play-money markets with fewer unique traders are flagged thin
UA = {"User-Agent": "ga-ballot-2026 (playground static site build)"}

# a = first-listed on the ballot, b = the other side. Values are platform-specific selectors.
CONTESTS: dict[str, dict[str, Any]] = {
    "senate": {
        "a": "Mike Collins",
        "b": "Jon Ossoff",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "georgia-senate-election-winner",
                "a": "Mike Collins",
                "b": "Jon Ossoff",
            },
            {"platform": "kalshi", "series": "SENATEGA", "a": "SENATEGA-26-R", "b": "SENATEGA-26-D"},
            {"platform": "manifold", "id": "cOqt565CRZ", "a": "Republican", "b": "Democratic"},
        ],
    },
    "governor": {
        "a": "Rick Jackson",
        "b": "Keisha Lance Bottoms",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "georgia-governor-winner-2026",
                "a": "Rick Jackson",
                "b": "Keisha Lance",
            },
            {"platform": "kalshi", "series": "GOVPARTYGA", "a": "GOVPARTYGA-26-R", "b": "GOVPARTYGA-26-D"},
            {"platform": "manifold", "id": "JCkqQkGivcOi59ArT0BY", "a": "Republican Party", "b": "Democratic Party"},
        ],
    },
    "lt-governor": {
        "a": "Greg Dolezal",
        "b": "Josh McLaurin",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "georgia-lieutenant-governor-election-winner-2026",
                "a": "Greg Dolezal",
                "b": "Josh McLaurin",
            },
            {"platform": "kalshi", "series": "KXLTGOVGA", "a": "KXLTGOVGA-26-GOP", "b": "KXLTGOVGA-26-DEM"},
        ],
    },
    "secretary-of-state": {
        "a": "Tim Fleming",
        "b": "Penny Brown Reynolds",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "georgia-secretary-of-state-election-winner-2026",
                "a": "Tim Fleming",
                "b": "Penny Brown Reynolds",
            },
            {"platform": "kalshi", "series": "KXSECSTATEGA", "a": "KXSECSTATEGA-26-R", "b": "KXSECSTATEGA-26-D"},
        ],
    },
    "attorney-general": {
        "a": "Brian Strickland",
        "b": "Tanya Miller",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "georgia-attorney-general-election-winner-2026",
                "a": "Brian Strickland",
                "b": "Tanya Miller",
            },
            {"platform": "kalshi", "series": "KXATTYGENGA", "a": "KXATTYGENGA-26-R", "b": "KXATTYGENGA-26-D"},
        ],
    },
    "agriculture": {
        "a": "Tyler Harper",
        "b": "Katherine E. Juhan-Arnold",
        "sources": [
            {
                "platform": "kalshi",
                "series": "KXGAAGRICOMM",
                "a": "KXGAAGRICOMM-26NOV03-THAR",
                "b": "KXGAAGRICOMM-26NOV03-KJUA",
            },
        ],
    },
    "fulton-chair": {
        "a": "Eric J. Tatum",
        "b": "Mo Ivory",
        "sources": [
            {
                "platform": "polymarket",
                "slug": "2026-fulton-county-commission-chair-election-winner-20260626005048754",
                "a": "Eric J. Tatum",
                "b": "Mo Ivory",
            },
        ],
    },
    # Kalshi numbers the measures differently from the ballot: its A2 is the 9-1-1 fund and its A3 is probate judges.
    # Single yes/no markets have no "b" side; their price is already the chance of passing.
    "amendment-1": {
        "a": "Yes",
        "b": "No",
        "sources": [
            {"platform": "kalshi", "series": "KXSTATEBALLOTMEASURE", "a": "KXSTATEBALLOTMEASURE-GA-A1"},
            {"platform": "manifold", "id": "Nnp6hlL0t5"},
        ],
    },
    "amendment-2": {
        "a": "Yes",
        "b": "No",
        "sources": [
            {"platform": "kalshi", "series": "KXSTATEBALLOTMEASURE", "a": "KXSTATEBALLOTMEASURE-GA-A3"},
            {"platform": "manifold", "id": "ggAlhyq98h"},
        ],
    },
    "amendment-3": {
        "a": "Yes",
        "b": "No",
        "sources": [
            {"platform": "kalshi", "series": "KXSTATEBALLOTMEASURE", "a": "KXSTATEBALLOTMEASURE-GA-A2"},
            {"platform": "manifold", "id": "R9cQcUsQtE"},
        ],
    },
}


def get(url: str, params: dict[str, Any] | None = None) -> Any:
    r = requests.get(url, params=params, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()


def day(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.UTC).date().isoformat()


def days_since_start() -> list[str]:
    today = dt.datetime.now(dt.UTC).date()
    return [(START + dt.timedelta(n)).isoformat() for n in range((today - START).days + 1)]


def normalize(a: dict[str, float], b: dict[str, float] | None = None) -> list[list[Any]]:
    """Join two daily price maps on date and return [[date, a / (a + b)], ...] from START onward."""
    if b is None:
        return [[d, round(a[d], 4)] for d in sorted(a) if d >= START.isoformat()]
    out = []
    for d in sorted(set(a) & set(b)):
        if d < START.isoformat() or a[d] + b[d] <= 0:
            continue
        out.append([d, round(a[d] / (a[d] + b[d]), 4)])
    return out


def polymarket(src: dict[str, Any]) -> dict[str, Any]:
    event = get("https://gamma-api.polymarket.com/events", {"slug": src["slug"]})[0]
    sides: dict[str, dict[str, float]] = {}
    for key in ("a", "b"):
        market = next(m for m in event["markets"] if (m.get("groupItemTitle") or "").startswith(src[key]))
        token = json.loads(market["clobTokenIds"])[0]
        hist = get("https://clob.polymarket.com/prices-history", {"market": token, "interval": "max", "fidelity": 1440})
        sides[key] = {
            day(p["t"]): float(p["p"]) for p in hist["history"]
        }  # later points overwrite earlier same-day ones
    volume = float(event.get("volume") or 0)
    return {
        "platform": "Polymarket",
        "url": f"https://polymarket.com/event/{src['slug']}",
        "volume": round(volume),
        "unit": "USD traded",
        "thin": volume < THIN_USD,
        "points": normalize(sides["a"], sides["b"]),
    }


def kalshi(src: dict[str, Any]) -> dict[str, Any]:
    start_ts = int(dt.datetime.combine(START, dt.time(), dt.UTC).timestamp())
    end_ts = int(dt.datetime.now(dt.UTC).timestamp())
    sides: dict[str, dict[str, float]] = {}
    volume = 0.0
    for key in [k for k in ("a", "b") if k in src]:
        ticker = src[key]
        volume += float(get(f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}")["market"]["volume_fp"])
        candles = get(
            f"https://api.elections.kalshi.com/trade-api/v2/series/{src['series']}/markets/{ticker}/candlesticks",
            {"start_ts": start_ts, "end_ts": end_ts, "period_interval": 1440},
        )["candlesticks"]
        series: dict[str, float] = {}
        for c in candles:
            price = c["price"].get("close_dollars")
            if price is None:  # no trade that day: fall back to the bid/ask midpoint
                bid, ask = c["yes_bid"].get("close_dollars"), c["yes_ask"].get("close_dollars")
                if bid is None or ask is None:
                    continue
                price = (float(bid) + float(ask)) / 2
            # end_period_ts is midnight UTC closing the day, so step back one second to label the day it covers
            series[day(c["end_period_ts"] - 1)] = float(price)
        sides[key] = series
    event_ticker = src["a"].rsplit("-", 1)[0]
    return {
        "platform": "Kalshi",
        "url": f"https://kalshi.com/markets/{src['series'].lower()}/{event_ticker.lower()}",
        "volume": round(volume),
        "unit": "contracts traded",
        "thin": volume < THIN_USD,
        "points": normalize(sides["a"], sides.get("b")),
    }


def manifold(src: dict[str, Any]) -> dict[str, Any]:
    market = get(f"https://api.manifold.markets/v0/market/{src['id']}")
    bets: list[dict[str, Any]] = []
    before = None
    while True:
        page = get("https://api.manifold.markets/v0/bets", {"contractId": src["id"], "limit": 1000, "before": before})
        bets += page
        if len(page) < 1000:
            break
        before = page[-1]["id"]
    bets.sort(key=lambda b: b["createdTime"])

    if market["outcomeType"] == "BINARY":
        answer_ids = {"a": None, "b": None}
    else:
        by_text = {a["text"]: a["id"] for a in market["answers"]}
        answer_ids = {"a": by_text[src["a"]], "b": by_text[src["b"]]}

    # walk bets in time order, carrying each answer's latest probability forward day by day
    current: dict[str | None, float] = {}
    eod: dict[str, dict[str | None, float]] = {}
    for b in bets:
        current[b.get("answerId")] = b["probAfter"]
        eod[day(b["createdTime"] / 1000)] = dict(current)
    points = []
    last: dict[str | None, float] = {}
    for d in days_since_start():
        if d in eod:
            last = eod[d]
        elif not last:  # seed with the most recent state before START
            prior = [k for k in eod if k < d]
            last = eod[max(prior)] if prior else {}
        if market["outcomeType"] == "BINARY":
            if None in last:
                points.append([d, round(last[None], 4)])
        elif answer_ids["a"] in last and answer_ids["b"] in last:
            pa, pb = last[answer_ids["a"]], last[answer_ids["b"]]
            if pa + pb > 0:
                points.append([d, round(pa / (pa + pb), 4)])
    traders = int(market.get("uniqueBettorCount") or 0)
    return {
        "platform": "Manifold",
        "url": market["url"],
        "volume": round(float(market.get("volume") or 0)),
        "unit": "play-money mana",
        "traders": traders,
        "thin": traders < THIN_TRADERS,
        "points": points,
    }


FETCHERS = {"polymarket": polymarket, "kalshi": kalshi, "manifold": manifold}


def main() -> None:
    out: dict[str, Any] = {"asOf": dt.datetime.now(dt.UTC).isoformat(timespec="minutes"), "contests": {}}
    for cid, cfg in CONTESTS.items():
        series = []
        for src in cfg["sources"]:
            try:
                s = FETCHERS[src["platform"]](src)
            except Exception as e:  # one dead market shouldn't sink the whole snapshot
                print(f"  ! {cid} {src['platform']}: {e}")
                continue
            if s["points"]:
                s["latest"] = s["points"][-1][1]
                series.append(s)
            print(f"{cid:20} {s['platform']:10} {len(s['points']):4} pts  latest={s.get('latest')}  thin={s['thin']}")
        out["contests"][cid] = {"a": cfg["a"], "b": cfg["b"], "series": series}
    OUT.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
