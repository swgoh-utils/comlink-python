# coding=utf-8
"""Era helper functions over the game data ``eraDefinition`` collection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..exceptions import SwgohComlinkValueError
from ._utils import get_function_name
from ._wire import as_int, as_list, base_id


def get_era_units(
    eras: dict[str, Any] | list[dict[str, Any]],
    era_id: str | None = None,
    *,
    now: datetime | None = None,
    include_loaned: bool = False,
) -> list[str]:
    """List the base ids of the units that belong to an Era.

    Game data carries a few ``eraDefinition`` entries at once, typically the previous, current and next Era,
    each open from ``startTimeMs`` until ``endTimeMs`` (epoch milliseconds, sent as strings). Consecutive Eras
    share their boundary, so the window is read as half-open: an Era ending at the moment the next begins is no
    longer active.

    An Era's own units are its ``eraUnitId`` list plus its ``journeyUnit``, which is normally in that list
    already. Eras also lend older units for their episodes (``loanedUnit``); those are added after the Era's
    own units when ``include_loaned`` is set.

    Args:
        eras: The response from ``SwgohComlink.get_game_data()`` (request ``DataItems.ERA_DEFINITION``), or
            its ``eraDefinition`` list.
        era_id: The ``id`` of the Era to read, e.g. ``"ERA09_MYTHS"``. Defaults to the Era active at ``now``.
        now: The time to compare against when ``era_id`` is omitted. A naive value is read as local time.
            Defaults to the current time.
        include_loaned: Also list the units the Era lends to players. [Default: False]

    Returns:
        Unit base ids in game data order, each listed once. An empty list when ``era_id`` is omitted and no
        Era is active at ``now``.

    Raises:
        SwgohComlinkValueError: If ``eras`` is not a ``get_game_data()`` response or ``eraDefinition`` list,
            or ``era_id`` names no Era in it.

    Examples:
        >>> game_data = comlink.get_game_data(items=DataItems.ERA_DEFINITION)  # doctest: +SKIP
        >>> get_era_units(game_data, "ERA09_MYTHS")  # doctest: +SKIP
        ['DARTHJARJAR', 'THERONIN', 'STORMTROOPERCONCEPT', 'LUKESTARKILLER', 'YODADSV', 'JAXXON', ...]
    """
    definitions = eras.get("eraDefinition") if isinstance(eras, dict) else eras
    if not isinstance(definitions, list):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'eras' must be a get_game_data() response or its 'eraDefinition' list, "
            f"not {type(eras)}"
        )
    definitions = [era for era in definitions if isinstance(era, dict)]

    if era_id is None:
        now = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
        now_ms = now.timestamp() * 1000
        era = next(
            (e for e in definitions if as_int(e.get("startTimeMs")) <= now_ms < as_int(e.get("endTimeMs"))), None
        )
        if era is None:
            return []
    else:
        era = next((e for e in definitions if e.get("id") == era_id), None)
        if era is None:
            raise SwgohComlinkValueError(
                f"{get_function_name()}: no Era with id {era_id!r} (available: {[e.get('id') for e in definitions]})"
            )

    unit_ids = [*as_list(era.get("eraUnitId")), era.get("journeyUnit")]
    if include_loaned:
        unit_ids += [loan.get("id") for loan in as_list(era.get("loanedUnit")) if isinstance(loan, dict)]
    # dict.fromkeys drops repeats (the journey unit, a loan of an Era unit) and keeps first-seen order
    return list(dict.fromkeys(unit for unit in map(base_id, unit_ids) if unit))
