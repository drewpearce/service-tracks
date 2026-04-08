import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";
import type { Church, MeResponse, User } from "../types/api";

interface AuthState {
  user: User | null;
  church: Church | null;
  loading: boolean;
  authenticated: boolean;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [church, setChurch] = useState<Church | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchMe = useCallback(async () => {
    try {
      const data = await apiClient<MeResponse>("/api/auth/me", {
        suppressAuthRedirect: true,
      });
      setUser(data.user);
      setChurch(data.church);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        setUser(null);
        setChurch(null);
      }
    }
  }, []);

  const refreshAuth = useCallback(async () => {
    await fetchMe();
  }, [fetchMe]);

  useEffect(() => {
    fetchMe().finally(() => setLoading(false));
  }, [fetchMe]);

  const logout = useCallback(async () => {
    try {
      await apiClient("/api/auth/logout", { method: "POST" });
    } catch {
      // Ignore errors — log out locally regardless
    }
    setUser(null);
    setChurch(null);
    navigate("/login");
  }, [navigate]);

  const authenticated = user !== null;

  return (
    <AuthContext.Provider
      value={{ user, church, loading, authenticated, logout, refreshAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
