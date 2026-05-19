# Pre-release distribution via GitHub Releases (alpha / beta / rc)

**Status:** accepted (2026-05-19). Supersedes ADR-0001 §"Consequences"
line 14 ("No PRs, tags, releases, or pushes from this repo until a
reintegration decision is made") **only for PEP 440 pre-release
versions distributed as GitHub Releases**. All other clauses of
ADR-0001 stay in force.

v3 has shipped four research phases (v3.0 through v3.3) with full
parity tests, async-aware client surfaces, typed `/data` segments,
GameDataCache, bimorphic StatCalc, and a pure-Python restructure
delivering +16.3 % on the hot path. 888 tests pass on the integration
branch. The work is far enough along that community early adopters
can usefully install + report bugs.

ADR-0001's "no tags or releases" clause was written when v3's surface
was unstable and a pre-release would have been irresponsible. That
condition no longer holds for the v3.0.0 series of alpha releases.
But the bigger ADR-0001 decision — *whether and how to reintegrate
with upstream* — is a separate, larger conversation that we are not
yet ready to have. This ADR carves a narrow exception so we can ship
something tryable without prejudging the reintegration question.

## Decision

**Permitted under this ADR:**

- PEP 440 pre-release versions (`aN`, `bN`, `rcN`) tagged on this
  repo, distributed as **GitHub Releases only**. The wheel + sdist
  are attached as Release assets; the canonical install instructions
  are `pip install <github-release-url-to-wheel>` or
  `pip install git+https://...@v3.0.0aN`.
- A new workflow `.github/workflows/alpha-release.yml` that builds,
  signs (Sigstore keyless OIDC), and creates the GitHub Release.
- An auxiliary `.github/labels.yml` + `label-sync` workflow that
  manages the `v2` / `v3` issue labels so triagers can disambiguate
  bug reports.

**Forbidden under this ADR:**

- Any push to PyPI from this repo. The existing
  `.github/workflows/release.yml` (which targets PyPI via OIDC
  trusted publishing) is **not** triggered by this exception. PyPI
  publication remains gated on reintegration with upstream.
- Any non-pre-release tag (`3.0.0`, `3.0.1`, `3.1.0`, …). Final
  releases on this repo would commit to a successor relationship
  with upstream that this ADR explicitly does not establish.
- Tagging directly on a research branch. Pre-release tags MUST
  originate from a `release/v*` branch cut from the relevant
  research branch (or `main`); the alpha-release workflow enforces
  this with a branch-ref guard.

**Stability ladder for pre-releases under this ADR:**

| Channel | Stability commitment |
|---|---|
| `aN` (alpha) | **None.** API may change without warning between `aN` and `a(N+1)`. Use for evaluation and bug reporting only. |
| `bN` (beta) | **Aspirational.** Breaking changes possible but the maintainer commits to documenting them in the release notes. |
| `rcN` (release candidate) | **Full.** Breaking changes only for security fixes; otherwise treat as the final release surface. |

If the maintainer wants to ship a final `3.0.0` (no `aN`/`bN`/`rcN`
suffix), that requires either (a) reintegration with upstream and
publishing through `.github/workflows/release.yml` to PyPI, or
(b) a new ADR that supersedes this one and explicitly permits final
releases from the research repo.

## Sunset

This ADR's exception expires when **whichever first occurs:**

1. Reintegration with upstream completes (at which point `release.yml`
   takes over and this exception is moot), OR
2. **2027-05-19** (twelve months from acceptance). At that point a
   new ADR re-evaluates whether the pre-release channel has met its
   goals or should be retired.

If neither occurs by the sunset date, alpha distribution must pause
pending an ADR review.

## Consequences

- Community early adopters can install + report bugs against
  v3.0.0aN without waiting for reintegration. ADR-0001's intent
  (no surprise upstream contamination) is preserved because PyPI
  remains untouched and the `swgoh_comlink` PyPI namespace
  continues to point at v2.x.
- A `v3` GitHub issue label (synced from `.github/labels.yml`)
  disambiguates v3-alpha bug reports from v2-stable bug reports.
  The bug-report and feature-request issue templates require a
  Version dropdown so triagers can filter cleanly.
- The release branch convention (`release/v*` cut from a research
  branch, tagged via the alpha-release workflow, then merged back
  to the source research branch with a `chore(release): resume
  dev cycle at <next>.dev0` commit) is now the established pattern
  for any pre-release this repo cuts.

## Alternatives considered + rejected

- **Rename to `swgoh-comlink-next` and publish to PyPI.** Breaks
  the succession path to v2's PyPI name; eventual reintegration
  would require a second rename. Rejected.
- **Publish to PyPI under `--pre` (still as `swgoh_comlink`).**
  Irreversible in the namespace sense — once a pre-release ships
  to PyPI under the v2 package name, the maintainer relationship
  to upstream is implicitly redefined. Narrows escape hatches.
  Rejected.
- **Private TestPyPI distribution.** Adds install friction for
  community testers (custom `--index-url`). The audience for this
  alpha is broader than the kind of testers who would tolerate
  that. Rejected.
- **Keep ADR-0001 unchanged and ship as "unofficial" artifacts
  outside any release process.** Loses the discoverability,
  signing, and bug-report-channel benefits of GitHub Releases.
  Rejected.

## References

- ADR-0001 — Standalone research repo, not a branch of upstream
- ADR-0005 — Typed-dict client split (the surface this alpha exposes)
- ADR-0006 — StatCalc internals overhaul (v3.2 winners that ship)
- ADR-0007 — StatCalc rewrite evaluation (v3.3 winners that ship;
  native variants stay on throwaway prototype branches)
