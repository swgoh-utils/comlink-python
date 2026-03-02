from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


class TestGetPlayerArena(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_arena(self, mock_post):
        """Test that get_player_arena() builds correct payload."""
        mock_post.return_value = {
            "allyCode": "314927874",
            "level": 85,
            "name": "Mar Trepodi",
            "playerRating": {},
            "pvpProfile": [],
        }

        comlink = SwgohComlink()
        p = comlink.get_player_arena(allycode=245866537)

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["allyCode"], "245866537")
        self.assertFalse(payload["payload"]["playerDetailsOnly"])
        self.assertIn("name", p)

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_arena_details_only(self, mock_post):
        """Test that player_details_only is passed through to the payload."""
        mock_post.return_value = {"name": "Test"}

        comlink = SwgohComlink()
        comlink.get_player_arena(allycode=245866537, player_details_only=True)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertTrue(payload["payload"]["playerDetailsOnly"])

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_arena_details_only_alias(self, mock_post):
        """Test that the camelCase alias playerDetailsOnly works via param_alias."""
        mock_post.return_value = {"name": "Test"}

        comlink = SwgohComlink()
        comlink.get_player_arena(allycode=245866537, playerDetailsOnly=True)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertTrue(payload["payload"]["playerDetailsOnly"])

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_player_arena_details_only_alias_false(self, mock_post):
        """Test that passing playerDetailsOnly=False propagates correctly (param_alias fix)."""
        mock_post.return_value = {"name": "Test"}

        comlink = SwgohComlink()
        comlink.get_player_arena(allycode=245866537, playerDetailsOnly=False)

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertFalse(payload["payload"]["playerDetailsOnly"])


if __name__ == "__main__":
    main()
