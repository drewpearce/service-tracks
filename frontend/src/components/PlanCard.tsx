import { useState } from "react";
import { apiClient, ApiClientError } from "../api/client";
import type { Plan, PlatformSyncResult, SyncTriggerResponse } from "../types/api";

interface PlanCardProps {
  plan: Plan;
}

export default function PlanCard({ plan }: PlanCardProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [platformResults, setPlatformResults] = useState<PlatformSyncResult[] | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [matchedCount, setMatchedCount] = useState<number | null>(null);
  const [unmatchedCount, setUnmatchedCount] = useState<number | null>(null);

  const displayUnmatched = unmatchedCount ?? plan.unmatched_count;
  const displayMatched = matchedCount ?? plan.songs.filter((s) => s.matched).length;

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    setPlatformResults(null);
    try {
      const csrf = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] ?? "";
      const response = await apiClient<SyncTriggerResponse>(
        `/api/plans/${plan.pco_plan_id}/sync`,
        {
          method: "POST",
          headers: { "X-CSRF-Token": decodeURIComponent(csrf) },
        }
      );
      setSyncStatus(response.sync_status);
      setMatchedCount(response.songs_matched);
      setUnmatchedCount(response.songs_unmatched);
      setPlatformResults(response.platforms);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSyncError("Sync failed. Please try again.");
      }
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="rounded-lg bg-white p-4 shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500">
            {new Date(plan.date + "T00:00:00").toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            })}
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-gray-900">{plan.title}</h3>
        </div>
        <div className="flex items-center gap-2">
          {syncStatus && (
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                syncStatus === "synced"
                  ? "bg-green-100 text-green-700"
                  : syncStatus === "partial"
                  ? "bg-amber-100 text-amber-700"
                  : syncStatus === "error"
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-700"
              }`}
            >
              {syncStatus}
            </span>
          )}
          <button
            onClick={() => void handleSync()}
            disabled={syncing}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "Updating…" : "Update Playlist"}
          </button>
        </div>
      </div>

      {/* Song list */}
      <ul className="mt-3 space-y-1">
        {plan.songs.map((song) => (
          <li key={song.pco_song_id} className="flex items-center gap-2 text-sm">
            <span
              className={`h-2 w-2 rounded-full ${
                song.matched ? "bg-green-500" : "bg-amber-400"
              }`}
            />
            <span className="text-gray-700">{song.title}</span>
          </li>
        ))}
      </ul>

      {/* Match count summary */}
      <p className="mt-2 text-xs text-gray-500">
        {displayMatched} matched · {displayUnmatched} unmatched
      </p>

      {/* Playlists */}
      {plan.playlists.length > 0 && (
        <div className="mt-3 space-y-1">
          {plan.playlists.map((pl) => (
            <div key={pl.platform} className="text-xs">
              <div className="flex items-center gap-2">
                <span className="capitalize text-gray-500">{pl.platform === "youtube" ? "YouTube Music" : pl.platform}:</span>
                {pl.url ? (
                  <a
                    href={pl.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    Open playlist ↗
                  </a>
                ) : (
                  <span className="text-gray-400">Not yet created</span>
                )}
              </div>
              {pl.last_synced_at && (
                <p className="ml-0 text-gray-400">
                  Last synced {new Date(pl.last_synced_at).toLocaleString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Per-platform sync results */}
      {platformResults && (
        <div className="mt-3 border-t pt-3 space-y-1">
          {platformResults.map((r) => (
            <div key={r.platform} className="text-xs">
              <span className="capitalize font-medium text-gray-700">{r.platform}: </span>
              <span
                className={
                  r.sync_status === "synced"
                    ? "text-green-600"
                    : r.sync_status === "error"
                    ? "text-red-600"
                    : "text-gray-500"
                }
              >
                {r.sync_status}
              </span>
              {r.playlist_url && (
                <>
                  {" · "}
                  <a
                    href={r.playlist_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    View playlist ↗
                  </a>
                </>
              )}
              {r.error_message && (
                <span className="ml-1 text-red-500">({r.error_message})</span>
              )}
            </div>
          ))}
        </div>
      )}

      {syncError && <p className="mt-2 text-xs text-red-600">{syncError}</p>}
    </div>
  );
}
