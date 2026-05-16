# coding=utf-8
"""Endpoint regression tests: SDK output == golden (or cassette for passthroughs).

One row per endpoint case. Each row runs **twice** — once through
:class:`SwgohComlink` (sync) and once through :class:`SwgohComlinkAsync` —
which gives both regression coverage and free sync/async parity in the
same parametrization.

Cases come in two flavors:

* **Golden-backed.** The SDK post-processes the response (e.g. ``get_guild``
  unwraps the outer ``"guild"`` key) and the canonical post-process output
  is committed under ``tests/v3/golden/``. Test asserts ``output == golden``.

* **Passthrough.** The SDK returns ``response.json()`` unchanged. Storing
  a golden would duplicate the cassette (and bloat git for ``data``,
  ``localization``, and ``player_large``). Test asserts ``output ==
  json.loads(cassette_bytes)``.

A failure in either flavor means *either* (a) SDK behavior drifted (Phase 3
changes the return type to Structs, so all goldens flip in that phase), or
(b) the cassette was re-recorded and content differs. Both cases require a
deliberate ``_regen_goldens`` and review.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from tests.v3.conftest import CassetteServer, load_cassette_bytes

# ── Case spec ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EndpointCase:
    """One regression scenario.

    Attributes:
        id: Pytest test ID (also the golden filename when golden-backed).
        method: SDK method name (must exist on both sync and async clients).
        kwargs: Keyword arguments passed to the method.
        cassette_overrides: Endpoint → cassette mapping applied before the call.
        golden: Golden file stem under ``tests/v3/golden/``. ``None`` means
            passthrough — :attr:`passthrough_cassette` carries the source.
        passthrough_cassette: Cassette to decode and compare against when
            :attr:`golden` is ``None``.
    """

    id: str
    method: str
    kwargs: dict[str, Any]
    cassette_overrides: dict[str, str] = field(default_factory=dict)
    golden: str | None = None
    passthrough_cassette: str | None = None

    def __post_init__(self) -> None:
        if self.golden is None and self.passthrough_cassette is None:
            raise ValueError(f"{self.id}: either golden or passthrough_cassette is required")
        if self.golden is not None and self.passthrough_cassette is not None:
            raise ValueError(f"{self.id}: golden and passthrough_cassette are mutually exclusive")


CASES: list[EndpointCase] = [
    EndpointCase(
        id="metadata",
        method="get_game_metadata",
        kwargs={},
        golden="metadata",
    ),
    EndpointCase(
        id="player_small",
        method="get_player",
        kwargs={"allycode": 855566316},
        cassette_overrides={"player": "player_small"},
        golden="player_small",
    ),
    EndpointCase(
        id="player_large_passthrough",
        method="get_player",
        kwargs={"allycode": 314927874},
        cassette_overrides={"player": "player_large"},
        passthrough_cassette="player_large",
    ),
    EndpointCase(
        id="guild",
        method="get_guild",
        kwargs={"guild_id": "GbsabjvbQESUd8r_qPqdYg"},
        golden="guild",
    ),
    EndpointCase(
        id="leaderboard",
        method="get_leaderboard",
        kwargs={"leaderboard_type": 6, "league": "kyber", "division": 1},
        golden="leaderboard",
    ),
    EndpointCase(
        id="data_passthrough",
        method="get_game_data",
        kwargs={"request_segment": 0, "version": "x"},  # version arg avoids extra metadata fetch
        passthrough_cassette="data",
    ),
    EndpointCase(
        id="localization_passthrough",
        method="get_localization",
        # localization_id="x" avoids the extra get_latest_game_data_version() side-call
        kwargs={"localization_id": "x", "locale": "ENG_US", "unzip": True},
        passthrough_cassette="localization_eng_us",
    ),
]


def _expected(case: EndpointCase, golden: Callable[[str], Any]) -> Any:
    """Return the expected payload for *case* (golden file or cassette JSON)."""
    if case.golden is not None:
        return golden(case.golden)
    assert case.passthrough_cassette is not None
    return json.loads(load_cassette_bytes(case.passthrough_cassette))


def _apply_overrides(case: EndpointCase, server: CassetteServer) -> None:
    for endpoint, cassette in case.cassette_overrides.items():
        server.use(endpoint, cassette)


# ── Sync tests ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_sync_endpoint_matches_expected(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink: Any,
    golden: Callable[[str], Any],
) -> None:
    """SDK (sync) output for *case* matches its golden or passthrough cassette."""
    _apply_overrides(case, cassette_server)
    method = getattr(recorded_comlink, case.method)
    result = method(**case.kwargs)
    expected = _expected(case, golden)
    assert result == expected


# ── Async tests ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_async_endpoint_matches_expected(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink_async: Any,
    golden: Callable[[str], Any],
) -> None:
    """SDK (async) output for *case* matches its golden or passthrough cassette.

    Combined with :func:`test_sync_endpoint_matches_expected` this also
    asserts sync/async parity by transitivity — both must equal the same
    expected payload.
    """
    _apply_overrides(case, cassette_server)
    method: Callable[..., Awaitable[Any]] = getattr(recorded_comlink_async, case.method)
    result = await method(**case.kwargs)
    expected = _expected(case, golden)
    assert result == expected
