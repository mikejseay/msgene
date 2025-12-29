"""NetworkX graph building and operations."""

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
