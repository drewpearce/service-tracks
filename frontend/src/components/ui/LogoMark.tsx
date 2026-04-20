interface LogoMarkProps {
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "h-6 w-6",
  md: "h-8 w-8",
  lg: "h-12 w-12",
};

/**
 * ServiceTracks logo mark.
 *
 * Dog-eared teal bulletin with a play triangle and two queued track rows.
 * Reads as "a service plan that's playable" — the bridge between the
 * church service plan and the streaming playlist.
 *
 * Works on both the slate-900 sidebar and the cool off-white canvas: the
 * teal body comes from `text-teal-500` (via `fill-current`); interior
 * elements are slate-100 and read correctly against the teal at any size.
 */
export default function LogoMark({ size = "md" }: LogoMarkProps) {
  return (
    <svg
      className={`${sizes[size]} text-teal-500 flex-shrink-0`}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="ServiceTracks"
    >
      {/* Badge body with dog-eared top-right corner */}
      <path
        className="fill-current"
        d="M15 4H34L44 14V33A11 11 0 0 1 33 44H15A11 11 0 0 1 4 33V15A11 11 0 0 1 15 4Z"
      />
      {/* Folded corner (page peel) */}
      <path className="fill-slate-100/40" d="M34 4L44 14H34Z" />
      {/* Play triangle (now-playing track) */}
      <path className="fill-slate-100" d="M12 12L21 17L12 22Z" />
      {/* Queued track rows */}
      <rect className="fill-slate-100" x="12" y="26" width="21" height="3" rx="1.5" />
      <rect className="fill-slate-100" x="12" y="33" width="15" height="3" rx="1.5" />
    </svg>
  );
}
