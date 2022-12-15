from unittest import TestCase, main, mock
from src import swgoh_comlink

class TestGetGameData(TestCase):
    @mock.patch('requests.request')
    def test_get_game_data(self, mock_request):
        """
        Test that game data can be retrieved from game server correctly
        """
        mock_response = mock.Mock(status_code=200)
        mock_response.content.decode.return_value = '{"units": ""}'
        mock_request.return_value = mock_response
        comlink = swgoh_comlink.SwgohComlink()
        game_data = comlink.get_game_data(version="latest", include_pve_units=False, request_segment=4)
        self.assertTrue('units' in game_data.keys())


if __name__ == '__main__':
    main()
