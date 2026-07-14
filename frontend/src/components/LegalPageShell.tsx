import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { LogoMark } from "./ui";

interface LegalPageShellProps {
  title: string;
  lastUpdated: string;
  children: ReactNode;
}

/**
 * Standalone public layout for legal documents (Privacy Policy, Terms of
 * Service). Not wrapped in the authenticated Layout/nav shell — these pages
 * must be reachable by anyone, including OAuth reviewers, without signing in.
 */
export function LegalPageShell({ title, lastUpdated, children }: LegalPageShellProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link to="/login" className="flex items-center gap-2.5">
            <LogoMark size="sm" />
            <span className="font-display text-lg font-semibold tracking-tight text-slate-900">
              ServiceTracks
            </span>
          </Link>
          <Link
            to="/login"
            className="text-[13px] font-medium text-slate-500 hover:text-slate-900 underline-offset-2 hover:underline"
          >
            ← Back to sign in
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-[32px] font-semibold tracking-tight text-slate-900">{title}</h1>
        <p className="mt-2 text-[13px] text-slate-500">Last updated: {lastUpdated}</p>

        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-800">
          This is a working draft provided for transparency. It has not yet been reviewed by legal
          counsel — please treat it as informational until a reviewed version is published.
        </div>

        <div
          className="mt-8 space-y-4 [&_a]:text-teal-600 [&_a]:underline [&_h2]:mt-8 [&_h2]:font-display [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-slate-900 [&_li]:text-[14px] [&_li]:leading-relaxed [&_p]:text-[14px] [&_p]:leading-relaxed [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5"
        >
          {children}
        </div>
      </main>
    </div>
  );
}
