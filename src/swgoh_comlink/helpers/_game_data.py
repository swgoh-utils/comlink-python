# coding=utf-8
"""Game data query helper functions (raids, datacrons, localization, units)."""

from __future__ import annotations

import base64
import io
import logging
import time
import zipfile
from collections.abc import Coroutine
from math import floor
from typing import TYPE_CHECKING, Any, overload

from ..exceptions import SwgohComlinkValueError
from ._utils import _client_kind, get_function_name

if TYPE_CHECKING:
    from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

logger = logging.getLogger(__name__)

# Unit rarity as sent with enums=False and enums=True
_SEVEN_STAR = (7, "SEVEN_STAR")


def get_raid_leaderboard_ids(campaign_data: list[dict[str, Any]]) -> list[str]:
    """
    Extracts and returns the raid leaderboard IDs from the provided campaign data.

    This function processes the `campaign_data` to find and extract the IDs of
    raids associated with the guild campaigns. The IDs are formatted as a string
    specifying the type and structure of the raid. The function specifically works
    with the "GUILD" campaign type and retrieves IDs from the "NORMAL_DIFF"
    difficulty group.

    Args:
        campaign_data (list): A list of campaign data structures, where each
            structure represents campaign information. The input data is
            expected to have nested dictionaries and lists with specific keys
            such as 'id', 'campaignMap', 'campaignNodeDifficultyGroup', and
            'campaignNode'.

    Returns:
        list: A list containing formatted raid leaderboard IDs extracted from the
        guild campaign data. Each ID is constructed as a string containing the
        relevant identifiers for the campaign and its raids.

    Raises:
        KeyError: If any of the required keys are missing in the input data.
        TypeError: If `campaign_data` is not structured as expected, such as if
            it is not a list or contains improperly formatted elements.
    """
    raid_ids: list[str] = []
    guild_campaigns = next((item for item in campaign_data if item.get("id") == "GUILD"), None)
    if guild_campaigns is None:
        return raid_ids
    for raid in guild_campaigns["campaignMap"][0]["campaignNodeDifficultyGroup"][0]["campaignNode"]:
        for mission in raid["campaignNodeMission"]:
            elements = [
                guild_campaigns["id"],
                guild_campaigns["campaignMap"][0]["id"],
                "NORMAL_DIFF",
                raid["id"],
                mission["id"],
            ]
            raid_ids.append(":".join(elements))
    return raid_ids


def create_localized_unit_name_dictionary(locale: str | list[Any]) -> dict[str, str]:
    """Create localized translation mapping for unit names

    Take a localization element from the SwgohComlink.get_localization() result dictionary and
    extract the unit name entries (``UNIT_*`` keys containing ``_NAME``).

    The keys are localization keys, not base ids: look a unit up with its ``nameKey`` from the game
    data ``units`` collection. Many name keys cannot be derived from the base id (``CT7567`` is
    ``UNIT_REX_NAME``, ``VEERS`` is ``UNIT_VEERS_GENERAL_NAME``, reworked units use ``_NAME_V2``).

    Args:
        locale: The string element or List[bytes] from the SwgohComlink.get_localization()
                                        result key value

    Returns:
        A dictionary of unit name localization key (e.g. ``"UNIT_REX_NAME"``) to the unit's name.

    Examples:
        >>> names = create_localized_unit_name_dictionary(locale)  # doctest: +SKIP
        >>> names[unit["nameKey"]]  # doctest: +SKIP
        'CT-7567 "Rex"'
    """
    if not isinstance(locale, list) and not isinstance(locale, str):
        raise SwgohComlinkValueError("'locale' must be a list of strings or string containing newlines.")

    unit_name_map = {}
    lines = []
    if isinstance(locale, str):
        lines = locale.split("\n")
    elif isinstance(locale, list):
        lines = locale
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.rstrip("\n")
        if line.startswith("#") or "|" not in line:
            continue
        if line.startswith("UNIT_"):
            name_key, desc = line.split("|", 1)
            if "_NAME" in name_key:
                unit_name_map[name_key] = desc
    return unit_name_map


def _parse_localization_bundle(bundle: dict[str, Any], language: str) -> dict[str, str]:
    """Decode a ``get_localization()`` response and parse one language file into a dictionary.

    The Comlink ``localization`` endpoint returns a base64-encoded zip archive under the
    ``localizationBundle`` key. Each archive entry is a newline-delimited text file whose lines
    are ``KEY|value`` pairs (``#`` prefixed lines are comments).

    Args:
        bundle: The dictionary returned by ``SwgohComlink.get_localization()``.
        language: Locale identifier (e.g. ``"eng_us"``) used to select the ``Loc_<LANG>.txt`` entry.

    Returns:
        A dictionary mapping localization keys to their localized string values.

    Raises:
        SwgohComlinkValueError: If the response is missing the ``localizationBundle`` key or the
            archive does not contain a file for the requested language.

    """
    if "localizationBundle" not in bundle:
        err_msg = f"{get_function_name()}: response is missing the 'localizationBundle' key."
        raise SwgohComlinkValueError(err_msg)

    decoded = base64.b64decode(bundle["localizationBundle"])
    target = f"Loc_{language.upper()}.txt"
    result: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(decoded)) as zip_obj:
        names = zip_obj.namelist()
        if target not in names:
            err_msg = f"{get_function_name()}: '{target}' not found in localization bundle (available: {names})."
            raise SwgohComlinkValueError(err_msg)
        with zip_obj.open(target) as raw, io.TextIOWrapper(raw, encoding="utf-8") as stream:
            for line in stream:
                if line.startswith("#"):
                    continue
                key, sep, value = line.rstrip("\r\n").partition("|")
                if sep:
                    result[key] = value
    return result


@overload
def get_localization_dictionary(comlink: SwgohComlink, language: str = "eng_us") -> dict[str, str]: ...
@overload
def get_localization_dictionary(
    comlink: SwgohComlinkAsync, language: str = "eng_us"
) -> Coroutine[Any, Any, dict[str, str]]: ...
def get_localization_dictionary(
    comlink: Any, language: str = "eng_us"
) -> dict[str, str] | Coroutine[Any, Any, dict[str, str]]:
    """Fetch a localization bundle and parse it into a key/value dictionary.

    Args:
        comlink: Instance of SwgohComlink. An instance of SwgohComlinkAsync is also accepted, in which case
            the result of :func:`async_get_localization_dictionary` is returned for the caller to await.
        language: Locale identifier to retrieve. [Default: ``"eng_us"``]

    Returns:
        A dictionary mapping localization keys to their localized string values, or an awaitable of it
        when ``comlink`` is a SwgohComlinkAsync.

    Raises:
        SwgohComlinkValueError: If ``comlink`` is not a SwgohComlink or SwgohComlinkAsync instance, or
            the response cannot be parsed for the requested language.

    """
    kind = _client_kind(comlink)
    if kind == "async":
        return async_get_localization_dictionary(comlink, language=language)
    if kind != "sync":
        err_msg = f"{get_function_name()}: The 'comlink' argument is required and must be an instance of SwgohComlink."
        raise SwgohComlinkValueError(err_msg)

    if not isinstance(language, str) or not language:
        err_msg = f"{get_function_name()}: 'language' must be a non-empty string."
        raise SwgohComlinkValueError(err_msg)

    bundle = comlink.get_localization(locale=language)
    return _parse_localization_bundle(bundle, language)


async def async_get_localization_dictionary(comlink: Any, language: str = "eng_us") -> dict[str, str]:
    """Fetch a localization bundle and parse it into a key/value dictionary (async version).

    Args:
        comlink: Instance of SwgohComlinkAsync.
        language: Locale identifier to retrieve. [Default: ``"eng_us"``]

    Returns:
        A dictionary mapping localization keys to their localized string values.

    Raises:
        SwgohComlinkValueError: If ``comlink`` is not a SwgohComlinkAsync instance, or the response
            cannot be parsed for the requested language.

    """
    if _client_kind(comlink) != "async":
        err_msg = (
            f"{get_function_name()}: The 'comlink' argument is required and must be an instance of SwgohComlinkAsync."
        )
        raise SwgohComlinkValueError(err_msg)

    if not isinstance(language, str) or not language:
        err_msg = f"{get_function_name()}: 'language' must be a non-empty string."
        raise SwgohComlinkValueError(err_msg)

    bundle = await comlink.get_localization(locale=language)
    return _parse_localization_bundle(bundle, language)


def get_playable_units(units_collection: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the playable units from the game data 'units' collection, one seven-star row per unit.

    A unit is playable when it is obtainable and its ``obtainableTime`` is ``"0"``. Event and Galactic
    Legend template variants carry a far-future ``obtainableTime`` instead. A missing ``obtainableTime``
    (older game data) counts as ``"0"``, and ``rarity`` may be ``7`` or ``"SEVEN_STAR"`` (``enums=True``).
    """
    if not isinstance(units_collection, list):
        raise SwgohComlinkValueError(f"'units_collection' must be a list, not {type(units_collection)}")

    return [
        unit
        for unit in units_collection
        if unit.get("rarity") in _SEVEN_STAR
        and unit.get("obtainable") is True
        and str(unit.get("obtainableTime") or "0") == "0"
    ]


def get_current_datacron_sets(datacron_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get the currently active datacron sets

    Args:
        datacron_list (list): List of 'datacronSet' from game data

    Returns:
        Filtered list of only active datacron sets

    Raises:
        SwgohComlinkValueError: If datacron list is not a list

    """
    if not isinstance(datacron_list, list):
        raise SwgohComlinkValueError(
            f"{get_function_name()}, 'datacron_list' must be a list, not {type(datacron_list)}"
        )
    current_datacron_sets = []
    for datacron in datacron_list:
        if int(datacron["expirationTimeMs"]) > floor(time.time() * 1000):
            current_datacron_sets.append(datacron)
    return current_datacron_sets


def get_datacron_dismantle_value(
    datacron: dict[str, Any], datacron_set_list: list[dict[str, Any]], recipe_list: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Retrieves datacron dismantle materials based on the input datacron, datacron sets, and recipes.

    Arguments:
        datacron (dict): The datacron object from a player object.
        datacron_set_list (list): The game data 'datacronSet' collection.
        recipe_list (list): The game data 'recipe' collection.

    Returns:
        dict: A dictionary mapping ingredient IDs to their required dismantle material
              details, which include the quantity and type.
    """
    dismantle_materials: dict[str, Any] = {}
    set_id = datacron.get("setId")
    focused: bool = datacron.get("focused", False)
    affix_tier = len(datacron.get("affix", []))

    def find_object_by_id(obj_list: list[dict[str, Any]], obj_id: Any) -> dict[str, Any] | None:
        return next((obj for obj in obj_list if obj.get("id") == obj_id), None)

    datacron_set = find_object_by_id(datacron_set_list, set_id)
    if not datacron_set:
        return dismantle_materials

    tier_element = "focusedTier" if focused else "tier"
    dust_recipe_id = next(
        (tier.get("dustGrantRecipeId") for tier in datacron_set.get(tier_element, []) if tier.get("id") == affix_tier),
        None,
    )
    if not dust_recipe_id:
        return dismantle_materials

    dust_recipe = find_object_by_id(recipe_list, dust_recipe_id)
    if not dust_recipe:
        return dismantle_materials

    for ingredient in dust_recipe.get("ingredients", []):
        dismantle_materials[ingredient.get("id")] = {
            "quantity": ingredient.get("maxQuantity"),
            "type": ingredient.get("type"),
        }
    dismantle_materials["focused"] = focused
    return dismantle_materials


def get_datacron_dismantle_total(
    datacrons: list[dict[str, Any]], datacron_set_list: list[dict[str, Any]], recipe_list: list[dict[str, Any]]
) -> dict[str, Any]:
    """Calculate aggregated dismantle materials across all datacrons.

    Calls :func:`get_datacron_dismantle_value` for each datacron and sums
    the quantities per ingredient ID.

    Arguments:
        datacrons (list): List of datacron objects from a player object.
        datacron_set_list (list): The game data ``datacronSet`` collection.
        recipe_list (list): The game data ``recipe`` collection.

    Returns:
        dict: A dictionary mapping ingredient IDs to total quantity and type,
              e.g. ``{"mat_id": {"quantity": 150, "type": 3}}``.
    """
    totals: dict[str, Any] = {}
    for datacron in datacrons:
        materials = get_datacron_dismantle_value(datacron, datacron_set_list, recipe_list)
        for ingredient_id, info in materials.items():
            if ingredient_id == "focused":
                continue
            if ingredient_id in totals:
                totals[ingredient_id]["quantity"] += info.get("quantity", 0)
            else:
                totals[ingredient_id] = {
                    "quantity": info.get("quantity", 0),
                    "type": info.get("type"),
                }
    return totals
