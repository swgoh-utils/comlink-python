# coding=utf-8
"""Phase 6 tests — ``_optional.require`` + ``compat.to_pydantic``.

Covers:

* :func:`swgoh_comlink._optional.require` — successful import; friendly
  ``ImportError`` with install hint on missing module.
* :func:`swgoh_comlink._optional.has_extra` — True/False probe.
* :func:`swgoh_comlink.compat.to_pydantic` — round-trips a real Player
  Struct to a user-defined ``BaseModel``. Skipped if ``[pydantic]``
  isn't installed in the test environment.
"""

from __future__ import annotations

from typing import Any

import pytest

from swgoh_comlink._optional import has_extra, require

# ── require() ───────────────────────────────────────────────────────────────


def test_require_returns_modules_in_order() -> None:
    """Successful import returns a list of module objects, same order as args."""
    mods = require("test", "json", "os")
    assert [m.__name__ for m in mods] == ["json", "os"]


def test_require_friendly_error_on_missing() -> None:
    """Missing module raises with the pip install hint."""
    with pytest.raises(ImportError) as ctx:
        require("nonexistent", "this_module_does_not_exist_anywhere_42")
    assert "pip install swgoh-comlink[nonexistent]" in str(ctx.value)


def test_require_chained_cause_preserves_original_error() -> None:
    """The original ImportError is set as ``__cause__`` for debugging."""
    try:
        require("foo", "this_module_does_not_exist_anywhere_42")
    except ImportError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ImportError)


def test_require_no_modules_raises_value_error() -> None:
    """Calling require() with no modules is a programming bug, not a runtime path."""
    with pytest.raises(ValueError, match="at least one module"):
        require("anything")


# ── has_extra() ─────────────────────────────────────────────────────────────


def test_has_extra_true_for_stdlib() -> None:
    assert has_extra("anything", "json") is True
    assert has_extra("anything", "json", "os") is True


def test_has_extra_false_for_missing() -> None:
    assert has_extra("anything", "this_module_does_not_exist_anywhere_42") is False
    # short-circuits on first missing
    assert has_extra("anything", "json", "this_module_does_not_exist_anywhere_42") is False


# ── compat.to_pydantic ──────────────────────────────────────────────────────

_HAS_PYDANTIC = has_extra("pydantic", "pydantic")


@pytest.mark.skipif(not _HAS_PYDANTIC, reason="pydantic not installed in this venv")
def test_to_pydantic_round_trips_player(cassette_server: Any, recorded_comlink: Any) -> None:
    """User-defined BaseModel validates against a real Player Struct."""
    from pydantic import BaseModel, Field

    from swgoh_comlink import compat

    class MyPlayer(BaseModel):
        name: str
        ally_code: str = Field(alias="allyCode")
        level: int

        # pydantic v2 ignores extras by default; only the fields above are
        # validated and the rest of the Player payload passes through.
        model_config = {"extra": "ignore", "populate_by_name": True}

    cassette_server.use("player", "player_small")
    p = recorded_comlink.get_player(allycode=855566316)
    mp = compat.to_pydantic(p, MyPlayer)
    assert isinstance(mp, MyPlayer)
    assert mp.name == "Mar Elezra"
    assert mp.ally_code == "855566316"
    assert mp.level > 0


@pytest.mark.skipif(_HAS_PYDANTIC, reason="this test only runs WITHOUT pydantic installed")
def test_to_pydantic_friendly_error_without_extra() -> None:
    """When [pydantic] isn't installed, to_pydantic raises with install hint."""
    from swgoh_comlink import compat

    with pytest.raises(ImportError, match=r"pip install swgoh-comlink\[pydantic\]"):
        # The first arg can be anything; require() raises before touching it.
        compat.to_pydantic(object(), object)  # type: ignore[arg-type]
