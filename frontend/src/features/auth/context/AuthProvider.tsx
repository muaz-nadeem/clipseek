import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { logoutRequest, type TokenResponse } from "../../../shared/api/client";

type AuthState = {
  token: string | null;
  email: string | null;
  userId: number | null;
  setSession: (data: TokenResponse) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

function persistSession(data: TokenResponse) {
  localStorage.setItem("ivs_token", data.access_token);
  localStorage.setItem("ivs_refresh", data.refresh_token);
  localStorage.setItem("ivs_email", data.email);
  localStorage.setItem("ivs_user_id", String(data.user_id));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("ivs_token"));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem("ivs_email"));
  const [userId, setUserId] = useState<number | null>(() => {
    const raw = localStorage.getItem("ivs_user_id");
    return raw ? Number(raw) : null;
  });

  useEffect(() => {
    const onRefresh = () => {
      setToken(localStorage.getItem("ivs_token"));
      setEmail(localStorage.getItem("ivs_email"));
      const raw = localStorage.getItem("ivs_user_id");
      setUserId(raw ? Number(raw) : null);
    };
    window.addEventListener("ivs-auth-refresh", onRefresh);
    window.addEventListener("storage", onRefresh);
    return () => {
      window.removeEventListener("ivs-auth-refresh", onRefresh);
      window.removeEventListener("storage", onRefresh);
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      token,
      email,
      userId,
      setSession: (data) => {
        persistSession(data);
        setToken(data.access_token);
        setEmail(data.email);
        setUserId(data.user_id);
      },
      logout: () => {
        void logoutRequest();
        localStorage.removeItem("ivs_token");
        localStorage.removeItem("ivs_refresh");
        localStorage.removeItem("ivs_email");
        localStorage.removeItem("ivs_user_id");
        setToken(null);
        setEmail(null);
        setUserId(null);
      },
    }),
    [token, email, userId],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
