import type { SyncLogEntry } from "../types/api";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const nowMs = Date.now();
  const diffMs = nowMs - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

interface SyncLogListProps {
  syncs: SyncLogEntry[];
}

export default function SyncLogList({ syncs }: SyncLogListProps) {
  if (syncs.length === 0) {
    return (
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-lg font-semibold text-gray-900">Recent syncs</h2>
        <p className="mt-2 text-sm text-gray-500">No syncs yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="text-lg font-semibold text-gray-900">Recent syncs</h2>
      <ul className="mt-3 divide-y divide-gray-100">
        {syncs.map((sync) => (
          <li key={sync.id} className="flex items-center justify-between py-2 text-sm">
            <div className="flex items-center gap-3">
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  sync.status === "synced"
                    ? "bg-green-100 text-green-700"
                    : sync.status === "partial"
                    ? "bg-amber-100 text-amber-700"
                    : sync.status === "error"
                    ? "bg-red-100 text-red-700"
                    : "bg-gray-100 text-gray-600"
                }`}
              >
                {sync.status}
              </span>
              <span className="capitalize text-gray-600">{sync.sync_trigger}</span>
              <span className="text-gray-500">
                {sync.songs_matched}/{sync.songs_total} matched
              </span>
            </div>
            <span className="text-xs text-gray-400">
              {formatRelativeTime(sync.started_at)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
