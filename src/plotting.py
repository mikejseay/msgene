"""Visualization functions for family tree graphs."""

from pathlib import Path

import networkx as nx
import pydot

from graph import build_union_layout_graph


def plot_graph(G: nx.DiGraph, output_path: Path | None = None):
    """
    Plot the family tree using the union-node model and Graphviz hierarchical layout.

    Creates a proper genealogical chart where:
    - Parents appear above children (ancestors at top)
    - Spouses are aligned horizontally on the same rank
    - Siblings align under their family node
    - Family/union nodes connect spouse pairs to their children

    Args:
        G: NetworkX DiGraph with person nodes and PARENT_OF/SPOUSE_OF edges
        output_path: Path to save the output image (PNG). If None, displays interactively.
    """
    # Build the union-node layout graph
    H = build_union_layout_graph(G)

    # Create pydot graph with hierarchical settings
    P = pydot.Dot(graph_type="digraph")
    P.set("rankdir", "TB")  # Top-to-bottom (ancestors at top)
    P.set("splines", "ortho")  # Orthogonal edges for cleaner tree look
    P.set("nodesep", "0.4")  # Horizontal spacing between nodes
    P.set("ranksep", "0.6")  # Vertical spacing between ranks

    # Track spouse pairs with their family nodes for rank=same subgraphs
    spouse_pairs: list[tuple] = []

    # Add nodes
    for node, data in H.nodes(data=True):
        node_type = data.get("node_type", "person")

        if node_type == "family":
            # Family nodes are small invisible points
            P.add_node(
                pydot.Node(
                    str(node),
                    shape="point",
                    width="0.1",
                    height="0.1",
                    label="",
                )
            )
            # Track spouse pairs with family node for rank alignment
            spouses = data.get("spouses", ())
            if len(spouses) == 2:
                spouse_pairs.append((spouses[0], spouses[1], node))
        else:
            # Person nodes
            sex = data.get("sex")
            given_name = data.get("given_name", "")
            surname = data.get("surname", "")
            birth_date = data.get("birth_date", "")
            death_date = data.get("death_date", "")

            # Extract years from dates (assume format like "YYYY-MM-DD" or just "YYYY")
            birth_year = birth_date[:4] if birth_date else ""
            death_year = death_date[:4] if death_date else ""

            # Build label
            label = f"{given_name}\n{surname}\n{birth_year}-{death_year}"

            # Color by sex
            if sex == "M":
                fillcolor = "lightblue"
            elif sex == "F":
                fillcolor = "lightpink"
            else:
                fillcolor = "lightgray"

            P.add_node(
                pydot.Node(
                    str(node),
                    label=label,
                    shape="box",
                    style="rounded,filled",
                    fillcolor=fillcolor,
                    fontsize="10",
                )
            )

    # Add edges
    for u, v, data in H.edges(data=True):
        edge_type = data.get("edge_type", "")

        if edge_type == "spouse_to_family":
            # Spouse to family node: no arrow, constraint to keep hierarchy
            P.add_edge(
                pydot.Edge(
                    str(u),
                    str(v),
                    dir="none",
                    color="darkgray",
                )
            )
        elif edge_type == "family_to_child":
            # Family node to child: arrow pointing down
            P.add_edge(
                pydot.Edge(
                    str(u),
                    str(v),
                    color="darkgray",
                )
            )

    # Add rank=same subgraphs to align spouse pairs and family nodes horizontally
    for i, (a, b, _) in enumerate(spouse_pairs):
        sg = pydot.Subgraph(f"couple_{i}", rank="same")
        sg.add_node(pydot.Node(str(a)))
        sg.add_node(pydot.Node(str(b)))
        P.add_subgraph(sg)

    # Render
    if output_path:
        # Determine format from extension
        ext = output_path.suffix.lower().lstrip(".")
        if ext not in ("png", "svg", "pdf"):
            ext = "png"

        P.write(str(output_path), format=ext)
        print(f"Graph saved to {output_path}")
    else:
        # Save to temporary file and display
        import tempfile

        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            P.write(f.name, format="png")
            img = mpimg.imread(f.name)
            plt.figure(figsize=(20, 16))
            plt.imshow(img)
            plt.axis("off")
            plt.tight_layout()
            plt.show()
