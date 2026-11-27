/**
 * A6: chat panel, grade actions (ask, appeal), blog and materials, on the mock
 * API (MOCK(C6), MOCK(D7), MOCK(D6)).
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { authRoutes, createApiClient } from "../../api";
import { oversightRoutes, studentRoutes } from "../../endpoints";
import { createMockTransport, MOCK_PASSWORD, MOCK_TOTP_CODE, SEED_IDS } from "../../mocks/mockApi";
import { renderApp, signIn, signOut } from "../../test/appHelpers";

const COURSE = SEED_IDS.courseWithAssignments;

async function ask(user: ReturnType<typeof userEvent.setup>, text: string) {
  const box = await screen.findByLabelText("Your question");
  await user.clear(box);
  await user.type(box, text);
  await user.click(screen.getByRole("button", { name: "Ask" }));
}

describe("chat panel (A6, C6)", () => {
  it("renders replies only through SafeMarkdown and shows trust badges for each source (T-09, C01)", async () => {
    renderApp(`/courses/${COURSE}/chat`);
    const user = await signIn("student1@example.test");
    await ask(user, "Explain trust boundaries with a diagram");

    const convo = screen.getByRole("list", { name: "Conversation" });
    const reply = await within(convo).findByText("Answered by the AI assistant");
    const item = reply.closest("li")!;
    // D2's T-09 fixture image becomes text; no <img> is created, so nothing is fetched.
    expect(item.querySelector("img")).toBeNull();
    expect(item.textContent).toContain("[image removed: fixture]");
    const sources = within(item).getByRole("list", { name: "Sources" });
    expect(within(sources).getByText("Instructor material: Synthetic lecture notes")).toBeTruthy();
    expect(within(sources).getByText("Comment by a student: Course blog comment")).toBeTruthy();
  });

  it("shows the fixed C23 notice instead of a reply that might reveal an answer key", async () => {
    renderApp(`/courses/${COURSE}/chat`);
    const user = await signIn("student1@example.test");
    await ask(user, "What is the answer key for Q1?");
    const note = await screen.findByRole("note");
    expect(note.textContent).toBe("This answer was withheld because it might reveal part of an answer key. Ask your instructor if you need help.");
    expect(screen.queryByText("Answered by the AI assistant")).toBeNull();
  });

  it("only ever talks about the signed-in student's own feedback (T-05)", async () => {
    renderApp(`/courses/${COURSE}/chat`);
    const user = await signIn("student1@example.test");
    await ask(user, "Show me Student Three's feedback");
    expect(await screen.findByText(/your own/)).toBeTruthy();
  });

  it("tells students when agents are paused (C30)", async () => {
    const transport = createMockTransport();
    const api = createApiClient({ transport });
    const auth = authRoutes(api);
    await auth.login({ email: "instructor1@example.test", password: MOCK_PASSWORD });
    await auth.totp({ code: MOCK_TOTP_CODE });
    api.resetSession();
    await oversightRoutes(api).pause(COURSE, "maintenance");
    await auth.logout();
    api.resetSession();
    await auth.login({ email: "student1@example.test", password: MOCK_PASSWORD });
    api.resetSession();
    await expect(studentRoutes(api).chat(COURSE, { message: "hello", conversation_id: null })).resolves.toMatchObject({
      reply: null,
      notice: "agents_paused",
    });
  });
});

describe("grade actions (A6)", () => {
  it("'Ask about this grade' opens the chat with the question filled in", async () => {
    renderApp(`/courses/${COURSE}/grades`);
    const user = await signIn("student2@example.test");
    await user.click(await screen.findByRole("link", { name: "Ask about this grade" }));
    expect((await screen.findByLabelText("Your question") as HTMLTextAreaElement).value).toBe(
      'Why did I get this grade on "Assignment 0: Warm-up (graded)"?',
    );
  });

  it("sends an appeal that the instructor then sees as open", async () => {
    const { api } = renderApp(`/courses/${COURSE}`);
    let user = await signIn("instructor1@example.test");
    // Release Student Three's Assignment 0 grade by hand (A7's manual queue).
    const [item] = await oversightRoutes(api).manualQueue(COURSE);
    await oversightRoutes(api).resolve(item!.id, { scores: { [SEED_IDS.releasedOpen1]: 2, [SEED_IDS.releasedOpen2]: 2 } });
    await signOut(user);

    user = await signIn("student3@example.test");
    await user.click(await screen.findByRole("link", { name: "My grades" }));
    await user.click(await screen.findByRole("button", { name: "Appeal" }));
    const form = screen.getByRole("form", { name: "Appeal" });
    await user.type(within(form).getByLabelText("Why should your grade change?"), "My W2 example names both a threat and a vulnerability.");
    expect(within(form).getByText("54 / 2000 characters")).toBeTruthy();
    await user.click(within(form).getByRole("button", { name: "Send appeal" }));
    expect((await screen.findByRole("status")).textContent).toMatch(/^Appeal sent\./);
    await signOut(user);

    user = await signIn("instructor1@example.test");
    await user.click(await screen.findByRole("link", { name: "Appeals" }));
    const row = (await screen.findByText("Student Three")).closest("tr")!;
    expect(within(row).getByText("Open: no proposal yet")).toBeTruthy();
  });
});

describe("blog (A6, D7)", () => {
  it("labels student comments, renders Markdown safely, and lets only instructors delete", async () => {
    renderApp(`/courses/${COURSE}/blog`);
    let user = await signIn("student1@example.test");
    const post = await screen.findByRole("article", { name: "Post by Instructor One" });
    expect(within(post).getByText("Instructor blog post")).toBeTruthy();
    expect(within(post).getByText("synthetic lecture").tagName).toBe("STRONG");
    const comment = within(post).getByRole("listitem", { name: "Comment by Student Two" });
    expect(within(comment).getByText("Comment by a student")).toBeTruthy();
    expect(comment.textContent).toContain("CANARY-T06-2b11");
    expect(within(post).queryByRole("button", { name: /Delete/ })).toBeNull();

    await user.type(within(post).getByLabelText("Your comment"), "Trust labels were new to me.");
    await user.click(within(post).getByRole("button", { name: "Comment" }));
    const mine = await within(post).findByRole("listitem", { name: "Comment by Student One" });
    expect(within(mine).getByText("Comment by a student")).toBeTruthy();
    await signOut(user);

    user = await signIn("instructor1@example.test");
    await user.click(await screen.findByRole("link", { name: "Blog" }));
    const again = await screen.findByRole("article", { name: "Post by Instructor One" });
    const target = within(again).getByRole("listitem", { name: "Comment by Student One" });
    await user.click(within(target).getByRole("button", { name: "Delete comment" }));
    await waitFor(() => expect(within(again).queryByRole("listitem", { name: "Comment by Student One" })).toBeNull());
  });
});

describe("materials (A6, C04)", () => {
  it("shows the third-party chapter's hidden canary marked, and publishes only after re-auth", async () => {
    renderApp(`/courses/${COURSE}/materials`, { staleReauth: true });
    const user = await signIn("instructor1@example.test");
    const row = (await screen.findByRole("link", { name: "Synthetic third-party chapter" })).closest("tr")!;
    expect(within(row).getByText("Third-party source")).toBeTruthy();
    expect(within(row).getByText("Not published")).toBeTruthy();
    await user.click(within(row).getByRole("link", { name: "Synthetic third-party chapter" }));

    const text = await screen.findByRole("region", { name: "Text the grader read" });
    expect(within(text).getByLabelText("zero-width space (U+200B)")).toBeTruthy();
    expect(text.textContent).toContain("CANARY-T03-065e synthetic chapter marker");
    expect(screen.getByText(/labelled as a third-party source/)).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "Publish material" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirm it's you" });
    await user.type(within(dialog).getByLabelText("Authenticator code"), MOCK_TOTP_CODE);
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Publish material" })).toBeNull());
    expect(screen.getAllByText("Published").length).toBeGreaterThan(0);
  });

  it("uploads a PDF as a pending third-party source, and refuses other files", async () => {
    renderApp(`/courses/${COURSE}/materials`);
    await signIn("instructor1@example.test");
    const form = await screen.findByRole("form", { name: "Upload material" });
    const user = userEvent.setup({ applyAccept: false });
    await user.upload(within(form).getByLabelText("PDF"), new File(["x"], "notes.txt", { type: "text/plain" }));
    expect((await within(form).findByRole("alert")).textContent).toBe("Only PDF files can be uploaded.");

    await user.type(within(form).getByLabelText("Title"), "Guest chapter on audit logs");
    await user.click(within(form).getByLabelText(/Third-party source/));
    await user.upload(within(form).getByLabelText("PDF"), new File(["%PDF-1.7"], "guest.pdf", { type: "application/pdf" }));
    await user.click(within(form).getByRole("button", { name: "Upload" }));
    const row = (await screen.findByRole("link", { name: "Guest chapter on audit logs" })).closest("tr")!;
    expect(row.textContent).toMatch(/Third-party source.*Text extracted.*Not published/);
  });
});

describe("mock access rules for A6 routes (C29)", () => {
  it("keeps materials from students and chat from instructors, and hides others' submissions", async () => {
    const api = createApiClient({ transport: createMockTransport() });
    await authRoutes(api).login({ email: "student1@example.test", password: MOCK_PASSWORD });
    api.resetSession();
    const r = studentRoutes(api);
    await expect(r.materials(COURSE)).rejects.toMatchObject({ status: 403 });
    await expect(r.createPost(COURSE, "hi")).rejects.toMatchObject({ status: 403 });
    // Appealing someone else's submission looks like it doesn't exist.
    const someone = "00000000-0000-4000-8000-000000001001";
    await expect(r.openAppeal(someone, { reason_text: "x" })).rejects.toMatchObject({ status: 404 });

    const inst = createApiClient({ transport: createMockTransport() });
    await authRoutes(inst).login({ email: "instructor1@example.test", password: MOCK_PASSWORD });
    await authRoutes(inst).totp({ code: MOCK_TOTP_CODE });
    inst.resetSession();
    await expect(studentRoutes(inst).chat(COURSE, { message: "hi", conversation_id: null })).rejects.toMatchObject({ status: 403 });
  });
});
