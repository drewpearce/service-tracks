import LogoMark from "./LogoMark";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const textSizes = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-2xl",
};

const gaps = {
  sm: "gap-1.5",
  md: "gap-2",
  lg: "gap-2.5",
};

/**
 * ServiceTracks full lockup: mark + wordmark.
 *
 * The wordmark uses a Service/Tracks color split — "Service" picks up the
 * ambient foreground color so it works on either slate-900 or off-white,
 * and "Tracks" is teal-500 to echo the mark.
 */
export default function Logo({ size = "md", className = "" }: LogoProps) {
  return (
    <div className={`inline-flex items-center ${gaps[size]} ${className}`.trim()}>
      <LogoMark size={size} />
      <span
        className={`font-display font-bold tracking-tight leading-none ${textSizes[size]}`}
      >
        Service<span className="text-teal-500">Tracks</span>
      </span>
    </div>
  );
}
