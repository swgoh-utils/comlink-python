# coding=utf-8
"""v3.2 Phase 5 — parity tests for the shipped surface.

Two candidates landed from the three-axis StatCalc research:

* **Candidate A** — bimorphic input on :meth:`StatCalc.calc_player_stats`
  and :meth:`StatCalc.calc_roster_stats`. A Comlink-format dict and the
  typed :class:`~swgoh_comlink._models.Player` Struct must produce
  byte-identical per-unit stats and GP.
* **Candidate E** — :func:`get_statcalc_game_data` persists the
  StatCalc-normalized game_data via :class:`GameDataCache`. The
  disk-warm-reloaded form must drive StatCalc to the same per-unit
  output as the freshly-built form.

Both surfaces ship under the v3.2 ≥ 50 % cold-start / ≥ 10 % hot-path
decision rules recorded in ADR-0006. Parity failure is non-shippable;
these tests are load-bearing.

The two other shipped-ish behaviours fall out of A's implementation:
``calc_roster_stats`` also accepts a list of
:class:`~swgoh_comlink._models.RosterUnit` Structs, and the typed
:class:`Player` Struct works as a list element when a caller hands
:meth:`calc_player_stats` ``[player_struct_a, player_struct_b]``.
"""

from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from swgoh_comlink._cache import GameDataCache
from swgoh_comlink._models import PLAYER_DECODER
from swgoh_comlink.StatCalc import StatCalc, get_statcalc_game_data
from swgoh_comlink.StatCalc.data_builder._builder_base import GameDataBuilderBase

_FIXTURES = Path(__file__).resolve().parents[1].parent / "benchmarks" / "v3" / "fixtures"

_PLAYERS = ["player_small", "player_large"]


def _have_cassette(name: str) -> bool:
    return (_FIXTURES / f"{name}.json.gz").exists()


def _load_player_bytes(name: str) -> bytes:
    with gzip.open(_FIXTURES / f"{name}.json.gz", "rb") as fh:
        return fh.read()


# ── Shared fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def raw_game_data() -> dict[str, Any]:
    if not _have_cassette("data"):
        pytest.skip("/data cassette missing — record cassettes first")
    with gzip.open(_FIXTURES / "data.json.gz", "rb") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


@pytest.fixture(scope="module")
def game_data(raw_game_data: dict[str, Any]) -> dict[str, Any]:
    return GameDataBuilderBase._build_game_data(raw_game_data)


@pytest.fixture(scope="module")
def sc_baseline(game_data: dict[str, Any]) -> StatCalc:
    return StatCalc(game_data=game_data)


# ── Candidate A — bimorphic dict / Struct input ─────────────────────────────


@pytest.mark.parametrize("player_name", _PLAYERS)
def test_bimorphic_player_struct_matches_dict(
    sc_baseline: StatCalc,
    player_name: str,
) -> None:
    """Player Struct input → identical per-unit stats vs Comlink-format dict."""
    if not _have_cassette(player_name):
        pytest.skip(f"{player_name} cassette missing")
    body = _load_player_bytes(player_name)

    dict_player = json.loads(body)
    sc_baseline.calc_player_stats(dict_player)
    dict_units = dict_player["rosterUnit"]

    struct_player = PLAYER_DECODER.decode(body)
    struct_result = sc_baseline.calc_player_stats(struct_player)
    assert isinstance(struct_result, dict)
    struct_units = struct_result["rosterUnit"]

    assert len(struct_units) == len(dict_units)
    for d_unit, s_unit in zip(dict_units, struct_units, strict=True):
        d_def = d_unit.get("definitionId")
        s_def = s_unit.get("definitionId")
        assert d_def == s_def, f"definitionId drift: {d_def!r} vs {s_def!r}"
        assert d_unit.get("stats") == s_unit.get("stats"), (
            f"stats drift on {d_def}: dict={d_unit.get('stats')!r} struct={s_unit.get('stats')!r}"
        )
        assert d_unit.get("gp") == s_unit.get("gp"), (
            f"gp drift on {d_def}: dict={d_unit.get('gp')!r} struct={s_unit.get('gp')!r}"
        )


@pytest.mark.parametrize("player_name", _PLAYERS)
def test_bimorphic_roster_unit_struct_list(
    sc_baseline: StatCalc,
    player_name: str,
) -> None:
    """A list of RosterUnit Structs through calc_roster_stats matches a list of dicts."""
    if not _have_cassette(player_name):
        pytest.skip(f"{player_name} cassette missing")
    body = _load_player_bytes(player_name)

    dict_player = json.loads(body)
    sc_baseline.calc_roster_stats(dict_player["rosterUnit"])
    dict_units = dict_player["rosterUnit"]

    struct_player = PLAYER_DECODER.decode(body)
    struct_units = sc_baseline.calc_roster_stats(list(struct_player.roster_unit))
    assert isinstance(struct_units, list)

    assert len(struct_units) == len(dict_units)
    for d_unit, s_unit in zip(dict_units, struct_units, strict=True):
        assert d_unit.get("stats") == s_unit.get("stats")
        assert d_unit.get("gp") == s_unit.get("gp")


def test_bimorphic_list_of_player_structs(sc_baseline: StatCalc) -> None:
    """`calc_player_stats([struct_a, struct_b])` matches `calc_player_stats([dict_a, dict_b])`."""
    if not _have_cassette("player_small"):
        pytest.skip("player_small cassette missing")
    body = _load_player_bytes("player_small")

    dict_payload = [json.loads(body), json.loads(body)]
    sc_baseline.calc_player_stats(dict_payload)

    struct_payload = [PLAYER_DECODER.decode(body), PLAYER_DECODER.decode(body)]
    result = sc_baseline.calc_player_stats(struct_payload)

    assert isinstance(result, list)
    assert len(result) == 2
    for dict_p, struct_p in zip(dict_payload, result, strict=True):
        d_units = dict_p["rosterUnit"]
        s_units = struct_p["rosterUnit"]  # type: ignore[index]
        assert len(d_units) == len(s_units)
        for d_unit, s_unit in zip(d_units, s_units, strict=True):
            assert d_unit.get("stats") == s_unit.get("stats")
            assert d_unit.get("gp") == s_unit.get("gp")


def test_bimorphic_dict_path_unchanged(sc_baseline: StatCalc) -> None:
    """The legacy dict path returns the same input object (mutated in place)."""
    if not _have_cassette("player_small"):
        pytest.skip("player_small cassette missing")
    body = _load_player_bytes("player_small")
    dict_player = json.loads(body)
    result = sc_baseline.calc_player_stats(dict_player)
    # Identity is preserved on the dict path — callers depending on
    # in-place mutation aren't broken by the v3.2 boundary check.
    assert result is dict_player


# ── Candidate E — cached normalized game_data ───────────────────────────────


def test_cached_normalized_inmem_memo(raw_game_data: dict[str, Any]) -> None:
    """Repeated get_statcalc_game_data calls hit the in-mem memo (no client)."""
    mock_client = MagicMock()
    md = MagicMock()
    md.latest_gamedata_version = "v_test_inmem"
    mock_client.get_game_metadata.return_value = md
    mock_client.get_game_data.return_value = raw_game_data

    with tempfile.TemporaryDirectory() as td:
        cache = GameDataCache(cache_dir=td)
        get_statcalc_game_data(mock_client, cache=cache)  # populate
        before = mock_client.get_game_data.call_count
        for _ in range(5):
            get_statcalc_game_data(mock_client, cache=cache)
        after = mock_client.get_game_data.call_count
        assert after == before, "in-mem memo failed — client.get_game_data was called on repeat get_statcalc_game_data"


def test_cached_normalized_disk_warm_round_trip(
    raw_game_data: dict[str, Any],
    game_data: dict[str, Any],
    sc_baseline: StatCalc,
) -> None:
    """First call writes to disk; a fresh in-mem cache rehydrates from disk
    and drives StatCalc to the same output as the freshly-built form."""
    if not _have_cassette("player_small"):
        pytest.skip("player_small cassette missing")

    mock_client = MagicMock()
    md = MagicMock()
    md.latest_gamedata_version = "v_test_parity"
    mock_client.get_game_metadata.return_value = md
    mock_client.get_game_data.return_value = raw_game_data

    with tempfile.TemporaryDirectory() as td:
        cache1 = GameDataCache(cache_dir=td)
        gd_first = get_statcalc_game_data(mock_client, cache=cache1)
        assert set(gd_first) == set(game_data)

        # Fresh in-mem cache, same dir → must take the disk-warm path
        cache2 = GameDataCache(cache_dir=td)
        gd_second = get_statcalc_game_data(mock_client, cache=cache2)

    assert set(gd_second) == set(game_data)

    # Parity: StatCalc on the disk-warm form must match baseline.
    sc_warm = StatCalc(game_data=gd_second)
    body = _load_player_bytes("player_small")

    baseline_player = json.loads(body)
    sc_baseline.calc_player_stats(baseline_player)

    warm_player = json.loads(body)
    sc_warm.calc_player_stats(warm_player)

    assert baseline_player == warm_player, "StatCalc output drift after disk-warm-loaded normalized game_data"
