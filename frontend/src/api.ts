/**
 * The one HTTP client for /api (A1; 01-interfaces.md §4.1 and §10).
 *
 * - Sends the session cookie (same-origin only) and never reads or stores it:
 *   it is HttpOnly (§4.1).
 * - Adds X-CSRF-Token to every state-changing request. The token comes from
 *   GET /api/auth/csrf and is kept in memory only, never in Web Storage (T-10).
 * - On `401 reauth_required` (C28) asks the app to re-authenticate the
 *   instructor, then retries the request exactly once.
 */
import type { ApiErrorCode, Course, CsrfResponse, LoginRequest, LoginResponse, Me, TotpRequest } from "./apiTypes";

/** Same signature as `fetch`, so tests and the mock can stand in for it. */
export type Transport = (url: string, init: RequestInit) => Promise<Response>;

/** Resolves true if the user re-authenticated, false if they cancelled. */
export type ReauthHandler = () => Promise<boolean>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode | "unknown";

  constructor(status: number, code: ApiErrorCode | "unknown") {
    super(`API error ${status} ${code}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface ApiClientOptions {
  transport?: Transport;
  onReauthRequired?: ReauthHandler;
}

export interface RequestOptions {
  /** Set false for the re-auth call itself so it can never loop. */
  allowReauth?: boolean;
}

type Method = "GET" | "POST" | "PUT" | "DELETE";

const STATE_CHANGING: ReadonlySet<Method> = new Set(["POST", "PUT", "DELETE"]);

export function createApiClient(options: ApiClientOptions = {}) {
  const transport: Transport = options.transport ?? ((url, init) => fetch(url, init));
  let reauthHandler: ReauthHandler | undefined = options.onReauthRequired;
  // Memory only. Cleared whenever the session changes (login, logout).
  let csrfToken: string | null = null;
  // Several requests can hit reauth_required at once; ask the user only once.
  let pendingReauth: Promise<boolean> | null = null;

  async function csrf(): Promise<string> {
    if (csrfToken === null) {
      const body = await send<CsrfResponse>("GET", "/auth/csrf", undefined, { allowReauth: false });
      csrfToken = body.csrf_token;
    }
    return csrfToken;
  }

  function reauthenticate(): Promise<boolean> {
    if (!reauthHandler) return Promise.resolve(false);
    if (pendingReauth === null) {
      pendingReauth = reauthHandler().finally(() => {
        pendingReauth = null;
      });
    }
    return pendingReauth;
  }

  async function send<T>(method: Method, path: string, body: unknown, opts: RequestOptions = {}): Promise<T> {
    const allowReauth = opts.allowReauth ?? true;
    // Only ever talk to our own /api: no absolute or protocol-relative URLs.
    if (!path.startsWith("/") || path.startsWith("//")) {
      throw new Error(`API path must start with a single "/": ${path}`);
    }
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (STATE_CHANGING.has(method)) headers["X-CSRF-Token"] = await csrf();

    const response = await transport(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error",
    });

    if (response.ok) {
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    }

    const code = await errorCode(response);
    if (response.status === 401 && code === "reauth_required" && allowReauth) {
      if (await reauthenticate()) {
        return send<T>(method, path, body, { allowReauth: false });
      }
    }
    if (response.status === 403 && code === "csrf_invalid") {
      csrfToken = null; // fetch a fresh token on the next state-changing call
    }
    throw new ApiError(response.status, code);
  }

  return {
    get: <T>(path: string, opts?: RequestOptions) => send<T>("GET", path, undefined, opts),
    post: <T>(path: string, body?: unknown, opts?: RequestOptions) => send<T>("POST", path, body, opts),
    put: <T>(path: string, body?: unknown, opts?: RequestOptions) => send<T>("PUT", path, body, opts),
    delete: <T>(path: string, opts?: RequestOptions) => send<T>("DELETE", path, undefined, opts),
    /** Forget the CSRF token; call when the session changes. */
    resetSession(): void {
      csrfToken = null;
    },
    setReauthHandler(handler: ReauthHandler | undefined): void {
      reauthHandler = handler;
    },
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

async function errorCode(response: Response): Promise<ApiErrorCode | "unknown"> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "error" in body && typeof body.error === "string") {
      return body.error as ApiErrorCode;
    }
  } catch {
    // Not JSON (for example a proxy error page): fall through.
  }
  return "unknown";
}

/** Typed wrappers for the §10 routes the shell uses. */
export function authRoutes(api: ApiClient) {
  return {
    me: () => api.get<Me>("/me"),
    login: (body: LoginRequest) => api.post<LoginResponse>("/auth/login", body, { allowReauth: false }),
    totp: (body: TotpRequest) => api.post<void>("/auth/totp", body, { allowReauth: false }),
    reauth: (body: TotpRequest) => api.post<void>("/auth/reauth", body, { allowReauth: false }),
    logout: () => api.post<void>("/auth/logout", undefined, { allowReauth: false }),
    courses: () => api.get<Course[]>("/courses"),
  };
}
