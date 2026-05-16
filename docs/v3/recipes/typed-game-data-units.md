# Typed access to `/data.units`

v3.0 returns `/data` as a raw `dict[str, Any]` for backward compatibility
(82 segments, most without observable schema in our cassettes). The
`units` segment — the largest, ~11k entries — is the one piece of `/data`
where deep typing pays off measurably (2.12× faster decode, 36% less
peak memory, 34% smaller resident footprint on the recorded cassette).

A v3.1 probe ships an **opt-in** typed view of just the units segment.
The dict path is unchanged.

## When to use this

* You consume `/data` regularly and care about decode time or memory.
* You want attribute access (`unit.name_key`, `unit.skill_reference[0].skill_id`)
  instead of stringly-typed dict lookups.
* You want IDE / type-checker support over unit definitions.

If you only need a handful of unit definitions and don't mind dict
indexing, skip this — the helper round-trips through JSON, so the win
only shows up once you're processing many units.

## Usage

```python
from swgoh_comlink import SwgohComlink, compat

with SwgohComlink(url="http://comlink.local:3000") as client:
    raw = client.get_game_data(request_segment=0)   # unchanged dict path
    units = compat.decode_units_segment(raw)         # list[Unit]

    for unit in units:
        if unit.combat_type == 1:                    # 1 = character, 2 = ship
            print(unit.base_id, unit.name_key, len(unit.skill_reference))
```

Works the same with `GameDataCache`:

```python
from swgoh_comlink import compat
from swgoh_comlink._cache import GameDataCache

cache = GameDataCache()
raw = cache.get_game_data(client)                    # disk-or-memory cached
units = compat.decode_units_segment(raw)             # typed view of the segment
```

## What you get on a `Unit`

The shape mirrors the comlink wire format with `snake_case` field names:

* **Scalars**: `id`, `base_id`, `name_key`, `rarity`, `max_rarity`,
  `combat_type`, `force_alignment`, `base_power`, `unit_class`, …
* **Booleans**: `obtainable`, `legend`, `big`, `loaned_unit`, …
* **Typed nested**: `base_stat: UnitBaseStat`, `unit_tier: list[UnitTierEntry]`,
  `relic_definition: RelicDefinition | None`, `skill_reference:
  list[SkillReference]`, `basic_attack_ref: AbilityRef`,
  `mod_recommendation: list[ModRecommendation]`, `example_squad:
  list[ExampleSquadEntry]`, `crew: list[CrewMember]`, `category_id: list[str]`, …
* **Ability refs** share a single 12-field `AbilityRef` Struct
  (`basic_attack_ref`, `leader_ability_ref`, `limit_break_ref[i]`,
  `unique_ability_ref[i]`).

Always-empty / always-null fields in the recorded cassette
(`basicAttack`, `leaderAbility`, `limitBreak`, `uniqueAbility`,
`effectIconPriorityOverride`) are deliberately **omitted** from the
Struct. If you need them, stay on the dict path.

## Cost model

The helper extracts `payload["units"]`, re-encodes it to JSON, and
decodes via a cached `msgspec.json.Decoder(list[Unit])`. The re-encode
round-trip is the honest cost when you're decoding a value already in
dict form (e.g. a cached `/data` response). On the recorded cassette:

| Path | Decode wall | Peak alloc | Resident |
|---|---:|---:|---:|
| `dict` (`UNTYPED_DECODER`) | 685 ms | 462 MiB | 478 MiB |
| `typed` (this helper) | **324 ms** (2.12× faster) | **298 MiB** (0.64×) | **313 MiB** (0.66×) |

If a future v3.x release plumbs the typed decoder through `_request`,
the dict-then-re-encode hop disappears — the helper's contract stays the
same.

## Not yet typed

`/data` carries 82 segments. v3.0 + this probe types one: `units`. The
other 81 (`material`, `equipment`, `skill`, `ability`, `category`, …)
remain `dict[str, Any]` on the response. The probe's numbers green-light
typing the rest in v3.1 (see `docs/v3/benchmark-report.md` "Units-segment
typed-decode experiment").
