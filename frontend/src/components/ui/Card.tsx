import { clsx } from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

type CardVariant = "default" | "interactive" | "selected" | "inverse" | "attention" | "placeholder";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  children: ReactNode;
}

const variantClasses: Record<CardVariant, string> = {
  default: "bg-white border border-slate-200",
  interactive:
    "bg-white border border-slate-200 cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_rgba(15,23,42,0.18)]",
  selected: "bg-white border-2 border-teal-500",
  inverse: "bg-slate-900 text-slate-100",
  attention: "bg-rose-50 border border-rose-200",
  placeholder: "border-2 border-dashed border-slate-300",
};

export default function Card({ variant = "default", className, children, ...props }: CardProps) {
  return (
    <div
      className={clsx("rounded-2xl p-5", variantClasses[variant], className)}
      {...props}
    >
      {children}
    </div>
  );
}
