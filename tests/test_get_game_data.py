from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkValueError


class TestGetGameData(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_game_data_with_version(self, mock_post):
        """Test that get_game_data() builds correct payload when version is given."""
        mock_post.return_value = {"units": [{"id": "UNIT_001"}]}

        comlink = SwgohComlink()
        result = comlink.get_game_data(version="0.33.0:abc", include_pve_units=False, request_segment=4)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["version"], "0.33.0:abc")
        self.assertFalse(payload["payload"]["includePveUnits"])
        self.assertEqual(payload["payload"]["requestSegment"], 4)
        self.assertIn("units", result)

    @mock.patch.object(SwgohComlink, "_post")
    @mock.patch.object(SwgohComlink, "_get_game_version", return_value="0.33.0:auto")
    def test_get_game_data_auto_version(self, mock_version, mock_post):
        """Test that get_game_data() fetches version automatically when not provided."""
        mock_post.return_value = {"units": []}

        comlink = SwgohComlink()
        comlink.get_game_data()

        mock_version.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["version"], "0.33.0:auto")

    def test_get_game_data_invalid_segment(self):
        """Test that invalid request_segment raises SwgohComlinkValueError."""
        comlink = SwgohComlink()
        with self.assertRaises(SwgohComlinkValueError):
            comlink.get_game_data(version="v1", request_segment=5)
        with self.assertRaises(SwgohComlinkValueError):
            comlink.get_game_data(version="v1", request_segment=-1)


if __name__ == "__main__":
    main()
