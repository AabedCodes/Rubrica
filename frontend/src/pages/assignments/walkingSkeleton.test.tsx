/**
 * The walking skeleton through the real screens on the mock API (A2):
 * instructor creates an assignment with a rubric and key and publishes it;
 * a student submits; the instructor grades and approves; the student sees
 * the released grade. Steps 1–3 of the demo (docs/plan/README.md §5).
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SEED_IDS } from "../../mocks/mockApi";
import { renderApp, signIn, signOut } from "../../test/appHelpers";

const COURSE = SEED_IDS.courseWithAssignments;
const A1 = SEED_IDS.publishedAssignment;

describe("A2 instructor: create, rubric, key, publish", () => {
  it("creates a draft, validates and saves the rubric and key, and publishes after re-auth (C28)", async () => {
    renderApp(`/courses/${COURSE}/assignments`, { staleReauth: true });
    const user = await signIn("instructor1@example.test");

    await user.click(await screen.findByRole("link", { name: "New assignment" }));
    await user.type(await screen.findByLabelText("Title"), "Assignment 3: Logging");
    await user.type(screen.getByLabelText("Instructions"), "Answer both questions.");
    await user.type(screen.getByLabelText("Due"), "2099-01-15T12:00");
    await user.click(screen.getByRole("button", { name: "Create draft" }));

    expect(await screen.findByRole("heading", { name: "Assignment 3: Logging" })).toBeTruthy();
    expect(screen.getByText("Draft")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Publish assignment" }) as HTMLButtonElement).disabled).toBe(true);

    // Invalid rubric: blank label and 0 points are caught before saving.
    const rubric = screen.getByRole("form", { name: "Rubric" });
    await user.type(within(rubric).getByLabelText("Max points"), "0");
    await user.click(within(rubric).getByRole("button", { name: "Save rubric" }));
    const errors = await within(rubric).findByRole("alert");
    expect(errors.textContent).toMatch(/write a label/);
    expect(errors.textContent).toMatch(/more than 0/);

    // Fix it and add an objective criterion.
    await user.type(within(rubric).getByLabelText("Label"), "Explain what to log.");
    await user.clear(within(rubric).getByLabelText("Max points"));
    await user.type(within(rubric).getByLabelText("Max points"), "4");
    await user.click(within(rubric).getByRole("button", { name: "Add criterion" }));
    const labels = within(rubric).getAllByLabelText("Label");
    await user.type(labels[1]!, "Pick the log level (A-C).");
    await user.type(within(rubric).getAllByLabelText("Max points")[1]!, "1");
    await user.selectOptions(within(rubric).getAllByLabelText("Kind")[1]!, "objective");
    await user.click(within(rubric).getByRole("button", { name: "Save rubric" }));

    // After saving, the answer key editor has one entry per criterion.
    const key = await screen.findByRole("form", { name: "Answer key" });
    await user.type(within(key).getByLabelText("What a full-marks answer contains"), "Security events with actor and outcome.");
    await user.type(within(key).getByLabelText("Correct answer"), "B");
    await user.click(within(key).getByRole("button", { name: "Save answer key" }));
    expect(await within(key).findByText("draft")).toBeTruthy();

    // Publishing needs a fresh TOTP code: the re-auth modal opens, then the publish retries.
    await user.click(screen.getByRole("button", { name: "Publish assignment" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirm it's you" });
    await user.type(within(dialog).getByLabelText("Authenticator code"), "123456");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("Published")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Save rubric" })).toBeNull(); // rubric is read-only once published
  });
});

describe("A2 end to end: submit, grade, approve, release", () => {
  it("runs the demo's main flow and the student sees only the released grade (R10)", async () => {
    renderApp(`/courses/${COURSE}/assignments/${A1}`);

    // Student submits.
    let user = await signIn("student1@example.test");
    expect(await screen.findByRole("heading", { name: "Assignment 1: Threat modelling basics" })).toBeTruthy();
    const form = screen.getByRole("form", { name: "Submission" });
    await user.type(within(form).getByLabelText(/Q1\. Which STRIDE category/), "B");
    await user.type(within(form).getByLabelText("Your answer"), "Q2. Student text crosses into the model. Q3. Validate scores in code.");
    await user.upload(within(form).getByLabelText("PDF (optional)"), new File(["%PDF-1.7"], "answer.pdf", { type: "application/pdf" }));
    await user.click(within(form).getByRole("button", { name: "Submit" }));
    const current = await screen.findByRole("region", { name: "Your current submission" });
    expect(current.textContent).toContain("answer.pdf");
    expect(current.textContent).toContain("Validate scores in code.");
    expect(current.textContent).toMatch(/appears here once your instructor releases it/);
    await signOut(user);

    // Instructor runs grading and reviews.
    user = await signIn("instructor1@example.test");
    await user.click(await screen.findByRole("link", { name: "Assignments" }));
    // Two published assignments now (A7 seeds a graded Assignment 0); review Assignment 1.
    const a1Row = (await screen.findByRole("link", { name: "Assignment 1: Threat modelling basics" })).closest("tr")!;
    await user.click(within(a1Row).getByRole("link", { name: "Review grades" }));
    await user.click(await screen.findByRole("button", { name: "Start grading run" }));
    expect(await screen.findByText(/Grading run started for 4 submissions/)).toBeTruthy();

    const rows = await screen.findAllByRole("row");
    const body = rows.slice(1); // skip the header
    // Flagged first (C36); flagged rows can't be bulk-selected.
    expect(within(body[0]!).queryByText("Full marks") ?? within(body[0]!).queryByText("Attempts disagree")).not.toBeNull();
    const fourBox = screen.getByRole("checkbox", { name: "Select Student Four" }) as HTMLInputElement;
    expect(fourBox.disabled).toBe(true);
    expect(within(screen.getByText("Student Four").closest("tr")!).getByText("Full marks")).toBeTruthy();

    await user.click(screen.getByRole("checkbox", { name: "Select Student One" }));
    await user.click(screen.getByRole("button", { name: "Approve selected (1)" }));
    expect(await screen.findByText("Approved and released 1 grade.")).toBeTruthy();
    await waitFor(() => expect(within(screen.getByText("Student One").closest("tr")!).getByText("released")).toBeTruthy());
    await signOut(user);

    // Student sees the released grade with feedback, labelled as AI-written.
    user = await signIn("student1@example.test");
    await user.click(await screen.findByRole("link", { name: "My grades" }));
    const grade = await screen.findByRole("region", { name: "Your grade" });
    expect(within(grade).getByRole("heading", { name: /Grade: \d+(\.5)? \/ 10/ })).toBeTruthy();
    expect(within(grade).getAllByText("Written by the AI grader").length).toBeGreaterThan(0);
    expect(within(grade).getByText("Marked automatically")).toBeTruthy();
  });

  it("shows a student nothing about grades that are not released", async () => {
    renderApp(`/courses/${COURSE}/grades`);
    await signIn("student1@example.test");
    expect((await screen.findAllByText("Not submitted.")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("region", { name: "Your grade" })).toBeNull();
  });

  it("refuses a non-PDF attachment before sending anything", async () => {
    renderApp(`/courses/${COURSE}/assignments/${A1}`);
    await signIn("student1@example.test");
    const form = await screen.findByRole("form", { name: "Submission" });
    // applyAccept: false simulates a browser that lets the user pick any file.
    const user = userEvent.setup({ applyAccept: false });
    await user.upload(within(form).getByLabelText("PDF (optional)"), new File(["x"], "notes.txt", { type: "text/plain" }));
    expect((await within(form).findByRole("alert")).textContent).toBe("Only PDF files can be attached.");
    expect((within(form).getByRole("button", { name: "Submit" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
