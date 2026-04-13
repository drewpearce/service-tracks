import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiClient, ApiClientError } from "../api/client";
import type { ChurchSettings } from "../types/api";

export default function Settings() {
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [playlistMode, setPlaylistMode] = useState<"shared" | "per_plan">("shared");
  const [nameTemplate, setNameTemplate] = useState("");
  const [descriptionTemplate, setDescriptionTemplate] = useState("");

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    apiClient<ChurchSettings>("/api/settings")
      .then((s) => {
        setPlaylistMode(s.playlist_mode);
        setNameTemplate(s.playlist_name_template);
        setDescriptionTemplate(s.playlist_description_template);
      })
      .catch((err) => {
        if (err instanceof ApiClientError && err.status === 403) {
          setLoadError("Please verify your email to access settings.");
        } else {
          setLoadError("Failed to load settings.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await apiClient<ChurchSettings>("/api/settings", {
        method: "PATCH",
        body: JSON.stringify({
          playlist_mode: playlistMode,
          playlist_name_template: nameTemplate,
          playlist_description_template: descriptionTemplate,
        }),
      });
      setSaveSuccess(true);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSaveError("Failed to save settings. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-sm text-red-600">{loadError}</p>
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      <div className="rounded-lg bg-white p-6 shadow">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Playlist mode */}
          <div>
            <p className="text-sm font-medium text-gray-700">Playlist mode</p>
            <div className="mt-2 space-y-2">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="playlist_mode"
                  value="shared"
                  checked={playlistMode === "shared"}
                  onChange={() => setPlaylistMode("shared")}
                  className="accent-blue-600"
                />
                Shared — one persistent playlist per platform, updated on each sync
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="radio"
                  name="playlist_mode"
                  value="per_plan"
                  checked={playlistMode === "per_plan"}
                  onChange={() => setPlaylistMode("per_plan")}
                  className="accent-blue-600"
                />
                Per service — a separate playlist created for each service plan
              </label>
            </div>
          </div>

          {/* Playlist name template */}
          <div>
            <label
              htmlFor="name-template"
              className="block text-sm font-medium text-gray-700"
            >
              Playlist name template
            </label>
            <input
              id="name-template"
              type="text"
              required
              value={nameTemplate}
              onChange={(e) => setNameTemplate(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-gray-500">
              Available variables: <code>{"{church_name}"}</code>, <code>{"{date}"}</code>,{" "}
              <code>{"{date_iso}"}</code>, <code>{"{title}"}</code>
            </p>
          </div>

          {/* Playlist description template */}
          <div>
            <label
              htmlFor="description-template"
              className="block text-sm font-medium text-gray-700"
            >
              Playlist description template
            </label>
            <textarea
              id="description-template"
              rows={3}
              value={descriptionTemplate}
              onChange={(e) => setDescriptionTemplate(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-gray-500">
              Available variables: <code>{"{church_name}"}</code>, <code>{"{date}"}</code>,{" "}
              <code>{"{date_iso}"}</code>, <code>{"{title}"}</code>
            </p>
          </div>

          {saveError && <p className="text-sm text-red-600">{saveError}</p>}
          {saveSuccess && (
            <p className="text-sm text-green-600">Settings saved.</p>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
        </form>
      </div>
    </div>
  );
}
