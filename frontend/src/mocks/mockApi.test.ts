import { describe, expect, it } from "vitest";
import { authRoutes, createApiClient } from "../api";
import { createMockTransport, MOCK_PASSWORD, MOCK_TOTP_CODE } from "./mockApi";

function setup() {
  const api = createApiClient({ transport: createMockTransport() });
  return { api, routes: authRoutes(api) };
}

describe("mock API (MOCK(E4))", () => {
  it("returns 401 for /me before sign-in", async () => {
    const { routes } = setup();
    await expect(routes.me()).rejects.toMatchObject({ status: 401, code: "unauthenticated" });
  });

  it("signs a student in directly", async () => {
    const { routes } = setup();
    await expect(routes.login({ email: "student1@example.test", password: MOCK_PASSWORD })).resolves.toEqual({ status: "ok" });
    await expect(routes.me()).resolves.toMatchObject({ role: "student" });
    await expect(routes.courses()).resolves.toHaveLength(2);
  });

  it("requires TOTP for instructors (C27)", async () => {
    const { routes } = setup();
    await expect(routes.login({ email: "instructor1@example.test", password: MOCK_PASSWORD })).resolves.toEqual({
      status: "totp_required",
    });
    await expect(routes.me()).rejects.toMatchObject({ status: 401 });
    await expect(routes.totp({ code: "000000" })).rejects.toMatchObject({ code: "totp_invalid" });
    await routes.totp({ code: MOCK_TOTP_CODE });
    await expect(routes.me()).resolves.toMatchObject({ role: "instructor" });
  });

  it("rejects a wrong password", async () => {
    const { routes } = setup();
    await expect(routes.login({ email: "student1@example.test", password: "wrong" })).rejects.toMatchObject({
      status: 401,
      code: "invalid_credentials",
    });
  });

  it("rejects state-changing calls without the CSRF token (§4.1)", async () => {
    const transport = createMockTransport();
    const response = await transport("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "student1@example.test", password: MOCK_PASSWORD }),
    });
    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual({ error: "csrf_invalid" });
  });

  it("ends the session on logout", async () => {
    const { api, routes } = setup();
    await routes.login({ email: "student1@example.test", password: MOCK_PASSWORD });
    await routes.logout();
    api.resetSession();
    await expect(routes.me()).rejects.toMatchObject({ status: 401 });
  });
});
