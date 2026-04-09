import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import type { MatchRequest, TrackSearchResult as TrackSearchResultType } from "../types/api";

interface TrackSearchResultProps {
  track: TrackSearchResultType;
  pcoSongId: string;
  pcoSongTitle: string;
  pcoSongArtist: string | null;
  platform: string;
}

export default function TrackSearchResult({
  track,
  pcoSongId,
  pcoSongTitle,
  pcoSongArtist,
  platform,
}: TrackSearchResultProps) {
  const navigate = useNavigate();
  const [selecting, setSelecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSelect() {
    setError(null);
    setSelecting(true);
    try {
      const csrf = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] ?? "";
      const body: MatchRequest = {
        pco_song_id: pcoSongId,
        pco_song_title: pcoSongTitle,
        pco_song_artist: pcoSongArtist,
        platform: platform,
        track_id: track.track_id,
        track_title: track.title,
        track_artist: track.artist,
      };
      await apiClient("/api/songs/match", {
        method: "POST",
        headers: { "X-CSRF-Token": decodeURIComponent(csrf) },
        body: JSON.stringify(body),
      });
      setDone(true);
      setTimeout(() => navigate(`/songs?platform=${platform}`), 800);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError("Failed to save match. Please try again.");
      }
      setSelecting(false);
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-lg bg-white p-3 shadow">
      {track.image_url ? (
        <img
          src={track.image_url}
          alt={track.album ?? "Album art"}
          className="h-16 w-16 rounded object-cover"
        />
      ) : (
        <div className="flex h-16 w-16 items-center justify-center rounded bg-gray-100 text-gray-400 text-xs">
          No art
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-gray-900">{track.title}</p>
        <p className="truncate text-xs text-gray-500">{track.artist}</p>
        {track.album && (
          <p className="truncate text-xs text-gray-400">{track.album}</p>
        )}
      </div>
      <div className="flex flex-col items-end gap-1">
        {done ? (
          <span className="text-xs font-medium text-green-600">Matched!</span>
        ) : (
          <button
            onClick={() => void handleSelect()}
            disabled={selecting}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {selecting ? "Saving…" : "Select"}
          </button>
        )}
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    </div>
  );
}
