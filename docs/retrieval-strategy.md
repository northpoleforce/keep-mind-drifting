# Retrieval Strategy (Draft)

## Objective

Blend short-term conversational recency with long-term memory from Evermemos.

## Weighted Merge

- Cache weight: `0.6`
- Evermemos weight: `0.4`

Score formula:

`final_score = cache_weight * cache_score + memory_weight * memory_score`

## Context Assembly

1. Query session cache (recent local turns).
2. Query Evermemos semantic/history context.
3. Merge, dedupe, and sort by `final_score`.
4. Build LLM prompt context window.
