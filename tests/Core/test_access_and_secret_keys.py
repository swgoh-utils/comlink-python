from swgoh_comlink import SwgohComlink


def test_access_and_secret_keys(allycode):
    secure_comlink = SwgohComlink(port=3010, access_key="public_access_key", secret_key="private_secret_key")
    player = secure_comlink.get_player(allycode)
    assert 'name' in player.keys()
