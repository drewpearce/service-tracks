import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import { Hero, Input, MonoChip, Textarea } from "../components/ui";
import { useAuth } from "../hooks/authContext";
import type { StreamingPlatformSettings, StreamingStatusResponse } from "../types/api";

const VARIABLES = ["{church_name}", "{date}", "{date_iso}", "{title}"];

type Platform = "spotify" | "youtube";
const PLATFORM_LABEL: Record<Platform, string> = {
  spotify: "Spotify",
  youtube: "YouTube Music",
};

interface PlatformForm {
  playlist_mode: "shared" | "per_plan";
  playlist_name_template: string;
  playlist_description_template: string;
}

interface PlatformFormState {
  form: PlatformForm;
  saving: boolean;
  saveError: string | null;
  saveSuccess: boolean;
}

const EMPTY_FORM_STATE: PlatformFormState = {
  form: { playlist_mode: "shared", playlist_name_template: "", playlist_description_template: "" },
  saving: false,
  saveError: null,
  saveSuccess: false,
};

export default function Settings() {
  const { church } = useAuth();
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectedPlatforms, setConnectedPlatforms] = useState<Platform[]>([]);
  const [reauthPlatforms, setReauthPlatforms] = useState<Platform[]>([]);
  const [platformState, setPlatformState] = useState<Record<Platform, PlatformFormState>>({
    spotify: EMPTY_FORM_STATE,
    youtube: EMPTY_FORM_STATE,
  });

  useEffect(() => {
    async function load() {
      try {
        const status = await apiClient<StreamingStatusResponse>("/api/streaming/status");
        const connected = status.connections
          .filter((c) => c.connected && (c.platform === "spotify" || c.platform === "youtube"))
          .map((c) => c.platform as Platform);
        setConnectedPlatforms(connected);

        const needsReauth = status.connections
          .filter((c) => c.status === "needs_reauth" && (c.platform === "spotify" || c.platform === "youtube"))
          .map((c) => c.platform as Platform);
        setReauthPlatforms(needsReauth);

        const results = await Promise.all(
          connected.map((p) => apiClient<StreamingPlatformSettings>(`/api/streaming/${p}/settings`)),
        );
        setPlatformState((prev) => {
          const next = { ...prev };
          results.forEach((r) => {
            const p = r.platform as Platform;
            next[p] = {
              form: {
                playlist_mode: r.playlist_mode,
                playlist_name_template: r.playlist_name_template,
                playlist_description_template: r.playlist_description_template,
              },
              saving: false,
              saveError: null,
              saveSuccess: false,
            };
          });
          return next;
        });
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 403) {
          setLoadError("Please verify your email to access settings.");
        } else {
          setLoadError("Failed to load settings.");
        }
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  function updateForm(platform: Platform, patch: Partial<PlatformForm>) {
    setPlatformState((prev) => ({
      ...prev,
      [platform]: {
        ...prev[platform],
        form: { ...prev[platform].form, ...patch },
        saveSuccess: false,
      },
    }));
  }

  async function handleSubmit(platform: Platform, e: FormEvent) {
    e.preventDefault();
    setPlatformState((prev) => ({
      ...prev,
      [platform]: { ...prev[platform], saving: true, saveError: null, saveSuccess: false },
    }));
    const { form } = platformState[platform];
    try {
      await apiClient<StreamingPlatformSettings>(`/api/streaming/${platform}/settings`, {
        method: "PATCH",
        body: JSON.stringify(form),
      });
      setPlatformState((prev) => ({
        ...prev,
        [platform]: { ...prev[platform], saving: false, saveSuccess: true },
      }));
    } catch {
      setPlatformState((prev) => ({
        ...prev,
        [platform]: {
          ...prev[platform],
          saving: false,
          saveError: "Failed to save settings. Please try again.",
        },
      }));
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
          Control how ServiceTracks names and structures your playlists, per streaming service.
        </p>
      </Hero>

      <div className="px-10 py-10 max-w-4xl space-y-10">
        {reauthPlatforms.length > 0 && (
          <div className="space-y-3">
            {reauthPlatforms.map((p) => (
              <div
                key={p}
                className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[13px] text-amber-800"
              >
                {PLATFORM_LABEL[p]} needs to be reconnected — sign-in expired.{" "}
                <Link to="/setup/streaming" className="underline font-medium">
                  Reconnect
                </Link>
              </div>
            ))}
          </div>
        )}

        {connectedPlatforms.length === 0 && (
          <div className="rounded-2xl bg-white border border-slate-200 p-6">
            <p className="text-[14px] text-slate-700">
              No streaming services connected yet.{" "}
              <a href="/setup/streaming" className="text-teal-600 hover:text-teal-700 underline-offset-2 underline">
                Connect a service
              </a>{" "}
              to configure its playlist settings.
            </p>
          </div>
        )}

        {connectedPlatforms.map((platform) => {
          const state = platformState[platform];
          return (
            <PlatformSettingsCard
              key={platform}
              platform={platform}
              state={state}
              onChange={(patch) => updateForm(platform, patch)}
              onSubmit={(e) => void handleSubmit(platform, e)}
            />
          );
        })}
      </div>
    </>
  );
}

function PlatformSettingsCard({
  platform,
  state,
  onChange,
  onSubmit,
}: {
  platform: Platform;
  state: PlatformFormState;
  onChange: (patch: Partial<PlatformForm>) => void;
  onSubmit: (e: FormEvent) => void;
}) {
  const { form, saving, saveError, saveSuccess } = state;
  const label = PLATFORM_LABEL[platform];

  return (
    <form onSubmit={onSubmit} className="space-y-6 rounded-2xl bg-white border border-slate-200 p-6">
      <header>
        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500 font-semibold">{label}</p>
        <h2 className="mt-1 font-display text-2xl font-semibold tracking-tight text-slate-900">
          Playlist settings
        </h2>
      </header>

      <section className="space-y-3">
        <h3 className="text-[14px] font-medium text-slate-900">How playlists are structured</h3>
        <div className="rounded-2xl border border-slate-200 divide-y divide-slate-100">
          <label className="flex items-start gap-4 p-5 cursor-pointer">
            <input
              type="radio"
              name={`playlist_mode_${platform}`}
              value="shared"
              checked={form.playlist_mode === "shared"}
              onChange={() => onChange({ playlist_mode: "shared" })}
              className="mt-0.5 accent-teal-600"
            />
            <div>
              <p className="text-[14px] font-medium text-slate-900">Shared</p>
              <p className="text-[13px] text-slate-500">
                One persistent playlist on {label}, updated on each sync.
              </p>
            </div>
          </label>
          <label className="flex items-start gap-4 p-5 cursor-pointer">
            <input
              type="radio"
              name={`playlist_mode_${platform}`}
              value="per_plan"
              checked={form.playlist_mode === "per_plan"}
              onChange={() => onChange({ playlist_mode: "per_plan" })}
              className="mt-0.5 accent-teal-600"
            />
            <div>
              <p className="text-[14px] font-medium text-slate-900">Per service</p>
              <p className="text-[13px] text-slate-500">
                A separate playlist created on {label} for each service plan.
              </p>
            </div>
          </label>
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-[14px] font-medium text-slate-900">Playlist name</h3>
          <p className="mt-0.5 text-[13px] text-slate-500">
            Template used when ServiceTracks creates or renames a playlist on {label}.
          </p>
        </div>
        <Input
          type="text"
          required
          value={form.playlist_name_template}
          onChange={(e) => onChange({ playlist_name_template: e.target.value })}
          mono
        />
        <div className="flex flex-wrap gap-1.5">
          {VARIABLES.map((v) => (
            <MonoChip key={v}>{v}</MonoChip>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="text-[14px] font-medium text-slate-900">Playlist description</h3>
          <p className="mt-0.5 text-[13px] text-slate-500">
            Appears in the playlist's metadata on {label}.
          </p>
        </div>
        <Textarea
          rows={3}
          value={form.playlist_description_template}
          onChange={(e) => onChange({ playlist_description_template: e.target.value })}
          mono
        />
        <div className="flex flex-wrap gap-1.5">
          {VARIABLES.map((v) => (
            <MonoChip key={v}>{v}</MonoChip>
          ))}
        </div>
      </section>

      <div className="flex items-center justify-between gap-4 pt-2">
        <div className="text-[13px]">
          {saveSuccess && <span className="text-teal-600 font-medium">Saved.</span>}
          {saveError && <span className="text-rose-600">{saveError}</span>}
        </div>
        <button
          type="submit"
          disabled={saving}
          className="rounded-full bg-slate-900 text-white px-6 py-2.5 text-[13px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          {saving ? "Saving…" : `Save ${label} settings`}
        </button>
      </div>
    </form>
  );
}
