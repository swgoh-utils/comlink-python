from unittest import TestCase, main, mock
from src import swgoh_comlink

class TestGetLocalizationBundle(TestCase):
    @mock.patch('requests.request')
    def test_get_localization_bundle(self, mock_request):
        """
        Test that localization data can be retrieved from game server correctly
        """
        mock_response = mock.Mock(status_code=200)
        mock_response.content.decode.return_value = '{"localizationBundle": ""}'
        mock_request.return_value = mock_response
        comlink = swgoh_comlink.SwgohComlink()
        game_data = comlink.get_localization(id="latest", unzip=False)
        self.assertTrue('localizationBundle' in game_data.keys())


if __name__ == '__main__':
    main()
