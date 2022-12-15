from unittest import TestCase, main, mock
from src import swgoh_comlink

class TestGetMetadata(TestCase):
    @mock.patch('requests.request')
    def test_get_metadata(self, mock_request):
        """
        Test that game metadata can be retrieved from game server correctly
        """
        mock_response = mock.Mock(status_code=200)
        mock_response.content.decode.return_value = '{"serverVersion": ""}'
        mock_request.return_value = mock_response
        comlink = swgoh_comlink.SwgohComlink()
        md = comlink.get_game_metadata()
        self.assertTrue('serverVersion' in md.keys())


if __name__ == '__main__':
    main()
