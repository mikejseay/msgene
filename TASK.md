Currently the plot places nodes in seemingly random positions. Can we try to place them in a more logical way so that the family tree structure is respected?

For “parents above children, siblings aligned”, you want a **hierarchical / layered DAG layout** (often called **Sugiyama-style**). NetworkX’s default layouts are mostly force-directed, so they’ll look “random” for a family tree.

Here are good, established options—starting with the most practical.

## Option 1 (most common): **Graphviz `dot`** via NetworkX + PyGraphviz/Pydot

Graphviz’s `dot` layout is built specifically for hierarchical graphs (top → bottom ranks), and it supports constraints like “these nodes should be on the same level.”

**How to use it from NetworkX**

* NetworkX exposes Graphviz layouts via:

  * `networkx.drawing.nx_agraph.graphviz_layout` / `pygraphviz_layout` (PyGraphviz) ([networkx.org][1])
  * `networkx.drawing.nx_pydot.graphviz_layout` / `pydot_layout` (pydot) ([networkx.org][2])
* The key is: use `prog="dot"` (not `spring_layout`, not `neato`). ([networkx.org][1])

**How to get “siblings on the same level”**
Graphviz lets you group nodes into a subgraph with `rank=same`, which forces them onto the same rank/level. ([Graphviz][3])
In practice, you usually:

1. compute a “generation” number for each node (distance from a chosen root or topological layer), and
2. write a DOT file that creates one `{ rank=same; ... }` block per generation.

NetworkX can also export DOT (`write_dot` / `to_pydot`) so you can generate DOT and then run `dot` yourself. ([networkx.org][4])

**Why this is the default recommendation**

* Best “tree-like” layout quality with minimal effort
* Works for moderate-sized graphs
* Easy export to SVG/PDF/PNG

Perfect—**parent→child** edges are exactly what hierarchical layout engines want. The tricky part is **spouses**, because “spouse edges” are *horizontal constraints* that can confuse a pure DAG layout (and can even create cycles if you treat them like regular directed edges).

The cleanest way to get a classic genealogy chart is:

## 1) Don’t feed `SPOUSE_OF` edges to the hierarchical layout as normal edges

Treat spouse links as **decorations** (drawn on top), or as **special edges with no ranking constraint**, so they don’t pull nodes up/down.

In Graphviz/DOT terms, spouse edges should usually have:

* `constraint=false` (don’t affect layering)
* often `dir=none` (no arrow)
* optionally `style=dashed` or `color=gray` (purely aesthetic)

## 2) If you want *really* good charts: add “family/marriage nodes”

Most genealogy renderers don’t layout spouses as a raw edge. They create a **union node** (sometimes called a family node):

* spouses → (family node)
* (family node) → children

This makes the structure a proper **layered tree of “families”**, and the layout becomes dramatically cleaner.

### Why it helps

* spouses naturally sit on the same generation
* all children hang from the union, so siblings line up nicely
* fewer edge crossings than “two parents both pointing to every child”

---

# Recommended approach with Graphviz `dot`

### A) Build a layout graph (DAG) that *excludes* spouse edges

Use only `PARENT_OF` edges (or better, the union-node model below), then render.

### B) Overlay spouse edges after positions are computed

Either:

* draw them in DOT with `constraint=false`, or
* compute positions via `dot`, then draw spouse lines yourself (matplotlib, plotly, etc.)

---

## Best practice: union-node model (example)

Assume your original graph `G` has:

* `PARENT_OF`: parent → child
* `SPOUSE_OF`: spouse → spouse (or both directions)

We’ll create a new graph `H` for layout:

* Each person remains a node.
* For each spouse pair, create a `FAM_<id>` node.
* Add edges `spouse -> fam` (constraint=false or true; usually true is fine) and `fam -> child` (true).
* Optionally, for single-parent cases, create a `FAM_<parent>_<child>` node so the child still hangs from a “family” anchor (keeps styling consistent).

### DOT rendering via `pydot` (simple and practical)

```python
import networkx as nx
from networkx.drawing.nx_pydot import to_pydot
import itertools

def build_union_layout_graph(G: nx.DiGraph) -> nx.DiGraph:
    H = nx.DiGraph()

    # Copy person nodes
    for n, data in G.nodes(data=True):
        H.add_node(n, **data)

    # Collect spouse pairs (avoid duplicates)
    spouse_pairs = set()
    for u, v, edata in G.edges(data=True):
        if edata.get("type") == "SPOUSE_OF":
            a, b = sorted([u, v], key=str)
            spouse_pairs.add((a, b))

    # Map spouse pair -> family node id
    fam_for_pair = {}
    for (a, b) in spouse_pairs:
        fam_id = f"FAM_{a}_{b}"
        fam_for_pair[(a, b)] = fam_id
        H.add_node(fam_id, shape="point", width="0.05", label="")  # small dot

        # Keep spouses near the family node
        H.add_edge(a, fam_id)
        H.add_edge(b, fam_id)

        # Force spouses on same rank using a helper attribute later in DOT
        H.nodes[a].setdefault("_rank_group", []).append(f"couple_{fam_id}")
        H.nodes[b].setdefault("_rank_group", []).append(f"couple_{fam_id}")

    # Parent -> child edges in original
    parent_of = [(u, v) for u, v, edata in G.edges(data=True) if edata.get("type") == "PARENT_OF"]

    # Build quick lookup of spouses for pairing parents
    spouses_of = {}
    for a, b in spouse_pairs:
        spouses_of.setdefault(a, set()).add(b)
        spouses_of.setdefault(b, set()).add(a)

    # For each child, try to find a spouse pair among its parents (if you have two)
    parents_by_child = {}
    for p, c in parent_of:
        parents_by_child.setdefault(c, []).append(p)

    for child, parents in parents_by_child.items():
        parents = list(dict.fromkeys(parents))  # unique, keep order

        fam_id = None
        if len(parents) >= 2:
            # pick a parent pair that are spouses
            found = None
            for p1, p2 in itertools.combinations(parents, 2):
                a, b = sorted([p1, p2], key=str)
                if (a, b) in fam_for_pair:
                    found = (a, b)
                    break
            if found:
                fam_id = fam_for_pair[found]

        if fam_id is None:
            # fallback: create a single-parent family node (or a generic one for multi-parent non-spouse)
            fam_id = f"FAM_{'_'.join(map(str, parents))}"
            if fam_id not in H:
                H.add_node(fam_id, shape="point", width="0.05", label="")
                for p in parents:
                    H.add_edge(p, fam_id)

        # child hangs from family node
        H.add_edge(fam_id, child)

    return H

def write_family_tree_dot(H: nx.DiGraph, path: str):
    P = to_pydot(H)

    # Use a top-down hierarchical layout
    P.set_rankdir("TB")        # top-to-bottom
    P.set_splines("ortho")     # often nicer for trees; try "true" too
    P.set_nodesep("0.25")
    P.set_ranksep("0.6")

    # Basic node styling (optional)
    for node in P.get_nodes():
        name = node.get_name().strip('"')
        if name.startswith("FAM_"):
            node.set_shape("point")
            node.set_label("")
        else:
            node.set_shape("box")
            node.set_style("rounded")

    # Enforce spouse rank alignment (rank=same) for each couple group
    # We stored a hint in _rank_group; pydot doesn't automatically reflect it, so we rebuild groups:
    # We'll infer couples by the family nodes: spouses point into a FAM node.
    # Create subgraphs: {rank=same; spouseA spouseB}
    for fam in [n for n in H.nodes if str(n).startswith("FAM_")]:
        preds = list(H.predecessors(fam))
        people_preds = [p for p in preds if not str(p).startswith("FAM_")]
        if len(people_preds) == 2:
            sg = PydotSubgraph_rank_same(people_preds)
            P.add_subgraph(sg)

    P.write_raw(path)

def PydotSubgraph_rank_same(nodes):
    import pydot
    sg = pydot.Subgraph(rank="same")
    for n in nodes:
        sg.add_node(pydot.Node(str(n)))
    return sg

# Usage:
# H = build_union_layout_graph(G)
# write_family_tree_dot(H, "tree.dot")
# Then run: dot -Tsvg tree.dot -o tree.svg
```

**What you’ll get**

* `dot` will place generations cleanly (parents above children)
* spouses in a couple tend to sit side-by-side
* siblings align under the same family node

If you *don’t* want union nodes, you can still do it, but you’ll fight more crossings and “V” shapes (two parents both pointing at each child).

---

## Handling `SPOUSE_OF` edges (if you still want them drawn)

If you stick with the union-node model, you often don’t need explicit spouse edges at all (the couple is implied by both connecting to the family node). But if you do want a visible spouse line:

* add an extra DOT edge between spouses with `constraint=false` and `dir=none`

In pydot, you can add those edges after `to_pydot(H)`.

---

## Small but important modeling tips

* **Make spouse edges undirected** conceptually. In a DiGraph you may store both directions; when rendering, treat it as one relationship.
* **Multiple partners**: union-node model handles this naturally: each partnership gets its own `FAM_*` node, and the person connects to multiple family nodes.
* **Unknown parent**: keep a family node with one spouse edge missing; or add a placeholder node (e.g., “Unknown father”).

---

## If you want interactive viewing instead

A fast path: **pyvis** with hierarchical mode can look decent for exploration, but Graphviz usually wins for “printable genealogy chart” quality. If you want, tell me roughly how big your graph is (hundreds of people vs. tens of thousands), and whether you want **descendant charts** (one root → down) or **ancestor charts** (one person → up). Those choices change the best layout settings (and the “generation” definition).
