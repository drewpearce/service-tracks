import { useEffect, useState } from "react";
import { apiClient, ApiClientError } from "../api/client";
import { Button, Hero } from "../components/ui";
import type {
  SpotifyAuthorizeResponse,
  StreamingStatusResponse,
  YouTubeAuthorizeResponse,
} from "../types/api";

function SpotifyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.36-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2z" />
    </svg>
  );
}

function YouTubeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zm5.5 12.5L10 17V7l7.5 5.5z" />
    </svg>
  );
}

type Platform = "spotify" | "youtube";
type ConfirmKind = "reset" | "disconnect";

interface ConfirmState {
  platform: Platform;
  kind: ConfirmKind;
}

const PLATFORM_LABEL: Record<Platform, string> = {
  spotify: "Spotify",
  youtube: "YouTube Music",
};

function ConfirmDialog({
  state,
  onCancel,
  onConfirm,
  busy,
}: {
  state: ConfirmState;
  onCancel: () => void;
  onConfirm: () => void;
  busy: boolean;
}) {
  const label = PLATFORM_LABEL[state.platform];
  const isDisconnect = state.kind === "disconnect";
  const title = isDisconnect ? `Disconnect ${label}?` : `Reset ${label}?`;
  const body = isDisconnect
    ? `We'll forget the tokens and playlist IDs for ${label}. Existing playlists on ${label} will stay — you can delete them there if you want. You'll need to reconnect to sync again.`
    : `We'll forget all stored playlist IDs for ${label} and reset its playlist mode, name, and description to the defaults. The connection itself stays. The next sync will create fresh playlists on ${label}.`;
  const confirmLabel = isDisconnect ? "Disconnect" : "Reset";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl border border-slate-200 p-6">
        <h3 id="confirm-dialog-title" className="font-display text-xl font-semibold tracking-tight text-slate-900">
          {title}
        </h3>
        <p className="mt-3 text-[14px] text-slate-600 leading-relaxed">{body}</p>
        <div className="mt-6 flex items-center justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={busy}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function SetupStreaming() {
  const [statusData, setStatusData] = useState<StreamingStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectingSpotify, setConnectingSpotify] = useState(false);
  const [connectingYouTube, setConnectingYouTube] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  const [oauthBanner] = useState<
    { kind: "success"; message: string } | { kind: "error"; message: string } | null
  >(() => {
    if (typeof window === "undefined") return null;
    const params = new URLSearchParams(window.location.search);
    const spotify = params.get("spotify");
    const youtube = params.get("youtube");
    if (spotify === "connected") return { kind: "success", message: "Spotify connected successfully." };
    if (spotify === "error" || spotify === "denied") return { kind: "error", message: "Spotify authorization failed." };
    if (youtube === "connected") return { kind: "success", message: "YouTube Music connected successfully." };
    if (youtube === "error" || youtube === "denied") return { kind: "error", message: "YouTube Music authorization failed." };
    return null;
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has("spotify") || params.has("youtube")) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function loadStatus() {
    try {
      const s = await apiClient<StreamingStatusResponse>("/api/streaming/status");
      setStatusData(s);
      setLoadError(null);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setLoadError("Please verify your email before connecting streaming services.");
      } else {
        setLoadError("Failed to load streaming status.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  async function handleConnectSpotify() {
    setActionError(null);
    setConnectingSpotify(true);
    try {
      const response = await apiClient<SpotifyAuthorizeResponse>("/api/streaming/spotify/authorize");
      window.location.href = response.authorization_url;
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setActionError("Please verify your email before connecting Spotify.");
      } else {
        setActionError("Failed to start Spotify authorization. Please try again.");
      }
      setConnectingSpotify(false);
    }
  }

  async function handleConnectYouTube() {
    setActionError(null);
    setConnectingYouTube(true);
    try {
      const response = await apiClient<YouTubeAuthorizeResponse>("/api/streaming/youtube/authorize");
      window.location.href = response.authorization_url;
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setActionError("Please verify your email before connecting YouTube Music.");
      } else {
        setActionError("Failed to start YouTube Music authorization. Please try again.");
      }
      setConnectingYouTube(false);
    }
  }

  async function handleConfirm() {
    if (!confirm) return;
    setConfirmBusy(true);
    setActionError(null);
    setActionInfo(null);
    try {
      if (confirm.kind === "disconnect") {
        await apiClient(`/api/streaming/${confirm.platform}`, { method: "DELETE" });
        setActionInfo(`${PLATFORM_LABEL[confirm.platform]} disconnected.`);
      } else {
        await apiClient(`/api/streaming/${confirm.platform}/reset`, { method: "POST" });
        setActionInfo(`${PLATFORM_LABEL[confirm.platform]} reset to defaults.`);
      }
      setConfirm(null);
      await loadStatus();
    } catch {
      setActionError(`Failed to ${confirm.kind} ${PLATFORM_LABEL[confirm.platform]}. Please try again.`);
    } finally {
      setConfirmBusy(false);
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

  const spotifyConnection = statusData?.connections.find((c) => c.platform === "spotify");
  const spotifyConnected = spotifyConnection?.connected ?? false;
  const youtubeConnection = statusData?.connections.find((c) => c.platform === "youtube");
  const youtubeConnected = youtubeConnection?.connected ?? false;

  return (
    <>
      <Hero>
        <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
          Setup · Streaming
        </p>
        <h1 className="font-display text-[40px] leading-[1.05] font-semibold tracking-tight">
          Connect streaming services
        </h1>
        <p className="mt-3 max-w-xl text-[14px] text-slate-300 leading-relaxed">
          Connect your streaming accounts so ServiceTracks can create and update playlists automatically.
        </p>
      </Hero>

      <div className="px-10 py-10 max-w-3xl space-y-4">
        {oauthBanner && (
          <div
            className={`rounded-2xl p-4 text-[13px] border ${
              oauthBanner.kind === "success"
                ? "bg-teal-50 border-teal-200 text-teal-700"
                : "bg-rose-50 border-rose-200 text-rose-700"
            }`}
          >
            {oauthBanner.message}
          </div>
        )}
        {actionInfo && (
          <div className="rounded-2xl p-4 text-[13px] border bg-teal-50 border-teal-200 text-teal-700">
            {actionInfo}
          </div>
        )}
        {actionError && (
          <div className="rounded-2xl p-4 text-[13px] border bg-rose-50 border-rose-200 text-rose-700">
            {actionError}
          </div>
        )}

        {/* Spotify */}
        <article className="rounded-2xl bg-white border border-slate-200 p-6">
          <div className="flex items-start gap-5">
            <div className="flex-shrink-0 h-14 w-14 rounded-2xl bg-teal-500 flex items-center justify-center">
              <SpotifyIcon className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-xl font-semibold tracking-tight text-slate-900">
                    Spotify
                  </h2>
                  {spotifyConnected && spotifyConnection ? (
                    <div className="mt-1 flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />
                      <span className="text-[13px] text-teal-600 font-medium">
                        Connected as {spotifyConnection.external_user_id}
                      </span>
                    </div>
                  ) : (
                    <p className="mt-1 text-[13px] text-slate-500">
                      Connect Spotify to sync playlists automatically.
                    </p>
                  )}
                </div>
                <button
                  onClick={() => void handleConnectSpotify()}
                  disabled={connectingSpotify}
                  className={`rounded-full px-5 py-2.5 text-[13px] font-semibold transition-colors flex-shrink-0 disabled:opacity-50 ${
                    spotifyConnected
                      ? "border border-slate-300 text-slate-700 hover:border-slate-900 hover:bg-slate-900 hover:text-white"
                      : "bg-slate-900 text-white hover:bg-slate-800"
                  }`}
                >
                  {connectingSpotify ? "Redirecting…" : spotifyConnected ? "Reconnect" : "Connect Spotify"}
                </button>
              </div>
              {spotifyConnected && (
                <div className="mt-4 flex items-center gap-3">
                  <button
                    onClick={() => setConfirm({ platform: "spotify", kind: "reset" })}
                    className="text-[12px] font-medium text-slate-600 hover:text-slate-900 underline-offset-2 hover:underline"
                  >
                    Reset settings
                  </button>
                  <span className="text-slate-300">·</span>
                  <button
                    onClick={() => setConfirm({ platform: "spotify", kind: "disconnect" })}
                    className="text-[12px] font-medium text-rose-600 hover:text-rose-700 underline-offset-2 hover:underline"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          </div>
        </article>

        {/* YouTube Music */}
        <article className="rounded-2xl bg-white border border-slate-200 p-6">
          <div className="flex items-start gap-5">
            <div className="flex-shrink-0 h-14 w-14 rounded-2xl bg-rose-500 flex items-center justify-center">
              <YouTubeIcon className="h-8 w-8 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-display text-xl font-semibold tracking-tight text-slate-900">
                    YouTube Music
                  </h2>
                  {youtubeConnected && youtubeConnection ? (
                    <div className="mt-1 flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />
                      <span className="text-[13px] text-teal-600 font-medium">
                        Connected · channel {youtubeConnection.external_user_id}
                      </span>
                    </div>
                  ) : (
                    <p className="mt-1 text-[13px] text-slate-500">
                      Connect YouTube Music to sync playlists automatically.
                    </p>
                  )}
                </div>
                <button
                  onClick={() => void handleConnectYouTube()}
                  disabled={connectingYouTube}
                  className={`rounded-full px-5 py-2.5 text-[13px] font-semibold transition-colors flex-shrink-0 disabled:opacity-50 ${
                    youtubeConnected
                      ? "border border-slate-300 text-slate-700 hover:border-slate-900 hover:bg-slate-900 hover:text-white"
                      : "bg-slate-900 text-white hover:bg-slate-800"
                  }`}
                >
                  {connectingYouTube ? "Redirecting…" : youtubeConnected ? "Reconnect" : "Connect YouTube Music"}
                </button>
              </div>
              {youtubeConnected && (
                <div className="mt-4 flex items-center gap-3">
                  <button
                    onClick={() => setConfirm({ platform: "youtube", kind: "reset" })}
                    className="text-[12px] font-medium text-slate-600 hover:text-slate-900 underline-offset-2 hover:underline"
                  >
                    Reset settings
                  </button>
                  <span className="text-slate-300">·</span>
                  <button
                    onClick={() => setConfirm({ platform: "youtube", kind: "disconnect" })}
                    className="text-[12px] font-medium text-rose-600 hover:text-rose-700 underline-offset-2 hover:underline"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          </div>
        </article>
      </div>

      {confirm && (
        <ConfirmDialog
          state={confirm}
          onCancel={() => (confirmBusy ? null : setConfirm(null))}
          onConfirm={() => void handleConfirm()}
          busy={confirmBusy}
        />
      )}
    </>
  );
}
