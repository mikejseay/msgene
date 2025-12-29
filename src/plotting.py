"""Visualization functions for family tree graphs."""

from pathlib import Path

import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
import matplotlib.pyplot as plt


def plot_graph(G: nx.DiGraph, output_path: Path | None = None):
    """
    Plot the family tree using Graphviz hierarchical layout.

    Parents appear above children (ancestors at top), spouses aligned horizontally.
    """
    plt.figure(figsize=(20, 16))

    # Use Graphviz 'dot' for hierarchical tree layout
    # rankdir=TB = top-to-bottom (ancestors at top)
    pos = graphviz_layout(G, prog="dot")

    # Separate edges by type for different styling
    parent_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("relationship_type") == "PARENT_OF"
    ]
    spouse_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("relationship_type") == "SPOUSE_OF"
    ]

    # Color nodes by sex
    node_colors = []
    for node in G.nodes():
        sex = G.nodes[node].get("sex")
        if sex == "M":
            node_colors.append("lightblue")
        elif sex == "F":
            node_colors.append("lightpink")
        else:
            node_colors.append("lightgray")

    # Create node labels (name)
    labels = {}
    for node in G.nodes():
        labels[node] = G.nodes[node].get("person_name", "?")

    # Draw nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        node_size=800,
        alpha=0.9,
    )

    # Draw node labels
    nx.draw_networkx_labels(
        G,
        pos,
        labels=labels,
        font_size=8,
        font_weight="bold",
    )

    # Draw parent-child edges (solid arrows pointing down to children)
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=parent_edges,
        edge_color="darkgray",
        arrows=True,
        arrowsize=15,
        width=1.5,
        alpha=0.8,
    )

    # Draw spouse edges (dashed red lines, no arrows)
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=spouse_edges,
        edge_color="red",
        style="dashed",
        arrows=False,
        width=1.5,
        alpha=0.6,
    )

    plt.title(
        f"Family Tree ({G.number_of_nodes()} people, {G.number_of_edges()} relationships)",
        fontsize=14,
        fontweight="bold",
    )
    plt.axis("off")
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Graph saved to {output_path}")
    else:
        plt.show()
