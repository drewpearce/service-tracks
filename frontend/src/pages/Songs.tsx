import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import SongMappingTable from "../components/SongMappingTable";
import { Hero } from "../components/ui";
import type { MappingsResponse, StreamingStatusResponse, UnmatchedSongsResponse } from "../types/api";

type Tab = "unmatched" | "mappings";

const PLATFORM_LABELS: Record<string, string> = {
  spotify: "Spotify",
  youtube: "YouTube Music",
};

export default function Songs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const platform = searchParams.get("platform") ?? "spotify";

  const [tab, setTab] = useState<Tab>("unmatched");
  const [connectedPlatforms, setConnectedPlatforms] = useState<string[]>([]);
  const initialPlatform = useRef(platform);
  const [unmatchedData, setUnmatchedData] = useState<UnmatchedSongsResponse | null>(null);
  const [mappingsData, setMappingsData] = useState<MappingsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient<StreamingStatusResponse>("/api/streaming/status")
      .then((s) => {
        const active = s.connections.filter((c) => c.connected).map((c) => c.platform);
        setConnectedPlatforms(active);
        if (active.length > 0 && !active.includes(initialPlatform.current)) {
          setSearchParams({ platform: active[0] }, { replace: true });
        }
      })
      .catch(() => {});
  }, [setSearchParams]);

  async function loadUnmatched(p: string) {
    setLoading(true);
    setError(null);
    try {
      setUnmatchedData(await apiClient<UnmatchedSongsResponse>(`/api/songs/unmatched?platform=${p}`));
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

  async function loadMappings(p: string) {
    setLoading(true);
    setError(null);
    try {
      setMappingsData(await apiClient<MappingsResponse>(`/api/songs/mappings?platform=${p}`));
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
    if (tab === "unmatched") void loadUnmatched(platform);
    else void loadMappings(platform);
  }, [tab, platform]);

  const unmatchedCount = unmatchedData?.unmatched_songs.length ?? 0;
  const mappedCount = mappingsData?.mappings.length ?? 0;

  return (
    <>
      <Hero>
        <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
          Library · {PLATFORM_LABELS[platform] ?? platform}
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
        {/* Tab row + platform selector */}
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

          {connectedPlatforms.length > 1 && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="text-slate-500">Platform:</span>
              <select
                value={platform}
                onChange={(e) => {
                  setError(null);
                  setUnmatchedData(null);
                  setMappingsData(null);
                  setSearchParams({ platform: e.target.value });
                }}
                className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[13px] text-slate-900 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 focus:outline-none"
              >
                {connectedPlatforms.map((p) => (
                  <option key={p} value={p}>{PLATFORM_LABELS[p] ?? p}</option>
                ))}
              </select>
            </div>
          )}
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

        {/* Unmatched */}
        {!loading && !error && tab === "unmatched" && unmatchedData && (
          unmatchedData.unmatched_songs.length === 0 ? (
            <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-teal-50">
                <svg className="h-5 w-5 text-teal-600" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-[14px] font-medium text-slate-900">All songs are matched!</p>
              <p className="mt-1 text-[13px] text-slate-500">Every song in your upcoming plans has a streaming track.</p>
            </div>
          ) : (
            <div className="rounded-2xl bg-white border border-slate-200 overflow-hidden">
              <ul className="divide-y divide-slate-100">
                {unmatchedData.unmatched_songs.map((song) => (
                  <li key={song.pco_song_id} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 transition-colors">
                    <span className="h-2 w-2 rounded-full bg-rose-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-[14px] font-semibold text-slate-900 truncate">{song.title}</p>
                      <p className="text-[12px] text-slate-500">
                        {song.artist && <span>{song.artist}</span>}
                        {song.artist && song.last_used_date && <span className="mx-1.5 text-slate-300">·</span>}
                        {song.last_used_date && <span>Last used {song.last_used_date}</span>}
                      </p>
                    </div>
                    <Link
                      to={`/songs/match/${song.pco_song_id}?title=${encodeURIComponent(song.title)}&artist=${encodeURIComponent(song.artist ?? "")}&platform=${platform}`}
                      className="rounded-full bg-slate-900 text-white px-4 py-1.5 text-[12px] font-semibold hover:bg-slate-800 transition-colors flex-shrink-0"
                    >
                      Match →
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )
        )}

        {/* Mappings */}
        {!loading && !error && tab === "mappings" && mappingsData && (
          <SongMappingTable
            mappings={mappingsData.mappings}
            onRefresh={() => void loadMappings(platform)}
          />
        )}
      </div>
    </>
  );
}
