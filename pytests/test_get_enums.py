from unittest import TestCase, main

from ..src import swgoh_comlink


class TestGetEnums(TestCase):
    def test_get_enums(self):
        """
        Test that game enums can be retrieved from game server correctly
        """
        comlink = swgoh_comlink.SwgohComlink()
        en = comlink.get_enums()
        self.assertTrue('CombatType' in en.keys())


if __name__ == '__main__':
    main()
