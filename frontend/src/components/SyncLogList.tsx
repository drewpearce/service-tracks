import type { SyncLogEntry } from "../types/api";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return "Yesterday";
  return `${diffDay}d ago`;
}

function triggerLabel(trigger: string): string {
  return trigger.charAt(0).toUpperCase() + trigger.slice(1) + " sync";
}

interface SyncLogListProps {
  syncs: SyncLogEntry[];
}

export default function SyncLogList({ syncs }: SyncLogListProps) {
  return (
    <section>
      <div className="flex items-end justify-between mb-6">
        <h2 className="font-display text-3xl font-semibold tracking-tight text-slate-900">
          Recent activity
        </h2>
      </div>

      {syncs.length === 0 ? (
        <div className="rounded-2xl bg-white border border-slate-200 px-6 py-8 text-center">
          <p className="text-[14px] text-slate-400">No syncs yet.</p>
        </div>
      ) : (
        <div className="rounded-2xl bg-white border border-slate-200 divide-y divide-slate-100">
          {syncs.map((sync) => {
            const synced = sync.status === "synced";
            const partial = sync.status === "partial";
            return (
              <div key={sync.id} className="flex items-center justify-between px-6 py-4">
                <div className="flex items-center gap-4">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-widest border ${
                      synced
                        ? "bg-teal-50 border-teal-200 text-teal-700"
                        : partial
                        ? "bg-rose-50 border-rose-200 text-rose-700"
                        : "bg-slate-100 border-slate-200 text-slate-600"
                    }`}
                  >
                    {sync.status.charAt(0).toUpperCase() + sync.status.slice(1)}
                  </span>
                  <span className="text-[14px] text-slate-700">{triggerLabel(sync.sync_trigger)}</span>
                  <span className="font-display text-[14px] font-semibold tabular-nums text-slate-500">
                    {sync.songs_matched}/{sync.songs_total}
                  </span>
                </div>
                <span className="text-[12px] text-slate-500 font-medium">
                  {formatRelativeTime(sync.started_at)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
