# CHANGELOG


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
