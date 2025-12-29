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
    cursor.execute("SELECT id, name, sex, birth_date, death_date, given_name, surname FROM person")
    for row in cursor.fetchall():
        G.add_node(
            row[0],
            person_name=row[1],
            sex=row[2],
            birth_date=row[3],
            death_date=row[4],
            given_name=row[5],
            surname=row[6],
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


def get_lineage_subgraph(
    G: nx.DiGraph, center_id: int, sex: str = "M", radius: int = 1
) -> nx.DiGraph:
    """
    Extract a subgraph representing the "lineage" of center_id of a particular sex - the union of
    ego subgraphs of a given radius for a chain of parents of a given sex.
    Begin with center_id. Add its ego subgraph of the given radius to the set.
    Next, find the node's parent (PARENT_OF) of the given sex. Add its ego subgraph to the set.
    Continue recursively by finding the next parent of the given sex and adding its ego subgraph.
    Return the subgraph of G containing the union of nodes from all ego subgraphs found this way.
    In the special case that radius = 0, ego subgraphs should only contain a node's spouse.

    Args:
        G: The full graph
        center_id: The person ID to center the subgraph on
        sex: The sex of parents to recursively iterate through
        radius: Maximum distance from center (default 1)

    Returns:
        A subgraph containing nodes within `radius` edges of the parental lineage `center_id` of
        a given sex.
    """
    if center_id not in G:
        raise ValueError(f"Person ID {center_id} not found in graph")

    # Use undirected view for ego graph extraction
    undirected = G.to_undirected()

    # Collect all nodes from ego subgraphs along the lineage
    all_nodes: set[int] = set()

    current_id = center_id
    while current_id is not None:
        # Add ego subgraph nodes for current person
        # In the special case that radius = 0, ego subgraphs should only contain a node's spouse.
        if radius == 0:
            # Add current person and their spouse(s)
            all_nodes.add(current_id)
            for neighbor in G.predecessors(current_id):
                if G.edges[neighbor, current_id].get("relationship_type") == "SPOUSE_OF":
                    all_nodes.add(neighbor)
            for neighbor in G.successors(current_id):
                if G.edges[current_id, neighbor].get("relationship_type") == "SPOUSE_OF":
                    all_nodes.add(neighbor)
        else:
            ego = nx.ego_graph(undirected, current_id, radius=radius)
            all_nodes.update(ego.nodes())

        # Find parent of the given sex
        # PARENT_OF edges go from parent → child, so parents are predecessors
        next_parent = None
        for parent in G.predecessors(current_id):
            edge_data = G.edges[parent, current_id]
            if edge_data.get("relationship_type") == "PARENT_OF":
                parent_data = G.nodes[parent]
                if parent_data.get("sex") == sex:
                    next_parent = parent
                    break

        current_id = next_parent

    # Return the directed subgraph induced by these nodes
    return G.subgraph(all_nodes).copy()


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
        # De-duplicate parents while preserving order
        parents = list(dict.fromkeys(parents))

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
