from swgoh_comlink import SwgohComlink


def test_get_enums():
    comlink = SwgohComlink()
    en = comlink.get_enums()
    assert "CombatType" in en.keys()
    assert en["CombatType"] == {'CHARACTER': 1, 'CombatType_DEFAULT': 0, 'SHIP': 2}
