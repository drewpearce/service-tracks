import clsx from "clsx";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/authContext";
import LogoMark from "./ui/LogoMark";
import VerificationBanner from "./VerificationBanner";

const NAV_LINKS = [
  {
    label: "Dashboard",
    to: "/dashboard",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7m-9 2v10a1 1 0 001 1h4a1 1 0 001-1V10M9 21h6" />
      </svg>
    ),
  },
  {
    label: "Songs",
    to: "/songs",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V5l12-2v12M9 17a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    label: "PCO Setup",
    to: "/setup/pco",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    label: "Streaming",
    to: "/setup/streaming",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072M12 18a6 6 0 010-12m0 12a6 6 0 000-12m0 12v2m0-14V4" />
      </svg>
    ),
  },
  {
    label: "Settings",
    to: "/settings",
    icon: (
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

function avatarInitials(email: string): string {
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]/);
  if (parts.length >= 2) {
    return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
  }
  return local.slice(0, 2).toUpperCase();
}

export default function Layout() {
  const { user, church, logout } = useAuth();
  const location = useLocation();

  const initials = user ? avatarInitials(user.email) : "";

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 flex w-64 flex-col bg-slate-900 text-white">
        {/* Logo */}
        <div className="flex h-16 items-center px-6">
          <div className="flex items-center gap-2.5">
            <LogoMark size="md" />
            <span className="font-display text-lg font-semibold tracking-tight">
              ServiceTracks
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 text-[14px]">
          {NAV_LINKS.map(({ label, to, icon }) => {
            const active =
              location.pathname === to ||
              (to !== "/dashboard" && location.pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 font-medium transition-colors",
                  active
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                )}
              >
                {icon}
                {label}
                {active && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-teal-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-slate-800">
          <div className="flex items-center gap-2.5 px-4 py-3">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-teal-400 to-rose-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium truncate">{user?.email}</p>
              <p className="text-[11px] text-slate-400 truncate">{church?.name}</p>
            </div>
            <button
              onClick={() => void logout()}
              className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0 px-1"
              title="Log out"
              aria-label="Log out"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col pl-64">
        {user && <VerificationBanner emailVerified={user.email_verified} />}
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
