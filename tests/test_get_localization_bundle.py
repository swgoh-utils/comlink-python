from unittest import TestCase, main, mock

from swgoh_comlink import SwgohComlink


class TestGetLocalizationBundle(TestCase):
    @mock.patch.object(SwgohComlink, "_post")
    def test_get_localization_with_id(self, mock_post):
        """Test that get_localization() builds correct payload when localization_id is given."""
        mock_post.return_value = {"localizationBundle": {"en": {}}}

        comlink = SwgohComlink()
        result = comlink.get_localization(localization_id="loc_v1")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["id"], "loc_v1")
        self.assertIn("localizationBundle", result)

    @mock.patch.object(SwgohComlink, "_post")
    def test_get_localization_with_locale(self, mock_post):
        """Test that locale is appended to the localization id."""
        mock_post.return_value = {"localizationBundle": {}}

        comlink = SwgohComlink()
        comlink.get_localization(localization_id="loc_v1", locale="eng_us")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        self.assertEqual(payload["payload"]["id"], "loc_v1:ENG_US")


if __name__ == "__main__":
    main()
