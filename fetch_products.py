"""Fetch real grocery product data from OpenFoodFacts (free, no API key).

Pulls products from a few everyday categories and saves a clean catalog to
products.json. If the network is unavailable, falls back to the bundled
sample_products.json so the demo always runs.

OpenFoodFacts data is licensed under ODbL: https://world.openfoodfacts.org
"""
import json
import shutil
import sys
import time
from pathlib import Path

import requests

HEADERS = {"User-Agent": "grocery-price-matcher-demo/1.0 (student demo project)"}

DATA_DIR = Path(__file__).resolve().parent
OUT = DATA_DIR / "products.json"
SAMPLE = DATA_DIR / "sample_products.json"

CATEGORIES = ["breakfast-cereals", "chocolates", "biscuits", "plant-based-drinks", "pastas"]
PER_CATEGORY = 25
FIELDS = "code,product_name,brands,quantity,categories_tags"


def clean(products):
    catalog, seen = [], set()
    for p in products:
        name = (p.get("product_name") or "").strip()
        brand = (p.get("brands") or "").split(",")[0].strip()
        qty = (p.get("quantity") or "").strip()
        if not name or len(name) < 3 or name.lower() in seen:
            continue
        seen.add(name.lower())
        catalog.append({
            "id": p.get("code") or f"off-{len(catalog)}",
            "name": name,
            "brand": brand,
            "quantity": qty,
            "category": (p.get("categories_tags") or ["en:unknown"])[0].replace("en:", ""),
        })
    return catalog


def fetch():
    products = []
    for cat in CATEGORIES:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {"action": "process", "tagtype_0": "categories", "tag_contains_0": "contains",
                  "tag_0": cat, "json": 1, "page_size": PER_CATEGORY, "fields": FIELDS}
        for attempt in range(4):
            try:
                r = requests.get(url, headers=HEADERS, params=params, timeout=20)
                r.raise_for_status()
                products.extend(r.json().get("products", []))
                break
            except requests.RequestException:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))  # the free API rate-limits; back off
        time.sleep(2)  # be polite to the free API
    return clean(products)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    try:
        catalog = fetch()
        if len(catalog) < 30:
            raise RuntimeError(f"only {len(catalog)} usable products")
        OUT.write_text(json.dumps(catalog, indent=2))
        print(f"Fetched {len(catalog)} real products from OpenFoodFacts -> {OUT}")
        # Refresh the bundled offline fallback too.
        shutil.copy(OUT, SAMPLE)
    except Exception as e:  # noqa: BLE001 - any failure falls back to bundled data
        if SAMPLE.exists():
            shutil.copy(SAMPLE, OUT)
            print(f"Live fetch failed ({e}); using bundled sample -> {OUT}")
        else:
            sys.exit(f"Fetch failed and no bundled sample found: {e}")


if __name__ == "__main__":
    main()
