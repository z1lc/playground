#!/usr/bin/env python3
"""Fetch restaurant density data from Yelp Fusion API for neighborhood comparison."""

import json
import os
import time

import httpx

YELP_API_KEY = os.environ["YELP_API_KEY"]
YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"

NEIGHBORHOODS = {
    "North Panhandle + Anza Vista": {
        "lat": 37.7760, "lng": -122.4375, "radius_m": 800, "population": 10003
    },
    "Greenwich Village": {
        "lat": 40.7335, "lng": -73.9985, "radius_m": 600, "population": 23138
    },
    "Virginia Highland + Morningside": {
        "lat": 33.7870, "lng": -84.3530, "radius_m": 1200, "population": 16090
    },
    "Mercer Island": {
        "lat": 47.5707, "lng": -122.2221, "radius_m": 2000, "population": 24467
    },
}

HEADERS = {"Authorization": f"Bearer {YELP_API_KEY}"}


def fetch_restaurants(name, config):
    """Fetch all restaurants for a neighborhood, paginating through results."""
    all_businesses = {}
    offset = 0
    total = None

    while True:
        params = {
            "latitude": config["lat"],
            "longitude": config["lng"],
            "radius": config["radius_m"],
            "categories": "restaurants",
            "limit": 50,
            "offset": offset,
            "sort_by": "best_match",
        }
        resp = httpx.get(YELP_SEARCH_URL, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if total is None:
            total = data["total"]
            print(f"  {name}: {total} total restaurants found")

        for biz in data["businesses"]:
            if not biz.get("is_closed", False):
                all_businesses[biz["id"]] = biz

        offset += 50
        # Yelp API caps offset+limit at 240
        if offset >= total or offset + 50 > 240:
            break
        time.sleep(0.5)

    return list(all_businesses.values()), total


def compute_metrics(businesses, total_from_api, population):
    """Compute density, rating, and price metrics."""
    count = len(businesses)
    restaurants_per_1k = round(total_from_api / (population / 1000), 1)

    ratings = [b["rating"] for b in businesses if b.get("rating") is not None]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

    price_map = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}
    prices = [price_map[b["price"]] for b in businesses if b.get("price") in price_map]

    if prices:
        avg_price_level = round(sum(prices) / len(prices), 1)
        dollar_2_plus = sum(1 for p in prices if p >= 2)
        pct_dollar_2_plus = round(dollar_2_plus / len(prices) * 100, 1)
    else:
        avg_price_level = None
        pct_dollar_2_plus = None

    return {
        "restaurants_per_1k": restaurants_per_1k,
        "total_restaurants": total_from_api,
        "avg_rating": avg_rating,
        "avg_price_level": avg_price_level,
        "pct_dollar_2_plus": pct_dollar_2_plus,
    }


def main():
    results = {}
    for name, config in NEIGHBORHOODS.items():
        print(f"Fetching: {name}")
        businesses, total = fetch_restaurants(name, config)
        metrics = compute_metrics(businesses, total, config["population"])
        results[name] = metrics
        print(f"  Result: {json.dumps(metrics)}")
        time.sleep(0.5)

    print("\n--- JSON for insertion into DATA ---")
    for name, metrics in results.items():
        print(f'        "restaurant_density":{json.dumps(metrics)},')


if __name__ == "__main__":
    main()
