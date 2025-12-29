"""Data classes for family tree entities."""

from dataclasses import dataclass


@dataclass
class Person:
    id: int
    name: str
    given_name: str | None
    surname: str | None
    sex: str | None
    birth_date_string: str | None
    birth_date: str | None  # ISO format YYYY-MM-DD or None
    birth_place: str | None
    death_date_string: str | None
    death_date: str | None  # ISO format YYYY-MM-DD or None
    death_place: str | None


@dataclass
class Relationship:
    person1_id: int
    person2_id: int
    relationship_type: str  # PARENT_OF, CHILD_OF, SPOUSE_OF
