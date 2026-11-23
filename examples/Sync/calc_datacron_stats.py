"""
calc_datacron_stats.py
Applying a datacron to a roster with local StatCalc support.

A datacron is never equipped to a unit — a player owns dozens and picks one per
squad when they deploy. So there is no such thing as "this unit's stats with
datacrons", only "this unit's stats given *this* datacron". You name the one you
mean; the library never chooses.

Demonstrates:
  1. Applying a datacron and reading its contribution
  2. Combining `final` and `datacron` to get battle-ready stats
  3. Affix requirements — the same datacron gives different units different amounts
  4. Comparing several datacrons for one unit
  5. Ships, which datacrons never touch
  6. Doing the same against a real player from a running Comlink service

Examples 1 to 5 use a hand-authored roster and need only game data, which is
fetched from GitHub. Example 6 needs a running Comlink service.
"""

from swgoh_comlink import StatCalc, SwgohComlink

# ── A datacron, shaped as the game reports one ────────────────────────────
#
# Affixes come in threes. Every third one grants an *ability* rather than a
# stat — it reports stat type 1 with value 0 and names a targeting rule. Those
# contribute nothing to stats and StatCalc skips them.
#
# `requiredUnitTier` is a gear tier and `requiredRelicTier` a relic tier. Both
# are compared directly against the unit. Note relic tiers are encoded with
# their locked and unlocked base states occupying the first two values, so a
# `requiredRelicTier` of 8 means relic 6 as a player would count it.
#
# Values are fixed point, where 1e8 is 100%. 27143270 is 27.14327%.


def stat_affix(stat_type, value, unit_tier=0, relic_tier=1):
    return {
        "statType": stat_type,
        "statValue": str(value),
        "requiredUnitTier": unit_tier,
        "requiredRelicTier": relic_tier,
        "abilityId": "",
        "targetRule": "",
    }


def ability_affix(ability_id, unit_tier=0, relic_tier=1):
    return {
        "statType": 1,
        "statValue": "0",
        "requiredUnitTier": unit_tier,
        "requiredRelicTier": relic_tier,
        "abilityId": ability_id,
        "targetRule": "target_datacron_darkside",
    }


# Stat types: 16 Critical Damage, 48 Offense%, 56 Protection%
maxed_datacron = {
    "id": "maxed",
    "affix": [
        stat_affix(16, 17_443_980, unit_tier=2),
        stat_affix(48, 2_828_575, unit_tier=2),
        ability_affix("datacron_faction_generic_043", unit_tier=2),
        stat_affix(16, 34_405_787, unit_tier=4),
        stat_affix(16, 33_342_140, unit_tier=4),
        ability_affix("datacron_faction_generic_007", relic_tier=6),
        stat_affix(48, 19_515_055, relic_tier=8),
        stat_affix(56, 27_143_270, relic_tier=8),
        ability_affix("datacron_character_talia_001", relic_tier=8),
    ],
}

# A shorter one, for the comparison in Example 4.
starter_datacron = {
    "id": "starter",
    "affix": [
        stat_affix(56, 8_305_491, unit_tier=2),
        stat_affix(55, 6_086_343, unit_tier=2),
        ability_affix("datacron_faction_generic_023", unit_tier=2),
    ],
}


def character(def_id, gear_tier=13, relic_tier=12):
    """A roster unit. `relic_tier=None` gives a unit with no relic at all."""
    return {
        "definitionId": f"{def_id}:SEVEN_STAR",
        "currentRarity": 7,
        "currentLevel": 85,
        "currentTier": gear_tier,
        "equipment": [],
        "skill": [],
        "equippedStatMod": [],
        "relic": None if relic_tier is None else {"currentTier": relic_tier},
    }


calc = StatCalc()  # fetches game data from GitHub on init


# ── Example 1: apply a datacron and read its contribution ─────────────────

player = {
    "rosterUnit": [character("CADBANE")],
    "datacron": [maxed_datacron, starter_datacron],
}

calc.calc_player_stats(player, datacron_id="maxed")
stats = player["rosterUnit"][0]["stats"]


def show(value):
    """Percentage stats come back as fractions; flat stats as whole numbers."""
    return f"{value:,.0f}" if abs(value) >= 100 else f"{value:.4f}"


print("=== Example 1: what the datacron adds ===")
for name, amount in sorted(stats["datacron"].items()):
    print(f"  {name:<20} +{show(amount)}")

# Ask for nothing and nothing changes — no `datacron` key appears at all.
untouched = {"rosterUnit": [character("CADBANE")], "datacron": []}
calc.calc_player_stats(untouched)
print("\n  bucket present when no datacron requested:", "datacron" in untouched["rosterUnit"][0]["stats"])


# ── Example 2: combining the buckets ──────────────────────────────────────
#
# The `datacron` bucket sits *beside* `final`, never inside it. A datacron is a
# hypothetical you supplied, so folding it into `final` would make that field
# mean different things depending on an argument. Add them yourself:

combined = {name: value + stats["datacron"].get(name, 0) for name, value in stats["final"].items()}


print("\n=== Example 2: final + datacron ===")
for name in ("Protection", "Physical Damage", "Critical Damage", "Health"):
    before, after = stats["final"][name], combined[name]
    moved = "" if before == after else "  <- moved"
    print(f"  {name:<18} {show(before):>10}  ->  {show(after):>10}{moved}")

# Health is untouched because this datacron carries no Health affix. That is
# the normal case: a datacron moves a handful of stats, not all of them.
#
# The addition is correct for *every* stat, including ones reported as
# percentages such as Armor. Those are stored non-linearly, so a raw percentage
# could not simply be added — the bucket holds the marginal amount the datacron
# actually contributes on top of everything else.


# ── Example 3: affix requirements ─────────────────────────────────────────
#
# Each affix names a gear tier and a relic tier the unit must reach. One
# datacron therefore contributes differently across a roster.

squad = {
    "rosterUnit": [
        character("CADBANE", gear_tier=13, relic_tier=12),  # relic 10 — clears everything
        character("BOSSK", gear_tier=13, relic_tier=7),  # relic 5 — below the relic-8 affixes
        character("JAWA", gear_tier=1, relic_tier=None),  # no relic — clears nothing
    ],
    "datacron": [maxed_datacron],
}
calc.calc_player_stats(squad, datacron_id="maxed")

print("\n=== Example 3: the same datacron, three units ===")
for unit in squad["rosterUnit"]:
    name = unit["definitionId"].split(":")[0]
    relic = (unit["relic"] or {}).get("currentTier", 1)
    granted = sorted(unit["stats"]["datacron"]) or ["nothing"]
    print(f"  {name:<9} gear {unit['currentTier']:<3} relic {relic:<3} -> {', '.join(granted)}")

# BOSSK sits below the relic requirement on two affixes, so he gets strictly
# less than CADBANE from the very same datacron. JAWA qualifies for nothing.


# ── Example 4: comparing datacrons ────────────────────────────────────────
#
# The library never picks for you, so comparing means asking twice.

print("\n=== Example 4: which datacron suits this unit? ===")
for datacron_id in ("maxed", "starter"):
    candidate = {"rosterUnit": [character("CADBANE")], "datacron": [maxed_datacron, starter_datacron]}
    calc.calc_player_stats(candidate, datacron_id=datacron_id)
    bucket = candidate["rosterUnit"][0]["stats"]["datacron"]
    protection = bucket.get("Protection", 0)
    damage = bucket.get("Physical Damage", 0)
    print(f"  {datacron_id:<9} Protection +{protection:<10,.0f} Physical Damage +{damage:,.0f}")


# ── Example 5: ships ──────────────────────────────────────────────────────
#
# Datacrons are a squad mechanic. No game mode applies one to a fleet battle,
# so ships receive no bucket and their stats are untouched.

fleet = {
    "rosterUnit": [character("CADBANE"), character("VULTUREDROID")],  # a crewless ship
    "datacron": [maxed_datacron],
}
calc.calc_player_stats(fleet, datacron_id="maxed")

print("\n=== Example 5: ships are never affected ===")
for unit in fleet["rosterUnit"]:
    name = unit["definitionId"].split(":")[0]
    has_bucket = "datacron" in unit["stats"]
    print(f"  {name:<14} datacron bucket: {has_bucket}")


# ── Example 6: a real player ──────────────────────────────────────────────
#
# Requires a running Comlink service. The datacron id comes from the player's
# own collection, which is why this entry point takes an id rather than an
# object — `calc_roster_stats` and `calc_char_stats` take the object, having no
# player to look it up in. Naming a datacron the player does not own raises
# KeyError, so a mistyped id fails loudly rather than silently adding nothing.

comlink = SwgohComlink()
real_player = comlink.get_player(allycode=314927874)

print("\n=== Example 6: a real player ===")
if not real_player.get("datacron"):
    print("  this player owns no datacrons")
else:
    chosen = real_player["datacron"][0]
    calc.calc_player_stats(real_player, datacron_id=chosen["id"])

    affected = [unit for unit in real_player["rosterUnit"] if unit.get("stats", {}).get("datacron")]
    print(f"  {chosen['templateId']} adds stats to {len(affected)} of {len(real_player['rosterUnit'])} units")
    for unit in affected[:3]:
        name = unit["definitionId"].split(":")[0]
        added = ", ".join(f"{stat} +{show(amount)}" for stat, amount in sorted(unit["stats"]["datacron"].items()))
        print(f"  {name:<20} {added}")
