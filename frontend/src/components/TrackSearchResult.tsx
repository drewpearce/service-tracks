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
  isBestMatch?: boolean;
}

function formatDuration(ms: number): string {
  const totalSec = Math.round(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export default function TrackSearchResult({
  track,
  pcoSongId,
  pcoSongTitle,
  pcoSongArtist,
  platform,
  isBestMatch = false,
}: TrackSearchResultProps) {
  const navigate = useNavigate();
  const [selecting, setSelecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSelect() {
    setError(null);
    setSelecting(true);
    try {
      const body: MatchRequest = {
        pco_song_id: pcoSongId,
        pco_song_title: pcoSongTitle,
        pco_song_artist: pcoSongArtist,
        platform,
        track_id: track.track_id,
        track_title: track.title,
        track_artist: track.artist,
      };
      await apiClient("/api/songs/match", { method: "POST", body: JSON.stringify(body) });
      setDone(true);
      setTimeout(() => navigate(`/songs?platform=${platform}`), 800);
    } catch (err) {
      if (err instanceof ApiClientError) setError("Failed to save match. Please try again.");
      setSelecting(false);
    }
  }

  return (
    <article
      className={`rounded-2xl bg-white p-4 flex items-center gap-4 relative transition-all ${
        isBestMatch
          ? "border-2 border-teal-500"
          : "border border-slate-200 hover:border-slate-300"
      }`}
    >
      {isBestMatch && (
        <span className="absolute -top-2.5 left-4 inline-flex items-center gap-1 rounded-full bg-teal-500 text-white text-[10px] font-semibold px-2 py-0.5 uppercase tracking-widest">
          <svg className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Best match
        </span>
      )}

      {track.image_url ? (
        <img
          src={track.image_url}
          alt={track.album ?? "Album art"}
          className="h-14 w-14 flex-shrink-0 rounded-xl object-cover"
        />
      ) : (
        <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
          <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" />
          </svg>
        </div>
      )}

      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-semibold text-slate-900 truncate">{track.title}</p>
        <p className="text-[12px] text-slate-500 truncate">{track.artist}</p>
        {track.album && (
          <p className="text-[11px] text-slate-400 truncate">{track.album}</p>
        )}
      </div>

      {track.duration_ms && (
        <span className="text-[12px] text-slate-400 tabular-nums flex-shrink-0">
          {formatDuration(track.duration_ms)}
        </span>
      )}

      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        {done ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 border border-teal-200 px-3 py-1 text-[12px] font-semibold text-teal-700">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            Matched!
          </span>
        ) : (
          <button
            onClick={() => void handleSelect()}
            disabled={selecting}
            className="rounded-full bg-slate-900 text-white px-4 py-1.5 text-[12px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            {selecting ? "Saving…" : "Select"}
          </button>
        )}
        {error && <p className="text-[11px] text-rose-600">{error}</p>}
      </div>
    </article>
  );
}
