"""Graph validation for family tree data."""

import networkx as nx


def validate_graph(G: nx.DiGraph) -> list[str]:
    """
    Validate the family tree graph for:
    - Cycles in parent-child relationships
    - Impossible ages (child born before parent)
    - Date ordering issues

    Returns a list of warning messages.
    """
    warnings: list[str] = []

    # Create a subgraph with only PARENT_OF edges for cycle detection
    parent_edges = [
        (u, v) for u, v, d in G.edges(data=True) if d.get("relationship_type") == "PARENT_OF"
    ]
    parent_graph = nx.DiGraph(parent_edges)

    # Check for cycles
    try:
        cycle = nx.find_cycle(parent_graph, orientation="original")
        cycle_nodes = [edge[0] for edge in cycle]
        warnings.append(f"Cycle detected in parent-child relationships: {cycle_nodes}")
    except nx.NetworkXNoCycle:
        pass  # No cycle found, which is good

    # Check for impossible ages (child born before parent)
    # birth_date is now ISO format (YYYY-MM-DD) which can be compared as strings
    for parent, child, data in G.edges(data=True):
        if data.get("relationship_type") != "PARENT_OF":
            continue

        parent_data = G.nodes[parent]
        child_data = G.nodes[child]

        parent_birth = parent_data.get("birth_date")
        child_birth = child_data.get("birth_date")

        if parent_birth and child_birth:
            # Check if child is born before parent (ISO dates can be string-compared)
            if child_birth < parent_birth:
                warnings.append(
                    f"Impossible: {child_data.get('person_name')} born before parent "
                    f"{parent_data.get('person_name')}"
                )
            else:
                # Check if parent was too young (< 12 years old)
                # Parse years from ISO format
                try:
                    parent_year = int(parent_birth[:4])
                    child_year = int(child_birth[:4])
                    if child_year - parent_year < 12:
                        warnings.append(
                            f"Suspicious: {parent_data.get('person_name')} was less than 12 years "
                            f"old when {child_data.get('person_name')} was born"
                        )
                except (ValueError, IndexError):
                    pass

    # Check death before birth
    for _, data in G.nodes(data=True):
        birth = data.get("birth_date")
        death = data.get("death_date")

        if birth and death and death < birth:
            warnings.append(f"Impossible: {data.get('person_name')} died before being born")

    return warnings
