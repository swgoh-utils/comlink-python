# Typed access to `/data` segments

`/data` returns 80+ segments. v3 ships **typed `msgspec.Struct`s for 14
of them** (the high-value ones operators actually inspect), exposed
through a single generic helper. Everything else stays as
`dict[str, Any]` — and the same helper accepts your own Struct for
shapes the SDK doesn't ship.

## The helper

```python
from swgoh_comlink import SwgohComlink, compat

with SwgohComlink(url="http://comlink.local:3000") as client:
    raw = client.get_game_data(request_segment=0)        # unchanged: dict[str, Any]
    units = compat.decode_segment(raw, "units")           # → list[Unit]
    materials = compat.decode_segment(raw, "material")    # → list[Material]
    skills = compat.decode_segment(raw, "skill")          # → list[SkillDefinition]
```

The first positional argument is the dict you got back from
`get_game_data`. The second is the top-level segment key from `/data`.
Output is a list of typed Structs you can iterate, dot-access, and
type-check.

If the segment is empty or missing, you get `[]`. No exceptions for the
common "segment absent from this `request_segment`" case.

## Stock segments

`compat.STOCK_SEGMENT_TYPES` lists the 14 known mappings:

| Segment key | Struct | Approx. count |
|---|---|---:|
| `units` | `Unit` | 11,169 |
| `skill` | `SkillDefinition` | 1,892 |
| `material` | `Material` | 858 |
| `ability` | `Ability` | 6,465 |
| `campaign` | `Campaign` | 16 |
| `effect` | `Effect` | 60,015 |
| `equipment` | `Equipment` | 698 |
| `recipe` | `Recipe` | 2,172 |
| `statMod` | `StatMod` | 288 |
| `statModSet` | `StatModSet` | 8 |
| `datacronAffixTemplateSet` | `DatacronAffixTemplateSet` | 722 |
| `datacronTemplate` | `DatacronTemplate` | 61 |
| `datacronSet` | `DatacronSet` | 10 |
| `datacronHelpEntry` | `DatacronHelpEntry` | 5 |

All Struct classes are importable from `swgoh_comlink._models`. Counts
are from the recorded benchmark cassette and will drift as Capital Games
adds content.

## Bring your own Struct

For segments the SDK doesn't ship, or when you want a smaller curated
view of a stock segment, pass `target=` with your own Struct:

```python
import msgspec
from swgoh_comlink import SwgohComlink, compat

class MyTinyMaterial(msgspec.Struct, rename="camel"):
    """Just the three fields I actually care about."""
    id: str = ""
    rarity: int = 0
    tier: int = 0

with SwgohComlink(url="...") as client:
    raw = client.get_game_data(request_segment=0)
    mats = compat.decode_segment(raw, "material", target=MyTinyMaterial)
    # mats is list[MyTinyMaterial] — only the fields you defined.
```

Two things to know about your custom Struct:

1. **`rename="camel"`** — the wire format is camelCase; your Python
   fields should be snake_case and msgspec rewrites them.
2. **Defaults on every field** — `forbid_unknown_fields=False` is the
   default (Comlink ships extra fields you don't care about); make
   every field have a default value so partial cassettes don't break
   decoding.

You don't need to register your type anywhere. The helper only consults
`STOCK_SEGMENT_TYPES` when `target=None`.

## Cost model

On the recorded `/data` cassette, decoded from JSON bytes:

| Path | Decode wall (units alone) | Aggregate decode wall (all 14) |
|---|---:|---:|
| `dict` (untyped msgspec) | 950 ms | ~3,290 ms |
| `typed` (`decode_segment`) | **228 ms** (4.16× faster) | **~1,840 ms** (1.79× faster) |

Aggregate memory: 0.66× the dict baseline (~34% less). Aggregate
resident size: 0.66×. Per-segment numbers in
[`docs/v3/benchmark-report.md`](../benchmark-report.md).

The dict-input path of the helper (the common case after a
`GameDataCache` hit) uses `msgspec.convert` and skips the JSON
re-encode hop, so real-world cost is lower than the bench numbers.

## What's intentionally not typed

* **The other ~70+ `/data` segments** (`battleEnvironments`, `xpTable`,
  `statProgression`, `category`, `helpEntry`, `challenge`,
  `eventSampling`, `warDefinition`, `targetingSet`, `requirement`,
  `powerUpBundle`, `raidConfig`, `guildRaid`, `guildExchangeItem`,
  `table`, `unlockAnnouncementDefinition`, `battleTargetingRule`,
  `territoryBattleDefinition`, `territoryWarDefinition`,
  `environmentCollection`, `challengeStyle`, …). Use `target=` if you
  need them typed.
* **Always-empty / always-null fields** within the stock segments
  (`basicAttack`, `leaderAbility`, `limitBreak`, `uniqueAbility`,
  `effectIconPriorityOverride`, `material.raidImmediateLookup`,
  `equipment.actionLinkLookup`, …). They're dropped from the typed
  view; `forbid_unknown_fields=False` keeps the SDK resilient if
  Capital Games re-populates them.
* **Sparse / variable-shape sub-fields** (`ability.aiParams`,
  `effect.persistentVfxReference`, `recipe.craftRequirement`, …).
  Typed as `dict[str, Any] | None` rather than guessed-at Structs —
  drop the dict back into the typed Struct if you need attribute access.

## Recipe-vs-segment quick reference

* You want one fully-typed list of stock entities → `decode_segment(raw, "segment_key")`.
* You want only a few fields per entry, your own naming → `decode_segment(raw, "segment_key", target=YourStruct)`.
* You want the raw `/data` dict you've always had → `client.get_game_data()` (unchanged).
* You want typed `/data` cached across runs → wrap `GameDataCache` around your client; `decode_segment(cache.get_game_data(client), ...)` works the same on the cached dict.
