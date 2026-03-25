from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

import networkx as nx
import pandas as pd
from pyvis.network import Network


DEFAULT_NODE_SIZE = 14
HIGHLIGHT_NODE_SIZE = 26
MAX_LABEL_LEN = 22


def load_data(nodes_path: str = "data/nodes.csv", edges_path: str = "data/edges.csv") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load nodes and edges data, normalizing IDs to strings."""
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)

    nodes_df["spotify_id"] = nodes_df["spotify_id"].astype(str)
    edges_df["id_0"] = edges_df["id_0"].astype(str)
    edges_df["id_1"] = edges_df["id_1"].astype(str)

    return nodes_df, edges_df


def get_initial_node_ids(nodes_df: pd.DataFrame, total: int = 20, step: int = 10) -> List[str]:
    """Pick the initial set: every nth artist from popularity-sorted list."""
    ranked = (
        nodes_df[["spotify_id", "popularity"]]
        .sort_values("popularity", ascending=False)
        .drop_duplicates("spotify_id")
        .reset_index(drop=True)
    )
    picked = ranked.iloc[::step].head(total)
    return picked["spotify_id"].astype(str).tolist()


def build_shown_graph(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, shown_ids: Iterable[str]) -> nx.Graph:
    """Build a graph using only currently shown IDs and the edges between them."""
    shown_set: Set[str] = set(str(s) for s in shown_ids)
    g = nx.Graph()

    if not shown_set:
        return g

    shown_nodes = nodes_df[nodes_df["spotify_id"].isin(shown_set)].copy()
    for _, row in shown_nodes.iterrows():
        g.add_node(
            row["spotify_id"],
            name=row.get("name", "Unknown"),
            followers=float(row.get("followers", 0) if pd.notna(row.get("followers", 0)) else 0),
            popularity=int(row.get("popularity", 0) if pd.notna(row.get("popularity", 0)) else 0),
            genres=str(row.get("genres", "")),
            chart_hits=str(row.get("chart_hits", "")),
        )

    shown_edges = edges_df[
        edges_df["id_0"].isin(shown_set) & edges_df["id_1"].isin(shown_set)
    ]
    for _, row in shown_edges.iterrows():
        if row["id_0"] != row["id_1"]:
            g.add_edge(row["id_0"], row["id_1"])

    return g


def detect_communities(g: nx.Graph) -> Dict[str, int]:
    """Detect communities on the shown graph only."""
    if g.number_of_nodes() == 0:
        return {}

    if g.number_of_edges() == 0:
        return {n: idx for idx, n in enumerate(g.nodes())}

    try:
        communities = nx.community.louvain_communities(g, seed=42)
    except Exception:
        communities = list(nx.community.greedy_modularity_communities(g))

    partition: Dict[str, int] = {}
    for cid, members in enumerate(communities):
        for node in members:
            partition[str(node)] = cid
    return partition


def compute_global_stats(g: nx.Graph) -> Dict[str, float | int | str]:
    """Compute stats for the shown graph only."""
    n = g.number_of_nodes()
    m = g.number_of_edges()

    if n == 0:
        return {
            "nodes": 0,
            "edges": 0,
            "density": 0.0,
            "avg_degree": 0.0,
            "components": 0,
            "largest_component": 0,
            "top_degree": "",
        }

    components = list(nx.connected_components(g))
    degree_sorted = sorted(g.degree(), key=lambda x: x[1], reverse=True)[:5]
    top_degree = ", ".join([f"{g.nodes[nid].get('name', nid)} ({deg})" for nid, deg in degree_sorted])

    return {
        "nodes": n,
        "edges": m,
        "density": nx.density(g),
        "avg_degree": (2 * m) / n if n else 0.0,
        "components": len(components),
        "largest_component": max(len(c) for c in components) if components else 0,
        "top_degree": top_degree,
    }


def compute_node_stats(g: nx.Graph, node_id: str, partition: Dict[str, int]) -> Dict[str, float | int | str]:
    """Compute node-level metrics using only the shown graph."""
    node_id = str(node_id)
    if node_id not in g:
        return {}

    if g.number_of_nodes() <= 1:
        betweenness = 0.0
        closeness = 0.0
    else:
        betweenness = nx.betweenness_centrality(g).get(node_id, 0.0)
        closeness = nx.closeness_centrality(g).get(node_id, 0.0)

    attrs = g.nodes[node_id]
    return {
        "id": node_id,
        "name": attrs.get("name", node_id),
        "degree": int(g.degree(node_id)),
        "degree_centrality": nx.degree_centrality(g).get(node_id, 0.0),
        "betweenness": betweenness,
        "closeness": closeness,
        "clustering": nx.clustering(g, node_id) if g.number_of_edges() else 0.0,
        "community": partition.get(node_id, -1),
        "popularity": attrs.get("popularity", 0),
        "followers": attrs.get("followers", 0),
        "genres": attrs.get("genres", ""),
        "chart_hits": attrs.get("chart_hits", ""),
    }


def remove_node_with_report(g: nx.Graph, node_id: str) -> Dict[str, Dict[str, float | int | str]]:
    """Remove a node and return before/after graph stats."""
    before = compute_global_stats(g)
    updated = g.copy()

    if node_id in updated:
        updated.remove_node(node_id)

    after = compute_global_stats(updated)
    return {"before": before, "after": after}


def _truncate(text: str, size: int = MAX_LABEL_LEN) -> str:
    return text if len(text) <= size else text[: size - 1] + "…"


def _palette() -> List[str]:
    return [
        "#ff6b6b",
        "#4ecdc4",
        "#1a535c",
        "#ff9f1c",
        "#2ec4b6",
        "#e71d36",
        "#011627",
        "#6a4c93",
        "#1982c4",
        "#8ac926",
    ]


def build_pyvis_html(
    g: nx.Graph,
    partition: Dict[str, int],
    selected_node: str | None = None,
    height_px: int = 650,
) -> str:
    """Render shown graph as Pyvis HTML."""
    net = Network(height=f"{height_px}px", width="100%", bgcolor="#f8fbff", font_color="#1b1f23")
    net.barnes_hut(gravity=-8500, central_gravity=0.25, spring_length=120, spring_strength=0.01, damping=0.9)

    colors = _palette()

    for node_id, attrs in g.nodes(data=True):
        community = partition.get(node_id, 0)
        color = colors[community % len(colors)]
        degree = g.degree(node_id)
        size = DEFAULT_NODE_SIZE + min(24, degree * 2)

        if selected_node and str(selected_node) == str(node_id):
            size = max(size, HIGHLIGHT_NODE_SIZE)

        title = (
            f"<b>{attrs.get('name', node_id)}</b><br>"
            f"ID: {node_id}<br>"
            f"Popularity: {attrs.get('popularity', 0)}<br>"
            f"Followers: {int(attrs.get('followers', 0))}<br>"
            f"Degree (shown graph): {degree}<br>"
            f"Community: {community}<br>"
            f"Genres: {attrs.get('genres', '')}<br>"
            f"Chart hits: {attrs.get('chart_hits', '')}"
        )

        net.add_node(
            node_id,
            label=_truncate(str(attrs.get("name", node_id))),
            title=title,
            color=color,
            size=size,
            borderWidth=2,
        )

    for source, target in g.edges():
        net.add_edge(source, target, color="#97a6b2")

    net.set_options(
        """
        {
          "interaction": {
            "hover": true,
            "multiselect": false,
            "navigationButtons": true,
            "tooltipDelay": 120
          },
          "physics": {
            "enabled": true,
            "barnesHut": {
              "gravitationalConstant": -8500,
              "springLength": 120,
              "springConstant": 0.01,
              "damping": 0.9
            },
            "stabilization": {
              "enabled": true,
              "iterations": 700,
              "updateInterval": 25
            }
          }
        }
        """
    )
    return net.generate_html(notebook=False)


def get_addable_artists(nodes_df: pd.DataFrame, shown_ids: Iterable[str]) -> pd.DataFrame:
    shown_set = set(str(x) for x in shown_ids)
    addable = nodes_df[~nodes_df["spotify_id"].astype(str).isin(shown_set)].copy()
    addable = addable.sort_values(["popularity", "followers"], ascending=[False, False])
    return addable
