"""Tests for GAC bracket boundary probing and scanning helpers."""

import asyncio

from swgoh_comlink.helpers._gac import (
    _async_find_bracket_boundary,
    _find_bracket_boundary,
)


def _make_probe(boundary: int):
    """Return a probe function that returns True for indices < boundary."""

    def probe(index: int) -> bool:
        return index < boundary

    return probe


def _make_async_probe(boundary: int):
    """Return an async probe function that returns True for indices < boundary."""

    async def probe(index: int) -> bool:
        return index < boundary

    return probe


# ── Sync boundary probing ─────────────────────────────────────────────


class TestFindBracketBoundary:
    def test_typical_league(self):
        """~6250 brackets (50k players / 8 per bracket)."""
        boundary = _find_bracket_boundary(_make_probe(6250))
        assert boundary == 6249

    def test_large_league(self):
        """~18750 brackets (150k players)."""
        boundary = _find_bracket_boundary(_make_probe(18750))
        assert boundary == 18749

    def test_empty(self):
        """Returns -1 when bracket 0 is empty."""
        boundary = _find_bracket_boundary(_make_probe(0))
        assert boundary == -1

    def test_small_league(self):
        """Works for < 1024 brackets (initial probe overshoots immediately)."""
        boundary = _find_bracket_boundary(_make_probe(100))
        assert boundary == 99

    def test_exact_power_of_two(self):
        """Boundary exactly at a power of 2."""
        boundary = _find_bracket_boundary(_make_probe(2048))
        assert boundary == 2047

    def test_one_bracket(self):
        """Single bracket (only index 0 is non-empty)."""
        boundary = _find_bracket_boundary(_make_probe(1))
        assert boundary == 0

    def test_two_brackets(self):
        """Two brackets (indices 0 and 1)."""
        boundary = _find_bracket_boundary(_make_probe(2))
        assert boundary == 1

    def test_custom_initial_step(self):
        """Works with a custom initial step."""
        boundary = _find_bracket_boundary(_make_probe(500), initial_step=64)
        assert boundary == 499

    def test_probe_call_count_is_logarithmic(self):
        """Verify the probe is called O(log n) times, not O(n)."""
        call_count = 0
        n = 6250

        def counting_probe(index: int) -> bool:
            nonlocal call_count
            call_count += 1
            return index < n

        _find_bracket_boundary(counting_probe)
        # Exponential phase: ~log2(6250/1024) + log2(1024) ≈ 13 probes
        # Binary phase: ~13 probes
        # Total should be well under 50
        assert call_count < 50


# ── Async boundary probing ────────────────────────────────────────────


class TestAsyncFindBracketBoundary:
    def test_typical_league(self):
        boundary = asyncio.run(_async_find_bracket_boundary(_make_async_probe(6250)))
        assert boundary == 6249

    def test_empty(self):
        boundary = asyncio.run(_async_find_bracket_boundary(_make_async_probe(0)))
        assert boundary == -1

    def test_small_league(self):
        boundary = asyncio.run(_async_find_bracket_boundary(_make_async_probe(100)))
        assert boundary == 99

    def test_one_bracket(self):
        boundary = asyncio.run(_async_find_bracket_boundary(_make_async_probe(1)))
        assert boundary == 0

    def test_matches_sync(self):
        """Async and sync produce identical results across various sizes."""

        async def _run():
            for n in [0, 1, 2, 50, 500, 6250, 18750]:
                sync_result = _find_bracket_boundary(_make_probe(n))
                async_result = await _async_find_bracket_boundary(_make_async_probe(n))
                assert sync_result == async_result, f"Mismatch for n={n}"

        asyncio.run(_run())
