# Golden snapshots

Canonical SDK output for each cassette under
[`benchmarks/v3/fixtures/`](../../../benchmarks/v3/fixtures/). Used by the
parametrized tests in [`test_endpoint_goldens.py`](../test_endpoint_goldens.py)
to detect drift across phases.

## What's a golden, vs a cassette?

A **cassette** is the raw HTTP response bytes the SDK receives from comlink
(gzipped). A **golden** is what the SDK *returns* to the caller after any
post-decode transformation (e.g. `get_guild` unwraps the outer `"guild"` key).

For most endpoints the SDK is a passthrough — golden ≈ decoded cassette. For
those endpoints we deliberately *omit* the golden and have the test compare
against the cassette directly, to avoid duplicating ~80 MiB of JSON in git
for `/data` and `~5 MiB` for `/localization`.

| Endpoint | Cassette | Golden? | Reason |
|---|---|---|---|
| `get_game_metadata` | `metadata` | yes | small; canonical reference |
| `get_player(...)` (small) | `player_small` | yes | 94 KiB pretty-printed |
| `get_player(...)` (large) | `player_large` | **no** | 7.5 MiB pretty-printed — diffs unreviewable; test against cassette directly |
| `get_guild(...)` | `guild` | yes | SDK unwraps `"guild"` key |
| `get_leaderboard(...)` | `leaderboard` | yes | small |
| `get_game_data(...)` | `data` | **no** | 80 MiB JSON; test asserts `result == json.loads(cassette)` |
| `get_localization(...)` | `localization_eng_us` | **no** | 5 MiB; same as above |

## Regenerating

```bash
uv run python -m tests.v3._regen_goldens
```

The script wires the cassette server, calls every SDK endpoint, and writes
each result to `golden/<name>.json` (pretty-printed, sorted keys). After
regenerating, review the diff carefully — an unexpected change here means
either the SDK behavior shifted or a cassette was re-recorded with new data.
