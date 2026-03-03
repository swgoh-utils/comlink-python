from __future__ import annotations

import pytest

from swgoh_comlink import StatCalc


@pytest.fixture
def stubbed_calc(monkeypatch: pytest.MonkeyPatch) -> StatCalc:
    calc = StatCalc.__new__(StatCalc)
    calc._unit_data = {}
    calc._mod_set_data = {}
    calc._gear_data = {}
    calc._cr_tables = {}
    calc._gp_tables = {}
    calc._relic_data = {}

    monkeypatch.setattr(calc, "_normalize_char", lambda unit: dict(unit))
    monkeypatch.setattr(
        calc,
        "_get_char_raw_stats",
        lambda _char: {"base": {"Health": 1000}, "final": {"Health": 1000}},
    )
    monkeypatch.setattr(calc, "_calculate_base_stats", lambda stats, _lvl, _defid: stats)
    monkeypatch.setattr(calc, "_calculate_mod_stats", lambda _base, _char: {"Speed": 10})
    monkeypatch.setattr(calc, "_format_stats", lambda stats, _lvl: stats)
    monkeypatch.setattr(calc, "_calc_char_gp", lambda _char: 12345)

    return calc


def test_calc_char_stats_offline_pipeline_mutates_unit(stubbed_calc: StatCalc) -> None:
    unit = {
        "defId": "BOSSK",
        "rarity": 7,
        "level": 85,
        "gear": 13,
        "equipped": [],
        "skills": [],
    }

    result = stubbed_calc.calc_char_stats(unit)

    assert result is unit
    assert unit["stats"]["mods"]["Speed"] == 10
    assert unit["stats"]["gp"] == 12345
    assert unit["gp"] == 12345
