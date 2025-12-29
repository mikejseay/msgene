Python tools for working with genealogy / family trees.

We use `uv` for dependency management and `numpy` style docstrings.

## Common file formats / serializations

### 1) **GEDCOM** (`.ged`)

The long-standing interchange format for genealogy apps. It’s a line-oriented, tag-based text format (not CSV/JSON), and it models *Individuals* plus *Families* and links them by IDs. There are multiple versions in the wild; the current “official” spec line is maintained at gedcom.io. ([FamilySearch GEDCOM][1])

Practical notes:

* Many exports you’l`l find are **GEDCOM 5.5 / 5.5.1**-ish; **GEDCOM 7** exists, but support varies by software. ([FamilySearch GEDCOM][2])
* GEDCOM can also be paired with packaging approaches (e.g., including media). FamilySearch describes a “GEDZip” packaging idea in the GEDCOM 7 ecosystem. ([FamilySearch][3])

## Common *internal* data representations (what you build in code)

### A) **Graph model (recommended for most projects)**

Represent people as nodes and relationships as edges:

* `PARENT_OF` / `CHILD_OF`
* `SPOUSE_OF` (often many-to-many, time-bounded)
* optionally “event” nodes (Birth, Marriage, Death) if you want citations/sources cleanly

Why it’s good: ancestry, descendant, cousin/relationship queries become graph traversals.

### B) **Relational model**

Tables like:

* `person(id, name, sex, ...)`
* `parent_child(parent_id, child_id, relationship_type)`
* `family(id, ...)` plus membership tables

Why it’s good: easy to persist in SQLite/Postgres; strong constraints; good for apps.

## Python-first libraries and tools

### Parse/import GEDCOM (your `.ged`)

Two commonly used Python parsers:

* **`ged4py`** – focused on parsing GEDCOM efficiently (not writing), supports GEDCOM 5.5.1; good when you want to read a big `.ged` and load it into your own model. ([PyPI][6])
* **`python-gedcom`** – another GEDCOM parsing/manipulation library; its docs note support around GEDCOM 5.5. ([python-gedcom.readthedocs.io][7])

### Work with the data once parsed (analysis + querying)

* **NetworkX** (Python) for ancestry/descendant queries, lowest-common-ancestor, etc., once you map your people to a directed graph. NetworkX includes standard DAG/tree algorithms (ancestors, LCA, etc.). ([networkx.org][9])
* **SQLite** for a personal project backend (simple, portable) and keep a clean edge table for relationships. (A very common pattern is “parse GEDCOM → SQLite → query”.)

### Visualization

* **Graphviz** is a classic choice to render trees/graphs cleanly (either directly or via Python bindings). Many genealogy apps also use Graphviz-style layouts.

### “Bigger” tool options (useful even if you’re coding)

* **Gramps desktop**: import/export GEDCOM, work with `.gramps`, and inspect tricky edge cases (multiple marriages, unknown parents, citations). It’s a great “reference implementation” to compare your output against. ([Wikipedia][8])
* **Neo4j** (optional): if you *really* want graph-native storage + Cypher queries, Neo4j has published examples of importing GEDCOM and modeling parent relationships. ([Graph Database & Analytics][10])

## A practical workflow for a personal Python project

1. **Parse**: `ged4py` (or `python-gedcom`) to read `.ged` into objects. ([ged4py.readthedocs.io][11])
2. **Normalize** into your own schema:

   * people table
   * relationships edge table (`parent`, `child`, `spouse`, with attributes like dates/notes/source pointers)
3. **Store**: SQLite (or Postgres) and/or build an in-memory NetworkX graph for algorithms. ([networkx.org][9])
4. **Validate**:

   * check for cycles in parentage
   * check impossible ages / date ordering
5. **Export**:

   * for sharing with other genealogy tools: GEDCOM (harder because writing needs to match dialects)
   * for your own usage: JSON/CSV + a clear versioned schema

If you tell me what GEDCOM version your file is (or which product exported it—Ancestry, MyHeritage, etc.), I can suggest which parser tends to be the least painful and what edge cases to expect (character encoding, custom tags, etc.).

[1]: https://gedcom.io/specs/?utm_source=chatgpt.com "GEDCOM Specifications"
[2]: https://gedcom.io/specifications/FamilySearchGEDCOMv7.html?utm_source=chatgpt.com "The FamilySearch GEDCOM Specification"
[3]: https://www.familysearch.org/en/gedcom/?utm_source=chatgpt.com "GEDCOM Genealogy Tools"
[4]: https://www.familysearch.org/innovate/gedcom-x?utm_source=chatgpt.com "GEDCOM X"
[5]: https://www.gramps-project.org/wiki/index.php/Gramps_XML?utm_source=chatgpt.com "Gramps XML"
[6]: https://pypi.org/project/ged4py/?utm_source=chatgpt.com "ged4py"
[7]: https://python-gedcom.readthedocs.io/?utm_source=chatgpt.com "Module gedcom — python-gedcom 2.0.0 documentation"
[8]: https://en.wikipedia.org/wiki/Gramps_%28software%29?utm_source=chatgpt.com "Gramps (software)"
[9]: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.ancestors.html?utm_source=chatgpt.com "ancestors — NetworkX 3.6.1 documentation"
[10]: https://neo4j.com/blog/developer/discover-auradb-free-importing-gedcom-files-and-exploring-genealogy-ancestry-data-as-a-graph/?utm_source=chatgpt.com "Discover AuraDB Free: Importing GEDCOM & Genealogy ..."
[11]: https://ged4py.readthedocs.io/en/latest/usage.html?utm_source=chatgpt.com "Usage — GEDCOM parser for Python 0.4.4 documentation"
