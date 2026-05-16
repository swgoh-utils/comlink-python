# comlink-python v3.0 — Phased Implementation Plan (research repo edition)

This is a **standalone research repo** at `/Users/marktripod/code/comlink-python-v3/`, cloned from `swgoh-utils/comlink-python@main` at SHA `4a064f1`. It is decoupled from upstream (see [ADR-0001](docs/adr/0001-standalone-research-repo.md)). Domain glossary lives in [CONTEXT.md](CONTEXT.md).

**Operating rules for Claude Code (apply to every phase):**

- All work happens inside `/Users/marktripod/code/comlink-python-v3/` on branch `v3.0-dev` or a per-phase feature branch `v3/phase-N-<slug>`.
- Each phase commits its work onto its feature branch and merges back into `v3.0-dev` on completion. **Do not `git push`**, do not open PRs, do not tag, do not release. This repo is local-only until a separate reintegration decision is made.
- If upstream lands a bug fix that v3 needs (e.g. an arena-payout fix from `develop`), pull it in via `git fetch upstream && git cherry-pick <sha>` (after a one-time `git remote add upstream https://github.com/swgoh-utils/comlink-python.git`).
- Use `git stash` or files under `/tmp` for throwaway scratch work; keep the working tree clean between phases.
- At the end of each phase, produce a **phase report** at `docs/v3/phase-N-report.md` summarizing: scope delivered, commit SHAs, files touched, deviations from the plan, open questions, benchmark results vs. baseline.
- Before declaring a phase complete, run the full test suite (`uv run pytest`) and the phase's benchmark harness; both must be green / show expected deltas.
- Benchmarks live in `benchmarks/v3/` and are independent of the test suite. Each benchmark script writes a JSON result to `benchmarks/v3/results/<phase>-<date>.json` for diffing.

---

## Phase 0 — Baseline + benchmark harness

**Branch:** `v3.0-dev` (already created)

**Goals:**
1. Capture a frozen v2.0.x **baseline** of every metric v3.0 intends to improve, so later claims are defensible.
2. Stand up the benchmark harness that all later phases reuse.

**Tasks:**

1. Confirm starting state: `pwd` reports `/Users/marktripod/code/comlink-python-v3`, `git status` is clean (except for the initial v3 setup artifacts — `CONTEXT.md`, `docs/adr/*`, this file, bumped `pyproject.toml`, `version.py` at `3.0.0.dev0`), `git log -1` shows the clone-point SHA.
2. Create `benchmarks/v3/` with:
   - `_harness.py` — shared helpers: `measure(callable, *, warmup=3, iters=20)` returning median + p95 + stdev; `track_memory(callable)` using `tracemalloc` for peak/current; `track_import_time(module)` using `python -X importtime` parsed via subprocess; `Reporter` class that writes `{phase, metric, value, unit, git_sha, timestamp}` JSON.
   - `fixtures/` directory: **real recordings** from a live comlink (yours or `comlink.swgoh.dev`), gzipped on disk. Capture `/player` (small ~50-unit and large ~250-unit rosters), `/guild`, `/data` (full dump), `/localization` (one locale), `/getLeaderboard`. These cassettes are the input to every later micro-benchmark and must be byte-identical across phases.
   - `_record.py` — one-shot script that talks to a configured comlink URL and writes the cassettes. Re-run only when comlink server endpoints change; document policy in `benchmarks/v3/fixtures/README.md`.
   - `bench_baseline.py` — runs every benchmark below against the current v2.0.x code (initial state of `v3.0-dev`) and writes `results/phase-0-baseline.json`.
3. Add `docs/v3/` directory with `README.md` describing the plan, and `phase-0-report.md` template.

**Baseline metrics to capture:**

| Metric | How to measure | Why it matters |
|---|---|---|
| **Cold import time** | `python -X importtime -c "import swgoh_comlink"` parsed; median of 10 runs | Phase 5 (lazy `__getattr__`) targets this |
| **Installed wheel size** | `pip download swgoh-comlink==2.0.7 --no-deps -d /tmp/wheels` + `du -sb` on the whole resolved tree from a clean venv | Phase 6 (extras taxonomy) shifts this |
| **Site-packages size after install** | `du -sb $(python -c 'import site; print(site.getsitepackages()[0])')` minus baseline empty-venv size | Same as above |
| **`get_player` end-to-end latency (small roster, ~50 units)** | Median of 20 calls against fixture-backed mock server; warmup 3 | Phase 2 retry/transport overhead, Phase 3 msgspec decode |
| **`get_player` end-to-end latency (large roster, ~250 units)** | Same, on the large-roster cassette | Same |
| **`get_data` decode time** | Time only the parsing step (`response.content` → object), excluding network | Phase 3 msgspec is the headline win |
| **`get_data` peak memory during decode** | `tracemalloc.start(); ...; peak = tracemalloc.get_traced_memory()[1]` | Phase 3 |
| **`get_data` resident object size (post-decode)** | `pympler.asizeof(decoded)` on the returned object graph | Phase 3 |
| **100× `get_player` concurrent (async)** | `asyncio.gather` of 100 calls against mock; total wall time + peak memory | Phase 2 |
| **Method-body duplication ratio** | Custom script: AST-diff each `get_*` in `swgoh_comlink.py` vs `swgoh_comlink_async.py`; report % of overlapping lines | Phase 4 |
| **Import-graph cost** | `python -X importtime ... 2>&1 \| awk` to sum cumulative ms for the whole `swgoh_comlink.*` tree | Phase 5 |

**Phase 0 exit criteria:** `bench_baseline.py` runs clean; `results/phase-0-baseline.json` exists; all numbers reproducible across 3 runs within ±5%. Cassettes are gzipped and checked in (expect ~15-20 MB total — `/data` alone is ~15 MB gzipped; the full-payload size is load-bearing for Phase 3's headline numbers and cannot be reduced). No code changes to `src/swgoh_comlink/`.

---

## Phase 1 — Test harness (mock comlink + fixtures)

**Branch:** `v3/phase-1-test-harness` off `v3.0-dev`.

**Goals:** Make later phases safe to refactor by providing a deterministic local comlink. No production code changes.

**Tasks:**
1. Add `tests/v3/` with a **`pytest_httpx`-backed mock server fixture** that replays the Phase 0 cassettes (with gzip decompression in the loader).
2. Add a `conftest.py` fixture `recorded_comlink` returning a context manager wrapping `httpx_mock` with all standard endpoints pre-registered.
3. Add **golden-output tests**: for each endpoint, assert the v2.0.x current behavior produces a known JSON shape. These tests become the regression net — they keep passing through every phase, and any intentional breaking change in Phase 3 must be reflected as an explicit golden-file update.
4. **Coverage ratchet:** in `pyproject.toml` (or a new `coverage.toml`), set `fail_under` to `max(current_coverage, 50)`. Each subsequent phase nudges this number up by whatever its new code adds. The 90% target is the Phase 9 exit criterion, not a Phase 1 gate.

**Benchmarking:** none new. Re-run `bench_baseline.py` through the mock to confirm fixture-backed numbers match real-network numbers within ±10%.

**Phase 1 exit criteria:** `uv run pytest tests/v3/` is green; golden files committed in `tests/v3/golden/`; coverage gate is ratchet-style.

---

## Phase 2 — Core resilience layer (retries, transport, options merge)

**Branch:** `v3/phase-2-resilience-core` off `v3.0-dev` after Phase 1 lands.

**Goals:** Land the **non-breaking** parts of the new client architecture first: retry/backoff, the `_base_client.py` skeleton, `with_options`, the inject-or-own httpx client policy. No public API breaks yet — v2 method signatures and return types unchanged.

**Tasks:**
1. Add `stamina>=24.3` to `[project.dependencies]`.
2. Create `src/swgoh_comlink/_retry.py` with:
   - `_should_retry(status: int) -> bool` — true for {408, 425, 429, 500, 502, 503, 504}.
   - `_parse_retry_after(headers, cap_seconds=120.0) -> float | None`.
   - `retrying_sync(*, attempts, on)` and `retrying_async(...)` — thin stamina wrappers preconfigured with full-jitter backoff.
3. Create `src/swgoh_comlink/_base_client.py` housing:
   - `_BaseClient` with: `_build_request`, `_decode` (currently delegates to `response.json()` — msgspec swap is Phase 3), `_should_retry`, `_map_error`, `with_options(**overrides) -> Self` shallow-clone.
   - `NOT_GIVEN` sentinel and `NotGiven` type.
4. Refactor `SwgohComlink` and `SwgohComlinkAsync` to **inherit from `_BaseClient`** while keeping all method bodies. The `_request` method moves up; endpoint wrappers stay where they are.
5. Add `http_client=` constructor kwarg on both classes; track ownership and only auto-close when owned.
6. Raise default `keepalive_expiry` to 30s; add three named pool presets (`DEFAULT_LIMITS`, `BOT_LIMITS`, `BULK_LIMITS`) selectable via `profile="default"|"bot"|"bulk"`.
7. Wire retries into the unified `_request()` path. Default `max_retries=3`; opt-out via `max_retries=0`.

**Benchmarking — Phase 2 deltas:**

- **`bench_retry_overhead.py`**: 1000 successful (200 OK) requests through the mock; compare median latency with `max_retries=0` vs `max_retries=3`. **Expected:** <2% overhead on the happy path.
- **`bench_retry_recovery.py`**: mock returns 429 with `Retry-After: 1` on attempt 1, then 200; assert total wall time is `1.0s + base_latency ± 0.1s`. Also run for 503 (no Retry-After, expect exponential backoff: ~0.5s ± jitter for first retry).
- **`bench_pool_warm.py`**: 50 sequential `get_player` calls with a 10s sleep between calls 25 and 26 → confirm call 26 reuses the connection under new defaults (`keepalive_expiry=30s`).

**Phase 2 exit criteria:** all v2.0.x tests still pass; Phase 0 baselines unchanged within ±5%; retry-recovery benchmarks meet expectations.

---

## Phase 3 — Typed responses via `msgspec.Struct`

**Branch:** `v3/phase-3-msgspec-models` off `v3.0-dev` after Phase 2.

**Goals:** The single highest-impact change in v3.0. Replace dict returns with `msgspec.Struct` types for every endpoint. This **is** a breaking change; ship the `raw=True` escape hatch and the `compat.to_dict()` helper in this same phase. See [ADR-0003](docs/adr/0003-no-getitem-shim-on-structs.md) for why no `__getitem__` shim.

**Tasks:**
1. Add `msgspec>=0.18` to `[project.dependencies]`.
2. Create `src/swgoh_comlink/_models.py` with Structs for every endpoint return type. Start with the small ones (`Metadata`, `Enums`, `Events`, `NameSpaces`, `SegmentedContent`) to validate the pattern, then `Player`, `Unit`, `Skill`, `Mod`, `GuildProfile`, `LeaderboardEntry`, `GameDataSegment`, `Localization`.
3. For each Struct, decide `gc=False` per the msgspec rule of thumb: leaf data nodes that never reference back into a cycle get `gc=False` for the ~75× GC speedup; container Structs holding lists of children stay `gc=True`.
4. Instantiate one **module-level `msgspec.json.Decoder(T)` per response type** in `_base_client.py`. Never construct decoders per-call.
5. Change `_BaseClient._decode` to read `response.content` (bytes, not text) and dispatch through the cached decoder.
6. Add `raw=True` keyword to every endpoint method; when set, bypass decoding and return the raw `dict | list`.
7. Create `src/swgoh_comlink/compat.py` with `to_dict(struct) -> dict` (one-liner via `msgspec.to_builtins`) and a deprecation warning saying it will be removed in v3.2.
8. Update golden-output tests from Phase 1: assert Struct attribute access produces the same data the dict access did.

**Benchmarking — Phase 3 deltas (headline numbers, full statistical rigor applies):**

- **`bench_decode_speed.py`**: load each fixture as raw bytes; measure (a) `json.loads(bytes)`, (b) `orjson.loads(bytes)`, (c) `msgspec.json.decode(bytes)` (untyped), (d) `decoder.decode(bytes)` (typed Struct). Report all four for `/data`, `/localization`, `/player` (small + large), `/getLeaderboard`. **Expected:** (d) is 3–5× faster than (a) on `/data`; (d) ≥ (c) ≥ (b) > (a) on every fixture. If (d) is slower than (c), the Struct schema is wrong (probably has `dict[str, Any]` fields defeating the optimization).
- **`bench_decode_memory.py`**: `tracemalloc.start(); decoded = decode(bytes); peak = tracemalloc.get_traced_memory()[1]; del decoded; gc.collect()`. Report peak for each parser × each fixture. **Expected:** msgspec-typed peak is 4–6× lower than stdlib json on `/data`.
- **`bench_object_size.py`**: `pympler.asizeof(decoded)` for the post-decode object graph. **Expected:** Struct graph is 40–60% smaller than equivalent dict graph.
- **`bench_attribute_access.py`**: 1M iterations of `obj.roster_unit[0].definition_id` vs `obj['rosterUnit'][0]['definitionId']`. Sanity check; Struct should win by ~10–20%.
- **End-to-end re-run of Phase 0 `bench_baseline.py`**: `get_data` and large-roster `get_player` numbers should show the projected improvements. **This is the headline result of v3.0 — capture it carefully.**
- **Memory regression guard:** create `tests/v3/test_memory_budgets.py` asserting peak memory for `get_data()` stays under a fixed budget (e.g., 80 MiB for the standard fixture).
- **Statistical rigor:** Phase 3 is the only phase where Mann-Whitney U at p<0.05 is required on every comparative claim (because these are the public marketing numbers). Use `scipy.stats.mannwhitneyu`; reject any "improvement" with p > 0.05.

**Phase 3 exit criteria:** every endpoint returns Structs by default; `raw=True` returns dicts; `compat.to_dict()` round-trips lossless; all benchmark deltas meet or exceed projections; golden tests updated.

---

## Phase 4 — Sibling-on-base sync/async collapse

**Branch:** `v3/phase-4-sibling-clients` off `v3.0-dev` after Phase 3.

**Goals:** Reduce remaining ~60–75% method-body duplication to 6–10 lines per endpoint. Pure structural cleanup riding on top of Phase 2's `_base_client.py` and Phase 3's typed models.

**Tasks:**
1. For each endpoint, rewrite the sync and async wrappers to the minimal shape:
   ```python
   def get_player(self, allycode=None, *, player_id=None):
       req = self._build_request("/player", _player_payload(allycode, player_id))
       resp = self._send(req)
       return self._decode(resp.content, Player)
   ```
2. Extract `_player_payload`, `_guild_payload`, etc. into a `_payloads.py` module (pure functions shared between sync and async).
3. Collapse helper async siblings (`async_get_gac_brackets`, `async_get_guild_members`, `async_get_current_gac_event`) — pick whichever signature is cleaner, delete the duplicate, re-export the surviving name from both client classes.
4. Re-run the duplication-ratio benchmark from Phase 0.

**Benchmarking:**

- **`bench_duplication.py`**: re-run the AST-diff script. **Expected:** method-body duplication drops from baseline ~65% to <10%.
- **`bench_line_counts.py`**: SLOC delta. Tracking metric, not a pass/fail.
- **Re-run end-to-end latency**: pure refactor — if numbers move >5%, something is wrong.

**Phase 4 exit criteria:** duplication ratio <10%; no end-to-end regression beyond ±5%; tests green; LOC reduction documented.

---

## Phase 5 — Lazy imports + package structure

**Branch:** `v3/phase-5-lazy-imports` off `v3.0-dev` after Phase 4.

**Goals:** Drop cold import time from ~15–40 ms to ~2 ms. Reorganize subpackages per the blueprint.

**Tasks:**
1. Rewrite `__init__.py` with PEP 562 `__getattr__`:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from ._sync_client import SwgohComlink
       from ._async_client import SwgohComlinkAsync
       # ... full public surface here for IDE/mypy support

   _LAZY = {
       "SwgohComlink": "._sync_client",
       "SwgohComlinkAsync": "._async_client",
       # ...
   }

   def __getattr__(name):
       if name in _LAZY:
           import importlib
           mod = importlib.import_module(_LAZY[name], __package__)
           value = getattr(mod, name)
           globals()[name] = value
           return value
       raise AttributeError(name)
   ```
2. Verify no eager `import httpx` happens at package load. Move any module-level httpx imports inside functions or under `TYPE_CHECKING`.
3. Rename `src/swgoh_comlink/StatCalc/` → `src/swgoh_comlink/statcalc/` (PEP 8 compliance). Use `git mv` so history follows.
4. Move builders into `src/swgoh_comlink/builders/` with `_base.py`, `_sync.py`, `_async.py`.
5. Set up `cli/` subpackage with the existing `migrate.py` logic plus a shim that produces a friendly error if `click` isn't installed (Phase 6 will move `click` to `[cli]`).
6. Verify all imports still resolve via the `__getattr__` route: `python -c "from swgoh_comlink import SwgohComlink, SwgohComlinkAsync; print(SwgohComlink)"`.

**Benchmarking:**

- **`bench_import_time.py`**: `python -X importtime -c "import swgoh_comlink" 2>&1 | tail -1`. Median of 20 runs after fresh interpreter starts (use `subprocess.run` per run to avoid module caching). **Expected:** ≥10× reduction vs baseline. Sub-target: `import swgoh_comlink` should not trigger import of `httpx`, `httpcore`, `anyio` — verify by parsing the importtime output.
- **`bench_import_then_use.py`**: cold `import swgoh_comlink` + `SwgohComlink(url=...)`. Should equal baseline import time (instantiation triggers the deferred httpx import). The "total cost of first use" sanity check.
- **`bench_script_startup.py`**: representative 1-liner script end-to-end. **Expected:** ≥30 ms reduction for short-lived CLI users.

**Phase 5 exit criteria:** cold import time hits target; `httpx`-not-loaded assertion passes; renames don't break tests.

---

## Phase 6 — Optional extras taxonomy + CLI under `[cli]`

**Branch:** `v3/phase-6-extras` off `v3.0-dev` after Phase 5.

**Goals:** Codify the extras taxonomy. Move `click` and `swgoh-migrate` behind `[cli]`.

Extras shipped in v3.0: `[cli]`, `[cache]`, `[pydantic]`, `[all]`. Optionally `[http2]` and `[brotli]` if a use case materializes during Phases 7–9; otherwise drop them. **Not shipped in v3.0:** `[ratelimit]`, `[circuitbreaker]` (see [ADR-0004](docs/adr/0004-defer-ratelimit-circuitbreaker-to-v3-1.md)).

**Tasks:**
1. Update `pyproject.toml`:
   - `[project.dependencies]` v3.0 core: `httpx>=0.28`, `msgspec>=0.18`, `stamina>=24.3`.
   - Add `[project.optional-dependencies]`:
     - `cli = ["click>=8.1"]`
     - `cache = ["diskcache>=5.6", "cachetools>=5.3"]`
     - `pydantic = ["pydantic>=2.5"]`
     - `all = ["swgoh_comlink[cli,cache,pydantic]"]`
   - Bump `coverage fail_under` per the ratchet — Phase 6 typically adds packaging code, not many lines, so this is a small bump.
   - Remove `UP036` and `B904` suppressions after fixing the underlying issues (version block in `__init__.py`, exception chaining in `exceptions.py`).
2. Implement `_optional.py` helper:
   ```python
   def require(extra: str, *modules: str):
       try:
           return [importlib.import_module(m) for m in modules]
       except ImportError as e:
           raise ImportError(
               f"This feature requires the '{extra}' extra. "
               f"Install with: pip install swgoh-comlink[{extra}]"
           ) from e
   ```
3. Gate each optional feature behind `require(...)` at the import site.
4. **`[pydantic]` adapter (per D6 sub-decision):** implement as the dynamic-adapter path — at call time, `BaseModel.model_validate(msgspec.to_builtins(struct))`. Do **not** hand-maintain parallel pydantic types. Provide an `as_model=True` keyword (parallel to `raw=True`) that returns the pydantic Model instead of the Struct.
5. Verify `pip install swgoh-comlink[cli]` produces a working `swgoh-migrate` and a base install does not.

**Benchmarking:**

- **`bench_install_size.py`**: in a fresh venv, `pip install ./dist/swgoh_comlink-3.0.0.dev0-py3-none-any.whl` and measure `du -sb` of site-packages minus empty-venv baseline. Repeat for each extras combination. **Expected:** base ≈ 2.2 MB; `[cli]` adds ~350 KB; `[pydantic]` adds ~5 MB; `[all]` ≈ 8 MB.
- **`bench_resolve_time.py`**: `pip install --dry-run` timing for each extras combination.
- **`bench_import_with_extras.py`**: confirm `import swgoh_comlink` time is the same whether or not extras are installed.

**Phase 6 exit criteria:** all extras combinations install cleanly; base install matches target size; missing-extra error messages are helpful; pydantic adapter round-trips a `Player` Struct losslessly.

---

## Phase 7 — `GameDataCache` (diskcache + version-keyed)

**Branch:** `v3/phase-7-game-data-cache` off `v3.0-dev` after Phase 6.

**Goals:** Eliminate ~99% of `/data` and `/localization` traffic for repeat users via a version-aware on-disk cache. Behind `[cache]`.

**Tasks:**
1. Create `src/swgoh_comlink/_cache.py` with:
   - `GameDataCache(cache_dir=None, version_ttl_seconds=30)` — wraps `diskcache.Cache` with msgspec.msgpack serialization.
   - Keys are `(version, segment, locale)` tuples; `tag=version` on every set for evict-by-tag.
   - `get_or_fetch(client, segment, locale)` that probes `client.get_metadata()` (cached for 30s via in-memory `cachetools.TTLCache`), checks for cached segment, fetches+stores on miss.
2. Rewrite `GameDataBuilder` to be **lazy per segment** atop `GameDataCache`. Each accessor (`builder.units()`, `builder.skills()`, etc.) triggers at most one segment fetch.
3. Add `builder.preload_all(concurrency=4)` that fans out segment fetches in parallel (`asyncio.gather` async; `concurrent.futures.ThreadPoolExecutor` sync).
4. Document the cache directory location (XDG-compliant: `~/.cache/swgoh-comlink/` on Linux, `~/Library/Caches/swgoh-comlink/` on macOS).

**Benchmarking:**

- **`bench_cache_cold_vs_warm.py`**: time `builder.units()` cold (fetch + decode + write) vs warm (cache hit + msgpack decode). **Expected:** warm 100–1000× faster; absolute warm latency <5 ms for `units`.
- **`bench_cache_version_invalidation.py`**: prime cache, mock metadata returning a new version, call `builder.units()` — should evict and refetch cleanly. Assert on disk size that old tagged entries are gone.
- **`bench_cache_disk_size.py`**: measure disk usage after full preload. Compare msgpack vs json. **Expected:** msgpack ~2–3× smaller.
- **`bench_full_data_pull_first_run_vs_repeat.py`**: end-to-end. **Expected:** second run ≥50× faster.

**Phase 7 exit criteria:** all cache benchmarks pass projections; cache survives process restart; version invalidation works; sync and async paths share serialization format.

---

## ~~Phase 8 — Rate limiting + circuit breaker~~ (deferred to v3.1)

Phase 8 from the original plan is **deferred** to a `v3.1-research` milestone in this repo. See [ADR-0004](docs/adr/0004-defer-ratelimit-circuitbreaker-to-v3-1.md). Operators needing concurrency control on v3.0 use vanilla `asyncio.Semaphore` patterns — document a recipe in Phase 9 (renumbered from old Phase 9).

---

## Phase 8 — Streaming, `raw_request`, `healthcheck`, async StatCalc (was Phase 9)

**Branch:** `v3/phase-8-ergonomics` off `v3.0-dev` after Phase 7.

**Goals:** Land the "high-value" tier from the blueprint that doesn't fit elsewhere.

**Tasks:**
1. `stream=True` on `get_data()` and `get_localization()` returning an `httpx` streaming context manager yielding bytes chunks.
2. `client.raw_request(method, path, payload=None)` escape hatch returning the raw `httpx.Response`.
3. `client.healthcheck(timeout=5.0) -> bool` hitting `/enums` with a short timeout for bot startup probes.
4. Async-aware StatCalc: `calc_roster_stats_async(...)` offloads CPU work to `asyncio.to_thread` for small rosters and to a `ProcessPoolExecutor` for rosters above a threshold (benchmark to find threshold).

**Benchmarking:**

- **`bench_streaming_memory.py`**: `get_data(stream=True)` piped to `/dev/null`; compare peak memory vs `get_data()`. **Expected:** streaming peak ≈ chunk size (~64 KB) vs full ~80 MiB.
- **`bench_statcalc_threshold.py`**: time `calc_roster_stats` on rosters of {10, 50, 100, 250, 500}, comparing inline / `asyncio.to_thread` / `ProcessPoolExecutor`. **Expected:** to_thread wins below ~100 units; process pool wins above.
- **`bench_event_loop_blocking.py`**: event-loop responsiveness during concurrent `calc_roster_stats_async` on a large roster. **Expected:** heartbeat stays within 10 ms.

**Phase 8 exit criteria:** streaming holds memory flat regardless of payload size; StatCalc threshold documented and codified as the default; event-loop responsiveness verified under load.

---

## Phase 9 — Migration tooling, compat layer, internal notes, final benchmark report (was Phase 10)

**Branch:** `v3/phase-9-migration-docs` off `v3.0-dev` after Phase 8.

**Goals:** Make v2 → v3 a smooth path for the future, **if** reintegration ever happens. Since this is a research repo, these are internal notes, not user-facing docs.

**Tasks:**
1. Extend `swgoh-migrate` with a v2 → v3 ruleset covering dict-indexing → Struct attribute access (`player['rosterUnit']` → `player.roster_unit`), removed `async_*` helper aliases, CLI extras requirement, any renames. Codemod-style rewrites via `libcst` or `redbaron`.
2. Flesh out `compat.py`: ensure `to_dict()` round-trips every Struct losslessly. (No `__getitem__` shim — see [ADR-0003](docs/adr/0003-no-getitem-shim-on-structs.md).)
3. Write `docs/v3/migration.md` with side-by-side v2 → v3 examples — for future-self reference and any eventual upstream PR.
4. Write `docs/v3/recipes/` covering: long-running bot setup (retries + cache); bulk analyst setup; short-lived CLI script setup with `[cli]` only; **operator-side concurrency control via `asyncio.Semaphore`** (in lieu of the deferred `[ratelimit]`).
5. **Coverage exit gate:** ratchet `fail_under` to 90 here. If real coverage isn't there, the gap is either uncovered code that should be tested or dead code that should be deleted.
6. Run **`bench_v3_final.py`** — full re-run of every benchmark from every phase against `v3.0-dev` HEAD. Generate `docs/v3/benchmark-report.md` with tables comparing v2.0.7 baseline to v3.0.

**Phase 9 exit criteria:** final benchmark report shows every projected improvement either met or documented; migration tooling exercised on a sample v2-using script; coverage ≥90%; `v3.0-dev` HEAD is the artifact ready for whatever reintegration path comes next.

---

## Cross-cutting benchmarking principles

- **Always run from a clean venv** for install-size and import-time measurements. Use `uv venv` or `python -m venv` then `pip install -e .[extras]`.
- **Always warm up** before timing. Three throwaway iterations is the minimum; httpx connection-pool benchmarks need more.
- **Report median + p95, not mean.** A single GC pause skews the mean; medians are robust.
- **Default rule for blocking on regressions:** block only on regressions of **≥5% AND p<0.05**. Smaller regressions get a footnote in the phase report. Mann-Whitney U at p<0.05 is required **only on Phase 3 headline numbers** (decode speed, decode memory, object size, end-to-end latency on `/data` and large-roster `/player`) since those are the load-bearing claims of v3. Other phases use the simpler ±5% delta tolerance.
- **Capture the git SHA** in every result JSON so reports can be regenerated post-hoc.
- **Pin the Python version** used for benchmarks in `benchmarks/v3/python-version` and refuse to run if `sys.version_info` doesn't match.
- **No network in micro-benchmarks** except where the benchmark name explicitly says "end-to-end." Use `pytest-httpx` fixtures everywhere else.
- **Compare apples to apples on memory.** `tracemalloc` peak for "how much did this allocation campaign cost"; `pympler.asizeof` for "how big is this object graph at rest." Don't mix them.
- **A regression in any phase's benchmark is a blocker for that phase** (under the ≥5% + p<0.05 rule). Don't accumulate small slowdowns waiting to fix them later.

---

## Branch dependency graph

```
v3.0-dev   (integration; local only, never pushed)
  ├── v3/phase-1-test-harness        (Phase 1)
  ├── v3/phase-2-resilience-core     (Phase 2)
  ├── v3/phase-3-msgspec-models      (Phase 3, needs P2)
  ├── v3/phase-4-sibling-clients     (Phase 4, needs P3)
  ├── v3/phase-5-lazy-imports        (Phase 5, needs P4)
  ├── v3/phase-6-extras              (Phase 6, needs P5)
  ├── v3/phase-7-game-data-cache     (Phase 7, needs P6)
  ├── v3/phase-8-ergonomics          (Phase 8, needs P7)
  └── v3/phase-9-migration-docs      (Phase 9, needs P8)
```

Each feature branch is merged back into `v3.0-dev` (with `--no-ff` for visible phase boundaries) on phase exit.

---

## Reintegration with upstream (out of scope)

Explicitly **not** part of this plan. Once `v3.0-dev` HEAD passes Phase 9 exit, separately evaluate: cherry-pick selected commits onto an upstream feature branch; open a v3 PR; fork the project under a new name; or shelve. Until then, this repo is local research and produces no public artifacts.
