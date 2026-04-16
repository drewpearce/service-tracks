import { useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import { Input, LogoMark } from "../components/ui";
import { useAuth } from "../hooks/authContext";
import type { RegisterResponse } from "../types/api";

export default function Register() {
  const { authenticated, loading, refreshAuth } = useAuth();
  const navigate = useNavigate();

  const [churchName, setChurchName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!loading && authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!churchName.trim()) {
      setError("Church name is required.");
      return;
    }
    setSubmitting(true);
    try {
      await apiClient<RegisterResponse>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, church_name: churchName }),
        suppressAuthRedirect: true,
      });
      await refreshAuth();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setError("An account with this email already exists.");
        } else {
          setError("Something went wrong. Please try again.");
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Brand panel */}
      <div
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden text-white"
        style={{
          background:
            "radial-gradient(70% 70% at 10% 10%, rgba(20,184,166,0.22) 0%, transparent 60%), radial-gradient(50% 60% at 90% 100%, rgba(244,63,94,0.16) 0%, transparent 60%), #0F172A",
        }}
      >
        <div className="relative flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-2.5">
            <LogoMark size="md" />
            <span className="font-display text-xl font-semibold tracking-tight">ServiceTracks</span>
          </div>
          <div className="max-w-lg">
            <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-5">
              Sunday → Spotify
            </p>
            <h1 className="font-display text-[44px] leading-[1.05] font-semibold tracking-tight">
              Your Sunday set list,
              <br />
              <span className="text-teal-400">automatically synced</span>.
            </h1>
            <p className="mt-6 text-[15px] text-slate-300 leading-relaxed">
              Connect Planning Center and your streaming accounts. ServiceTracks keeps every
              playlist in lockstep — no copy-paste, no missed songs.
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.25em] text-slate-400 font-medium mb-4">
              Works with
            </p>
            <div className="flex items-center gap-6 text-slate-400">
              <span className="inline-flex items-center gap-2 text-[13px]">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2zm7 4a1 1 0 00-1 1v4H7a1 1 0 100 2h4v4a1 1 0 102 0v-4h4a1 1 0 100-2h-4V8a1 1 0 00-1-1z" />
                </svg>
                Planning Center
              </span>
              <span className="inline-flex items-center gap-2 text-[13px]">
                <svg className="h-5 w-5 text-teal-400" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.36-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2z" />
                </svg>
                Spotify
              </span>
              <span className="inline-flex items-center gap-2 text-[13px]">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12s5.37 12 12 12 12-5.37 12-12S18.63 0 12 0zm5.5 12.5L10 17V7l7.5 5.5z" />
                </svg>
                YouTube Music
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 flex-col lg:w-1/2">
        <header className="flex items-center justify-between px-10 py-6">
          <div className="flex items-center gap-2 lg:hidden">
            <LogoMark size="sm" />
            <span className="font-display text-base font-semibold">ServiceTracks</span>
          </div>
          <div className="ml-auto text-[13px] text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="font-medium text-slate-900 hover:text-teal-600">
              Sign in →
            </Link>
          </div>
        </header>

        <div className="flex-1 flex items-center justify-center px-10 pb-10">
          <div className="w-full max-w-sm">
            <div className="mb-8">
              <h2 className="font-display text-[32px] font-semibold tracking-tight text-slate-900">
                Create your account
              </h2>
              <p className="mt-2 text-[14px] text-slate-500">
                Get your church synced in under 5 minutes.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="church-name" className="block text-[13px] font-medium text-slate-700 mb-1.5">
                  Church name
                </label>
                <Input
                  id="church-name"
                  type="text"
                  required
                  placeholder="Grace Community Church"
                  value={churchName}
                  onChange={(e) => setChurchName(e.target.value)}
                  error={!!error}
                />
              </div>
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
              <div>
                <label htmlFor="password" className="block text-[13px] font-medium text-slate-700 mb-1.5">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  required
                  placeholder="Min. 8 characters"
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  error={!!error}
                />
              </div>

              {error && <p className="text-[13px] text-rose-600">{error}</p>}

              <button
                type="submit"
                disabled={submitting}
                className="w-full rounded-full bg-slate-900 text-white py-3 text-[14px] font-semibold hover:bg-slate-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
              >
                <span>{submitting ? "Creating account…" : "Get started"}</span>
                {!submitting && (
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                )}
              </button>
            </form>

            <p className="mt-6 text-center text-[12px] text-slate-400">
              By signing up, you agree to our{" "}
              <a href="https://service-tracks.com/terms" className="hover:text-slate-600 underline underline-offset-2">
                Terms
              </a>{" "}
              and{" "}
              <a href="https://service-tracks.com/privacy" className="hover:text-slate-600 underline underline-offset-2">
                Privacy Policy
              </a>
              .
            </p>
          </div>
        </div>

        <footer className="px-10 py-6 text-[11px] text-slate-400 text-center lg:text-left">
          ServiceTracks · service-tracks.com
        </footer>
      </div>
    </div>
  );
}
