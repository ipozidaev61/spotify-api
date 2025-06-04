from flask import Flask, request, jsonify
import base64
import requests

app = Flask(__name__)

SPOTIFY_API_BASE = "https://api.spotify.com/v1"


def get_headers(token):
    return {
        "Authorization": f"{token}"
    }
	
def refresh_access_token(client_id, client_secret, refresh_token):
    token_url = "https://accounts.spotify.com/api/token"

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception(f"Failed to refresh token: {response.text}")

    return response.json()

@app.route('/v1/token', methods=['POST'])
def get_token():
    payload = request.get_json()

    client_id = payload.get("client_id")
    client_secret = payload.get("client_secret")
    refresh_token = payload.get("refresh_token")

    if not all([client_id, client_secret, refresh_token]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        token_data = refresh_access_token(client_id, client_secret, refresh_token)
        return jsonify(token_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/v1/saved-tracks', methods=['GET'])
def get_saved_tracks():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Authorization header missing"}), 401

    all_tracks = []
    url = f"{SPOTIFY_API_BASE}/me/tracks?limit=50"
    response = requests.get(url, headers=get_headers(token))
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch saved tracks"}), response.status_code

    data = response.json()
    for item in data['items']:
        track = item['track']
        artist = track['artists'][0]['name']
        title = track['name']
        all_tracks.append(f"{artist} - {title}")

    return jsonify(all_tracks)


@app.route('/v1/playlist', methods=['POST'])
def create_playlist():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Authorization header missing"}), 401

    content = request.get_json()
    if not content or 'tracks' not in content:
        return jsonify({"error": "No tracks provided"}), 400
		
    if 'title' not in content:
        return jsonify({"error": "No title provided"}), 400

    track_list = content['tracks']

    user_resp = requests.get(f"{SPOTIFY_API_BASE}/me", headers=get_headers(token))
    if user_resp.status_code != 200:
        return jsonify({"error": "Failed to get user profile"}), user_resp.status_code
    user_id = user_resp.json()['id']

    create_resp = requests.post(
        f"{SPOTIFY_API_BASE}/users/{user_id}/playlists",
        headers={**get_headers(token), "Content-Type": "application/json"},
        json={"name": content['title'], "public": False}
    )
    if create_resp.status_code != 201:
        return jsonify({"error": "Failed to create playlist"}), create_resp.status_code

    playlist_id = create_resp.json()['id']

    return add_tracks_to_playlist(token, track_list, playlist_id)


@app.route('/v1/playlist/<playlist_id>', methods=['POST'])
def add_to_existing_playlist(playlist_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Authorization header missing"}), 401

    content = request.get_json()
    if not content or 'tracks' not in content:
        return jsonify({"error": "No tracks provided"}), 400

    track_list = content['tracks']
    return add_tracks_to_playlist(token, track_list, playlist_id)


def add_tracks_to_playlist(token, track_list, playlist_id):
    uris = []

    for item in track_list:
        artist, title = map(str.strip, item.split(' - ', 1))
        query = f"{title} artist:{artist}"
        search_resp = requests.get(
            f"{SPOTIFY_API_BASE}/search",
            headers=get_headers(token),
            params={"q": query, "type": "track", "limit": 1}
        )
        if search_resp.status_code != 200:
            continue

        results = search_resp.json().get('tracks', {}).get('items', [])
        if results:
            uris.append(results[0]['uri'])

    if not uris:
        return jsonify({"error": "No tracks found"}), 404

    add_resp = requests.post(
        f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks",
        headers={**get_headers(token), "Content-Type": "application/json"},
        json={"uris": uris}
    )

    if add_resp.status_code != 201:
        return jsonify({"error": "Failed to add tracks"}), add_resp.status_code

    return jsonify({"message": "Tracks added", "playlist_id": playlist_id})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
