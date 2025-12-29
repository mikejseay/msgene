"""SQLite database operations for family tree storage."""

from pathlib import Path
import sqlite3

from models import Person, Relationship


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
            birth_date_string TEXT,
            birth_date TEXT,
            birth_place TEXT,
            death_date_string TEXT,
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


def store_data(conn: sqlite3.Connection, persons: list[Person], relationships: list[Relationship]):
    """Insert persons and relationships into the database."""
    cursor = conn.cursor()

    # Insert persons
    cursor.executemany(
        """
        INSERT OR REPLACE INTO person
        (id, name, given_name, surname, sex, birth_date_string, birth_date, birth_place, death_date_string, death_date, death_place)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                p.id,
                p.name,
                p.given_name,
                p.surname,
                p.sex,
                p.birth_date_string,
                p.birth_date,
                p.birth_place,
                p.death_date_string,
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
