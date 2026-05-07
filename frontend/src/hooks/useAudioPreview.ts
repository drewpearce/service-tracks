import { useCallback, useEffect, useRef, useState } from "react";

export interface AudioPreviewControls {
  playingId: string | null;
  toggle: (id: string, url: string) => void;
  stop: () => void;
}

/**
 * Owns a single shared HTMLAudioElement so only one preview plays at a time
 * across all candidate cards. `toggle(id, url)` starts that preview, pausing
 * any previous one; calling toggle with the currently-playing id pauses it.
 */
export function useAudioPreview(): AudioPreviewControls {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof Audio === "undefined") return;
    const audio = new Audio();
    audioRef.current = audio;
    const handleEnd = () => setPlayingId(null);
    audio.addEventListener("ended", handleEnd);
    return () => {
      audio.removeEventListener("ended", handleEnd);
      audio.pause();
      audioRef.current = null;
    };
  }, []);

  const stop = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    setPlayingId(null);
  }, []);

  const toggle = useCallback((id: string, url: string) => {
    const audio = audioRef.current;
    if (!audio) return;

    if (playingId === id) {
      audio.pause();
      setPlayingId(null);
      return;
    }

    if (audio.src !== url) {
      audio.src = url;
    }
    audio.currentTime = 0;
    void audio.play().then(() => setPlayingId(id)).catch(() => setPlayingId(null));
  }, [playingId]);

  return { playingId, toggle, stop };
}
