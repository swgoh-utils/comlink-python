# Phase 6 — Optional extras taxonomy + pydantic adapter

**Branch:** `v3/phase-6-extras` (off `v3.0-dev`)

**Status:** complete; ready to merge.

Packaging-heavy phase: declare the v3.0 extras taxonomy in
`pyproject.toml`, wire up `_optional.require()` for friendly missing-
extra errors, and ship the pydantic adapter promised in D6.

## Scope delivered

- [x] **`src/swgoh_comlink/_optional.py`** — `require(extra, *modules)`
      eagerly imports and raises an `ImportError` with the
      copy-pasteable pip install hint on missing modules. Plus
      `has_extra(extra, *modules)` for cheap True/False probes.
- [x] **`pyproject.toml` `[project.optional-dependencies]`** — `cache`
      (`diskcache>=5.6`, `cachetools>=5.3`), `pydantic` (`pydantic>=2.5`),
      `all` (meta-extra combining both). Documented with inline comments
      explaining the deferred / skipped extras.
- [x] **`compat.to_pydantic(struct, model_class)`** — converts any
      `msgspec.Struct` to an instance of a user-defined
      `pydantic.BaseModel` via `BaseModel.model_validate(to_builtins(struct))`.
      Guards behind `_optional.require("pydantic", "pydantic")` so a
      missing extra surfaces with the install hint.
- [x] **`tests/v3/test_optional.py`** — 8 tests covering require/has_extra
      behavior + a real Player → BaseModel round-trip (skipped gracefully
      if `[pydantic]` isn't installed).
- [x] **Coverage ratchet 90 → 92** in pyproject (current actual ~96%).
- [x] All 716 tests pass (709 previous + 7 new); 29 skipped.

## Commit SHAs

- `<TBD>` — `feat(packaging): extras taxonomy + _optional.require + compat.to_pydantic`

## Files modified

```
NEW   src/swgoh_comlink/_optional.py        require() / has_extra()
MOD   src/swgoh_comlink/compat.py           +to_pydantic() adapter
MOD   pyproject.toml                        [project.optional-dependencies]
                                            coverage fail_under: 90 → 92
NEW   tests/v3/test_optional.py             8 tests
NEW   docs/v3/phase-6-report.md
```

## Deviations from the plan

| Plan said | Reality | Why |
|---|---|---|
| Move `click` and `swgoh-migrate` behind `[cli]` extra | **Skipped — no `click` in the codebase.** | The migrate module already uses stdlib `argparse`. Nothing to move. Documented in pyproject comments; `[cli]` extra not declared. |
| `as_model=True` kwarg on every typed endpoint (parallel to `raw=True`) | **Skipped.** Shipped `compat.to_pydantic(struct, model_class)` instead. | The `as_model=True` path requires pre-defining a `BaseModel` for every typed endpoint, doubling the type surface. The dynamic-adapter helper achieves the same outcome without the maintenance debt — caller provides the model, SDK provides the bridge. This is the D6 sub-decision (Phase 3 report) made concrete. |
| Bump `coverage fail_under = 90` per ratchet | 90 → **92** | Modest nudge. Phase 9 final target is 95+; gradual climb. Current actual is ~96.5%. |
| Remove `UP036` and `B904` ruff suppressions (after fixing the underlying issues) | **Skipped.** Suppressions stay. | Pre-existing v2 code (`__init__.py` version block + `exceptions.py` raise chaining). Not Phase 6 blocking; sweep with other v2 cleanup in v3.1. |
| Add `[http2]` / `[brotli]` extras | **Skipped.** | Speculative; per plan "decide at Phase 6 — if no recipe documents the use case, drop them." No recipe yet. |
| Add `[ratelimit]` / `[circuitbreaker]` | **Skipped per ADR-0004.** | Deferred to v3.1-research. |
| Verify `pip install swgoh-comlink[cli]` produces a working `swgoh-migrate` | Not applicable (no `[cli]`). | `swgoh-migrate` works on a base install (stdlib argparse only). |

## v3.0 extras taxonomy (final shape)

| Extra | Adds | Used by | Status |
|---|---|---|---|
| `cache` | `diskcache>=5.6`, `cachetools>=5.3` | Phase 7 (`GameDataCache`) | declared, ready for Phase 7 |
| `pydantic` | `pydantic>=2.5` | `compat.to_pydantic` | declared + used |
| `all` | meta-extra (`cache + pydantic`) | convenience | declared |
| ~~`cli`~~ | n/a | n/a | not declared — no click in codebase |
| ~~`http2`~~ | n/a | n/a | not declared — speculative |
| ~~`brotli`~~ | n/a | n/a | not declared — speculative |
| ~~`ratelimit`~~ | n/a | Phase 8 | **deferred to v3.1** (ADR-0004) |
| ~~`circuitbreaker`~~ | n/a | Phase 8 | **deferred to v3.1** (ADR-0004) |

Base install (`pip install swgoh-comlink`) gives a fully-functional v3
client: typed Structs, lazy imports, retry, profile presets, all v3
goodness. The extras unlock specifically opt-in features.

## `_optional.require` ergonomics

The error message is the contract:

```python
>>> from swgoh_comlink._optional import require
>>> require("cache", "diskcache")
Traceback (most recent call last):
  ...
ImportError: This feature requires the 'cache' extra. Install with: pip install swgoh-comlink[cache]
```

Used by `compat.to_pydantic` today; will be used by Phase 7 in
`_cache.py` to gate diskcache/cachetools imports.

## `compat.to_pydantic` usage pattern

User defines the BaseModel; SDK provides the bridge:

```python
from pydantic import BaseModel, Field
from swgoh_comlink import compat

class MyPlayer(BaseModel):
    name: str
    ally_code: str = Field(alias="allyCode")
    level: int
    model_config = {"populate_by_name": True}

client = SwgohComlink(url="http://comlink.local:3000")
player_struct = client.get_player(allycode=123456789)
player_model = compat.to_pydantic(player_struct, MyPlayer)
```

The conversion goes:
1. `msgspec.to_builtins(struct)` → dict with camelCase keys
2. `MyPlayer.model_validate(dict)` → typed pydantic instance

Pydantic's `Field(alias="...")` handles camelCase ↔ snake_case mapping
in user code — keeps the SDK's pydantic story clean (no double type
hierarchy on our side).

## Open questions

- **Pydantic v1 support?** Currently requires v2 (`model_validate`). If a
  v1 user shows up, document a manual fallback or add a v1 codepath.
- **`as_model=True` ever?** If user feedback says the kwarg-form is the
  ergonomic blocker, revisit in v3.1 with a code-generated pydantic
  module shipped from `msgspec.json.schema(Struct)` output. Not a v3.0
  scope decision.
- **Should `[pydantic]` install pydantic-settings too?** No (env-driven
  config isn't the SDK's domain). If a recipe wants pydantic-settings,
  the user installs it.

## Phase 6 exit criteria check

- [x] `pyproject.toml` declares the v3.0 extras (cache, pydantic, all).
- [x] `_optional.require` works + tested.
- [x] `compat.to_pydantic` ships + tested.
- [x] All v3 + v2 tests still green (716 / 29 skipped).
- [x] Base install (no extras) works — verified by the normal test run.

Ready to merge `v3/phase-6-extras` → `v3.0-dev` (`--no-ff`).
