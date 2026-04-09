import { useEffect, useState } from "react";
import { apiClient, ApiClientError } from "../api/client";
import type {
  SpotifyAuthorizeResponse,
  StreamingStatusResponse,
  YouTubeAuthorizeResponse,
} from "../types/api";

export default function SetupStreaming() {
  const [statusData, setStatusData] = useState<StreamingStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectingSpotify, setConnectingSpotify] = useState(false);
  const [connectingYouTube, setConnectingYouTube] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  // Read OAuth callback query params synchronously at mount (?spotify=connected, ?youtube=connected, etc.)
  // Computed once via useState initializer so it doesn't trigger a setState-in-effect.
  const [oauthBanner] = useState<
    | { kind: "success"; message: string }
    | { kind: "error"; message: string }
    | null
  >(() => {
    if (typeof window === "undefined") return null;
    const params = new URLSearchParams(window.location.search);
    const spotify = params.get("spotify");
    const youtube = params.get("youtube");
    if (spotify === "connected") {
      return { kind: "success", message: "Spotify connected successfully." };
    }
    if (spotify === "error" || spotify === "denied") {
      return { kind: "error", message: "Spotify authorization failed." };
    }
    if (youtube === "connected") {
      return { kind: "success", message: "YouTube Music connected successfully." };
    }
    if (youtube === "error" || youtube === "denied") {
      return { kind: "error", message: "YouTube Music authorization failed." };
    }
    return null;
  });

  useEffect(() => {
    // Clean OAuth query params out of the URL after reading them.
    const params = new URLSearchParams(window.location.search);
    if (params.has("spotify") || params.has("youtube")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    apiClient<StreamingStatusResponse>("/api/streaming/status")
      .then((s) => setStatusData(s))
      .catch((err) => {
        if (err instanceof ApiClientError && err.status === 403) {
          setLoadError("Please verify your email before connecting streaming services.");
        } else {
          setLoadError("Failed to load streaming status.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleConnectSpotify() {
    setConnectError(null);
    setConnectingSpotify(true);
    try {
      const response = await apiClient<SpotifyAuthorizeResponse>(
        "/api/streaming/spotify/authorize"
      );
      window.location.href = response.authorization_url;
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setConnectError("Please verify your email before connecting Spotify.");
      } else {
        setConnectError("Failed to start Spotify authorization. Please try again.");
      }
      setConnectingSpotify(false);
    }
  }

  async function handleConnectYouTube() {
    setConnectError(null);
    setConnectingYouTube(true);
    try {
      const response = await apiClient<YouTubeAuthorizeResponse>(
        "/api/streaming/youtube/authorize"
      );
      window.location.href = response.authorization_url;
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setConnectError("Please verify your email before connecting YouTube Music.");
      } else {
        setConnectError("Failed to start YouTube Music authorization. Please try again.");
      }
      setConnectingYouTube(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-sm text-red-600">{loadError}</p>
      </div>
    );
  }

  const spotifyConnection = statusData?.connections.find(
    (c) => c.platform === "spotify"
  );
  const spotifyConnected = spotifyConnection?.connected ?? false;

  const youtubeConnection = statusData?.connections.find(
    (c) => c.platform === "youtube"
  );
  const youtubeConnected = youtubeConnection?.connected ?? false;

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Streaming Setup</h1>

      {oauthBanner && (
        <div
          className={
            oauthBanner.kind === "success"
              ? "rounded-lg bg-green-50 p-4 text-sm text-green-800"
              : "rounded-lg bg-red-50 p-4 text-sm text-red-800"
          }
        >
          {oauthBanner.message}
        </div>
      )}

      {/* Spotify card */}
      <div className="rounded-lg bg-white p-6 shadow">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Spotify</h2>
            {spotifyConnected && spotifyConnection ? (
              <div className="mt-1 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
                <span className="text-sm text-green-700">
                  Connected as {spotifyConnection.external_user_id}
                </span>
              </div>
            ) : (
              <p className="mt-1 text-sm text-gray-500">
                Connect Spotify to sync playlists automatically.
              </p>
            )}
          </div>
          {!spotifyConnected && (
            <button
              onClick={() => void handleConnectSpotify()}
              disabled={connectingSpotify}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {connectingSpotify ? "Redirecting…" : "Connect Spotify"}
            </button>
          )}
        </div>
      </div>

      {/* YouTube Music card */}
      <div className="rounded-lg bg-white p-6 shadow">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">YouTube Music</h2>
            {youtubeConnected && youtubeConnection ? (
              <div className="mt-1 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
                <span className="text-sm text-green-700">
                  Connected (channel {youtubeConnection.external_user_id})
                </span>
              </div>
            ) : (
              <p className="mt-1 text-sm text-gray-500">
                Connect YouTube Music to sync playlists automatically.
              </p>
            )}
          </div>
          {!youtubeConnected && (
            <button
              onClick={() => void handleConnectYouTube()}
              disabled={connectingYouTube}
              className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {connectingYouTube ? "Redirecting…" : "Connect YouTube Music"}
            </button>
          )}
        </div>
      </div>

      {connectError && <p className="text-sm text-red-600">{connectError}</p>}
    </div>
  );
}
