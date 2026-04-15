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

# Single collection
units = comlink.get_game_data(items=DataItems.UNITS)

# Multiple collections via addition
data = comlink.get_game_data(items=DataItems.SKILL + DataItems.EQUIPMENT)

# All collections
everything = comlink.get_game_data(items=DataItems.ALL)
```

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
Constants.RELIC_TIERS      # {"0": "LOCKED", "1": "UNLOCKED", "2": "1", ...}
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
functions and do not require a comlink instance.

### calc_current_stamina

::: swgoh_comlink.helpers._conquest.calc_current_stamina
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
