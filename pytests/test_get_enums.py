from unittest import TestCase, main
from swgoh_comlink import SwgohComlink


class TestGetEnums(TestCase):
    def test_get_enums(self):
        """
        Test that game enums can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        en = comlink.get_enums()
        self.assertTrue('CombatType' in en.keys())


if __name__ == '__main__':
    main()
