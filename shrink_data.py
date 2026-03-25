import pandas as pd
import os

nodes = pd.read_csv("data/nodes.csv")
print(f"Original nodes: {len(nodes)}")

threshold = nodes["popularity"].quantile(0.95)
print(f"Popularity 25th percentile: {threshold}")

nodes_filtered = nodes[nodes["popularity"] > threshold].copy()
print(f"Nodes after filtering: {len(nodes_filtered)}")

kept_ids = set(nodes_filtered["spotify_id"])

edges = pd.read_csv("data/edges.csv")
print(f"Original edges: {len(edges)}")

edges_filtered = edges[
    edges["id_0"].isin(kept_ids) & edges["id_1"].isin(kept_ids)
].copy()
print(f"Edges after filtering: {len(edges_filtered)}")

os.makedirs("data/filtered", exist_ok=True)
nodes_filtered.to_csv("data/filtered/nodes.csv", index=False)
edges_filtered.to_csv("data/filtered/edges.csv", index=False)
print("Saved to data/filtered/")
