# Contributing to comlink-python

Thanks for your interest in contributing to comlink-python! This guide covers everything you need to get started — from setting up a local dev environment to getting your pull request merged.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Setting Up Your Development Environment](#setting-up-your-development-environment)
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
- [Getting Help](#getting-help)

---

## Code of Conduct

Be respectful, constructive, and patient. We're all here because we enjoy the game and want to build useful tools for the community. Harassment, insults, and unconstructive negativity won't be tolerated.

---

## Getting Started

### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **[uv](https://docs.astral.sh/uv/)** — used for dependency management and virtual environments
- **Git**
- **Docker** (optional) — for running a local [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) service for integration tests

#### Optional:
- **GitHub CLI** : https://cli.github.com/

### Setting Up Your Development Environment (Recommended)

1. **Fork and clone the repository**

   ```bash
   gh auth login
   gh repo fork swgoh-utils/comlink-python
   ```
   
   ```bash
   git clone https://github.com/<your-username>/comlink-python.git
   cd comlink-python
   ```
    #### Configure upstream remote (optional, but highly recommended)

    ```bash
    git remote add upstream https://github.com/swgoh-utils/comlink-python.git
    git config --local branch.main.remote upstream
    git remote set-url --push upstream github@github.com:<your-username>/comlink-python.git
   ```
   
2. **Install uv** (if you don't have it)

   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Create a virtual environment and install dependencies**

   ```bash
   uv venv
   source .venv/bin/activate    # Linux/macOS
   # .venv\Scripts\activate     # Windows

   uv sync --group dev
   ```

4. **Verify the installation**

   ```bash
   uv run python -c "from swgoh_comlink import SwgohComlink; print('OK')"
   ```

### Running a Local Comlink Service

Some tests (integration tests) require a running swgoh-comlink instance. The easiest way is Docker:

```bash
docker run -d --name swgoh-comlink -p 3000:3000 ghcr.io/swgoh-utils/swgoh-comlink:latest
```

This starts comlink on `http://localhost:3000`, which is the default URL the library connects to.

> **Note:** Unit tests should use mocks and never require a running comlink service. See [Writing Tests](#writing-tests) below.

---

## Project Structure

```
comlink-python/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml          # Bug report template
│   │   └── feature_request.yml     # Feature request template
│   ├── workflows/
│   │   ├── ci.yml                  # CI pipeline (lint, type-check, test, docs, build)
│   │   ├── commit-lint.yml         # Commit message validation (wagoid action)
│   │   ├── commitlint.yml          # Commit message validation (npm-based)
│   │   ├── integration.yml         # Integration tests against live comlink services
│   │   ├── labeler.yml             # Auto-label PRs by file path
│   │   ├── release.yml             # Semantic release → PyPI publish
│   │   └── test.yml                # Quick test + docs build
│   ├── CODEOWNERS                  # Code ownership
│   ├── dependabot.yml              # Automated dependency updates
│   ├── labeler.yml                 # Label-to-path configuration
│   └── pull_request_template.md    # PR checklist template
├── docs/
│   ├── api/
│   │   ├── async.md                # SwgohComlinkAsync API reference
│   │   ├── comlink.md              # SwgohComlink API reference
│   │   ├── exceptions.md           # Exception classes reference
│   │   ├── helpers.md              # Helper functions reference
│   │   └── statcalc.md             # StatCalc API reference
│   ├── index.md                    # Documentation home
│   ├── logging.md                  # Logging configuration guide
│   └── migration.md                # v1.x → v2.x migration guide
├── examples/                       # Usage examples for each endpoint
├── src/
│   └── swgoh_comlink/
│       ├── StatCalc/
│       │   ├── data_builder/
│       │   │   ├── _builder_base.py  # Shared game data transformation logic
│       │   │   ├── builder.py        # Sync GameDataBuilder
│       │   │   └── builder_async.py  # Async GameDataBuilderAsync
│       │   ├── __init__.py           # StatCalc package exports
│       │   ├── calculator.py         # Local stat/GP calculator (sync)
│       │   └── calculator_async.py   # Async StatCalcAsync
│       ├── helpers/
│       │   ├── __init__.py           # Helpers package exports
│       │   ├── _arena.py             # Arena payout time calculations
│       │   ├── _constants.py         # Game constants and enum lookups
│       │   ├── _data_items.py        # DataItems IntFlag for game data collections
│       │   ├── _decorators.py        # Timing and debug logging decorators
│       │   ├── _gac.py               # Grand Arena Championship bracket helpers
│       │   ├── _game_data.py         # Raid IDs, datacrons, localization, units
│       │   ├── _guild.py             # Guild member extraction helpers
│       │   ├── _omicron.py           # Omicron ability detection
│       │   ├── _sentinels.py         # Sentinel values (REQUIRED, MISSING)
│       │   ├── _stat_data.py         # Stat name/ID mapping tables
│       │   └── _utils.py             # Enum lookup, file I/O, path utilities
│       ├── migrate/
│       │   ├── __init__.py           # Migration tool entry point
│       │   └── ...                   # v1 → v2 migration scanner and rules
│       ├── __init__.py               # Package entry point, public exports
│       ├── _base.py                  # SwgohComlinkBase (shared sync/async logic)
│       ├── exceptions.py             # Custom exception classes
│       ├── globals.py                # Logging configuration
│       ├── swgoh_comlink.py          # SwgohComlink (sync client)
│       ├── swgoh_comlink_async.py    # SwgohComlinkAsync (async client)
│       └── version.py                # Package version (managed by hatch)
├── tests/
│   ├── integration/                  # Tests requiring a running comlink service
│   ├── resources/                    # Test fixture data (example-player.json, etc.)
│   ├── statcalc/                     # StatCalc-specific tests (import, parity, offline)
│   ├── unit/                         # Mocked unit tests for sync/async clients
│   ├── conftest.py                   # Shared pytest fixtures and markers
│   └── test_*.py                     # Additional test modules
├── pyproject.toml                    # Project metadata, build config, tool settings
├── uv.lock                           # Locked dependency versions
├── CHANGELOG.md                      # Auto-generated from commit history
├── CONTRIBUTING.md                   # This file
├── LICENSE                           # MIT License
└── README.md
```

### Key modules at a glance

| Module | Purpose |
|--------|---------|
| `_base.py` | `SwgohComlinkBase` — shared payload construction, HMAC signing, and config for both clients |
| `swgoh_comlink.py` | `SwgohComlink` — synchronous HTTP client (all endpoint methods) |
| `swgoh_comlink_async.py` | `SwgohComlinkAsync` — asynchronous HTTP client (mirrors sync API) |
| `StatCalc/calculator.py` | `StatCalc` — local stat and GP calculation for game units |
| `helpers/` | `DataItems` IntFlag enum, `Constants` class, 25+ utility functions split across focused submodules |
| `exceptions.py` | `SwgohComlinkException` and `SwgohComlinkValueError` |
| `globals.py` | Shared logging setup (`get_logger()`) |
| `version.py` | Single `__version__` string, managed by hatch during releases |

---

## Making Changes

### Branching Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable release branch. All PRs target this branch. |
| `2.0-development` | Next major version development (breaking changes, architectural work) |
| `1.0-maintenance` | Legacy maintenance branch |

**For most contributions:**

```bash
git checkout main
git pull upstream main
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

This project follows standard Python conventions. Please keep these in mind:

**General principles:**

- Follow [PEP 8](https://peps.python.org/pep-0008/) for formatting
- Use **complete type annotations** on all functions, parameters, and return values — the project enforces `mypy --strict`
- Use `from __future__ import annotations` at the top of each module for modern annotation syntax
- Use docstrings (Google style) on all public classes and methods
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

- Standard library imports first, then third-party, then local — separated by blank lines
- Use `from __future__ import annotations` at the top of each module
- Prefer specific imports over wildcard: `from json import dumps, loads`

### Writing Tests

Tests live in the `tests/` directory and use `pytest` (configured in `pyproject.toml`). Both sync and async tests are supported via `pytest-asyncio`. Run tests with:

```bash
# Run all tests
uv run pytest tests/

# Run a specific test file
uv run pytest tests/test_get_player.py

# Run with verbose output
uv run pytest tests/ -v
```

**Unit tests vs integration tests:**

| Type | Requires comlink? | Mocking | When to use |
|------|-------------------|---------|-------------|
| Unit test | No | Mock `_post()` | All new code should have unit tests |
| Integration test | Yes | None | Optional; validates real API behavior |

**Writing a unit test (preferred):**

New tests should mock the `_post()` method so they can run anywhere without a comlink service:

```python
from unittest import TestCase, mock
from swgoh_comlink import SwgohComlink


class TestGetPlayer(TestCase):
    @mock.patch.object(SwgohComlink, '_post')
    def test_get_player_by_allycode(self, mock_post):
        """Test that get_player() builds correct payload for allycode lookup"""
        mock_post.return_value = {
            'name': 'TestPlayer',
            'allyCode': '123456789',
            'level': 85
        }
        comlink = SwgohComlink()
        result = comlink.get_player(allycode=123456789)

        # Verify the method was called with expected payload
        mock_post.assert_called_once_with(
            endpoint='player',
            payload={
                'payload': {'allyCode': '123456789'},
                'enums': False
            }
        )
        self.assertEqual(result['name'], 'TestPlayer')
```

**Test file naming:** `test_<feature_or_method>.py`

**What to test:**

- Payload construction — verify the correct JSON payload is built for each method
- Parameter validation — edge cases, invalid inputs, boundary values
- Error handling — how the client handles HTTP errors, bad JSON, connection failures
- Helper functions — each utility function in the `helpers/` package should have its own tests

### Commit Messages

This project uses the [Angular commit convention](https://www.conventionalcommits.org/) with [git-changelog](https://pawamoy.github.io/git-changelog/) to auto-generate `CHANGELOG.md`. Your commit messages directly become release notes, so please follow this format:

```
<type>(<scope>): <short description>
```

**Types** (recognized by the changelog generator):

| Type | Use for | CHANGELOG section |
|------|---------|-------------------|
| `feat` | New features or capabilities | Features |
| `fix` | Bug fixes | Bug Fixes |
| `refactor` | Code restructuring (no behavior change) | Code Refactoring |
| `build` | Build system or dependency changes | Build |
| `deps` | Dependency updates | Dependencies |
| `chore` | Routine maintenance, config changes, version bumps | Chores |
| `docs` | Documentation additions or updates | Documentation |

Other types (`test`, `style`, `ci`) are valid conventional commits but are **not included** in the generated changelog.

**Scope** is optional but encouraged. Common scopes:

- `core` — changes to the client classes (`swgoh_comlink.py`, `swgoh_comlink_async.py`, `_base.py`)
- `helpers` — changes to the `helpers/` package
- `statcalc` — changes to the `StatCalc/` package
- `deps` — dependency updates

**Examples:**

```bash
# Good
feat(core): add verify_ssl parameter to SwgohComlink constructor
fix(helpers): remove debug print statement from human_time()
refactor(core): generalize _post() into _request() for GET/POST support
fix: correct param_alias decorator to handle falsy values
chore(deps): update requests to version 2.32.4
chore(release): bump version to 1.18.0 and update workflow
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

---

## Submitting a Pull Request

1. **Sync your fork with upstream and rebase your branch:**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

   If you have merge conflicts, resolve them locally before pushing.

2. **Run the checks locally:**

   ```bash
   # Lint
   uvx ruff check src/ tests/

   # Type check
   uv run mypy src/swgoh_comlink/

   # Tests
   uv run pytest tests/ -v
   ```

3. **Push your branch to your fork:**

   ```bash
   git push origin <your-branch-name>
   ```

4. **Open a pull request:**

   Using GitHub CLI:

   ```bash
   gh pr create --repo swgoh-utils/comlink-python --base main --fill
   ```

   Or go to [github.com/swgoh-utils/comlink-python/pulls](https://github.com/swgoh-utils/comlink-python/pulls)
   and click **"New pull request"** → **"compare across forks"** → select your fork and branch.

5. **PR description should include:**
   - What the change does and why
   - Which issue it addresses (e.g., "Closes #51")
   - Any breaking changes or migration notes
   - How you tested the change

6. **PR checklist:**

   - [ ] Code follows the project's style conventions
   - [ ] All new public methods have docstrings with type hints
   - [ ] New functionality includes unit tests (mocked, not requiring live comlink)
   - [ ] Existing tests still pass (`uv run pytest tests/`)
   - [ ] Commit messages follow Angular convention
   - [ ] Ruff linter passes (`uvx ruff check src/ tests/`)
   - [ ] Ruff formatter passes (`uvx ruff format --check src/ tests/`)
   - [ ] Mypy strict passes (`uv run mypy src/swgoh_comlink/`)
   - [ ] No unrelated changes bundled in

7. **After submitting:**

   CI checks (lint, tests, commit message validation, build) will run automatically.
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

Before opening an issue, check the [existing issues](https://github.com/swgoh-utils/comlink-python/issues) to avoid duplicates.

**Bug reports** should include:

- Python version (`python --version`)
- Package version (`python -c "from swgoh_comlink import version; print(version)"`)
- Comlink version (if relevant)
- Minimal code to reproduce the issue
- Expected vs actual behavior
- Full traceback (if applicable)

**Feature requests** should include:

- What you're trying to accomplish
- How you're currently working around it (if applicable)
- A proposed API or approach (if you have one in mind)

**Labels used in this project:**

| Label | Meaning |
|-------|---------|
| `bug` | Something isn't working correctly |
| `security` | Security-related issue |
| `enhancement` | New feature or capability |
| `feature request` | Community-requested feature |
| `code maintenance` | Internal cleanup, refactoring, tech debt |
| `testing` | Test coverage or infrastructure |

---

## Release Process

Releases are handled by the maintainer through the GitHub Actions `release.yml` workflow. Contributors don't need to manage versioning or releases, but here's how it works for reference:

1. The release workflow is triggered manually (`workflow_dispatch`)
2. [Hatch](https://hatch.pypa.io/) bumps the version in `src/swgoh_comlink/version.py`
3. [git-changelog](https://pawamoy.github.io/git-changelog/) regenerates `CHANGELOG.md` from commit history
4. The new version is tagged and pushed
5. The package is built with `hatch build` and published to [PyPI](https://pypi.org/project/swgoh-comlink/)

This is why conventional commit messages matter — they become the release notes automatically.

**Version scheme:** [Semantic Versioning](https://semver.org/)

- **Patch** (1.17.x): Bug fixes, documentation
- **Minor** (1.x.0): New features, backward-compatible changes
- **Major** (x.0.0): Breaking API changes

---

## Getting Help

- **Issues:** [github.com/swgoh-utils/comlink-python/issues](https://github.com/swgoh-utils/comlink-python/issues)
- **Discord:** [Join the server](https://discord.gg/6PBfG5MzR3) for real-time discussion
- **Wiki:** [swgoh-comlink wiki](https://github.com/swgoh-utils/swgoh-comlink/wiki) for general comlink documentation

---

Thank you for contributing! Every fix, feature, test, and docs improvement helps the SWGOH developer community.
