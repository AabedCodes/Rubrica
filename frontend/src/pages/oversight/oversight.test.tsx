/**
 * A7: confirmation screens (C25, T-02), manual queue, audit view (R9, C37) and
 * the pause switch (C30), on the mock API (MOCK(C7), MOCK(D3), MOCK(E10), MOCK(E11)).
 */
import { screen, waitFor, within } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { authRoutes, createApiClient } from "../../api";
import { gradingRoutes, oversightRoutes } from "../../endpoints";
import { createMockTransport, MOCK_PASSWORD, MOCK_TOTP_CODE, SEED_IDS } from "../../mocks/mockApi";
import { renderApp, signIn, signOut } from "../../test/appHelpers";
import { acceptEffect } from "./ProposalConfirmPage";

const COURSE = SEED_IDS.courseWithAssignments;

async function confirmReauth(user: UserEvent) {
  const dialog = await screen.findByRole("dialog", { name: "Confirm it's you" });
  await user.type(within(dialog).getByLabelText("Authenticator code"), MOCK_TOTP_CODE);
  await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
}

describe("grade-change confirmation (C25, T-02)", () => {
  it("shows database numbers, not the agent's claims; labels who wrote what; needs re-auth; the student sees the result", async () => {
    renderApp(`/courses/${COURSE}/appeals`, { staleReauth: true });
    let user = await signIn("instructor1@example.test");
    await user.click(await screen.findByRole("link", { name: "Review proposal" }));

    const table = await screen.findByRole("table", { name: "Current and proposed scores" });
    const totals = within(table).getByRole("row", { name: /^Total/ });
    expect(within(totals).getAllByRole("cell").map((c) => c.textContent)).toEqual(["8", "4.5", "6.5"]);

    // The AI rationale claims "8 / 8"; the effect line and the table show the stored 6.5.
    const ai = screen.getByRole("region", { name: "Written by the AI assistant" });
    expect(ai.textContent).toContain("total 8 / 8");
    expect(screen.getByText(/so the released total goes from 4.5 to 6.5 out of 8/)).toBeTruthy();

    // The student's appeal, with D2's seeded canary, is shown as plain text in its own box.
    const student = screen.getByRole("region", { name: "Written by the student" });
    expect(student.textContent).toContain("CANARY-T02-062e synthetic appeal");

    await user.click(screen.getByRole("button", { name: "Accept proposal" }));
    await confirmReauth(user);
    expect(await screen.findByText(/^Accepted by Instructor One/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Accept proposal" })).toBeNull();
    await signOut(user);

    user = await signIn("student2@example.test");
    await user.click(await screen.findByRole("link", { name: "Assignments" }));
    await user.click(await screen.findByRole("link", { name: "My grades" }));
    expect(await screen.findByRole("heading", { name: "Grade: 6.5 / 8" })).toBeTruthy();
  });

  it("describes the effect from the stored values only", () => {
    const effect = acceptEffect({
      criteria: [
        { criterion_id: "a", label: "W1. x", kind: "open", max_points: 4, current: 2, proposed: 3 },
        { criterion_id: "b", label: "W2. y", kind: "open", max_points: 4, current: 2.5, proposed: 2.5 },
      ],
      current_total: 4.5,
      proposed_total: 5.5,
      max_total: 8,
    } as Parameters<typeof acceptEffect>[0]);
    expect(effect).toBe(
      "Accepting changes W1 from 2 to 3, so the released total goes from 4.5 to 5.5 out of 8. The student sees the new grade, and the change is audited.",
    );
  });
});

describe("draft confirmation (C25)", () => {
  it("accepts an assignment draft as a new DRAFT assignment, without re-auth", async () => {
    renderApp(`/courses/${COURSE}/drafts`, { staleReauth: true });
    const user = await signIn("instructor1@example.test");
    const rows = await screen.findAllByRole("link", { name: "Review draft" });
    await user.click(rows[0]!);
    expect(await screen.findByText(/Accepting creates a new DRAFT assignment "Assignment 3: Logging and monitoring" with 2 criteria/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Accept draft" }));
    expect(await screen.findByText("This draft was accepted.")).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();

    await user.click(screen.getByRole("link", { name: "Assignments" }));
    const row = (await screen.findByRole("link", { name: "Assignment 3: Logging and monitoring" })).closest("tr")!;
    expect(within(row).getByText("Draft")).toBeTruthy();
  });

  it("needs re-auth to accept an answer-key draft (§10)", async () => {
    renderApp(`/courses/${COURSE}/drafts`, { staleReauth: true });
    const user = await signIn("instructor1@example.test");
    const rows = await screen.findAllByRole("link", { name: "Review draft" });
    await user.click(rows[1]!);
    expect(await screen.findByText(/This needs your authenticator code/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Accept draft" }));
    await confirmReauth(user);
    expect(await screen.findByText("This draft was accepted.")).toBeTruthy();
  });
});

describe("manual queue (C37)", () => {
  it("explains the reason in plain words and releases the instructor's in-range scores", async () => {
    renderApp(`/courses/${COURSE}/manual-queue`);
    const user = await signIn("instructor1@example.test");
    const row = (await screen.findByRole("link", { name: "Student Three" })).closest("tr")!;
    expect(within(row).getByText("Grader output failed validation")).toBeTruthy();
    await user.click(within(row).getByRole("link", { name: "Student Three" }));

    const w1 = await screen.findByLabelText(/^W1\./);
    await user.type(w1, "5");
    expect((await screen.findByRole("alert")).textContent).toBe("From 0 to 4 in steps of 0.5.");
    expect((screen.getByRole("button", { name: "Release my grade" }) as HTMLButtonElement).disabled).toBe(true);
    await user.clear(w1);
    await user.type(w1, "3");
    await user.type(screen.getByLabelText(/^W2\./), "3.5");
    expect(screen.getByText(/Submitting releases this grade \(6.5 \/ 8\)/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Release my grade" }));
    expect(await screen.findByText(/^Graded and released on/)).toBeTruthy();
  });
});

describe("audit view (R9, C37; demo step 7)", () => {
  it("shows before/after values from approval, the T-05 denial, the chain status and the full-marks alert", async () => {
    const { api } = renderApp(`/courses/${COURSE}`);
    const user = await signIn("instructor1@example.test");
    await screen.findByRole("navigation", { name: "Course" });

    // Grade Assignment 1 (the CANARY-T04 submission gets full marks) and approve it with a change, as on A5's screen.
    const grading = gradingRoutes(api);
    await grading.startRun(SEED_IDS.publishedAssignment);
    const four = (await grading.proposedGrades(SEED_IDS.publishedAssignment)).find((r) => r.student.display_name === "Student Four")!;
    await grading.approve({ proposed_grade_ids: [four.id], score_changes: { [four.id]: { [SEED_IDS.openCriterion1]: 1.5 } } });

    await user.click(screen.getByRole("link", { name: "Audit log" }));
    expect(await screen.findByText(/Hash chain intact/)).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toMatch(/Alert: full marks rate \(high\)/);

    const table = screen.getByRole("table", { name: "Audit rows" });
    const approve = within(table)
      .getAllByRole("row")
      .find((r) => r.textContent?.includes("approve_release") && r.textContent.includes("→"))!;
    expect(approve.textContent).toContain("5 → 1.5");
    expect(approve.textContent).toContain("Instructor One");

    // Filter to denials: the chat agent's refused get_my_feedback (T-05).
    await user.selectOptions(screen.getByLabelText("Decision"), "denied");
    const denied = within(table).getAllByRole("row").slice(1);
    expect(denied).toHaveLength(1);
    expect(denied[0]!.textContent).toMatch(/chat-agent.*get_my_feedback.*denied.*E_NOT_FOUND/);
  });
});

describe("pause switch (C30)", () => {
  it("pauses with a reason and re-auth, shows the banner, routes grading to the manual queue, and resumes", async () => {
    renderApp(`/courses/${COURSE}/settings`, { staleReauth: true });
    let user = await signIn("instructor1@example.test");

    await user.type(await screen.findByLabelText(/^Reason/), "Investigating unusual full-marks rate");
    await user.click(screen.getByRole("button", { name: "Pause AI agents for this course" }));
    await confirmReauth(user);
    expect(await screen.findByText(/AI agents are paused for this course/)).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Investigating unusual full-marks rate");

    // The banner follows the instructor to other course pages, and grading goes to the manual queue.
    await user.click(screen.getByRole("link", { name: "Assignments" }));
    expect(await screen.findByText(/AI agents are paused for this course/)).toBeTruthy();
    const a1 = (await screen.findByRole("link", { name: "Assignment 1: Threat modelling basics" })).closest("tr")!;
    await user.click(within(a1).getByRole("link", { name: "Review grades" }));
    await user.click(await screen.findByRole("button", { name: "Start grading run" }));
    expect(await screen.findByText("AI agents are paused: 3 submissions sent to the manual queue.")).toBeTruthy();
    await user.click(screen.getByRole("link", { name: "Manual queue" }));
    expect((await screen.findAllByText("Grading paused")).length).toBe(3);

    // Students see a gentler notice and can still work.
    await signOut(user);
    user = await signIn("student1@example.test");
    await screen.findByRole("option", { name: /SEC-101/ }); // the switcher loads its courses first
    await user.selectOptions(screen.getByRole("combobox", { name: "Course" }), COURSE);
    expect(await screen.findByText("Grading may take longer than usual. You can still submit your work.")).toBeTruthy();
    await signOut(user);

    user = await signIn("instructor1@example.test");
    await screen.findByRole("option", { name: /SEC-101/ }); // the switcher loads its courses first
    await user.selectOptions(screen.getByRole("combobox", { name: "Course" }), COURSE);
    await user.click(await screen.findByRole("link", { name: "Course settings" }));
    await user.click(await screen.findByRole("button", { name: "Resume AI agents" }));
    await confirmReauth(user); // resume needs re-auth too (C28, C30)
    await waitFor(() => expect(screen.queryByText(/AI agents are paused for this course/)).toBeNull());
  });
});

describe("mock access rules for A7 routes (C29)", () => {
  it("refuses students, answering 404 for per-record routes (§10.1)", async () => {
    const api = createApiClient({ transport: createMockTransport() });
    await authRoutes(api).login({ email: "student1@example.test", password: MOCK_PASSWORD });
    api.resetSession();
    const o = oversightRoutes(api);
    for (const call of [o.appeals(COURSE), o.drafts(COURSE), o.manualQueue(COURSE), o.audit(COURSE), o.pause(COURSE, "x")]) {
      await expect(call).rejects.toMatchObject({ status: 403 });
    }
    const instructorApi = createApiClient({ transport: createMockTransport() });
    await authRoutes(instructorApi).login({ email: "instructor1@example.test", password: MOCK_PASSWORD });
    await authRoutes(instructorApi).totp({ code: MOCK_TOTP_CODE });
    instructorApi.resetSession();
    const [appeal] = await oversightRoutes(instructorApi).appeals(COURSE);
    await expect(o.proposal(appeal!.proposal_id!)).rejects.toMatchObject({ status: 404 });
    // Any member may read the pause state, so students see the notice.
    await expect(o.controls(COURSE)).resolves.toMatchObject({ agents_paused: false });
  });

  it("rejects manual scores outside 0..max or off the 0.5 grid", async () => {
    const api = createApiClient({ transport: createMockTransport() });
    await authRoutes(api).login({ email: "instructor1@example.test", password: MOCK_PASSWORD });
    await authRoutes(api).totp({ code: MOCK_TOTP_CODE });
    api.resetSession();
    const o = oversightRoutes(api);
    const [item] = await o.manualQueue(COURSE);
    for (const bad of [5, -1, 1.25]) {
      await expect(o.resolve(item!.id, { scores: { [SEED_IDS.releasedOpen1]: bad, [SEED_IDS.releasedOpen2]: 1 } })).rejects.toMatchObject({ status: 400 });
    }
  });
});
