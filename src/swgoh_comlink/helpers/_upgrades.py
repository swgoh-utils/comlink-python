# coding=utf-8
"""Unit upgrade cost helper functions: gear tiers, gear crafting, relic promotions and ability upgrades."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._localization import _localize
from ._utils import get_function_name

# recipe.ingredients[].type (ItemType), as integers (enums=False) or names (enums=True)
_CURRENCY = {3, "CURRENCY"}
_MATERIAL = {7, "MATERIAL"}
_EQUIPMENT = {11, "EQUIPMENT"}
# Currency ingredient id -> UpgradeCost field. Ship abilities charge Ship Building Materials (SHIP_GRIND)
# where everything else charges credits (GRIND).
_CURRENCY_FIELDS: dict[str, Literal["credits", "ship_credits"]] = {"GRIND": "credits", "SHIP_GRIND": "ship_credits"}
# Every character's thirteenth unitTier slots this placeholder piece six times: a G13 unit slots nothing.
_PLACEHOLDER_PIECE = "9999"
_RELIC_TABLE = "relic_promotion_table"
_RELIC_ROW_KEY = re.compile(r"^TIER_(?P<tier>\d+)$")
# units.unitTier[].tier and equipment.tier (UnitTier), as integers (enums=False) or names such as "TIER_01"
# (enums=True); TIER_UNDEFINED is 0.
_UNIT_TIER_NAME = re.compile(r"^TIER_(?P<tier>\d+)$")
_UNIT_TIER_UNDEFINED = "TIER_UNDEFINED"
# skill.tier[0] upgrades the ability from level 1 to level 2.
_FIRST_TIER_LEVEL = 2


class UpgradeCost(TypedDict):
    """What an upgrade charges. Every helper in this module reports its costs in this shape."""

    credits: int
    """Credits (currency ``GRIND``)."""
    ship_credits: int
    """Ship Building Materials (currency ``SHIP_GRIND``), which ship abilities charge instead of credits."""
    materials: dict[str, int]
    """``material`` id -> quantity, e.g. ability materials and relic salvage."""
    equipment: dict[str, int]
    """``equipment`` piece id -> quantity."""


class GearTier(TypedDict):
    """One gear tier of a character, as returned by :func:`get_unit_gear_tiers`."""

    tier: int
    """The gear tier the pieces are slotted at. Slotting all six promotes the unit to ``tier + 1``."""
    equipment: list[str]
    """Piece ids in slot order. Empty at tier 13, which slots nothing."""
    cost: UpgradeCost
    """The pieces as ``equipment`` counts. Slotting and promoting are free, so no credits."""


class GearCraftNode(TypedDict):
    """One piece in a gear craft tree, as returned by :func:`get_gear_craft_tree`."""

    id: str
    name: str
    """Localized piece name, falling back to its ``nameKey``."""
    tier: int
    """The piece's gear tier (``equipment.tier``)."""
    mark: str
    """The piece's mark, e.g. ``"Mk XII"``."""
    quantity: int
    """How many of this piece the tree needs here: 1 at the root, and for an ingredient the recipe quantity
    times its parent's ``quantity``."""
    recipe_credits: int
    """Credits this piece's own recipe charges to craft one of it; 0 for a piece that is not crafted."""
    cost: UpgradeCost
    """Everything needed to make ``quantity`` of this piece from uncraftable pieces: their counts under
    ``equipment`` and the crafting credits of every step."""
    ingredients: list[GearCraftNode]
    """The pieces the recipe consumes, in recipe order. Empty for a piece that is farmed, not crafted."""


class RelicPromotionCost(TypedDict):
    """One relic promotion, as returned by :func:`get_relic_promotion_costs`."""

    relic_tier: int
    """The relic tier the promotion reaches, on the player scale (``1`` is R0 -> R1)."""
    recipe_id: str
    cost: UpgradeCost


class AbilityUpgradeTier(TypedDict):
    """One upgrade of an ability, as listed in :attr:`AbilityUpgradeCosts.tiers`."""

    level: int
    """The skill level this upgrade reaches. Level 1 is the base ability, so upgrades start at 2."""
    recipe_id: str
    is_zeta: bool
    is_omicron: bool
    cost: UpgradeCost


class AbilityUpgradeCosts(TypedDict):
    """A unit ability's upgrade costs, as returned by :func:`get_ability_upgrade_costs`."""

    base_id: str
    """The unit the ability belongs to."""
    crew_base_id: str | None
    """For a ship's crew ability, the crew member it comes from; otherwise ``None``."""
    skill_id: str
    tiers: list[AbilityUpgradeTier]


def _empty_cost() -> UpgradeCost:
    return {"credits": 0, "ship_credits": 0, "materials": {}, "equipment": {}}


def _add_cost(total: UpgradeCost, cost: Mapping[str, Any], times: int = 1) -> None:
    """Add ``times`` x ``cost`` into ``total``; fields missing from ``cost`` count as zero."""
    total["credits"] += int(cost.get("credits") or 0) * times
    total["ship_credits"] += int(cost.get("ship_credits") or 0) * times
    for field in ("materials", "equipment"):
        bucket = total[field]
        for item_id, quantity in (cost.get(field) or {}).items():
            bucket[item_id] = bucket.get(item_id, 0) + int(quantity) * times


def _recipe_cost(recipe: dict[str, Any], func_name: str) -> UpgradeCost:
    """Read a recipe's ingredients into an :class:`UpgradeCost`, rejecting anything that is not exact."""
    cost = _empty_cost()
    for ingredient in recipe.get("ingredients") or []:
        item_id, kind = str(ingredient.get("id", "")), ingredient.get("type")
        low, high = ingredient.get("minQuantity"), ingredient.get("maxQuantity")
        # A range has no single cost; reporting either end would be a guess.
        if low != high:
            raise SwgohComlinkValueError(
                f"{func_name}: recipe {recipe.get('id')!r} charges {low} to {high} of {item_id!r}, not one quantity"
            )
        quantity = int(low or 0)
        if kind in _CURRENCY:
            if item_id not in _CURRENCY_FIELDS:
                raise SwgohComlinkValueError(
                    f"{func_name}: recipe {recipe.get('id')!r} charges unsupported currency {item_id!r}"
                )
            cost[_CURRENCY_FIELDS[item_id]] += quantity
        elif kind in _MATERIAL or kind in _EQUIPMENT:
            bucket = cost["materials"] if kind in _MATERIAL else cost["equipment"]
            bucket[item_id] = bucket.get(item_id, 0) + quantity
        else:
            raise SwgohComlinkValueError(
                f"{func_name}: recipe {recipe.get('id')!r} has ingredient {item_id!r} of unsupported type {kind!r}"
            )
    return cost


def _tier_number(value: Any, owner: str, func_name: str) -> int:
    """Read a ``UnitTier`` value as an integer; a missing tier counts as 0."""
    if value is None or value == _UNIT_TIER_UNDEFINED:
        return 0
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        if (match := _UNIT_TIER_NAME.match(value)) is not None:
            return int(match["tier"])
    raise SwgohComlinkValueError(f"{func_name}: {owner} has unrecognized tier {value!r}")


def _get_recipe(recipe_map: dict[str, dict[str, Any]], recipe_id: str, owner: str, func_name: str) -> dict[str, Any]:
    if (recipe := recipe_map.get(recipe_id)) is None:
        raise SwgohComlinkValueError(f"{func_name}: recipe {recipe_id!r} of {owner} is not in 'recipes'")
    return recipe


def _check_lists(func_name: str, **collections: Any) -> None:
    for arg_name, arg in collections.items():
        if not isinstance(arg, list):
            raise SwgohComlinkValueError(f"{func_name}: '{arg_name}' must be a list, not {type(arg)}")


def _find_unit(units: list[dict[str, Any]], base_id: Any, func_name: str) -> dict[str, Any]:
    """The first ``units`` row for ``base_id`` (case-insensitive); every rarity row carries the same tiers."""
    if not isinstance(base_id, str):
        raise SwgohComlinkValueError(f"{func_name}: 'base_id' must be a string, not {type(base_id)}")
    unit = next((u for u in units if str(u.get("baseId", "")).upper() == base_id.upper()), None)
    if unit is None:
        raise SwgohComlinkValueError(f"{func_name}: unit {base_id!r} is not in 'units'")
    return unit


def _build_craft_tree(
    piece_map: dict[str, dict[str, Any]],
    recipe_map: dict[str, dict[str, Any]],
    piece_id: str,
    quantity: int,
    localization: dict[str, str] | None,
    func_name: str,
    path: tuple[str, ...],
) -> GearCraftNode:
    """Build the :class:`GearCraftNode` for ``quantity`` of ``piece_id``; ``path`` holds its ancestors."""
    if (piece := piece_map.get(piece_id)) is None:
        raise SwgohComlinkValueError(f"{func_name}: equipment {piece_id!r} is not in 'equipment'")
    if piece_id in path:
        raise SwgohComlinkValueError(f"{func_name}: equipment {piece_id!r} is crafted from itself")
    node: GearCraftNode = {
        "id": piece_id,
        "name": _localize(localization, piece.get("nameKey"), piece.get("nameKey") or piece_id),
        "tier": _tier_number(piece.get("tier"), f"equipment {piece_id!r}", func_name),
        "mark": str(piece.get("mark") or ""),
        "quantity": quantity,
        "recipe_credits": 0,
        "cost": _empty_cost(),
        "ingredients": [],
    }
    if not (recipe_id := piece.get("recipeId")):
        node["cost"]["equipment"][piece_id] = quantity
        return node
    recipe_cost = _recipe_cost(_get_recipe(recipe_map, recipe_id, f"equipment {piece_id!r}", func_name), func_name)
    # A gear recipe consumes pieces and credits only.
    if recipe_cost["ship_credits"] or recipe_cost["materials"]:
        raise SwgohComlinkValueError(f"{func_name}: recipe {recipe_id!r} of a gear piece charges more than credits")
    node["recipe_credits"] = recipe_cost["credits"]
    node["cost"]["credits"] = recipe_cost["credits"] * quantity
    for ingredient_id, ingredient_quantity in recipe_cost["equipment"].items():
        child = _build_craft_tree(
            piece_map,
            recipe_map,
            ingredient_id,
            ingredient_quantity * quantity,
            localization,
            func_name,
            (*path, piece_id),
        )
        _add_cost(node["cost"], child["cost"])
        node["ingredients"].append(child)
    return node


def get_unit_gear_tiers(units: list[dict[str, Any]], base_id: str) -> list[GearTier]:
    """List the gear a character slots at each gear tier.

    Read from ``units.unitTier[].equipmentSet``. A unit at tier ``n`` slots that tier's six pieces to
    promote to ``n + 1``, so taking a unit from G1 to G13 needs the pieces of tiers 1 to 12. Tier 13's
    ``equipmentSet`` holds six ``"9999"`` placeholders, not real gear: it is returned with no pieces.

    The pieces are listed as they are slotted. Pass the tiers' ``cost`` to :func:`sum_upgrade_costs` with
    the ``equipment`` and ``recipe`` collections to get the salvage and credits needed to craft them.

    Args:
        units: The game data ``units`` collection. The first row for ``base_id`` is used, so the raw
            per-rarity collection works.
        base_id: The character's base id (case-insensitive), e.g. ``"COMMANDERLUKESKYWALKER"``.

    Returns:
        A list of :class:`GearTier` dictionaries, tier 1 first. Ships have no gear, so a ship returns an
        empty list.

    Raises:
        SwgohComlinkValueError: If ``units`` is not a list, ``base_id`` is not a string or is not in
            ``units``, or a ``unitTier`` has a tier that is not a number or ``UnitTier`` name.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.UNITS)  # doctest: +SKIP
        >>> tiers = get_unit_gear_tiers(game_data["units"], "COMMANDERLUKESKYWALKER")  # doctest: +SKIP
        >>> tiers[0]["equipment"]  # doctest: +SKIP
        ['001', '006', '005', '010', '003', '006']
    """
    func_name = get_function_name()
    _check_lists(func_name, units=units)
    unit = _find_unit(units, base_id, func_name)

    owner = f"unit {unit.get('baseId')!r}"
    numbered = [(_tier_number(t.get("tier"), owner, func_name), t) for t in unit.get("unitTier") or []]
    result: list[GearTier] = []
    for tier, unit_tier in sorted(numbered, key=lambda pair: pair[0]):
        pieces = [str(piece) for piece in unit_tier.get("equipmentSet") or [] if str(piece) != _PLACEHOLDER_PIECE]
        cost = _empty_cost()
        for piece in pieces:
            cost["equipment"][piece] = cost["equipment"].get(piece, 0) + 1
        result.append({"tier": tier, "equipment": pieces, "cost": cost})
    return result


def get_gear_craft_tree(
    equipment: list[dict[str, Any]],
    recipes: list[dict[str, Any]],
    equipment_id: str,
    localization: dict[str, str] | None = None,
) -> GearCraftNode:
    """Expand a gear piece into its full craft tree, down to the pieces that are farmed rather than crafted.

    Joins ``equipment.recipeId`` -> ``recipe.ingredients``. A gear recipe consumes other pieces
    (ingredient type 11, ``EQUIPMENT``) and credits; a piece with no ``recipeId`` is a leaf.

    Args:
        equipment: The game data ``equipment`` collection.
        recipes: The game data ``recipe`` collection.
        equipment_id: The piece to expand, e.g. ``"164"``.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names are returned as their localization keys.

    Returns:
        The root :class:`GearCraftNode` (``quantity`` 1). Its ``cost`` is the total salvage and credits
        needed to craft the piece.

    Raises:
        SwgohComlinkValueError: If a collection is not a list, ``localization`` is not a dictionary, a piece
            or recipe in the tree is missing or a piece's tier is not a number or ``UnitTier`` name, or a
            recipe has an ingredient that is not exact or is of a kind a gear recipe should not hold.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.EQUIPMENT | DataItems.RECIPE)  # doctest: +SKIP
        >>> loc = get_localization_dictionary(comlink)  # doctest: +SKIP
        >>> tree = get_gear_craft_tree(game_data["equipment"], game_data["recipe"], "164", loc)  # doctest: +SKIP
        >>> tree["cost"]["credits"]  # doctest: +SKIP
        44650
    """
    func_name = get_function_name()
    _check_lists(func_name, equipment=equipment, recipes=recipes)
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(f"{func_name}: 'localization' must be a dictionary, not {type(localization)}")
    if not isinstance(equipment_id, str):
        raise SwgohComlinkValueError(f"{func_name}: 'equipment_id' must be a string, not {type(equipment_id)}")

    piece_map = {str(piece.get("id")): piece for piece in equipment}
    recipe_map = {str(recipe.get("id")): recipe for recipe in recipes}
    return _build_craft_tree(piece_map, recipe_map, equipment_id, 1, localization, func_name, ())


def get_relic_promotion_costs(tables: list[dict[str, Any]], recipes: list[dict[str, Any]]) -> list[RelicPromotionCost]:
    """List the cost of each relic promotion.

    The promotion recipes are named by the ``table`` collection's ``relic_promotion_table`` rows,
    ``TIER_01`` (R0 -> R1) to ``TIER_10`` (R9 -> R10), on the player relic scale rather than the wire
    ``relicTier`` one (see :func:`convert_relic_tier`). Each recipe charges credits and relic materials.

    The ``table`` collection has no ``DataItems`` member of its own: ``DataItems.TABLE`` (an alias of
    ``DataItems.XP_TABLE``) returns both ``table`` and ``xpTable``.

    Args:
        tables: The game data ``table`` collection.
        recipes: The game data ``recipe`` collection.

    Returns:
        A list of :class:`RelicPromotionCost` dictionaries, R1 first. Sum a slice of them with
        :func:`sum_upgrade_costs`, e.g. ``costs[:9]`` for R0 to R9.

    Raises:
        SwgohComlinkValueError: If a collection is not a list, ``relic_promotion_table`` is missing or its
            rows are not ``TIER_01`` to ``TIER_<n>``, or a recipe is missing or not exact.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.TABLE | DataItems.RECIPE)  # doctest: +SKIP
        >>> relics = get_relic_promotion_costs(game_data["table"], game_data["recipe"])  # doctest: +SKIP
        >>> relics[0]["cost"]  # doctest: +SKIP
        {'credits': 10000, 'ship_credits': 0, 'materials': {'SCV_001': 40}, 'equipment': {}}
    """
    func_name = get_function_name()
    _check_lists(func_name, tables=tables, recipes=recipes)
    table = next((t for t in tables if t.get("id") == _RELIC_TABLE), None)
    if table is None:
        raise SwgohComlinkValueError(f"{func_name}: '{_RELIC_TABLE}' is not in 'tables'")

    by_tier: dict[int, str] = {}
    for row in table.get("row") or []:
        if (match := _RELIC_ROW_KEY.match(str(row.get("key", "")))) is None or not row.get("value"):
            raise SwgohComlinkValueError(f"{func_name}: unexpected '{_RELIC_TABLE}' row {row!r}")
        by_tier[int(match["tier"])] = str(row["value"])
    if sorted(by_tier) != list(range(1, len(by_tier) + 1)):
        raise SwgohComlinkValueError(f"{func_name}: '{_RELIC_TABLE}' tiers {sorted(by_tier)} are not 1 to n")

    recipe_map = {str(recipe.get("id")): recipe for recipe in recipes}
    return [
        {
            "relic_tier": tier,
            "recipe_id": recipe_id,
            "cost": _recipe_cost(_get_recipe(recipe_map, recipe_id, f"relic tier {tier}", func_name), func_name),
        }
        for tier, recipe_id in sorted(by_tier.items())
    ]


def get_ability_upgrade_costs(
    units: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    recipes: list[dict[str, Any]],
    base_id: str,
) -> list[AbilityUpgradeCosts]:
    """List the upgrade cost of every level of a unit's abilities, with zeta and omicron levels flagged.

    Joins ``units.skillReference`` -> ``skill.tier[].recipeId`` -> ``recipe``. A ship's crew abilities
    (``units.crew[].skillReference``) are included, with ``crew_base_id`` set. Ship abilities charge
    Ship Building Materials, reported as ``ship_credits``, rather than credits.

    Args:
        units: The game data ``units`` collection. The first row for ``base_id`` is used, so the raw
            per-rarity collection works.
        skills: The game data ``skill`` collection.
        recipes: The game data ``recipe`` collection.
        base_id: The unit's base id (case-insensitive).

    Returns:
        A list of :class:`AbilityUpgradeCosts` dictionaries in ``skillReference`` order, followed by any
        crew abilities. Each lists its upgrades from level 2 up.

    Raises:
        SwgohComlinkValueError: If a collection is not a list, ``base_id`` is not a string or is not in
            ``units``, a skill or recipe the unit names is missing, or a recipe is not exact.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.UNITS | DataItems.SKILL | DataItems.RECIPE)  # doctest: +SKIP
        >>> abilities = get_ability_upgrade_costs(
        ...     game_data["units"], game_data["skill"], game_data["recipe"], "COMMANDERLUKESKYWALKER"
        ... )  # doctest: +SKIP
        >>> total = sum_upgrade_costs(tier["cost"] for ability in abilities for tier in ability["tiers"])  # doctest: +SKIP
    """
    func_name = get_function_name()
    _check_lists(func_name, units=units, skills=skills, recipes=recipes)
    unit = _find_unit(units, base_id, func_name)
    skill_map = {str(skill.get("id")): skill for skill in skills}
    recipe_map = {str(recipe.get("id")): recipe for recipe in recipes}

    references = [(ref, None) for ref in unit.get("skillReference") or []] + [
        (ref, crew.get("unitId")) for crew in unit.get("crew") or [] for ref in crew.get("skillReference") or []
    ]
    result: list[AbilityUpgradeCosts] = []
    for reference, crew_base_id in references:
        skill_id = str(reference.get("skillId", ""))
        if (skill := skill_map.get(skill_id)) is None:
            raise SwgohComlinkValueError(
                f"{func_name}: skill {skill_id!r} of {unit.get('baseId')!r} is not in 'skills'"
            )
        tiers: list[AbilityUpgradeTier] = []
        for index, skill_tier in enumerate(skill.get("tier") or []):
            recipe_id = str(skill_tier.get("recipeId", ""))
            recipe = _get_recipe(recipe_map, recipe_id, f"skill {skill_id!r}", func_name)
            tiers.append(
                {
                    "level": index + _FIRST_TIER_LEVEL,
                    "recipe_id": recipe_id,
                    "is_zeta": bool(skill_tier.get("isZetaTier")),
                    "is_omicron": bool(skill_tier.get("isOmicronTier")),
                    "cost": _recipe_cost(recipe, func_name),
                }
            )
        result.append(
            {"base_id": unit.get("baseId", ""), "crew_base_id": crew_base_id, "skill_id": skill_id, "tiers": tiers}
        )
    return result


def sum_upgrade_costs(
    costs: Iterable[UpgradeCost],
    equipment: list[dict[str, Any]] | None = None,
    recipes: list[dict[str, Any]] | None = None,
) -> UpgradeCost:
    """Add up upgrade costs, optionally breaking gear down into the salvage it is crafted from.

    Takes the ``cost`` of any mix of :class:`GearTier`, :class:`RelicPromotionCost` and
    :class:`AbilityUpgradeTier` entries. Fields missing from a cost count as zero.

    With both ``equipment`` and ``recipes``, every craftable piece in the total is replaced by the pieces
    its recipe consumes, all the way down, and the crafting credits are added; ``equipment`` in the result
    then holds only pieces that are farmed rather than crafted.

    Args:
        costs: The costs to add, e.g. ``tier["cost"] for tier in gear_tiers[:12]``.
        equipment: Optional game data ``equipment`` collection, to craft gear down to salvage.
        recipes: Optional game data ``recipe`` collection, to craft gear down to salvage.

    Returns:
        The total as an :class:`UpgradeCost`, with ``materials`` and ``equipment`` sorted by id.

    Raises:
        SwgohComlinkValueError: If only one of ``equipment`` and ``recipes`` is given, either is not a list,
            a cost is not a mapping, or crafting meets a missing piece or recipe or an ingredient that is not
            exact.

    Examples:
        >>> tiers = get_unit_gear_tiers(game_data["units"], "COMMANDERLUKESKYWALKER")  # doctest: +SKIP
        >>> g1_to_g13 = sum_upgrade_costs(
        ...     (tier["cost"] for tier in tiers), game_data["equipment"], game_data["recipe"]
        ... )  # doctest: +SKIP
        >>> relics = get_relic_promotion_costs(game_data["table"], game_data["recipe"])  # doctest: +SKIP
        >>> r0_to_r9 = sum_upgrade_costs(relic["cost"] for relic in relics[:9])  # doctest: +SKIP
    """
    func_name = get_function_name()
    if (equipment is None) != (recipes is None):
        raise SwgohComlinkValueError(f"{func_name}: pass both 'equipment' and 'recipes' to craft gear, or neither")

    total = _empty_cost()
    for cost in costs:
        if not isinstance(cost, Mapping):
            raise SwgohComlinkValueError(f"{func_name}: each cost must be a mapping, not {type(cost)}")
        _add_cost(total, cost)

    if equipment is not None and recipes is not None:
        _check_lists(func_name, equipment=equipment, recipes=recipes)
        piece_map = {str(piece.get("id")): piece for piece in equipment}
        recipe_map = {str(recipe.get("id")): recipe for recipe in recipes}
        pieces, total["equipment"] = total["equipment"], {}
        for piece_id, quantity in pieces.items():
            if quantity:
                tree = _build_craft_tree(piece_map, recipe_map, piece_id, 1, None, func_name, ())
                _add_cost(total, tree["cost"], quantity)

    total["materials"] = dict(sorted(total["materials"].items()))
    total["equipment"] = dict(sorted(total["equipment"].items()))
    return total
