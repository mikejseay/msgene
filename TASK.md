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