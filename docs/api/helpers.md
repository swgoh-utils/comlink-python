# Helpers API

The `swgoh_comlink.helpers` subpackage provides utility functions, constants,
and data structures for working with game data returned by the Comlink API.

All public names are importable directly from `swgoh_comlink.helpers`:

```python
from swgoh_comlink.helpers import DataItems, Constants, sanitize_allycode
```

### Sync and async clients

Helpers that make requests take a client as their first argument. Each one has an `async_` twin,
and the sync-named helper also accepts a `SwgohComlinkAsync`: it hands the call to the twin and
returns an awaitable. Subclasses of either client are accepted too.

```python
members = get_guild_members(comlink, allycode=123456789)                # SwgohComlink
members = await get_guild_members(async_comlink, allycode=123456789)    # SwgohComlinkAsync
members = await async_get_guild_members(async_comlink, allycode=123456789)
```

Given an async client, argument errors are raised when the result is awaited rather than when the
helper is called. The `async_` twins accept only async clients.

---

## DataItems

`DataItems` is an `IntFlag` enum mapping game data collection names to bit
positions for use with `get_game_data(items=...)`.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import DataItems

comlink = SwgohComlink()

# A single collection
units = comlink.get_game_data(items=DataItems.UNITS)

# Only the collections you need, combined with `|`
data = comlink.get_game_data(items=DataItems.SKILL | DataItems.EQUIPMENT)

# Whole segments (the collections returned by the legacy request_segment= calls)
segments = comlink.get_game_data(items=DataItems.SEGMENT1 | DataItems.SEGMENT2)

# All collections
everything = comlink.get_game_data(items=DataItems.ALL)
```

Request only the collections you need where you can. Comlink assembles the whole
response before sending it, so smaller masks are faster and use less memory on both
sides. For example, `DataItems.CHALLENGE | DataItems.CONQUEST` returns about 32 MB
in about 2.4 seconds, versus about 147 MB in about 12.5 seconds for
`SEGMENT2 | SEGMENT4`.

!!! warning "Combine members with `|`, not `+`"
    Some members are aliases that share a bit with another member. For example,
    `CONQUEST_DEFINITION`, `ARTIFACT_DEFINITION` and `CONQUEST_MISSION` are all the
    `CONQUEST` bit. Adding aliases together sets a different bit:
    `DataItems.CONQUEST_DEFINITION + DataItems.ARTIFACT_DEFINITION` requests
    `ABILITY_DECISION_TREE`. Bitwise OR (`|`) is always safe.

!!! note
    Comlink accepts any `items` bitmask from 1 to 2<sup>52</sup> − 1, or `-1`
    (`DataItems.ALL`) for everything, and rejects values outside that range with an
    HTTP 400. Older Comlink releases had a bug in how CDN URLs were built that could
    make some single-collection requests fail; upgrade Comlink if you see that.

Use `DataItems.members()` to list all available member names.

::: swgoh_comlink.helpers._data_items.DataItems
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - members

---

## Constants

`Constants` holds game-related lookup tables (leagues, divisions, relic tiers,
max values) and provides a `get()` classmethod that resolves both legacy
Constants names and DataItems member names.

```python
from swgoh_comlink.helpers import Constants

Constants.LEAGUES          # {"kyber": 100, "aurodium": 80, ...}
Constants.DIVISIONS        # {"1": 25, "2": 20, ...}
Constants.RELIC_TIERS      # {"1": "LOCKED", "2": "UNLOCKED", "3": "1", ...} (wire relic tier -> relic)
Constants.MAX_VALUES       # {"GEAR_TIER": 13, "UNIT_LEVEL": 85, ...}

# Resolve a collection name to its integer value
Constants.get("UNITS")              # "137438953472"
Constants.get("UnitDefinitions")    # "137438953472" (legacy name)
```

::: swgoh_comlink.helpers._constants.Constants
    options:
      show_root_heading: true
      show_root_full_path: false
      show_if_no_docstring: false
      members:
        - get
        - get_names

---

## Utility Functions

General-purpose validation and conversion helpers.

### sanitize_allycode

::: swgoh_comlink.helpers._utils.sanitize_allycode
    options:
      show_root_heading: true
      show_root_full_path: false

### human_time

::: swgoh_comlink.helpers._utils.human_time
    options:
      show_root_heading: true
      show_root_full_path: false

### convert_relic_tier

::: swgoh_comlink.helpers._utils.convert_relic_tier
    options:
      show_root_heading: true
      show_root_full_path: false

### validate_file_path

::: swgoh_comlink.helpers._utils.validate_file_path
    options:
      show_root_heading: true
      show_root_full_path: false

### get_enum_key_by_value

::: swgoh_comlink.helpers._utils.get_enum_key_by_value
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Wire Value Helpers

Comlink payloads are loosely typed. These functions read one raw field each and fail
soft to a fixed default, so one unusable field never costs the whole record. They do
not need a comlink instance.

| Payload quirk | Helper |
|---------------|--------|
| `int64` values arrive as strings (`"1655938556"`) | `as_int` |
| Ids such as `matchId` sometimes arrive as integers | `as_id` |
| Enums arrive as an int, a numeric string, the member name, or a decoder-style name such as `CURRENCYTYPE_SHARDCURRENCY` | `parse_enum`, `as_scalar` |
| Timestamps are seconds (`guildJoinTime`, Conquest `lastRefreshTime`) or milliseconds (`lastActivityTime`), and `0` means "no time" | `as_epoch` |
| A repeated field with one element can decode as a single object | `as_list` |
| Unit identifiers are `"BASEID:SEVEN_STAR"` or a bare `"BASEID"` | `base_id` |

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import as_epoch, as_int, base_id, parse_enum

comlink = SwgohComlink()
player = comlink.get_player(allycode=123456789)
last_active = as_epoch(player["lastActivityTime"])  # aware UTC datetime, or None
season_score = as_int(player.get("lifetimeSeasonScore"))
roster = {base_id(unit["definitionId"]) for unit in player["rosterUnit"]}

currency = comlink.get_enums()["CurrencyType"]
parse_enum(16, currency)                            # 'SHARD_CURRENCY'
parse_enum("CURRENCYTYPE_SHARDCURRENCY", currency)  # 'SHARD_CURRENCY'
```

!!! note
    `bool` is never read as a number: `as_int(True)` is `0`, not `1`, and
    `parse_enum(True, ...)` is `None`. Values below 10<sup>11</sup> are read as
    seconds by `as_epoch` (10<sup>11</sup> seconds is the year 5138).

### as_int

::: swgoh_comlink.helpers._wire.as_int
    options:
      show_root_heading: true
      show_root_full_path: false

### as_str

::: swgoh_comlink.helpers._wire.as_str
    options:
      show_root_heading: true
      show_root_full_path: false

### as_id

::: swgoh_comlink.helpers._wire.as_id
    options:
      show_root_heading: true
      show_root_full_path: false

### as_scalar

::: swgoh_comlink.helpers._wire.as_scalar
    options:
      show_root_heading: true
      show_root_full_path: false

### as_epoch

::: swgoh_comlink.helpers._wire.as_epoch
    options:
      show_root_heading: true
      show_root_full_path: false

### as_list

::: swgoh_comlink.helpers._wire.as_list
    options:
      show_root_heading: true
      show_root_full_path: false

### base_id

::: swgoh_comlink.helpers._wire.base_id
    options:
      show_root_heading: true
      show_root_full_path: false

### parse_enum

::: swgoh_comlink.helpers._wire.parse_enum
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Arena Helpers

### get_arena_payout

::: swgoh_comlink.helpers._arena.get_arena_payout
    options:
      show_root_heading: true
      show_root_full_path: false

### get_max_rank_jump

::: swgoh_comlink.helpers._arena.get_max_rank_jump
    options:
      show_root_heading: true
      show_root_full_path: false

---

## GAC Helpers

Functions for working with Grand Arena Championships data. Functions prefixed
with `async_` accept a `SwgohComlinkAsync` instance and must be awaited.

### Sync

#### get_current_gac_event

::: swgoh_comlink.helpers._gac.get_current_gac_event
    options:
      show_root_heading: true
      show_root_full_path: false

#### get_gac_brackets

::: swgoh_comlink.helpers._gac.get_gac_brackets
    options:
      show_root_heading: true
      show_root_full_path: false

### Async

#### async_get_current_gac_event

::: swgoh_comlink.helpers._gac.async_get_current_gac_event
    options:
      show_root_heading: true
      show_root_full_path: false

#### async_get_gac_brackets

::: swgoh_comlink.helpers._gac.async_get_gac_brackets
    options:
      show_root_heading: true
      show_root_full_path: false

### Utilities

#### convert_league_to_int

::: swgoh_comlink.helpers._gac.convert_league_to_int
    options:
      show_root_heading: true
      show_root_full_path: false

#### convert_divisions_to_int

::: swgoh_comlink.helpers._gac.convert_divisions_to_int
    options:
      show_root_heading: true
      show_root_full_path: false

#### search_gac_brackets

::: swgoh_comlink.helpers._gac.search_gac_brackets
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Event Helpers

Functions for reading the game's event schedule from `get_events()`. These do not
call comlink themselves.

### get_event_schedule

Lists the events that are live now and those scheduled to start later, with start
and end times as timezone-aware datetimes and readable names.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import get_event_schedule, get_localization_dictionary

comlink = SwgohComlink()
loc = get_localization_dictionary(comlink)

for event in get_event_schedule(comlink.get_events(), loc):
    ends = event["end"].strftime("%Y-%m-%d %H:%M UTC") if event["end"] else "never"
    print(event["status"], event["name"], ends)
# live THE MANDALORIAN - Hero's Journey never
# live ACTION JAXXON - Special Marquee Event 2026-09-24 12:00 UTC
# upcoming THE WANDERER'S BLADE - Special Marquee Event 2026-10-13 12:00 UTC
```

Names keep the game's own capitalisation. Most events have a two-line banner: `title`
is its first line (`"THE MANDALORIAN"`), `subtitle` the second (`"Hero's Journey"`),
and `name` joins them with `" - "`, so either the joined string or the two parts can be
displayed.

!!! note
    Permanent events such as journeys have a single run that the game ends in the
    year 2126; their `end` is `None`. When two runs of an event overlap at a
    changeover, the one ending first is used.

::: swgoh_comlink.helpers._events.get_event_schedule
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._events.ScheduledEvent
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Guild Helpers

### Sync

#### get_guild_members

::: swgoh_comlink.helpers._guild.get_guild_members
    options:
      show_root_heading: true
      show_root_full_path: false

### Async

#### async_get_guild_members

::: swgoh_comlink.helpers._guild.async_get_guild_members
    options:
      show_root_heading: true
      show_root_full_path: false

### get_guild_activity

Summarizes a guild's recent Territory Battles, Territory Wars and raid, and lists its
members with their role, join time, last activity and score in the last raid. Pass it
the result of `get_guild()` requested with `include_recent_guild_activity_info=True`;
without that flag the recent results are empty.

```python
from datetime import datetime, timezone

from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import get_guild_activity

comlink = SwgohComlink()
guild = comlink.get_guild(guild_id, include_recent_guild_activity_info=True)
activity = get_guild_activity(guild)

print(f"TW record: {activity['territory_war_wins']}-{activity['territory_war_losses']}")
if activity["best_territory_battle"]:
    print("Best recent TB:", activity["best_territory_battle"]["total_stars"], "stars")

now = datetime.now(timezone.utc)
for member in activity["members"]:
    days = (now - member["joined"]).days if member["joined"] else None
    print(member["name"], member["role"], days, member["raid_score"])
```

!!! note
    `guildJoinTime` is in epoch seconds while `lastActivityTime` is in epoch
    milliseconds; both are returned as timezone-aware UTC datetimes.

::: swgoh_comlink.helpers._guild.get_guild_activity
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._guild.GuildActivity
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._guild.GuildMemberActivity
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._guild.TerritoryBattleResult
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._guild.TerritoryWarResult
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._guild.RaidResult
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Conquest Helpers

Functions for working with Conquest game mode data. These are pure calculation
and data-transformation functions and do not require a comlink instance.

### calc_current_stamina

::: swgoh_comlink.helpers._conquest.calc_current_stamina
    options:
      show_root_heading: true
      show_root_full_path: false

### calc_stamina_full_time

Returns when a unit's Conquest stamina reaches 100, using the same regeneration
model as `calc_current_stamina`.

```python
from datetime import datetime, timedelta, timezone

from swgoh_comlink.helpers import calc_stamina_full_time

# One entry of a player's Conquest status 'unitStamina' list
unit = {"unitId": "...", "remainingStamina": 90, "lastRefreshTime": "1790164800"}
full_at = calc_stamina_full_time(unit)
time_left = max(full_at - datetime.now(timezone.utc), timedelta(0))
```

::: swgoh_comlink.helpers._conquest.calc_stamina_full_time
    options:
      show_root_heading: true
      show_root_full_path: false

### get_conquest_feats

Lists the feats for a Conquest event (the newest one by default), covering both
global and per-sector feats, with keycard rewards and any bonus artifact.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import DataItems, get_conquest_feats, get_localization_dictionary

comlink = SwgohComlink()
# The CONQUEST bit also covers 'conquestDefinition' and 'artifactDefinition'
game_data = comlink.get_game_data(items=DataItems.CHALLENGE | DataItems.CONQUEST)
loc = get_localization_dictionary(comlink)

feats = get_conquest_feats(
    game_data["conquestDefinition"],
    game_data["challenge"],
    loc,
    game_data["artifactDefinition"],
    difficulty="hard",
)
for feat in feats:
    print(feat["scope"], feat["name"], feat["keycards"])
```

!!! tip
    Requesting only the `CHALLENGE` and `CONQUEST` collections returns about 32 MB of
    game data instead of about 147 MB for `SEGMENT2 | SEGMENT4`, and is roughly 5x faster.

::: swgoh_comlink.helpers._conquest.get_conquest_feats
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._conquest.ConquestFeat
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Territory Battle Helpers

Functions for reading what a Territory Battle asks for and pays from its definition
in the game data: the points each planet's stars need, each mission's squad
requirement and points, and each platoon's points. They read only game data
collections and a localization dictionary, so they do not require a comlink instance
and say nothing about a battle in progress.

Each function covers every Territory Battle in the collection unless `tb_id` names
one: `"t01D"` Hoth Rebel Assault, `"t02D"` Hoth Imperial Retaliation, `"t03D"`
Geonosis Separatist Might, `"t04D"` Geonosis Republic Offensive or `"t05D"` Rise of
the Empire.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import (
    DataItems,
    get_localization_dictionary,
    get_tb_mission_requirements,
    get_tb_mission_scores,
    get_tb_platoon_definitions,
    get_tb_star_thresholds,
)

comlink = SwgohComlink()
# TERRITORY_BATTLE_DEFINITION is the GUILD bit, CAMPAIGN carries 'campaign',
# CATEGORY 'category', and TABLE (the XP_TABLE bit) carries 'table'.
game_data = comlink.get_game_data(
    items=DataItems.TERRITORY_BATTLE_DEFINITION | DataItems.CAMPAIGN | DataItems.CATEGORY | DataItems.TABLE
)
loc = get_localization_dictionary(comlink)
definitions = game_data["territoryBattleDefinition"]

for zone in get_tb_star_thresholds(definitions, loc, tb_id="t05D"):
    print(zone["name"], zone["stars"])

for mission in get_tb_mission_requirements(
    definitions, game_data["campaign"], game_data["category"], loc, tb_id="t05D"
):
    if mission["hidden_reason"] is None:
        print(mission["zone_id"], mission["requirement_text"].replace("\n", " / "))

for score in get_tb_mission_scores(definitions, game_data["table"], tb_id="t05D"):
    if score["hidden_reason"] is None:
        print(score["zone_id"], score["wave_points"])

for zone in get_tb_platoon_definitions(definitions, loc, tb_id="t05D"):
    print(zone["name"], f"R{zone['min_relic']}", zone["total_points"])
```

!!! note "`hidden_reason` is a heuristic"
    A few strike zones are fully defined in game data but never shown in game: a second
    zone on a planet that reuses an earlier zone's mission (`"duplicate"`), and special
    missions left among the strike zones of a version 3 map (`"special"`). The game data
    does not mark them; `hidden_reason` infers them from how the definition is wired. On
    game data 0.40.6 it flags three Rise of the Empire zones and nothing on the other maps.
    Treat it as a filter that may need revisiting when a new map is added.

!!! note
    A mission's requirement is not in the battle definition. Each mission zone names
    a campaign mission, and `get_tb_mission_requirements` reads that mission's
    entry gate from the `campaign` collection. Relic floors are returned as the relic
    level shown in game, not the wire `RelicTier` value.

### get_tb_star_thresholds

::: swgoh_comlink.helpers._territory_battle.get_tb_star_thresholds
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBZoneStars
    options:
      show_root_heading: true
      show_root_full_path: false

### get_tb_mission_requirements

::: swgoh_comlink.helpers._territory_battle.get_tb_mission_requirements
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBMissionRequirement
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBCategory
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBMandatoryUnit
    options:
      show_root_heading: true
      show_root_full_path: false

### get_tb_mission_scores

::: swgoh_comlink.helpers._territory_battle.get_tb_mission_scores
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBMissionScore
    options:
      show_root_heading: true
      show_root_full_path: false

### get_tb_platoon_definitions

::: swgoh_comlink.helpers._territory_battle.get_tb_platoon_definitions
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBReconZone
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._territory_battle.TBPlatoon
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Game Data Helpers

Pure data-transformation functions for working with game data collections.
These do not require a comlink instance.

### get_raid_leaderboard_ids

::: swgoh_comlink.helpers._game_data.get_raid_leaderboard_ids
    options:
      show_root_heading: true
      show_root_full_path: false

### create_localized_unit_name_dictionary

::: swgoh_comlink.helpers._game_data.create_localized_unit_name_dictionary
    options:
      show_root_heading: true
      show_root_full_path: false

### get_playable_units

::: swgoh_comlink.helpers._game_data.get_playable_units
    options:
      show_root_heading: true
      show_root_full_path: false

### get_current_datacron_sets

::: swgoh_comlink.helpers._game_data.get_current_datacron_sets
    options:
      show_root_heading: true
      show_root_full_path: false

### get_datacron_dismantle_value

::: swgoh_comlink.helpers._game_data.get_datacron_dismantle_value
    options:
      show_root_heading: true
      show_root_full_path: false

### get_datacron_dismantle_total

::: swgoh_comlink.helpers._game_data.get_datacron_dismantle_total
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Game Configuration Helpers

Functions for reading the game's own configuration values (limits and tuning) from
`get_game_metadata()`. These do not call comlink themselves.

### get_game_config

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import get_game_config, get_game_config_int

comlink = SwgohComlink()
metadata = comlink.get_game_metadata()

config = get_game_config(metadata)               # every key, as strings
config["stat-mod-highlight-stat"]                # 'SPEED'
get_game_config_int(metadata, "max-conquest-currency")   # 3500
get_game_config_int(metadata, "stat-mod-max-storage")    # 500
get_game_config_int(metadata, "max-datacron-currency")   # 100000000
```

!!! note
    Every configuration value is a string, including the numeric ones, and some keys
    hold text such as `"true"` or `"SPEED"`. `get_game_config_int` returns its
    `default` (`None` unless given) for a missing key or a value that is not an integer.

::: swgoh_comlink.helpers._game_config.get_game_config
    options:
      show_root_heading: true
      show_root_full_path: false

### get_game_config_int

::: swgoh_comlink.helpers._game_config.get_game_config_int
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Ability and Effect Helpers

Functions for reading unit abilities and named battle effects from game data and a
localization dictionary. These do not require a comlink instance.

### get_unit_abilities

Lists units' abilities with their name, kind, description at every level, and which
level is a zeta or an omicron. Ships include their crew members' abilities.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import (
    OMICRON_MODE,
    DataItems,
    get_localization_dictionary,
    get_playable_units,
    get_unit_abilities,
)

comlink = SwgohComlink()
game_data = comlink.get_game_data(items=DataItems.UNITS | DataItems.SKILL | DataItems.ABILITY)
loc = get_localization_dictionary(comlink)

# Every Territory War omicron, with what it adds
for ability in get_unit_abilities(
    get_playable_units(game_data["units"]),
    game_data["skill"],
    game_data["ability"],
    loc,
    omicron_mode=8,
):
    omicron_tier = next(tier for tier in ability["tiers"] if tier["is_omicron"])
    print(ability["unit_name"], ability["name"], OMICRON_MODE[ability["omicron_mode"]])
    print("   ", omicron_tier["upgrade"])
```

!!! note
    Names and descriptions come from the keys each `ability` record names, so a
    reworked ability shows its current text rather than the original wording the
    game keeps under the old key. `skill.nameKey` is not used: it is usually a
    placeholder such as `DEFENSE_UP_NAME_KEY`.

::: swgoh_comlink.helpers._abilities.get_unit_abilities
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._abilities.UnitAbility
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._abilities.AbilityTier
    options:
      show_root_heading: true
      show_root_full_path: false

### get_named_effects

Maps every named buff and debuff (Potency Up, Fear, Overcharge, ...) to its in-game
description. Useful for tooltips, help commands, or resolving an effect name a user
typed.

```python
from swgoh_comlink.helpers import get_localization_dictionary, get_named_effects

effects = get_named_effects(get_localization_dictionary(comlink))
print(effects["Potency Up"]["description"])
# Increased chance to apply detrimental effects
```

::: swgoh_comlink.helpers._abilities.get_named_effects
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._abilities.NamedEffect
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Item and Reward Helpers

Functions for naming the items that rewards, previews and inventories carry, and
catalogs for game data whose names cannot be derived from their ids. These do not
require a comlink instance.

### ItemNames

Resolves an `(ItemType, id)` pair to a display name. Item ids are only unique within
an `ItemType`, so both are needed. `ItemType` may be a number (`7`) or an enum name
(`"MATERIAL"`), so game data fetched with or without `enums=True` works.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import DataItems, ItemNames, get_localization_dictionary

comlink = SwgohComlink()
game_data = comlink.get_game_data(
    items=DataItems.MATERIAL
    | DataItems.EQUIPMENT
    | DataItems.UNITS
    | DataItems.MYSTERY_STAT_MOD  # also covers 'mysteryBox'
    | DataItems.STAT_MOD_SET
    | DataItems.PLAYER_TITLE
    | DataItems.PLAYER_PORTRAIT
)
# enums is optional; with it, item types and currencies added to the game since
# this release are recognised. get_enums() fetches them once per game data version
# and caches them on the client as comlink.enums.
comlink.get_enums()
names = ItemNames(game_data, get_localization_dictionary(comlink), enums=comlink.enums)

names.get("MATERIAL", "unitshard_GLLEIA")  # 'Leia Organa'
names.get(3, "GRIND")                      # 'Credits'
names.get(16, "35155")                     # '5-dot Defense Square mod (A)'
names.get(6, "")                           # None: XP names no particular item
```

!!! note
    No game data collection names a currency, so currencies are named from
    `CURRENCY_NAMES`, which is English whatever the localization. A currency it does
    not list but `get_enums()` does is spelled out from its member name
    (`GUILD_RAID_CURRENCY_13` reads "Guild Raid Currency 13"). A mystery mod has
    no name of its own and is described by what it rolls, in English with a
    localized set name.

::: swgoh_comlink.helpers._items.ItemNames
    options:
      show_root_heading: true
      show_root_full_path: false

### get_named_rewards

Reads a reward preview list (a campaign mission's `rewardPreview`,
`firstCompleteRewardPreview`, `instanceFirstCompleteRewardPreview` or
`conditionalRewardsPreview`, or an event instance's `rewardPreview`) into named
rewards. Items of a `conditionalRewardsPreview` are nested one level down, under
`bucketItem`, and are listed with the requirement they depend on. A mission's rank
reward previews (`rankRewardPreview`, `immediateRegularRankRewardPreview`) are
not read: each of their entries is a rank range, so pass an entry's
`detailedReward` (or `primaryReward`) list instead.

```python
from swgoh_comlink.helpers import get_named_rewards

game_data = comlink.get_game_data(items=DataItems.CAMPAIGN | DataItems.MATERIAL | DataItems.UNITS)
names = ItemNames(game_data, get_localization_dictionary(comlink))

events = next(c for c in game_data["campaign"] if c["id"] == "EVENTS")
for campaign_map in events["campaignMap"]:
    for group in campaign_map["campaignNodeDifficultyGroup"]:
        for node in group["campaignNode"]:
            for mission in node["campaignNodeMission"]:
                for reward in get_named_rewards(mission["conditionalRewardsPreview"], names):
                    print(node["id"], mission["id"], reward["name"], reward["max_quantity"])
```

::: swgoh_comlink.helpers._items.get_named_rewards
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._items.NamedReward
    options:
      show_root_heading: true
      show_root_full_path: false

### get_mod_catalog

Recovers an equipped mod's set, slot and rarity from its `definitionId`, and each
set's name and how many mods complete it.

```python
from swgoh_comlink.helpers import get_mod_catalog

game_data = comlink.get_game_data(items=DataItems.STAT_MOD_SET)  # also covers 'statMod'
catalog = get_mod_catalog(game_data["statMod"], game_data["statModSet"], get_localization_dictionary(comlink))

player = comlink.get_player(allycode=123456789)
for equipped in player["rosterUnit"][0]["equippedStatMod"]:
    mod = catalog["definitions"][equipped["definitionId"]]
    print(mod["set_name"], mod["slot_name"], mod["rarity"], catalog["sets"][mod["set_id"]]["set_count"])
```

::: swgoh_comlink.helpers._items.get_mod_catalog
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._items.ModCatalog
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._items.ModSet
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._items.ModDefinition
    options:
      show_root_heading: true
      show_root_full_path: false

### get_data_disc_names

::: swgoh_comlink.helpers._items.get_data_disc_names
    options:
      show_root_heading: true
      show_root_full_path: false

### get_player_title_names

::: swgoh_comlink.helpers._items.get_player_title_names
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Upgrade Cost Helpers

Functions for working out what the game charges to take a unit up: the gear for each
gear tier and the salvage it is crafted from, relic promotions, and ability upgrades
with their zeta and omicron levels. These do not require a comlink instance.

Every cost is an `UpgradeCost`: credits, Ship Building Materials (`ship_credits`,
which ship abilities charge instead of credits), materials by `material` id, and gear
pieces by `equipment` id. `sum_upgrade_costs` adds any mix of them and, given the
`equipment` and `recipe` collections, crafts gear down to the salvage it is made from.

```python
from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import (
    DataItems,
    get_ability_upgrade_costs,
    get_relic_promotion_costs,
    get_unit_gear_tiers,
    sum_upgrade_costs,
)

comlink = SwgohComlink()
# DataItems.TABLE (an alias of XP_TABLE) returns the 'table' collection as well as 'xpTable'
game_data = comlink.get_game_data(
    items=DataItems.UNITS | DataItems.EQUIPMENT | DataItems.RECIPE | DataItems.SKILL | DataItems.TABLE
)
units, equipment, recipes = game_data["units"], game_data["equipment"], game_data["recipe"]

# G1 to G13: the pieces of tiers 1 to 12, crafted down to salvage
gear = get_unit_gear_tiers(units, "COMMANDERLUKESKYWALKER")
g13 = sum_upgrade_costs((tier["cost"] for tier in gear), equipment, recipes)

# R0 to R9: the first nine promotions
relics = get_relic_promotion_costs(game_data["table"], recipes)
r9 = sum_upgrade_costs(relic["cost"] for relic in relics[:9])

# Every ability to its maximum level
abilities = get_ability_upgrade_costs(units, game_data["skill"], recipes, "COMMANDERLUKESKYWALKER")
maxed = sum_upgrade_costs(tier["cost"] for ability in abilities for tier in ability["tiers"])

total = sum_upgrade_costs([g13, r9, maxed])
print(f"{total['credits']:,} credits", total["materials"], total["equipment"])
```

!!! note
    Costs are exact or not reported: a recipe ingredient with a quantity range
    (`minQuantity` differing from `maxQuantity`), a currency other than credits or Ship
    Building Materials, or a missing recipe, piece or skill raises
    `SwgohComlinkValueError` rather than being guessed at or skipped. Game data fetched
    with `enums=True` works too.

### get_unit_gear_tiers

::: swgoh_comlink.helpers._upgrades.get_unit_gear_tiers
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.GearTier
    options:
      show_root_heading: true
      show_root_full_path: false

### get_gear_craft_tree

::: swgoh_comlink.helpers._upgrades.get_gear_craft_tree
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.GearCraftNode
    options:
      show_root_heading: true
      show_root_full_path: false

### get_relic_promotion_costs

::: swgoh_comlink.helpers._upgrades.get_relic_promotion_costs
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.RelicPromotionCost
    options:
      show_root_heading: true
      show_root_full_path: false

### get_ability_upgrade_costs

::: swgoh_comlink.helpers._upgrades.get_ability_upgrade_costs
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.AbilityUpgradeCosts
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.AbilityUpgradeTier
    options:
      show_root_heading: true
      show_root_full_path: false

### sum_upgrade_costs

::: swgoh_comlink.helpers._upgrades.sum_upgrade_costs
    options:
      show_root_heading: true
      show_root_full_path: false

::: swgoh_comlink.helpers._upgrades.UpgradeCost
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Omicron Helpers

Functions for querying omicron skill data from game data collections.

### get_tw_omicrons

::: swgoh_comlink.helpers._omicron.get_tw_omicrons
    options:
      show_root_heading: true
      show_root_full_path: false

### get_omicron_skills

::: swgoh_comlink.helpers._omicron.get_omicron_skills
    options:
      show_root_heading: true
      show_root_full_path: false

### get_omicron_skill_tier

::: swgoh_comlink.helpers._omicron.get_omicron_skill_tier
    options:
      show_root_heading: true
      show_root_full_path: false

### is_omicron_skill

::: swgoh_comlink.helpers._omicron.is_omicron_skill
    options:
      show_root_heading: true
      show_root_full_path: false

### get_unit_from_skill

::: swgoh_comlink.helpers._omicron.get_unit_from_skill
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Localization Helpers

Utilities for working with the SWGOH client's BBCode-style markup that appears
throughout localization bundles (ability descriptions, mod descriptions, event
banners, etc.).

### parse_swgoh_string

Parse a raw localization string and convert it to plain text, ANSI-colored
terminal output, Discord markdown, or HTML. The parser follows
`NGUIText.ParseSymbol()` semantics, so it handles the same tag family the game
engine itself supports.

```python
from swgoh_comlink.helpers import parse_swgoh_string

raw = "[c][FF0000][b]Boss[/b][-] deals [u]2x[/u] damage[/c]"

parse_swgoh_string(raw)                       # 'Boss deals 2x damage'
parse_swgoh_string(raw, output="discord")     # '**Boss** deals __2x__ damage'
parse_swgoh_string(raw, output="web")         # HTML with <b>, <u>, <span style=...>
parse_swgoh_string(raw, output="terminal")    # ANSI truecolor escapes
```

Supported markup:

| Tag(s) | Purpose |
|--------|---------|
| `[c] [/c] [-c]` | Optional color block wrapper |
| `[-]` | Reset the active color |
| `[RGB]` / `[RGBA]` / `[RRGGBB]` / `[RRGGBBAA]` | Hex color literal (short forms duplicate each nibble) |
| `[A]` | 1-digit hex alpha (reuses the previous RGB or white) |
| `[b] [/b]` / `[i] [/i]` | Bold / italic |
| `[u] [/u]` / `[s] [/s]` | Underline / strikethrough |
| `[t] [/t]` | Sprite color marker (stripped in text output) |
| `[sub] [sub=X] [/sub]` / `[sup] [sup=X] [/sup]` | Subscript / superscript with optional scale |
| `[y=X] [/y]` | Font scaling (web output uses inline `font-size`) |
| `\n` | Literal backslash-n escape -> newline |

The `[c]...[/c]` wrapper is optional — bare `[FF0000]` takes effect on its
own, and `[-]` clears the active color whether or not you're inside a `[c]`
block.

::: swgoh_comlink.helpers._localization.parse_swgoh_string
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Decorators

### func_timer

::: swgoh_comlink.helpers._decorators.func_timer
    options:
      show_root_heading: true
      show_root_full_path: false

### func_debug_logger

::: swgoh_comlink.helpers._decorators.func_debug_logger
    options:
      show_root_heading: true
      show_root_full_path: false

---

## Stat Data Constants

Reference data dictionaries available as module-level exports. These are also
accessible via `Constants` for backward compatibility.

| Name | Description |
|------|-------------|
| `STAT_ENUMS` | Mapping of stat enum names to integer values |
| `UNIT_STAT_ENUMS_MAP` | Mapping of stat IDs to enum name and display name |
| `STATS` | Stat display names and formatting info |
| `MOD_SET_IDS` | Mod set type ID to name mapping |
| `MOD_SLOTS` | Mod slot ID to name mapping |
| `UNIT_RARITY` | Rarity integer to star count mapping |
| `UNIT_RARITY_NAMES` | Rarity integer to display name mapping |
| `LANGUAGES` | Supported game language codes |
| `OMICRON_MODE` | Omicron mode IDs to game mode names |
| `ITEM_TYPES` | `ItemType` number to enum member name (a snapshot of `get_enums()`) |
| `CURRENCY_TYPES` | `CurrencyType` number to enum member name (a snapshot of `get_enums()`) |
| `CURRENCY_NAMES` | `CurrencyType` member name to English display name |
