import { apiClient, ApiClientError } from "../api/client";
import type { SongMapping } from "../types/api";

interface SongMappingTableProps {
  mappings: SongMapping[];
  onRefresh: () => void;
}

export default function SongMappingTable({ mappings, onRefresh }: SongMappingTableProps) {
  if (mappings.length === 0) {
    return <p className="text-sm text-gray-500">No song mappings yet.</p>;
  }

  async function handleRemove(id: string) {
    if (!window.confirm("Remove this song mapping?")) return;
    try {
      const csrf = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)?.[1] ?? "";
      await apiClient(`/api/songs/mappings/${id}`, {
        method: "DELETE",
        headers: { "X-CSRF-Token": decodeURIComponent(csrf) },
      });
      onRefresh();
    } catch (err) {
      if (err instanceof ApiClientError) {
        alert("Failed to remove mapping. Please try again.");
      }
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-gray-700">PCO Song</th>
            <th className="px-4 py-2 text-left font-medium text-gray-700">Streaming Track</th>
            <th className="px-4 py-2 text-left font-medium text-gray-700">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {mappings.map((m) => (
            <tr key={m.id}>
              <td className="px-4 py-2">
                <p className="font-medium text-gray-900">{m.pco_song_title}</p>
                {m.pco_song_artist && (
                  <p className="text-xs text-gray-500">{m.pco_song_artist}</p>
                )}
              </td>
              <td className="px-4 py-2">
                <p className="font-medium text-gray-900">{m.track_title}</p>
                {m.track_artist && (
                  <p className="text-xs text-gray-500">{m.track_artist}</p>
                )}
              </td>
              <td className="px-4 py-2">
                <button
                  onClick={() => void handleRemove(m.id)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
