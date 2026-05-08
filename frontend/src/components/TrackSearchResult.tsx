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
  isSuggested?: boolean;
  isPlaying?: boolean;
  onTogglePreview?: (id: string) => void;
}

function spotifyTrackId(trackId: string): string | null {
  // Spotify URIs are "spotify:track:{id}"; legacy cache rows may lack external_url.
  const parts = trackId.split(":");
  return parts.length === 3 && parts[0] === "spotify" && parts[1] === "track" ? parts[2] : null;
}

function externalUrlFor(platform: string, track: TrackSearchResultType): string | null {
  if (track.external_url) return track.external_url;
  if (platform === "spotify") {
    const id = spotifyTrackId(track.track_id);
    return id ? `https://open.spotify.com/track/${id}` : null;
  }
  if (platform === "youtube" && track.track_id) {
    return `https://music.youtube.com/watch?v=${track.track_id}`;
  }
  return null;
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
  isSuggested = false,
  isPlaying = false,
  onTogglePreview,
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
      setTimeout(() => navigate("/songs"), 800);
    } catch (err) {
      if (err instanceof ApiClientError) setError("Failed to save match. Please try again.");
      setSelecting(false);
    }
  }

  const spotifyId = platform === "spotify" ? spotifyTrackId(track.track_id) : null;
  const externalUrl = externalUrlFor(platform, track);
  const showInlinePlay = !!spotifyId;
  const showExternalLink = !showInlinePlay && !!externalUrl;

  return (
    <article
      className={`rounded-2xl bg-white p-4 relative transition-all ${
        isSuggested
          ? "border-2 border-indigo-500"
          : isBestMatch
            ? "border-2 border-teal-500"
            : "border border-slate-200 hover:border-slate-300"
      }`}
    >
      {isSuggested ? (
        <span className="absolute -top-2.5 left-4 inline-flex items-center gap-1 rounded-full bg-indigo-500 text-white text-[10px] font-semibold px-2 py-0.5 uppercase tracking-widest">
          <svg className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Suggested
        </span>
      ) : isBestMatch ? (
        <span className="absolute -top-2.5 left-4 inline-flex items-center gap-1 rounded-full bg-teal-500 text-white text-[10px] font-semibold px-2 py-0.5 uppercase tracking-widest">
          <svg className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Best match
        </span>
      ) : null}

      <div className="flex items-center gap-4">
        <div className="group/art relative h-14 w-14 flex-shrink-0">
          {track.image_url ? (
            <img
              src={track.image_url}
              alt={track.album ?? "Album art"}
              referrerPolicy="no-referrer"
              className="h-14 w-14 rounded-xl object-cover"
            />
          ) : (
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
              <svg className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" />
              </svg>
            </div>
          )}
          {showInlinePlay ? (
            <button
              type="button"
              onClick={() => onTogglePreview?.(track.track_id)}
              aria-label={isPlaying ? "Hide preview" : "Play preview"}
              className={`absolute inset-0 flex items-center justify-center rounded-xl bg-slate-900/55 text-white transition-opacity focus:outline-none focus:ring-2 focus:ring-teal-400 ${
                isPlaying ? "opacity-100" : "opacity-0 group-hover/art:opacity-100 focus:opacity-100"
              }`}
            >
              {isPlaying ? (
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="5" width="4" height="14" rx="1" />
                  <rect x="14" y="5" width="4" height="14" rx="1" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>
          ) : showExternalLink ? (
            <a
              href={externalUrl!}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Open track in new tab"
              className="absolute inset-0 flex items-center justify-center rounded-xl bg-slate-900/55 text-white opacity-0 transition-opacity group-hover/art:opacity-100 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 5v14l11-7z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 4h6v6" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 4l-7 7" />
              </svg>
            </a>
          ) : null}
        </div>

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
      </div>

      {isPlaying && spotifyId && (
        <iframe
          src={`https://open.spotify.com/embed/track/${spotifyId}?utm_source=generator&autoplay=1`}
          title={`Spotify preview: ${track.title}`}
          width="100%"
          height={80}
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          loading="lazy"
          className="mt-3 rounded-xl border-0"
        />
      )}
    </article>
  );
}
