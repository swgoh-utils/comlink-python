from unittest import TestCase, main, mock

import requests

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkException


class TestGetEnums(TestCase):
    @mock.patch("requests.request")
    def test_get_enums(self, mock_request):
        """Test that get_enums() makes a GET request via _request() and returns parsed JSON."""
        mock_response = mock.Mock()
        mock_response.content = b'{"CombatType": {"1": "CHARACTER", "2": "SHIP"}}'
        mock_request.return_value = mock_response

        comlink = SwgohComlink()
        result = comlink.get_enums()

        mock_request.assert_called_once_with("GET", "http://localhost:3000/enums", headers={}, verify=True)
        self.assertIn("CombatType", result)

    @mock.patch("requests.request")
    def test_get_enums_with_hmac(self, mock_request):
        """Test that get_enums() applies HMAC authentication when keys are set."""
        mock_response = mock.Mock()
        mock_response.content = b'{"CombatType": {"1": "CHARACTER"}}'
        mock_request.return_value = mock_response

        comlink = SwgohComlink(access_key="test_access", secret_key="test_secret")
        comlink.get_enums()

        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "GET")
        self.assertEqual(call_args[0][1], "http://localhost:3000/enums")
        headers = call_args[1]["headers"]
        self.assertIn("X-Date", headers)
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("HMAC-SHA256 Credential=test_access,Signature="))

    @mock.patch("requests.request")
    def test_get_enums_respects_verify_ssl(self, mock_request):
        """Test that get_enums() passes verify_ssl=False when configured."""
        mock_response = mock.Mock()
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        comlink = SwgohComlink(verify_ssl=False)
        comlink.get_enums()

        mock_request.assert_called_once_with("GET", "http://localhost:3000/enums", headers={}, verify=False)

    @mock.patch("requests.request", side_effect=requests.ConnectionError("Connection refused"))
    def test_get_enums_connection_error(self, mock_request):
        """Test that get_enums() wraps connection errors in SwgohComlinkException."""
        comlink = SwgohComlink()
        with self.assertRaises(SwgohComlinkException):
            comlink.get_enums()

    @mock.patch("requests.request")
    def test_get_enums_no_json_body_for_get(self, mock_request):
        """Test that GET requests do not include a json body."""
        mock_response = mock.Mock()
        mock_response.content = b"{}"
        mock_request.return_value = mock_response

        comlink = SwgohComlink()
        comlink.get_enums()

        call_kwargs = mock_request.call_args[1]
        self.assertNotIn("json", call_kwargs)


if __name__ == "__main__":
    main()
