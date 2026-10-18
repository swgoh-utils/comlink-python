# Contributing to comlink-python

Thanks for your interest in contributing to comlink-python! This guide covers everything you need to get started — from setting up a local dev environment to getting your pull request merged.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Setting Up Your Development Environment](#setting-up-your-development-environment-recommended)
  - [Running a Local Comlink Service](#running-a-local-comlink-service)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
  - [Branching Strategy](#branching-strategy)
  - [Code Style](#code-style)
  - [Writing Tests](#writing-tests)
  - [Commit Messages](#commit-messages)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Issue Guidelines](#issue-guidelines)
- [Release Process](#release-process)
  - [Publishing the docs](#publishing-the-docs)
- [Getting Help](#getting-help)

---

## Code of Conduct

Be respectful, constructive, and patient. We're all here because we enjoy the game and want to build useful tools for the community. Harassment, insults, and unconstructive negativity won't be tolerated.

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold it.

> **Found a security vulnerability?** Please don't open a public issue — follow the private reporting process in [SECURITY.md](SECURITY.md).

---

## Getting Started

### Prerequisites

- **Python 3.10+** (CI tests 3.10 through 3.14)
- **[uv](https://docs.astral.sh/uv/)** — used for dependency management, virtual environments, and running tools
- **Git**
- **Docker** (optional) — for running a local [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) service for integration tests
- **Node.js** (optional) — only for the StatCalc parity tests against the JavaScript reference implementation

#### Optional:
- **GitHub CLI** : https://cli.github.com/

### Setting Up Your Development Environment (Recommended)

1. **Fork and clone the repository**

   ```bash
   gh auth login
   gh repo fork swgoh-utils/comlink-python --clone
   cd comlink-python
   ```

   Or, without the GitHub CLI:

   ```bash
   git clone https://github.com/<your-username>/comlink-python.git
   cd comlink-python
   ```

    #### Configure upstream remote (optional, but highly recommended)

    ```bash
    git remote add upstream https://github.com/swgoh-utils/comlink-python.git
    git config --local branch.develop.remote upstream
    # Safety net: pushes to "upstream" go to your fork instead
    git remote set-url --push upstream git@github.com:<your-username>/comlink-python.git
    ```

2. **Install uv** (if you don't have it)

   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Install dependencies**

   `uv sync` creates the `.venv` virtual environment automatically:

   ```bash
   uv sync --group dev
   ```

   Run tools with `uv run <command>` — there is no need to activate the virtual environment.

4. **Install the pre-commit hooks** (runs Ruff, ty, and commitlint before each commit)

   ```bash
   uvx pre-commit install --hook-type pre-commit --hook-type commit-msg
   ```

5. **Verify the installation**

   ```bash
   uv run python -c "from swgoh_comlink import SwgohComlink; print('OK')"
   ```

### Running a Local Comlink Service

Some tests (integration tests) require a running swgoh-comlink instance. The easiest way is Docker:

```bash
docker run -d --name swgoh-comlink -p 3000:3000 \
  -e APP_NAME=comlink-python-dev \
  ghcr.io/swgoh-utils/swgoh-comlink:4.5.0
```

This starts comlink on `http://localhost:3000`, which is the default URL the library connects to. CI pins the same image tag (see `.github/workflows/integration.yml`).

> **Note:** Unit tests should use mocks and never require a running comlink service. See [Writing Tests](#writing-tests) below.

---

## Project Structure

```
comlink-python/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml          # Bug report template
│   │   ├── config.yml              # Issue chooser links (security, upstream comlink, Discord)
│   │   ├── documentation.yml       # Documentation issue template
│   │   └── feature_request.yml     # Feature request template
│   ├── release-pr/                 # Release PR bodies written by prepare-release.yml
│   ├── tools/                      # Python helpers the workflows run (release + issue bookkeeping)
│   ├── workflows/
│   │   ├── backmerge.yml           # Stages the main → develop back-merge after a release
│   │   ├── ci.yml                  # CI pipeline (lint, type-check, test, docs, build)
│   │   ├── commitlint.yml          # Commit message validation (runs the pre-commit hook)
│   │   ├── docs.yml                # Publishes the versioned docs site (mike → gh-pages)
│   │   ├── integration.yml         # Integration tests against live comlink services
│   │   ├── issue-fixed-in-develop.yml # Comments on issues a merge into develop resolves
│   │   ├── labeler.yml             # Auto-label PRs by file path
│   │   ├── prepare-release.yml     # Regenerates CHANGELOG.md and stages a release branch
│   │   └── release.yml             # Build → PyPI → tag + GitHub Release (version via hatch-vcs)
│   ├── CODEOWNERS                  # Code ownership
│   ├── dependabot.yml              # Automated dependency updates
│   ├── labeler.yml                 # Label-to-path configuration
│   └── pull_request_template.md    # PR checklist template
├── docs/                           # MkDocs site (guides + API reference)
│   ├── api/                        # API reference pages (rendered from docstrings)
│   ├── examples.md                 # Examples overview
│   ├── index.md                    # Documentation home
│   ├── logging.md                  # Logging configuration guide
│   └── migration.md                # v1.x → v2.x migration guide
├── examples/                       # Runnable usage examples (Sync/ and Async/)
├── parity/                         # StatCalc parity harness against the JS reference implementation
├── src/
│   └── swgoh_comlink/
│       ├── StatCalc/
│       │   ├── data_builder/       # GameDataBuilder / GameDataBuilderAsync (game data transformation)
│       │   ├── calculator.py       # StatCalc — local stat/GP calculator (sync)
│       │   └── calculator_async.py # StatCalcAsync
│       ├── helpers/                # Public helper functions, Constants, DataItems (focused private submodules)
│       ├── migrate/                # swgoh-migrate: v1 → v2 migration scanner and rules
│       ├── __init__.py             # Package entry point, public exports
│       ├── _base.py                # SwgohComlinkBase (shared sync/async logic, HMAC signing)
│       ├── exceptions.py           # Custom exception classes
│       ├── globals.py              # Logging configuration
│       ├── py.typed                # PEP 561 marker: the package ships inline type hints
│       ├── retry.py                # Retry/backoff configuration
│       ├── swgoh_comlink.py        # SwgohComlink (sync client)
│       ├── swgoh_comlink_async.py  # SwgohComlinkAsync (async client)
│       └── version.py              # Exposes __version__ (derived from the Git tag via hatch-vcs)
├── tests/
│   ├── examples/                   # Tests for the scripts in examples/
│   ├── integration/                # Tests requiring a running comlink service (opt-in)
│   ├── resources/                  # Test fixture data (example-player.json, gameData.json, ...)
│   ├── statcalc/                   # StatCalc parity tests (opt-in, need Node.js)
│   ├── unit/                       # Mocked unit tests — the bulk of the suite
│   └── conftest.py                 # Shared fixtures and opt-in marker handling
├── CHANGELOG.md                    # Auto-generated from commit history
├── CITATION.cff                    # Citation metadata
├── CODE_OF_CONDUCT.md              # Contributor Covenant code of conduct
├── CONTRIBUTING.md                 # This file
├── LICENSE                         # MIT License
├── README.md
├── SECURITY.md                     # Supported versions and vulnerability reporting
├── SUPPORT.md                      # Where to get help / report what
├── mkdocs.yml                      # Docs site configuration
├── overrides/                      # MkDocs Material theme overrides (version banners)
├── pyproject.toml                  # Project metadata, build config, tool settings
└── uv.lock                         # Locked dependency versions
```

### Key modules at a glance

| Module | Purpose |
|--------|---------|
| `_base.py` | `SwgohComlinkBase` — shared payload construction, HMAC signing, and config for both clients |
| `swgoh_comlink.py` | `SwgohComlink` — synchronous HTTP client (all endpoint methods) |
| `swgoh_comlink_async.py` | `SwgohComlinkAsync` — asynchronous HTTP client (mirrors sync API) |
| `retry.py` | Retry and backoff behavior for transient HTTP failures |
| `StatCalc/calculator.py` | `StatCalc` — local stat and GP calculation for game units |
| `helpers/` | `DataItems` IntFlag enum, `Constants` class, and utility functions split across focused submodules |
| `exceptions.py` | `SwgohComlinkException`, `SwgohComlinkValueError`, and `SwgohComlinkTypeError` |
| `globals.py` | Shared logging setup (`get_logger()`) |
| `version.py` | Exposes `__version__`, derived from the Git tag at build time via hatch-vcs |

---

## Making Changes

### Branching Strategy

| Branch | Purpose |
|--------|---------|
| `develop` | Integration branch. **All contribution PRs target this branch.** |
| `main` | Released code. Only release PRs (from `develop`) and back-merges touch it. |

**For most contributions:**

```bash
git checkout develop
git pull upstream develop
git checkout -b <type>/<short-description>
```

Use a descriptive branch name following the pattern `<type>/<description>`:

```
fix/param-alias-falsy-values
feat/async-client
refactor/split-helpers-module
docs/contributing-guide
```

### Code Style

This project follows standard Python conventions, enforced by [Ruff](https://docs.astral.sh/ruff/) (lint + format) and [ty](https://docs.astral.sh/ty/) (type checking). Please keep these in mind:

**General principles:**

- Follow [PEP 8](https://peps.python.org/pep-0008/) for formatting — `uv run ruff format` handles this for you
- Use **complete type annotations** on all functions, parameters, and return values — the package ships a `py.typed` marker, so downstream users' type checkers rely on them
- Use `from __future__ import annotations` at the top of each module for modern annotation syntax
- Use docstrings (Google style) on all public classes and methods — they are rendered into the API reference
- Keep lines to 120 characters max (the project doesn't enforce 79)

**Naming:**

- Public methods use `snake_case`: `get_player()`, `get_guild()`
- camelCase aliases exist for backward compatibility but **don't add new ones** — they are legacy
- Private/internal methods are prefixed with underscore: `_post()`, `_get_game_version()`
- Constants use `UPPER_SNAKE_CASE`

**Docstring format:**

```python
def get_player(
    self,
    allycode: str | int | None = None,
    player_id: str | None = None,
    enums: bool = False,
) -> dict[str, Any]:
    """
    Get player information from game. Either allycode or player_id must be provided.

    Args:
        allycode: integer or string representing player allycode
        player_id: string representing player game ID
        enums: boolean [Defaults to False]

    Returns:
        A dictionary containing the player information.
    """
```

**Imports:**

- Standard library imports first, then third-party, then local — separated by blank lines (Ruff sorts them)
- Use `from __future__ import annotations` at the top of each module
- Prefer specific imports over wildcard: `from json import dumps, loads`

### Writing Tests

Tests live in the `tests/` directory and use `pytest` (configured in `pyproject.toml`), with [pytest-httpx](https://colin-b.github.io/pytest_httpx/) for mocking HTTP and `pytest-asyncio` (in `auto` mode) for async tests. Run tests with:

```bash
# Run the default (mocked) suite
uv run pytest tests/

# Run a specific test file
uv run pytest tests/unit/test_client_requests.py

# Run with verbose output and coverage
uv run pytest tests/ -v --cov=swgoh_comlink --cov-report=term-missing
```

**Test categories:**

| Type | Location | Requires | How to run |
|------|----------|----------|------------|
| Unit | `tests/unit/` | Nothing | Runs by default |
| Integration | `tests/integration/` | Comlink on `localhost:3000` (and `3001` for HMAC) | `RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration/` |
| Parity | `tests/statcalc/` | Node.js | `RUN_PARITY_TESTS=1 uv run pytest tests/statcalc/` |

All new code should have unit tests. Opt-in categories are skipped automatically unless their environment variable is set.

**Writing a unit test (preferred):**

Mock the HTTP layer with the `httpx_mock` fixture so tests run anywhere without a comlink service. The `comlink` and `call` fixtures in `tests/unit/conftest.py` are parametrized over both `SwgohComlink` and `SwgohComlinkAsync`, so one test body covers both clients:

```python
import json

from pytest_httpx import HTTPXMock


async def test_get_player_by_allycode(comlink, call, httpx_mock: HTTPXMock) -> None:
    """get_player() builds the correct payload for an allycode lookup."""
    httpx_mock.add_response(json={"name": "TestPlayer"})

    result = await call(comlink, "get_player", allycode=123456789)

    request = httpx_mock.get_request()
    assert request is not None
    assert str(request.url) == "http://localhost:3000/player"
    assert json.loads(request.content) == {"payload": {"allyCode": "123456789"}, "enums": False}
    assert result == {"name": "TestPlayer"}
```

**Test file naming:** `test_<feature_or_module>.py`

**What to test:**

- Payload construction — verify the correct JSON payload is built for each method
- Parameter validation — edge cases, invalid inputs, boundary values
- Error handling — how the client handles HTTP errors, bad JSON, connection failures
- Helper functions — each utility function in the `helpers/` package should have its own tests
- Sync/async parity — new client behavior should be exercised against both clients

### Commit Messages

This project uses the [Conventional Commits](https://www.conventionalcommits.org/) / Angular convention with [git-changelog](https://pawamoy.github.io/git-changelog/) to auto-generate `CHANGELOG.md`. Your commit messages directly become release notes, so please follow this format:

```
<type>(<scope>): <short description>
```

**Types that appear in the CHANGELOG:**

| Type | Use for | CHANGELOG section |
|------|---------|-------------------|
| `feat` | New features or capabilities | Features |
| `fix` | Bug fixes | Bug Fixes |
| `perf` | Performance improvements | Performance Improvements |
| `refactor` | Code restructuring (no behavior change) | Code Refactoring |
| `revert` | Reverting an earlier change (`revert: <original subject>`) | Reverts |
| `docs` | Documentation additions or updates | Docs |

Other accepted types — `build`, `deps`, `chore`, `test`, `style`, `ci` — are valid but **not included** in the generated changelog.

> **Changelog.** `CHANGELOG.md` is generated by `git-changelog` from Conventional Commit
> messages — do not edit it by hand. Preview locally with `uv run git-changelog --bumped-version`
> and `uv run git-changelog`. See [Release Process](#release-process) for how releases are cut.

**Scope** is optional but encouraged. Common scopes:

- `core` — changes to the client classes (`swgoh_comlink.py`, `swgoh_comlink_async.py`, `_base.py`)
- `helpers` — changes to the `helpers/` package
- `statcalc` — changes to the `StatCalc/` package
- `hmac`, `async`, `exceptions`, `typing` — focused areas of the clients
- `deps`, `ci`, `docs`, `tests`, `examples`, `release`

Types and scopes are defined in [`.commitlintrc.json`](.commitlintrc.json), the single config used by both the
pre-commit `commit-msg` hook and the CI **Commit Lint** check. Unknown scopes produce a warning, not a failure.
The commitlint, preset and Node versions are pinned once, on the `commitlint` hook in
[`.pre-commit-config.yaml`](.pre-commit-config.yaml); CI runs that same hook, so a message that passes locally
passes in CI.

**Examples:**

```bash
# Good
feat(core): add verify_ssl parameter to SwgohComlink constructor
fix(helpers): remove debug print statement from human_time()
refactor(core): generalize _post() into _request() for GET/POST support
fix: correct param_alias decorator to handle falsy values
chore(deps): bump httpx to 0.28.1
docs: add contributing guide
test: add mocked unit tests for get_player and get_guild

# Bad — too vague, not conventional
updated stuff
fix bug
changes
```

**Multi-line commits** (for complex changes):

```
feat(core): add async client support

Introduces SwgohComlinkAsync using httpx for non-blocking API calls.
Extracts shared payload construction into _ComlinkBase mixin.

Closes #12
```

Mark breaking changes with a `BREAKING CHANGE: <description>` footer — this drives the major version bump.
**Don't use the `feat!:` shorthand:** the changelog generator's Angular convention doesn't recognize it, so the
commit would be left out of the changelog entirely. Commit Lint rejects `!` before the colon for this reason.

> **Gotcha — accidental major bumps.** git-changelog decides a commit is breaking by matching
> `^break(s|ing changes?)?[ :].+$` against **every line** of the message, case-insensitively. So any
> body line that *starts* with `break`, `breaks`, `breaking change` or `breaking changes` followed by a
> space or colon bumps the major version — even mid-paragraph prose that just happened to wrap there:
>
> ```
> docs: explain the changelog conventions
>
> Commits must use the
> BREAKING CHANGE footer (the angular convention ignores "feat!:").   <- bumps to 3.0.0!
> ```
>
> Never start a body line with those words unless it is the intentional `BREAKING CHANGE: <description>`
> footer — reflow the text so the word lands mid-line instead (`Commits must use the BREAKING CHANGE`
> / `footer ...`). Upper-case `BREAKING CHANGE:` with a colon is the only form to use; `BREAKING-CHANGE:`
> is not recognized at all. As a backstop, the **prepare release** workflow lists every line that
> triggered a major in its job summary, and with `bump=auto` it stops unless one of them is the exact
> `BREAKING CHANGE: ` footer. Check before pushing with
> `uv run python .github/tools/breaking_changes.py --bump auto --next-tag "$(uv run git-changelog --bumped-version)"`.

---

## Submitting a Pull Request

1. **Sync your fork with upstream and rebase your branch:**

   ```bash
   git fetch upstream
   git rebase upstream/develop
   ```

   If you have merge conflicts, resolve them locally before pushing.

2. **Run the checks locally** (the pre-commit hooks cover most of this):

   ```bash
   # Lint and format
   uv run ruff check src/ tests/
   uv run ruff format --check src/ tests/

   # Type check
   uv run ty check src/swgoh_comlink/

   # Tests
   uv run pytest tests/
   ```

3. **Push your branch to your fork:**

   ```bash
   git push origin <your-branch-name>
   ```

4. **Open a pull request against `develop`:**

   Using GitHub CLI:

   ```bash
   gh pr create --repo swgoh-utils/comlink-python --base develop --fill
   ```

   Or go to [github.com/swgoh-utils/comlink-python/pulls](https://github.com/swgoh-utils/comlink-python/pulls)
   and click **"New pull request"** → **"compare across forks"** → select `develop` as the base and your fork and branch as the head.

5. **Fill in the PR template.** It asks for:
   - What the change does and why
   - Which issue it addresses (e.g., "Closes #51")
   - Any breaking changes or migration notes
   - How you tested the change
   - A short checklist mirroring the CI checks

   **Linking issues:** use a closing keyword (`Closes #51`, `Fixes #51`, `Resolves #51`), with one
   keyword per issue — `Closes #1, #2` only closes #1. Because PRs merge into `develop` rather than
   the default branch, GitHub won't close the issue at merge time. Instead, a bot comment on the
   issue notes that the fix is in `develop`, and the issue closes automatically when the next
   release merges into `main`.

6. **After submitting:**

   CI checks (lint, type check, tests on Python 3.10–3.14, docs build, package build, commit message validation, and integration tests) run automatically.
   Address any failures before requesting review — the maintainer is automatically
   assigned via CODEOWNERS when a PR is opened.

   If you need to update your PR after feedback, push additional commits to the same
   branch on your fork. The PR updates automatically:

   ```bash
   # Make changes, then:
   git add .
   git commit -m "fix(core): address review feedback"
   git push origin <your-branch-name>
   ```

---

## Issue Guidelines

Before opening an issue, check the [existing issues](https://github.com/swgoh-utils/comlink-python/issues) to avoid duplicates. Usage questions are better asked on [Discord](https://discord.gg/6PBfG5MzR3) — see [SUPPORT.md](SUPPORT.md).

**Bug reports** should include:

- Python version (`python --version`)
- Package version (`python -c "import swgoh_comlink; print(swgoh_comlink.version)"`)
- Comlink service version (if relevant)
- Minimal code to reproduce the issue
- Expected vs actual behavior
- Full traceback (if applicable)

Never paste your comlink `access_key` / `secret_key` into an issue.

**Feature requests** should include:

- What you're trying to accomplish
- How you're currently working around it (if applicable)
- A proposed API or approach (if you have one in mind)

**Labels used in this project:**

| Label | Meaning |
|-------|---------|
| `bug` | Something isn't working correctly |
| `enhancement` | New feature or capability |
| `documentation` | Improvements or additions to documentation |
| `question` | Further information is requested |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention is needed |
| `code maintenance` | Internal cleanup, refactoring, tech debt |
| `test` | Test coverage or infrastructure |
| `dependencies`, `ci`, `build` | Dependency, CI, and build changes (mostly applied automatically) |

---

## Release Process

Releases are handled by the maintainer through GitHub Actions. Contributors don't need to manage versioning or releases, but here's how it works for reference:

1. **prepare release** (`prepare-release.yml`) is dispatched on `develop`. It computes the next version from the Conventional Commits since the last tag (or a chosen `patch`/`minor`/`major` bump), regenerates `CHANGELOG.md`, pushes a `release/vX.Y.Z` branch, and dispatches **Deploy docs** on it. If the computed version is a major, the job summary lists the commit lines that triggered it, and an `auto` bump stops unless one is a real `BREAKING CHANGE:` footer (see [Commit Messages](#commit-messages)).
2. The maintainer opens the release PR from that branch into `main` (a link is in the workflow summary). Its body restates every `Closes #N` from the PRs merged since the last release, so GitHub closes those issues when it merges. CI runs as normal and the PR is merged.
3. **comlink-python release** (`release.yml`) is dispatched on `main`. It reads the version from `CHANGELOG.md`, builds the package — [hatch-vcs](https://github.com/ofek/hatch-vcs) stamps that version, so **no version string is committed to the repo** — and publishes to [PyPI](https://pypi.org/project/swgoh-comlink/) via trusted publishing.
4. Only after a successful publish is the Git tag created and a GitHub Release cut, with release notes auto-generated from the PR history.
5. **back-merge main into develop** (`backmerge.yml`) then stages a branch so `main` can be merged back into `develop`.

This is why conventional commit messages matter — they become the changelog and drive the version bump.

**Version scheme:** [Semantic Versioning](https://semver.org/)

- **Patch** (2.4.x): Bug fixes, documentation
- **Minor** (2.x.0): New features, backward-compatible changes
- **Major** (x.0.0): Breaking API changes

### Publishing the docs

The docs site at [swgoh-utils.github.io/comlink-python](https://swgoh-utils.github.io/comlink-python/) is versioned with [mike](https://github.com/jimporter/mike). Each version has its own copy of the site in a folder on the `gh-pages` branch, and the version picker in the header (Material for MkDocs, `extra.version.provider: mike`) switches between them.

Deploys run **only from `release/*` branches of `swgoh-utils/comlink-python`**. [`docs.yml`](.github/workflows/docs.yml) runs after every push to one that touches the docs. The docs version is the [PEP 440](https://peps.python.org/pep-0440/) version in the branch name (`release/` and an optional `v` are stripped), and [`.github/scripts/docs_version.py`](.github/scripts/docs_version.py) picks the alias from what is already deployed:

| Branch | Version | Alias | Picker title |
|---|---|---|---|
| `release/v2.5.0` (newest stable so far) | `2.5.0` | `latest`, the site default | `2.5.0` |
| `release/v2.4.2` after `2.5.0` is deployed | `2.4.2` | none | `2.4.2` |
| `release/v2.6.0` after `2.5.0` | `2.6.0` | `latest` (moves off `2.5.0`) | `2.6.0` |
| `release/v3.0.0a2` | `3.0.0a2` | `alpha` | `3.0.0a2 (alpha)` |
| `release/v3.0.0b1` | `3.0.0b1` | `beta` | `3.0.0b1 (beta)` |
| `release/v3.0.0rc1` | `3.0.0rc1` | `rc` | `3.0.0rc1 (rc)` |
| `release/v3.0.0.dev1`, `release/v3.0.0a2.dev1` | as named | `dev` | `… (dev)` |
| `release/v3.0.0a2` after `3.0.0a3` is deployed | `3.0.0a2` | none | `3.0.0a2 (alpha)` |
| `release/next`, `release/v2.5.0+local` | the job fails: not a public PEP 440 version | | |

- **Stable versions** take `latest` only when they are at least as new as every stable version already deployed, so a patch for an older line never takes it. The root URL redirects to `latest`.
- **Pre-releases** take the alias for their kind (`alpha`, `beta`, `rc`, or `dev`, which wins for `aN.devM`) only when they are at least as new as every deployed version of that kind. They never touch `latest` or the default, and every page shows a "pre-release" banner ([`overrides/main.html`](overrides/main.html); the deploy sets `DOCS_PRERELEASE`, which feeds `extra.prerelease` in `mkdocs.yml`). Stable versions instead get Material's "older version" banner whenever they are not `latest`.
- **Every release is its own folder.** `2.5.0` and `2.5.1` both stay in the picker; remove ones you no longer want with `mike delete` (below).
- **Nothing else deploys.** Pushes to `main`, `develop` or tags, runs in forks, and manual runs on a non-`release/*` ref skip the job. Deleting a release branch after its PR merges leaves its docs on `gh-pages`.
- **Release timing.** `prepare-release.yml` pushes `release/vX.Y.Z` before the release PR merges and before the PyPI publish, so a stable release's docs can go live (and take `latest`) before the package is on PyPI. That push is made with `GITHUB_TOKEN`, and GitHub does not start workflows from `GITHUB_TOKEN` pushes, so `prepare-release.yml` dispatches **Deploy docs** on the new branch itself (`workflow_dispatch` is the documented exception). Later pushes to the branch, such as review fixes, deploy on their own.
- Deploys queue in the `gh-pages` concurrency group, so they never race.

**Preview the versioned site locally** without touching the remote (the deploy commits to a local `gh-pages` branch only):

```bash
uv sync --group docs
uv run mike deploy --title "2.5.0" 2.5.0 latest   # or: --title "3.0.0a2 (alpha)" 3.0.0a2 alpha
uv run mike set-default latest
uv run mike serve                                 # http://localhost:8000/
git branch -D gh-pages                            # throw the local preview away
```

For a quick single-version preview, `uv run mkdocs serve` is still enough; the version picker only appears under `mike serve`.

#### One-time cutover (maintainer)

The site used to be deployed by `actions/deploy-pages` from `main`, as a single version. To switch to the versioned layout:

1. **Merge the versioned docs setup into `develop`** (the normal PR), so every future `release/vX.Y.Z` branch carries it.
2. **Publish 2.5.0.** `main` is the 2.5.0 release, so cut `release/v2.5.0` from `main`, bring the docs setup onto it (cherry-pick the merged commits from `develop`), and push it to `swgoh-utils/comlink-python`. The deploy creates `gh-pages` with `2.5.0/`, the `latest` alias and the root redirect. The old site stays live while the Pages source is still "GitHub Actions". By hand instead:

   ```bash
   git switch release/v2.5.0
   uv sync --group docs
   uv run mike deploy --push --update-aliases --title "2.5.0" 2.5.0 latest
   uv run mike set-default --push latest
   ```

3. **Switch the Pages source.** First allow the branch to deploy: in **Settings → Environments → `github-pages` → Deployment branches and tags**, add **`gh-pages`** (branch-based Pages builds still deploy through this environment, and it only allowed `main`). Then, in **Settings → Pages → Build and deployment**, change **Source** from "GitHub Actions" to **"Deploy from a branch"**, branch **`gh-pages`**, folder **`/ (root)`**. Check that the root URL opens the 2.5.0 docs.
4. **Protect `gh-pages`** (optional, recommended). Add a ruleset or branch protection rule for `gh-pages` that blocks force pushes and deletion. Leave direct pushes allowed for GitHub Actions: the deploy pushes with the workflow's `GITHUB_TOKEN`, so a rule that requires pull requests or status checks would block it (or add "GitHub Actions" to the bypass list).
5. **Keep the `github-pages` environment.** Branch-based Pages builds (`pages-build-deployment`) deploy through it, so deleting it or removing `gh-pages` from its deployment branches stops the site from updating.

This cutover was completed on 2026-10-18: `2.5.0` (`latest`) and `3.0.0a2` (`alpha`) are published, and `gh-pages` is protected by the **Protect gh-pages** ruleset.

#### Maintaining versions

- **Remove a version** (for example a superseded pre-release): `uv run mike delete --push 3.0.0a1`.
- **Retitle** a version: `uv run mike retitle --push 3.0.0b1 "3.0.0b1 (beta, final)"`.
- **Move an alias by hand**: `uv run mike alias --push --update-aliases 2.5.1 latest`.
- **Rebuild a version** by pushing to (or re-running the workflow on) its release branch; recreate the branch from its tag if it was deleted.

---

## Getting Help

- **Docs:** [swgoh-utils.github.io/comlink-python](https://swgoh-utils.github.io/comlink-python/)
- **Issues:** [github.com/swgoh-utils/comlink-python/issues](https://github.com/swgoh-utils/comlink-python/issues)
- **Discord:** [Join the server](https://discord.gg/6PBfG5MzR3) for real-time discussion
- **Wiki:** [swgoh-comlink wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for general comlink documentation

---

Thank you for contributing! Every fix, feature, test, and docs improvement helps the SWGOH developer community.
