"""NetworkX graph building and operations."""

import itertools
import sqlite3

import networkx as nx


def build_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    """Build a NetworkX directed graph from the database."""
    G = nx.DiGraph()
    cursor = conn.cursor()

    # Add nodes (persons)
    # Note: use 'person_name' instead of 'name' to avoid conflict with pydot
    cursor.execute("SELECT id, name, sex, birth_date, death_date FROM person")
    for row in cursor.fetchall():
        G.add_node(
            row[0], person_name=row[1], sex=row[2], birth_date=row[3], death_date=row[4]
        )

    # Add edges (relationships)
    cursor.execute("SELECT person1_id, person2_id, relationship_type FROM relationship")
    for row in cursor.fetchall():
        G.add_edge(row[0], row[1], relationship_type=row[2])

    return G


def get_ego_subgraph(G: nx.DiGraph, center_id: int, radius: int = 2) -> nx.DiGraph:
    """
    Extract a subgraph containing nodes within a given degree of a center node.

    Args:
        G: The full graph
        center_id: The person ID to center the subgraph on
        radius: Maximum distance from center (default 2)

    Returns:
        A subgraph containing only nodes within `radius` edges of `center_id`
    """
    if center_id not in G:
        raise ValueError(f"Person ID {center_id} not found in graph")

    # Use undirected view for ego graph to capture both directions
    # (parents, children, spouses all within radius)
    undirected = G.to_undirected()
    ego = nx.ego_graph(undirected, center_id, radius=radius)

    # Return the directed subgraph induced by these nodes
    return G.subgraph(ego.nodes()).copy()


def build_union_layout_graph(G: nx.DiGraph) -> nx.DiGraph:
    """
    Build a layout graph using the union-node model for better family tree visualization.

    Creates "family nodes" (union nodes) that connect spouse pairs to their children.
    This produces cleaner hierarchical layouts where:
    - Spouses naturally sit on the same generation
    - All children hang from the union node, so siblings align
    - Fewer edge crossings than direct parent→child edges

    Args:
        G: Original graph with PARENT_OF and SPOUSE_OF edges

    Returns:
        A new graph with family nodes suitable for hierarchical layout
    """
    H = nx.DiGraph()

    # Copy person nodes with their attributes
    for n, data in G.nodes(data=True):
        H.add_node(n, node_type="person", **data)

    # Collect spouse pairs (avoid duplicates by sorting)
    spouse_pairs: set[tuple] = set()
    for u, v, edata in G.edges(data=True):
        if edata.get("relationship_type") == "SPOUSE_OF":
            a, b = tuple(sorted([u, v], key=str))
            spouse_pairs.add((a, b))

    # Map spouse pair -> family node id
    fam_for_pair: dict[tuple, str] = {}
    for a, b in spouse_pairs:
        fam_id = f"FAM_{a}_{b}"
        fam_for_pair[(a, b)] = fam_id
        # Family node is a small connector point
        H.add_node(fam_id, node_type="family", spouses=(a, b))
        # Connect spouses to family node
        H.add_edge(a, fam_id, edge_type="spouse_to_family")
        H.add_edge(b, fam_id, edge_type="spouse_to_family")

    # Build lookup: spouse -> set of their partners
    spouses_of: dict[int, set[int]] = {}
    for a, b in spouse_pairs:
        spouses_of.setdefault(a, set()).add(b)
        spouses_of.setdefault(b, set()).add(a)

    # Collect parent->child edges
    parent_of_edges = [
        (u, v)
        for u, v, edata in G.edges(data=True)
        if edata.get("relationship_type") == "PARENT_OF"
    ]

    # Group parents by child
    parents_by_child: dict[int, list[int]] = {}
    for parent, child in parent_of_edges:
        parents_by_child.setdefault(child, []).append(parent)

    # For each child, connect them to the appropriate family node
    for child, parents in parents_by_child.items():
        parents = list(dict.fromkeys(parents))  # unique, preserve order

        fam_id = None

        # Try to find a spouse pair among the parents
        if len(parents) >= 2:
            for p1, p2 in itertools.combinations(parents, 2):
                a, b = tuple(sorted([p1, p2], key=str))
                if (a, b) in fam_for_pair:
                    fam_id = fam_for_pair[(a, b)]
                    break

        # If no spouse pair found, create a single-parent family node
        if fam_id is None:
            fam_id = f"FAM_{'_'.join(map(str, sorted(parents, key=str)))}"
            if fam_id not in H:
                H.add_node(fam_id, node_type="family", spouses=tuple(parents))
                for p in parents:
                    H.add_edge(p, fam_id, edge_type="spouse_to_family")

        # Child hangs from family node
        H.add_edge(fam_id, child, edge_type="family_to_child")

    return H
