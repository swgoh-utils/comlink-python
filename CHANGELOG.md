# CHANGELOG

<!-- insertion marker -->
<a name="v2.4.0"></a>

## [v2.4.0](https://github.com/swgoh-utils/comlink-python/compare/v2.3.1...v2.4.0) (2026-10-09)

### Features

- **helpers:** give events a title and subtitle and keep the game's case ([d6366ce](https://github.com/swgoh-utils/comlink-python/commit/d6366ce36209300fe902150c17b09e5bf77f7e40))
- **client:** cache get_enums() per game data version ([6077166](https://github.com/swgoh-utils/comlink-python/commit/60771668da7ca5ef501becc885085e79612e7a80))
- **helpers:** read item and currency types from get_enums() ([f614e8d](https://github.com/swgoh-utils/comlink-python/commit/f614e8d3ce75ebd2ddd1b1393b5c745cffdecd52))
- **helpers:** accept async clients in sync-named helpers ([8c43c6e](https://github.com/swgoh-utils/comlink-python/commit/8c43c6e9d76b1a2f8ab0480deb2b6787c802cb41))
- **helpers:** add get_game_config and get_game_config_int ([a8db628](https://github.com/swgoh-utils/comlink-python/commit/a8db628140d50b5642d427792cde9d12c7c85dd9))
- **helpers:** add get_guild_activity summary of a guild's recent activity ([ca8a14e](https://github.com/swgoh-utils/comlink-python/commit/ca8a14eca8959f02477c7700785675c71e6cb327))
- **helpers:** add get_event_schedule for live and upcoming events ([8a91f9a](https://github.com/swgoh-utils/comlink-python/commit/8a91f9ae6875a5c559f190a050c6e47ab00c848b))
- **helpers:** add calc_stamina_full_time for Conquest stamina ([1e70512](https://github.com/swgoh-utils/comlink-python/commit/1e705126044e7dabe4fbee820a65ecd0c79034ab))
- **helpers:** name game items, reward previews and id catalogs ([9be7920](https://github.com/swgoh-utils/comlink-python/commit/9be79208d91f341e244f0329e28c3679a8acdc19))
- **helpers:** add ItemType and CurrencyType constant tables ([88568ed](https://github.com/swgoh-utils/comlink-python/commit/88568edb73c4c84cad1f345b88df2d2fb1f7608b))
- **helpers:** add Territory Battle definition helpers ([aa71a71](https://github.com/swgoh-utils/comlink-python/commit/aa71a712425df502444e7b944c82db092b936ee4))
- **helpers:** add unit upgrade cost helpers ([c675d2c](https://github.com/swgoh-utils/comlink-python/commit/c675d2c5a3c03c4bc4011c789249e981f2465ffe))
- **helpers:** add readers for loosely typed wire values ([06de8a3](https://github.com/swgoh-utils/comlink-python/commit/06de8a3847e1600e8e193e6ea6d4a0ca32f99c3b))
- **client:** raise typed HTTP errors and add opt-in retry and pacing ([f9e4341](https://github.com/swgoh-utils/comlink-python/commit/f9e4341c122f8bb1973698369d3942ad05d210c9))
- **exceptions:** add typed HTTP errors carrying status, code, detail and Retry-After ([49919f1](https://github.com/swgoh-utils/comlink-python/commit/49919f165dd7eac67befa86b5fd22add1b42715f))
- **helpers:** add get_unit_abilities and get_named_effects ([8610d57](https://github.com/swgoh-utils/comlink-python/commit/8610d5703ec4cf6c58e3046193f4f82a04a6e590))
- **helpers:** add get_conquest_feats for listing Conquest feats ([6625872](https://github.com/swgoh-utils/comlink-python/commit/6625872f75d9992758a1f738252f896b9f652f0d))

### Bug Fixes

- **client:** make retry pacing safe for concurrent async callers ([d3735e0](https://github.com/swgoh-utils/comlink-python/commit/d3735e0c78d9bed8381aef5856a5b1561a7f52db))
- **helpers:** name GALACTIC_BUNDLE_CURRENCY as the Hyperdrive Token ([dafdc69](https://github.com/swgoh-utils/comlink-python/commit/dafdc692b313f706889770c5ba0952aedcd87cd5))
- **helpers:** harden item helpers against odd records and enum values ([f52f184](https://github.com/swgoh-utils/comlink-python/commit/f52f184f577ed1f7d8fb38a9748ecc5d3cd8bbf9))
- **helpers:** reject TB collections whose entries are not dictionaries ([4f51cd1](https://github.com/swgoh-utils/comlink-python/commit/4f51cd1a847f90457eb76a555bc2ea454755ec6e))
- **helpers:** read type-prefixed enum names in the TB helpers ([55878f8](https://github.com/swgoh-utils/comlink-python/commit/55878f836e6928eb02644d5349c25458e1f5fe56))
- **helpers:** accept partial costs and check collections first in sum_upgrade_costs ([c15ddb6](https://github.com/swgoh-utils/comlink-python/commit/c15ddb6a9103816902b6fcb43f241ae61186fb6c))
- **helpers:** read UnitTier enum names in the gear upgrade helpers ([857b472](https://github.com/swgoh-utils/comlink-python/commit/857b472fcc4ed568be0a162ecf543612420e4bdc))
- **helpers:** read only upper-case text as a decoder-style enum name ([f2e253c](https://github.com/swgoh-utils/comlink-python/commit/f2e253c1aed4a974e5c6b8a098c289fea04b5af0))
- **client:** log when a retrying call gives up ([e078c92](https://github.com/swgoh-utils/comlink-python/commit/e078c9244a7e5e92bd0dc0ae8494191ab8297b82))
- **client:** give back a pacing slot when an async wait is cancelled ([de782f5](https://github.com/swgoh-utils/comlink-python/commit/de782f5d9cec48494f6010644fd93f3c601273c7))
- **client:** reject mistyped RetryPolicy fields with SwgohComlinkTypeError ([105a202](https://github.com/swgoh-utils/comlink-python/commit/105a202b86d6a7b3de9b059fbd68d2436a2eb06e))
- **exceptions:** make typed HTTP errors picklable and copyable ([244e84c](https://github.com/swgoh-utils/comlink-python/commit/244e84c657e276358b9e385914a6f088475b8e85))
- **helpers:** include conquest feats whose id has no kind token ([4fe8819](https://github.com/swgoh-utils/comlink-python/commit/4fe8819e2f9207644667629af09a8c478781d737))
- **helpers:** tolerate missing fields and enum rarity in get_playable_units ([f1c1fdc](https://github.com/swgoh-utils/comlink-python/commit/f1c1fdc9a8143069afa0de0ac204852d2227ae73))
- **helpers:** request guild activity info in get_guild_members ([b7cc896](https://github.com/swgoh-utils/comlink-python/commit/b7cc896f9c927ac3a7a7f121de74717941a7ab45))
- **helpers:** compute get_arena_payout in UTC and return an aware datetime ([cd2c772](https://github.com/swgoh-utils/comlink-python/commit/cd2c772ade2616a90ab9f0e0c5f713c6db59e634))
- **helpers:** use the game's relic offset of 2 in convert_relic_tier ([83c9abb](https://github.com/swgoh-utils/comlink-python/commit/83c9abba8261266d3226ce9d061d5192002f3b03))

### Code Refactoring

- **helpers:** move _localize into _localization for reuse ([70b9c41](https://github.com/swgoh-utils/comlink-python/commit/70b9c418dac39844a9c16bde032afb027ab3684f))

### Performance Improvements

- **helpers:** stop walking the stack on valid item helper calls ([95bcdc3](https://github.com/swgoh-utils/comlink-python/commit/95bcdc35fd8626b68a5af5cd4ea1c7fb98dbd444))

### Docs

- **helpers:** describe hidden_reason as a heuristic ([81d5b21](https://github.com/swgoh-utils/comlink-python/commit/81d5b21da87054618f7599c98adf6167c2339fce))
- **helpers:** pass the client's cached enums to ItemNames in examples ([32cc8d1](https://github.com/swgoh-utils/comlink-python/commit/32cc8d138607ad3818a243532feb2bbb16911c09))
- **readme:** describe the get_enums() cache ([6bd073b](https://github.com/swgoh-utils/comlink-python/commit/6bd073b7244e1f82f6b08cbfc1118d64d2b9bd03))
- **helpers:** show ItemNames reading live enums ([bb38391](https://github.com/swgoh-utils/comlink-python/commit/bb38391b16142a7974d46926bcd8e415045cf082))
- **api:** describe retry jitter, endpoint holds and cancelled waits ([3db84e6](https://github.com/swgoh-utils/comlink-python/commit/3db84e6ad2cf01177bb7030adee8a1b794aefa75))
- **helpers:** explain sync and async client handling ([737e128](https://github.com/swgoh-utils/comlink-python/commit/737e128249c71d37fc1ccabb9f5a2c7334c309eb))
- **helpers:** print the mission scores in the TB example ([12dd359](https://github.com/swgoh-utils/comlink-python/commit/12dd35939fa761fe50a5ef5766cfc44591e98220))
- **helpers:** describe wire readers with public payload examples ([1c976f6](https://github.com/swgoh-utils/comlink-python/commit/1c976f6cf36c7e076667f3d29969d04565ba0bf8))
- **api:** match the retries heading case across client pages ([83cc59c](https://github.com/swgoh-utils/comlink-python/commit/83cc59c4dfc14a0bf621bbaaa4e37ca76e363032))
- **helpers:** document item, reward and catalog helpers ([8d7edf3](https://github.com/swgoh-utils/comlink-python/commit/8d7edf31527fb705e32dbcabcf70222a4769518f))
- **helpers:** document the Territory Battle definition helpers ([6622a3a](https://github.com/swgoh-utils/comlink-python/commit/6622a3a85b476ca83708078aa82ee14ac9abe9d0))
- **helpers:** document upgrade cost helpers and the DataItems bit for 'table' ([32394a8](https://github.com/swgoh-utils/comlink-python/commit/32394a8851e64e9ac5ba5a18d2981ebdcfac38be))
- **helpers:** add Wire Value Helpers section ([ed23e07](https://github.com/swgoh-utils/comlink-python/commit/ed23e07b41e246ac579c6ac751e2b91c6828b795))
- **api:** document typed HTTP errors and the retry policy ([4db0261](https://github.com/swgoh-utils/comlink-python/commit/4db0261f35eb21d92357c72f887762f24f6ae18d))
- **helpers:** clarify create_localized_unit_name_dictionary is keyed by nameKey ([4782fdd](https://github.com/swgoh-utils/comlink-python/commit/4782fdd0addb60f7da804414f2eef1a45e2cc1e6))
- **helpers:** document single-collection DataItems requests and | combining ([b99bcb3](https://github.com/swgoh-utils/comlink-python/commit/b99bcb3ea2e3dc87a27ff69547e43b47f97f7a49))

<a name="v2.3.1"></a>

## [v2.3.1](https://github.com/swgoh-utils/comlink-python/compare/v2.3.0...v2.3.1) (2026-10-05)

### Bug Fixes

- **statcalc:** resolve gear slot for slot-less equipment entries ([8bd7e73](https://github.com/swgoh-utils/comlink-python/commit/8bd7e735a8545d4d688dcfca4ae184219c3bd10b))
- **statcalc:** skip ships with incomplete crew instead of aborting roster ([2e5d514](https://github.com/swgoh-utils/comlink-python/commit/2e5d5140e7e63cd695bbdcb3bcbbf2897970f9a1))
- **statcalc:** carry purchasedAbilityId through raw unit normalization ([bc3e0e8](https://github.com/swgoh-utils/comlink-python/commit/bc3e0e8ee64869f4622640431262369e373f48f0))
- **helpers:** include unit name keys with variant suffixes like _NAME_V2 ([bfe109a](https://github.com/swgoh-utils/comlink-python/commit/bfe109ad8669a7657d2f9d8e55c2d78fa5f20e39))

<a name="v2.3.0"></a>

## [v2.3.0](https://github.com/swgoh-utils/comlink-python/compare/v2.2.0...v2.3.0) (2026-08-03)

### Features

- **cache:** cache game/localization versions from /metadata with configurable TTL (#117) ([d351759](https://github.com/swgoh-utils/comlink-python/commit/d35175900932c79e5836f383fb6b3ce8dd39f6d9))
- **cache:** cache game/localization versions from /metadata with configurable TTL ([8cdd771](https://github.com/swgoh-utils/comlink-python/commit/8cdd7719619ac7b83ceb66c069825572e17d018a))

### Bug Fixes

- **hmac:** sign the bytes actually sent so empty-payload POSTs validate ([943fd7f](https://github.com/swgoh-utils/comlink-python/commit/943fd7ff490813a74ad50d7c4e4c35ef76b3e79d))
- **tests:** call get_game_data with items= instead of the rejected request_segment ([60c19bf](https://github.com/swgoh-utils/comlink-python/commit/60c19bf390818d0610802a1cd3a3ca7f1cb59829))
- **client:** send clientSpecs key expected by /metadata endpoint ([1909912](https://github.com/swgoh-utils/comlink-python/commit/1909912fc10b1deb822b816b46a0e7577da7e422))
- **exceptions:** stop logging tracebacks from exception constructors ([f841fa8](https://github.com/swgoh-utils/comlink-python/commit/f841fa88bd64abc6a66326ee0654e367976733ce))

### Docs

- **changelog:** update for v2.2.0 ([7b917de](https://github.com/swgoh-utils/comlink-python/commit/7b917dea5ce146c2cce9bbd90b436ba010f01207))

<a name="v2.2.0"></a>

## [v2.2.0](https://github.com/swgoh-utils/comlink-python/compare/v2.1.0...v2.2.0) (2026-07-12)

### Features

- **helpers:** add localization dictionary parsing with sync and async support (#108) ([45dce8a](https://github.com/swgoh-utils/comlink-python/commit/45dce8a5f402ccb192b9598d308dd86a703ea43b))

### Bug Fixes

- **tests:** switch HMAC rejection tests from GET to POST endpoint (#89) ([75feb67](https://github.com/swgoh-utils/comlink-python/commit/75feb6701648cbaf986624bb90532b8fe24d443a))
- **helpers:** ensure arena payout time adjusts correctly when shifted to past ([c9e3f59](https://github.com/swgoh-utils/comlink-python/commit/c9e3f59b91a51137867f766f448d7deda07e90b0))
- **helpers:** handle multi-day offsets in get_arena_payout ([e8a6e05](https://github.com/swgoh-utils/comlink-python/commit/e8a6e05d997559c23734dda5fee2c44cd172d2e8))

<a name="v2.1.0"></a>

## [v2.1.0](https://github.com/swgoh-utils/comlink-python/compare/v2.0.7...v2.1.0) (2026-06-03)

### Bug Fixes

- **examples): update string quoting and rename params for localization bundle calls docs(helpers): document parse_swgoh_string and its extended tag grammar chore: add commitlint config and ignore .pythonrc.py fix(helpers:** extend parse_swgoh_string to cover full NGUI tag set (#83) ([1536853](https://github.com/swgoh-utils/comlink-python/commit/15368533fc09cbbf60964d3ca5044fc9e8c91499))

<a name="v2.0.7"></a>

## [v2.0.7](https://github.com/swgoh-utils/comlink-python/compare/v2.0.6...v2.0.7) (2026-03-30)

### Bug Fixes

- update `sanitize_url` to handle HTTPS URLs without ports, update tests for improved coverage ([577951a](https://github.com/swgoh-utils/comlink-python/commit/577951a6877f47a62c7bf062399fcca6611c9caf))


## [v2.0.6](https://github.com/swgoh-utils/comlink-python/releases/tag/v2.0.6) - 2026-03-29

<small>[Compare with v1.18.0rc1](https://github.com/swgoh-utils/comlink-python/compare/v1.18.0rc1...v2.0.6)</small>

### Features

- add Conquest helpers module (`_conquest.py`) with `calc_current_stamina()` for
  computing current Conquest energy based on last refresh time and regeneration
  rate ([044733b](https://github.com/swgoh-utils/comlink-python/commit/044733b)).
- add HTTP status error handling via `response.raise_for_status()` in both sync
  and async request methods ([23e878c](https://github.com/swgoh-utils/comlink-python/commit/23e878c)).
- add examples documentation page and update README with links to examples.
- add `parse_loc_zip()` utility for parsing SWGOH localization bundle ZIP data
  into structured dictionaries.
- add `_localization.py` module with SWGOH string parsing utilities for extracting
  and transforming game localization data.
- improve error handling with enhanced exception hierarchy in `exceptions.py`.
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

- add inline documentation for mod `definitionId` format in `StatCalc/calculator.py`.
- simplify GAC helpers (`_gac.py`) by reducing complexity and improving type
  checks ([61aa92b](https://github.com/swgoh-utils/comlink-python/commit/61aa92b)).
- extract localization helpers from `_utils.py` into dedicated `_localization.py`
  module and update `helpers/__init__.py` exports.
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

### Testing

- add unit tests for `parse_loc_zip` and SWGOH string parsing utilities
  (`test_parse_loc_zip.py`).
- add advanced localization bundle example (`examples/Sync/get_location_bundle_adv.py`).
- add `gameData.json` test fixture to `tests/resources`.
- remove unused imports and minor cleanup across unit test files.
- rewrite unit tests to use `pytest-httpx` mocking instead of `monkeypatch`.
- add comprehensive async client test suite mirroring sync coverage.
- add `test_base.py` with tests for base class utilities, HMAC, payload builders,
  and validation logic.
- add 96 offline unit tests for `GameDataBuilder` transformation logic covering
  all row parsers, builder functions, and utility helpers (`test_builder_base.py`).
- add 68 offline unit tests for `StatCalc` calculator covering stat computation,
  GP calculation, mod formats, gear aggregation, and ship stats (`test_calculator.py`).
- add 107 pure helper function tests covering `_utils`, `_arena`, `_omicron`,
  `_game_data`, `_gac`, `_constants`, `_decorators`, and `globals` (`test_helpers.py`).
- add 29 mocked helper tests for GAC event/bracket scanning and guild member
  retrieval, both sync and async variants (`test_helpers_mocked.py`).
- add 18 migration tool tests covering rules, scanner, reporter, and CLI
  (`test_migrate.py`).
- add 8 tests for `StatCalcAsync`, `GameDataBuilder`, and `GameDataBuilderAsync`
  (`test_statcalc_async.py`).
- add Conquest stamina helper tests in `test_helpers_mocked.py`.
- increase test coverage from 38% to 96% (440 total unit tests).

### Breaking Changes

- remove all sentinel objects (`REQUIRED`, `MISSING`, `GIVEN`,
  `MutualExclusiveRequired`, `OPTIONAL`, `NotSet`) and the `_sentinels.py`
  module entirely. Functions now use standard Python patterns: required
  parameters have no default, optional parameters default to `None`.
- change `get_gac_brackets()` and `async_get_gac_brackets()` `limit` parameter
  from sentinel-based default to `int` with default `0` (meaning no limit).

### Bug Fixes

- fix `calc_current_stamina` logic for accurate regeneration calculation and
  enhance type hinting ([02a2fed](https://github.com/swgoh-utils/comlink-python/commit/02a2fed)).
- fix HMAC empty payload serialization to use empty string (`""`) instead of
  empty object (`{}`) for compatibility with comlink v4 (#51).
- fix `GameDataBuilder` output to match the JS `gameData.json` reference:
  correct field name mappings (`tierList`→`tier`, `unitTierList`→`unitTier`,
  `statList`→`stat`, `equipmentSetList`→`equipmentSet`, `crewMemberList`→`crewMember`),
  flatten unit iteration to use `obtainable`/`obtainableTime` filters instead of
  nested `unitDef` groups, share CR and GP table references where the JS implementation
  does, fix slot decrementing in `_gear_piece_gp_rows()`, add `set=0` filter in
  `_mod_gp_rows()`, and normalize whole-number floats to `int` via `_num()`.
- fix numeric string and negative value handling in `_build_game_data_payload`.

### Dependencies

- replace `requests>=2.32.4` with `httpx>=0.28`.
- add `pytest-httpx>=0.35` and `pytest-asyncio>=0.24` to dev dependencies.
- bump `urllib3` from 2.3.0 to 2.6.3.
- update `certifi` and `charset-normalizer` versions.

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
- add GAC bracket helper examples for sync and async clients
  (`examples/Sync/get_gac_brackets.py`, `examples/Async/get_gac_brackets.py`).
- remove exhaustive test documentation from published docs.

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
