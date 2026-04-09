import { createContext, useContext } from "react";
import type { Church, User } from "../types/api";

export interface AuthState {
  user: User | null;
  church: Church | null;
  loading: boolean;
  authenticated: boolean;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
