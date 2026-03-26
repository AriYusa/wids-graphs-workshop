from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Set, Tuple

import networkx as nx
import pandas as pd
from pyvis.network import Network

from unique_genre import parse_raw_genres


DEFAULT_NODE_SIZE = 8
HIGHLIGHT_NODE_SIZE = 16
MAX_LABEL_LEN = 22


def load_data(nodes_path: str = "data/nodes.csv", edges_path: str = "data/edges.csv") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load nodes and edges data, normalizing IDs to strings."""
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)

    nodes_df["spotify_id"] = nodes_df["spotify_id"].astype(str)
    edges_df["id_0"] = edges_df["id_0"].astype(str)
    edges_df["id_1"] = edges_df["id_1"].astype(str)

    nodes_df["simplified_genres"] = nodes_df["simplified_genres"].apply(parse_raw_genres)

    return nodes_df, edges_df


INITIAL_ARTIST_IDS: List[str] = [
    "6eUKZXaKkcviH0Ku9w2n3V",  # Ed Sheeran
    "4q3ewBCX7sLwd24euuV69X",  # Bad Bunny
    "5cj0lLjcoR7YOSnhnX0Po5",  # Doja Cat
    "6ZLTlhejhndI4Rh53vYhrY",  # Ozzy Osbourne
    "246dkjvS1zLTtiykXe5h60",  # Post Malone
    "0Y5tJX1MQlPlqiwlOH1tJY",  # Travis Scott
    "3TVXtAsR1Inumwj472S9r4",  # Drake
    "7CajNmpbOovFoOoasH2HaY",  # Calvin Harris
    # "1Xyo4u8uXC1ZmMpatF05PJ",  # The Weeknd
    "2h93pZq0e7k5yf4dywlkpM",  # Frank Ocean
    "0YC192cP3KPCRWx8zr8MfZ",  # Hans Zimmer
    "1YZhNFBxkEB5UKTgMDvot4",  # Lang Lang
    "7dGJo4pcD2V6oG8kP0tJRR",  # Eminem
    "3PhoLpVuITZKcymswpck5b",  # Elton John
    "1HY2Jd0NmPuamShAr6KMms",  # Lady Gaga
    "2lolQgalUvZDfp5vvVtTYV",  # Tony Bennett
    "0du5cEVh5yTK9QJze8zA0C",  # Bruno Mars
    "5M52tdBnJaKSvOpJGz8mfZ",  # Black Sabbath
    "41MozSoPIsD1dJM0CLPjZF",  # BLACKPINK
]


def get_initial_node_ids(nodes_df: pd.DataFrame, **_kwargs) -> List[str]:
    """Return the curated starting artist IDs that exist in the dataset."""
    available = set(nodes_df["spotify_id"].astype(str))
    return [nid for nid in INITIAL_ARTIST_IDS if nid in available]


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
            main_genre=str(row.get("main_genre", "Other")),
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


def _followers_size(followers: float, min_size: int = 5, max_size: int = 22, ceiling: float = 60_000_000) -> int:
    normalized = min(max(0.0, followers) / ceiling, 1.0)
    return int(min_size + normalized * (max_size - min_size))


GENRE_COLORS: Dict[str, str] = {
    "Pop":        "#f21821",
    "Hip-Hop":    "#cdde25",
    "Rock":       "#fa931a",
    "Metal":      "#bf168d",
    "Electronic": "#01295F",
    "Classical":  "#8f59a7",
    "Country":    "#f8631f",
    "R&B":        "#931D1D",
    "Reggae":     "#F799A7",
    "Latin":      "#6363E6",
    "Folk":       "#FFFA69",
    "Jazz":       "#63AF34",
    "Blues":      "#7EB2DD",
    "Other":      "#E7F0FF", 
}


def _genre_color(main_genre: str) -> str:
    return GENRE_COLORS.get(main_genre, GENRE_COLORS["Other"])


def build_pyvis_html(
    g: nx.Graph,
    partition: Dict[str, int],
    selected_node: str | None = None,
    height_px: int = 650,
) -> str:
    """Render shown graph as Pyvis HTML."""
    net = Network(height=f"{height_px}px", width="100%", bgcolor="#f8fbff", font_color="#1b1f23")
    net.barnes_hut(gravity=-8500, central_gravity=0.25, spring_length=120, spring_strength=0.01, damping=0.9)

    for node_id, attrs in g.nodes(data=True):
        color = _genre_color(attrs.get("main_genre", "Other"))
        degree = g.degree(node_id)
        size = _followers_size(attrs.get("followers", 0))

        if selected_node and str(selected_node) == str(node_id):
            size = max(size, HIGHLIGHT_NODE_SIZE)

        title = (
            f"<b>{attrs.get('name', node_id)}</b><br>"
            f"ID: {node_id}<br>"
            f"Followers: {int(attrs.get('followers', 0))}<br>"
            f"Main Genre: {attrs.get('main_genre', 'Other')}"
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
    addable = addable.sort_values(["followers"], ascending=[False])
    return addable


def _full_layout(g: nx.Graph, scale: float = 600.0) -> Dict[str, Tuple[float, float]]:
    """Fresh spring layout for all nodes, packing disconnected components compactly."""
    components = sorted(nx.connected_components(g), key=len, reverse=True)
    if len(components) == 1:
        pos = nx.spring_layout(g, seed=42, scale=scale, iterations=80)
        return {str(nid): (float(xy[0]), float(xy[1])) for nid, xy in pos.items()}

    comp_layouts: list[dict] = []
    for comp in components:
        sub = g.subgraph(comp)
        comp_scale = scale * math.sqrt(len(comp) / g.number_of_nodes())
        comp_scale = max(comp_scale, 80.0)
        if len(comp) == 1:
            (node,) = comp
            sub_pos = {node: (0.0, 0.0)}
        else:
            sub_pos = nx.spring_layout(sub, seed=42, scale=comp_scale, iterations=80)
        comp_layouts.append(sub_pos)

    n_cols = max(1, math.ceil(math.sqrt(len(comp_layouts))))
    gap = scale * 0.35
    boxes = []
    for sub_pos in comp_layouts:
        xs = [xy[0] for xy in sub_pos.values()]
        ys = [xy[1] for xy in sub_pos.values()]
        boxes.append((min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))

    final_pos: Dict[str, Tuple[float, float]] = {}
    x_cursor = 0.0
    y_cursor = 0.0
    max_row_h = 0.0
    for i, (sub_pos, (bx, by, bw, bh)) in enumerate(zip(comp_layouts, boxes)):
        if i % n_cols == 0 and i > 0:
            y_cursor += max_row_h + gap
            x_cursor = 0.0
            max_row_h = 0.0
        for nid, (x, y) in sub_pos.items():
            final_pos[str(nid)] = (float(x - bx + x_cursor), float(y - by + y_cursor))
        x_cursor += bw + gap
        max_row_h = max(max_row_h, bh)

    return final_pos


def _compute_layout(
    g: nx.Graph,
    existing_positions: Dict[str, Tuple[float, float]] | None = None,
    scale: float = 600.0,
) -> Dict[str, Tuple[float, float]]:
    """Return {node_id: (x, y)}, reusing existing_positions where available.

    Nodes already in existing_positions keep their coordinates so the graph
    doesn't jump when a node is added or removed.  New nodes are placed near
    the centroid of their already-positioned neighbors, or in empty space when
    they have no such neighbors.
    """
    if g.number_of_nodes() == 0:
        return {}

    existing_positions = existing_positions or {}
    node_ids = {str(n) for n in g.nodes()}

    # Keep only positions that still belong to the current graph.
    fixed: Dict[str, Tuple[float, float]] = {
        nid: pos for nid, pos in existing_positions.items() if nid in node_ids
    }
    new_nodes = [nid for nid in node_ids if nid not in fixed]

    if not new_nodes:
        return dict(fixed)

    if not fixed:
        return _full_layout(g, scale)

    # Bounding box of existing positions — used to park isolated new nodes.
    all_xs = [x for x, _ in fixed.values()]
    all_ys = [y for _, y in fixed.values()]
    park_x = max(all_xs) + scale * 0.4
    park_y = (min(all_ys) + max(all_ys)) / 2.0
    park_step = scale * 0.15

    result = dict(fixed)
    isolated_count = 0
    for nid in new_nodes:
        neighbor_pos = [fixed[str(nb)] for nb in g.neighbors(nid) if str(nb) in fixed]
        if neighbor_pos:
            cx = sum(x for x, _ in neighbor_pos) / len(neighbor_pos)
            cy = sum(y for _, y in neighbor_pos) / len(neighbor_pos)
            rng = random.Random(nid)
            offset = scale * 0.08
            result[nid] = (
                cx + rng.uniform(-offset, offset),
                cy + rng.uniform(-offset, offset),
            )
        else:
            result[nid] = (park_x, park_y + isolated_count * park_step)
            isolated_count += 1

    return result


def build_agraph_payload(
    g: nx.Graph,
    partition: Dict[str, int],
    existing_positions: Dict[str, Tuple[float, float]] | None = None,
    newly_added_id: str | None = None,
    selected_node_id: str | None = None,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, Tuple[float, float]]]:
    """Convert shown graph to streamlit-agraph payload dictionaries.

    Returns (nodes, edges, positions) where positions should be stored in
    session_state and passed back on the next call to keep the layout stable.
    """
    nodes: List[Dict[str, object]] = []
    edges: List[Dict[str, object]] = []

    layout = _compute_layout(g, existing_positions=existing_positions)

    for node_id, attrs in g.nodes(data=True):
        size = _followers_size(attrs.get("followers", 0))

        title = (
            f"{attrs.get('name', node_id)}\n"
            f"Main Genre: {attrs.get('main_genre', 'Other')}\n"
            f"Followers: {int(attrs.get('followers', 0))}\n"
        )

        x, y = layout.get(str(node_id), (0, 0))
        node_dict: Dict[str, object] = {
            "id": str(node_id),
            "label": _truncate(str(attrs.get("name", node_id))),
            "title": title,
            "size": size,
            "color": _genre_color(attrs.get("main_genre", "Other")),
            "shape": "dot",
            "font": {"size": 18},
            "x": x,
            "y": y,
        }

        nodes.append(node_dict)

    for source, target in g.edges():
        edges.append({"source": str(source), "target": str(target), "color": "#97a6b2"})

    return nodes, edges, layout
