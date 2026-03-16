"""Tests for the SwgohComlinkBase class and related utilities in _base.py."""

from __future__ import annotations

import hashlib
import logging
from json import dumps

import pytest

from swgoh_comlink import SwgohComlink
from swgoh_comlink._base import _SENSITIVE_KEYS, SwgohComlinkBase, param_alias, sanitize_url
from swgoh_comlink.exceptions import SwgohComlinkValueError

# ── sanitize_url ─────────────────────────────────────────────────────────


class TestSanitizeUrl:
    def test_strips_trailing_slash(self):
        assert sanitize_url("http://localhost:3000/") == "http://localhost:3000"

    def test_http_url_unchanged(self):
        assert sanitize_url("http://localhost:3000") == "http://localhost:3000"

    def test_https_without_port_gets_443(self):
        assert sanitize_url("https://example.com") == "https://example.com:443"

    def test_https_with_port_unchanged(self):
        assert sanitize_url("https://example.com:8443") == "https://example.com:8443"

    def test_strips_multiple_trailing_slashes(self):
        assert sanitize_url("http://localhost:3000///") == "http://localhost:3000"


# ── param_alias ──────────────────────────────────────────────────────────


class TestParamAlias:
    def test_alias_is_translated(self):
        @param_alias(param="snake_case", alias="camelCase")
        def func(**kwargs):
            return kwargs

        result = func(camelCase="value")
        assert result == {"snake_case": "value"}

    def test_original_param_passes_through(self):
        @param_alias(param="snake_case", alias="camelCase")
        def func(**kwargs):
            return kwargs

        result = func(snake_case="value")
        assert result == {"snake_case": "value"}

    def test_alias_not_present_passes_through(self):
        @param_alias(param="snake_case", alias="camelCase")
        def func(**kwargs):
            return kwargs

        result = func(other="value")
        assert result == {"other": "value"}


# ── SwgohComlinkBase direct instantiation ────────────────────────────────


class TestBaseDirectInstantiation:
    def test_cannot_instantiate_base_directly(self):
        with pytest.raises(TypeError, match="Only subclasses"):
            SwgohComlinkBase()


# ── Constructor ──────────────────────────────────────────────────────────


class TestConstructor:
    def test_host_override(self):
        client = SwgohComlink(host="192.168.1.1", port=4000, stats_port=4223)
        assert client.url_base == "http://192.168.1.1:4000"
        assert client.stats_url_base == "http://192.168.1.1:4223"
        client.close()

    def test_hmac_enabled_with_keys(self):
        client = SwgohComlink(access_key="pub", secret_key="priv")
        assert client.hmac is True
        assert client.access_key == "pub"
        assert client.secret_key == "priv"
        client.close()

    def test_hmac_disabled_without_keys(self):
        client = SwgohComlink()
        assert client.hmac is False
        client.close()

    def test_hmac_from_env(self, monkeypatch):
        monkeypatch.setenv("ACCESS_KEY", "env_pub")
        monkeypatch.setenv("SECRET_KEY", "env_priv")
        client = SwgohComlink()
        assert client.hmac is True
        assert client.access_key == "env_pub"
        assert client.secret_key == "env_priv"
        client.close()

    def test_verify_ssl_default(self):
        client = SwgohComlink()
        assert client.verify_ssl is True
        client.close()

    def test_verify_ssl_false(self):
        client = SwgohComlink(verify_ssl=False)
        assert client.verify_ssl is False
        client.close()


# ── HMAC header construction ─────────────────────────────────────────────


class TestHmacHeaders:
    def test_no_hmac_returns_empty_headers(self):
        client = SwgohComlink()
        headers = client._construct_request_headers("POST", "player", {"payload": {}})
        assert headers == {}
        client.close()

    def test_hmac_returns_auth_headers(self):
        client = SwgohComlink(access_key="mykey", secret_key="mysecret")
        headers = client._construct_request_headers("POST", "player", {"payload": {}})
        assert "Authorization" in headers
        assert "X-Date" in headers
        assert headers["Authorization"].startswith("HMAC-SHA256 Credential=mykey,Signature=")
        client.close()

    def test_hmac_with_no_payload(self):
        client = SwgohComlink(access_key="mykey", secret_key="mysecret")
        headers = client._construct_request_headers("GET", "enums")
        assert "Authorization" in headers
        assert "X-Date" in headers
        client.close()

    def test_hmac_signature_changes_with_endpoint(self):
        client = SwgohComlink(access_key="mykey", secret_key="mysecret")
        h1 = client._construct_request_headers("POST", "player")
        h2 = client._construct_request_headers("POST", "guild")
        sig1 = h1["Authorization"].split("Signature=")[1]
        sig2 = h2["Authorization"].split("Signature=")[1]
        assert sig1 != sig2
        client.close()

    def test_hmac_empty_payload_uses_empty_string(self, monkeypatch):
        """Verify empty payload is serialized as '""' not '{}' for comlink v4 compatibility (#51).

        This test validates the "after" behavior (empty string) matches and the
        "before" behavior (empty dict) would produce a different, incorrect signature.
        """
        import hmac as hmac_mod
        import time

        fixed_time = 1700000000.0
        monkeypatch.setattr(time, "time", lambda: fixed_time)

        client = SwgohComlink(access_key="mykey", secret_key="mysecret")
        headers = client._construct_request_headers("POST", "enums")
        actual_sig = headers["Authorization"].split("Signature=")[1]

        req_time = str(int(fixed_time * 1000))

        def _compute_sig(payload_string: str) -> str:
            hmac_obj = hmac_mod.new(key=b"mysecret", digestmod=hashlib.sha256)
            hmac_obj.update(req_time.encode())
            hmac_obj.update(b"POST")
            hmac_obj.update(b"/enums")
            payload_hash = hashlib.md5(payload_string.encode()).hexdigest()  # noqa: S324
            hmac_obj.update(payload_hash.encode())
            return hmac_obj.hexdigest()

        # "after" — comlink v4: empty body serialized as dumps("")
        expected_sig = _compute_sig(dumps(""))
        assert actual_sig == expected_sig

        # "before" — pre-v4: empty body serialized as dumps({})
        old_sig = _compute_sig(dumps({}))
        assert actual_sig != old_sig
        client.close()


# ── _get_player_payload ──────────────────────────────────────────────────


class TestGetPlayerPayload:
    def test_with_allycode(self):
        payload = SwgohComlinkBase._get_player_payload(allycode=123456789)
        assert payload == {"payload": {"allyCode": "123456789"}, "enums": False}

    def test_with_player_id(self):
        payload = SwgohComlinkBase._get_player_payload(player_id="abc-123")
        assert payload == {"payload": {"playerId": "abc-123"}, "enums": False}

    def test_player_id_takes_precedence(self):
        payload = SwgohComlinkBase._get_player_payload(allycode=123, player_id="abc-123")
        assert "playerId" in payload["payload"]
        assert "allyCode" not in payload["payload"]

    def test_with_enums(self):
        payload = SwgohComlinkBase._get_player_payload(allycode=123456789, enums=True)
        assert payload["enums"] is True

    def test_invalid_allycode_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="9-digit"):
            SwgohComlinkBase._get_player_payload(allycode=12345)

    def test_no_args_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="allycode"):
            SwgohComlinkBase._get_player_payload()


# ── _build_game_data_payload ─────────────────────────────────────────────


class TestBuildGameDataPayload:
    def test_default_payload(self):
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0")
        assert payload == {
            "payload": {
                "version": "1.0",
                "devicePlatform": "Android",
                "includePveUnits": True,
                "requestSegment": 0,
            },
            "enums": False,
        }

    def test_with_items_string(self):
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", items="ALL")
        assert payload["payload"]["items"] == "-1"
        assert "requestSegment" not in payload["payload"]

    def test_with_items_known_constant(self):
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", items="SkillDefinitions")
        assert payload["payload"]["items"] == "4"

    def test_with_items_unknown_string(self):
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", items="nonexistent")
        assert payload["payload"]["items"] == "-1"

    def test_invalid_request_segment_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="request_segment"):
            SwgohComlinkBase._build_game_data_payload(game_version="1.0", request_segment=5)

    def test_negative_request_segment_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="request_segment"):
            SwgohComlinkBase._build_game_data_payload(game_version="1.0", request_segment=-1)

    def test_valid_request_segments(self):
        for seg in range(5):
            payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", request_segment=seg)
            assert payload["payload"]["requestSegment"] == seg

    def test_with_numeric_string_items(self):
        """Numeric strings (e.g. from str(int(IntFlag))) pass through as-is."""
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", items="206196178989")
        assert payload["payload"]["items"] == "206196178989"
        assert "requestSegment" not in payload["payload"]

    def test_with_negative_numeric_string_items(self):
        """Negative numeric strings (e.g. '-1' for ALL) pass through as-is."""
        payload = SwgohComlinkBase._build_game_data_payload(game_version="1.0", items="-1")
        assert payload["payload"]["items"] == "-1"
        assert "requestSegment" not in payload["payload"]


# ── _build_unit_stats_endpoint ───────────────────────────────────────────


class TestBuildUnitStatsEndpoint:
    def test_no_flags_no_language(self):
        assert SwgohComlinkBase._build_unit_stats_endpoint() == "api"

    def test_with_single_flag(self):
        result = SwgohComlinkBase._build_unit_stats_endpoint(flags=["calcGP"])
        assert result == "api?flags=calcGP"

    def test_with_multiple_flags(self):
        result = SwgohComlinkBase._build_unit_stats_endpoint(flags=["calcGP", "onlyGP"])
        assert "flags=calcGP,onlyGP" in result

    def test_with_language_only(self):
        result = SwgohComlinkBase._build_unit_stats_endpoint(language="eng_us")
        assert result == "api?language=eng_us"

    def test_with_flags_and_language(self):
        result = SwgohComlinkBase._build_unit_stats_endpoint(flags=["calcGP"], language="eng_us")
        assert "flags=calcGP" in result
        assert "language=eng_us" in result
        assert result.startswith("api?")

    def test_invalid_flags_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="flags"):
            SwgohComlinkBase._build_unit_stats_endpoint(flags=["invalidFlag"])

    def test_non_list_flags_raises(self):
        with pytest.raises(SwgohComlinkValueError, match="flags"):
            SwgohComlinkBase._build_unit_stats_endpoint(flags="calcGP")


# ── _mask ─────────────────────────────────────────────────────────────────


class TestMask:
    def test_none_returns_none_string(self):
        assert SwgohComlinkBase._mask(None) == "None"

    def test_short_value_fully_hidden(self):
        assert SwgohComlinkBase._mask("abc") == "***"

    def test_exact_visible_length_fully_hidden(self):
        assert SwgohComlinkBase._mask("abcd") == "***"

    def test_longer_value_partially_shown(self):
        assert SwgohComlinkBase._mask("my_secret_key_value") == "my_s***"

    def test_custom_visible_count(self):
        assert SwgohComlinkBase._mask("my_secret_key_value", visible=2) == "my***"


# ── __repr__ ──────────────────────────────────────────────────────────────


class TestRepr:
    def test_repr_masks_keys(self):
        client = SwgohComlink(access_key="public_key_123", secret_key="super_secret_456")
        r = repr(client)
        assert "super_secret_456" not in r
        assert "public_key_123" not in r
        assert "publ***" in r
        assert "supe***" in r
        client.close()

    def test_repr_no_keys(self):
        client = SwgohComlink()
        r = repr(client)
        assert "hmac=False" in r
        assert "access_key='None'" in r
        assert "secret_key='None'" in r
        client.close()

    def test_repr_shows_url(self):
        client = SwgohComlink(url="http://myhost:9000")
        r = repr(client)
        assert "http://myhost:9000" in r
        client.close()


# ── Sensitive key masking in logs ─────────────────────────────────────────


class TestSensitiveKeyMasking:
    def test_sensitive_keys_set_contains_expected(self):
        assert "secret_key" in _SENSITIVE_KEYS
        assert "access_key" in _SENSITIVE_KEYS

    def test_func_debug_logger_masks_sensitive_kwargs(self, caplog):
        from swgoh_comlink.helpers import func_debug_logger

        @func_debug_logger
        def dummy(**kwargs):
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="swgoh_comlink.helpers"):
            dummy(secret_key="top_secret", access_key="pub_key", normal="visible")

        log_output = caplog.text
        assert "top_secret" not in log_output
        assert "pub_key" not in log_output
        assert "visible" in log_output
