/**
 * MOCK API: in-memory stand-in for the §10 routes until E4 (identity) lands.
 *
 * Loaded only when import.meta.env.MODE === "mock" (`npm run dev:mock`) and by
 * tests. build-guard.ts refuses to build a production bundle in mock mode.
 *
 * Every mocked route is tagged `MOCK(<task>)`. To find what is left to switch
 * to the real API:  grep -rn "MOCK(" frontend/src
 *
 * Synthetic data only (CLAUDE.md). The mock password is not a real secret; it
 * carries the CANARY-T19 marker so secret scanners can recognise it as fake.
 */
import type { Course, LoginRequest, Me, Role, TotpRequest } from "../apiTypes";
import type { Transport } from "../api";

export const MOCK_PASSWORD = "mock-only-CANARY-T19";
export const MOCK_TOTP_CODE = "123456";

interface MockUser extends Me {
  email: string;
}

export const MOCK_USERS: readonly MockUser[] = [
  { id: "00000000-0000-4000-8000-000000000001", email: "student1@example.test", display_name: "Student One", role: "student" },
  { id: "00000000-0000-4000-8000-000000000002", email: "instructor1@example.test", display_name: "Instructor One", role: "instructor" },
];

export const MOCK_COURSES: readonly Omit<Course, "role">[] = [
  { id: "00000000-0000-4000-8000-0000000000c1", code: "SEC-101", title: "Synthetic Course: AI Security" },
  { id: "00000000-0000-4000-8000-0000000000c2", code: "SEC-202", title: "Synthetic Course: Secure Systems" },
];

const ENROLLMENTS: Record<string, readonly string[]> = {
  [MOCK_USERS[0]!.id]: [MOCK_COURSES[0]!.id, MOCK_COURSES[1]!.id],
  [MOCK_USERS[1]!.id]: [MOCK_COURSES[0]!.id],
};

type Session = { state: "none" } | { state: "pending_totp"; user: MockUser } | { state: "active"; user: MockUser };

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function error(status: number, code: string): Response {
  return json(status, { error: code });
}

async function readBody<T>(init: RequestInit): Promise<Partial<T>> {
  if (typeof init.body !== "string") return {};
  try {
    return JSON.parse(init.body) as Partial<T>;
  } catch {
    return {};
  }
}

export function createMockTransport(): Transport {
  let session: Session = { state: "none" };
  let csrfToken = "";
  let counter = 0;

  return async (url, init) => {
    const method = (init.method ?? "GET").toUpperCase();
    const path = new URL(url, "http://mock.invalid").pathname;
    const headers = new Headers(init.headers);

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
      const body = await readBody<LoginRequest>(init);
      const user = MOCK_USERS.find((u) => u.email === body.email);
      if (!user || body.password !== MOCK_PASSWORD) return error(401, "invalid_credentials");
      if (user.role === "instructor") {
        session = { state: "pending_totp", user };
        return json(200, { status: "totp_required" });
      }
      session = { state: "active", user };
      return json(200, { status: "ok" });
    }

    // MOCK(E4): §10 POST /auth/totp
    if (method === "POST" && path === "/api/auth/totp") {
      const body = await readBody<TotpRequest>(init);
      if (session.state !== "pending_totp") return error(401, "unauthenticated");
      if (body.code !== MOCK_TOTP_CODE) return error(401, "totp_invalid");
      session = { state: "active", user: session.user };
      return new Response(null, { status: 204 });
    }

    // MOCK(E4): §10 POST /auth/reauth (C28)
    if (method === "POST" && path === "/api/auth/reauth") {
      const body = await readBody<TotpRequest>(init);
      if (session.state !== "active") return error(401, "unauthenticated");
      if (body.code !== MOCK_TOTP_CODE) return error(401, "totp_invalid");
      return new Response(null, { status: 204 });
    }

    // MOCK(E4): §10 POST /auth/logout
    if (method === "POST" && path === "/api/auth/logout") {
      session = { state: "none" };
      csrfToken = "";
      return new Response(null, { status: 204 });
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

    return error(404, "not_found");
  };
}
