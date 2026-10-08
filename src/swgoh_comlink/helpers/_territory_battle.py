# coding=utf-8
"""Territory Battle definition helper functions: star thresholds, mission gates, mission scores and platoons."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._constants import Constants
from ._localization import _localize
from ._stat_data import UNIT_RARITY
from ._utils import get_function_name

# The two zone arrays that hold missions, and the mission type each one means. A special-mission campaign
# mission can still sit in the strike array (the Geonosis maps put their point-paying ones there).
_MISSION_ZONES = (("strikeZoneDefinition", "combat"), ("covertZoneDefinition", "special"))
# TerritoryRewardType and CombatType values. A victoryPointRewards bracket that pays MYSTERY_BOX_CONFLICT (3)
# is not a star.
_GALACTIC_SCORE = 1
_VICTORY_POINT = 2
_SHIP = 2
# Over a third of the game's categories key their name as the literal 'PLACEHOLDER'; none is a real name.
_PLACEHOLDER = "PLACEHOLDER"
_SCORE_ROW = "GALACTIC_SCORE"
# The dump of the game data spells the flag with an underscore; Comlink sends it without.
_VERSION_3_KEYS = ("territoryBattleVersion3", "territoryBattleVersion_3")
# int32 max: the game's "no limit" for maxUnitCountPerPlayer and maxAttemptsAllowed.
_UNLIMITED = 2**31 - 1
_PHASE = re.compile(r"phase(\d+)", re.IGNORECASE)


def _enum_names(names: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    """Enum names as matched by :func:`_wire_int`: upper case without underscores, longest first."""
    return tuple(sorted(((name.replace("_", ""), number) for name, number in names.items()), key=lambda n: -len(n[0])))


# Enum names sent with enums=True. Servers spell them either bare (VICTORY_POINT, RELIC_TIER_05) or prefixed
# with their type and without inner underscores (TERRITORYREWARDTYPE_VICTORYPOINT, RELICTIER_RELICTIER05);
# both end in the same letters once underscores are removed, so names are matched by suffix.
_REWARD_TYPE_NAMES = _enum_names({"GALACTIC_SCORE": 1, "VICTORY_POINT": 2, "MYSTERY_BOX_CONFLICT": 3})
_COMBAT_TYPE_NAMES = _enum_names({"CHARACTER": 1, "SHIP": 2})
_RARITY_NAMES = _enum_names({name: rarity for rarity, name in UNIT_RARITY.items()})
_UNIT_TIER_NAMES = _enum_names({f"TIER_{tier:02d}": tier for tier in range(1, 21)})
_RELIC_TIER_NAMES = _enum_names(
    {
        "RELIC_LOCKED": 1,
        "RELIC_UNLOCKED": 2,
        **{f"RELIC_TIER_{tier:02d}": tier + Constants.RELIC_OFFSET for tier in range(1, 51)},
    }
)


class TBZoneStars(TypedDict):
    """A Territory Battle conflict zone (planet) and its stars, as returned by :func:`get_tb_star_thresholds`."""

    tb_id: str
    """The ``territoryBattleDefinition`` id, e.g. ``"t05D"``."""
    zone_id: str
    name: str
    """Localized zone name, falling back to its ``nameKey``."""
    phase: int | None
    """The phase number read from the zone id, or ``None`` when the id carries none."""
    is_bonus: bool
    force_alignment: int | str
    """The zone's raw ``forceAlignment`` (1 neutral, 2 light side, 3 dark side)."""
    stars: list[int]
    """The territory points at which each star is earned, ascending. Usually three, but fewer on zones whose
    early brackets pay a mystery box instead of a star."""


class TBCategory(TypedDict):
    """A unit category named by a mission gate, as returned in :class:`TBMissionRequirement`."""

    id: str
    name: str
    """Localized category name; the id when the category has no name of its own."""


class TBMandatoryUnit(TypedDict):
    """A unit a mission requires by name, as returned in :attr:`TBMissionRequirement.mandatory_units`."""

    base_id: str
    slot: int
    """The squad position the game places the unit in, starting at 0; -1 (on older maps) for no fixed slot."""


class TBMissionRequirement(TypedDict):
    """A Territory Battle mission's squad gate, as returned by :func:`get_tb_mission_requirements`."""

    tb_id: str
    zone_id: str
    conflict_zone_id: str
    """The conflict zone (planet) the mission belongs to."""
    phase: int | None
    mission_type: str
    """``"combat"`` for a ``strikeZoneDefinition`` zone, ``"special"`` for a ``covertZoneDefinition`` zone."""
    is_fleet: bool
    name: str
    """Localized zone name (e.g. ``"Combat Mission"``), falling back to its ``nameKey``."""
    campaign_mission_id: str
    resolved: bool
    """``False`` when the zone's campaign mission was not found in ``campaigns``. The gate fields below are
    then empty or zero."""
    requirement_text: str
    """The requirement as the game words it, without markup and with one line per clause, e.g.
    ``"5x Jedi (Relic 5+)\\nMace Windu\\nKit Fisto"``. The localization key when no dictionary is given."""
    allowed_categories: list[TBCategory]
    """Squad units must belong to these categories, combined as ``category_match_type`` says."""
    category_match_type: int | str
    """The gate's raw ``matchType`` (1 match all, 2 match any)."""
    commander_categories: list[TBCategory]
    """The leader must belong to one of these categories. Empty when any leader is allowed."""
    excluded_categories: list[TBCategory]
    mandatory_units: list[TBMandatoryUnit]
    """Units the squad must include, in slot order."""
    min_squad_size: int
    max_squad_size: int
    min_rarity: int
    min_gear: int
    min_level: int
    min_relic: int
    """The minimum relic level as shown in game. 0 when the mission has no relic floor."""
    hidden_reason: str | None
    """Why the game is not expected to show this combat mission, or ``None``. ``"duplicate"``: an earlier zone
    on the same planet already uses its campaign mission. ``"special"``: a special-mission campaign mission
    left in the strike array of a version 3 map, where special missions are covert zones."""


class TBMissionScore(TypedDict):
    """The territory points a Territory Battle mission pays, as returned by :func:`get_tb_mission_scores`."""

    tb_id: str
    zone_id: str
    conflict_zone_id: str
    phase: int | None
    mission_type: str
    """``"combat"`` or ``"special"``, as in :class:`TBMissionRequirement`."""
    reward_table_id: str
    wave_points: list[int]
    """Cumulative points by waves completed: ``wave_points[n]`` is what clearing ``n`` waves pays, so
    ``wave_points[0]`` is 0 and the last entry is a full clear."""
    max_points: int
    hidden_reason: str | None
    """As in :class:`TBMissionRequirement`."""


class TBPlatoon(TypedDict):
    """One platoon of a recon zone, as returned in :attr:`TBReconZone.platoons`."""

    platoon_id: str
    squad_ids: list[str]
    points: int
    """Territory points paid for filling the platoon."""


class TBReconZone(TypedDict):
    """A Territory Battle recon zone and its platoons, as returned by :func:`get_tb_platoon_definitions`."""

    tb_id: str
    zone_id: str
    conflict_zone_id: str
    phase: int | None
    name: str
    is_fleet: bool
    min_rarity: int
    """The rarity a unit must have to fill a platoon slot."""
    min_relic: int
    """The relic level, as shown in game, a unit must have to fill a slot. 0 when there is no relic floor."""
    max_units_per_player: int | None
    """How many units one player may place in the zone, or ``None`` for no limit."""
    platoons: list[TBPlatoon]
    total_points: int


def _wire_int(value: Any, names: tuple[tuple[str, int], ...] = ()) -> int:
    """An integer game data field as sent with or without enums.

    Numbers may arrive as ints or, for int64 fields, as strings; with ``enums=True`` an enum field arrives as
    its name, which is matched against ``names`` (from :func:`_enum_names`) by suffix, so both the bare and
    the type-prefixed spelling are read. Anything unrecognized is 0.
    """
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            spelled = value.upper().replace("_", "")
            return next((number for name, number in names if spelled.endswith(name)), 0)
    return 0


def _relic_level(wire: Any) -> int:
    """``RelicTier`` as the relic level shown in game, floored at 0 so ``RELIC_LOCKED`` (1) is no floor."""
    return max(_wire_int(wire, _RELIC_TIER_NAMES) - Constants.RELIC_OFFSET, 0)


def _phase(zone_id: str) -> int | None:
    match = _PHASE.search(zone_id)
    return int(match[1]) if match else None


def _check_collection(arg_name: str, collection: Any, func_name: str) -> None:
    """Raise unless ``collection`` is a game data collection: a list of dictionaries."""
    if not isinstance(collection, list):
        raise SwgohComlinkValueError(f"{func_name}: '{arg_name}' must be a list, not {type(collection)}")
    if not all(isinstance(item, dict) for item in collection):
        raise SwgohComlinkValueError(f"{func_name}: '{arg_name}' must be a list of dictionaries")


def _select_definitions(
    definitions: list[dict[str, Any]], localization: dict[str, str] | None, tb_id: str | None, func_name: str
) -> list[dict[str, Any]]:
    """Validate the shared arguments and return the definitions to read: all of them, or the one ``tb_id`` names."""
    _check_collection("territory_battle_definitions", definitions, func_name)
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(f"{func_name}: 'localization' must be a dictionary, not {type(localization)}")
    if tb_id is None:
        return definitions
    if not isinstance(tb_id, str):
        raise SwgohComlinkValueError(f"{func_name}: 'tb_id' must be a string, not {type(tb_id)}")
    selected = [d for d in definitions if str(d.get("id", "")).upper() == tb_id.upper()]
    if not selected:
        known = ", ".join(str(d.get("id")) for d in definitions)
        raise SwgohComlinkValueError(f"{func_name}: unknown Territory Battle {tb_id!r}. Known: {known}")
    return selected


def _mission_zones(definition: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every mission-bearing zone of one definition, in definition order, with its mission type."""
    for array, mission_type in _MISSION_ZONES:
        for zone in definition.get(array) or []:
            yield mission_type, zone


def _hidden_reasons(definition: dict[str, Any]) -> dict[str, str]:
    """Zone id -> reason, for the strike zones the definition's own wiring says the game does not show.

    Zones are walked in definition order, so of two zones on one planet that share a campaign mission the
    later one is the duplicate. Sharing a mission across planets is normal on the Hoth maps and is not
    flagged. A special-mission campaign mission in the strike array is only flagged on a version 3 map: the
    Geonosis maps put playable, point-paying special missions there by design.
    """
    version_3 = any(definition.get(key) for key in _VERSION_3_KEYS)
    claimed: set[tuple[str, str]] = set()
    reasons: dict[str, str] = {}
    for mission_type, zone in _mission_zones(definition):
        zone_definition = zone.get("zoneDefinition") or {}
        mission_id = (zone.get("campaignElementIdentifier") or {}).get("campaignMissionId") or ""
        key = (zone_definition.get("linkedConflictId") or "", mission_id)
        if mission_type == "combat":
            if key in claimed:
                reasons[zone_definition.get("zoneId", "")] = "duplicate"
            elif version_3 and "SPECIALMISSION" in mission_id.upper():
                reasons[zone_definition.get("zoneId", "")] = "special"
        claimed.add(key)
    return reasons


def _campaign_key(identifier: Mapping[str, Any]) -> tuple[Any, ...]:
    """A ``campaignElementIdentifier`` as a lookup key. Node ids repeat across difficulties, so it is part of it."""
    return (
        identifier.get("campaignId"),
        identifier.get("campaignMapId"),
        identifier.get("campaignNodeDifficulty"),
        identifier.get("campaignNodeId"),
        identifier.get("campaignMissionId"),
    )


def _campaign_missions(campaigns: list[dict[str, Any]], wanted: set[Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Every ``campaignNodeMission`` of the ``wanted`` campaigns, keyed like :func:`_campaign_key`."""
    return {
        (
            campaign.get("id"),
            campaign_map.get("id"),
            group.get("campaignNodeDifficulty"),
            node.get("id"),
            mission.get("id"),
        ): mission
        for campaign in campaigns
        if campaign.get("id") in wanted
        for campaign_map in campaign.get("campaignMap") or []
        for group in campaign_map.get("campaignNodeDifficultyGroup") or []
        for node in group.get("campaignNode") or []
        for mission in node.get("campaignNodeMission") or []
    }


def get_tb_star_thresholds(
    territory_battle_definitions: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    *,
    tb_id: str | None = None,
) -> list[TBZoneStars]:
    """List each Territory Battle conflict zone (planet) with the territory points that earn its stars.

    A star is a ``conflictZoneDefinition[].victoryPointRewards`` bracket whose reward type is ``VICTORY_POINT``
    (2). Not every bracket is one: two Rise of the Empire bonus zones pay a ``MYSTERY_BOX_CONFLICT`` (3) for
    their first two brackets, so they have a single star. Thresholds are sorted rather than taken in payload
    order, and ``galacticScoreRequirement`` (an int64, so usually sent as a string) is read as an integer.

    Args:
        territory_battle_definitions: The game data ``territoryBattleDefinition`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, zone names are returned as their localization keys.
        tb_id: Restrict to one Territory Battle by definition id (case-insensitive): ``"t01D"`` Hoth Rebel
            Assault, ``"t02D"`` Hoth Imperial Retaliation, ``"t03D"`` Geonosis Separatist Might, ``"t04D"``
            Geonosis Republic Offensive or ``"t05D"`` Rise of the Empire. [Default: all]

    Returns:
        A list of :class:`TBZoneStars` dictionaries, in definition order.

    Raises:
        SwgohComlinkValueError: If ``territory_battle_definitions`` is not a list of dictionaries,
            ``localization`` is not a dictionary, or ``tb_id`` does not match any definition.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.TERRITORY_BATTLE_DEFINITION)  # doctest: +SKIP
        >>> zones = get_tb_star_thresholds(game_data["territoryBattleDefinition"], tb_id="t05D")  # doctest: +SKIP
        >>> zones[0]["zone_id"], zones[0]["stars"]  # doctest: +SKIP
        ('tb3_mixed_phase01_conflict01', [116406250, 186250000, 248333333])
    """
    definitions = _select_definitions(territory_battle_definitions, localization, tb_id, get_function_name())
    result: list[TBZoneStars] = []
    for definition in definitions:
        for zone in definition.get("conflictZoneDefinition") or []:
            zone_definition = zone.get("zoneDefinition") or {}
            zone_id = zone_definition.get("zoneId", "")
            stars = sorted(
                _wire_int(bracket.get("galacticScoreRequirement"))
                for bracket in zone.get("victoryPointRewards") or []
                if _wire_int((bracket.get("reward") or {}).get("type"), _REWARD_TYPE_NAMES) == _VICTORY_POINT
            )
            result.append(
                {
                    "tb_id": definition.get("id", ""),
                    "zone_id": zone_id,
                    "name": _localize(
                        localization, zone_definition.get("nameKey"), zone_definition.get("nameKey") or zone_id
                    ),
                    "phase": _phase(zone_id),
                    "is_bonus": bool(zone.get("isBonus")),
                    "force_alignment": zone.get("forceAlignment", 0),
                    "stars": stars,
                }
            )
    return result


def get_tb_mission_requirements(
    territory_battle_definitions: list[dict[str, Any]],
    campaigns: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    *,
    tb_id: str | None = None,
) -> list[TBMissionRequirement]:
    """List the squad each Territory Battle combat and special mission accepts.

    The gate is not in the battle definition. Each strike and covert zone names its mission with a five-part
    ``campaignElementIdentifier`` (campaign, map, node difficulty, node, mission) that resolves through
    ``campaign`` -> ``campaignMap`` -> ``campaignNodeDifficultyGroup`` -> ``campaignNode`` ->
    ``campaignNodeMission``, and that mission's ``entryCategoryAllowed`` is the gate. The node difficulty is
    part of the key because node ids repeat across difficulties.

    ``minimumRelicTier`` is on the wire ``RelicTier`` scale and is returned as the relic level shown in game
    (wire value minus ``Constants.RELIC_OFFSET``, floored at 0, so fleet missions' ``RELIC_LOCKED`` is 0).
    Category names come from each category's ``descKey``; categories keyed ``PLACEHOLDER`` have no name and
    are returned with their id. The requirement text is the mission's ``descKey`` with its colour markup
    removed and its literal ``\\n`` separators turned into newlines.

    Args:
        territory_battle_definitions: The game data ``territoryBattleDefinition`` collection.
        campaigns: The game data ``campaign`` collection.
        categories: The game data ``category`` collection, used to name the gate's categories.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names and requirement text are returned as their localization keys.
        tb_id: Restrict to one Territory Battle by definition id (case-insensitive), as in
            :func:`get_tb_star_thresholds`. [Default: all]

    Returns:
        A list of :class:`TBMissionRequirement` dictionaries, in definition order with each definition's
        combat missions before its special missions.

    Raises:
        SwgohComlinkValueError: If a collection is not a list of dictionaries, ``localization`` is not a
            dictionary, or ``tb_id`` does not match any definition.

    Examples:
        >>> game_data = comlink.get_game_data(
        ...     items=DataItems.TERRITORY_BATTLE_DEFINITION | DataItems.CAMPAIGN | DataItems.CATEGORY
        ... )  # doctest: +SKIP
        >>> missions = get_tb_mission_requirements(
        ...     game_data["territoryBattleDefinition"], game_data["campaign"], game_data["category"],
        ...     get_localization_dictionary(comlink), tb_id="t05D",
        ... )  # doctest: +SKIP
        >>> missions[0]["requirement_text"], missions[0]["min_relic"]  # doctest: +SKIP
        ('5x Jedi (Relic 5+)', 5)
    """
    func_name = get_function_name()
    definitions = _select_definitions(territory_battle_definitions, localization, tb_id, func_name)
    _check_collection("campaigns", campaigns, func_name)
    _check_collection("categories", categories, func_name)

    missions = _campaign_missions(
        campaigns,
        {
            (zone.get("campaignElementIdentifier") or {}).get("campaignId")
            for definition in definitions
            for _, zone in _mission_zones(definition)
        },
    )
    category_keys = {category.get("id"): category.get("descKey") for category in categories}
    names: dict[str, str] = {}

    def named(category_ids: list[str] | None) -> list[TBCategory]:
        for category_id in category_ids or []:
            if category_id not in names:
                key = category_keys.get(category_id)
                names[category_id] = (
                    category_id if not key or key == _PLACEHOLDER else _localize(localization, key, key)
                )
        return [{"id": category_id, "name": names[category_id]} for category_id in category_ids or []]

    result: list[TBMissionRequirement] = []
    for definition in definitions:
        hidden = _hidden_reasons(definition)
        for mission_type, zone in _mission_zones(definition):
            zone_definition = zone.get("zoneDefinition") or {}
            zone_id = zone_definition.get("zoneId", "")
            identifier = zone.get("campaignElementIdentifier") or {}
            mission = missions.get(_campaign_key(identifier))
            gate = (mission or {}).get("entryCategoryAllowed") or {}
            desc_key = (mission or {}).get("descKey") or ""
            result.append(
                {
                    "tb_id": definition.get("id", ""),
                    "zone_id": zone_id,
                    "conflict_zone_id": zone_definition.get("linkedConflictId", ""),
                    "phase": _phase(zone_id),
                    "mission_type": mission_type,
                    "is_fleet": _wire_int(zone.get("combatType"), _COMBAT_TYPE_NAMES) == _SHIP,
                    "name": _localize(
                        localization, zone_definition.get("nameKey"), zone_definition.get("nameKey") or zone_id
                    ),
                    "campaign_mission_id": identifier.get("campaignMissionId", ""),
                    "resolved": mission is not None,
                    "requirement_text": _localize(localization, desc_key, desc_key),
                    "allowed_categories": named(gate.get("categoryId")),
                    "category_match_type": gate.get("matchType", 0),
                    "commander_categories": named(gate.get("commanderCategoryId")),
                    "excluded_categories": named(gate.get("excludeCategoryId")),
                    "mandatory_units": [
                        {"base_id": unit.get("id", ""), "slot": _wire_int(unit.get("slot"))}
                        for unit in sorted(
                            gate.get("mandatoryRosterUnit") or [], key=lambda u: _wire_int(u.get("slot"))
                        )
                    ],
                    "min_squad_size": _wire_int(gate.get("minimumRequiredUnitQuantity")),
                    "max_squad_size": _wire_int(gate.get("maximumAllowedUnitQuantity")),
                    "min_rarity": _wire_int(gate.get("minimumUnitRarity"), _RARITY_NAMES),
                    "min_gear": _wire_int(gate.get("minimumUnitTier"), _UNIT_TIER_NAMES),
                    "min_level": _wire_int(gate.get("minimumUnitLevel")),
                    "min_relic": _relic_level(gate.get("minimumRelicTier")),
                    "hidden_reason": hidden.get(zone_id),
                }
            )
    return result


def get_tb_mission_scores(
    territory_battle_definitions: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    *,
    tb_id: str | None = None,
) -> list[TBMissionScore]:
    """List the territory points each Territory Battle mission pays, by waves completed.

    A mission zone names its points table in ``encounterRewardTableId``. That ``table`` entry's rows are keyed
    by waves completed, as strings and in no guaranteed order, and each holds a cumulative
    ``GALACTIC_SCORE:<points>`` value, so a two-wave mission reads ``{0: 0, 1: 100000, 2: 200000}``. Rows are
    placed by their key; a wave missing from the table repeats the previous wave's total, and rows paying
    anything other than ``GALACTIC_SCORE`` are ignored.

    Covert zones (special missions) have no points table: they pay items, not territory points, and are not
    listed. Special missions the Geonosis maps place in the strike array do have tables and are listed.

    Args:
        territory_battle_definitions: The game data ``territoryBattleDefinition`` collection.
        tables: The game data ``table`` collection.
        tb_id: Restrict to one Territory Battle by definition id (case-insensitive), as in
            :func:`get_tb_star_thresholds`. [Default: all]

    Returns:
        A list of :class:`TBMissionScore` dictionaries, in definition order.

    Raises:
        SwgohComlinkValueError: If a collection is not a list of dictionaries, ``tb_id`` does not match any
            definition, or a mission names a table that is not in ``tables``.

    Examples:
        >>> game_data = comlink.get_game_data(
        ...     items=DataItems.TERRITORY_BATTLE_DEFINITION | DataItems.TABLE
        ... )  # doctest: +SKIP
        >>> scores = get_tb_mission_scores(
        ...     game_data["territoryBattleDefinition"], game_data["table"], tb_id="t05D"
        ... )  # doctest: +SKIP
        >>> scores[0]["wave_points"]  # doctest: +SKIP
        [0, 100000, 200000]
    """
    func_name = get_function_name()
    definitions = _select_definitions(territory_battle_definitions, None, tb_id, func_name)
    _check_collection("tables", tables, func_name)

    wanted = {
        zone.get("encounterRewardTableId")
        for definition in definitions
        for _, zone in _mission_zones(definition)
        if zone.get("encounterRewardTableId")
    }
    # 'table' holds every kind of game table; only parse the ones a mission names.
    curves: dict[str, list[int]] = {}
    for table in tables:
        if table.get("id") not in wanted:
            continue
        by_waves: dict[int, int] = {}
        for row in table.get("row") or []:
            kind, _, value = str(row.get("value") or "").partition(":")
            if kind == _SCORE_ROW:
                by_waves[_wire_int(row.get("key"))] = _wire_int(value)
        curve: list[int] = []
        for waves in range(max(by_waves, default=-1) + 1):
            curve.append(by_waves.get(waves, curve[-1] if curve else 0))
        curves[table["id"]] = curve
    if missing := sorted(wanted - curves.keys()):
        raise SwgohComlinkValueError(
            f"{func_name}: reward tables {missing} are not in 'tables'. Request them with DataItems.TABLE."
        )

    result: list[TBMissionScore] = []
    for definition in definitions:
        hidden = _hidden_reasons(definition)
        for mission_type, zone in _mission_zones(definition):
            if not (table_id := zone.get("encounterRewardTableId")):
                continue
            zone_definition = zone.get("zoneDefinition") or {}
            zone_id = zone_definition.get("zoneId", "")
            curve = curves[table_id]
            result.append(
                {
                    "tb_id": definition.get("id", ""),
                    "zone_id": zone_id,
                    "conflict_zone_id": zone_definition.get("linkedConflictId", ""),
                    "phase": _phase(zone_id),
                    "mission_type": mission_type,
                    "reward_table_id": table_id,
                    "wave_points": list(curve),
                    "max_points": curve[-1] if curve else 0,
                    "hidden_reason": hidden.get(zone_id),
                }
            )
    return result


def _platoon(platoon: dict[str, Any]) -> TBPlatoon:
    reward = platoon.get("reward") or {}
    return {
        "platoon_id": platoon.get("id", ""),
        "squad_ids": [squad.get("id", "") for squad in platoon.get("squad") or []],
        "points": _wire_int(reward.get("value"))
        if _wire_int(reward.get("type"), _REWARD_TYPE_NAMES) == _GALACTIC_SCORE
        else 0,
    }


def get_tb_platoon_definitions(
    territory_battle_definitions: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    *,
    tb_id: str | None = None,
) -> list[TBReconZone]:
    """List each Territory Battle recon zone with its platoons, unit floor and the points each platoon pays.

    Read from ``reconZoneDefinition``. Platoon rewards are listed per platoon because they can differ within
    a zone; only ``GALACTIC_SCORE`` rewards count as points. The zone's ``unitRelicTier`` is on the wire
    ``RelicTier`` scale and is returned as the relic level shown in game. The game data does not list which
    units each platoon asks for; those appear only on a live battle's map.

    Args:
        territory_battle_definitions: The game data ``territoryBattleDefinition`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, zone names are returned as their localization keys.
        tb_id: Restrict to one Territory Battle by definition id (case-insensitive), as in
            :func:`get_tb_star_thresholds`. [Default: all]

    Returns:
        A list of :class:`TBReconZone` dictionaries, in definition order.

    Raises:
        SwgohComlinkValueError: If ``territory_battle_definitions`` is not a list of dictionaries,
            ``localization`` is not a dictionary, or ``tb_id`` does not match any definition.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.TERRITORY_BATTLE_DEFINITION)  # doctest: +SKIP
        >>> zones = get_tb_platoon_definitions(game_data["territoryBattleDefinition"], tb_id="t05D")  # doctest: +SKIP
        >>> zones[0]["min_relic"], zones[0]["total_points"]  # doctest: +SKIP
        (5, 60000000)
    """
    definitions = _select_definitions(territory_battle_definitions, localization, tb_id, get_function_name())
    result: list[TBReconZone] = []
    for definition in definitions:
        for zone in definition.get("reconZoneDefinition") or []:
            zone_definition = zone.get("zoneDefinition") or {}
            zone_id = zone_definition.get("zoneId", "")
            platoons = [_platoon(platoon) for platoon in zone.get("platoonDefinition") or []]
            max_units = _wire_int(zone_definition.get("maxUnitCountPerPlayer"))
            result.append(
                {
                    "tb_id": definition.get("id", ""),
                    "zone_id": zone_id,
                    "conflict_zone_id": zone_definition.get("linkedConflictId", ""),
                    "phase": _phase(zone_id),
                    "name": _localize(
                        localization, zone_definition.get("nameKey"), zone_definition.get("nameKey") or zone_id
                    ),
                    "is_fleet": _wire_int(zone.get("combatType"), _COMBAT_TYPE_NAMES) == _SHIP,
                    "min_rarity": _wire_int(zone.get("unitRarity"), _RARITY_NAMES),
                    "min_relic": _relic_level(zone.get("unitRelicTier")),
                    "max_units_per_player": None if max_units in (0, _UNLIMITED) else max_units,
                    "platoons": platoons,
                    "total_points": sum(platoon["points"] for platoon in platoons),
                }
            )
    return result
