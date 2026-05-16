# Standalone research repo, not a branch of upstream

**Status:** accepted

v3 of `swgoh_comlink` is developed in a separate local clone at `/Users/marktripod/code/comlink-python-v3/`, decoupled from the public `swgoh-utils/comlink-python` repo. Once research is mature, a separate decision will be made about how (or whether) to re-incorporate changes upstream — by cherry-picking, opening a PR, forking, or abandoning.

## Why

A worktree- or branch-based v3 inside the public repo coupled v3's experimental cadence to upstream's release cycle, blocked v3 work on unrelated v2.1-track merges (`develop` → `main`), and complicated the gitignore / topology mechanics. A standalone clone lets v3 evolve `pyproject.toml`, dependency floors, the package layout, even the package name without affecting upstream contributors, and removes any risk of accidentally pushing experimental commits.

## Consequences

- `~/code/comlink-python/` is never touched by v3 work.
- No PRs, tags, releases, or pushes from this repo until a reintegration decision is made.
- Pulling in upstream bug fixes (e.g. the arena-payout fixes currently on `develop`) is a manual `git fetch upstream && git cherry-pick` step rather than automatic.
- The package keeps the name `swgoh_comlink` during research to minimize diff churn; renaming is a reintegration-time concern.
