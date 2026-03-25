from __future__ import annotations

import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

from graph_utils import (
    build_agraph_payload,
    build_shown_graph,
    compute_global_stats,
    compute_node_stats,
    detect_communities,
    get_addable_artists,
    get_initial_node_ids,
    load_data,
    remove_node_with_report,
)


st.set_page_config(
    page_title="Learning To See Data - Spotify Network",
    page_icon="🎵",
    layout="wide",
)


@st.cache_data
def get_data():
    return load_data("data/nodes.csv", "data/edges.csv")


def build_state():
    nodes_df, _ = get_data()

    if "shown_node_ids" not in st.session_state:
        st.session_state.shown_node_ids = set(get_initial_node_ids(nodes_df, total=20, step=5))

    if "selected_node_id" not in st.session_state:
        st.session_state.selected_node_id = None


def render_global_stats(stats):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Shown Nodes", stats["nodes"])
    c2.metric("Shown Edges", stats["edges"])
    c3.metric("Density", f"{stats['density']:.4f}")
    c4.metric("Avg Degree", f"{stats['avg_degree']:.2f}")
    c5.metric("Components", stats["components"])
    c6.metric("Largest Component", stats["largest_component"])


def render_node_stats(node_stats):
    if not node_stats:
        st.info("Choose a node in the sidebar to inspect node-level metrics.")
        return

    st.subheader(f"Node Stats: {node_stats['name']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Degree", node_stats["degree"])
    c2.metric("Degree Centrality", f"{node_stats['degree_centrality']:.4f}")
    c3.metric("Betweenness", f"{node_stats['betweenness']:.4f}")
    c4.metric("Closeness", f"{node_stats['closeness']:.4f}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Clustering Coef", f"{node_stats['clustering']:.4f}")
    c6.metric("Community", node_stats["community"])
    c7.metric("Popularity", int(node_stats["popularity"]))

    st.caption(
        f"Followers: {int(node_stats['followers'])} | Genres: {node_stats['genres']}"
    )


def main():
    nodes_df, edges_df = get_data()
    build_state()
    name_by_id = dict(zip(nodes_df["spotify_id"].astype(str), nodes_df["name"].astype(str)))

    st.title("Learning To See Data: Artist Collaboration Network")
    st.write(
        "Explore relationships as a graph. Metrics are computed only on the currently shown nodes and edges."
    )

    shown_ids = st.session_state.shown_node_ids
    shown_graph = build_shown_graph(nodes_df, edges_df, shown_ids)
    partition = detect_communities(shown_graph)
    global_stats = compute_global_stats(shown_graph)

    with st.sidebar:
        st.header("Workshop Controls")

        st.markdown("### Reset")
        if st.button("Reset to Initial 20 Nodes", use_container_width=True):
            st.session_state.shown_node_ids = set(get_initial_node_ids(nodes_df, total=20, step=10))
            st.session_state.selected_node_id = None
            st.rerun()

        st.markdown("### Inspect Node")
        shown_options = sorted(
            list(shown_graph.nodes()),
            key=lambda nid: name_by_id.get(str(nid), str(nid)).lower(),
        )

        if shown_options:
            selected_id = st.selectbox(
                "Pick node for stats",
                shown_options,
                index=0,
                key="selected_node_id_select",
                format_func=lambda nid: name_by_id.get(str(nid), str(nid)),
            )
            st.session_state.selected_node_id = selected_id
        else:
            st.session_state.selected_node_id = None

        st.markdown("### Remove Node")
        remove_options = [None] + shown_options
        remove_id = st.selectbox(
            "Remove from shown graph",
            remove_options,
            key="remove_node_id_select",
            format_func=lambda nid: "None" if nid is None else name_by_id.get(str(nid), str(nid)),
        )
        if st.button("Remove Node", use_container_width=True):
            if remove_id is not None:
                node_id = str(remove_id)
                report = remove_node_with_report(shown_graph, node_id)
                if node_id in st.session_state.shown_node_ids:
                    st.session_state.shown_node_ids.remove(node_id)
                if st.session_state.selected_node_id == node_id:
                    st.session_state.selected_node_id = None
                st.rerun()

        st.markdown("### Add Artist")
        addable_df = get_addable_artists(nodes_df, st.session_state.shown_node_ids)
        if len(addable_df) > 0:
            add_preview = addable_df.head(1500).copy()
            add_ids = add_preview["spotify_id"].astype(str).tolist()
            add_id = st.selectbox(
                "Search and add artist",
                add_ids,
                key="add_artist_id_select",
                format_func=lambda nid: name_by_id.get(str(nid), str(nid)),
            )

            if st.button("Add Artist + Existing Collabs", use_container_width=True):
                st.session_state.shown_node_ids.add(str(add_id))
                st.rerun()
        else:
            st.caption("No more artists available to add.")

        st.markdown("### Notes")
        st.caption("Left click a node in the graph to inspect it. Use Delete Selected Node for fast removal.")

    agraph_nodes_raw, agraph_edges_raw = build_agraph_payload(shown_graph, partition)
    agraph_nodes = [Node(**n) for n in agraph_nodes_raw]
    agraph_edges = [Edge(**e) for e in agraph_edges_raw]
    graph_config = Config(
        width="100%",
        height=680,
        directed=False,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
    )

    clicked_node_id = agraph(nodes=agraph_nodes, edges=agraph_edges, config=graph_config)
    if clicked_node_id and clicked_node_id in shown_graph:
        st.session_state.selected_node_id = clicked_node_id

    selected_node_id = st.session_state.selected_node_id
    node_stats = compute_node_stats(shown_graph, selected_node_id, partition) if selected_node_id else {}

    st.subheader("Shown Graph Stats")
    render_global_stats(global_stats)

    render_node_stats(node_stats)

if __name__ == "__main__":
    main()
