import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import { Input, LogoMark } from "../components/ui";

function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="mb-8 flex items-center gap-2.5">
        <LogoMark size="md" />
        <span className="font-display text-xl font-semibold tracking-tight text-slate-900">
          ServiceTracks
        </span>
      </div>
      <div className="w-full max-w-sm rounded-3xl bg-white border border-slate-200 p-8">
        {children}
      </div>
    </div>
  );
}

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiClient("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSubmitted(true);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <AuthShell>
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-teal-50">
            <svg className="h-6 w-6 text-teal-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
            Check your email
          </h2>
          <p className="mt-2 text-[14px] text-slate-500">
            If an account with that email exists, a reset link has been sent.
          </p>
          <Link
            to="/login"
            className="mt-6 inline-block text-[13px] font-medium text-teal-600 hover:text-teal-700"
          >
            ← Back to sign in
          </Link>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
        Forgot password?
      </h2>
      <p className="mt-2 text-[14px] text-slate-500">
        Enter your email and we'll send a reset link.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="email" className="block text-[13px] font-medium text-slate-700 mb-1.5">
            Email address
          </label>
          <Input
            id="email"
            type="email"
            required
            placeholder="jonathan@gracechurch.org"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={!!error}
          />
        </div>
        {error && <p className="text-[13px] text-rose-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-full bg-slate-900 text-white py-3 text-[14px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          {submitting ? "Sending…" : "Send reset link"}
        </button>
      </form>

      <Link
        to="/login"
        className="mt-5 block text-center text-[13px] font-medium text-slate-500 hover:text-slate-900"
      >
        ← Back to sign in
      </Link>
    </AuthShell>
  );
}
