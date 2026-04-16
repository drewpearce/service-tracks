import { Link } from "react-router-dom";
import type { StreamingConnectionStatus } from "../types/api";

interface SetupChecklistProps {
  pco_connected: boolean;
  service_type_selected: boolean;
  streaming_connections: StreamingConnectionStatus[];
}

const CIRCUMFERENCE = 2 * Math.PI * 42; // r=42

export default function SetupChecklist({
  pco_connected,
  service_type_selected,
  streaming_connections,
}: SetupChecklistProps) {
  const spotifyConnected = streaming_connections.some(
    (c) => c.platform === "spotify" && c.connected
  );

  const steps = [
    {
      done: pco_connected,
      label: "Connect Planning Center Online",
      actionTo: "/setup/pco",
      actionLabel: "Connect PCO",
    },
    {
      done: service_type_selected,
      label: "Select a service type in PCO",
      actionTo: "/setup/pco",
      actionLabel: "Select →",
    },
    {
      done: spotifyConnected,
      label: "Connect Spotify",
      actionTo: "/setup/streaming",
      actionLabel: "Connect",
    },
  ];

  const doneCount = steps.filter((s) => s.done).length;
  const allDone = doneCount === steps.length;
  if (allDone) return null;

  const pct = Math.round((doneCount / steps.length) * 100);
  const offset = CIRCUMFERENCE * (1 - doneCount / steps.length);

  return (
    <section className="rounded-3xl bg-white border border-slate-200 p-8 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-72 h-72 rounded-full bg-teal-50 blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none" />
      <div className="relative flex items-start justify-between gap-8">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <span className="inline-flex items-center rounded-full bg-teal-500 text-white px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide">
              {doneCount === 0 ? "Get started" : "Almost there"}
            </span>
            <span className="text-[12px] text-slate-500 tabular-nums">
              {doneCount} of {steps.length} complete
            </span>
          </div>
          <h2 className="font-display text-3xl font-semibold tracking-tight text-slate-900">
            Finish setup
          </h2>
          <p className="mt-2 text-[14px] text-slate-500">
            {steps.length - doneCount} step{steps.length - doneCount !== 1 ? "s" : ""} between you and automated Sunday sync.
          </p>

          <ul className="mt-6 space-y-3">
            {steps.map((step, i) => (
              <li key={i} className="flex items-center gap-4">
                {step.done ? (
                  <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-teal-500 text-white">
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                ) : (
                  <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-50 border-2 border-slate-200 text-slate-500 font-semibold text-[12px]">
                    {i + 1}
                  </span>
                )}
                <span className={`flex-1 text-[14px] ${step.done ? "line-through text-slate-400" : "font-medium text-slate-900"}`}>
                  {step.label}
                </span>
                {step.done ? (
                  <span className="text-[11px] text-slate-400">Connected</span>
                ) : (
                  <Link
                    to={step.actionTo}
                    className="rounded-full bg-slate-900 text-white px-4 py-1.5 text-[12px] font-semibold hover:bg-slate-800 transition-colors"
                  >
                    {step.actionLabel}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex-shrink-0 w-40 h-40">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="42" stroke="#E2E8F0" strokeWidth="8" fill="none" />
            <circle
              cx="50" cy="50" r="42"
              stroke="#0D9488"
              strokeWidth="8"
              fill="none"
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <p className="font-display text-4xl font-semibold text-slate-900">{pct}%</p>
            <p className="text-[11px] text-slate-500 uppercase tracking-widest">done</p>
          </div>
        </div>
      </div>
    </section>
  );
}
