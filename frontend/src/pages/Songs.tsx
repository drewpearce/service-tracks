import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import SongCard from "../components/SongCard";
import { Hero } from "../components/ui";
import type { MappingsResponse, StreamingStatusResponse, UnmatchedSongsResponse } from "../types/api";

type Tab = "unmatched" | "mappings";

export default function Songs() {
  const [tab, setTab] = useState<Tab>("unmatched");
  const [connectedPlatforms, setConnectedPlatforms] = useState<string[] | null>(null);
  const [unmatchedData, setUnmatchedData] = useState<UnmatchedSongsResponse | null>(null);
  const [mappingsData, setMappingsData] = useState<MappingsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient<StreamingStatusResponse>("/api/streaming/status")
      .then((s) => {
        setConnectedPlatforms(s.connections.filter((c) => c.connected).map((c) => c.platform));
      })
      .catch(() => setConnectedPlatforms([]));
  }, []);

  async function loadUnmatched() {
    setLoading(true);
    setError(null);
    try {
      setUnmatchedData(await apiClient<UnmatchedSongsResponse>("/api/songs/unmatched"));
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setError("Please verify your email to view and match songs.");
      } else {
        setError("Failed to load unmatched songs.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadMappings() {
    setLoading(true);
    setError(null);
    try {
      setMappingsData(await apiClient<MappingsResponse>("/api/songs/mappings"));
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 403) {
        setError("Please verify your email to view song mappings.");
      } else {
        setError("Failed to load song mappings.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (tab === "unmatched") void loadUnmatched();
    else void loadMappings();
  }, [tab]);

  const unmatchedCount = unmatchedData?.unmatched_songs.length ?? 0;
  const mappedCount = mappingsData?.songs.length ?? 0;
  const noPlatformsConnected = connectedPlatforms !== null && connectedPlatforms.length === 0;

  return (
    <>
      <Hero>
        <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
          Library
        </p>
        <h1 className="font-display text-[40px] leading-[1.05] font-semibold tracking-tight">
          Songs
        </h1>
        {tab === "unmatched" && unmatchedData && (
          <p className="mt-3 text-[15px] text-slate-400">
            {unmatchedCount === 0
              ? "All songs are matched."
              : <><span className="text-white font-semibold">{unmatchedCount} song{unmatchedCount !== 1 ? "s" : ""}</span> still need a match.</>
            }
          </p>
        )}
      </Hero>

      <div className="px-10 py-8 max-w-5xl">
        <div className="flex items-center justify-between mb-6 border-b border-slate-200">
          <div className="flex gap-1">
            {(["unmatched", "mappings"] as Tab[]).map((t) => (
              <button
                key={t}
                onClick={() => { setError(null); setTab(t); }}
                className={`relative px-4 py-3 text-[14px] font-medium transition-colors ${
                  tab === t
                    ? "text-slate-900 font-semibold after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-teal-500"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {t === "unmatched" ? "Unmatched" : "All Mappings"}
                {t === "unmatched" && unmatchedCount > 0 && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-rose-100 text-rose-700 text-[10px] font-semibold px-1.5 py-0.5 tabular-nums">
                    {unmatchedCount}
                  </span>
                )}
                {t === "mappings" && mappedCount > 0 && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-slate-100 text-slate-600 text-[10px] font-semibold px-1.5 py-0.5 tabular-nums">
                    {mappedCount}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-2xl bg-white border border-slate-200 p-6 mb-6">
            <p className="text-[14px] text-rose-600">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
          </div>
        )}

        {!loading && !error && noPlatformsConnected && (
          <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
            <p className="text-[14px] font-medium text-slate-900">No streaming services connected.</p>
            <p className="mt-1 text-[13px] text-slate-500">Connect Spotify or YouTube Music to start matching songs.</p>
            <Link
              to="/settings"
              className="mt-4 inline-block rounded-full bg-slate-900 text-white px-4 py-1.5 text-[12px] font-semibold hover:bg-slate-800 transition-colors"
            >
              Go to Settings →
            </Link>
          </div>
        )}

        {!loading && !error && !noPlatformsConnected && tab === "unmatched" && unmatchedData && (
          unmatchedData.unmatched_songs.length === 0 ? (
            <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-teal-50">
                <svg className="h-5 w-5 text-teal-600" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-[14px] font-medium text-slate-900">All upcoming songs are fully matched!</p>
              <p className="mt-1 text-[13px] text-slate-500">Every song in your upcoming plans has a streaming track on every connected platform.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {unmatchedData.unmatched_songs.map((song) => (
                <SongCard
                  key={song.pco_song_id}
                  song={song}
                  onAfterRemove={() => void loadUnmatched()}
                />
              ))}
            </div>
          )
        )}

        {!loading && !error && !noPlatformsConnected && tab === "mappings" && mappingsData && (
          mappingsData.songs.length === 0 ? (
            <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
              <p className="text-[14px] text-slate-400">No song mappings yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {mappingsData.songs.map((song) => (
                <SongCard
                  key={song.pco_song_id}
                  song={song}
                  onAfterRemove={() => void loadMappings()}
                />
              ))}
            </div>
          )
        )}
      </div>
    </>
  );
}
