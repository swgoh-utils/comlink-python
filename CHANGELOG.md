# Changelog

<!--next-version-placeholder-->

## v1.12.0 (2023-05-16)
### Feature
* Added get_latest_game_data_version() method for simplified access to game data and language bundle version information ([`dce650f`](https://github.com/swgoh-utils/comlink-python/commit/dce650f29e88758009211039f64689f3ee197e55))

## v1.11.1 (2023-02-19)
### Documentation
* Changed get_guilds_by_criteria() -> search_criteria_template example elements to snake case for compliance with comlink expected input. ([`87cfbe0`](https://github.com/swgoh-utils/comlink-python/commit/87cfbe05d030e86cccd95924755ef6d9092077a3))

## v1.11.0 (2023-02-14)
### Feature
* Add get_guild_leaderboard() ([`402943c`](https://github.com/swgoh-utils/comlink-python/commit/402943cb9441154d36537a27f189e987cbe48cd1))

## v1.10.0 (2023-02-07)
### Feature
* Add get_leaderboard(). update README.md. add requests package to install_dependencies iin pyproject.toml. ([`84f1982`](https://github.com/swgoh-utils/comlink-python/commit/84f1982cad26a274cb354f3219f54d2d42b218c9))

## v1.9.0 (2023-01-31)
### Feature
* Add get_events(). update get_player_arena to include 'playerDetailsOnly' parameter. ([`49189ae`](https://github.com/swgoh-utils/comlink-python/commit/49189ae22d71d6923f8e3d21525551d9b3e1d679))
* Add get_events(). update get_player_arena to include 'playerDetailsOnly' parameter. ([`18a143e`](https://github.com/swgoh-utils/comlink-python/commit/18a143e77b86b41193588dda23ce8d9ef6c47d7f))

## v1.8.0 (2023-01-31)
### Feature
* Add get_unit_stats() ([`c1e46f8`](https://github.com/swgoh-utils/comlink-python/commit/c1e46f8af417dc620422040bbafe9c90a90f4cf1))
* Initial get_unit_stat() implementation. ([`59cba96`](https://github.com/swgoh-utils/comlink-python/commit/59cba96f290de3f12e5e807a50a15044eb53fceb))

## v1.7.7 (2023-01-20)
### Fix
* Replace getGuild() JSON parameter element include_recent_guild_activity_info with includeRecentGuildActivityInfo ([`4d58e04`](https://github.com/swgoh-utils/comlink-python/commit/4d58e04fb3c3824ffd99b04080a03d178030e61e))

### Feature
* Added CI/CD workflow ([`5519abb`](https://github.com/swgoh-utils/comlink-python/commit/5519abb63f56cc1e4ec438c2fbb37d90788a435c))

### Fix
* Removed asyncio modifications that were committed prematurely ([`a7c29e0`](https://github.com/swgoh-utils/comlink-python/commit/a7c29e0960e6415863ceac46024df40229cba35d))
