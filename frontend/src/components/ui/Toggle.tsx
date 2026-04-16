import { clsx } from "clsx";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export default function Toggle({ checked, onChange, disabled = false, className }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative h-6 w-11 rounded-full transition-colors focus-visible:outline-none",
        "focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
        checked ? "bg-teal-500" : "bg-slate-200",
        disabled && "cursor-not-allowed opacity-40",
        className,
      )}
    >
      <span
        className={clsx(
          "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
          checked && "translate-x-5",
        )}
      />
    </button>
  );
}
