from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkValueError


class TestGetUnitStats(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_unit_stats_with_list(self, mock_post):
        """Test that get_unit_stats() posts to stats endpoint with correct payload."""
        mock_post.return_value = {"stats": {"gp": 12345}}

        comlink = SwgohComlink()
        roster = [{"id": "UNIT_001", "defId": "DARTHMALGUS"}]
        result = comlink.get_unit_stats(roster, flags=["calcGP", "gameStyle"])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs.kwargs.get("url_base") or call_kwargs[1].get("url_base"), "http://localhost:3223")
        self.assertIn("calcGP", call_kwargs.kwargs.get("endpoint") or call_kwargs[1].get("endpoint"))
        self.assertIn("gp", result["stats"])

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_unit_stats_dict_wrapped_as_list(self, mock_post):
        """Test that a dict payload is automatically wrapped in a list."""
        mock_post.return_value = {}

        comlink = SwgohComlink()
        comlink.get_unit_stats({"id": "UNIT_001"})

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertIsInstance(payload, list)

    def test_get_unit_stats_invalid_flags(self):
        """Test that invalid flags raise SwgohComlinkValueError."""
        comlink = SwgohComlink()
        with self.assertRaises(SwgohComlinkValueError):
            comlink.get_unit_stats([{}], flags=["invalidFlag"])


if __name__ == "__main__":
    main()
