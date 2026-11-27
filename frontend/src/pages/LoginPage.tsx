import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { ApiError } from "../api";
import { useAuth } from "../auth/AuthContext";

export function loginErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "invalid_credentials") return "Email or password is wrong.";
    if (err.code === "rate_limited") return "Too many attempts. Wait a few minutes and try again.";
  }
  return "Sign-in failed. Try again.";
}

/** Only follow redirects to our own paths, never to another site. */
export function safeNext(value: unknown): string {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function LoginPage() {
  const { state, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const next = safeNext((location.state as { from?: unknown } | null)?.from);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "signed_in") return <Navigate to={next} replace />;

  return (
    <div className="auth-page">
      <h1>Sign in to Rubrica</h1>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          login({ email, password })
            .then((result) => {
              navigate(result === "totp_required" ? "/login/totp" : next, { replace: true, state: { from: next } });
            })
            .catch((err: unknown) => {
              setError(loginErrorMessage(err));
              setPassword("");
              setBusy(false);
            });
        }}
      >
        <label>
          Email
          <input type="email" name="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy}>
          Sign in
        </button>
      </form>
    </div>
  );
}
