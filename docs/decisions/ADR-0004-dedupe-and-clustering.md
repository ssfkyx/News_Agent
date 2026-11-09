# ADR-0004: Dedupe via canonical URL, content hash, simhash and union-find

- **Status:** Accepted
- **Date:** 2026-11-08
- **Deciders:** Project owner + implementation agent
- **Supersedes:** —
- **Related ADRs:** see `docs/decisions/README.md`

## Context
The same article appears via multiple channels and languages; exact URL matching is insufficient and embedding-based dedupe would add dependencies and cost.

## Decision
Cluster candidates with union-find using three signals: identical canonical URL/content hash, 64-bit simhash Hamming distance <= 3 combined with title Jaccard >= 0.5, or title Jaccard >= 0.8. Represent each cluster by the highest-weight/earliest item and count distinct sources as heat.

## Rationale
Deterministic, dependency-free and cheap for a few hundred candidates; heat feeds ranking and explains 'also reported by N outlets'.

## Consequences (Costs)
Not semantic: paraphrased headlines can slip through; hence the optional LLM merge pass (ADR-0007). O(n^2) comparison is acceptable at current candidate volume.

## Code locations (traceability)
- `src/newsagent/dedupe.py :: build_clusters, jaccard, hamming`
- `src/newsagent/normalize.py :: simhash64`
- `src/newsagent/select.py :: rank_and_select`
