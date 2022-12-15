from unittest import TestCase, main, mock
from src import swgoh_comlink

class TestGetPlayer(TestCase):
    @mock.patch('requests.request')
    def test_get_player(self, mock_request):
        """
        Test that player data can be retrieved from game server correctly
        """
        mock_response = mock.Mock(status_code=200)
        mock_response.content.decode.return_value = '{"name": ""}'
        mock_request.return_value = mock_response
        comlink = swgoh_comlink.SwgohComlink()
        allyCode = 245866537
        p = comlink.get_player(allycode=allyCode)
        self.assertTrue('name' in p.keys())


if __name__ == '__main__':
    main()
