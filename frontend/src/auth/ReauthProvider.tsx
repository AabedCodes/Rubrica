import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { ApiError, authRoutes, type ApiClient } from "../api";

/**
 * Re-authentication modal (C28). Releasing grades, accepting an answer key and
 * deciding an appeal need a TOTP code entered within the last 5 minutes
 * (01-interfaces.md §4.1). When the API answers `401 reauth_required`, the
 * client calls the handler registered here; the modal asks for the code and
 * the client retries the original request once.
 */
export function ReauthProvider({ api, children }: { api: ApiClient; children: ReactNode }) {
  const [resolver, setResolver] = useState<((ok: boolean) => void) | null>(null);

  useEffect(() => {
    api.setReauthHandler(
      () =>
        new Promise<boolean>((resolve) => {
          setResolver(() => resolve);
        }),
    );
    return () => api.setReauthHandler(undefined);
  }, [api]);

  const close = (ok: boolean) => {
    resolver?.(ok);
    setResolver(null);
  };

  return (
    <>
      {children}
      {resolver && <ReauthDialog api={api} onDone={close} />}
    </>
  );
}

function ReauthDialog({ api, onDone }: { api: ApiClient; onDone: (ok: boolean) => void }) {
  const titleId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="modal-backdrop">
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <h2 id={titleId}>Confirm it's you</h2>
        <p>This action needs a fresh code from your authenticator app.</p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setBusy(true);
            setError(null);
            authRoutes(api)
              .reauth({ code })
              .then(() => onDone(true))
              .catch((err: unknown) => {
                setError(err instanceof ApiError && err.code === "totp_invalid" ? "That code is not valid." : "Could not confirm. Try again.");
                setBusy(false);
              });
          }}
        >
          <label>
            Authenticator code
            <input
              ref={inputRef}
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
          <div className="actions">
            <button type="button" onClick={() => onDone(false)} disabled={busy}>
              Cancel
            </button>
            <button type="submit" disabled={busy}>
              Confirm
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
