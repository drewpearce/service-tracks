import { useCallback, useState } from "react";

export interface AudioPreviewControls {
  playingId: string | null;
  toggle: (id: string) => void;
  stop: () => void;
}

/**
 * Tracks which candidate's preview is currently playing so only one row's
 * embedded player is mounted at a time. Mounting/unmounting the iframe is
 * what actually starts and stops audio — this hook just owns the single-id
 * coordination state.
 */
export function useAudioPreview(): AudioPreviewControls {
  const [playingId, setPlayingId] = useState<string | null>(null);

  const toggle = useCallback((id: string) => {
    setPlayingId((prev) => (prev === id ? null : id));
  }, []);

  const stop = useCallback(() => setPlayingId(null), []);

  return { playingId, toggle, stop };
}
