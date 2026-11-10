"""Match the same product across stores with sentence embeddings.

Encodes every listing's name with a SentenceTransformers model, then clusters
cross-store listings with greedy average-linkage agglomeration:
merge two groups only when their average pairwise cosine similarity clears the
threshold AND the merge keeps at most one listing per store. That structure
constraint stops the "chaining" failure of naive union-find, where one bridge
link merges whole categories.

Because generated listings carry ground-truth product ids, the script reports
pairwise precision/recall so matching quality is measurable, not vibes.
"""
import itertools
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent
LISTINGS = DATA_DIR / "store_listings.csv"
OUT = DATA_DIR / "matches.csv"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
THRESHOLD = 0.75


def cluster(sim, stores, threshold):
    """Greedy average-linkage clustering over cross-store candidate pairs."""
    n = sim.shape[0]
    groups = [{i} for i in range(n)]
    gid = list(range(n))

    def avg_sim(a, b):
        return float(np.mean([sim[i, j] for i in a for j in b]))

    candidates = sorted(
        ((sim[i, j], i, j) for i, j in itertools.combinations(range(n), 2)
         if stores[i] != stores[j] and sim[i, j] >= threshold),
        reverse=True,
    )
    for _, i, j in candidates:
        gi, gj = gid[i], gid[j]
        if gi == gj:
            continue
        a, b = groups[gi], groups[gj]
        if {stores[x] for x in a} & {stores[x] for x in b}:
            continue  # keep at most one listing per store per group
        if avg_sim(a, b) >= threshold:
            groups[gi] = a | b
            groups[gj] = set()
            for x in a | b:
                gid[x] = gi
    return [g for g in groups if g]


def pairwise_pr(groups, truth):
    """Precision/recall over predicted vs true listing pairs."""
    def pairs(member_sets):
        out = set()
        for members in member_sets:
            out.update(tuple(sorted(p))
                       for p in itertools.combinations(sorted(members), 2))
        return out

    true_groups = defaultdict(set)
    for idx, t in enumerate(truth):
        true_groups[t].add(idx)
    pred = pairs([g for g in groups if len(g) > 1])
    true = pairs(list(true_groups.values()))
    tp = len(pred & true)
    return (tp / len(pred) if pred else 0.0, tp / len(true) if true else 0.0)


def main():
    df = pd.read_csv(LISTINGS)
    model = SentenceTransformer(MODEL_NAME)
    emb = model.encode(df["listing_name"].tolist(),
                       normalize_embeddings=True, show_progress_bar=False)
    sim = emb @ emb.T

    groups = cluster(sim, df["store"].tolist(), THRESHOLD)
    precision, recall = pairwise_pr(groups, df["product_id"].tolist())

    group_of = {}
    for k, g in enumerate(groups):
        for i in g:
            group_of[i] = k
    df["group_id"] = [f"prod-{group_of[i]:04d}" for i in range(len(df))]

    # Confidence = mean similarity of a listing to the rest of its group.
    conf = []
    for i in range(len(df)):
        peers = groups[group_of[i]] - {i}
        conf.append(round(float(np.mean([sim[i, j] for j in peers])), 3) if peers else np.nan)
    df["match_confidence"] = conf
    df["matched_stores"] = df["group_id"].map(df.groupby("group_id")["store"].nunique())
    df.to_csv(OUT, index=False)

    matched = df[df["matched_stores"] > 1].groupby("group_id").ngroups
    print(f"Listings: {len(df)} | matched product groups: {matched} | threshold: {THRESHOLD}")
    print(f"Pairwise precision: {precision:.3f} | recall: {recall:.3f}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
