import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface UserProfile {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_admin: boolean;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  last_login: string | null;
}

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
}

// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------
const TOKEN_KEY = "marketos_access_token";
const REFRESH_KEY = "marketos_refresh_token";

export const getAccessToken = () => localStorage.getItem(TOKEN_KEY);
const getRefreshToken = () => localStorage.getItem(REFRESH_KEY);
const setTokens = (access: string, refresh: string) => {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
};
const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
};

// ---------------------------------------------------------------------------
// Auth-aware fetch helper (exported so all API calls can use it)
// ---------------------------------------------------------------------------
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Fetch current user profile using stored token
  const fetchMe = useCallback(async (): Promise<boolean> => {
    const token = getAccessToken();
    if (!token) return false;
    try {
      const res = await apiFetch("/api/v1/auth/me");
      if (res.ok) {
        const user: UserProfile = await res.json();
        setState({ user, isAuthenticated: true, isLoading: false });
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  // Refresh token exchange
  const refreshSession = useCallback(async (): Promise<boolean> => {
    const refresh = getRefreshToken();
    if (!refresh) return false;
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (res.ok) {
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return await fetchMe();
      }
      return false;
    } catch {
      return false;
    }
  }, [fetchMe]);

  // On mount — try to restore session
  useEffect(() => {
    (async () => {
      const ok = await fetchMe();
      if (!ok) {
        const refreshed = await refreshSession();
        if (!refreshed) {
          clearTokens();
          setState({ user: null, isAuthenticated: false, isLoading: false });
        }
      }
    })();
  }, [fetchMe, refreshSession]);

  // Auto-refresh access token every 12 minutes (before 15-min expiry)
  useEffect(() => {
    const interval = setInterval(() => refreshSession(), 12 * 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshSession]);

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    await fetchMe();
  };

  const register = async (email: string, password: string, fullName?: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    await fetchMe();
  };

  const logout = () => {
    clearTokens();
    setState({ user: null, isAuthenticated: false, isLoading: false });
  };

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

