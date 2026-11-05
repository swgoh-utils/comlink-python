"""Holds arriving during a reserved wait must delay admission."""

import asyncio

import pytest

from swgoh_comlink import RetryPolicy, SwgohComlinkAsync, retry


async def test_hold_extensions_during_wait_are_observed(make_comlink, call, httpx_mock, monkeypatch):
    now = [100.0]
    waits = []
    monkeypatch.setattr(retry, "_clock", lambda: now[0])
    client = make_comlink(retry=RetryPolicy(min_interval=1))
    httpx_mock.add_response(json={}, is_reusable=True)
    await call(client, "get_game_metadata")

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds
        if len(waits) <= 2:
            client._hold_endpoint("metadata", False, 5)

    async def async_sleep(seconds):
        sleep(seconds)

    monkeypatch.setattr(retry, "_sleep", sleep)
    monkeypatch.setattr(retry, "_async_sleep", async_sleep)
    # A regression that never re-checks the hold must fail, not hang.
    async with asyncio.timeout(5):
        await call(client, "get_game_metadata")
    assert waits == [1, 5, 5]
    assert len(httpx_mock.get_requests()) == 2


async def test_cancellation_during_extended_hold_releases_slot(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(retry, "_clock", lambda: now[0])
    parked = asyncio.Event()
    async with SwgohComlinkAsync(retry=RetryPolicy(min_interval=1)) as client:
        client._pace_delay("metadata", False)
        calls = 0

        async def sleep(seconds):
            nonlocal calls
            calls += 1
            if calls == 1:
                now[0] += seconds
                client._hold_endpoint("metadata", False, 5)
            else:
                parked.set()
                await asyncio.Event().wait()

        monkeypatch.setattr(retry, "_async_sleep", sleep)
        task = asyncio.create_task(client.get_game_metadata())
        try:
            # Without the re-check the task never parks in a second sleep; fail rather than hang.
            async with asyncio.timeout(5):
                await parked.wait()
        finally:
            task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert client._pace_delay("metadata", False) == 5
