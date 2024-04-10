from swgoh_comlink import SwgohComlink


def test_construct_request_headers():
    base = SwgohComlink(access_key='abcxyz', secret_key='zyxdef')
    headers = base._construct_request_headers(
        endpoint="getEvents",
        payload={})
    assert 'X-Date' in headers.keys()
    assert 'Authorization' in headers.keys()


def test_construct_url_base():
    cl = SwgohComlink()
    base_url = cl.construct_url_base("http", "localhost", 8888)
    assert base_url == "http://localhost:8888"


def test_get_player_payload(allycode):
    cl = SwgohComlink()
    player_payload = cl._get_player_payload(allycode)
    assert player_payload == {'payload': {'allyCode': str(allycode)}, 'enums': False}
