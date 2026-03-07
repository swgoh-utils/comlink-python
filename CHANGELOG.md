# CHANGELOG

<!-- insertion marker -->

## [v2.0.0 Pending Release] - feature/async

### Breaking Changes

- remove `OPTIONAL` and `NotSet` sentinel exports from `swgoh_comlink.helpers`.
  Replace any usage with plain `None` defaults or `int` defaults as appropriate.
- remove external `sentinels` library dependency. The package now uses an inline
  `Sentinel` class. Code importing sentinels from `swgoh_comlink.helpers` should
  remove references to `OPTIONAL` and `NotSet`.
- change `get_gac_brackets()` and `async_get_gac_brackets()` `limit` parameter
  from sentinel-based default to `int` with default `0` (meaning no limit).

### Features

- add `SwgohComlinkAsync` async client with full API parity to `SwgohComlink`.
  Both clients inherit from a shared `SwgohComlinkBase` class.
- add `StatCalcAsync` async stat calculator with `create()` factory method for
  non-blocking game data initialization. Inherits all calculation methods from
  `StatCalc`.
- add `GameDataBuilder` / `GameDataBuilderAsync` to build StatCalc game data
  dynamically from a running Comlink service instead of fetching a static file
  from GitHub.
- replace `requests` library with `httpx` for both sync and async HTTP support.
- add connection pooling via persistent `httpx.Client` / `httpx.AsyncClient` instances.
- add context manager support (`with SwgohComlink()` and `async with SwgohComlinkAsync()`).
- add async helper variants: `async_get_current_gac_event()`, `async_get_gac_brackets()`,
  and `async_get_guild_members()` for use with `SwgohComlinkAsync`.
- add exponential probing with binary search for GAC bracket boundary discovery,
  reducing HTTP requests from O(n) to O(log n).
- add parallel batch fetching via `asyncio.gather` in `async_get_gac_brackets()`
  for significantly faster bracket collection.
- add comprehensive Helpers API reference and Exceptions documentation pages.

### Code Refactoring

- replace external `sentinels` library with inline `Sentinel` class; remove
  unused sentinels (`OPTIONAL`, `NotSet`, `EMPTY`, `NotGiven`, `SET`,
  `MutualRequiredNotSet`).
- extract shared logic (HMAC auth, payload builders, URL sanitization, param_alias decorator)
  into `_base.py` base class.
- unify all HTTP communication through a single `_request()` gateway method
  in both sync and async clients.
- refactor monolithic `helpers.py` (1,970 lines) into a focused `helpers/` subpackage
  with domain-specific modules (`_arena.py`, `_gac.py`, `_game_data.py`, `_guild.py`,
  `_omicron.py`, `_utils.py`, `_decorators.py`, `_sentinels.py`, `_data_items.py`,
  `_stat_data.py`, `_constants.py`). All existing import paths are preserved via
  backward-compatible re-export shim in `helpers/__init__.py`.
- consolidate 4 duplicate copies of stat data (Constants.STAT_ENUMS,
  Constants.UNIT_STAT_ENUMS_MAP, Constants.STATS, StatCalc.STATS_NAME_MAP) into a
  single canonical `STATS` dict in `helpers/_stat_data.py` with derived views.
- replace 489-line inline `STATS_NAME_MAP` dict in `StatCalc/calculator.py` with
  import from `helpers/_stat_data`.

### Dependencies

- replace `requests>=2.32.4` with `httpx>=0.28`.
- add `pytest-httpx>=0.35` and `pytest-asyncio>=0.24` to dev dependencies.

### Logging

- refactor logging to follow Python library best practice: attach only `NullHandler`
  to the package root logger; remove forced `StreamHandler` and level configuration.
- remove unused logger instances from `_base.py`, `swgoh_comlink.py`, and
  `swgoh_comlink_async.py`.
- switch `exceptions.py` and `helpers.py` to use `logging.getLogger(__name__)` directly.
- keep `LoggingFormatter` as an opt-in convenience in `globals.py`.
- rewrite `docs/logging.md` for the new approach.

### Tools

- add `swgoh-migrate` CLI tool (`python -m swgoh_comlink.migrate`) for scanning
  user codebases and identifying deprecated import patterns, API changes, and
  migration steps needed when upgrading from v1.x. Supports `--severity`,
  `--no-color`, and `--exclude` options.

### Documentation

- add migration guide (`docs/migration.md`) covering dependency changes, exception
  handling, logging configuration, and client lifecycle.
- add migration summary section to README with link to the full guide.

### Testing

- rewrite unit tests to use `pytest-httpx` mocking instead of `monkeypatch`.
- add comprehensive async client test suite mirroring sync coverage.
- add `test_base.py` with tests for base class utilities, HMAC, payload builders,
  and validation logic.
- increase test coverage from 38% to 48% (100% on core modules `_base.py`,
  `swgoh_comlink.py`, and `swgoh_comlink_async.py`).

---

## [v1.18.0rc1](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.18.0rc1) - 2026-03-03

<small>[Compare with v1.17.0](https://github.com/swgoh-utils/comlink-python/compare/v1.17.0...v1.18.0rc1)</small>

### Features

- add StatCalc module for local stat and GP calculation without an external
  swgoh-stats service ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).

### Bug Fixes

- remove duplicate `_rename_stats` call in `calc_char_stats` that caused
  `AttributeError` on second pass ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).
- fix `calc_player_stats` type annotations, `isinstance` syntax, and list
  mutation bug ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).
- remove stray `print()` statements and unnecessary `deepcopy` in
  `_rename_stats` ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).

### Documentation

- expand StatCalc usage guide in README and mkdocs API
  reference ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).
- add missing `get_name_spaces` and `get_segmented_content` methods to README
  table ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).
- update CONTRIBUTING.md project structure and key modules for StatCalc and
  test subdirectories ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).

### Chores

- remove unused `scripts/verify-upstream.sh` ([a880097](https://github.com/swgoh-utils/comlink-python/commit/a880097889b30e345c80ec99ff207d4e50daa431) by
  MarTrepodi).

## [v1.17.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.17.0) - 2025-11-18

<small>[Compare with v1.16.0](https://github.com/swgoh-utils/comlink-python/compare/v1.16.0...v1.17.0)</small>

### Features

- add new namespace and content retrieval methods in support of comlink
  3.3.1 ([1bf354d](https://github.com/swgoh-utils/comlink-python/commit/1bf354dcebc0f381ba3b4264dbfc75208d16ed93) by
  MarTrepodi).

## [v1.16.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.16.0) - 2025-10-02

<small>[Compare with v1.14.0](https://github.com/swgoh-utils/comlink-python/compare/v1.14.0...v1.16.0)</small>

### Features

- add custom exceptions and
  logging ([9855b5a](https://github.com/swgoh-utils/comlink-python/commit/9855b5af23d286bb545da12df3472526292371cd) by
  MarTrepodi).
- add function to calculate datacron dismantle
  value ([af0a6a7](https://github.com/swgoh-utils/comlink-python/commit/af0a6a7a46e10227450f9d866ffbb18a9d05a724) by
  MarTrepodi).
- enhance typings, validation, and constants
  support ([eab2851](https://github.com/swgoh-utils/comlink-python/commit/eab2851d2c6c22bebd597dfe3aa3d014a65828f9) by
  MarTrepodi).
- add LightspeedToken enum value to DataItems class in
  helpers.py ([2d22988](https://github.com/swgoh-utils/comlink-python/commit/2d22988ee332f37147a2cbad625625be96d50545)
  by MarTrepodi).
- add function to calculate arena payout
  time ([7eed7c1](https://github.com/swgoh-utils/comlink-python/commit/7eed7c177035ea21d4a95a6777fd2c05f52419c5) by
  MarTrepodi).
- add threaded player fetch script for parallel data
  collection ([ca143b3](https://github.com/swgoh-utils/comlink-python/commit/ca143b313bd8a576c007812228ca872e4e78e6ce)
  by MarTrepodi).
- add function to calculate max rank
  jump ([de28969](https://github.com/swgoh-utils/comlink-python/commit/de289692588236f7c4cecfa1da60386a9920df41) by
  MarTrepodi).

### Code Refactoring

- update imports and fix formatting in __init__
  .py ([e42045e](https://github.com/swgoh-utils/comlink-python/commit/e42045e86212049940634b0e429840b8195896d2) by
  MarTrepodi).

## [v1.14.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.14.0) - 2025-03-09

<small>[Compare with v1.13.0](https://github.com/swgoh-utils/comlink-python/compare/v1.13.0...v1.14.0)</small>

### Bug Fixes

- downgrade urllib3 to v1.26.20 (
  #43) ([d39c3fd](https://github.com/swgoh-utils/comlink-python/commit/d39c3fdc048637ee1a0c94874b617bb2cde0fe3f) by
  MarTrepodi).
- downgrade urllib3 to
  v1.26.20 ([d6c0676](https://github.com/swgoh-utils/comlink-python/commit/d6c0676b2124506c865a478bf67bbf7f485c9add) by
  MarTrepodi).
- update build command and correct version
  number ([5e4a1d8](https://github.com/swgoh-utils/comlink-python/commit/5e4a1d85811e4aa47a0d58e8c6c831d244cc8260) by
  MarTrepodi).

### Features

- add DataItems IntFlag enum for game data
  collection ([629a865](https://github.com/swgoh-utils/comlink-python/commit/629a865f257eaf624087069261026203cf333510)
  by MarTrepodi).

### Code Refactoring

- simplify code and improve
  consistency ([7616b0c](https://github.com/swgoh-utils/comlink-python/commit/7616b0c4958f51eac88a20f0024a177e98d4c235)
  by MarTrepodi).
- rename tests folder and add new helper
  function ([9ba58f6](https://github.com/swgoh-utils/comlink-python/commit/9ba58f6aa659f84ca54920178eebe8fb5eebca4b) by
  MarTrepodi).
- update method calls with explicit argument
  names ([c61ba96](https://github.com/swgoh-utils/comlink-python/commit/c61ba967d4bf29c17ef1fb77c7c1162e6d423022) by
  MarTrepodi).

## [v1.13.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.13.0) - 2025-02-26

<small>[Compare with v1.12.4](https://github.com/swgoh-utils/comlink-python/compare/v1.12.4...v1.13.0)</small>

### Bug Fixes

- fix get_unit_stats() method to properly handle full player roster
  collection ([015ccc8](https://github.com/swgoh-utils/comlink-python/commit/015ccc8ed80a00caa6366b62c5155ec955961ba4)
  by MarTrepodi). chore: update minimum supported python version to 3.10 in pyproject.toml

## [v1.12.4](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.12.4) - 2024-08-09

<small>[Compare with v1.12.3](https://github.com/swgoh-utils/comlink-python/compare/v1.12.3...v1.12.4)</small>

## [v1.12.3](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.12.3) - 2024-08-09

<small>[Compare with v1.12.1](https://github.com/swgoh-utils/comlink-python/compare/v1.12.1...v1.12.3)</small>

### Features

- add 'items' parameter to get_game_data() and 'locale' parameter to
  get_localization() ([a4c3e6b](https://github.com/swgoh-utils/comlink-python/commit/a4c3e6b304e8886466d835b2bf2f525357b05c17)
  by MarTrepodi).

## [v1.12.1](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.12.1) - 2024-03-26

<small>[Compare with v1.12.0](https://github.com/swgoh-utils/comlink-python/compare/v1.12.0...v1.12.1)</small>

## [v1.12.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.12.0) - 2023-05-16

<small>[Compare with v1.11.1](https://github.com/swgoh-utils/comlink-python/compare/v1.11.1...v1.12.0)</small>

### Features

- added get_latest_game_data_version() method for simplified access to game data and language bundle version
  information ([dce650f](https://github.com/swgoh-utils/comlink-python/commit/dce650f29e88758009211039f64689f3ee197e55)
  by MarTrepodi).

## [v1.11.1](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.11.1) - 2023-02-19

<small>[Compare with v1.11.0](https://github.com/swgoh-utils/comlink-python/compare/v1.11.0...v1.11.1)</small>

## [v1.11.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.11.0) - 2023-02-14

<small>[Compare with v1.10.0](https://github.com/swgoh-utils/comlink-python/compare/v1.10.0...v1.11.0)</small>

### Features

- add
  get_guild_leaderboard() ([402943c](https://github.com/swgoh-utils/comlink-python/commit/402943cb9441154d36537a27f189e987cbe48cd1)
  by MarTrepodi).

## [v1.10.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.10.0) - 2023-02-07

<small>[Compare with v1.9.0](https://github.com/swgoh-utils/comlink-python/compare/v1.9.0...v1.10.0)</small>

### Features

- add get_leaderboard(). update README.md. add requests package to install_dependencies iin
  pyproject.toml. ([84f1982](https://github.com/swgoh-utils/comlink-python/commit/84f1982cad26a274cb354f3219f54d2d42b218c9)
  by MarTrepodi).

## [v1.9.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.9.0) - 2023-01-31

<small>[Compare with v1.8.0](https://github.com/swgoh-utils/comlink-python/compare/v1.8.0...v1.9.0)</small>

### Features

- add get_events(). update get_player_arena to include 'playerDetailsOnly'
  parameter. ([49189ae](https://github.com/swgoh-utils/comlink-python/commit/49189ae22d71d6923f8e3d21525551d9b3e1d679)
  by MarTrepodi).

## [v1.8.0](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.8.0) - 2023-01-31

<small>[Compare with v1.7.7](https://github.com/swgoh-utils/comlink-python/compare/v1.7.7...v1.8.0)</small>

### Build

- add swgoh-stat to test.yml
  workflow ([5ef5ecf](https://github.com/swgoh-utils/comlink-python/commit/5ef5ecf4474390379603336f5275847ca32f949d) by
  MarTrepodi).

### Features

- add
  get_unit_stats() ([c1e46f8](https://github.com/swgoh-utils/comlink-python/commit/c1e46f8af417dc620422040bbafe9c90a90f4cf1)
  by MarTrepodi).
- initial get_unit_stat()
  implementation. ([59cba96](https://github.com/swgoh-utils/comlink-python/commit/59cba96f290de3f12e5e807a50a15044eb53fceb)
  by MarTrepodi).

## [v1.7.7](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.7.7) - 2023-01-20

<small>[Compare with v1.7.6](https://github.com/swgoh-utils/comlink-python/compare/v1.7.6...v1.7.7)</small>

### Build

- split ci/cd workflow into separate test and release workflows. add link to PyPi package location in README.md. sync
  file based release version number with GitHub
  tag. ([4a2f58a](https://github.com/swgoh-utils/comlink-python/commit/4a2f58a137cb0644ea3c43dd882bc34838fb5856) by
  MarTrepodi).

### Bug Fixes

- replace getGuild() JSON parameter element include_recent_guild_activity_info with
  includeRecentGuildActivityInfo ([4d58e04](https://github.com/swgoh-utils/comlink-python/commit/4d58e04fb3c3824ffd99b04080a03d178030e61e)
  by MarTrepodi).

## [v1.7.6](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.7.6) - 2023-01-19

<small>[Compare with v1.7.5](https://github.com/swgoh-utils/comlink-python/compare/v1.7.5...v1.7.6)</small>

### Build

- enable automated release deployment to
  PyPi ([cf50a74](https://github.com/swgoh-utils/comlink-python/commit/cf50a741c2b0aaa4502826524f001bbbf0cde2cf) by
  MarTrepodi).

## [v1.7.5](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.7.5) - 2023-01-19

<small>[Compare with v1.7.4](https://github.com/swgoh-utils/comlink-python/compare/v1.7.4...v1.7.5)</small>

### Build

- updated pyproject.toml for setuptool dynamic version
  extraction ([f7a8c73](https://github.com/swgoh-utils/comlink-python/commit/f7a8c736d8279bb88b724d2ff69dde9418e62b42)
  by MarTrepodi).
- updated pyproject.toml for setuptools version extraction from
  module ([86bc265](https://github.com/swgoh-utils/comlink-python/commit/86bc265955752f497126468cc8441a0395abf159) by
  MarTrepodi).
- remove build_command from
  pyproject.toml ([fe260e0](https://github.com/swgoh-utils/comlink-python/commit/fe260e0a777ba5ab5f01330ffb263c0f9d049512)
  by MarTrepodi).
- manually bump release version to sync ci/cd
  automation ([56c23b2](https://github.com/swgoh-utils/comlink-python/commit/56c23b20c965a7ef41c67c9b702107541224486a)
  by MarTrepodi).
- added installation of python build module to ci/cd
  workflow ([6e1e2b6](https://github.com/swgoh-utils/comlink-python/commit/6e1e2b687ab6368330a1f44cbf4a69b3e9953d09) by
  MarTrepodi).
- added version source directive to pull from github
  tag ([b91f0b4](https://github.com/swgoh-utils/comlink-python/commit/b91f0b47163da90b1abfb0952262427728fcdafa) by
  MarTrepodi).

## [v1.7.4](https://github.com/swgoh-utils/comlink-python/releases/tag/v1.7.4) - 2023-01-19

<small>[Compare with first commit](https://github.com/swgoh-utils/comlink-python/compare/871ea4be044f19a647a4638e23fc5e42bcf53ea5...v1.7.4)</small>

### Build

- removed publishing of release to PyPi until CD process has been fully
  validated. ([8e975eb](https://github.com/swgoh-utils/comlink-python/commit/8e975eb1dbd9ea6f2e8c0e5d7b9409a01fd9d672)
  by MarTrepodi).

### Bug Fixes

- removed asyncio modifications that were committed
  prematurely ([a7c29e0](https://github.com/swgoh-utils/comlink-python/commit/a7c29e0960e6415863ceac46024df40229cba35d)
  by MarTrepodi).
- Fixed instance instantiation syntax for
  pytests ([ec54bea](https://github.com/swgoh-utils/comlink-python/commit/ec54bea1fdec5a598b0b3c23700090481d88aa70) by
  MarTrepodi).
- Added version.py for external version
  bumping ([dbdc1e1](https://github.com/swgoh-utils/comlink-python/commit/dbdc1e1e4df749ae2ea3c5ceec115663c366b4c2) by
  MarTrepodi).
- Updated tests for latest package import
  refactor ([4204afb](https://github.com/swgoh-utils/comlink-python/commit/4204afb4d9453fb65694fea15253c541ffe06054) by
  MarTrepodi).

### Features

- added CI/CD
  workflow ([5519abb](https://github.com/swgoh-utils/comlink-python/commit/5519abb63f56cc1e4ec438c2fbb37d90788a435c) by
  MarTrepodi).
- Refactor for single module import from package. Added game version collection at instance instantiation. Game data
  version parameter for get_game_data() now defaults to current version if not
  supplied. ([0bfa33a](https://github.com/swgoh-utils/comlink-python/commit/0bfa33a753a2088c801296e4446500fdfb568037) by
  MarTrepodi).

## v1.14.0 (2025-03-09)

### Bug Fixes

- **build**: Update build command and correct version number
  ([`5e4a1d8`](https://github.com/swgoh-utils/comlink-python/commit/5e4a1d85811e4aa47a0d58e8c6c831d244cc8260))

Updated the build command in pyproject.toml to install dependencies from requirements.txt before
  building. Corrected the version number in version.py to align with the intended release version.

- **dependencies**: Downgrade urllib3 to v1.26.20
  ([`d6c0676`](https://github.com/swgoh-utils/comlink-python/commit/d6c0676b2124506c865a478bf67bbf7f485c9add))

Downgraded urllib3 due to compatibility issues with v2.3.0. This ensures stability and prevents
  potential runtime errors in dependent services.

- **dependencies**: Downgrade urllib3 to v1.26.20
  ([#43](https://github.com/swgoh-utils/comlink-python/pull/43),
  [`d39c3fd`](https://github.com/swgoh-utils/comlink-python/commit/d39c3fdc048637ee1a0c94874b617bb2cde0fe3f))

Downgraded urllib3 due to compatibility issues with v2.3.0. This ensures stability and prevents
  potential runtime errors in dependent services.

### Chores

- Simplify and update requirements.txt dependencies
  ([`c9c3cf1`](https://github.com/swgoh-utils/comlink-python/commit/c9c3cf16f25c2e310dc714813484f79d13e0fe18))

Replaced pinned dependency versions with version ranges for `requests` and `urllib3`. This change
  simplifies the file and keeps compatibility within specified ranges, improving maintainability.

- Simplify and update requirements.txt dependencies
  ([`74732d7`](https://github.com/swgoh-utils/comlink-python/commit/74732d716dedc663670d6da65ccfaf33e35704b0))

Replaced pinned dependency versions with version ranges for `requests` and `urllib3`. This change
  simplifies the file and keeps compatibility within specified ranges, improving maintainability.

- Switch to uv. clean up dependencies and remove CI workflow
  ([`e8e0285`](https://github.com/swgoh-utils/comlink-python/commit/e8e0285c40cf34cc5497e280cd5d1c5164742bec))

Removed `requirements.txt`, `requirements-dev.txt`, and the associated GitHub Actions CI workflow
  for testing and building. Introduced `uv.lock` to manage dependencies with Python 3.10+ and
  streamline dependency management approach.

- Update build command and version to 1.13.1
  ([`684780c`](https://github.com/swgoh-utils/comlink-python/commit/684780ca389c9c0422921d69eeb29bfe3d3fba6f))

Simplified the build command by removing redundant dependencies. Disabled automatic upload to GitHub
  releases and bumped the version to 1.13.1 for consistency with changes.

- Update release workflow and add requirements file
  ([`08cfb4f`](https://github.com/swgoh-utils/comlink-python/commit/08cfb4f52e1e9c015939b0e534ef598124ce5f28))

Remove unnecessary parameters from the release workflow to simplify the GitHub Action configuration.
  Add autogenerated `requirements.txt` for dependency tracking and reproducibility. This improves
  overall maintenance and clarity of the project.

- Update release workflow and add requirements file
  ([`a74be78`](https://github.com/swgoh-utils/comlink-python/commit/a74be78d9b897b9c67c9393eabb90b4f7c62a993))

Remove unnecessary parameters from the release workflow to simplify the GitHub Action configuration.
  Add autogenerated `requirements.txt` for dependency tracking and reproducibility. This improves
  overall maintenance and clarity of the project.

### Features

- Add DataItems IntFlag enum for game data collection
  ([`629a865`](https://github.com/swgoh-utils/comlink-python/commit/629a865f257eaf624087069261026203cf333510))

Introduce `DataItems` enum to map game data collections to bit positions, enabling easier management
  of `get_game_data()` parameters. Includes conveniences like aliases, combined segments, and a
  `members()` method for listing member names. This improves clarity and flexibility when specifying
  game data items.

### Refactoring

- Rename tests folder and add new helper function
  ([`9ba58f6`](https://github.com/swgoh-utils/comlink-python/commit/9ba58f6aa659f84ca54920178eebe8fb5eebca4b))

Removed outdated and redundant unit tests under 'pytests' directory as they are no longer relevant.
  Added a new helper function `get_raid_leaderboard_ids()` to retrieve raid leaderboard IDs from
  campaign data. Updated the package version to 1.13.0 to reflect these changes.

- Simplify code and improve consistency
  ([`7616b0c`](https://github.com/swgoh-utils/comlink-python/commit/7616b0c4958f51eac88a20f0024a177e98d4c235))

Updated variable assignments and formatting to enhance readability and maintain consistent styling.
  Transitioned docstring format to Google style for improved developer clarity and standardized
  descriptions across methods.

- Update method calls with explicit argument names
  ([`c61ba96`](https://github.com/swgoh-utils/comlink-python/commit/c61ba967d4bf29c17ef1fb77c7c1162e6d423022))

Updated `get_player` and `get_guild` calls to use named arguments for better readability and
  clarity. Also fixed a typo in the installation command in the README.


## v1.13.0 (2025-02-26)

### Bug Fixes

- **core**: Fix get_unit_stats() method to properly handle full player roster collection
  ([`015ccc8`](https://github.com/swgoh-utils/comlink-python/commit/015ccc8ed80a00caa6366b62c5155ec955961ba4))

doc: add manual entries to CHANGELOG.md for last two releases

chore: update minimum supported python version to 3.10 in pyproject.toml

### Continuous Integration

- Add requests module to build requirements
  ([`e9a8e24`](https://github.com/swgoh-utils/comlink-python/commit/e9a8e249d7e4262d81c51e5691a6b21b2a59f145))

- Fixed requirements.txt typo in build command
  ([`9667c9e`](https://github.com/swgoh-utils/comlink-python/commit/9667c9eb1c7cd9a92e847174b4a9c9a09eaa54c7))

- Update pyproject.toml to add installation of requirements.txt
  ([`a8ff60b`](https://github.com/swgoh-utils/comlink-python/commit/a8ff60b913fef662c24a59cd123a7d263e1366f0))

- Update pyproject.toml to add pip install build to the semantic_release tool build directive
  ([`fd5e918`](https://github.com/swgoh-utils/comlink-python/commit/fd5e9187ce00e7b8aeed5353b7c6b06a3dee728e))

- Update pyproject.toml to add version_variable location list.
  ([`c13dd9c`](https://github.com/swgoh-utils/comlink-python/commit/c13dd9cb05d4aa4db3dacc37df6e5eb640dfce3f))

ci: remove python setup from release.yml

- Update release.yml to use latest semantic-release actions and PyPi trusted publishing
  ([`2551f3b`](https://github.com/swgoh-utils/comlink-python/commit/2551f3b31c5b7bbbef012c28a48801d15514d918))


## v1.12.4 (2024-08-08)

### Documentation

- Add examples for 'items' parameter use in get_game_data.py and 'locale' parameter in
  get_localization.py
  ([`e4a0eda`](https://github.com/swgoh-utils/comlink-python/commit/e4a0edac8cd59c5152b2e64ebbbcaf995e179f0c))


## v1.12.2 (2024-08-08)

### Features

- Add 'items' parameter to get_game_data() and 'locale' parameter to get_localization()
  ([`a4c3e6b`](https://github.com/swgoh-utils/comlink-python/commit/a4c3e6b304e8886466d835b2bf2f525357b05c17))


## v1.12.1 (2024-03-25)

### Chores

- Add /pytests to .gitignore
  ([`660fd2d`](https://github.com/swgoh-utils/comlink-python/commit/660fd2d4e41030ffa4dbb9963785bd1fae262ad0))

### Continuous Integration

- Bump version number to test release automation
  ([`cc52bd5`](https://github.com/swgoh-utils/comlink-python/commit/cc52bd51faf48b568f839b180a208bf6e46d2cc5))

- Remove -v DEBUG from line 36
  ([`d6e4777`](https://github.com/swgoh-utils/comlink-python/commit/d6e47778d6f9aec521596b83287607cfe26414c8))

- Update release.yml to include token write permissions
  ([`b0fc307`](https://github.com/swgoh-utils/comlink-python/commit/b0fc30766ec1d41349094d27e744120346271706))

- Update to pypi trusted publisher model with github oidc
  ([`50bd3b2`](https://github.com/swgoh-utils/comlink-python/commit/50bd3b26da519343ed1f57dd1c51a862636cd70d))

### Testing

- Refactor code in get_player_arena.py test suite
  ([`17bc68e`](https://github.com/swgoh-utils/comlink-python/commit/17bc68ec6ef55f5621b3ce5d73e21575310b7eb7))

The commit includes minor changes to clean up the test script 'test_get_player_arena.py'. It has
  edited variable names in the method 'get_player_arena' to align with the required standards, along
  with some minor code formatting for better readability.


## v1.12.0 (2023-05-16)

### Chores

- Add type hinting for all parameters and returns
  ([`1c23223`](https://github.com/swgoh-utils/comlink-python/commit/1c23223f7e9d9449097f2b1a4a37c8c258bf72ff))

- Added GAC specific aliases to get_leaderboard() method. Add alias of 'includeRecent' to parameter
  'include_recent_guild_activity_info' for get_guild() method.
  ([`0e13ace`](https://github.com/swgoh-utils/comlink-python/commit/0e13acec805465ae319cca15ce405943923bc915))

- Correct get_player_arena() parameter playerDetailsOnly name using new alias wrapper
  ([`f4be346`](https://github.com/swgoh-utils/comlink-python/commit/f4be34625c0e170a5265e0ae16ced28d3627b227))

- Correct test case class name in test_get_unit_stats.py
  ([`9647bdd`](https://github.com/swgoh-utils/comlink-python/commit/9647bddf73ea18a7d9cf5d637ea08ba9fcb320f8))

- Move github workflow test.yml to stash and added to gitignore
  ([`2b9aaf6`](https://github.com/swgoh-utils/comlink-python/commit/2b9aaf695acad168c9c0261c78675a0ad50f0c01))

- Update .gitignore
  ([`65ee0bd`](https://github.com/swgoh-utils/comlink-python/commit/65ee0bde363529f069714be8524cd1b83285a135))

- Update get_player_arena() parameter alias wrapper to be more concise
  ([`f8d6538`](https://github.com/swgoh-utils/comlink-python/commit/f8d6538fa3773e665611a506fa282929a7dab00d))

### Features

- Added get_latest_game_data_version() method for simplified access to game data and language bundle
  version information
  ([`dce650f`](https://github.com/swgoh-utils/comlink-python/commit/dce650f29e88758009211039f64689f3ee197e55))

### Testing

- Refactor test_get_player_arena.py to add negative test case for invalid argument
  ([`94d8b84`](https://github.com/swgoh-utils/comlink-python/commit/94d8b84ea049a3d2252d77fb81419d8729adc26b))

- Refactor test_get_player_arena.py to use mock object and include both new and aliased
  player_detail_only parameter syntax
  ([`474eb96`](https://github.com/swgoh-utils/comlink-python/commit/474eb96d78b82d708f20ec84fe1fb9b34f259896))


## v1.11.1 (2023-02-19)

### Documentation

- Changed get_guilds_by_criteria() -> search_criteria_template example elements to snake case for
  compliance with comlink expected input.
  ([`87cfbe0`](https://github.com/swgoh-utils/comlink-python/commit/87cfbe05d030e86cccd95924755ef6d9092077a3))


## v1.11.0 (2023-02-14)

### Features

- Add get_guild_leaderboard()
  ([`402943c`](https://github.com/swgoh-utils/comlink-python/commit/402943cb9441154d36537a27f189e987cbe48cd1))


## v1.10.0 (2023-02-07)

### Continuous Integration

- Correct dependency syntax in test.yml
  ([`13f02c6`](https://github.com/swgoh-utils/comlink-python/commit/13f02c607da37da93d6d9aa2cf6e821dd49026a5))

- Correct environment naming and service dependencies in test.yml
  ([`3bd8ff0`](https://github.com/swgoh-utils/comlink-python/commit/3bd8ff0ebbabd7ba0d4949ae8e0ac0809fac0050))

- Remove container name statements from test.yml
  ([`57d2aa6`](https://github.com/swgoh-utils/comlink-python/commit/57d2aa6b9eb361e7b855205f279e82ab4311bf86))

- Remove network statements from test.yml
  ([`259fee4`](https://github.com/swgoh-utils/comlink-python/commit/259fee4e39fc5738d6740a7ccb3c30a8051ab345))

### Features

- Add get_leaderboard(). update README.md. add requests package to install_dependencies iin
  pyproject.toml.
  ([`84f1982`](https://github.com/swgoh-utils/comlink-python/commit/84f1982cad26a274cb354f3219f54d2d42b218c9))


## v1.9.0 (2023-01-31)


## v1.8.0 (2023-01-31)

### Build System

- Add swgoh-stat to test.yml workflow
  ([`5ef5ecf`](https://github.com/swgoh-utils/comlink-python/commit/5ef5ecf4474390379603336f5275847ca32f949d))

### Features

- Add get_events(). update get_player_arena to include 'playerDetailsOnly' parameter.
  ([`49189ae`](https://github.com/swgoh-utils/comlink-python/commit/49189ae22d71d6923f8e3d21525551d9b3e1d679))

- Add get_events(). update get_player_arena to include 'playerDetailsOnly' parameter.
  ([`18a143e`](https://github.com/swgoh-utils/comlink-python/commit/18a143e77b86b41193588dda23ce8d9ef6c47d7f))

- Add get_unit_stats()
  ([`c1e46f8`](https://github.com/swgoh-utils/comlink-python/commit/c1e46f8af417dc620422040bbafe9c90a90f4cf1))

- Initial get_unit_stat() implementation.
  ([`59cba96`](https://github.com/swgoh-utils/comlink-python/commit/59cba96f290de3f12e5e807a50a15044eb53fceb))


## v1.7.7 (2023-01-20)

### Bug Fixes

- Replace getGuild() JSON parameter element include_recent_guild_activity_info with
  includeRecentGuildActivityInfo
  ([`4d58e04`](https://github.com/swgoh-utils/comlink-python/commit/4d58e04fb3c3824ffd99b04080a03d178030e61e))

### Build System

- Split ci/cd workflow into separate test and release workflows. add link to PyPi package location
  in README.md. sync file based release version number with GitHub tag.
  ([`4a2f58a`](https://github.com/swgoh-utils/comlink-python/commit/4a2f58a137cb0644ea3c43dd882bc34838fb5856))


## v1.7.6 (2023-01-19)

### Build System

- Enable automated release deployment to PyPi
  ([`cf50a74`](https://github.com/swgoh-utils/comlink-python/commit/cf50a741c2b0aaa4502826524f001bbbf0cde2cf))

- Enable automated release deployment to PyPi
  ([`1c5e0de`](https://github.com/swgoh-utils/comlink-python/commit/1c5e0de60d448f164c03a5af3076e9dd00594a1d))


## v1.7.5 (2023-01-19)

### Build System

- Added installation of python build module to ci/cd workflow
  ([`6e1e2b6`](https://github.com/swgoh-utils/comlink-python/commit/6e1e2b687ab6368330a1f44cbf4a69b3e9953d09))

- Added version source directive to pull from github tag
  ([`b91f0b4`](https://github.com/swgoh-utils/comlink-python/commit/b91f0b47163da90b1abfb0952262427728fcdafa))

- Manually bump release version to sync ci/cd automation
  ([`56c23b2`](https://github.com/swgoh-utils/comlink-python/commit/56c23b20c965a7ef41c67c9b702107541224486a))

- Remove build_command from pyproject.toml
  ([`fe260e0`](https://github.com/swgoh-utils/comlink-python/commit/fe260e0a777ba5ab5f01330ffb263c0f9d049512))

- Updated pyproject.toml for setuptool dynamic version extraction
  ([`f7a8c73`](https://github.com/swgoh-utils/comlink-python/commit/f7a8c736d8279bb88b724d2ff69dde9418e62b42))

- Updated pyproject.toml for setuptool dynamic version extraction
  ([`a954b80`](https://github.com/swgoh-utils/comlink-python/commit/a954b8051ea36d7c4f5660d4b639a32256b04264))

- Updated pyproject.toml for setuptool dynamic version extraction
  ([`1d18cc2`](https://github.com/swgoh-utils/comlink-python/commit/1d18cc21bc3d54660bd5e896c0dfc0f9170fcea7))

- Updated pyproject.toml for setuptools version extraction from module
  ([`86bc265`](https://github.com/swgoh-utils/comlink-python/commit/86bc265955752f497126468cc8441a0395abf159))


## v1.7.4 (2023-01-19)

### Bug Fixes

- Removed asyncio modifications that were committed prematurely
  ([`a7c29e0`](https://github.com/swgoh-utils/comlink-python/commit/a7c29e0960e6415863ceac46024df40229cba35d))

- **pacakge**: Added version.py for external version bumping
  ([`dbdc1e1`](https://github.com/swgoh-utils/comlink-python/commit/dbdc1e1e4df749ae2ea3c5ceec115663c366b4c2))

- **pacakge**: Fixed instance instantiation syntax for pytests
  ([`ec54bea`](https://github.com/swgoh-utils/comlink-python/commit/ec54bea1fdec5a598b0b3c23700090481d88aa70))

- **pacakge**: Fixed instance instantiation syntax for pytests
  ([`eea1156`](https://github.com/swgoh-utils/comlink-python/commit/eea11563ed9f01499b60630459848e7392aef7c3))

- **tests**: Updated tests for latest package import refactor
  ([`4204afb`](https://github.com/swgoh-utils/comlink-python/commit/4204afb4d9453fb65694fea15253c541ffe06054))

### Build System

- Removed publishing of release to PyPi until CD process has been fully validated.
  ([`8e975eb`](https://github.com/swgoh-utils/comlink-python/commit/8e975eb1dbd9ea6f2e8c0e5d7b9409a01fd9d672))

### Chores

- Update links to github
  ([`9f68e03`](https://github.com/swgoh-utils/comlink-python/commit/9f68e0319b6be7b68179c228d5334948ab2e413c))

### Documentation

- **readme**: Corrected hmac example syntax
  ([`83f7233`](https://github.com/swgoh-utils/comlink-python/commit/83f7233ccf0ddcd13f2b65d332d619407d843c29))

### Features

- Added CI/CD workflow
  ([`5519abb`](https://github.com/swgoh-utils/comlink-python/commit/5519abb63f56cc1e4ec438c2fbb37d90788a435c))

- **package**: Refactor for single module import from package. Added game version collection at
  instance instantiation. Game data version parameter for get_game_data() now defaults to current
  version if not supplied.
  ([`0bfa33a`](https://github.com/swgoh-utils/comlink-python/commit/0bfa33a753a2088c801296e4446500fdfb568037))
