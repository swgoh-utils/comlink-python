# Helpers API

The `swgoh_comlink.helpers` subpackage provides utility functions, constants,
and data structures for working with game data returned by the Comlink API.

All public names are importable directly from `swgoh_comlink.helpers`:

```python
from swgoh_comlink.helpers import DataItems, Constants, sanitize_allycode
```

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

---

## Conquest Helpers

Functions for working with Conquest game mode data. These are pure calculation
and data-transformation functions and do not require a comlink instance.

### calc_current_stamina

::: swgoh_comlink.helpers._conquest.calc_current_stamina
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
# this release are recognised.
names = ItemNames(game_data, get_localization_dictionary(comlink), enums=comlink.get_enums())

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
