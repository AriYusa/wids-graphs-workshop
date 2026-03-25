from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from graph_utils import (
    build_pyvis_html,
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


def format_artist_option(row):
    return f"{row['name']} | popularity={int(row['popularity'])} | id={row['spotify_id']}"


def build_state():
    nodes_df, _ = get_data()

    if "shown_node_ids" not in st.session_state:
        st.session_state.shown_node_ids = set(get_initial_node_ids(nodes_df, total=20, step=10))

    if "selected_node_id" not in st.session_state:
        st.session_state.selected_node_id = None

    if "last_remove_report" not in st.session_state:
        st.session_state.last_remove_report = None


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
        f"Followers: {int(node_stats['followers'])} | Genres: {node_stats['genres']} | Chart hits: {node_stats['chart_hits']}"
    )


def main():
    nodes_df, edges_df = get_data()
    build_state()

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
            st.session_state.last_remove_report = None
            st.rerun()

        st.markdown("### Inspect Node")
        shown_options = [
            (nid, shown_graph.nodes[nid].get("name", nid))
            for nid in sorted(shown_graph.nodes(), key=lambda x: shown_graph.nodes[x].get("name", ""))
        ]
        shown_labels = [f"{name} | {nid}" for nid, name in shown_options]

        if shown_labels:
            selected_label = st.selectbox(
                "Pick node for stats",
                shown_labels,
                index=0,
                key="selected_node_label",
            )
            selected_id = selected_label.split(" | ")[-1]
            st.session_state.selected_node_id = selected_id
        else:
            st.session_state.selected_node_id = None

        st.markdown("### Remove Node")
        remove_label = st.selectbox("Remove from shown graph", ["None"] + shown_labels, key="remove_node_label")
        if st.button("Remove Node", use_container_width=True):
            if remove_label != "None":
                node_id = remove_label.split(" | ")[-1]
                report = remove_node_with_report(shown_graph, node_id)
                if node_id in st.session_state.shown_node_ids:
                    st.session_state.shown_node_ids.remove(node_id)
                st.session_state.last_remove_report = report
                if st.session_state.selected_node_id == node_id:
                    st.session_state.selected_node_id = None
                st.rerun()

        st.markdown("### Add Artist")
        addable_df = get_addable_artists(nodes_df, st.session_state.shown_node_ids)
        if len(addable_df) > 0:
            add_preview = addable_df.head(1500).copy()
            add_preview["label"] = add_preview.apply(format_artist_option, axis=1)
            add_label = st.selectbox("Search and add artist", add_preview["label"].tolist(), key="add_artist_label")

            if st.button("Add Artist + Existing Collabs", use_container_width=True):
                add_id = add_label.split(" | id=")[-1]
                st.session_state.shown_node_ids.add(add_id)
                st.rerun()
        else:
            st.caption("No more artists available to add.")

        st.markdown("### Notes")
        st.caption(
            "In Streamlit + Pyvis, direct click callbacks to Python are limited. "
            "Use this sidebar selector for exact node stats and controls."
        )

    selected_node_id = st.session_state.selected_node_id
    node_stats = compute_node_stats(shown_graph, selected_node_id, partition) if selected_node_id else {}

    html = build_pyvis_html(shown_graph, partition, selected_node=selected_node_id, height_px=640)
    components.html(html, height=680, scrolling=False)

    st.subheader("Shown Graph Stats")
    render_global_stats(global_stats)
    st.caption(f"Top by degree: {global_stats['top_degree']}")

    render_node_stats(node_stats)

    if st.session_state.last_remove_report:
        before = st.session_state.last_remove_report["before"]
        after = st.session_state.last_remove_report["after"]
        st.subheader("Robustness: Before vs After Removal")
        c1, c2, c3 = st.columns(3)
        c1.metric("Components", after["components"], delta=after["components"] - before["components"])
        c2.metric(
            "Largest Component",
            after["largest_component"],
            delta=after["largest_component"] - before["largest_component"],
        )
        c3.metric("Density", f"{after['density']:.4f}", delta=f"{after['density'] - before['density']:.4f}")


if __name__ == "__main__":
    main()
