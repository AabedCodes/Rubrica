import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { createApiClient } from "./api";
import { App } from "./App";
import { createMockTransport, MOCK_COURSES, MOCK_PASSWORD, MOCK_TOTP_CODE } from "./mocks/mockApi";
import { safeNext } from "./pages/LoginPage";
import { csrfHandler, jsonResponse, recordingTransport } from "./test/helpers";

const COURSE = MOCK_COURSES[0]!.id;

function renderApp(path = "/", api = createApiClient({ transport: createMockTransport() })) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App api={api} />
    </MemoryRouter>,
  );
  return api;
}

async function signIn(email: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), MOCK_PASSWORD);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  return user;
}

describe("app shell (A1)", () => {
  it("sends a signed-out visitor to the login page", async () => {
    renderApp(`/courses/${COURSE}/assignments`);
    expect(await screen.findByRole("heading", { name: "Sign in to Rubrica" })).toBeTruthy();
  });

  it("signs a student in, returns them to the page they asked for, and shows student navigation only", async () => {
    renderApp(`/courses/${COURSE}/assignments`);
    await signIn("student1@example.test");

    expect(await screen.findByRole("heading", { name: "Assignments" })).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Course" });
    expect(within(nav).getByRole("link", { name: "My grades" })).toBeTruthy();
    expect(within(nav).queryByRole("link", { name: "Audit log" })).toBeNull();
    expect(within(nav).queryByRole("link", { name: "Materials" })).toBeNull();
  });

  it("shows a student 'Not available' for an instructor-only screen", async () => {
    renderApp(`/courses/${COURSE}/audit`);
    await signIn("student1@example.test");
    expect(await screen.findByRole("heading", { name: "Not available" })).toBeTruthy();
  });

  it("takes an instructor through TOTP (C27) and shows instructor navigation", async () => {
    renderApp(`/courses/${COURSE}`);
    const user = await signIn("instructor1@example.test");

    await user.type(await screen.findByLabelText("Authenticator code"), MOCK_TOTP_CODE);
    await user.click(screen.getByRole("button", { name: "Verify" }));

    const nav = await screen.findByRole("navigation", { name: "Course" });
    expect(within(nav).getByRole("link", { name: "Audit log" })).toBeTruthy();
    expect(within(nav).queryByRole("link", { name: "My grades" })).toBeNull();
  });

  it("shows an error for a wrong password and clears the password field", async () => {
    renderApp("/login");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "student1@example.test");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Email or password is wrong.");
    expect((screen.getByLabelText("Password") as HTMLInputElement).value).toBe("");
  });

  it("lists the user's courses in the course switcher and navigates on change", async () => {
    renderApp("/");
    const user = await signIn("student1@example.test");

    const select = await screen.findByLabelText("Course");
    await screen.findByRole("option", { name: /SEC-202/ });
    await user.selectOptions(select, MOCK_COURSES[1]!.id);
    expect(await screen.findByRole("heading", { name: "Course overview" })).toBeTruthy();
    expect((select as HTMLSelectElement).value).toBe(MOCK_COURSES[1]!.id);
  });

  it("signs out", async () => {
    renderApp("/");
    const user = await signIn("student1@example.test");
    await user.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in to Rubrica" })).toBeTruthy();
  });

  it("opens the re-auth modal on 401 reauth_required and retries the request after a valid code (C28)", async () => {
    let approveCalls = 0;
    const { transport, calls } = recordingTransport(
      csrfHandler(),
      (c) => (c.url === "/api/me" ? jsonResponse(200, { id: "i1", display_name: "Instructor One", role: "instructor" }) : undefined),
      (c) => (c.url === "/api/courses" ? jsonResponse(200, []) : undefined),
      (c) => (c.url === "/api/auth/reauth" ? new Response(null, { status: 204 }) : undefined),
      (c) => {
        if (c.url !== "/api/proposed-grades/approve") return undefined;
        approveCalls += 1;
        return approveCalls === 1 ? jsonResponse(401, { error: "reauth_required" }) : jsonResponse(200, { approved: 1 });
      },
    );
    const api = renderApp("/", createApiClient({ transport }));
    await screen.findByRole("heading", { name: "Your courses" });

    const pending = api.post("/proposed-grades/approve", { ids: ["g1"] });
    const dialog = await screen.findByRole("dialog", { name: "Confirm it's you" });
    const user = userEvent.setup();
    await user.type(within(dialog).getByLabelText("Authenticator code"), "654321");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    await expect(pending).resolves.toEqual({ approved: 1 });
    expect(approveCalls).toBe(2);
    expect(calls.find((c) => c.url === "/api/auth/reauth")?.body).toEqual({ code: "654321" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("safeNext", () => {
  it("only allows same-site paths as the post-login destination", () => {
    expect(safeNext("/courses/1")).toBe("/courses/1");
    expect(safeNext("//attacker.example")).toBe("/");
    expect(safeNext("https://attacker.example")).toBe("/");
    expect(safeNext(undefined)).toBe("/");
  });
});
