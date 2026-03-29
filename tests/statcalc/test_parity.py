from pathlib import Path

import pytest
from parity.scripts.run_player_parity import run

pytestmark = pytest.mark.parity


def test_js_python_parity_with_example_player_rosterunit() -> None:
    player = Path(__file__).resolve().parents[1] / "resources" / "example-player.json"
    assert run(player) == 0
