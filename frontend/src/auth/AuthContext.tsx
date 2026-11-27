import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, authRoutes, type ApiClient } from "../api";
import type { LoginRequest, Me } from "../apiTypes";

export type AuthState =
  | { status: "loading" }
  | { status: "signed_out" }
  | { status: "totp_required" }
  | { status: "signed_in"; me: Me };

interface AuthContextValue {
  api: ApiClient;
  state: AuthState;
  login(credentials: LoginRequest): Promise<"signed_in" | "totp_required">;
  submitTotp(code: string): Promise<void>;
  logout(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ api, children }: { api: ApiClient; children: ReactNode }) {
  const routes = useMemo(() => authRoutes(api), [api]);
  const [state, setState] = useState<AuthState>({ status: "loading" });

  const loadMe = useCallback(async (): Promise<Me | null> => {
    try {
      return await routes.me();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return null;
      throw err;
    }
  }, [routes]);

  useEffect(() => {
    let cancelled = false;
    loadMe()
      .then((me) => {
        if (!cancelled) setState(me ? { status: "signed_in", me } : { status: "signed_out" });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "signed_out" });
      });
    return () => {
      cancelled = true;
    };
  }, [loadMe]);

  const finishSignIn = useCallback(async () => {
    // The session changed, so any CSRF token we hold belongs to the old one.
    api.resetSession();
    const me = await loadMe();
    setState(me ? { status: "signed_in", me } : { status: "signed_out" });
  }, [api, loadMe]);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const result = await routes.login(credentials);
      if (result.status === "totp_required") {
        setState({ status: "totp_required" });
        return "totp_required" as const;
      }
      await finishSignIn();
      return "signed_in" as const;
    },
    [routes, finishSignIn],
  );

  const submitTotp = useCallback(
    async (code: string) => {
      await routes.totp({ code });
      await finishSignIn();
    },
    [routes, finishSignIn],
  );

  const logout = useCallback(async () => {
    try {
      await routes.logout();
    } finally {
      api.resetSession();
      setState({ status: "signed_out" });
    }
  }, [api, routes]);

  const value = useMemo(() => ({ api, state, login, submitTotp, logout }), [api, state, login, submitTotp, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
