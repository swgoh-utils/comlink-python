from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


class TestGetGuildByName(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_guild_by_name(self, mock_post):
        """Test that get_guilds_by_name() builds correct payload."""
        mock_post.return_value = {"guild": [{"id": "GUILD_001", "name": "dead"}]}

        comlink = SwgohComlink()
        result = comlink.get_guilds_by_name("dead")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["name"], "dead")
        self.assertEqual(payload["payload"]["filterType"], 4)
        self.assertEqual(call_kwargs.kwargs.get("endpoint") or call_kwargs[1].get("endpoint"), "getGuilds")
        self.assertIn("guild", result)


if __name__ == "__main__":
    main()
