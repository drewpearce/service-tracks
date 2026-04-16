import { clsx } from "clsx";
import type { ReactNode } from "react";

type BadgeIntent = "teal" | "amber" | "rose" | "slate" | "inverse";

interface BadgeProps {
  intent?: BadgeIntent;
  dot?: boolean;
  className?: string;
  children: ReactNode;
}

const intentClasses: Record<BadgeIntent, { wrap: string; dot: string }> = {
  teal: {
    wrap: "bg-teal-50 border border-teal-200 text-teal-700",
    dot: "bg-teal-500",
  },
  amber: {
    wrap: "bg-amber-50 border border-amber-200 text-amber-700",
    dot: "bg-amber-500",
  },
  rose: {
    wrap: "bg-rose-50 border border-rose-200 text-rose-700",
    dot: "bg-rose-500",
  },
  slate: {
    wrap: "bg-slate-100 border border-slate-200 text-slate-600",
    dot: "bg-slate-400",
  },
  inverse: {
    wrap: "bg-slate-900 text-white",
    dot: "bg-white",
  },
};

export default function Badge({ intent = "slate", dot = false, className, children }: BadgeProps) {
  const { wrap, dot: dotColor } = intentClasses[intent];
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5",
        "text-[10px] font-semibold uppercase tracking-widest",
        wrap,
        className,
      )}
    >
      {dot && <span className={clsx("h-1.5 w-1.5 rounded-full shrink-0", dotColor)} />}
      {children}
    </span>
  );
}

/** Mono chip — for template variables like {church_name} */
export function MonoChip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border border-slate-200 bg-slate-50",
        "px-2 py-0.5 text-[11px] font-mono text-slate-700",
        className,
      )}
    >
      {children}
    </span>
  );
}
