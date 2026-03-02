from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


class TestGetMetadata(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_metadata(self, mock_post):
        """Test that get_game_metadata() builds correct payload."""
        mock_post.return_value = {
            "serverVersion": "21.04.0",
            "latestGamedataVersion": "0.33.0:abc",
            "latestLocalizationBundleVersion": "loc_v1",
        }

        comlink = SwgohComlink()
        md = comlink.get_game_metadata()

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs.kwargs.get("endpoint") or call_kwargs[1].get("endpoint"), "metadata")
        self.assertIn("serverVersion", md)

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_metadata_with_client_specs(self, mock_post):
        """Test that client_specs are included in the payload."""
        mock_post.return_value = {"serverVersion": "21.04.0"}

        comlink = SwgohComlink()
        specs = {"platform": "Android", "bundleId": "com.test"}
        comlink.get_game_metadata(client_specs=specs)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertIn("client_specs", payload["payload"])


if __name__ == "__main__":
    main()
