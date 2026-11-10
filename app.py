"""Grocery Price-Matching Dashboard.

Streamlit UI over the matcher output: see the same real-world product matched
across stores, compare prices, and spot the best deal. Run with:
    streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "matches.csv"

st.set_page_config(page_title="Grocery Price Matcher", page_icon="🛒", layout="wide")
st.title("🛒 Cross-Store Grocery Price Matcher")
st.caption(
    "Same product, different stores, different names - matched with sentence "
    "embeddings (all-MiniLM-L6-v2). Product data: OpenFoodFacts (real). "
    "Store listings & prices: simulated for this demo."
)

if not DATA.exists():
    st.error("No match output found. Run the pipeline first: "
             "python fetch_products.py && python generate_listings.py && python matcher.py")
    st.stop()

df = pd.read_csv(DATA)
matched = df[df["matched_stores"] > 1]

# ---- sidebar filters -------------------------------------------------------
st.sidebar.header("Filters")
stores = sorted(df["store"].unique())
picked = st.sidebar.multiselect("Stores", stores, default=stores)
query = st.sidebar.text_input("Search product")
min_conf = st.sidebar.slider("Min match confidence", 0.5, 1.0, 0.7, 0.01)

view = matched[matched["store"].isin(picked)]
view = view[view["match_confidence"].fillna(0) >= min_conf]
if query:
    view = view[view["listing_name"].str.contains(query, case=False, na=False)]

# ---- headline metrics ------------------------------------------------------
deals = (
    view.groupby("group_id")
    .agg(stores=("store", "nunique"), min_price=("price_usd", "min"),
         max_price=("price_usd", "max"))
    .query("stores > 1")
)
deals["save_pct"] = (1 - deals["min_price"] / deals["max_price"]) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Listings", len(df))
c2.metric("Matched products", matched["group_id"].nunique())
c3.metric("Stores", df["store"].nunique())
c4.metric("Avg potential saving", f"{deals['save_pct'].mean():.1f}%" if len(deals) else "-")

# ---- best deals ------------------------------------------------------------
st.subheader("💰 Biggest price gaps for the same product")
best = (
    view.groupby("group_id")
    .agg(example=("listing_name", "first"), stores=("store", "nunique"),
         min_price=("price_usd", "min"), max_price=("price_usd", "max"),
         confidence=("match_confidence", "mean"))
    .query("stores > 1")
    .assign(save_pct=lambda d: (1 - d["min_price"] / d["max_price"]) * 100)
    .sort_values("save_pct", ascending=False)
    .head(15)
    .round({"min_price": 2, "max_price": 2, "save_pct": 1, "confidence": 2})
)
st.dataframe(best, use_container_width=True)

# ---- per-product price comparison -----------------------------------------
st.subheader("📊 Price by store")
choices = best.index.tolist()
if choices:
    label_map = {g: best.loc[g, "example"] for g in choices}
    sel = st.selectbox("Pick a matched product", choices,
                       format_func=lambda g: label_map[g])
    sub = df[df["group_id"] == sel].sort_values("price_usd")
    st.bar_chart(sub.set_index("store")["price_usd"])
    st.caption("How each store listed this exact product (the entity-resolution problem in one table):")
    st.table(sub[["store", "listing_name", "price_usd", "match_confidence"]]
             .rename(columns={"listing_name": "raw listing name", "price_usd": "price (USD)"}))
else:
    st.info("No matched products under the current filters.")

# ---- match explorer --------------------------------------------------------
st.subheader("🔍 Match explorer")
with st.expander("Browse matched groups and their raw listing names"):
    for g, grp in view[view["matched_stores"] > 1].groupby("group_id"):
        names = " | ".join(f"{r.store}: {r.listing_name}" for r in grp.itertuples())
        st.markdown(f"**{g}** (confidence {grp['match_confidence'].mean():.2f})  \n{names}")

with st.expander("Unmatched listings (carried by one store only)"):
    st.dataframe(df[df["matched_stores"] == 1][["store", "listing_name", "price_usd"]],
                 use_container_width=True)
