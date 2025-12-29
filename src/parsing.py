"""GEDCOM parsing and date handling utilities."""

from pathlib import Path
import re

from ged4py import GedcomReader

from models import Person, Relationship


# Month name mappings (handle abbreviations and full names)
MONTH_MAP = {
    "JAN": 1,
    "JANUARY": 1,
    "FEB": 2,
    "FEBRUARY": 2,
    "MAR": 3,
    "MARCH": 3,
    "APR": 4,
    "APRIL": 4,
    "MAY": 5,
    "JUN": 6,
    "JUNE": 6,
    "JUL": 7,
    "JULY": 7,
    "AUG": 8,
    "AUGUST": 8,
    "SEP": 9,
    "SEPT": 9,
    "SEPTEMBER": 9,
    "OCT": 10,
    "OCTOBER": 10,
    "NOV": 11,
    "NOVEMBER": 11,
    "DEC": 12,
    "DECEMBER": 12,
}


def extract_numeric_id(xref_id: str) -> int:
    """Extract numeric part from GEDCOM xref_id like '@I_347421849@' or 'I674624289'."""
    # Remove @ symbols and extract all digits
    digits = re.sub(r"[^0-9]", "", xref_id)
    if not digits:
        raise ValueError(f"No numeric ID found in: {xref_id}")
    return int(digits)


def parse_date_string(date_str: str | None) -> str | None:
    """
    Parse a GEDCOM date string into ISO format (YYYY-MM-DD).
    Returns None if the date cannot be parsed.

    Handles formats like:
    - "25 NOV 1954"
    - "1698"
    - "ABOUT 1905"
    - "JAN 1905"
    - "(01-27-1920)"
    - "(02 May1838)"
    - "(04 05 1911)"
    - "(05/15/1923)"
    - "(06-06-1884)"
    - "(1839-08-29)"
    - "(SEPT. 17,1910)"
    - "(JULY 7,1913)"
    - "(Oct.12,1929)"
    - "(May, 1837)"
    - "(1789?)"
    - "(About:1746-00-00)"
    - "(around 1855)"
    - "(08 March 1893)"
    - "(1/15/1957)"
    - "(11 Aug. 1968)"
    - "(Abt.  1798)"
    - "(April 1817)"
    - "(April 17, 1850)"
    - "(about 1833)"
    """
    if not date_str:
        return None

    # Clean up the string
    s = date_str.strip()
    # Remove parentheses
    s = s.strip("()")
    # Remove trailing question marks
    s = s.rstrip("?")
    # Remove qualifiers (ABT, ABOUT, BEF, AFT, EST, CAL, AROUND, etc.) - with optional colon
    s = re.sub(
        r"^(ABT\.?|ABOUT|BEF\.?|BEFORE|AFT\.?|AFTER|EST\.?|CAL\.?|FROM|TO|BET\.?|AND|CIRCA|CA\.?|AROUND):?\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = s.strip()

    if not s:
        return None

    year: int | None = None
    month: int | None = None
    day: int | None = None

    # Pattern 0: ISO format "1839-08-29" or "1746-00-00" (YYYY-MM-DD)
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        # Handle 00 month/day as defaults
        if month == 0:
            month = 1
        if day == 0:
            day = 1
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 1: "25 NOV 1954" or "25 Nov 1954" (day month year)
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\.?\s*(\d{4})$", s)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).upper().rstrip(".")
        month = MONTH_MAP.get(month_str)
        year = int(match.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 2: "NOV 1954" or "November 1954" or "May, 1837" (month year, optional comma)
    match = re.match(r"^([A-Za-z]+)\.?,?\s*(\d{4})$", s)
    if match:
        month_str = match.group(1).upper().rstrip(".")
        month = MONTH_MAP.get(month_str)
        year = int(match.group(2))
        if month:
            return f"{year:04d}-{month:02d}-01"

    # Pattern 3: "1698" (year only)
    match = re.match(r"^(\d{4})$", s)
    if match:
        year = int(match.group(1))
        return f"{year:04d}-01-01"

    # Pattern 4: "01-27-1920" or "01/27/1920" (MM-DD-YYYY or MM/DD/YYYY)
    match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 5: "04 05 1911" (MM DD YYYY with spaces)
    match = re.match(r"^(\d{1,2})\s+(\d{1,2})\s+(\d{4})$", s)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 6: "02 May1838" (DD MonthYYYY - no space between month and year)
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)(\d{4})$", s)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).upper().rstrip(".")
        month = MONTH_MAP.get(month_str)
        year = int(match.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 7: "08 March 1893" or "11 Aug. 1968" (DD Month YYYY)
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})$", s)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).upper().rstrip(".")
        month = MONTH_MAP.get(month_str)
        year = int(match.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # Pattern 8: "April 17, 1850" or "SEPT. 17,1910" or "Oct.12,1929" (Month DD, YYYY - various spacing)
    match = re.match(r"^([A-Za-z]+)\.?\s*(\d{1,2}),?\s*(\d{4})$", s)
    if match:
        month_str = match.group(1).upper().rstrip(".")
        month = MONTH_MAP.get(month_str)
        day = int(match.group(2))
        year = int(match.group(3))
        if month:
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None


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
        birth_date_string, birth_place = extract_event_details(rec, "BIRT")
        death_date_string, death_place = extract_event_details(rec, "DEAT")

        # Parse date strings into ISO format
        birth_date = parse_date_string(birth_date_string)
        death_date = parse_date_string(death_date_string)

        persons.append(
            Person(
                id=indi_id,
                name=full_name,
                given_name=given_name,
                surname=surname,
                sex=sex,
                birth_date_string=birth_date_string,
                birth_date=birth_date,
                birth_place=birth_place,
                death_date_string=death_date_string,
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
