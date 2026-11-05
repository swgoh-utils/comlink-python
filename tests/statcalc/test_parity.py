from pathlib import Path

import pytest
from parity.scripts.run_player_parity import run

pytestmark = pytest.mark.parity


def test_js_python_parity_with_example_player_rosterunit() -> None:
    player = Path(__file__).resolve().parents[1] / "resources" / "example-player.json"
    assert run(player) == 0


def test_parity_is_offline_and_detects_numerical_regression(monkeypatch, capsys):
    import urllib.request

    from parity.scripts import run_player_parity as runner

    def no_network(*args, **kwargs):
        raise AssertionError("Parity must use committed fixtures")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    original = runner._run_python

    def wrong_gp(*args):
        result = original(*args)
        result["player"]["rosterUnit"][0]["gp"] += 1
        return result

    monkeypatch.setattr(runner, "_run_python", wrong_gp)
    assert runner.run(runner.DEFAULT_PLAYER) == 1
    assert ".gp:" in capsys.readouterr().err
