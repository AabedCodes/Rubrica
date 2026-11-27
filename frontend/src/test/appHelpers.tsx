import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { createApiClient } from "../api";
import { App } from "../App";
import { createMockTransport, MOCK_PASSWORD, MOCK_TOTP_CODE, type MockOptions } from "../mocks/mockApi";

/** Renders the whole app on the mock API. One transport = one mock world. */
export function renderApp(path = "/", options: MockOptions = {}) {
  const transport = createMockTransport(options);
  const api = createApiClient({ transport });
  render(
    <MemoryRouter initialEntries={[path]}>
      <App api={api} />
    </MemoryRouter>,
  );
  return { api, transport };
}

export async function signIn(email: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), MOCK_PASSWORD);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  if (email.startsWith("instructor")) {
    await user.type(await screen.findByLabelText("Authenticator code"), MOCK_TOTP_CODE);
    await user.click(screen.getByRole("button", { name: "Verify" }));
  }
  return user;
}

export async function signOut(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Sign out" }));
  await screen.findByRole("heading", { name: "Sign in to Rubrica" });
}
