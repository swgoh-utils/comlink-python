# Runbook — publishing the v3.0.0a1 alpha (fork-hosted)

Operator checklist for cutting the first public v3 alpha per
[ADR-0008](../../adr/0008-pre-release-distribution-via-github-releases.md)
(including the 2026-07-12 fork-hosting addendum). Everything below is
executed by the maintainer; nothing here runs automatically.

**Preconditions** (already true as of this writing):

- All release prep is committed on the local `release/v3.0.0a1` branch.
- `docs/v3/releases/v3.0.0a1.md` exists — `alpha-release.yml` uses it as
  the GitHub Release body (`body_path`), so the run fails without it.
- Local gates are green: ruff, ty, codegen drift, pytest (≥ 95 % coverage
  gate), `uv build`.

## 1. Create the fork

```bash
gh repo fork swgoh-utils/comlink-python --clone=false
```

Creates `MarTrepodi/comlink-python` (public — forks of public repos
cannot be private; pushing the branch publishes the full v3 history).

## 2. Push the release branch to the fork

```bash
cd ~/code/comlink-python-v3
git remote add fork https://github.com/MarTrepodi/comlink-python.git
git push fork release/v3.0.0a1
```

Do **not** push to `origin` (the upstream swgoh-utils repo) — that is
exactly what the fork-hosting addendum avoids.

## 3. Prepare the fork's settings (one-time, in the GitHub UI)

1. **Enable Actions** — Actions are disabled by default on new forks:
   fork → *Actions* tab → enable workflows.
2. **Workflow permissions** — `alpha-release.yml` declares
   `contents: write` (tag + Release) and `id-token: write` (Sigstore
   keyless signing) in its own `permissions:` block; confirm the repo
   setting *Settings → Actions → General → Workflow permissions* does
   not restrict below that (default "Read repository contents" is fine
   — job-level `permissions:` override it — but if the org policy
   disallows elevation, switch to "Read and write permissions").
3. **Labels** (optional but recommended) — dispatch the `label-sync`
   workflow so the `v3` label exists before bug reports arrive.

## 4. Dry run

Fork → *Actions* → **alpha-release** → *Run workflow*:

- **Branch:** `release/v3.0.0a1` (the workflow guards on `release/v*`)
- **version:** `3.0.0a1`
- **dry_run:** `true`

The run executes the full gate suite (tests, ruff, ty, codegen
drift), builds wheel + sdist via hatch-vcs
(`SETUPTOOLS_SCM_PRETEND_VERSION`), and Sigstore-signs the artifacts —
but creates **no tag and no Release**. Inspect the run summary and the
uploaded artifacts; confirm the wheel is
`swgoh_comlink-3.0.0a1-py3-none-any.whl` and its metadata URLs point at
the fork.

## 5. Real run

Re-dispatch with the same inputs but **dry_run: `false`**. This:

1. Re-runs all gates and the build/sign steps
2. Creates and pushes the annotated tag `v3.0.0a1`
3. Creates the **prerelease** GitHub Release with the signed wheel,
   sdist, signature bundles, and `SHA256SUMS`, using
   `docs/v3/releases/v3.0.0a1.md` as the body

## 6. Post-release smoke test

From a clean directory (not the repo):

```bash
uv venv smoke-v3 && source smoke-v3/bin/activate
uv pip install https://github.com/MarTrepodi/comlink-python/releases/download/v3.0.0a1/swgoh_comlink-3.0.0a1-py3-none-any.whl
python -c "import swgoh_comlink; print(swgoh_comlink.version)"   # -> 3.0.0a1
```

Then one live typed call against a local comlink (e.g. run
`examples/typed/Sync/get_player.py` with `COMLINK_URL` set). Also
verify the `git+` install path resolves the new tag:

```bash
uv pip install --dry-run "git+https://github.com/MarTrepodi/comlink-python.git@v3.0.0a1"
```

## 7. Announce + wrap up

- Confirm the Release page renders the notes and the install commands
  copy-paste cleanly (they should match
  [`install-alpha.md`](../install-alpha.md)).
- Per ADR-0008's release-branch convention, merge `release/v3.0.0a1`
  back to its source branch with a
  `chore(release): resume dev cycle at 3.0.0a2.dev0` commit when
  development resumes.

## Rollback (if the real run shipped something broken)

A GitHub Release can be deleted and its tag removed
(`git push fork :refs/tags/v3.0.0a1`) — but anyone may already have
installed the wheel, so prefer shipping a fixed `3.0.0a2` over mutating
`3.0.0a1`. Deleting a Release is acceptable only in the first minutes
after publication (e.g. a broken artifact discovered by the smoke
test).
