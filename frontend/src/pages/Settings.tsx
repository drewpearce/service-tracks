import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiClient, ApiClientError } from "../api/client";
import { Hero, Input, MonoChip, Textarea } from "../components/ui";
import { useAuth } from "../hooks/authContext";
import type { ChurchSettings } from "../types/api";

const VARIABLES = ["{church_name}", "{date}", "{date_iso}", "{title}"];

export default function Settings() {
  const { church } = useAuth();
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
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="px-10 py-10">
        <div className="rounded-2xl bg-white border border-slate-200 p-6">
          <p className="text-[14px] text-rose-600">{loadError}</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Hero>
        <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
          {church?.name}
        </p>
        <h1 className="font-display text-[40px] leading-[1.05] font-semibold tracking-tight">
          Settings
        </h1>
        <p className="mt-3 max-w-xl text-[14px] text-slate-400">
          Control how ServiceTracks names and structures your playlists.
        </p>
      </Hero>

      <div className="px-10 py-10">
        <div className="max-w-4xl grid grid-cols-4 gap-10">
          {/* Side nav */}
          <aside className="col-span-1">
            <nav className="space-y-1 text-[13px] sticky top-6">
              <a
                href="#playlists"
                className="block px-3 py-2 rounded-lg bg-slate-100 text-slate-900 font-medium"
              >
                Playlists
              </a>
            </nav>
          </aside>

          {/* Form */}
          <div className="col-span-3">
            <form onSubmit={handleSubmit} className="space-y-10">
              {/* Playlist mode */}
              <section id="playlists" className="space-y-4">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500 font-semibold">
                    Playlists
                  </p>
                  <h2 className="mt-1 font-display text-2xl font-semibold tracking-tight text-slate-900">
                    How playlists are structured
                  </h2>
                </div>
                <div className="rounded-2xl bg-white border border-slate-200 divide-y divide-slate-100">
                  <label className="flex items-start gap-4 p-5 cursor-pointer">
                    <input
                      type="radio"
                      name="playlist_mode"
                      value="shared"
                      checked={playlistMode === "shared"}
                      onChange={() => setPlaylistMode("shared")}
                      className="mt-0.5 accent-teal-600"
                    />
                    <div>
                      <p className="text-[14px] font-medium text-slate-900">Shared</p>
                      <p className="text-[13px] text-slate-500">
                        One persistent playlist per platform, updated on each sync.
                      </p>
                    </div>
                  </label>
                  <label className="flex items-start gap-4 p-5 cursor-pointer">
                    <input
                      type="radio"
                      name="playlist_mode"
                      value="per_plan"
                      checked={playlistMode === "per_plan"}
                      onChange={() => setPlaylistMode("per_plan")}
                      className="mt-0.5 accent-teal-600"
                    />
                    <div>
                      <p className="text-[14px] font-medium text-slate-900">Per service</p>
                      <p className="text-[13px] text-slate-500">
                        A separate playlist created for each service plan.
                      </p>
                    </div>
                  </label>
                </div>
              </section>

              {/* Name template */}
              <section className="space-y-4">
                <div>
                  <h3 className="font-display text-xl font-semibold tracking-tight text-slate-900">
                    Playlist name
                  </h3>
                  <p className="mt-0.5 text-[13px] text-slate-500">
                    Template used when ServiceTracks creates or renames a playlist.
                  </p>
                </div>
                <Input
                  type="text"
                  required
                  value={nameTemplate}
                  onChange={(e) => setNameTemplate(e.target.value)}
                  mono
                />
                <div className="flex flex-wrap gap-1.5">
                  {VARIABLES.map((v) => (
                    <MonoChip key={v}>{v}</MonoChip>
                  ))}
                </div>
                {nameTemplate && (
                  <div className="rounded-xl bg-slate-900 text-slate-100 p-4">
                    <p className="text-[10px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-2">
                      Preview
                    </p>
                    <p className="font-display text-lg font-semibold">{nameTemplate}</p>
                  </div>
                )}
              </section>

              {/* Description template */}
              <section className="space-y-4">
                <div>
                  <h3 className="font-display text-xl font-semibold tracking-tight text-slate-900">
                    Playlist description
                  </h3>
                  <p className="mt-0.5 text-[13px] text-slate-500">
                    Appears in the playlist's metadata on Spotify / YouTube Music.
                  </p>
                </div>
                <Textarea
                  rows={3}
                  value={descriptionTemplate}
                  onChange={(e) => setDescriptionTemplate(e.target.value)}
                  mono
                />
                <div className="flex flex-wrap gap-1.5">
                  {VARIABLES.map((v) => (
                    <MonoChip key={v}>{v}</MonoChip>
                  ))}
                </div>
              </section>

              {/* Save bar */}
              <div className="sticky bottom-4 flex items-center justify-between gap-4 rounded-2xl bg-white border border-slate-200 shadow-lg p-4">
                <div className="text-[13px]">
                  {saveSuccess && <span className="text-teal-600 font-medium">Settings saved.</span>}
                  {saveError && <span className="text-rose-600">{saveError}</span>}
                </div>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-full bg-slate-900 text-white px-6 py-2.5 text-[13px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}
