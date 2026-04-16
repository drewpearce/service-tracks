import type { ReactNode } from "react";

interface FormFieldProps {
  label?: string;
  htmlFor?: string;
  helper?: string;
  error?: string;
  className?: string;
  children: ReactNode;
}

export default function FormField({ label, htmlFor, helper, error, className, children }: FormFieldProps) {
  return (
    <div className={className}>
      {label && (
        <label
          htmlFor={htmlFor}
          className="block text-[13px] font-medium text-slate-700 mb-1.5"
        >
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="mt-1 text-[11px] text-rose-600">{error}</p>
      ) : helper ? (
        <p className="mt-1 text-[11px] text-slate-500">{helper}</p>
      ) : null}
    </div>
  );
}
