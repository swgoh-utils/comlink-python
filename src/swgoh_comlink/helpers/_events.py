# coding=utf-8
"""Game event schedule helper functions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from ..exceptions import SwgohComlinkValueError
from ._localization import parse_swgoh_string
from ._utils import _as_int, get_function_name

# Permanent events (journeys, legendary events) have one instance ending in the year 2126. Anything ending
# after this (2096-10-02) is treated as having no end.
_PERMANENT_MS = 4_000_000_000_000


class ScheduledEvent(TypedDict):
    """One live or upcoming game event as returned by :func:`get_event_schedule`."""

    event_id: str
    instance_id: str | None
    """The ``id`` of the run (instance) this entry describes, when the payload names one."""
    name: str
    """Localized name on one line: ``title`` and ``subtitle`` joined with ``" - "``, or ``title`` alone.
    Falls back to the event's ``nameKey`` and then its id."""
    title: str
    """The first line of the game's two-line banner, as the game writes it (often in capitals), e.g.
    ``"THE MANDALORIAN"``. Falls back like ``name``."""
    subtitle: str | None
    """The rest of the banner, e.g. ``"Hero's Journey"``, or ``None`` for a one-line name."""
    name_key: str
    type: int | str | None
    """The event's ``type`` (see the ``GameEventType`` enum), e.g. ``10`` for Grand Arena."""
    status: Literal["live", "upcoming"]
    start: datetime
    """When this run opens, as a timezone-aware UTC datetime."""
    end: datetime | None
    """When this run closes, as a timezone-aware UTC datetime, or ``None`` for a permanent event."""
    campaign_element: dict[str, Any] | None
    """The run's ``campaignElementIdentifier`` (the campaign node it plays), or ``None``."""


def _moment(millis: int) -> datetime:
    return datetime.fromtimestamp(millis / 1000, tz=timezone.utc)


def _event_name(text: str) -> tuple[str, str | None]:
    """Split an event's banner text into its title and subtitle, markup removed and case kept.

    ``THE MANDALORIAN\\n[c][FFC891]Hero's Journey[-][/c]`` -> ``("THE MANDALORIAN", "Hero's Journey")``. A
    one-line name has no subtitle; lines after the second are joined into the subtitle with ``" - "``.
    """
    lines = [line.strip() for line in parse_swgoh_string(text).splitlines() if line.strip()]
    if not lines:
        return "", None
    return lines[0], " - ".join(lines[1:]) or None


def get_event_schedule(
    events: dict[str, Any] | list[dict[str, Any]],
    localization: dict[str, str] | None = None,
    *,
    now: datetime | None = None,
    include_upcoming: bool = True,
) -> list[ScheduledEvent]:
    """List the game events that are live now and, optionally, those scheduled to start later.

    Each ``gameEvent`` has one or more ``instance`` entries, the runs it is scheduled for, each with a
    ``startTime`` and ``endTime`` in epoch milliseconds (sent as strings). An event is live when one of
    its runs holds ``now``, and upcoming when its next run has yet to open; the schedule carries runs
    days ahead. Each event is listed once: for the run that is live, or the one ending first when two
    overlap at a changeover, otherwise for its next run. Events whose every run has ended are left out.

    Permanent events (journeys, legendary events) have a single run ending in the year 2126; their
    ``end`` is ``None``.

    The game writes most event names as a two-line banner, ``THE MANDALORIAN\\n[c][FFC891]Hero's
    Journey[-][/c]``. Markup is removed and the case is kept as written: ``title`` is the first line
    (``"THE MANDALORIAN"``), ``subtitle`` the second (``"Hero's Journey"``), and ``name`` joins them as
    ``"THE MANDALORIAN - Hero's Journey"``.

    Args:
        events: The response from ``SwgohComlink.get_events()``, or its ``gameEvent`` list.
        localization: Optional localization dictionary, e.g. from :func:`get_localization_dictionary`.
            When omitted, names are returned as their localization keys.
        now: The time to compare against. A naive value is read as local time. Defaults to the current
            time.
        include_upcoming: Also list events whose next run has not started yet. [Default: True]

    Returns:
        A list of :class:`ScheduledEvent` dictionaries: live events in ``gameEvent`` order, then upcoming
        events soonest first.

    Raises:
        SwgohComlinkValueError: If ``events`` is not a ``get_events()`` response or list, or
            ``localization`` is not a dictionary.

    Examples:
        >>> loc = get_localization_dictionary(comlink)  # doctest: +SKIP
        >>> for event in get_event_schedule(comlink.get_events(), loc):  # doctest: +SKIP
        ...     print(event["status"], event["name"], event["end"])
        live THE MANDALORIAN - Hero's Journey None
    """
    game_events = events.get("gameEvent") if isinstance(events, dict) else events
    if not isinstance(game_events, list):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'events' must be a get_events() response or its 'gameEvent' list, "
            f"not {type(events)}"
        )
    if localization is not None and not isinstance(localization, dict):
        raise SwgohComlinkValueError(
            f"{get_function_name()}: 'localization' must be a dictionary, not {type(localization)}"
        )
    now = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    now_ms = now.timestamp() * 1000

    live: list[ScheduledEvent] = []
    upcoming: list[ScheduledEvent] = []
    for event in game_events:
        if not isinstance(event, dict):
            continue
        # A run without a usable window (no endTime, or one before its start) cannot be placed.
        runs = [
            (start, end, run)
            for run in event.get("instance") or []
            if isinstance(run, dict) and (end := _as_int(run.get("endTime"))) > (start := _as_int(run.get("startTime")))
        ]
        # The live run ending first (two can overlap at a changeover), else the next run to open
        status: Literal["live", "upcoming"] = "live"
        chosen = min((r for r in runs if r[0] <= now_ms < r[1]), key=lambda r: r[1], default=None)
        if chosen is None and include_upcoming:
            status = "upcoming"
            chosen = min((r for r in runs if r[0] > now_ms), key=lambda r: r[0], default=None)
        if chosen is None:
            continue
        start, end, run = chosen

        name_key = event.get("nameKey") or ""
        raw_name = localization.get(name_key) if localization is not None and name_key else None
        title, subtitle = _event_name(raw_name) if raw_name else ("", None)
        if not title:
            title, subtitle = name_key or event.get("id", ""), None
        name = f"{title} - {subtitle}" if subtitle else title
        element = run.get("campaignElementIdentifier")
        (live if status == "live" else upcoming).append(
            {
                "event_id": event.get("id", ""),
                "instance_id": run.get("id"),
                "name": name,
                "title": title,
                "subtitle": subtitle,
                "name_key": name_key,
                "type": event.get("type"),
                "status": status,
                "start": _moment(start),
                "end": None if end >= _PERMANENT_MS else _moment(end),
                "campaign_element": element if isinstance(element, dict) else None,
            }
        )
    upcoming.sort(key=lambda scheduled: scheduled["start"])
    return live + upcoming
