import { apiClient, ApiClientError } from "../api/client";
import type { SongMapping } from "../types/api";

interface SongMappingTableProps {
  mappings: SongMapping[];
  onRefresh: () => void;
}

export default function SongMappingTable({ mappings, onRefresh }: SongMappingTableProps) {
  if (mappings.length === 0) {
    return (
      <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
        <p className="text-[14px] text-slate-400">No song mappings yet.</p>
      </div>
    );
  }

  async function handleRemove(id: string) {
    if (!window.confirm("Remove this song mapping?")) return;
    try {
      await apiClient(`/api/songs/mappings/${id}`, { method: "DELETE" });
      onRefresh();
    } catch (err) {
      if (err instanceof ApiClientError) {
        alert("Failed to remove mapping. Please try again.");
      }
    }
  }

  return (
    <div className="rounded-2xl bg-white border border-slate-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-100">
          <thead>
            <tr className="bg-slate-50">
              <th className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                PCO Song
              </th>
              <th className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Streaming Track
              </th>
              <th className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Platform
              </th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {mappings.map((m) => (
              <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-5 py-4">
                  <p className="text-[14px] font-medium text-slate-900">{m.pco_song_title}</p>
                  {m.pco_song_artist && (
                    <p className="text-[12px] text-slate-500">{m.pco_song_artist}</p>
                  )}
                </td>
                <td className="px-5 py-4">
                  <p className="text-[14px] font-medium text-slate-900">{m.track_title}</p>
                  {m.track_artist && (
                    <p className="text-[12px] text-slate-500">{m.track_artist}</p>
                  )}
                </td>
                <td className="px-5 py-4">
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 capitalize">
                    {m.platform === "youtube" ? "YouTube Music" : m.platform}
                  </span>
                </td>
                <td className="px-5 py-4 text-right">
                  <button
                    onClick={() => void handleRemove(m.id)}
                    className="text-[12px] font-medium text-rose-600 hover:text-rose-700"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
