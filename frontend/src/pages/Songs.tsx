import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import SongMappingTable from "../components/SongMappingTable";
import type { MappingsResponse, StreamingStatusResponse, UnmatchedSongsResponse } from "../types/api";

type Tab = "unmatched" | "mappings";

const PLATFORM_LABELS: Record<string, string> = {
  spotify: "Spotify",
  youtube: "YouTube Music",
};

export default function Songs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const platform = searchParams.get("platform") ?? "spotify";

  const [tab, setTab] = useState<Tab>("unmatched");
  const [connectedPlatforms, setConnectedPlatforms] = useState<string[]>([]);
  const initialPlatform = useRef(platform);
  const [unmatchedData, setUnmatchedData] = useState<UnmatchedSongsResponse | null>(null);
  const [mappingsData, setMappingsData] = useState<MappingsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load connected platforms once on mount to populate the platform selector
  useEffect(() => {
    apiClient<StreamingStatusResponse>("/api/streaming/status")
      .then((s) => {
        const active = s.connections
          .filter((c) => c.connected)
          .map((c) => c.platform);
        setConnectedPlatforms(active);
        // If the URL platform isn't connected, default to first connected platform
        if (active.length > 0 && !active.includes(initialPlatform.current)) {
          setSearchParams({ platform: active[0] }, { replace: true });
        }
      })
      .catch(() => {
        // Non-fatal — fall back to default platform
      });
  }, [setSearchParams]);

  async function loadUnmatched(p: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<UnmatchedSongsResponse>(
        `/api/songs/unmatched?platform=${p}`
      );
      setUnmatchedData(data);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setError("Please verify your email to view and match songs.");
      } else {
        setError("Failed to load unmatched songs.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadMappings(p: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient<MappingsResponse>(
        `/api/songs/mappings?platform=${p}`
      );
      setMappingsData(data);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setError("Please verify your email to view song mappings.");
      } else {
        setError("Failed to load song mappings.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (tab === "unmatched") {
      void loadUnmatched(platform);
    } else {
      void loadMappings(platform);
    }
  }, [tab, platform]);

  function handleTabChange(newTab: Tab) {
    setError(null);
    setTab(newTab);
  }

  function handlePlatformChange(p: string) {
    setError(null);
    setUnmatchedData(null);
    setMappingsData(null);
    setSearchParams({ platform: p });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Songs</h1>

        {/* Platform selector — only show when more than one platform is connected */}
        {connectedPlatforms.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Platform:</span>
            <select
              value={platform}
              onChange={(e) => handlePlatformChange(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
            >
              {connectedPlatforms.map((p) => (
                <option key={p} value={p}>
                  {PLATFORM_LABELS[p] ?? p}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200">
        <button
          onClick={() => handleTabChange("unmatched")}
          className={`pb-2 text-sm font-medium ${
            tab === "unmatched"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Unmatched
        </button>
        <button
          onClick={() => handleTabChange("mappings")}
          className={`pb-2 text-sm font-medium ${
            tab === "mappings"
              ? "border-b-2 border-blue-600 text-blue-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          All Mappings
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {/* Unmatched tab content */}
      {!loading && !error && tab === "unmatched" && unmatchedData && (
        <div className="space-y-3">
          {unmatchedData.unmatched_songs.length === 0 ? (
            <div className="rounded-lg bg-white p-6 shadow text-center">
              <p className="text-sm text-gray-500">All songs are matched!</p>
            </div>
          ) : (
            unmatchedData.unmatched_songs.map((song) => (
              <div
                key={song.pco_song_id}
                className="flex items-center justify-between rounded-lg bg-white p-4 shadow"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{song.title}</p>
                  {song.artist && (
                    <p className="text-xs text-gray-500">{song.artist}</p>
                  )}
                  {song.last_used_date && (
                    <p className="text-xs text-gray-400">
                      Last used: {song.last_used_date}
                    </p>
                  )}
                </div>
                <Link
                  to={`/songs/match/${song.pco_song_id}?title=${encodeURIComponent(song.title)}&artist=${encodeURIComponent(song.artist ?? "")}&platform=${platform}`}
                  className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
                >
                  Match
                </Link>
              </div>
            ))
          )}
        </div>
      )}

      {/* Mappings tab content */}
      {!loading && !error && tab === "mappings" && mappingsData && (
        <div className="rounded-lg bg-white p-4 shadow">
          <SongMappingTable
            mappings={mappingsData.mappings}
            onRefresh={() => void loadMappings(platform)}
          />
        </div>
      )}
    </div>
  );
}
