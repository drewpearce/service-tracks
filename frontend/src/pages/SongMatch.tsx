import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import TrackSearchResult from "../components/TrackSearchResult";
import { Hero } from "../components/ui";
import { useDebounce } from "../hooks/useDebounce";
import type { SearchResponse } from "../types/api";

const PLATFORM_LABELS: Record<string, string> = {
  spotify: "Spotify",
  youtube: "YouTube Music",
};

export default function SongMatch() {
  const { pcoSongId } = useParams<{ pcoSongId: string }>();
  const [searchParams] = useSearchParams();
  const title = searchParams.get("title") ?? "";
  const artist = searchParams.get("artist") ?? "";
  const platform = searchParams.get("platform") ?? "spotify";

  const initialQuery = [title, artist].filter(Boolean).join(" ");
  const [query, setQuery] = useState(initialQuery);
  const debouncedQuery = useDebounce(query, 300);

  const [results, setResults] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!debouncedQuery.trim()) {
      queueMicrotask(() => { if (!cancelled) setResults(null); });
      return () => { cancelled = true; };
    }
    queueMicrotask(() => {
      if (cancelled) return;
      setSearching(true);
      setSearchError(null);
      apiClient<SearchResponse>(`/api/songs/search?platform=${platform}&q=${encodeURIComponent(debouncedQuery)}`)
        .then((data) => { if (!cancelled) setResults(data); })
        .catch((err) => { if (!cancelled && err instanceof ApiClientError) setSearchError("Search failed. Please try again."); })
        .finally(() => { if (!cancelled) setSearching(false); });
    });
    return () => { cancelled = true; };
  }, [debouncedQuery, platform]);

  const platformLabel = PLATFORM_LABELS[platform] ?? platform;

  return (
    <>
      <Hero>
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-[12px] text-slate-400 mb-6">
          <Link to={`/songs?platform=${platform}`} className="hover:text-white transition-colors">
            Songs
          </Link>
          <span className="text-slate-600">/</span>
          <Link to={`/songs?platform=${platform}`} className="hover:text-white transition-colors">
            Unmatched
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-slate-300 truncate max-w-xs">{title}</span>
        </nav>

        <h1 className="font-display text-[36px] leading-[1.1] font-semibold tracking-tight">
          Match: <span className="text-teal-400">{title}</span>
        </h1>
        {artist && (
          <p className="mt-2 text-[15px] text-slate-400">{artist}</p>
        )}

        {/* Source card + platform */}
        <div className="mt-6 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-3 rounded-2xl bg-slate-800/60 backdrop-blur border border-slate-700 px-4 py-2.5">
            <span className="inline-flex items-center rounded-full bg-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-300 uppercase tracking-widest">
              From PCO
            </span>
            <span className="text-[13px] font-medium">{title}</span>
            {artist && <span className="text-[12px] text-slate-400">— {artist}</span>}
          </div>

          <div className="inline-flex rounded-full bg-slate-800/60 backdrop-blur border border-slate-700 p-1">
            <span className="rounded-full bg-teal-500 px-4 py-1.5 text-[12px] font-semibold text-white">
              {platformLabel}
            </span>
          </div>
        </div>
      </Hero>

      <div className="px-10 py-8 max-w-4xl">
        {/* Search input */}
        <div className="relative mb-6">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${platformLabel} by title, artist, or album…`}
            className="w-full rounded-full border border-slate-300 bg-white pl-12 pr-6 py-3.5 text-[15px] text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 focus:outline-none transition-colors"
          />
          {results && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <span className="text-[11px] text-slate-500 tabular-nums">
                {results.results.length} result{results.results.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}
        </div>

        {searching && (
          <div className="flex h-16 items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
          </div>
        )}

        {searchError && (
          <p className="text-[13px] text-rose-600 mb-4">{searchError}</p>
        )}

        {!searching && results && (
          results.results.length === 0 ? (
            <div className="rounded-2xl bg-white border border-slate-200 px-6 py-10 text-center">
              <p className="text-[14px] text-slate-400">No results found. Try a different search.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {results.results.length > 0 && (
                <p className="flex items-center gap-2 text-[12px] text-slate-500 mb-3">
                  <svg className="h-3.5 w-3.5 text-teal-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Our best guess is first.
                </p>
              )}
              {results.results.map((track, i) => (
                <TrackSearchResult
                  key={track.track_id}
                  track={track}
                  pcoSongId={pcoSongId ?? ""}
                  pcoSongTitle={title}
                  pcoSongArtist={artist || null}
                  platform={platform}
                  isBestMatch={i === 0}
                />
              ))}
            </div>
          )
        )}
      </div>
    </>
  );
}
