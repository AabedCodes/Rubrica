/**
 * The mock must enforce the same access rules the real routes will (C29), so
 * screens built against it don't come to rely on data they won't get.
 */
import { describe, expect, it } from "vitest";
import { authRoutes, createApiClient } from "../api";
import { contentRoutes, gradingRoutes } from "../endpoints";
import { createMockTransport, MOCK_PASSWORD, MOCK_TOTP_CODE, SEED_IDS } from "./mockApi";

async function as(email: string, transport = createMockTransport()) {
  const api = createApiClient({ transport });
  const auth = authRoutes(api);
  const r = await auth.login({ email, password: MOCK_PASSWORD });
  if (r.status === "totp_required") await auth.totp({ code: MOCK_TOTP_CODE });
  api.resetSession();
  return { api, content: contentRoutes(api), grading: gradingRoutes(api), transport };
}

describe("mock content and grading routes: access rules", () => {
  it("never gives a student the answer key (T-01)", async () => {
    const { content } = await as("student1@example.test");
    await expect(content.getAnswerKey(SEED_IDS.publishedAssignment)).rejects.toMatchObject({ status: 403 });
    const a = await content.getAssignment(SEED_IDS.publishedAssignment);
    // The seeded key text and the expected value must never appear in what a student gets.
    const json = JSON.stringify(a);
    expect(json).not.toContain("Names a boundary between untrusted student text");
    expect(json).not.toMatch(/"expected"|answerKey|answer_key/);
  });

  it("hides draft assignments from students, as not found", async () => {
    const { content } = await as("student1@example.test");
    const list = await content.listAssignments(SEED_IDS.courseWithAssignments);
    expect(list.map((a) => a.status)).toEqual(["published"]);
    await expect(content.getAssignment(SEED_IDS.draftAssignment)).rejects.toMatchObject({ status: 404 });
  });

  it("blocks students from instructor actions (C29)", async () => {
    const { content, grading } = await as("student1@example.test");
    await expect(
      content.createAssignment(SEED_IDS.courseWithAssignments, { title: "x", instructions: "", due_at: new Date().toISOString() }),
    ).rejects.toMatchObject({ status: 403 });
    await expect(grading.startRun(SEED_IDS.publishedAssignment)).rejects.toMatchObject({ status: 403 });
    await expect(grading.proposedGrades(SEED_IDS.publishedAssignment)).rejects.toMatchObject({ status: 403 });
    await expect(grading.approve({ proposed_grade_ids: ["x"] })).rejects.toMatchObject({ status: 403 });
  });

  it("rejects rubric rows the database would reject (max_points > 0)", async () => {
    const { content } = await as("instructor1@example.test");
    await expect(content.putRubric(SEED_IDS.draftAssignment, { criteria: [{ label: "Q", max_points: 0, kind: "open" }] })).rejects.toMatchObject({
      status: 400,
    });
  });

  it("requires re-auth to approve when the sign-in code is stale (C28)", async () => {
    const { grading } = await as("instructor1@example.test", createMockTransport({ staleReauth: true }));
    await grading.startRun(SEED_IDS.publishedAssignment);
    const [row] = await grading.proposedGrades(SEED_IDS.publishedAssignment);
    await expect(grading.approve({ proposed_grade_ids: [row!.id] })).rejects.toMatchObject({ status: 401, code: "reauth_required" });
  });

  it("marks objective answers in code and computes totals from the scores (C20, §7)", async () => {
    const { grading } = await as("instructor1@example.test");
    await grading.startRun(SEED_IDS.publishedAssignment);
    const rows = await grading.proposedGrades(SEED_IDS.publishedAssignment);
    expect(rows).toHaveLength(3);
    const four = rows.find((r) => r.student.display_name === "Student Four")!;
    // The CANARY-T04 submission plays a fooled grader: full marks, and flagged for the instructor (C36).
    expect(four.total).toBe(four.max_total);
    expect(four.flags).toContain("full_marks");
    expect(rows.some((r) => r.flags.includes("disagreement"))).toBe(true);
    // A second run doesn't grade the same submissions twice.
    await expect(grading.startRun(SEED_IDS.publishedAssignment)).resolves.toMatchObject({ submissions: 0 });
  });
});
