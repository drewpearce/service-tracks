import clsx from "clsx";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/authContext";
import VerificationBanner from "./VerificationBanner";

const NAV_LINKS = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Songs", to: "/songs" },
  { label: "PCO Setup", to: "/setup/pco" },
  { label: "Streaming", to: "/setup/streaming" },
  { label: "Settings", to: "/settings" },
];

export default function Layout() {
  const { user, church, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white shadow">
        <div className="flex h-16 items-center border-b px-6">
          <span className="text-lg font-bold text-blue-600">ServiceTracks</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_LINKS.map(({ label, to }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                location.pathname === to ||
                  (to !== "/dashboard" && location.pathname.startsWith(to))
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-700 hover:bg-gray-100"
              )}
            >
              {label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col pl-64">
        {/* Header */}
        <header className="flex h-16 items-center justify-between border-b bg-white px-6 shadow-sm">
          <span className="text-sm font-medium text-gray-700">
            {church?.name ?? ""}
          </span>
          <button
            onClick={() => void logout()}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Log out
          </button>
        </header>

        {/* Verification banner */}
        {user && <VerificationBanner emailVerified={user.email_verified} />}

        {/* Page content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
