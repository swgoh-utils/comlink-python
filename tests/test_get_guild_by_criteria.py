from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


class TestGetGuildByCriteria(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_guild_by_criteria(self, mock_post):
        """Test that get_guilds_by_criteria() builds correct payload."""
        mock_post.return_value = {"guild": [{"id": "GUILD_001"}]}

        comlink = SwgohComlink()
        criteria = {"minGuildGalacticPower": 490000000}
        result = comlink.get_guilds_by_criteria(search_criteria=criteria)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["searchCriteria"], criteria)
        self.assertEqual(payload["payload"]["filterType"], 5)
        self.assertIn("guild", result)


if __name__ == "__main__":
    main()
