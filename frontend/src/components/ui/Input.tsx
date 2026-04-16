import { clsx } from "clsx";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  mono?: boolean;
  error?: boolean;
}

export default function Input({ mono = false, error = false, className, disabled, ...props }: InputProps) {
  return (
    <input
      disabled={disabled}
      className={clsx(
        "w-full rounded-lg border bg-white px-3.5 py-2 text-[13.5px] text-slate-900",
        "placeholder:text-slate-400 transition-colors focus:outline-none",
        mono && "font-mono",
        error
          ? "border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20"
          : "border-slate-300 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20",
        disabled && "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400",
        className,
      )}
      {...props}
    />
  );
}
