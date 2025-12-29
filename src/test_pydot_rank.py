import pydot

# 1. Create the main graph
P = pydot.Dot("my_graph", graph_type="digraph")
P.set("rankdir", "TB")  # Top-to-bottom (ancestors at top)
P.set("splines", "ortho")  # Orthogonal edges for cleaner tree look
P.set("nodesep", "0.4")  # Horizontal spacing between nodes
P.set("ranksep", "0.6")  # Vertical spacing between ranks

# 2. Define the nodes
dad = pydot.Node(
    name="Dad",
    label="Dad",
    shape="box",
    style="rounded,filled",
    fillcolor="lightblue",
    fontsize="10",
)
fam = pydot.Node(
    name="Family",
    label="",
    shape="point",
    width="0.1",
    height="0.1",
)
mom = pydot.Node(
    name="Mom",
    label="Mom",
    shape="box",
    style="rounded,filled",
    fillcolor="lightpink",
    fontsize="10",
)
son = pydot.Node(
    name="Child",
    label="Child",
    shape="box",
    style="rounded,filled",
    fillcolor="lightblue",
    fontsize="10",
)

# Add nodes to the main graph
P.add_node(dad)
P.add_node(fam)
P.add_node(mom)
P.add_node(son)

# 3. Add edges (this determines the default ranking if "rank=same" wasn't used)
P.add_edge(pydot.Edge(dad, fam))
P.add_edge(pydot.Edge(mom, fam))
P.add_edge(pydot.Edge(fam, son))

# 4. Create a subgraph for the nodes you want on the same rank
# The name can be empty or a specific name
subg = pydot.Subgraph(rank="same")

# 5. Add the specific nodes to this subgraph
subg.add_node(dad)
subg.add_node(fam)
subg.add_node(mom)

# Use invisible edges to force the left-to-right order B -> C -> A -> D
# The 'style="invis"' attribute makes the edges non-visible
subg.add_edge(pydot.Edge(dad, fam, style="invis"))
subg.add_edge(pydot.Edge(fam, mom, style="invis"))

# 6. Add the subgraph to the main graph
P.add_subgraph(subg)

# 7. Write the graph to a file (e.g., an image or a dot file)
P.write("example_rank_same.png", format="png")
# You can also print the DOT source to see the structure
# print(graph.to_string())
