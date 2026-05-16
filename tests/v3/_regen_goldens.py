# coding=utf-8
"""Regenerate canonical golden snapshots for the v3 test harness.

Standalone script (not pytest-collected — module name starts with ``_``).
Calls each SDK endpoint method against an in-process mock transport seeded
with the Phase 0 cassettes and writes each post-SDK-transformation result
to ``tests/v3/golden/<name>.json``.

Run with::

    uv run python -m tests.v3._regen_goldens

Use after Phase 0 cassettes are refreshed, or when intentionally changing
SDK behavior (Phase 3 will rewrite the goldens once Structs land — diff
review is the gate).

Implementation note: the regen script uses :class:`httpx.MockTransport`
directly rather than going through ``pytest-httpx``. The transport is a
zero-dependency stdlib of httpx, swapped in at client construction; the
conftest fixtures (which need fixture-scoped behavior) go through
``pytest-httpx`` instead. Both paths produce identical replay semantics.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from tests.v3.conftest import GOLDEN_DIR, load_cassette_bytes

# Goldens we explicitly skip. The SDK is a passthrough for these and the
# cassette already IS the canonical output; test parametrization compares
# against the cassette directly. Skipping avoids ~93 MiB of golden JSON
# in git (data ≈ 80, localization ≈ 5, player_large ≈ 7.5 — the last is
# small enough to commit but a 7.5 MiB diff is unreviewable).
_SKIP_GOLDEN: set[str] = {"data", "localization_eng_us", "player_large"}


def _make_transport(endpoint_to_cassette: dict[str, str]) -> httpx.MockTransport:
    """Mock transport that serves *endpoint_to_cassette* by URL path.

    Unknown endpoints return 404 to surface typos in callers.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path.lstrip("/")
        cassette = endpoint_to_cassette.get(path)
        if cassette is None:
            return httpx.Response(
                404,
                content=json.dumps({"error": f"no cassette for '{path}'"}).encode(),
                headers={"content-type": "application/json"},
            )
        return httpx.Response(
            200,
            content=load_cassette_bytes(cassette),
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(handler)


def _new_client(endpoint_to_cassette: dict[str, str]) -> Any:
    """Construct a :class:`SwgohComlink` whose httpx.Client uses the mock transport.

    Patches ``client.client`` after SDK construction — equivalent to what the
    Phase 0 baseline harness does for the same reason (v2 client builds its
    own httpx.Client internally).
    """
    from swgoh_comlink import SwgohComlink

    transport = _make_transport(endpoint_to_cassette)
    sdk = SwgohComlink(url="http://comlink.test")
    sdk.client.close()
    sdk.client = httpx.Client(base_url=sdk.url_base, transport=transport)
    return sdk


def _write_golden(name: str, payload: Any) -> Path:
    """Write *payload* as pretty-printed JSON to ``golden/<name>.json``."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def _cases() -> list[tuple[str, dict[str, str], Callable[[Any], Any]]]:
    """Per-golden definitions: ``(name, endpoint_mapping, call_lambda)``.

    The endpoint mapping is per-case so ``player_small`` and ``player_large``
    can both bind the same ``/player`` endpoint to different cassettes.
    """
    base = {
        "metadata": "metadata",
        "guild": "guild",
        "getLeaderboard": "leaderboard",
    }
    return [
        ("metadata", base | {}, lambda c: c.get_game_metadata()),
        (
            "player_large",
            base | {"player": "player_large"},
            lambda c: c.get_player(allycode=314927874),
        ),
        (
            "player_small",
            base | {"player": "player_small"},
            lambda c: c.get_player(allycode=855566316),
        ),
        (
            "guild",
            base,
            lambda c: c.get_guild(guild_id="GbsabjvbQESUd8r_qPqdYg"),
        ),
        (
            "leaderboard",
            base,
            lambda c: c.get_leaderboard(leaderboard_type=6, league="kyber", division=1),
        ),
    ]


def _prune_orphans(expected: set[str]) -> int:
    """Remove golden files whose name isn't in *expected*.

    Keeps ``README.md`` and any non-``.json`` file. Called at the start of
    regen so removing a case from :func:`_cases` (or adding one to
    :data:`_SKIP_GOLDEN`) actually deletes the orphaned golden — without
    this, a stale golden would linger and falsely pass tests that didn't
    realize it should be gone.
    """
    if not GOLDEN_DIR.exists():
        return 0
    removed = 0
    repo_root = GOLDEN_DIR.parent.parent.parent
    for path in GOLDEN_DIR.iterdir():
        if path.suffix != ".json":
            continue
        if path.stem in expected:
            continue
        path.unlink()
        sys.stderr.write(f"  pruned  {path.relative_to(repo_root)}  (no longer in case set)\n")
        removed += 1
    return removed


def regenerate() -> int:
    """Drive every case, write the goldens, prune orphans."""
    repo_root = GOLDEN_DIR.parent.parent.parent
    sys.stderr.write(f"Regenerating goldens under {GOLDEN_DIR.relative_to(repo_root)}\n")
    expected = {name for name, _, _ in _cases() if name not in _SKIP_GOLDEN}
    _prune_orphans(expected)

    written = 0
    for name, mapping, call in _cases():
        if name in _SKIP_GOLDEN:
            continue
        client = _new_client(mapping)
        try:
            payload = call(client)
        finally:
            client.close()
        path = _write_golden(name, payload)
        size_kib = path.stat().st_size / 1024
        sys.stderr.write(f"  wrote   {path.relative_to(repo_root)}  ({size_kib:.1f} KiB)\n")
        written += 1
    sys.stderr.write(f"\nWrote {written} golden(s).\n")
    return 0


if __name__ == "__main__":
    sys.exit(regenerate())
