import { clsx } from "clsx";
import type { TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  mono?: boolean;
  error?: boolean;
}

export default function Textarea({ mono = false, error = false, className, disabled, ...props }: TextareaProps) {
  return (
    <textarea
      disabled={disabled}
      className={clsx(
        "w-full rounded-lg border bg-white px-3.5 py-2 text-[13.5px] text-slate-900 resize-none",
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
