from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink
from swgoh_comlink.exceptions import SwgohComlinkValueError


class TestGetPlayer(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_by_allycode(self, mock_post):
        """Test that get_player() builds correct payload for allycode lookup."""
        mock_post.return_value = {"name": "TestPlayer", "allyCode": "245866537", "level": 85}

        comlink = SwgohComlink()
        result = comlink.get_player(allycode=245866537)

        mock_post.assert_called_once_with(
            endpoint="player", payload={"payload": {"allyCode": "245866537"}, "enums": False}
        )
        self.assertEqual(result["name"], "TestPlayer")

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_by_player_id(self, mock_post):
        """Test that get_player() uses playerId when provided."""
        mock_post.return_value = {"name": "TestPlayer"}

        comlink = SwgohComlink()
        comlink.get_player(player_id="abc123")

        mock_post.assert_called_once_with(
            endpoint="player", payload={"payload": {"playerId": "abc123"}, "enums": False}
        )

    def test_get_player_no_identifier(self):
        """Test that get_player() raises when neither allycode nor player_id is given."""
        comlink = SwgohComlink()
        with self.assertRaises(SwgohComlinkValueError):
            comlink.get_player()


if __name__ == "__main__":
    main()
