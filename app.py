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
        st.session_state.shown_node_ids = set(get_initial_node_ids(nodes_df))

    if "selected_node_id" not in st.session_state:
        st.session_state.selected_node_id = None

    if "node_positions" not in st.session_state:
        st.session_state.node_positions = {}


def render_global_stats(stats):
    c1, c2 = st.columns(2)
    c1.metric(
        "Density",
        f"{stats['density']:.4f}",
        help="How full the network is with connections (0 to 1)",
    )
    c2.metric(
        "Avg Collabs Per Artist",
        f"{stats['avg_degree']:.2f}",
        help="Avg Degree is the average number of collaborators per artist",
    )


def render_node_stats(node_stats):
    if not node_stats:
        st.info("Click an artist node in the graph to view artist-level stats.")
        return

    st.markdown(f"**{node_stats['name']}**")
    c1, c2 = st.columns(2)
    c1.metric(
        "Direct Collaborators",
        node_stats["degree"],
        help="Degree is the number of artists directly connected to this artist",
    )
    c2.metric(
        "Betweenness",
        f"{node_stats['betweenness']:.4f}",
        help="Betweenness is how often this artist links other artists through shortest paths.",
    )


def main():
    nodes_df, edges_df = get_data()
    build_state()
    name_by_id = dict(zip(nodes_df["spotify_id"].astype(str), nodes_df["name"].astype(str)))
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0.6rem;
        }
        div[data-testid="stMetricLabel"] p {
            font-size: 0.78rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.15rem;
            line-height: 1.15;
        }
        div[data-testid="stMetric"] {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    shown_ids = st.session_state.shown_node_ids
    shown_graph = build_shown_graph(nodes_df, edges_df, shown_ids)
    partition = detect_communities(shown_graph)
    global_stats = compute_global_stats(shown_graph)

    shown_options = sorted(
        list(shown_graph.nodes()),
        key=lambda nid: name_by_id.get(str(nid), str(nid)).lower(),
    )
    if shown_options and st.session_state.selected_node_id not in shown_graph:
        st.session_state.selected_node_id = shown_options[0]
    elif not shown_options:
        st.session_state.selected_node_id = None

    newly_added_id = st.session_state.pop("newly_added_id", None)
    selected_node_id = st.session_state.selected_node_id
    agraph_nodes_raw, agraph_edges_raw, new_positions = build_agraph_payload(
        shown_graph,
        partition,
        existing_positions=st.session_state.node_positions,
        newly_added_id=newly_added_id,
        selected_node_id=selected_node_id,
    )
    st.session_state.node_positions = new_positions
    agraph_nodes = [Node(**n) for n in agraph_nodes_raw]
    agraph_edges = [Edge(**e) for e in agraph_edges_raw]
    graph_config = Config(
        width="100%",
        height=680,
        directed=False,
        physics=False,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
        staticGraphWithDragAndDrop=True,
    )

    with st.sidebar:

        if st.button("Reset to Initial Nodes", use_container_width=True):
            st.session_state.shown_node_ids = set(get_initial_node_ids(nodes_df))
            st.session_state.selected_node_id = None
            st.session_state.node_positions = {}
            st.rerun()

        selected_for_delete = st.session_state.selected_node_id
        can_delete_selected = (
            selected_for_delete is not None
            and str(selected_for_delete) in st.session_state.shown_node_ids
        )
        if st.button(
            "Delete Selected Node",
            use_container_width=True,
            disabled=not can_delete_selected,
        ):
            node_id = str(selected_for_delete)
            remove_node_with_report(shown_graph, node_id)
            st.session_state.shown_node_ids.discard(node_id)
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
                st.session_state.newly_added_id = str(add_id)
                st.session_state.selected_node_id = str(add_id)
                st.rerun()
        else:
            st.caption("No more artists available to add.")

        st.markdown("### Graph Stats")
        render_global_stats(global_stats)

        st.markdown("### Artist Stats")
        node_stats_placeholder = st.container()

    clicked_node_id = agraph(nodes=agraph_nodes, edges=agraph_edges, config=graph_config)
    if clicked_node_id and clicked_node_id in shown_graph:
        st.session_state.selected_node_id = clicked_node_id
        selected_node_id = clicked_node_id

    node_stats = (
        compute_node_stats(shown_graph, selected_node_id, partition)
        if selected_node_id in shown_graph
        else {}
    )
    with node_stats_placeholder:
        render_node_stats(node_stats)


if __name__ == "__main__":
    main()
