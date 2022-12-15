from unittest import TestCase, main, mock
from src import swgoh_comlink


class TestGetEnums(TestCase):
    @mock.patch('requests.request')
    def test_get_enums(self, mock_request):
        """
        Test that game enums can be retrieved from game server correctly
        """
        mock_response = mock.Mock(status_code=200)
        mock_response.content.decode.return_value = '{"AcceptEncoding": ""}'
        mock_request.return_value = mock_response
        comlink = swgoh_comlink.SwgohComlink()
        en = comlink.get_enums()
        self.assertTrue('AcceptEncoding' in en.keys())


if __name__ == '__main__':
    main()
