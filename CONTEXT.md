# comlink-python (v3 research repo)

This repo is a standalone research effort to redesign the `swgoh_comlink` SDK around `msgspec.Struct` typed responses, lazy imports, and a unified sync/async client architecture. It is decoupled from the public `swgoh-utils/comlink-python` repo (see [ADR-0001](docs/adr/0001-standalone-research-repo.md)).

## Language

### Domain (game)

**Ally code**:
A 9-digit numeric identifier for a player account, e.g. `123456789`.
_Avoid_: account number, player number.

**Player**:
A single SWGOH account, identified by **Ally code** or `playerId`.
_Avoid_: User, account.

**Roster**:
The full collection of **Units** belonging to a **Player**.
_Avoid_: collection, lineup.

**Unit**:
A single playable character or ship, with skills, mods, and gear.
_Avoid_: character, hero, toon.

**Guild**:
A group of up to 50 **Players** with shared activities.

**Segment**:
A subset of the `/data` game-data dump (units, skills, mods, gear, …) addressable independently for caching.
_Avoid_: section, slice.

**Locale**:
A language code (e.g. `eng_us`, `fre_fr`) addressing a `/localization` payload.
_Avoid_: language, translation.

### Protocol & client

**Endpoint**:
A comlink HTTP path: `/player`, `/guild`, `/data`, `/localization`, `/getLeaderboard`, etc.
_Avoid_: route, API, method.

**Comlink**:
The upstream HTTP service (`swgoh-utils/swgoh-comlink`) this SDK speaks to.
_Avoid_: server, backend, API.

**Profile**:
A connection-pool preset (`default` / `bot` / `bulk`) selecting tuned httpx limits for a use case.
_Avoid_: config, preset, tier.

**Extra**:
A pip optional-dependency group (`[cli]`, `[cache]`, `[pydantic]`, …).
_Avoid_: feature flag, plugin.

### Typed-response model (v3 specific)

**Struct**:
A `msgspec.Struct` typed return value. Default v3 return shape for every endpoint.
_Avoid_: model, dataclass, schema.

**Model**:
A `pydantic.BaseModel`. Returned only when the user opts into the `[pydantic]` adapter.
_Avoid_: Struct (these are distinct), record.

**Raw mode**:
The `raw=True` keyword on any endpoint method, bypassing Struct decoding and returning the dict-shaped JSON.
_Avoid_: legacy mode, dict mode, v2 mode.

### Benchmarking & testing

**Cassette**:
A recorded comlink HTTP response stored as `*.json.gz` under `benchmarks/v3/fixtures/`. Replayed via `pytest-httpx` to make benchmarks reproducible without a live comlink.
_Avoid_: recording, snapshot.

**Fixture**:
A `pytest` test fixture. Distinct from a **Cassette** — fixtures may *load* cassettes.

**Baseline**:
The frozen v2.0.x metric set captured in Phase 0; the comparison anchor for every later benchmark in this repo.
_Avoid_: reference, control.

**Golden test**:
A regression test that asserts an endpoint produces a recorded canonical output. Becomes the safety net for refactoring across phases.
_Avoid_: snapshot test, characterization test.

## Relationships

- A **Player** belongs to at most one **Guild** and has exactly one **Roster** of many **Units**.
- An **Endpoint** call returns a **Struct** by default, a `dict` under **Raw mode**, or a **Model** if `[pydantic]` is installed and selected.
- `/data` returns multiple **Segments**; `/localization` returns one payload per **Locale**. Both are version-keyed and cacheable.
- A **Cassette** records one **Endpoint**'s response; a **Fixture** loads one or more cassettes for a test.
- The **Baseline** is the v2.0.x measurement set; every phase benchmarks its changes *against* the baseline, not against the previous phase.

## Flagged ambiguities

- "Account" was avoided entirely — both **Player** (game) and a hypothetical site-login user are sometimes called "account" in upstream conversation. Use **Player** for the game entity.
- "Model" can mean a pydantic `BaseModel` or, casually, "the data model of the SDK." Reserve **Model** for the pydantic sense; use "the SDK's typed response surface" for the broader concept.
- "Config" — overloaded between `pyproject.toml` settings, the **Profile** pool preset, and runtime `with_options(...)` overrides. Use the specific term in each context.

## Example dialogue

> **Dev:** "If I call `get_player(allycode, raw=True)`, do I still go through the **Profile** pool?"
> **Maintainer:** "Yes — **Raw mode** only changes decoding. The httpx **Profile** still applies, and so do retries, since those live in `_BaseClient._request` above the decode step."
>
> **Dev:** "And if I install `[pydantic]`, does `raw=True` short-circuit that too?"
> **Maintainer:** "Right. `raw=True` returns `dict | list` regardless of whether `[pydantic]` is installed. The pydantic **Model** path only kicks in when you ask for it explicitly via the adapter."
