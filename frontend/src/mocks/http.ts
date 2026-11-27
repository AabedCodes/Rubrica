/** MOCK helpers shared by the mocked route handlers. */
import type { MockUser, MockWorld } from "./state";

export interface MockRequest {
  method: string;
  path: string;
  /** Parsed JSON body, or the FormData for multipart uploads. */
  body: unknown;
}

export interface MockContext {
  world: MockWorld;
  user: MockUser;
  now(): number;
  /** True if the user's last TOTP entry is inside the re-auth window (C28). */
  reauthFresh(): boolean;
  enrolledIn(courseId: string): boolean;
}

/** A handler returns undefined when the request isn't one of its routes. */
export type MockHandler = (req: MockRequest, ctx: MockContext) => Response | undefined;

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export function error(status: number, code: string): Response {
  return json(status, { error: code });
}

export const noContent = () => new Response(null, { status: 204 });

/** Matches `path` against a pattern like "/api/assignments/:id/rubric". */
export function route(method: string, pattern: string, req: MockRequest): Record<string, string> | null {
  if (req.method !== method) return null;
  const want = pattern.split("/");
  const got = req.path.split("/");
  if (want.length !== got.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < want.length; i++) {
    const w = want[i]!;
    const g = got[i]!;
    if (w.startsWith(":")) params[w.slice(1)] = decodeURIComponent(g);
    else if (w !== g) return null;
  }
  return params;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) && !(value instanceof FormData);
}
