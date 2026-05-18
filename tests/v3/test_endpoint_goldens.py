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
import warnings
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import msgspec
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


def _to_dict(result: Any) -> Any:
    """Return a dict-shaped view of *result* for comparison against goldens.

    Phase 3 endpoint returns are typed :class:`msgspec.Struct` (default) or
    dict (``raw=True``). Goldens are dict-shaped JSON captured pre-Phase-3,
    so we round-trip Structs through :func:`msgspec.to_builtins` to compare
    on equal footing. This is *also* the lossless-round-trip assertion the
    Phase 3 plan demanded of ``compat.to_dict()``.
    """
    if isinstance(result, msgspec.Struct):
        return msgspec.to_builtins(result)
    return result


# ── Sync tests (typed default) ──────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_sync_endpoint_matches_expected(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink_typed: Any,
    golden: Callable[[str], Any],
) -> None:
    """Typed sync SDK round-trips through to_builtins == expected.

    For typed endpoints (Player, Metadata, Guild, Leaderboard), the SDK
    returns a Struct; we serialize back to dict for the golden compare.
    For passthrough endpoints (/data, /localization), the SDK returns a
    dict directly and we compare against the cassette.
    """
    _apply_overrides(case, cassette_server)
    method = getattr(recorded_comlink_typed, case.method)
    result = method(**case.kwargs)
    expected = _expected(case, golden)
    assert _to_dict(result) == expected


# ── Async tests (typed default) ─────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_async_endpoint_matches_expected(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink_async_typed: Any,
    golden: Callable[[str], Any],
) -> None:
    """Async parity: same Struct→dict round-trip yields the same expected payload.

    Combined with the sync test, this also gives free sync/async parity
    by transitivity.
    """
    _apply_overrides(case, cassette_server)
    method: Callable[..., Awaitable[Any]] = getattr(recorded_comlink_async_typed, case.method)
    result = await method(**case.kwargs)
    expected = _expected(case, golden)
    assert _to_dict(result) == expected


# ── raw=True path on the typed client: dict shape preserved ─────────────────


_RAW_TYPED_CASES = [c for c in CASES if c.golden is not None]


@pytest.mark.parametrize("case", _RAW_TYPED_CASES, ids=[c.id for c in _RAW_TYPED_CASES])
def test_sync_endpoint_raw_returns_dict(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink_typed: Any,
    golden: Callable[[str], Any],
) -> None:
    """``raw=True`` on a typed endpoint returns the v2 dict shape unchanged."""
    _apply_overrides(case, cassette_server)
    method = getattr(recorded_comlink_typed, case.method)
    result = method(raw=True, **case.kwargs)
    assert isinstance(result, dict), f"raw=True should return dict, got {type(result).__name__}"
    expected = _expected(case, golden)
    assert result == expected


# ── Dict client returns dict natively (no raw=True needed) ──────────────────


@pytest.mark.parametrize("case", _RAW_TYPED_CASES, ids=[c.id for c in _RAW_TYPED_CASES])
def test_sync_dict_client_returns_dict_natively(
    case: EndpointCase,
    cassette_server: CassetteServer,
    recorded_comlink: Any,
    golden: Callable[[str], Any],
) -> None:
    """The dict-default client returns the v2 dict shape with no ``raw=`` kwarg."""
    _apply_overrides(case, cassette_server)
    method = getattr(recorded_comlink, case.method)
    result = method(**case.kwargs)
    assert isinstance(result, dict), f"dict client should return dict, got {type(result).__name__}"
    expected = _expected(case, golden)
    assert result == expected


# ── compat.to_dict deprecation warning ──────────────────────────────────────


def test_compat_to_dict_round_trips_player(
    cassette_server: CassetteServer,
    recorded_comlink_typed: Any,
    golden: Callable[[str], Any],
) -> None:
    """``compat.to_dict(player)`` round-trips lossless to the golden dict."""
    from swgoh_comlink import compat

    cassette_server.use("player", "player_small")
    p = recorded_comlink_typed.get_player(allycode=855566316)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        as_dict = compat.to_dict(p)
    assert as_dict == golden("player_small")


def test_compat_to_dict_emits_deprecation_warning(
    cassette_server: CassetteServer,
    recorded_comlink_typed: Any,
) -> None:
    """First call to ``compat.to_dict()`` raises DeprecationWarning."""
    from swgoh_comlink import compat

    cassette_server.use("player", "player_small")
    p = recorded_comlink_typed.get_player(allycode=855566316)
    with pytest.warns(DeprecationWarning, match=r"removed in v3\.2"):
        compat.to_dict(p)
