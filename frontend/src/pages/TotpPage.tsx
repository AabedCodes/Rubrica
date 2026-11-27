import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { ApiError } from "../api";
import { useAuth } from "../auth/AuthContext";
import { safeNext } from "./LoginPage";

/** Instructor second factor at sign-in (C27, 01-interfaces.md §4.1). */
export function TotpPage() {
  const { state, submitTotp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const next = safeNext((location.state as { from?: unknown } | null)?.from);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "signed_in") return <Navigate to={next} replace />;
  if (state.status !== "totp_required") return <Navigate to="/login" replace />;

  return (
    <div className="auth-page">
      <h1>Enter your authenticator code</h1>
      <p>Instructors confirm every sign-in with a code from their authenticator app.</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          submitTotp(code)
            .then(() => navigate(next, { replace: true }))
            .catch((err: unknown) => {
              setError(err instanceof ApiError && err.code === "totp_invalid" ? "That code is not valid." : "Could not verify. Try again.");
              setCode("");
              setBusy(false);
            });
        }}
      >
        <label>
          Authenticator code
          <input
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy}>
          Verify
        </button>
      </form>
    </div>
  );
}
