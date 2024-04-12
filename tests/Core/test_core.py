import hashlib
import hmac

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync

cl = SwgohComlink()
async_cl = SwgohComlinkAsync()


def test_instance_type():
    assert cl.instance_type == 'SwgohComlink'


def test_is_async():
    assert cl.is_async is False


def test_async_instance_type():
    assert async_cl.instance_type == 'SwgohComlinkAsync'


def test_async_is_async():
    assert async_cl.is_async is True


def test_construct_request_headers():
    base = SwgohComlink(access_key='abcxyz', secret_key='zyxdef')
    headers = base._construct_request_headers(
        endpoint="getEvents",
        payload={})
    assert 'X-Date' in headers.keys()
    assert 'Authorization' in headers.keys()


def test_construct_url_base():
    base_url = cl.construct_url_base("http", "localhost", 8888)
    assert base_url == "http://localhost:8888"


def test_construct_url_base_invalid_protocol():
    with pytest.raises(ValueError):
        cl.construct_url_base("ftp", "localhost", 8888)


def test_construct_url_base_invalid_port():
    with pytest.raises(ValueError):
        cl.construct_url_base("http", "localhost", 88888)


def test_get_player_payload_with_allycode(allycode):
    player_payload = cl._get_player_payload(allycode)
    assert player_payload == {'payload': {'allyCode': str(allycode)}, 'enums': False}


def test_get_player_payload_with_player_id(player_id):
    player_payload = cl._get_player_payload(player_id=player_id)
    assert player_payload == {'payload': {'playerId': str(player_id)}, 'enums': False}


def test_get_player_payload_with_enums_true(player_id):
    player_payload = cl._get_player_payload(player_id=player_id, enums=True)
    assert player_payload == {'payload': {'playerId': str(player_id)}, 'enums': True}


def test_get_player_payload_with_both_allycode_and_player_id(allycode, player_id):
    with pytest.raises(ValueError):
        cl._get_player_payload(allycode=allycode, player_id=player_id, enums=True)


def test_get_player_payload_with_neither_allycode_and_player_id(allycode, player_id):
    with pytest.raises(ValueError):
        cl._get_player_payload()


def test_construct_unit_stats_query_string():
    q_string = cl._construct_unit_stats_query_string(flags=['calcGP', 'gameStyle'])
    assert q_string == '?flags=calcGP,gameStyle&language=eng_us'


def test_construct_unit_stats_query_string_with_unknown_language():
    q_string = cl._construct_unit_stats_query_string(flags=['calcGP', 'gameStyle'], language='unknown')
    assert q_string == '?flags=calcGP,gameStyle&language=eng_us'


def test_construct_unit_stats_query_string_with_invalid_flags_type():
    with pytest.raises(ValueError):
        cl._construct_unit_stats_query_string(flags={'calcGP', 'gameStyle'})


def test_make_game_data_payload():
    payload = cl._make_game_data_payload()
    assert payload == {}


def test_make_guilds_by_name_payload_no_guild_name():
    with pytest.raises(ValueError):
        cl._make_guilds_by_name_payload()


def test_make_guilds_by_criteria_no_criteria():
    with pytest.raises(ValueError):
        cl._make_guilds_by_criteria_payload()


def test_make_get_leaderboards_payload_no_type():
    with pytest.raises(ValueError):
        cl._make_get_leaderboards_payload()


def test_make_get_leaderboards_payload_no_league():
    with pytest.raises(ValueError):
        cl._make_get_leaderboards_payload(lb_type=6, division="3")


def test_make_get_leaderboards_payload_no_division():
    with pytest.raises(ValueError):
        cl._make_get_leaderboards_payload(lb_type=6, league="KYBER")


def test_make_get_leaderboards_payload_no_lb_id():
    with pytest.raises(ValueError):
        cl._make_get_leaderboards_payload(league="KYBER", division="4")


def test_make_get_leaderboards_payload_wrong_lb_id_type():
    with pytest.raises(ValueError):
        cl._make_get_leaderboards_payload(lb_type={}, league="KYBER", division="4")


def test_make_get_guilds_leaderboard_payload_wrong_lb_id_type():
    with pytest.raises(ValueError):
        cl._make_get_guild_leaderboard_payload(lb_id={})


def test_make_get_guilds_leaderboard_payload_no_lb_id():
    with pytest.raises(ValueError):
        cl._make_get_guild_leaderboard_payload()


def test_update_hmac_obj_both_argc_missing():
    with pytest.raises(ValueError):
        cl._update_hmac_obj()


def test_update_hmac_obj_wrong_hmac_type():
    with pytest.raises(ValueError):
        cl._update_hmac_obj(hmac_obj="obj", values=["a", "b"])


def test_update_hmac_obj_wrong_values_type():
    with pytest.raises(ValueError):
        cl._update_hmac_obj(hmac_obj=hmac.new(key="test".encode(), digestmod=hashlib.sha256), values={"a", "b"})


def test_make_guild_payload_no_guild_id():
    with pytest.raises(ValueError):
        cl._make_guild_payload()
