# coding=utf-8
"""Readers for the loosely typed values in Comlink payloads.

Game payloads are loosely typed on the wire: an ``int64`` arrives as a string, a field may be
absent, an enum is an int or a name depending on the ``enums`` flag, and a repeated field with one
element can decode as a bare object. These functions fail soft to a fixed default so that one
unusable field never costs the whole record.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from ..exceptions import SwgohComlinkValueError
from ._utils import get_function_name

# An epoch below this is seconds, at or above it milliseconds. The game uses both (guildJoinTime and
# Conquest lastRefreshTime are seconds, lastActivityTime is milliseconds), and 1e11 seconds is the
# year 5138 while 1e11 milliseconds is March 1973, so the two ranges cannot meet in real data.
_MILLISECONDS_FROM = 100_000_000_000
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def as_int(value: Any, default: int = 0) -> int:
    """Read a payload number, which arrives as a string as often as an int.

    ``int64`` fields are quoted under proto3's JSON mapping (``"1655938556"``) and bare elsewhere,
    so both parse. ``bool`` is never read as a number even though it subclasses ``int``:
    ``int(True)`` is ``1``, which would look like real data (a score, a timestamp).

    Args:
        value: The raw payload value.
        default: Returned when *value* is missing or is not a whole number. [Default: 0]

    Returns:
        The value as an int. A float is truncated; a string must hold a whole number
        (``"1.5"`` returns *default*).

    Examples:
        >>> as_int("1655938556")
        1655938556
        >>> as_int(None)
        0
        >>> as_int("", default=-1)
        -1
        >>> as_int(True)
        0
    """
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def as_str(value: Any, default: str = "") -> str:
    """Read a payload string, or *default* when the value is not one.

    Nothing is converted: a number, ``None`` or a nested object returns *default*. Use
    :func:`as_id` for an id that may arrive as a number.

    Args:
        value: The raw payload value.
        default: Returned when *value* is not a ``str``. [Default: ""]

    Returns:
        *value* when it is a string, otherwise *default*.

    Examples:
        >>> as_str("Rebels")
        'Rebels'
        >>> as_str(42)
        ''
    """
    return value if isinstance(value, str) else default


def as_id(value: Any, default: str = "") -> str:
    """Read an id that may arrive as a string or as a bare integer.

    Ids such as ``matchId`` and ``currentMatchId`` are usually strings but have also been sent as
    integers (``currentMatchId: 2``), so an int is converted with ``str()``. ``bool`` and anything
    other than a string or an int return *default*.

    Args:
        value: The raw payload value.
        default: Returned when *value* is neither a ``str`` nor an ``int``. [Default: ""]

    Returns:
        The id as a string.

    Examples:
        >>> as_id(2)
        '2'
        >>> as_id("O1700000000000:1")
        'O1700000000000:1'
        >>> as_id(None)
        ''
    """
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return default


def as_scalar(value: Any) -> int | str | None:
    """Read an enum-rendered field exactly as sent: an int or a string, otherwise ``None``.

    An enum field (``TerritoryZoneState``, ``ChannelEventType`` and the like) is a bare integer
    when fetched with ``enums=False`` and a name with ``enums=True``, so both are kept unchanged.
    ``bool`` is excluded despite subclassing ``int``. Use :func:`parse_enum` to resolve either
    form to the member name.

    Args:
        value: The raw payload value.

    Returns:
        *value* when it is an ``int`` or a ``str``, otherwise ``None``.

    Examples:
        >>> as_scalar(3)
        3
        >>> as_scalar("ZONE_OPEN")
        'ZONE_OPEN'
        >>> as_scalar(True) is None
        True
    """
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, str)) else None


def as_epoch(value: Any) -> datetime | None:
    """Read a payload timestamp as an aware UTC datetime, in seconds or milliseconds.

    The game sends both units: ``guildJoinTime`` and Conquest ``lastRefreshTime`` are seconds,
    ``lastActivityTime`` and most event and match times are milliseconds. A value below
    ``1e11`` is read as seconds (1e11 seconds is the year 5138) and anything larger as
    milliseconds. ``0``, ``"0"``, ``None`` and anything unreadable mean "no time" and return
    ``None`` rather than 1970: an unstarted phase carries the field set to zero.

    Args:
        value: The raw payload value, as an int or a numeric string.

    Returns:
        The moment as a timezone-aware UTC datetime, or ``None`` when *value* is missing, not
        positive, unreadable, or past the year 9999.

    Examples:
        >>> as_epoch("1700000000000")
        datetime.datetime(2023, 11, 14, 22, 13, 20, tzinfo=datetime.timezone.utc)
        >>> as_epoch(1655938556)
        datetime.datetime(2022, 6, 22, 22, 55, 56, tzinfo=datetime.timezone.utc)
        >>> as_epoch("0") is None
        True
    """
    number = as_int(value)
    if number <= 0:
        return None
    # timedelta arithmetic is exact, where fromtimestamp(ms / 1000) can be off by a microsecond.
    try:
        if number >= _MILLISECONDS_FROM:
            return _EPOCH + timedelta(milliseconds=number)
        return _EPOCH + timedelta(seconds=number)
    except OverflowError:
        return None


def as_list(value: Any) -> list[Any]:
    """Read a repeated field, whether it arrived as a list or as a single element.

    A repeated field with one element can decode the same as a scalar field, so a lone object
    is wrapped in a list. A missing field (``None``) is an empty list: proto3 omits empty
    repeated fields. A tuple is converted to a list; any other value becomes its only element.

    Args:
        value: The raw payload value.

    Returns:
        *value* itself when it is already a list (not a copy), otherwise a new list.

    Examples:
        >>> as_list([{"id": "a"}, {"id": "b"}])
        [{'id': 'a'}, {'id': 'b'}]
        >>> as_list({"id": "a"})
        [{'id': 'a'}]
        >>> as_list(None)
        []
    """
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, tuple):
        return list(value)
    return [value]


def base_id(unit_identifier: Any) -> str:
    """Return the base id from a unit identifier such as ``"GENERALSKYWALKER:SEVEN_STAR"``.

    Unit identifiers carry the unit's rarity after a colon, but not always: an unfilled
    Territory Battle platoon slot names its required unit with the bare base id (``"BOUSHH"``),
    so the identifier is split rather than sliced.

    Args:
        unit_identifier: A unit ``definitionId``, ``unitIdentifier`` or game data unit ``id``.

    Returns:
        The part before the first colon, or ``""`` when *unit_identifier* is not a string.

    Examples:
        >>> base_id("GENERALSKYWALKER:SEVEN_STAR")
        'GENERALSKYWALKER'
        >>> base_id("BOUSHH")
        'BOUSHH'
    """
    if not isinstance(unit_identifier, str):
        return ""
    return unit_identifier.split(":", 1)[0]


def _squash(name: str) -> str:
    """One spelling for an enum name: upper-cased, with the underscores dropped."""
    return name.upper().replace("_", "")


def _enum_type_name(members: Mapping[str, int]) -> str | None:
    """The enum's type name, read from its ``<TypeName>_DEFAULT`` zero member when it has one."""
    for name, number in members.items():
        type_name, _, suffix = name.rpartition("_")
        if suffix == "DEFAULT" and number == 0 and type_name and not type_name.isupper():
            return type_name
    return None


def parse_enum(value: Any, members: Mapping[str, int], *, enum_name: str | None = None) -> str | None:
    """Resolve any wire spelling of an enum value to the member's canonical name.

    An enum field arrives as an int (``16``), a numeric string (``"16"``), the member name
    (``"SHARD_CURRENCY"``), or a decoder-style name made of the enum type and the member name,
    upper-cased and without underscores (``"CURRENCYTYPE_SHARDCURRENCY"``). All four resolve to
    ``"SHARD_CURRENCY"``. Names are also matched ignoring case and underscores.

    A decoder-style name must hold exactly one underscore, and its first half must be the enum's
    type name when that is known: from *enum_name*, or else from a ``<TypeName>_DEFAULT`` member
    (most of the game's enums have one, such as ``CurrencyType_DEFAULT``). This keeps an unknown
    member from a newer game version, such as ``"NEW_GRIND"``, from being read as ``"GRIND"``.
    When the type name is not known, any first half is accepted. ``bool`` and floats are never read
    as a member value.

    Args:
        value: The raw payload value.
        members: One enum's member names mapped to their values, as returned for that enum by
            ``get_enums()`` (e.g. ``comlink.get_enums()["CurrencyType"]``).
        enum_name: The enum's type name (e.g. ``"CampaignNodeDifficulty"``), checked against the
            first half of a decoder-style name. [Default: inferred from *members* when possible]

    Returns:
        The member name as spelled in *members*, or ``None`` when *value* names no member or a
        name could mean more than one. When several names share a value, the first one in
        *members* is returned for that value.

    Raises:
        SwgohComlinkValueError: If *members* is not a mapping.

    Examples:
        >>> currency = {"CurrencyType_DEFAULT": 0, "GRIND": 1, "SHARD_CURRENCY": 16}
        >>> parse_enum(16, currency)
        'SHARD_CURRENCY'
        >>> parse_enum("16", currency)
        'SHARD_CURRENCY'
        >>> parse_enum("CURRENCYTYPE_SHARDCURRENCY", currency)
        'SHARD_CURRENCY'
        >>> parse_enum("NEW_GRIND", currency) is None
        True
    """
    if not isinstance(members, Mapping):
        raise SwgohComlinkValueError(f"{get_function_name()}: 'members' must be a mapping, not {type(members)}")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return next((name for name, number in members.items() if number == value), None)
    if not isinstance(value, str):
        return None

    text = value.strip()
    if text in members:
        return text
    digits = text.removeprefix("-")
    if digits.isascii() and digits.isdigit():
        return parse_enum(int(text), members)

    candidates = [_squash(text)]
    head, _, tail = text.partition("_")
    if tail and "_" not in tail:
        type_name = enum_name if enum_name is not None else _enum_type_name(members)
        if type_name is None or _squash(head) == _squash(type_name):
            candidates.append(_squash(tail))
    # A spelling that fits two members cannot be told apart, so neither wins. Two names can squash
    # alike ("A_B" and "AB"), and MetadataRequestType has both "MetadataRequestType_DEFAULT" and
    # "DEFAULT", so "METADATAREQUESTTYPE_DEFAULT" reads as either.
    matches = {name for name in members if _squash(name) in candidates}
    return matches.pop() if len(matches) == 1 else None
