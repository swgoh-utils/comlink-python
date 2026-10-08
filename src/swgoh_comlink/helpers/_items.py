# coding=utf-8
"""Item, reward and mod catalog helper functions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._localization import _localize
from ._stat_data import CURRENCY_NAMES, CURRENCY_TYPES, ITEM_TYPES, MOD_SET_IDS, MOD_SLOTS, UNIT_RARITY_NAMES

_ITEM_TYPE_NUMBERS = {name: number for number, name in ITEM_TYPES.items()}
_UNIT = _ITEM_TYPE_NUMBERS["UNIT"]
_CURRENCY = _ITEM_TYPE_NUMBERS["CURRENCY"]
_MATERIAL = _ITEM_TYPE_NUMBERS["MATERIAL"]
_EQUIPMENT = _ITEM_TYPE_NUMBERS["EQUIPMENT"]
_MYSTERY_BOX = _ITEM_TYPE_NUMBERS["MYSTERY_BOX"]
_MYSTERY_STAT_MOD = _ITEM_TYPE_NUMBERS["MYSTERY_STAT_MOD"]
_PLAYER_TITLE = _ITEM_TYPE_NUMBERS["PLAYER_TITLE"]
_PLAYER_PORTRAIT = _ITEM_TYPE_NUMBERS["PLAYER_PORTRAIT"]
_ARTIFACT = _ITEM_TYPE_NUMBERS["ARTIFACT"]
_LIGHTSPEED_TOKEN = _ITEM_TYPE_NUMBERS["LIGHTSPEED_TOKEN"]

# ItemType -> (game data collection, field holding the item's localization key). A mystery box is
# named by its titleKey; everything else by nameKey.
_NAMED_COLLECTIONS = {
    _MATERIAL: ("material", "nameKey"),
    _EQUIPMENT: ("equipment", "nameKey"),
    _MYSTERY_BOX: ("mysteryBox", "titleKey"),
    _PLAYER_TITLE: ("playerTitle", "nameKey"),
    _PLAYER_PORTRAIT: ("playerPortrait", "nameKey"),
    _ARTIFACT: ("artifactDefinition", "nameKey"),
    _LIGHTSPEED_TOKEN: ("lightspeedToken", "nameKey"),
}
# Every collection ItemNames reads, so a wrongly typed one is reported up front.
_ITEM_COLLECTIONS = (*(c for c, _ in _NAMED_COLLECTIONS.values()), "units", "mysteryStatMod", "statModSet")

# A unit shard is a material whose id is the unit's baseId behind this prefix.
_SHARD_PREFIX = "unitshard_"

# Enum member names that game data fetched with enums=True carries in place of the numbers. StatModSlot
# numbers start at 2: STATMOD_SLOT_01 is the Square (see MOD_SLOTS).
_MOD_SLOT_ENUMS = {f"STATMOD_SLOT_{n:02d}": n + 1 for n in range(1, 7)}
_MOD_TIER_ENUMS = {f"STATMOD_TIER_{n:02d}": n for n in range(1, 6)}
# Rarity also has NO_STAR (8), which UNIT_RARITY_NAMES leaves out.
_RARITY_ENUMS = {**{name: int(number) for name, number in UNIT_RARITY_NAMES.items()}, "NO_STAR": 8}
# A mod's tier as the letter the game shows on it.
_MOD_TIER_LETTERS = {1: "E", 2: "D", 3: "C", 4: "B", 5: "A"}


class ModSet(TypedDict):
    """A mod set as returned in :attr:`ModCatalog.sets`."""

    set_id: str
    name: str
    """Localized set name. Without a localization string it is the English name from ``MOD_SET_IDS``."""
    set_count: int
    """How many mods of the set complete its bonus: 4 for Speed, Offense and Critical Damage, 2 otherwise."""


class ModDefinition(TypedDict):
    """A mod definition as returned in :attr:`ModCatalog.definitions`."""

    definition_id: str
    set_id: str
    set_name: str
    slot: int
    """``StatModSlot`` number, 2 (Square) to 7 (Cross); see ``MOD_SLOTS``."""
    slot_name: str
    rarity: int
    """The mod's dots (pips), 1 to 6."""


class ModCatalog(TypedDict):
    """The mod catalog returned by :func:`get_mod_catalog`."""

    sets: dict[str, ModSet]
    """Set id to :class:`ModSet`."""
    definitions: dict[str, ModDefinition]
    """Mod ``definitionId`` to :class:`ModDefinition`."""


class NamedReward(TypedDict):
    """A single reward item as returned by :func:`get_named_rewards`."""

    item_type: int | str | None
    """The ``ItemType`` number (see ``ITEM_TYPES``). An enum name the table does not list is kept as given;
    an item with no ``type`` has ``None``."""
    id: str
    name: str
    """Display name; the item ``id`` (or the ``ItemType`` name for an item with no id, or ``""`` when it has
    neither) when it cannot be resolved."""
    min_quantity: int
    max_quantity: int
    base_id: str | None
    """For a unit, its ``baseId``; for a unit shard, the id after ``unitshard_``, which is the unit's
    ``baseId`` except for event shard variants such as ``VADER_JKL_EVENT``. Otherwise ``None``."""
    requirement_id: str | None
    """For an item of a ``conditionalRewardsPreview`` bucket, the requirement that must hold for it to be
    paid; otherwise ``None``."""


def _as_int(value: Any, enum_names: Mapping[str, int] | None = None) -> int | None:
    """Read an int field that may hold a number, a numeric string or (with ``enums=True``) an enum name."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if value.lstrip("-").isdigit():
            return int(value)
        if enum_names is not None:
            return enum_names.get(value)
    return None


def _item_type_number(item_type: Any) -> int | None:
    """An ``ItemType`` given as a number, a numeric string or an enum name, as its number."""
    return _as_int(item_type, _ITEM_TYPE_NUMBERS)


# The validators take the caller's name as a literal rather than from get_function_name(): that walks the
# stack through inspect.stack(), which would cost more than the work itself on every valid call.
def _check_list(arg_name: str, arg: Any, function_name: str) -> None:
    if not isinstance(arg, list):
        raise SwgohComlinkValueError(f"{function_name}: '{arg_name}' must be a list, not {type(arg)}")


def _check_localization(localization: Any, function_name: str) -> None:
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(f"{function_name}: 'localization' must be a dictionary, not {type(localization)}")


def _names_by_id(records: list[dict[str, Any]], localization: dict[str, str] | None) -> dict[str, str]:
    """Join each record's ``id`` to its own ``nameKey``, localized when possible."""
    return {
        record["id"]: _localize(localization, name_key, name_key)
        for record in records
        if isinstance(record, dict) and record.get("id") and (name_key := record.get("nameKey"))
    }


def get_data_disc_names(
    artifact_definitions: list[dict[str, Any]], localization: dict[str, str] | None = None
) -> dict[str, str]:
    """Map every Conquest data disc's definition id to its name.

    A Conquest payload names a data disc only by its ``definitionId``, and the localization key cannot be
    derived from it: keys carry typos the ids do not (``artifact_guard_and_pentrate_3_cost_rare`` is keyed
    ``ARTIFACT_GURAD_AND_PENTRATE_3_COST_RARE_NAME``, and ``certain_defeat`` keys spell ``COSE`` for
    ``COST``), some drop the cost tier (``artifact_evasive_technique_2_cost_common`` is
    ``ARTIFACT_EVASIVE_TECHNIQUE_COMMON_NAME``), some are ``_NAME_V2`` variants, and a rarity may reuse
    another rarity's key. So each ``artifactDefinition`` record is joined through its own ``nameKey``.

    Args:
        artifact_definitions: The game data ``artifactDefinition`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, the ``nameKey`` is returned in place of the name, which makes this the id to
            localization key join.

    Returns:
        A dictionary of definition id (as the game data spells it; some ids are mixed case) to name. A
        name the localization does not hold is returned as its ``nameKey``.

    Raises:
        SwgohComlinkValueError: If ``artifact_definitions`` is not a list or ``localization`` is not a
            dictionary.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.CONQUEST)  # doctest: +SKIP
        >>> discs = get_data_disc_names(game_data["artifactDefinition"], get_localization_dictionary(comlink))  # doctest: +SKIP
    """
    _check_list("artifact_definitions", artifact_definitions, "get_data_disc_names()")
    _check_localization(localization, "get_data_disc_names()")
    return _names_by_id(artifact_definitions, localization)


def get_player_title_names(
    player_titles: list[dict[str, Any]], localization: dict[str, str] | None = None
) -> dict[str, str]:
    """Map every player title id to its name.

    A player profile names its titles only by id, and a title's name is usually unrelated to it: the id
    records what earned the title (``PLAYERTITLE_GRANDARENA_INTRO`` is "Fight Me"), so spelling out the
    id is wrong for most titles. Nor can the localization key be derived from the id:
    ``PLAYERTITLE_GLLEIA_EVENT`` is keyed ``PLAYERTITLE_LEIA_EVENT_NAME``, some titles use ``_NAME_V2``
    keys, and the guild rank titles are keyed ``GuildMemberLevel_*``. So each ``playerTitle`` record is
    joined through its own ``nameKey``.

    Args:
        player_titles: The game data ``playerTitle`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, the ``nameKey`` is returned in place of the name, which makes this the id to
            localization key join.

    Returns:
        A dictionary of title id to name. A name the localization does not hold is returned as its
        ``nameKey``.

    Raises:
        SwgohComlinkValueError: If ``player_titles`` is not a list or ``localization`` is not a dictionary.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.PLAYER_TITLE)  # doctest: +SKIP
        >>> titles = get_player_title_names(game_data["playerTitle"], get_localization_dictionary(comlink))  # doctest: +SKIP
        >>> titles["PLAYERTITLE_GRANDARENA_INTRO"]  # doctest: +SKIP
        'Fight Me'
    """
    _check_list("player_titles", player_titles, "get_player_title_names()")
    _check_localization(localization, "get_player_title_names()")
    return _names_by_id(player_titles, localization)


def _mod_set_names(stat_mod_sets: list[dict[str, Any]], localization: dict[str, str] | None) -> dict[str, str]:
    """Set id to set name. A ``statModSet`` record keeps its localization key in ``name``, not ``nameKey``."""
    names: dict[str, str] = {}
    for mod_set in stat_mod_sets:
        if not isinstance(mod_set, dict):
            continue
        set_id = str(mod_set.get("id", ""))
        fallback = MOD_SET_IDS.get(set_id) or mod_set.get("name") or set_id
        names[set_id] = _localize(localization, mod_set.get("name"), fallback)
    return names


def get_mod_catalog(
    stat_mods: list[dict[str, Any]],
    stat_mod_sets: list[dict[str, Any]],
    localization: dict[str, str] | None = None,
) -> ModCatalog:
    """Map mod definition ids to their set, slot and rarity, and mod sets to their name and set count.

    An equipped mod names only its ``definitionId``; its set, slot and rarity are not on the mod itself
    and are recovered by joining the id to ``statMod``. How many mods complete a set comes from
    ``statModSet``. Numbers are read whether the game data was fetched with or without ``enums=True``.

    Args:
        stat_mods: The game data ``statMod`` collection.
        stat_mod_sets: The game data ``statModSet`` collection.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, or when it has no name for a set, set names are the English names from
            ``MOD_SET_IDS``.

    Returns:
        A :class:`ModCatalog` dictionary. Slot names come from ``MOD_SLOTS``.

    Raises:
        SwgohComlinkValueError: If a collection is not a list or ``localization`` is not a dictionary.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.STAT_MOD)  # doctest: +SKIP
        >>> catalog = get_mod_catalog(game_data["statMod"], game_data["statModSet"])  # doctest: +SKIP
        >>> mod = catalog["definitions"]["451"]  # doctest: +SKIP
        >>> mod["set_name"], mod["slot_name"], mod["rarity"]  # doctest: +SKIP
        ('Speed', 'Square', 5)
    """
    _check_list("stat_mods", stat_mods, "get_mod_catalog()")
    _check_list("stat_mod_sets", stat_mod_sets, "get_mod_catalog()")
    _check_localization(localization, "get_mod_catalog()")

    set_names = _mod_set_names(stat_mod_sets, localization)
    sets: dict[str, ModSet] = {
        str(mod_set["id"]): {
            "set_id": str(mod_set["id"]),
            "name": set_names[str(mod_set["id"])],
            "set_count": _as_int(mod_set.get("setCount")) or 0,
        }
        for mod_set in stat_mod_sets
        if isinstance(mod_set, dict) and mod_set.get("id") is not None
    }

    definitions: dict[str, ModDefinition] = {}
    for mod in stat_mods:
        if not isinstance(mod, dict) or not mod.get("id"):
            continue
        set_id = str(mod.get("setId", ""))
        slot = _as_int(mod.get("slot"), _MOD_SLOT_ENUMS) or 0
        definitions[mod["id"]] = {
            "definition_id": mod["id"],
            "set_id": set_id,
            "set_name": set_names.get(set_id) or MOD_SET_IDS.get(set_id, set_id),
            "slot": slot,
            "slot_name": MOD_SLOTS.get(str(slot), ""),
            "rarity": _as_int(mod.get("rarity"), _RARITY_ENUMS) or 0,
        }
    return {"sets": sets, "definitions": definitions}


def _range(low: int | None, high: int | None, labels: Mapping[int, str] | None = None) -> str:
    """``5`` for a fixed value, ``1-2`` for a range, each value written through ``labels`` when given."""

    def label(value: int | None) -> str:
        if value is None:
            return "?"
        return labels.get(value, "?") if labels is not None else str(value)

    return label(low) if low == high else f"{label(low)}-{label(high)}"


class ItemNames:
    """Resolve ``(ItemType, id)`` pairs from rewards, previews and inventories to display names.

    Item ids are only unique within an ``ItemType``, so a name is looked up by both. Build one per game
    data version and localization, then call :meth:`get` for as many items as needed; each collection is
    indexed once and each name is localized only the first time it is asked for.

    Which collection names each ``ItemType`` (pass the ones you need; the rest resolve to nothing):

    - ``UNIT``: ``units``. The id may carry a rarity, as in ``ANAKINKNIGHT:ONE_STAR``.
    - ``CURRENCY``: no collection. The id is the ``CurrencyType`` name (or number), named from
      ``CURRENCY_NAMES``, which is English whatever the localization.
    - ``MATERIAL``: ``material``. A unit shard (``unitshard_<baseId>``) is named by the unit: through the
      material's own ``nameKey``, which also covers event shard ids no unit has (such as
      ``unitshard_VADER_JKL_EVENT``), then through ``units``.
    - ``EQUIPMENT``: ``equipment``.
    - ``MYSTERY_BOX``: ``mysteryBox``, by its ``titleKey``.
    - ``MYSTERY_STAT_MOD``: ``mysteryStatMod`` and ``statModSet``. A mystery mod has no name of its own,
      so it is described by what it rolls: ``"5-dot Speed Arrow mod (A)"``, with ranges such as
      ``"1-2-dot"`` and ``"E-D"``, and ``any-slot`` for a mod that may land in any slot. The wording is
      English; the set name is localized.
    - ``PLAYER_TITLE``, ``PLAYER_PORTRAIT``, ``ARTIFACT`` (a Conquest data disc) and
      ``LIGHTSPEED_TOKEN``: ``playerTitle``, ``playerPortrait``, ``artifactDefinition`` and
      ``lightspeedToken``, always through the record's own ``nameKey``, since these names cannot be
      derived from their ids.

    ``XP`` and the other ``ItemType`` values name no particular item and resolve to nothing.

    Args:
        game_data: Game data collections keyed by collection name, such as the dictionary
            ``get_game_data`` returns.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names are returned as their localization keys.

    Raises:
        SwgohComlinkValueError: If ``game_data`` is not a dictionary, one of the collections it reads is
            not a list, or ``localization`` is not a dictionary.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.MATERIAL | DataItems.EQUIPMENT | DataItems.UNITS)  # doctest: +SKIP
        >>> names = ItemNames(game_data, get_localization_dictionary(comlink))  # doctest: +SKIP
        >>> names.get("MATERIAL", "unitshard_GLLEIA")  # doctest: +SKIP
        'Leia Organa'
        >>> names.get(3, "GRIND")  # doctest: +SKIP
        'Credits'
    """

    def __init__(self, game_data: Mapping[str, Any], localization: dict[str, str] | None = None) -> None:
        if not isinstance(game_data, Mapping):
            raise SwgohComlinkValueError(f"ItemNames: 'game_data' must be a dictionary, not {type(game_data)}")
        for collection in _ITEM_COLLECTIONS:
            if collection in game_data and not isinstance(game_data[collection], list):
                raise SwgohComlinkValueError(
                    f"ItemNames: game_data[{collection!r}] must be a list, not {type(game_data[collection])}"
                )
        _check_localization(localization, "ItemNames")
        self._localization = localization
        self._records: dict[int, dict[str, dict[str, Any]]] = {
            item_type: {
                str(r["id"]): r
                for r in game_data.get(collection) or []
                if isinstance(r, dict) and r.get("id") is not None
            }
            for item_type, (collection, _) in _NAMED_COLLECTIONS.items()
        }
        # The units collection has a row per rarity; any of them names the unit.
        self._units: dict[str, dict[str, Any]] = {}
        for unit in game_data.get("units") or []:
            if isinstance(unit, dict):
                self._units.setdefault(unit.get("baseId", ""), unit)
        self._mystery_mods = {
            str(r["id"]): r for r in game_data.get("mysteryStatMod") or [] if isinstance(r, dict) and r.get("id")
        }
        self._mod_sets = _mod_set_names(game_data.get("statModSet") or [], localization)
        self._cache: dict[tuple[int, str], str | None] = {}

    def _text(self, key: str | None) -> str | None:
        """The localized string for ``key``; the key itself without a localization; ``None`` if unresolved."""
        if not key:
            return None
        if self._localization is None:
            return key
        return _localize(self._localization, key, "") or None

    def _unit_name(self, base_id: str) -> str | None:
        unit = self._units.get(base_id)
        return self._text(unit.get("nameKey")) if unit else None

    def _mystery_mod_name(self, item_id: str) -> str | None:
        mod = self._mystery_mods.get(item_id)
        if mod is None:
            return None
        pips = _range(_as_int(mod.get("minRarity"), _RARITY_ENUMS), _as_int(mod.get("maxRarity"), _RARITY_ENUMS))
        tier = _range(
            _as_int(mod.get("minTier"), _MOD_TIER_ENUMS),
            _as_int(mod.get("maxTier"), _MOD_TIER_ENUMS),
            _MOD_TIER_LETTERS,
        )
        slots = [MOD_SLOTS.get(str(_as_int(slot, _MOD_SLOT_ENUMS)), "?") for slot in mod.get("slot") or []]
        slot = "any-slot" if len(set(slots)) >= len(MOD_SLOTS) else " or ".join(slots)
        set_id = str(mod.get("setId", ""))
        set_name = self._mod_sets.get(set_id) or MOD_SET_IDS.get(set_id, "")
        return " ".join(part for part in (f"{pips}-dot", set_name, slot, f"mod ({tier})") if part)

    def _resolve(self, item_type: int, item_id: str) -> str | None:
        if item_type == _CURRENCY:
            member = CURRENCY_TYPES.get(int(item_id)) if item_id.isdigit() else item_id
            return CURRENCY_NAMES.get(member) if member else None
        if item_type == _UNIT:
            return self._unit_name(item_id.split(":", 1)[0])
        if item_type == _MYSTERY_STAT_MOD:
            return self._mystery_mod_name(item_id)
        if item_type not in _NAMED_COLLECTIONS:
            return None
        record = self._records[item_type].get(item_id)
        name = self._text(record.get(_NAMED_COLLECTIONS[item_type][1])) if record else None
        if name is None and item_type == _MATERIAL and item_id.startswith(_SHARD_PREFIX):
            name = self._unit_name(item_id.removeprefix(_SHARD_PREFIX))
        return name

    def get(self, item_type: int | str, item_id: str | int, default: str | None = None) -> str | None:
        """Return the display name of an item, or ``default`` when it cannot be resolved.

        Args:
            item_type: The item's ``ItemType``, as a number (``7``) or an enum name (``"MATERIAL"``).
            item_id: The item's id. A currency may be given by its ``CurrencyType`` number.
            default: Returned when the item cannot be named. [Default: ``None``]

        Returns:
            The item's display name, or ``default``.
        """
        number = _item_type_number(item_type)
        if number is None:
            return default
        key = (number, str(item_id))
        if key not in self._cache:
            self._cache[key] = self._resolve(*key)
        name = self._cache[key]
        return default if name is None else name


def get_named_rewards(rewards: list[dict[str, Any]], item_names: ItemNames) -> list[NamedReward]:
    """Read a reward preview list into named rewards.

    Takes any of a campaign mission's reward previews (``rewardPreview``, ``firstCompleteRewardPreview``,
    ``instanceFirstCompleteRewardPreview``, ``conditionalRewardsPreview``) or an event instance's
    ``rewardPreview``. A ``conditionalRewardsPreview`` entry does not hold an item itself: its items are
    nested under ``bucketItem``, paid while its ``requirementId`` holds (a Galactic Legend event's shards
    until the tier's allotment is exhausted, for example). Those items are listed in their place, with
    ``requirement_id`` set. Entries that are neither an item nor a bucket are skipped, as are entries and
    bucket items that are not dictionaries.

    A campaign mission's rank reward previews (``rankRewardPreview``,
    ``immediateRegularRankRewardPreview``) are not reward lists of this shape: each entry is a rank range
    holding its items under ``primaryReward`` and ``detailedReward``. Passed as a whole they read as
    ``[]``; pass an entry's ``detailedReward`` (or ``primaryReward``) list instead.

    Args:
        rewards: A reward preview list.
        item_names: An :class:`ItemNames` built from the game data the rewards come from.

    Returns:
        A list of :class:`NamedReward` dictionaries in preview order.

    Raises:
        SwgohComlinkValueError: If ``rewards`` is not a list or ``item_names`` is not an :class:`ItemNames`.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.CAMPAIGN | DataItems.MATERIAL | DataItems.UNITS)  # doctest: +SKIP
        >>> names = ItemNames(game_data, get_localization_dictionary(comlink))  # doctest: +SKIP
        >>> mission = game_data["campaign"][4]["campaignMap"][0]["campaignNodeDifficultyGroup"][0][
        ...     "campaignNode"][0]["campaignNodeMission"][0]  # doctest: +SKIP
        >>> for reward in get_named_rewards(mission["rewardPreview"], names):  # doctest: +SKIP
        ...     print(reward["name"], reward["max_quantity"])
    """
    _check_list("rewards", rewards, "get_named_rewards()")
    if not isinstance(item_names, ItemNames):
        raise SwgohComlinkValueError(
            f"get_named_rewards(): 'item_names' must be an ItemNames instance, not {type(item_names)}"
        )

    result: list[NamedReward] = []
    for entry in rewards:
        if not isinstance(entry, dict):
            continue
        if "bucketItem" in entry:
            items = [
                (item, entry.get("requirementId") or None)
                for item in entry.get("bucketItem") or []
                if isinstance(item, dict)
            ]
        elif "type" in entry:
            items = [(entry, None)]
        else:
            continue
        for item, requirement_id in items:
            raw_type = item.get("type")
            number = _item_type_number(raw_type)
            item_type: int | str | None = (
                number if number is not None else (None if raw_type is None else str(raw_type))
            )
            item_id = str(item.get("id") or "")
            base_id: str | None = None
            if number == _UNIT:
                base_id = item_id.split(":", 1)[0]
            elif number == _MATERIAL and item_id.startswith(_SHARD_PREFIX):
                base_id = item_id.removeprefix(_SHARD_PREFIX)
            fallback = item_id or ITEM_TYPES.get(number or 0) or ("" if item_type is None else str(item_type))
            name = fallback if item_type is None else item_names.get(item_type, item_id, fallback) or fallback
            result.append(
                {
                    "item_type": item_type,
                    "id": item_id,
                    "name": name,
                    "min_quantity": _as_int(item.get("minQuantity")) or 0,
                    "max_quantity": _as_int(item.get("maxQuantity")) or 0,
                    "base_id": base_id,
                    "requirement_id": requirement_id,
                }
            )
    return result
