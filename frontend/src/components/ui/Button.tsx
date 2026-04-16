import { clsx } from "clsx";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "accent";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-slate-900 text-white hover:bg-slate-800",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
  ghost: "text-slate-600 hover:bg-slate-100",
  danger: "bg-rose-600 text-white hover:bg-rose-700",
  accent: "bg-teal-500 text-slate-900 hover:bg-teal-400",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-3 py-1 text-[11px]",
  md: "px-5 py-2 text-[13px]",
  lg: "px-6 py-2.5 text-[14px]",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  leadingIcon,
  trailingIcon,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={clsx(
        // Base
        "inline-flex items-center justify-center gap-1.5 rounded-full font-semibold transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-40",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <span
          className="h-3 w-3 rounded-full border-2 border-current border-t-transparent animate-spin"
          aria-hidden="true"
        />
      ) : (
        leadingIcon
      )}
      {children}
      {!loading && trailingIcon}
    </button>
  );
}
