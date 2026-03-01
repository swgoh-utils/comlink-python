from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


def mocked_get_enums(*args, **kwargs):
    return {
        'CombatType': {
            '1': 'CHARACTER',
            '2': 'SHIP',
        },
    }


class TestGetEnums(TestCase):
    @mock.patch.object(SwgohComlink, 'get_enums', side_effect=mocked_get_enums)
    def test_get_enums(self, mock_get_enums):
        """
        Test that game enums can be retrieved from game server correctly
        """
        comlink = SwgohComlink()
        en = comlink.get_enums()
        self.assertTrue('CombatType' in en.keys())


if __name__ == '__main__':
    main()
