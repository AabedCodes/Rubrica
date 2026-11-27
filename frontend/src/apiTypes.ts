/**
 * Request and response shapes for the 01-interfaces.md §10 routes the shell uses.
 *
 * §10 names these routes but not their bodies. Every shape marked ASSUMED is our
 * proposal until it is agreed in a PR to 01-interfaces.md §10 (auth: owner E,
 * task E4). Keep all of them in this one file so the mock (src/mocks/) and the
 * screens change together when the real contract lands.
 */

export type Role = "student" | "instructor";

/** GET /api/me. ASSUMED: §3.1 `users` columns minus secrets and email. */
export interface Me {
  id: string;
  display_name: string;
  role: Role;
}

/** GET /api/auth/csrf. ASSUMED field name. */
export interface CsrfResponse {
  csrf_token: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * POST /api/auth/login. ASSUMED: instructors get `totp_required` (C27) and
 * finish with POST /api/auth/totp; students are signed in at once.
 */
export type LoginResponse = { status: "ok" } | { status: "totp_required" };

/** POST /api/auth/totp and POST /api/auth/reauth (C27, C28). ASSUMED. */
export interface TotpRequest {
  code: string;
}

/**
 * GET /api/courses. ASSUMED: includes the caller's role in each course from
 * §3.1 `enrollments.role`, which the course switcher shows.
 */
export interface Course {
  id: string;
  code: string;
  title: string;
  role: Role;
}

/**
 * Error body for every non-2xx /api response. ASSUMED: `{ "error": "<code>" }`
 * with a fixed code and no free text, mirroring the MCP server's C33 rule.
 * `reauth_required` (HTTP 401) is named in docs/plan/A-product-owner.md A1.
 */
export type ApiErrorCode =
  | "unauthenticated"
  | "invalid_credentials"
  | "totp_invalid"
  | "reauth_required"
  | "csrf_invalid"
  | "rate_limited"
  | "forbidden"
  | "not_found"
  | "invalid_request"
  | "internal";

export interface ApiErrorBody {
  error: ApiErrorCode;
}
