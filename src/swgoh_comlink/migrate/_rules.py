# coding=utf-8
"""Migration rule definitions for detecting deprecated patterns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationRule:
    """A single migration check rule."""

    id: str
    pattern: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    suggestion: str


RULES: list[MigrationRule] = [
    # ── Import-related rules ──────────────────────────────────────────
    MigrationRule(
        id="DEP001",
        pattern=r"from\s+swgoh_comlink\.helpers\s+import\s+Constants",
        severity="INFO",
        message="Direct import of Constants from helpers.",
        suggestion=(
            "Constants is still available from swgoh_comlink.helpers. "
            "For game data collection values, prefer DataItems instead."
        ),
    ),
    MigrationRule(
        id="DEP002",
        pattern=r"^\s*import\s+requests\b",
        severity="WARNING",
        message="Import of 'requests' library detected.",
        suggestion=(
            "swgoh_comlink v2.x uses httpx instead of requests. Replace 'import requests' with 'import httpx'."
        ),
    ),
    MigrationRule(
        id="DEP003",
        pattern=r"requests\.RequestException",
        severity="WARNING",
        message="Use of requests.RequestException detected.",
        suggestion=("Replace with httpx.RequestError or catch SwgohComlinkException."),
    ),
    MigrationRule(
        id="DEP004",
        pattern=r"get_logger\s*\(.+log_level",
        severity="WARNING",
        message="get_logger() called with log_level parameter.",
        suggestion=(
            "get_logger() no longer accepts log_level. Configure logging via "
            "the standard logging module: logging.basicConfig(level=logging.DEBUG)"
        ),
    ),
    MigrationRule(
        id="DEP005",
        pattern=r"from\s+swgoh_comlink\.globals\s+import\s+get_logger",
        severity="INFO",
        message="Import of get_logger from globals.",
        suggestion=(
            "get_logger() is a thin wrapper around logging.getLogger(). Consider using logging.getLogger() directly."
        ),
    ),
    # ── Constants collection attribute usage ───────────────────────────
    MigrationRule(
        id="DEP010",
        pattern=(
            r"Constants\."
            r"(?:CategoryDefinitions|UnlockAnnouncements|SkillDefinitions|"
            r"EquipmentDefinitions|BattleEffectDefinitions|AllTables|"
            r"EnvironmentDefinitions|EventSampling|BattleTargetingSets|"
            r"Requirements|PowerUpBundles|GuildBannerDefinition|"
            r"BattleTargetingRules|PersistentVFX|CraftingMaterialDefinitions|"
            r"PlayerTitleDefinitions|PlayerPortraitDefinitions|"
            r"TimeZoneChangeConfig|EnvironmentCollections|"
            r"PersistentEffectPriorities|SocialStatus|AbilityDefinitions|"
            r"StatProgression|Challenge|WarDefinitions|StatMod|"
            r"RecipeDefinitions|ModRecommendations|ScavengerConversionSets|"
            r"Guild|Mystery|CooldownDefinitions|DailyActionCapDefinitions|"
            r"EnergyRewards|UnitGuideDefinitions|GalacticBundleDefinitions|"
            r"RelicTierDefinitions|UnitDefinitions|CampaignDefinitions|"
            r"Conquest|AbilityDecisionTrees|RecommendedSquads|"
            r"UnitGuideLayouts|DailyLoginRewardDefinitions|"
            r"CalendarCategories|TerritoryTournamentDailyRewards|"
            r"DatacronDefinitions|DisplayableEnemyDefinitions|"
            r"EpisodeDefinition|LinkingReward|Help|UBSUpdate)\b"
        ),
        severity="WARNING",
        message="Access to deprecated Constants collection attribute.",
        suggestion=(
            "Collection bit values have moved to the DataItems enum. "
            "Example: Constants.UnitDefinitions -> DataItems.UNITS. "
            "Constants.get() still resolves old names for backward compatibility."
        ),
    ),
    MigrationRule(
        id="DEP011",
        pattern=r"Constants\.Segment[1-4]\b",
        severity="INFO",
        message="Use of Constants.SegmentN detected.",
        suggestion=(
            "Consider using DataItems.SEGMENT1, DataItems.SEGMENT2, etc. Constants.SegmentN still works via the facade."
        ),
    ),
    MigrationRule(
        id="DEP012",
        pattern=r"Constants\.get\(",
        severity="INFO",
        message="Use of Constants.get() string-based resolver.",
        suggestion=(
            "Constants.get() still works and accepts both old Constants names "
            "and DataItems names. Prefer using DataItems directly: "
            "DataItems.UNITS or DataItems['UNITS']."
        ),
    ),
    MigrationRule(
        id="DEP013",
        pattern=r"Constants\.get_names\(",
        severity="INFO",
        message="Use of Constants.get_names() detected.",
        suggestion="Consider using DataItems.members() for collection names.",
    ),
    # ── Stat data access ──────────────────────────────────────────────
    MigrationRule(
        id="DEP020",
        pattern=r"Constants\.STAT_ENUMS\b",
        severity="INFO",
        message="Direct access to Constants.STAT_ENUMS.",
        suggestion=(
            "Still available through the Constants facade. The canonical source "
            "is now swgoh_comlink.helpers._stat_data.STAT_ENUMS."
        ),
    ),
    MigrationRule(
        id="DEP021",
        pattern=r"Constants\.STATS\b",
        severity="INFO",
        message="Direct access to Constants.STATS.",
        suggestion=(
            "Still available through the Constants facade. The canonical source "
            "is now swgoh_comlink.helpers._stat_data.STATS."
        ),
    ),
    MigrationRule(
        id="DEP022",
        pattern=r"Constants\.UNIT_STAT_ENUMS_MAP\b",
        severity="INFO",
        message="Direct access to Constants.UNIT_STAT_ENUMS_MAP.",
        suggestion=(
            "Still available through the Constants facade. The canonical source "
            "is now swgoh_comlink.helpers._stat_data.UNIT_STAT_ENUMS_MAP."
        ),
    ),
    # ── Client lifecycle ──────────────────────────────────────────────
    MigrationRule(
        id="DEP030",
        pattern=r"(?<!with\s)SwgohComlink\(\)",
        severity="INFO",
        message="SwgohComlink instantiation without context manager.",
        suggestion=("Consider using 'with SwgohComlink() as comlink:' for automatic connection cleanup."),
    ),
]
