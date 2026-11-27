import { vi } from "vitest";
import type { Transport } from "../api";

export interface Call {
  url: string;
  method: string;
  headers: Headers;
  body: unknown;
  credentials: RequestCredentials | undefined;
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/**
 * A transport that answers from a list of handlers and records every call.
 * Each handler gets the call and returns a Response, or undefined to fall
 * through to the next one.
 */
export function recordingTransport(...handlers: ((call: Call) => Response | undefined)[]) {
  const calls: Call[] = [];
  const transport = vi.fn<Transport>(async (url, init) => {
    const call: Call = {
      url,
      method: init.method ?? "GET",
      headers: new Headers(init.headers),
      body: typeof init.body === "string" ? JSON.parse(init.body) : undefined,
      credentials: init.credentials,
    };
    calls.push(call);
    for (const handler of handlers) {
      const response = handler(call);
      if (response) return response;
    }
    return jsonResponse(404, { error: "not_found" });
  });
  return { transport, calls };
}

export const csrfHandler = (token = "csrf-1") => (call: Call) =>
  call.url === "/api/auth/csrf" ? jsonResponse(200, { csrf_token: token }) : undefined;
