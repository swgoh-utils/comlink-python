# coding=utf-8
"""
Slimmed Constants facade.

Collection bit values have been removed (use :class:`DataItems` instead).
Stat data is proxied from :mod:`._stat_data` for backward compatibility.
"""

from __future__ import annotations

import logging

from ._data_items import DataItems
from ._stat_data import (
    LANGUAGES,
    MOD_SET_IDS,
    MOD_SLOTS,
    OMICRON_MODE,
    STAT_ENUMS,
    STATS,
    UNIT_RARITY,
    UNIT_RARITY_NAMES,
    UNIT_STAT_ENUMS_MAP,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy name mapping: old Constants PascalCase → DataItems UPPER_SNAKE_CASE
# ---------------------------------------------------------------------------

_LEGACY_NAME_MAP: dict[str, str] = {
    "ALL": "ALL",
    "CategoryDefinitions": "CATEGORY",
    "UnlockAnnouncements": "UNLOCK_ANNOUNCEMENT_DEFINITION",
    "SkillDefinitions": "SKILL",
    "EquipmentDefinitions": "EQUIPMENT",
    "BattleEffectDefinitions": "EFFECT",
    "AllTables": "XP_TABLE",
    "EnvironmentDefinitions": "BATTLE_ENVIRONMENTS",
    "EventSampling": "EVENT_SAMPLING",
    "BattleTargetingSets": "TARGETING_SET",
    "Requirements": "REQUIREMENT",
    "PowerUpBundles": "POWER_UP_BUNDLE",
    "GuildBannerDefinition": "GUILD_BANNER",
    "BattleTargetingRules": "BATTLE_TARGETING_RULE",
    "PersistentVFX": "PERSISTENT_VFX",
    "CraftingMaterialDefinitions": "MATERIAL",
    "PlayerTitleDefinitions": "PLAYER_TITLE",
    "PlayerPortraitDefinitions": "PLAYER_PORTRAIT",
    "TimeZoneChangeConfig": "TIME_ZONE_CHANGE_CONFIG",
    "EnvironmentCollections": "ENVIRONMENT_COLLECTION",
    "PersistentEffectPriorities": "EFFECT_ICON_PRIORITY",
    "SocialStatus": "SOCIAL_STATUS",
    "AbilityDefinitions": "ABILITY",
    "StatProgression": "STAT_PROGRESSION",
    "Challenge": "CHALLENGE",
    "WarDefinitions": "WAR_DEFINITION",
    "StatMod": "STAT_MOD_SET",
    "RecipeDefinitions": "RECIPE",
    "ModRecommendations": "MOD_RECOMMENDATION",
    "ScavengerConversionSets": "SCAVENGER_CONVERSION_SET",
    "Guild": "GUILD",
    "Mystery": "MYSTERY_BOX",
    "CooldownDefinitions": "COOLDOWN",
    "DailyActionCapDefinitions": "DAILY_ACTION_CAP",
    "EnergyRewards": "ENERGY_REWARD",
    "UnitGuideDefinitions": "UNIT_GUIDE_DEFINITION",
    "GalacticBundleDefinitions": "GALACTIC_BUNDLE",
    "RelicTierDefinitions": "RELIC_TIER_DEFINITION",
    "UnitDefinitions": "UNITS",
    "CampaignDefinitions": "CAMPAIGN",
    "Conquest": "CONQUEST",
    "RecommendedSquads": "RECOMMENDED_SQUAD",
    "UnitGuideLayouts": "UNIT_GUIDE_LAYOUT",
    "DailyLoginRewardDefinitions": "DAILY_LOGIN_REWARD_DEFINITION",
    "CalendarCategories": "CALENDAR_CATEGORY_DEFINITION",
    "TerritoryTournamentDailyRewards": "TERRITORY_TOURNAMENT_DAILY_REWARD_TABLE",
    "DatacronDefinitions": "DATACRON",
    "DisplayableEnemyDefinitions": "DISPLAYABLE_ENEMY",
    "EpisodeDefinition": "EPISODE_DEFINITION",
    "LinkingReward": "LINKING_REWARD",
}


class Constants:
    """Collection of constants used throughout the SwgohComlink project.

    Game data collection bit values have been moved to :class:`DataItems`.
    The ``get()`` classmethod still resolves both old Constants names and
    DataItems member names for backward compatibility.
    """

    RELIC_OFFSET = 2

    MAX_VALUES: dict[str, int] = {
        "GEAR_TIER": 13,
        "UNIT_LEVEL": 85,
        "RELIC_TIER": 10,
        "UNIT_RARITY": 7,
        "MOD_TIER": 5,
        "MOD_LEVEL": 15,
        "MOD_RARITY": 6,
    }

    LEAGUES: dict[str, int] = {
        "kyber": 100,
        "aurodium": 80,
        "chromium": 60,
        "bronzium": 40,
        "carbonite": 20,
    }

    DIVISIONS: dict[str, int] = {"1": 25, "2": 20, "3": 15, "4": 10, "5": 5}

    RELIC_TIERS: dict[str, str] = {
        "0": "LOCKED",
        "1": "UNLOCKED",
        "2": "1",
        "3": "2",
        "4": "3",
        "5": "4",
        "6": "5",
        "7": "6",
        "8": "7",
        "9": "8",
        "10": "9",
        "11": "10",
    }

    # Segment convenience values (kept for backward compat with examples)
    Segment1 = 2097151
    Segment2 = 68717379584
    Segment3 = 206158430208
    Segment4 = 281200098803712

    # Proxied stat data from _stat_data (backward compat)
    STAT_ENUMS = STAT_ENUMS
    UNIT_STAT_ENUMS_MAP = UNIT_STAT_ENUMS_MAP
    STATS = STATS
    MOD_SET_IDS = MOD_SET_IDS
    MOD_SLOTS = MOD_SLOTS
    UNIT_RARITY = UNIT_RARITY
    UNIT_RARITY_NAMES = UNIT_RARITY_NAMES
    LANGUAGES = LANGUAGES
    OMICRON_MODE = OMICRON_MODE

    @classmethod
    def get(cls, item: str) -> str | None:
        """Resolve a string name to a game data collection integer value.

        Accepts Constants attribute names (e.g. ``"UnitDefinitions"``),
        DataItems member names (e.g. ``"UNITS"``), or special names like
        ``"ALL"``.

        Returns:
            The integer value as a string, or ``None`` if not found.
        """
        # 1. Try own attributes first (Segment1, LEAGUES, etc.)
        val = getattr(cls, item, None)
        if val is not None and isinstance(val, (int, float)):
            return str(val)

        # 2. Try legacy name map → DataItems
        mapped_name = _LEGACY_NAME_MAP.get(item)
        if mapped_name:
            try:
                return str(DataItems[mapped_name].value)
            except KeyError:
                pass

        # 3. Try DataItems member name directly
        try:
            return str(DataItems[item].value)
        except KeyError:
            pass

        return None

    @classmethod
    def get_names(cls) -> list[str]:
        """Return a list of resolvable names (Constants attrs + DataItems members)."""
        own_names = [
            x
            for x in list(cls.__dict__.keys())
            if not x.startswith("_") and not isinstance(cls.__dict__[x], classmethod)
        ]
        return own_names + list(_LEGACY_NAME_MAP.keys()) + list(DataItems.members())
