from swgoh_comlink import SwgohComlink


def test_get_events():
    comlink = SwgohComlink()
    en = comlink.get_events()
    assert "gameEvent" in en.keys()
    assert len(en['gameEvent']) > 0
