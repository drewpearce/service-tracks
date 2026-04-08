import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import TrackSearchResult from "../components/TrackSearchResult";
import { useDebounce } from "../hooks/useDebounce";
import type { SearchResponse } from "../types/api";

export default function SongMatch() {
  const { pcoSongId } = useParams<{ pcoSongId: string }>();
  const [searchParams] = useSearchParams();
  const title = searchParams.get("title") ?? "";
  const artist = searchParams.get("artist") ?? "";

  const initialQuery = [title, artist].filter(Boolean).join(" ");
  const [query, setQuery] = useState(initialQuery);
  const debouncedQuery = useDebounce(query, 300);

  const [results, setResults] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults(null);
      return;
    }
    setSearching(true);
    setSearchError(null);
    apiClient<SearchResponse>(
      `/api/songs/search?platform=spotify&q=${encodeURIComponent(debouncedQuery)}`
    )
      .then((data) => setResults(data))
      .catch((err) => {
        if (err instanceof ApiClientError) {
          setSearchError("Search failed. Please try again.");
        }
      })
      .finally(() => setSearching(false));
  }, [debouncedQuery]);

  return (
    <div className="max-w-xl space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/songs" className="text-sm text-blue-600 hover:underline">
          ← Back to songs
        </Link>
      </div>

      <h1 className="text-xl font-bold text-gray-900">
        Match: <span className="text-gray-700">{title}</span>
        {artist && <span className="text-base font-normal text-gray-500"> — {artist}</span>}
      </h1>

      <div>
        <label htmlFor="search" className="block text-sm font-medium text-gray-700">
          Search Spotify
        </label>
        <input
          id="search"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by title, artist, or album…"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {searching && (
        <div className="flex h-16 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      )}

      {searchError && <p className="text-sm text-red-600">{searchError}</p>}

      {!searching && results && (
        <div className="space-y-2">
          {results.results.length === 0 ? (
            <p className="text-sm text-gray-500">No results found.</p>
          ) : (
            results.results.map((track) => (
              <TrackSearchResult
                key={track.track_id}
                track={track}
                pcoSongId={pcoSongId ?? ""}
                pcoSongTitle={title}
                pcoSongArtist={artist || null}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
