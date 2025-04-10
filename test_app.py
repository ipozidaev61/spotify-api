import unittest
from unittest.mock import patch, MagicMock
from app import app


class SpotifyAppTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.token = "Bearer test_token"

    @patch("requests.get")
    def test_get_saved_tracks_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "items": [
                {"track": {"artists": [{"name": "Artist"}], "name": "Song"}}
            ]
        }

        response = self.client.get("/v1/saved-tracks", headers={"Authorization": self.token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Artist - Song", response.get_json())

    @patch("requests.get")
    @patch("requests.post")
    def test_create_playlist_success(self, mock_post, mock_get):
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"id": "user123"}),
            MagicMock(status_code=200, json=lambda: {
                "tracks": {"items": [{"uri": "spotify:track:123"}]}
            })
        ]
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": "playlist123"}

        response = self.client.post(
            "/v1/create-playlist",
            headers={"Authorization": self.token},
            json={"title": "Test Playlist", "tracks": ["Artist - Song"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tracks added", response.get_data(as_text=True))

    @patch("requests.get")
    @patch("requests.post")
    def test_add_to_existing_playlist_success(self, mock_post, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "tracks": {"items": [{"uri": "spotify:track:123"}]}
        }
        mock_post.return_value.status_code = 201

        response = self.client.post(
            "/v1/add-to-playlist/playlist123",
            headers={"Authorization": self.token},
            json={"tracks": ["Artist - Song"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tracks added", response.get_data(as_text=True))

    def test_create_playlist_missing_data(self):
        response = self.client.post(
            "/v1/create-playlist",
            headers={"Authorization": self.token},
            json={"title": "No tracks"}
        )
        self.assertEqual(response.status_code, 400)

    def test_get_saved_tracks_no_auth(self):
        response = self.client.get("/v1/saved-tracks")
        self.assertEqual(response.status_code, 401)

    @patch("requests.post")
    def test_token_refresh(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "new_access_token"
        }

        response = self.client.post(
            "/v1/token",
            json={
                "client_id": "fake_id",
                "client_secret": "fake_secret",
                "refresh_token": "fake_refresh"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.get_json())


if __name__ == "__main__":
    unittest.main()