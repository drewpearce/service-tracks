import { useEffect, useState } from "react";
import { apiClient, ApiClientError } from "../api/client";
import type { SpotifyAuthorizeResponse, StreamingStatusResponse } from "../types/api";

export default function SetupStreaming() {
  const [statusData, setStatusData] = useState<StreamingStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

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
    setConnecting(true);
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
      setConnecting(false);
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

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Streaming Setup</h1>

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
              disabled={connecting}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {connecting ? "Redirecting…" : "Connect Spotify"}
            </button>
          )}
        </div>
        {connectError && <p className="mt-2 text-sm text-red-600">{connectError}</p>}
      </div>
    </div>
  );
}
