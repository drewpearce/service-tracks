import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
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

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const token = searchParams.get("token") ?? "";

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setValidationError(null);
    setApiError(null);
    if (password.length < 8) {
      setValidationError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setValidationError("Passwords do not match.");
      return;
    }
    try {
      await apiClient("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 400) {
        setApiError("Invalid or expired link. Please request a new reset email.");
      } else {
        setApiError("Something went wrong. Please try again.");
      }
    }
  }

  const error = validationError ?? apiError;

  if (success) {
    return (
      <AuthShell>
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-teal-50">
            <svg className="h-6 w-6 text-teal-600" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
            Password reset!
          </h2>
          <p className="mt-2 text-[14px] text-slate-500">Redirecting you to sign in…</p>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <h2 className="font-display text-[24px] font-semibold tracking-tight text-slate-900">
        Reset your password
      </h2>
      <p className="mt-2 text-[14px] text-slate-500">
        Choose a new password for your account.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="password" className="block text-[13px] font-medium text-slate-700 mb-1.5">
            New password
          </label>
          <Input
            id="password"
            type="password"
            required
            placeholder="Min. 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={!!error}
          />
        </div>
        <div>
          <label htmlFor="confirm-password" className="block text-[13px] font-medium text-slate-700 mb-1.5">
            Confirm new password
          </label>
          <Input
            id="confirm-password"
            type="password"
            required
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={!!error}
          />
        </div>
        {error && <p className="text-[13px] text-rose-600">{error}</p>}
        <button
          type="submit"
          className="w-full rounded-full bg-slate-900 text-white py-3 text-[14px] font-semibold hover:bg-slate-800 transition-colors"
        >
          Reset password
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
