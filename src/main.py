"""
Family tree application entry point.

1) Parse the family tree data in the "seay.ged" file into memory.
2) Normalize it into `person` (nodes) and `relationship` (edges) tables.
    - Ignore non-standard, Ancestry-specific custom tags.
3) Store the tables with SQLite.
4) Use the family tree data to create a networkx graph.
5) Validate the family tree data for cycles, impossible ages, and date ordering.
6) Plot the networkx graph.
"""

from pathlib import Path

from database import create_database, store_data
from graph import build_graph, get_ego_subgraph, get_lineage_subgraph
from parsing import normalize_data, parse_gedcom
from plotting import plot_graph
from validation import validate_graph


def main():
    # Paths
    project_root = Path(__file__).parent.parent
    gedcom_path = project_root / "seay.ged"
    db_path = project_root / "family_tree.db"
    plot_path = project_root / "family_tree.png"

    # Delete existing database to ensure fresh start
    if db_path.exists():
        db_path.unlink()
        print(f"Deleted existing database: {db_path}")

    print(f"Parsing GEDCOM file: {gedcom_path}")
    reader = parse_gedcom(gedcom_path)

    print("Normalizing data...")
    persons, relationships = normalize_data(reader)
    print(f"  Found {len(persons)} persons and {len(relationships)} relationships")

    print(f"Storing data in SQLite: {db_path}")
    conn = create_database(db_path)
    store_data(conn, persons, relationships)

    print("Building NetworkX graph...")
    G = build_graph(conn)
    print(f"  Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

    print("Validating graph...")
    warnings = validate_graph(G)
    if warnings:
        print(f"  Found {len(warnings)} validation warnings:")
        for w in warnings[:10]:  # Show first 10 warnings
            print(f"    - {w}")
        if len(warnings) > 10:
            print(f"    ... and {len(warnings) - 10} more")

        # Write all warnings to log file
        log_path = project_root / "validation_warnings.log"
        with open(log_path, "w") as f:
            f.write(f"Validation Warnings ({len(warnings)} total)\n")
            f.write("=" * 50 + "\n\n")
            for w in warnings:
                f.write(f"- {w}\n")
        print(f"  Full warnings written to: {log_path}")
    else:
        print("  No validation issues found")

    # Subset graph to nodes within degree 2 of a focal individual. Examples:
    # William R. Seay, Jr. = 347421849
    # Michael James Seay = 347421845
    focal_person_id = 347421845
    # print(f"Extracting subgraph within degree 2 of person {focal_person_id}...")
    subgraph = get_ego_subgraph(G, focal_person_id, radius=2)
    # subgraph = get_lineage_subgraph(G, focal_person_id, sex="M", radius=0)
    print(
        f"  Subgraph has {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges"
    )

    print(f"Plotting graph to: {plot_path}")
    plot_graph(subgraph, plot_path)

    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
