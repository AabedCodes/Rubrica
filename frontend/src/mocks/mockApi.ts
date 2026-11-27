/**
 * MOCK API: in-memory stand-in for the §10 routes until the real ones land.
 *
 * Loaded only when import.meta.env.MODE === "mock" (`npm run dev:mock`) and by
 * tests. build-guard.ts refuses to build a production bundle in mock mode.
 *
 * Every mocked route is tagged `MOCK(<task>)` with the task that replaces it.
 * To find what is left to switch to the real API:  grep -rn "MOCK(" frontend/src
 *
 * Synthetic data only (CLAUDE.md). The mock password is not a real secret; it
 * carries the CANARY-T19 marker so secret scanners can recognise it as fake.
 */
import type { Course, LoginRequest, Me, Role, TotpRequest } from "../apiTypes";
import type { Transport } from "../api";
import { contentHandler } from "./content";
import { gradingHandler } from "./grading";
import { oversightHandler } from "./oversight";
import { studentHandler } from "./student";
import { error, json, noContent, type MockContext, type MockHandler, type MockRequest } from "./http";
import { createWorld, ENROLLMENTS, MOCK_COURSES, MOCK_PASSWORD, MOCK_TOTP_CODE, MOCK_USERS, type MockUser } from "./state";

export { MOCK_COURSES, MOCK_PASSWORD, MOCK_TOTP_CODE, MOCK_USERS, SEED_IDS } from "./state";

/** Re-auth window from 01-interfaces.md §4.1 (C28): 5 minutes. */
const REAUTH_WINDOW_MS = 5 * 60 * 1000;

export interface MockOptions {
  /** Treat the sign-in TOTP as stale, so the first re-auth-protected action opens the modal (tests). */
  staleReauth?: boolean;
  now?: () => number;
}

const HANDLERS: readonly MockHandler[] = [contentHandler, gradingHandler, oversightHandler, studentHandler];

type Session = { state: "none" } | { state: "pending_totp"; user: MockUser } | { state: "active"; user: MockUser };

async function readBody(init: RequestInit): Promise<unknown> {
  if (init.body instanceof FormData) return init.body;
  if (typeof init.body !== "string") return undefined;
  try {
    return JSON.parse(init.body) as unknown;
  } catch {
    return undefined;
  }
}

export function createMockTransport(options: MockOptions = {}): Transport {
  const now = options.now ?? (() => Date.now());
  const world = createWorld(now());
  let session: Session = { state: "none" };
  let reauthAt: number | null = null;
  let csrfToken = "";
  let counter = 0;

  return async (url, init) => {
    const method = (init.method ?? "GET").toUpperCase();
    const path = new URL(url, "http://mock.invalid").pathname;
    const headers = new Headers(init.headers);
    const body = await readBody(init);

    // Mirror §4.1: state-changing calls need the CSRF token from GET /auth/csrf.
    if (method !== "GET" && (csrfToken === "" || headers.get("X-CSRF-Token") !== csrfToken)) {
      return error(403, "csrf_invalid");
    }

    // MOCK(E4): §10 GET /auth/csrf
    if (method === "GET" && path === "/api/auth/csrf") {
      counter += 1;
      csrfToken = `mock-csrf-${counter}`;
      return json(200, { csrf_token: csrfToken });
    }

    // MOCK(E4): §10 POST /auth/login (instructors continue with TOTP, C27)
    if (method === "POST" && path === "/api/auth/login") {
      const b = (body ?? {}) as Partial<LoginRequest>;
      const user = MOCK_USERS.find((u) => u.email === b.email);
      if (!user || b.password !== MOCK_PASSWORD) return error(401, "invalid_credentials");
      if (user.role === "instructor") {
        session = { state: "pending_totp", user };
        return json(200, { status: "totp_required" });
      }
      session = { state: "active", user };
      return json(200, { status: "ok" });
    }

    // MOCK(E4): §10 POST /auth/totp
    if (method === "POST" && path === "/api/auth/totp") {
      const b = (body ?? {}) as Partial<TotpRequest>;
      if (session.state !== "pending_totp") return error(401, "unauthenticated");
      if (b.code !== MOCK_TOTP_CODE) return error(401, "totp_invalid");
      session = { state: "active", user: session.user };
      reauthAt = options.staleReauth ? null : now();
      return noContent();
    }

    // MOCK(E4): §10 POST /auth/reauth (C28)
    if (method === "POST" && path === "/api/auth/reauth") {
      const b = (body ?? {}) as Partial<TotpRequest>;
      if (session.state !== "active") return error(401, "unauthenticated");
      if (b.code !== MOCK_TOTP_CODE) return error(401, "totp_invalid");
      reauthAt = now();
      return noContent();
    }

    // MOCK(E4): §10 POST /auth/logout
    if (method === "POST" && path === "/api/auth/logout") {
      session = { state: "none" };
      reauthAt = null;
      csrfToken = "";
      return noContent();
    }

    if (session.state !== "active") return error(401, "unauthenticated");
    const user = session.user;

    // MOCK(E4): §10 GET /me
    if (method === "GET" && path === "/api/me") {
      const me: Me = { id: user.id, display_name: user.display_name, role: user.role };
      return json(200, me);
    }

    // MOCK(E4): §10 GET /courses
    if (method === "GET" && path === "/api/courses") {
      const ids = ENROLLMENTS[user.id] ?? [];
      const role: Role = user.role;
      const courses: Course[] = MOCK_COURSES.filter((c) => ids.includes(c.id)).map((c) => ({ ...c, role }));
      return json(200, courses);
    }

    const req: MockRequest = { method, path, body };
    const ctx: MockContext = {
      world,
      user,
      now,
      reauthFresh: () => reauthAt !== null && now() - reauthAt <= REAUTH_WINDOW_MS,
      enrolledIn: (courseId) => (ENROLLMENTS[user.id] ?? []).includes(courseId),
    };
    for (const handler of HANDLERS) {
      const response = handler(req, ctx);
      if (response) return response;
    }
    return error(404, "not_found");
  };
}
