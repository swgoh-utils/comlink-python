# v3 benchmark fixtures (cassettes)

Real comlink HTTP responses, gzipped on disk, replayed via `pytest-httpx` in tests
and loaded directly by benchmark scripts. See [CONTEXT.md](../../../CONTEXT.md)
for the **Cassette** / **Fixture** distinction.

## Layout

```
fixtures/
├── README.md                 ← this file
├── player_small.json.gz      ← /player response, ~50-unit roster
├── player_large.json.gz      ← /player response, ~250-unit roster
├── guild.json.gz             ← /guild response
├── data.json.gz              ← /data full dump
├── localization_eng_us.json.gz  ← /localization for one locale
├── leaderboard.json.gz       ← /getLeaderboard response
└── metadata.json.gz          ← /metadata response (version-keying tests)
```

## Recording

To (re)populate, configure a comlink URL and run:

```bash
COMLINK_URL=http://localhost:3000 \
SMALL_ROSTER_ALLYCODE=123456789 \
LARGE_ROSTER_ALLYCODE=987654321 \
GUILD_ID=abc123 \
uv run python -m benchmarks.v3._record
```

The recorder writes each response to its canonical filename. Existing files
are overwritten; this is intentional — cassettes are not history.

## Regeneration policy

Re-record **only** when:

1. The upstream comlink service adds or changes an endpoint shape (new field,
   removed field, renamed field). This is what every later benchmark and
   golden test measures against — if cassettes drift, the comparisons lie.
2. The chosen sample players/guild become unrepresentative (e.g. the small
   roster grew to 200 units). Pick new ally codes and re-record everything.

Do **not** re-record on every phase, or to chase real-world game-state
changes. Cassettes are the **frozen baseline**; benchmarks depend on
byte-identical inputs across phases.

After re-recording, run `bench_baseline.py` and verify deltas are within
±5% of the previous baseline before accepting the new cassettes.
