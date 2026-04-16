interface LogoMarkProps {
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "h-6 w-6",
  md: "h-8 w-8",
  lg: "h-12 w-12",
};

const iconSizes = {
  sm: "h-3 w-3",
  md: "h-4 w-4",
  lg: "h-6 w-6",
};

export default function LogoMark({ size = "md" }: LogoMarkProps) {
  return (
    <div
      className={`${sizes[size]} rounded-lg bg-teal-500 flex items-center justify-center flex-shrink-0`}
    >
      <svg
        className={`${iconSizes[size]} text-slate-900`}
        fill="currentColor"
        viewBox="0 0 24 24"
      >
        <rect x="4" y="6" width="16" height="2.5" rx="1.25" />
        <rect x="4" y="10.75" width="12" height="2.5" rx="1.25" />
        <rect x="4" y="15.5" width="8" height="2.5" rx="1.25" />
      </svg>
    </div>
  );
}
