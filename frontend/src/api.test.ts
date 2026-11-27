import { describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "./api";
import { csrfHandler, jsonResponse, recordingTransport } from "./test/helpers";

describe("api client (A1, §4.1, §10)", () => {
  it("sends GET requests to /api with same-origin credentials and no CSRF header", async () => {
    const { transport, calls } = recordingTransport((c) => (c.url === "/api/me" ? jsonResponse(200, { id: "u1" }) : undefined));
    const api = createApiClient({ transport });

    await expect(api.get("/me")).resolves.toEqual({ id: "u1" });

    expect(calls).toHaveLength(1);
    expect(calls[0]!.credentials).toBe("same-origin");
    expect(calls[0]!.headers.has("X-CSRF-Token")).toBe(false);
  });

  it("fetches the CSRF token once and sends it on every state-changing request", async () => {
    const { transport, calls } = recordingTransport(csrfHandler("tok-A"), (c) =>
      c.method !== "GET" ? jsonResponse(200, { ok: true }) : undefined,
    );
    const api = createApiClient({ transport });

    await api.post("/things", { a: 1 });
    await api.put("/things/1", { a: 2 });
    await api.delete("/things/1");

    expect(calls.filter((c) => c.url === "/api/auth/csrf")).toHaveLength(1);
    const writes = calls.filter((c) => c.method !== "GET");
    expect(writes.map((c) => c.headers.get("X-CSRF-Token"))).toEqual(["tok-A", "tok-A", "tok-A"]);
    expect(writes[0]!.body).toEqual({ a: 1 });
  });

  it("fetches a new CSRF token after resetSession (login, logout)", async () => {
    let n = 0;
    const { transport, calls } = recordingTransport(
      (c) => (c.url === "/api/auth/csrf" ? jsonResponse(200, { csrf_token: `tok-${++n}` }) : undefined),
      () => new Response(null, { status: 204 }),
    );
    const api = createApiClient({ transport });

    await api.post("/a");
    api.resetSession();
    await api.post("/b");

    expect(calls.filter((c) => c.method === "POST").map((c) => c.headers.get("X-CSRF-Token"))).toEqual(["tok-1", "tok-2"]);
  });

  it("on 401 reauth_required asks for re-auth, then retries exactly once (C28)", async () => {
    let attempts = 0;
    const { transport } = recordingTransport(csrfHandler(), (c) => {
      if (c.url !== "/api/proposed-grades/approve") return undefined;
      attempts += 1;
      return attempts === 1 ? jsonResponse(401, { error: "reauth_required" }) : jsonResponse(200, { approved: 2 });
    });
    const onReauthRequired = vi.fn(async () => true);
    const api = createApiClient({ transport, onReauthRequired });

    await expect(api.post("/proposed-grades/approve", { ids: ["g1", "g2"] })).resolves.toEqual({ approved: 2 });
    expect(onReauthRequired).toHaveBeenCalledTimes(1);
    expect(attempts).toBe(2);
  });

  it("does not retry a second time if the retry also needs re-auth", async () => {
    let attempts = 0;
    const { transport } = recordingTransport(csrfHandler(), (c) => {
      if (c.url !== "/api/x") return undefined;
      attempts += 1;
      return jsonResponse(401, { error: "reauth_required" });
    });
    const onReauthRequired = vi.fn(async () => true);
    const api = createApiClient({ transport, onReauthRequired });

    await expect(api.post("/x")).rejects.toMatchObject({ status: 401, code: "reauth_required" });
    expect(onReauthRequired).toHaveBeenCalledTimes(1);
    expect(attempts).toBe(2);
  });

  it("does not retry when the user cancels re-auth", async () => {
    const { transport, calls } = recordingTransport(csrfHandler(), (c) =>
      c.url === "/api/x" ? jsonResponse(401, { error: "reauth_required" }) : undefined,
    );
    const api = createApiClient({ transport, onReauthRequired: async () => false });

    await expect(api.post("/x")).rejects.toBeInstanceOf(ApiError);
    expect(calls.filter((c) => c.url === "/api/x")).toHaveLength(1);
  });

  it("asks for re-auth only once when several requests need it at the same time", async () => {
    const seen = new Map<string, number>();
    const { transport } = recordingTransport(csrfHandler(), (c) => {
      const n = (seen.get(c.url) ?? 0) + 1;
      seen.set(c.url, n);
      return n === 1 ? jsonResponse(401, { error: "reauth_required" }) : jsonResponse(200, { url: c.url });
    });
    let release!: (ok: boolean) => void;
    const onReauthRequired = vi.fn(() => new Promise<boolean>((resolve) => (release = resolve)));
    const api = createApiClient({ transport, onReauthRequired });

    const both = Promise.all([api.post("/a"), api.post("/b")]);
    await vi.waitFor(() => expect(onReauthRequired).toHaveBeenCalled());
    release(true);

    await expect(both).resolves.toEqual([{ url: "/api/a" }, { url: "/api/b" }]);
    expect(onReauthRequired).toHaveBeenCalledTimes(1);
  });

  it("does not trigger re-auth for calls that opt out (login, the re-auth call itself)", async () => {
    const { transport } = recordingTransport(csrfHandler(), () => jsonResponse(401, { error: "reauth_required" }));
    const onReauthRequired = vi.fn(async () => true);
    const api = createApiClient({ transport, onReauthRequired });

    await expect(api.post("/auth/reauth", { code: "1" }, { allowReauth: false })).rejects.toBeInstanceOf(ApiError);
    expect(onReauthRequired).not.toHaveBeenCalled();
  });

  it("maps a non-JSON error body to code 'unknown'", async () => {
    const { transport } = recordingTransport(() => new Response("<html>bad gateway</html>", { status: 502 }));
    const api = createApiClient({ transport });

    await expect(api.get("/me")).rejects.toMatchObject({ status: 502, code: "unknown" });
  });

  it("drops the CSRF token after 403 csrf_invalid so the next write fetches a fresh one", async () => {
    let n = 0;
    let first = true;
    const { transport, calls } = recordingTransport(
      (c) => (c.url === "/api/auth/csrf" ? jsonResponse(200, { csrf_token: `tok-${++n}` }) : undefined),
      () => {
        if (first) {
          first = false;
          return jsonResponse(403, { error: "csrf_invalid" });
        }
        return jsonResponse(200, {});
      },
    );
    const api = createApiClient({ transport });

    await expect(api.post("/a")).rejects.toMatchObject({ code: "csrf_invalid" });
    await api.post("/a");
    expect(calls.filter((c) => c.method === "POST").map((c) => c.headers.get("X-CSRF-Token"))).toEqual(["tok-1", "tok-2"]);
  });

  it("refuses absolute and protocol-relative paths so it only ever calls our own /api", async () => {
    const { transport } = recordingTransport();
    const api = createApiClient({ transport });

    await expect(api.get("https://attacker.example/x")).rejects.toThrow();
    await expect(api.get("//attacker.example/x")).rejects.toThrow();
    expect(transport).not.toHaveBeenCalled();
  });

  it("never touches Web Storage (T-10)", async () => {
    const getItem = vi.spyOn(Storage.prototype, "getItem");
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const { transport } = recordingTransport(csrfHandler(), (c) =>
      c.url === "/api/x" && c.headers.get("X-CSRF-Token") ? jsonResponse(200, {}) : undefined,
    );
    const api = createApiClient({ transport });

    await api.post("/x");
    await api.get("/x").catch(() => undefined);

    expect(getItem).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
  });
});
