import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import { LogoMark } from "../components/ui";

type Status = "loading" | "success" | "error";

function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="mb-8 flex items-center gap-2.5">
        <LogoMark size="md" />
        <span className="font-display text-xl font-semibold tracking-tight text-slate-900">
          ServiceTracks
        </span>
      </div>
      <div className="w-full max-w-sm rounded-3xl bg-white border border-slate-200 p-8 text-center">
        {children}
      </div>
    </div>
  );
}

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token");
  const [status, setStatus] = useState<Status>(initialToken ? "loading" : "error");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) return;
    apiClient<{ email_verified: boolean }>("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then(() => setStatus("success"))
      .catch((err) => {
        if (err instanceof ApiClientError) setStatus("error");
      });
  }, [searchParams]);

  if (status === "loading") {
    return (
      <AuthShell>
        <div className="flex justify-center mb-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
        </div>
        <p className="text-[14px] text-slate-500">Verifying your email…</p>
      </AuthShell>
    );
  }

  if (status === "success") {
    return (
      <AuthShell>
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-teal-50">
          <svg className="h-6 w-6 text-teal-600" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
          Email verified!
        </h2>
        <p className="mt-2 text-[14px] text-slate-500">
          You can now use all features of ServiceTracks.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-block rounded-full bg-slate-900 text-white px-6 py-2.5 text-[13px] font-semibold hover:bg-slate-800 transition-colors"
        >
          Go to Dashboard →
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-50">
        <svg className="h-6 w-6 text-rose-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
      <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
        Verification failed
      </h2>
      <p className="mt-2 text-[14px] text-slate-500">
        Invalid or expired link. Please request a new verification email from your dashboard.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 inline-block text-[13px] font-medium text-teal-600 hover:text-teal-700"
      >
        ← Back to Dashboard
      </Link>
    </AuthShell>
  );
}
