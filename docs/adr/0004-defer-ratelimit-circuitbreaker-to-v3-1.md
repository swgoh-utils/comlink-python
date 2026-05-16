# Defer rate-limit and circuit-breaker work to v3.1

**Status:** accepted

v3.0 does **not** ship `[ratelimit]` or `[circuitbreaker]` extras, the `DualRateLimiter`, the `bulk_get_*` helpers, the `purgatory`-backed circuit breaker, or the recipe docs around them. These move to a `v3.1-research` milestone in this repo, gated on real bot-operator demand.

## Why

The original v3 plan's Phase 8 added significant scope — three new optional dependencies (`aiometer`, `aiolimiter`, `purgatory`), two new extras to document and test (`[ratelimit]`, `[circuitbreaker]`), four benchmark scripts, dual sync/async limiter implementations, and recipe documentation — for unproven demand. No specific operator has asked for it; the `(80, 1)` / `(18, 1)` defaults in the original plan were inferred from comlink's documented limits, not from observed cascading-failure scenarios.

Shipping v3.0 without Phase 8 keeps the milestone tight (msgspec, lazy imports, sibling clients, GameDataCache, `[cli]`, `[cache]`, `[pydantic]`) and avoids paying for speculative breadth before the core wins are validated.

## Consequences

- v3.0 phase count drops from 10 to 9 (Phase 8 removed; old Phases 9, 10 renumber).
- Operators who want concurrency control on v3.0 use vanilla `asyncio.Semaphore` patterns at the call site — documented as a recipe.
- When demand materializes, v3.1 can ship the rate-limit work as a standalone release without forcing the rest of v3.0 to wait.
