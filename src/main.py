"""
1) Parse the family tree data in the "seay.ged" file into memory.
2) Normalize it into `person` (nodes) and `relationship` (edges) tables.
    - Ignore non-standard, Ancestry-specific custom tags.
3) Store the tables with SQLite.
4) Use the family tree data to create a networkx graph.
5) Validate the family tree data for cycles, impossible ages, and date ordering.
6) Plot the networkx graph.
"""

from pathlib import Path
import sqlite3
from dataclasses import dataclass
from datetime import datetime
import re

from ged4py import GedcomReader
import networkx as nx
import matplotlib.pyplot as plt


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Person:
    id: int
    name: str
    given_name: str | None
    surname: str | None
    sex: str | None
    birth_date: str | None
    birth_place: str | None
    death_date: str | None
    death_place: str | None


@dataclass
class Relationship:
    person1_id: int
    person2_id: int
    relationship_type: str  # PARENT_OF, CHILD_OF, SPOUSE_OF


# ============================================================================
# 1) Parse GEDCOM
# ============================================================================


def extract_numeric_id(xref_id: str) -> int:
    """Extract numeric part from GEDCOM xref_id like '@I_347421849@' or 'I674624289'."""
    # Remove @ symbols and extract all digits
    digits = re.sub(r"[^0-9]", "", xref_id)
    if not digits:
        raise ValueError(f"No numeric ID found in: {xref_id}")
    return int(digits)


def parse_gedcom(filepath: Path) -> GedcomReader:
    """Parse a GEDCOM file and return the reader object."""
    return GedcomReader(str(filepath))


def extract_name_parts(indi) -> tuple[str, str | None, str | None]:
    """Extract full name, given name, and surname from an individual record."""
    name_rec = indi.sub_tag("NAME")
    if name_rec is None:
        return ("Unknown", None, None)

    name_value = name_rec.value
    if name_value is None:
        return ("Unknown", None, None)

    # ged4py returns NAME as tuple: (given, surname, suffix)
    if isinstance(name_value, tuple):
        given, surname, suffix = name_value
        parts = [p for p in [given, surname, suffix] if p]
        full_name = " ".join(parts) if parts else "Unknown"
        return (full_name, given or None, surname or None)

    # Fallback: string format "Given /Surname/"
    full_name = str(name_value).replace("/", "").strip() or "Unknown"

    givn = name_rec.sub_tag("GIVN")
    surn = name_rec.sub_tag("SURN")

    given_name = givn.value if givn else None
    surname = surn.value if surn else None

    return (full_name, given_name, surname)


def extract_event_details(indi, tag: str) -> tuple[str | None, str | None]:
    """Extract date and place from an event tag (BIRT, DEAT, etc.)."""
    event = indi.sub_tag(tag)
    if event is None:
        return (None, None)

    date_rec = event.sub_tag("DATE")
    place_rec = event.sub_tag("PLAC")

    # Convert date value to string (ged4py may return DateValue objects)
    date_val = None
    if date_rec and date_rec.value:
        date_val = str(date_rec.value)

    place_val = None
    if place_rec and place_rec.value:
        place_val = str(place_rec.value)

    return (date_val, place_val)


def extract_sex(indi) -> str | None:
    """Extract sex from an individual record."""
    sex_rec = indi.sub_tag("SEX")
    return sex_rec.value if sex_rec else None


# ============================================================================
# 2) Normalize Data
# ============================================================================


def normalize_data(reader: GedcomReader) -> tuple[list[Person], list[Relationship]]:
    """
    Extract persons and relationships from parsed GEDCOM data.
    Ignores non-standard Ancestry-specific tags (starting with _).
    """
    persons: list[Person] = []
    relationships: list[Relationship] = []

    # Track family records for relationship extraction
    families: dict[str, dict] = {}

    # First pass: extract all individuals
    for rec in reader.records0("INDI"):
        if rec.xref_id is None:
            continue

        indi_id = extract_numeric_id(rec.xref_id)
        full_name, given_name, surname = extract_name_parts(rec)
        sex = extract_sex(rec)
        birth_date, birth_place = extract_event_details(rec, "BIRT")
        death_date, death_place = extract_event_details(rec, "DEAT")

        persons.append(
            Person(
                id=indi_id,
                name=full_name,
                given_name=given_name,
                surname=surname,
                sex=sex,
                birth_date=birth_date,
                birth_place=birth_place,
                death_date=death_date,
                death_place=death_place,
            )
        )

    # Second pass: extract family records
    for rec in reader.records0("FAM"):
        fam_id = rec.xref_id

        if fam_id is None:
            continue

        husb = rec.sub_tag("HUSB")
        wife = rec.sub_tag("WIFE")

        husb_id = extract_numeric_id(husb.xref_id) if husb and husb.xref_id else None
        wife_id = extract_numeric_id(wife.xref_id) if wife and wife.xref_id else None

        child_ids = []
        for child in rec.sub_tags("CHIL"):
            if child.xref_id:
                child_ids.append(extract_numeric_id(child.xref_id))

        families[fam_id] = {
            "husb": husb_id,
            "wife": wife_id,
            "children": child_ids,
        }

    # Build relationships from families
    for fam_id, fam in families.items():
        husb_id = fam["husb"]
        wife_id = fam["wife"]
        children = fam["children"]

        # Spouse relationship
        if husb_id and wife_id:
            relationships.append(
                Relationship(
                    person1_id=husb_id,
                    person2_id=wife_id,
                    relationship_type="SPOUSE_OF",
                )
            )

        # Parent-child relationships
        for child_id in children:
            if husb_id:
                relationships.append(
                    Relationship(
                        person1_id=husb_id,
                        person2_id=child_id,
                        relationship_type="PARENT_OF",
                    )
                )
            if wife_id:
                relationships.append(
                    Relationship(
                        person1_id=wife_id,
                        person2_id=child_id,
                        relationship_type="PARENT_OF",
                    )
                )

    return persons, relationships


# ============================================================================
# 3) Store in SQLite
# ============================================================================


def create_database(db_path: Path) -> sqlite3.Connection:
    """Create SQLite database with person and relationship tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            given_name TEXT,
            surname TEXT,
            sex TEXT,
            birth_date TEXT,
            birth_place TEXT,
            death_date TEXT,
            death_place TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationship (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person1_id INTEGER NOT NULL,
            person2_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            FOREIGN KEY (person1_id) REFERENCES person(id),
            FOREIGN KEY (person2_id) REFERENCES person(id)
        )
    """)

    conn.commit()
    return conn


def store_data(
    conn: sqlite3.Connection, persons: list[Person], relationships: list[Relationship]
):
    """Insert persons and relationships into the database."""
    cursor = conn.cursor()

    # Insert persons
    cursor.executemany(
        """
        INSERT OR REPLACE INTO person 
        (id, name, given_name, surname, sex, birth_date, birth_place, death_date, death_place)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                p.id,
                p.name,
                p.given_name,
                p.surname,
                p.sex,
                p.birth_date,
                p.birth_place,
                p.death_date,
                p.death_place,
            )
            for p in persons
        ],
    )

    # Insert relationships
    cursor.executemany(
        """
        INSERT INTO relationship (person1_id, person2_id, relationship_type)
        VALUES (?, ?, ?)
        """,
        [(r.person1_id, r.person2_id, r.relationship_type) for r in relationships],
    )

    conn.commit()


# ============================================================================
# 4) Build NetworkX Graph
# ============================================================================


def build_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    """Build a NetworkX directed graph from the database."""
    G = nx.DiGraph()
    cursor = conn.cursor()

    # Add nodes (persons)
    cursor.execute("SELECT id, name, sex, birth_date, death_date FROM person")
    for row in cursor.fetchall():
        G.add_node(
            row[0], name=row[1], sex=row[2], birth_date=row[3], death_date=row[4]
        )

    # Add edges (relationships)
    cursor.execute("SELECT person1_id, person2_id, relationship_type FROM relationship")
    for row in cursor.fetchall():
        G.add_edge(row[0], row[1], relationship_type=row[2])

    return G


# ============================================================================
# 5) Validate Data
# ============================================================================


def parse_gedcom_date(date_str: str | None) -> datetime | None:
    """Attempt to parse a GEDCOM date string into a datetime object."""
    if not date_str:
        return None

    # Common GEDCOM date formats
    patterns = [
        (r"(\d{1,2}) (\w{3}) (\d{4})", "%d %b %Y"),  # 25 NOV 1954
        (r"(\w{3}) (\d{4})", "%b %Y"),  # NOV 1954
        (r"(\d{4})", "%Y"),  # 1954
    ]

    date_str = date_str.upper().strip()
    # Remove qualifiers like ABT, BEF, AFT, etc.
    date_str = re.sub(r"^(ABT|BEF|AFT|EST|CAL|FROM|TO|BET|AND)\s*", "", date_str)

    for pattern, fmt in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                return datetime.strptime(match.group(0), fmt)
            except ValueError:
                continue

    return None


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
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("relationship_type") == "PARENT_OF"
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
    for parent, child, data in G.edges(data=True):
        if data.get("relationship_type") != "PARENT_OF":
            continue

        parent_data = G.nodes[parent]
        child_data = G.nodes[child]

        parent_birth = parse_gedcom_date(parent_data.get("birth_date"))
        child_birth = parse_gedcom_date(child_data.get("birth_date"))

        if parent_birth and child_birth:
            # Check if child is born before parent
            if child_birth < parent_birth:
                warnings.append(
                    f"Impossible: {child_data.get('name')} born before parent "
                    f"{parent_data.get('name')}"
                )
            # Check if parent was too young (< 12 years old)
            elif (child_birth - parent_birth).days < 12 * 365:
                warnings.append(
                    f"Suspicious: {parent_data.get('name')} was less than 12 years old "
                    f"when {child_data.get('name')} was born"
                )

    # Check death before birth
    for node, data in G.nodes(data=True):
        birth = parse_gedcom_date(data.get("birth_date"))
        death = parse_gedcom_date(data.get("death_date"))

        if birth and death and death < birth:
            warnings.append(f"Impossible: {data.get('name')} died before being born")

    return warnings


# ============================================================================
# 6) Plot Graph
# ============================================================================


def plot_graph(G: nx.DiGraph, output_path: Path | None = None):
    """Plot the family tree graph using matplotlib."""
    plt.figure(figsize=(20, 16))

    # Use a layout that works without optional dependencies
    # For large graphs, use a simple layout; for smaller ones, try kamada_kawai
    if G.number_of_nodes() > 500:
        # For large graphs, use random layout (fast) or subsample
        pos = nx.random_layout(G, seed=42)
    else:
        try:
            pos = nx.kamada_kawai_layout(G)
        except Exception:
            pos = nx.random_layout(G, seed=42)

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

    # Draw the graph
    nx.draw(
        G,
        pos,
        node_color=node_colors,
        node_size=50,
        font_size=4,
        with_labels=False,
        arrows=True,
        edge_color="gray",
        alpha=0.7,
        width=0.3,
    )

    plt.title(
        f"Family Tree Graph ({G.number_of_nodes()} people, {G.number_of_edges()} relationships)"
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Graph saved to {output_path}")
    else:
        plt.show()


# ============================================================================
# Main
# ============================================================================


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
    else:
        print("  No validation issues found")

    print(f"Plotting graph to: {plot_path}")
    plot_graph(G, plot_path)

    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
