# v3 research notes

This subtree captures the per-phase work product of the v3 redesign. It is
internal to this research repo and is **not** part of the public mkdocs site
(see ADR-0001 — this repo is local-only until a reintegration decision is made).

## What lives here

```
docs/v3/
├── README.md              ← this file
├── phase-0-report.md      ← Phase 0 baseline + harness writeup
├── phase-1-report.md      ← (created at Phase 1 exit)
├── ...
├── phase-9-report.md      ← final + benchmark roll-up
├── migration.md           ← Phase 9: v2 → v3 migration notes
├── benchmark-report.md    ← Phase 9: consolidated baseline-vs-v3 deltas
└── recipes/               ← Phase 9: usage patterns
    ├── long-running-bot.md
    ├── bulk-analyst.md
    ├── cli-script.md
    └── operator-side-concurrency.md
```

## How to read the phase reports

Each phase exit produces `phase-N-report.md` capturing:

1. **Scope delivered** — which plan tasks landed, which were deferred.
2. **Commit SHAs** — the squashed or merged set on `v3.0-dev`.
3. **Files touched** — `git diff --stat` between the phase start and end.
4. **Deviations from the plan** — anything in the implementation that didn't
   match `v3_implementation_plan.md`, with the *why*.
5. **Open questions** — to-dos / risks visible at phase exit.
6. **Benchmark deltas vs baseline** — table of headline metrics, raw deltas,
   and (where required) statistical significance.

Use `phase-0-report.md` as the template for later phases — the structure should
stay stable so cross-phase comparisons are easy.

## Reading benchmark results

Raw JSON lives at `benchmarks/v3/results/phase-N-*.json`. Phase reports
summarize; the JSON is the source of truth.

Compare any two phases with::

    jq '.results[] | {metric, value, unit, status}' benchmarks/v3/results/phase-0-baseline.json
