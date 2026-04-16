import { useState } from "react";
import { apiClient, ApiClientError } from "../api/client";
import type { Plan, PlanPlaylist, SyncTriggerResponse } from "../types/api";

interface PlanCardProps {
  plan: Plan;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

export default function PlanCard({ plan }: PlanCardProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [displayPlaylists, setDisplayPlaylists] = useState<PlanPlaylist[] | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [matchedCount, setMatchedCount] = useState<number | null>(null);
  const [unmatchedCount, setUnmatchedCount] = useState<number | null>(null);

  const displayUnmatched = unmatchedCount ?? plan.unmatched_count;
  const displayMatched = matchedCount ?? plan.songs.filter((s) => s.matched).length;
  const status = syncStatus ?? (plan.unmatched_count > 0 ? "partial" : plan.playlists.length > 0 ? "synced" : "pending");

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    setDisplayPlaylists(null);
    try {
      const response = await apiClient<SyncTriggerResponse>(
        `/api/plans/${plan.pco_plan_id}/sync`,
        { method: "POST" }
      );
      setSyncStatus(response.sync_status);
      setMatchedCount(response.songs_matched);
      setUnmatchedCount(response.songs_unmatched);
      setDisplayPlaylists(
        response.platforms.map((p) => ({
          platform: p.platform,
          status: p.sync_status,
          url: p.playlist_url,
          last_synced_at: p.last_synced_at ?? null,
          error_message: p.error_message ?? null,
        }))
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSyncError("Sync failed. Please try again.");
      }
    } finally {
      setSyncing(false);
    }
  }

  const playlists = displayPlaylists ?? plan.playlists;
  const synced = status === "synced";

  // Parse date string "YYYY-MM-DD" in local time
  const [year, month, day] = plan.date.split("-").map(Number);
  const dateObj = new Date(year!, month! - 1, day!);
  const dayName = dateObj.toLocaleDateString("en-US", { weekday: "short" });
  const monthName = dateObj.toLocaleDateString("en-US", { month: "long" });
  const dayNum = dateObj.getDate();

  const lastSyncedAt = playlists
    .map((p) => p.last_synced_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  return (
    <article className="rounded-3xl bg-white border border-slate-200 overflow-hidden hover:shadow-[4px_4px_0_0_rgba(15,23,42,0.9)] hover:-translate-x-0.5 hover:-translate-y-0.5 transition-all">
      <div className="flex">
        {/* Date panel */}
        <div className="flex-shrink-0 w-32 bg-slate-50 flex flex-col items-center justify-center py-8 border-r border-slate-200 relative">
          <span
            className={`absolute top-0 left-0 right-0 h-1 ${synced ? "bg-teal-500" : "bg-rose-500"}`}
          />
          <p className="text-[11px] uppercase tracking-[0.25em] text-slate-500 font-semibold">
            {dayName}
          </p>
          <p className="font-display text-6xl font-semibold leading-none text-slate-900 my-1 tabular-nums">
            {dayNum}
          </p>
          <p className="text-[11px] text-slate-500 font-semibold uppercase tracking-widest">
            {monthName}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest border ${
                    synced
                      ? "bg-teal-50 border-teal-200 text-teal-700"
                      : status === "pending"
                      ? "bg-slate-50 border-slate-200 text-slate-600"
                      : "bg-rose-50 border-rose-200 text-rose-700"
                  }`}
                >
                  {synced ? "Synced" : status === "pending" ? "Not synced" : "Partial"}
                </span>
              </div>
              <h3 className="font-display text-2xl font-semibold tracking-tight text-slate-900">
                {plan.title}
              </h3>
              <p className="mt-1 text-[13px] text-slate-500">
                <span className="tabular-nums font-medium text-slate-900">{plan.songs.length} songs</span>
                {" · "}
                {displayMatched} matched
                {displayUnmatched > 0 && `, ${displayUnmatched} unmatched`}
              </p>
            </div>
            <button
              onClick={() => void handleSync()}
              disabled={syncing}
              className={`rounded-full px-5 py-2.5 text-[13px] font-semibold transition-colors flex-shrink-0 disabled:opacity-50 ${
                synced
                  ? "border border-slate-300 bg-white text-slate-900 hover:border-slate-900 hover:bg-slate-900 hover:text-white"
                  : "bg-slate-900 text-white hover:bg-slate-800"
              }`}
            >
              {syncing ? "Updating…" : "Update playlist ↻"}
            </button>
          </div>

          {/* Song chips */}
          {plan.songs.length > 0 && (
            <ul className="mt-5 flex flex-wrap gap-2">
              {plan.songs.map((song) => (
                <li
                  key={song.pco_song_id}
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-medium border ${
                    song.matched
                      ? "bg-teal-50 border-teal-100 text-slate-900"
                      : "bg-rose-50 border-rose-100 text-rose-700"
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${
                      song.matched ? "bg-teal-500" : "bg-rose-500"
                    }`}
                  />
                  {song.title}
                </li>
              ))}
            </ul>
          )}

          {/* Footer */}
          {(playlists.length > 0 || syncError) && (
            <div className="mt-5 pt-4 border-t border-slate-100 flex items-center gap-4 text-[12px] text-slate-500 flex-wrap">
              {playlists.map((pl) => pl.url ? (
                <span key={pl.platform} className="inline-flex items-center gap-1.5">
                  <span className="h-4 w-4 rounded-full bg-teal-500 flex items-center justify-center">
                    <span className="h-1 w-1 rounded-full bg-white" />
                  </span>
                  <a
                    href={pl.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-slate-900 hover:underline"
                  >
                    Open on {pl.platform === "youtube" ? "YouTube Music" : "Spotify"} ↗
                  </a>
                </span>
              ) : null)}
              {lastSyncedAt && (
                <span>Synced {formatRelativeTime(lastSyncedAt)}</span>
              )}
              {syncError && (
                <span className="text-rose-600">{syncError}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
