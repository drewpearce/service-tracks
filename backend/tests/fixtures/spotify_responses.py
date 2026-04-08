"""Realistic mock Spotify API JSON responses for use in tests."""

SPOTIFY_SEARCH_RESPONSE = {
    "tracks": {
        "items": [
            {
                "uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh",
                "name": "How Great Is Our God",
                "artists": [{"name": "Chris Tomlin"}],
                "album": {
                    "name": "Arriving",
                    "images": [
                        {"url": "https://i.scdn.co/image/abc123", "height": 640, "width": 640},
                        {"url": "https://i.scdn.co/image/abc123_small", "height": 300, "width": 300},
                    ],
                },
                "duration_ms": 253000,
            },
            {
                "uri": "spotify:track:7ouMYWpwJ422jRcDASZB7P",
                "name": "Amazing Grace",
                "artists": [{"name": "John Newton"}, {"name": "Various Artists"}],
                "album": {
                    "name": "Hymns",
                    "images": [
                        {"url": "https://i.scdn.co/image/def456", "height": 640, "width": 640},
                    ],
                },
                "duration_ms": 210000,
            },
        ]
    }
}

SPOTIFY_SEARCH_EMPTY_RESPONSE = {
    "tracks": {
        "items": []
    }
}

SPOTIFY_CREATE_PLAYLIST_RESPONSE = {
    "id": "playlist123",
    "name": "Sunday Morning Worship",
    "external_urls": {
        "spotify": "https://open.spotify.com/playlist/playlist123"
    },
}

SPOTIFY_PLAYLIST_TRACKS_RESPONSE = {
    "items": [
        {"track": {"uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"}},
        {"track": {"uri": "spotify:track:7ouMYWpwJ422jRcDASZB7P"}},
        {"track": None},  # deleted/unavailable track
    ]
}

SPOTIFY_USER_PROFILE_RESPONSE = {
    "id": "churchspotify123",
    "display_name": "Church Spotify Account",
    "email": "church@example.com",
}

SPOTIFY_TOKEN_RESPONSE = {
    "access_token": "new_access_token_abc",
    "refresh_token": "new_refresh_token_xyz",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "playlist-modify-public playlist-modify-private playlist-read-private",
}

SPOTIFY_TOKEN_REFRESH_WITH_NEW_REFRESH = {
    "access_token": "refreshed_access_token_abc",
    "refresh_token": "rotated_refresh_token_xyz",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "playlist-modify-public playlist-modify-private playlist-read-private",
}

SPOTIFY_TOKEN_REFRESH_WITHOUT_NEW_REFRESH = {
    "access_token": "refreshed_access_token_abc",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "playlist-modify-public playlist-modify-private playlist-read-private",
    # Note: no "refresh_token" key — Spotify omits it when using rolling refresh tokens
}

# replace_playlist_tracks returns 201 with a snapshot_id
SPOTIFY_REPLACE_TRACKS_RESPONSE = {
    "snapshot_id": "abc123"
}
