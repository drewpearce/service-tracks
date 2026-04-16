import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import PlanCard from "../components/PlanCard";
import SetupChecklist from "../components/SetupChecklist";
import SyncLogList from "../components/SyncLogList";
import { Hero } from "../components/ui";
import { useAuth } from "../hooks/authContext";
import type { DashboardResponse } from "../types/api";

function formatRelativeTime(dateString: string): string {
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

function daysUntil(dateStr: string): number {
  const [year, month, day] = dateStr.split("-").map(Number);
  const target = new Date(year!, month! - 1, day!);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86400000);
}

export default function Dashboard() {
  const { logout } = useAuth();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialSpotifyParam = searchParams.get("spotify");
  const computeInitialBanner = (): { type: "success" | "error"; message: string } | null => {
    if (initialSpotifyParam === "connected")
      return { type: "success", message: "Spotify connected successfully!" };
    if (initialSpotifyParam === "error" || initialSpotifyParam === "denied")
      return {
        type: "error",
        message:
          initialSpotifyParam === "denied"
            ? "Spotify connection was denied."
            : "Failed to connect Spotify. Please try again.",
      };
    return null;
  };
  const [spotifyBanner, setSpotifyBanner] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(computeInitialBanner);

  useEffect(() => {
    if (initialSpotifyParam) navigate("/dashboard", { replace: true });
  }, [initialSpotifyParam, navigate]);

  useEffect(() => {
    if (!spotifyBanner) return;
    const timer = setTimeout(() => setSpotifyBanner(null), 5000);
    return () => clearTimeout(timer);
  }, [spotifyBanner]);

  useEffect(() => {
    apiClient<DashboardResponse>("/api/dashboard")
      .then((d) => setData(d))
      .catch((err) => {
        if (err instanceof ApiClientError) setLoadError("Failed to load dashboard. Please refresh.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="px-10 py-10">
        <div className="rounded-2xl bg-white border border-slate-200 p-6">
          <p className="text-[14px] text-rose-600">{loadError ?? "Could not load dashboard."}</p>
        </div>
      </div>
    );
  }

  const spotifyConnected = data.streaming_connections.some(
    (c) => c.platform === "spotify" && c.connected
  );
  const totalMatched = data.upcoming_plans.reduce(
    (sum, p) => sum + p.songs.filter((s) => s.matched).length,
    0
  );
  const lastSync = data.recent_syncs[0];
  const nextPlan = data.upcoming_plans[0];
  const daysAway = nextPlan ? daysUntil(nextPlan.date) : null;

  let eyebrowDate: Date | null = null;
  if (nextPlan) {
    const [y, m, d] = nextPlan.date.split("-").map(Number);
    eyebrowDate = new Date(y!, m! - 1, d!);
  }

  return (
    <>
      <Hero>
        {/* Header row */}
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-2 text-[12px] text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-teal-400" />
            <span>All systems operational</span>
          </div>
          <button
            onClick={() => void logout()}
            className="rounded-full border border-slate-700 px-4 py-1.5 text-[13px] text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            Log out
          </button>
        </div>

        {/* Eyebrow */}
        {eyebrowDate && daysAway !== null && (
          <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-4">
            {eyebrowDate.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
            {" · "}
            {daysAway === 0 ? "Today" : daysAway === 1 ? "Tomorrow" : `${daysAway} days away`}
          </p>
        )}

        {/* Heading */}
        <h1 className="font-display text-[52px] leading-[1.05] font-semibold tracking-tight">
          Good morning,
          <br />
          <span className="text-teal-400">{data.church_name}.</span>
        </h1>

        {/* Subtext */}
        <p className="mt-5 max-w-xl text-[15px] text-slate-400 leading-relaxed">
          {data.upcoming_plans.length > 0 ? (
            <>
              {data.upcoming_plans.length} plan{data.upcoming_plans.length !== 1 ? "s" : ""} on deck
              {data.unmatched_song_count > 0 ? (
                <>, <span className="text-white font-semibold">{data.unmatched_song_count} song{data.unmatched_song_count !== 1 ? "s" : ""}</span> still need matching</>
              ) : (
                <>, all songs matched</>
              )}
              {lastSync ? (
                <>, and your last sync ran clean {formatRelativeTime(lastSync.started_at)}.</>
              ) : (
                "."
              )}
            </>
          ) : (
            "No upcoming plans found. Add service plans in Planning Center."
          )}
        </p>

        {/* Spotify OAuth banner (shown in hero context) */}
        {spotifyBanner && (
          <div
            className={`mt-6 rounded-2xl px-4 py-3 text-[13px] flex items-center gap-3 ${
              spotifyBanner.type === "success"
                ? "bg-teal-900/60 border border-teal-700 text-teal-200"
                : "bg-rose-900/60 border border-rose-700 text-rose-200"
            }`}
          >
            <span className="flex-1">{spotifyBanner.message}</span>
            <button
              onClick={() => setSpotifyBanner(null)}
              className="font-medium underline opacity-80 hover:opacity-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Metrics */}
        <div className="mt-10 grid grid-cols-4 gap-3 max-w-3xl">
          {[
            { label: "Upcoming", value: data.upcoming_plans.length, color: "" },
            { label: "Matched", value: totalMatched, color: "text-teal-400" },
            { label: "Unmatched", value: data.unmatched_song_count, color: data.unmatched_song_count > 0 ? "text-rose-400" : "" },
            { label: "Last sync", value: lastSync ? formatRelativeTime(lastSync.started_at) : "—", color: "" },
          ].map(({ label, value, color }) => (
            <div key={label} className="rounded-2xl bg-slate-800/60 backdrop-blur border border-slate-700 p-4">
              <p className="text-[11px] uppercase tracking-widest text-slate-400 font-medium">{label}</p>
              <p className={`mt-1 font-display text-3xl font-semibold tabular-nums ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      </Hero>

      {/* Content */}
      <div className="px-10 py-10 max-w-5xl space-y-10">
        {/* Setup checklist */}
        <SetupChecklist
          pco_connected={data.pco_connected}
          service_type_selected={data.service_type_selected}
          streaming_connections={data.streaming_connections}
        />

        {/* Unmatched alert */}
        {data.unmatched_song_count > 0 && spotifyConnected && (
          <section className="rounded-2xl bg-rose-50 border border-rose-200 p-5 flex items-center gap-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500 text-white flex-shrink-0">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-display text-xl font-semibold text-rose-700">
                {data.unmatched_song_count} unmatched song{data.unmatched_song_count !== 1 ? "s" : ""}
              </p>
              <p className="text-[13px] text-rose-700/80">
                Match them before Sunday or they'll be skipped in the playlist.
              </p>
            </div>
            <Link
              to="/songs"
              className="rounded-full bg-rose-600 text-white px-5 py-2.5 text-[13px] font-semibold hover:bg-rose-700 transition-colors flex-shrink-0"
            >
              Match now →
            </Link>
          </section>
        )}

        {/* Upcoming plans */}
        {data.upcoming_plans.length > 0 && (
          <section>
            <div className="flex items-end justify-between mb-6">
              <div>
                <p className="text-[11px] uppercase tracking-[0.25em] text-teal-600 font-semibold">
                  This week
                </p>
                <h2 className="mt-1 font-display text-4xl font-semibold tracking-tight text-slate-900">
                  Upcoming plans
                </h2>
              </div>
              <Link
                to="/plans"
                className="text-[13px] font-medium text-slate-500 hover:text-slate-900"
              >
                All plans →
              </Link>
            </div>
            <div className="grid grid-cols-1 gap-5">
              {data.upcoming_plans.map((plan) => (
                <PlanCard key={plan.pco_plan_id} plan={plan} />
              ))}
            </div>
          </section>
        )}

        {/* Recent activity */}
        <SyncLogList syncs={data.recent_syncs} />
      </div>
    </>
  );
}
