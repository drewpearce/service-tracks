import { clsx } from "clsx";
import type { ReactNode } from "react";

type EmptyStateIntent = "teal" | "rose" | "slate";

interface EmptyStateProps {
  icon: ReactNode;
  iconIntent?: EmptyStateIntent;
  title: string;
  body?: string;
  action?: ReactNode;
  className?: string;
}

const iconWrapClasses: Record<EmptyStateIntent, string> = {
  teal: "bg-teal-50 text-teal-600",
  rose: "bg-rose-50 text-rose-600",
  slate: "bg-slate-100 text-slate-500",
};

export default function EmptyState({
  icon,
  iconIntent = "slate",
  title,
  body,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx("rounded-2xl bg-white border border-slate-200 p-10 text-center", className)}>
      <div
        className={clsx(
          "mx-auto h-12 w-12 rounded-full flex items-center justify-center mb-4",
          iconWrapClasses[iconIntent],
        )}
      >
        {icon}
      </div>
      <p className="font-display text-lg font-semibold tracking-tight">{title}</p>
      {body && (
        <p className="mt-1 text-[13px] text-slate-500 max-w-[32ch] mx-auto">{body}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
