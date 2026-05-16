# No `__getitem__` shim on Structs in v3.0

**Status:** accepted

v3.0 returns `msgspec.Struct` instances from every endpoint and does **not** add a `__getitem__` deprecation shim that would let legacy v2-style `player['rosterUnit']` access keep working. Two soft on-ramps from v2 dict access are provided instead:

1. `raw=True` keyword on every endpoint method — bypasses Struct decoding and returns the dict-shaped JSON.
2. `compat.to_dict(struct)` — explicit one-time conversion of any Struct to a dict.

## Considered options

- **The shim with `DeprecationWarning`.** Smoothest possible v2 → v3 transition: existing user code runs unchanged with warnings, removed in v3.2. Rejected because it defeats the type-safety win of Structs (`ty`/mypy can't catch typos in `obj['rosterUnt']` the way they can in `obj.roster_unt`), it requires nontrivial camelCase ↔ snake_case mapping machinery that exposes exactly the friction users would hit, and deprecation warnings in practice get either silenced or pinned-in-config and never actually drive migration.
- **Per-Struct shims only on high-traffic types.** Rejected for documentation friction — "why does `Player` support indexing but `Metadata` doesn't?" becomes a recurring support question.

## Why

v3 is a major version and the dict → Struct migration is the load-bearing reason it exists. A shim signals we don't believe in our own change. `raw=True` and `to_dict()` already give two soft on-ramps; a third pushes past "ergonomic" into "compatibility theater."

## Consequences

- The `swgoh-migrate` v2 → v3 rewriter (Phase 10) carries the migration burden via codemods (`player['rosterUnit']` → `player.roster_unit`).
- Users who depend on dict access pay a one-line cost per call (`raw=True`) or per object (`to_dict(...)`).
- `compat.py` stays small: just `to_dict` and any genuinely lossless conversion helpers.
