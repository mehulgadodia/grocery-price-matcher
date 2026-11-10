# 🛒 Cross-Store Grocery Price Matcher

The same grocery product shows up with a different name in every store's feed:
"Nutella Hazelnut Spread 400g" here, "NUTELLA HAZELNUT SPRD 400 g" there.
Matching those listings is the unglamorous core of grocery pricing and
merchandising analytics - and it is exactly what this mini project does.

**Pipeline:** real product data from [OpenFoodFacts](https://world.openfoodfacts.org)
(free, no API key) → simulated multi-store listings with messy naming →
embedding-based entity resolution with
[SentenceTransformers](https://sbert.net) (`all-MiniLM-L6-v2`) →
a Streamlit dashboard for price comparison and best-deal discovery.

## Why this exists

Built as a hands-on demo of the product-matching problem grocery-pricing
platforms (like BetterBasket) solve at scale: entity resolution across
retailers, then price comparison on top of the matched catalog.

## Quickstart

```bash
pip install -r requirements.txt

python fetch_products.py       # real products from OpenFoodFacts (offline fallback included)
python generate_listings.py    # simulate 3 stores with messy listing names + prices
python matcher.py              # embedding matching + precision/recall report
streamlit run app.py               # dashboard on http://localhost:8501
```

## What's real and what's simulated

- **Real:** the product catalog (names, brands, sizes, categories) from
  OpenFoodFacts, and the matching pipeline itself.
- **Simulated:** the three fictional stores and their prices. OpenFoodFacts
  has no reliable per-store pricing, so listings are generated with
  store-specific naming styles and price jitter. Ground-truth product ids are
  kept, which lets `matcher.py` report honest **pairwise precision/recall**
  for the entity resolution.

## How matching works

1. Every listing's name is encoded with `all-MiniLM-L6-v2`.
2. Candidate pairs are cross-store listings with cosine similarity ≥ 0.75.
3. Greedy average-linkage clustering merges groups only when their average
   pairwise similarity clears the threshold and the merge keeps at most one
   listing per store (this structure constraint avoids the classic union-find
   chaining failure, where one bridge link merges whole categories).
4. On the bundled data this scores pairwise precision 0.995 / recall 0.972.
5. The dashboard compares prices within each group and surfaces the biggest
   gaps (i.e. where a shopper overpays).

## Dashboard features

- Headline stats: listings, matched products, average potential saving
- "Biggest price gaps" table across stores
- Per-product price-by-store chart with the raw listing names each store used
- Match explorer (raw names per group) and unmatched-listing view
- Filters: store, free-text search, minimum match confidence

## Extending this

- Swap simulated listings for real retailer feeds/scrapes (Scrapy/Playwright)
- Add an LLM verification pass on borderline candidate pairs
- Weight matching by pack size / unit price normalization
- Incremental matching against a persistent vector store (e.g. ChromaDB)

## Data & licenses

Product data © OpenFoodFacts contributors, available under the ODbL.
No credentials or API keys are used anywhere in this project.
