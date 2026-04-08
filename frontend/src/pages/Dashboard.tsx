import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import PlanCard from "../components/PlanCard";
import SetupChecklist from "../components/SetupChecklist";
import SyncLogList from "../components/SyncLogList";
import type { DashboardResponse } from "../types/api";

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Spotify OAuth callback banner
  const [spotifyBanner, setSpotifyBanner] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    const spotify = searchParams.get("spotify");
    if (spotify === "connected") {
      setSpotifyBanner({ type: "success", message: "Spotify connected successfully!" });
      navigate("/dashboard", { replace: true });
    } else if (spotify === "error" || spotify === "denied") {
      setSpotifyBanner({
        type: "error",
        message:
          spotify === "denied"
            ? "Spotify connection was denied."
            : "Failed to connect Spotify. Please try again.",
      });
      navigate("/dashboard", { replace: true });
    }
  }, [searchParams, navigate]);

  // Auto-dismiss banner after 5 seconds
  useEffect(() => {
    if (!spotifyBanner) return;
    const timer = setTimeout(() => setSpotifyBanner(null), 5000);
    return () => clearTimeout(timer);
  }, [spotifyBanner]);

  useEffect(() => {
    apiClient<DashboardResponse>("/api/dashboard")
      .then((d) => setData(d))
      .catch((err) => {
        if (err instanceof ApiClientError) {
          setLoadError("Failed to load dashboard. Please refresh.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-sm text-red-600">{loadError ?? "Could not load dashboard."}</p>
      </div>
    );
  }

  const spotifyConnected = data.streaming_connections.some(
    (c) => c.platform === "spotify" && c.connected
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{data.church_name}</h1>

      {/* Spotify OAuth banner */}
      {spotifyBanner && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            spotifyBanner.type === "success"
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {spotifyBanner.message}
          <button
            onClick={() => setSpotifyBanner(null)}
            className="ml-3 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Setup checklist */}
      <SetupChecklist
        pco_connected={data.pco_connected}
        service_type_selected={data.service_type_selected}
        streaming_connections={data.streaming_connections}
      />

      {/* Unmatched songs alert */}
      {data.unmatched_song_count > 0 && spotifyConnected && (
        <div className="flex items-center gap-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <span>
            {data.unmatched_song_count} song
            {data.unmatched_song_count !== 1 ? "s" : ""} need matching
          </span>
          <Link
            to="/songs"
            className="font-medium underline hover:text-amber-900"
          >
            Match songs
          </Link>
        </div>
      )}

      {/* Upcoming plans */}
      {data.upcoming_plans.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Upcoming plans</h2>
          {data.upcoming_plans.map((plan) => (
            <PlanCard key={plan.pco_plan_id} plan={plan} />
          ))}
        </div>
      )}

      {/* Recent syncs */}
      <SyncLogList syncs={data.recent_syncs} />
    </div>
  );
}
