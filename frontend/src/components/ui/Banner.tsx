import { clsx } from "clsx";
import type { ReactNode } from "react";

type BannerType = "info" | "warning" | "error" | "success";

interface BannerProps {
  type: BannerType;
  title: string;
  body?: string;
  action?: ReactNode;
  className?: string;
}

const typeConfig: Record<
  BannerType,
  { wrap: string; icon: string; title: string; body: string; svg: ReactNode }
> = {
  info: {
    wrap: "bg-teal-50 border border-teal-200",
    icon: "text-teal-600",
    title: "text-teal-900",
    body: "text-teal-800",
    svg: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  warning: {
    wrap: "bg-amber-50 border border-amber-200",
    icon: "text-amber-600",
    title: "text-amber-900",
    body: "text-amber-800",
    svg: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M5 20h14a2 2 0 001.84-2.75L13.74 4a2 2 0 00-3.48 0l-7.1 13.25A2 2 0 005 20z" />
      </svg>
    ),
  },
  error: {
    wrap: "bg-rose-50 border border-rose-200",
    icon: "text-rose-600",
    title: "text-rose-900",
    body: "text-rose-800",
    svg: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3a9 9 0 100 18 9 9 0 000-18z" />
      </svg>
    ),
  },
  success: {
    wrap: "bg-slate-900",
    icon: "text-teal-400",
    title: "text-white",
    body: "text-slate-300",
    svg: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
};

export default function Banner({ type, title, body, action, className }: BannerProps) {
  const config = typeConfig[type];
  return (
    <div className={clsx("flex items-start gap-3 rounded-xl p-4", config.wrap, className)}>
      <span className={clsx("shrink-0 mt-0.5", config.icon)}>{config.svg}</span>
      <div className="flex-1 min-w-0">
        <p className={clsx("text-[13.5px] font-semibold", config.title)}>{title}</p>
        {body && <p className={clsx("mt-0.5 text-[12.5px]", config.body)}>{body}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
