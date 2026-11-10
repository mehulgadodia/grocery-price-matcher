"""Generate per-store listings from the canonical product catalog.

Each fictional retailer lists a subset of products with its own naming style
(abbreviations, reordered brand/size, punctuation differences) and its own
price. This mirrors the real-world problem: the same product looks different
in every store's feed, which is what the matcher has to solve.

Prices are simulated for demo purposes; product identities are real
(OpenFoodFacts). Ground-truth product ids are kept so the matcher can be
evaluated honestly.
"""
import csv
import hashlib
import json
import random
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
PRODUCTS = DATA_DIR / "products.json"
OUT = DATA_DIR / "store_listings.csv"

rng = random.Random(42)

# Base USD price bands per category keyword.
PRICE_BANDS = {
    "cereal": (2.5, 6.5), "chocolate": (1.0, 4.5), "biscuit": (1.5, 5.0),
    "drink": (1.5, 4.0), "milk": (2.0, 5.0), "pasta": (1.0, 3.5),
}
DEFAULT_BAND = (1.0, 6.0)

STORES = {
    "FreshMart": {"carry_p": 0.80, "price_factor": 1.05},
    "ValueBasket": {"carry_p": 0.75, "price_factor": 0.92},
    "DailyGrocers": {"carry_p": 0.75, "price_factor": 1.00},
}

ABBREVS = {"chocolate": "Choc", "spread": "Sprd", "original": "Orig",
           "strawberry": "Strwbry", "vanilla": "Van", "cookies": "Ckies"}


def base_price(product):
    cat = product["category"].lower()
    band = next((v for k, v in PRICE_BANDS.items() if k in cat), DEFAULT_BAND)
    seed = int(hashlib.md5(product["id"].encode()).hexdigest()[:8], 16)
    lo, hi = band
    return round(lo + (seed % 1000) / 1000 * (hi - lo), 2)


def norm_size(qty):
    m = re.match(r"(\d+)\s*g\b", qty.lower())
    if m and int(m.group(1)) >= 1000:
        return f"{int(m.group(1)) / 1000:g} kg"
    return qty


def listing_name(product, store):
    name, brand, qty = product["name"], product["brand"], product["quantity"]
    if store == "FreshMart":
        text = " ".join(x for x in [brand, name, qty] if x)
    elif store == "ValueBasket":
        words = [ABBREVS.get(w.lower(), w) for w in name.split()]
        text = " ".join(words)
        if qty:
            text += f" {qty.replace(' ', '')}"
    else:  # DailyGrocers: name - brand, normalized size
        text = name if not brand else f"{name} - {brand}"
        if qty:
            text += f", {norm_size(qty)}"
    if rng.random() < 0.15:  # occasional messy casing / punctuation
        text = text.upper() if rng.random() < 0.5 else re.sub(r"[-,]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    products = json.loads(PRODUCTS.read_text())
    rows = []
    for p in products:
        price = base_price(p)
        for store, cfg in STORES.items():
            if rng.random() > cfg["carry_p"]:
                continue
            noisy = round(price * cfg["price_factor"] * rng.uniform(0.97, 1.03), 2)
            rows.append({
                "store": store,
                "listing_name": listing_name(p, store),
                "price_usd": noisy,
                "product_id": p["id"],
                "category": p["category"],
            })
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} listings across {len(STORES)} stores -> {OUT}")


if __name__ == "__main__":
    main()
