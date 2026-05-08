import { Link } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import { platformLabel } from "../lib/platforms";
import type { PlatformMappingState, SongWithPlatforms } from "../types/api";
import { Card } from "./ui";

interface SongCardProps {
  song: SongWithPlatforms;
  onAfterRemove: () => void;
}

export default function SongCard({ song, onAfterRemove }: SongCardProps) {
  const platformKeys = Object.keys(song.platforms);

  return (
    <Card className="p-0 overflow-hidden">
      <div className="px-5 py-4">
        <p className="text-[14px] font-semibold text-slate-900 truncate">{song.title}</p>
        <p className="text-[12px] text-slate-500">
          {song.artist && <span>{song.artist}</span>}
          {song.artist && song.last_used_date && <span className="mx-1.5 text-slate-300">·</span>}
          {song.last_used_date && <span>Last used {song.last_used_date}</span>}
        </p>
      </div>
      <ul className="divide-y divide-slate-100 border-t border-slate-100">
        {platformKeys.map((platform) => (
          <li key={platform}>
            <PlatformRow
              platform={platform}
              state={song.platforms[platform]}
              song={song}
              onAfterRemove={onAfterRemove}
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

interface PlatformRowProps {
  platform: string;
  state: PlatformMappingState;
  song: SongWithPlatforms;
  onAfterRemove: () => void;
}

function PlatformRow({ platform, state, song, onAfterRemove }: PlatformRowProps) {
  if (state.matched) {
    return <MatchedRow platform={platform} state={state} onAfterRemove={onAfterRemove} />;
  }
  return <UnmatchedRow platform={platform} song={song} />;
}

function MatchedRow({
  platform,
  state,
  onAfterRemove,
}: {
  platform: string;
  state: PlatformMappingState;
  onAfterRemove: () => void;
}) {
  async function handleRemove() {
    if (!state.mapping_id) return;
    if (!window.confirm(`Remove the ${platformLabel(platform)} match?`)) return;
    try {
      await apiClient(`/api/songs/mappings/${state.mapping_id}`, { method: "DELETE" });
      onAfterRemove();
    } catch (err) {
      if (err instanceof ApiClientError) {
        alert("Failed to remove mapping. Please try again.");
      }
    }
  }

  return (
    <div className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors">
      <span className="h-2.5 w-2.5 rounded-full bg-teal-500 flex-shrink-0" aria-hidden="true" />
      <span className="text-[12px] font-semibold uppercase tracking-widest text-slate-700 w-24 flex-shrink-0">
        {platformLabel(platform)}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-slate-900 truncate">{state.track_title}</p>
        {state.track_artist && (
          <p className="text-[12px] text-slate-500 truncate">{state.track_artist}</p>
        )}
      </div>
      <button
        onClick={handleRemove}
        className="text-[12px] font-medium text-rose-600 hover:text-rose-700 flex-shrink-0"
      >
        Remove
      </button>
    </div>
  );
}

function UnmatchedRow({ platform, song }: { platform: string; song: SongWithPlatforms }) {
  const matchHref = `/songs/match/${song.pco_song_id}?title=${encodeURIComponent(song.title)}&artist=${encodeURIComponent(
    song.artist ?? "",
  )}&platform=${platform}`;

  return (
    <div className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors">
      <span
        className="h-2.5 w-2.5 rounded-full border border-slate-300 flex-shrink-0"
        aria-hidden="true"
      />
      <span className="text-[12px] font-semibold uppercase tracking-widest text-slate-500 w-24 flex-shrink-0">
        {platformLabel(platform)}
      </span>
      <span className="flex-1 text-[13px] text-slate-400 italic">Not matched yet</span>
      <Link
        to={matchHref}
        className="rounded-full bg-slate-900 text-white px-3.5 py-1.5 text-[12px] font-semibold hover:bg-slate-800 transition-colors flex-shrink-0"
      >
        Match →
      </Link>
    </div>
  );
}
