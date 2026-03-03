from __future__ import annotations

import json
from typing import Any

from swgoh_comlink import SwgohComlink


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self.content = json.dumps(payload).encode("utf-8")
        self.status_code = status_code


def test_get_player_posts_expected_payload(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers")
        captured["verify"] = kwargs.get("verify")
        return _FakeResponse({"name": "Test Player"})

    monkeypatch.setattr("requests.request", fake_request)

    client = SwgohComlink(url="http://localhost:3000", verify_ssl=False)
    out = client.get_player(allycode=123456789)

    assert out["name"] == "Test Player"
    assert captured["method"] == "POST"
    assert captured["url"] == "http://localhost:3000/player"
    assert captured["json"] == {"payload": {"allyCode": "123456789"}, "enums": False}
    assert captured["verify"] is False


def test_get_game_data_posts_expected_payload(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers")
        captured["verify"] = kwargs.get("verify")
        return _FakeResponse({"units": []})

    monkeypatch.setattr("requests.request", fake_request)

    client = SwgohComlink(url="http://localhost:3000")
    out = client.get_game_data(
        version="1.2.3",
        include_pve_units=False,
        request_segment=4,
        enums=True,
    )

    assert out == {"units": []}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://localhost:3000/data"
    assert captured["json"] == {
        "payload": {
            "version": "1.2.3",
            "devicePlatform": "Android",
            "includePveUnits": False,
            "requestSegment": 4,
        },
        "enums": True,
    }
    assert captured["verify"] is True


def test_get_guild_unwraps_guild_key(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _FakeResponse({"guild": {"profile": {"name": "Guild Name"}}})

    monkeypatch.setattr("requests.request", fake_request)

    client = SwgohComlink(url="http://localhost:3000")
    out = client.get_guild(guild_id="guild-1", include_recent_guild_activity_info=True)

    assert out == {"profile": {"name": "Guild Name"}}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://localhost:3000/guild"
    assert captured["json"] == {
        "payload": {
            "guildId": "guild-1",
            "includeRecentGuildActivityInfo": True,
        },
        "enums": False,
    }
