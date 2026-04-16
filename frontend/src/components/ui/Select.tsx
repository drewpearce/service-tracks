import { clsx } from "clsx";
import type { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export default function Select({ error = false, className, disabled, children, ...props }: SelectProps) {
  return (
    <select
      disabled={disabled}
      className={clsx(
        "w-full rounded-lg border bg-white px-3.5 py-2 text-[13.5px] text-slate-900",
        "transition-colors focus:outline-none",
        error
          ? "border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20"
          : "border-slate-300 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20",
        disabled && "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
