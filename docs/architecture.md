# Architecture and routing semantics

## Scope

The repository isolates one engineering claim: a route can be optimized subject to an ordered constraint—become safe first, then remain safe while reaching an eligible shelter. It does not attempt to be a production emergency-navigation system.

## Domain boundary

The routing core understands nodes, undirected weighted edges, a hazardous-node set, and shelters. Polygon handling is an adapter that converts coordinates into that set. JSON parsing and CLI rendering are separate adapters.

This separation prevents map formats, network clients, Flask, Android, or rendering choices from changing the shortest-path logic. A future GIS adapter could replace the small built-in polygon projection while leaving the planner tests unchanged.

## Invariants

- Node and shelter identifiers are unique.
- Every edge and shelter references an existing node.
- Edge weights are finite and strictly positive.
- A boundary point is hazardous.
- Stage one contains hazardous nodes followed by exactly one safe exit node, unless the start is already safe.
- Every node in stage two is safe.
- An eligible shelter must be safe and reachable in the stage-two subgraph.
- The selected route minimizes the sum of both stage distances over all feasible exits and shelters.

## Algorithm

Let `H` be the union of explicitly hazardous nodes and nodes contained in or touching any hazard polygon.

If the start is in `H`, candidate exits are safe nodes adjacent to `H`. One Dijkstra run on the subgraph induced by `H` plus those exits obtains a constrained stage-one path to every reachable exit. Restricting the subgraph means an exit is the first safe node on its path.

For each reachable exit, Dijkstra runs on the subgraph induced by `V - H`. Each candidate shelter is then classified as ineligible, hazardous, unreachable, or reachable. The shortest reachable shelter for that exit becomes its stage-two candidate. The planner finally minimizes:

```text
total(exit, shelter) = distance(start, exit) + distance(exit, shelter)
```

The stable tie order is total distance, stage-one distance, exit identifier, then shelter identifier.

With `X` reachable exits, the current implementation costs `O((X + 1)(V + E) log V)` time and `O(V + E)` working memory per Dijkstra run. A reversed multi-source search could reduce repeated work, but it would complicate per-exit, per-shelter explanations. The current trade-off is appropriate for the small demonstrator.

## Why independent stage minimization is wrong

Minimizing stage one first fixes the nearest exit before considering what lies beyond it. In the committed fixture, that exit costs `2`, followed by `11` to the shelter. Another exit costs `4`, followed by `2`, so the complete constrained optimum is `6`, not `13`.

The planner therefore preserves two named stages without treating them as two independent optimization objectives.

## Failure semantics

Invalid structure is an input error. A valid but disconnected scenario is a planning result with no selected route, not an exception. This distinction lets automation separate malformed data (`3`) from an understood no-route result (`2`).

Candidate diagnostics remain available when no route exists. They identify disconnected exits and shelters rejected for eligibility, hazard membership, or reachability.

## Later extensions

Useful extensions would sit behind explicit interfaces: segment-polygon intersection, directed road restrictions, time-dependent weights, shelter capacity, live hazard freshness, and signed data provenance. They should not be presented as historical features or added without sources and failure policies.

