from unittest import TestCase, main, mock

import requests

from swgoh_comlink import SwgohComlink


class TestGetEnums(TestCase):
    @mock.patch("requests.request")
    def test_get_enums(self, mock_request):
        """Test that get_enums() makes a GET request and returns parsed JSON."""
        mock_response = mock.Mock()
        mock_response.content = b'{"CombatType": {"1": "CHARACTER", "2": "SHIP"}}'
        mock_request.return_value = mock_response

        comlink = SwgohComlink()
        en = comlink.get_enums()

        mock_request.assert_called_once_with("GET", "http://localhost:3000/enums", verify=True)
        self.assertIn("CombatType", en)

    @mock.patch("requests.request", side_effect=requests.ConnectionError("Connection refused"))
    def test_get_enums_connection_error(self, mock_request):
        """Test that get_enums() wraps connection errors in SwgohComlinkException."""
        from swgoh_comlink.exceptions import SwgohComlinkException

        comlink = SwgohComlink()
        with self.assertRaises(SwgohComlinkException):
            comlink.get_enums()


if __name__ == "__main__":
    main()
