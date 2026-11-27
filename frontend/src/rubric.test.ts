import { describe, expect, it } from "vitest";
import { validateAnswerKey, validateRubric, type KeyRow } from "./rubric";
import type { Criterion } from "./types/content";

describe("validateRubric (A2, C02)", () => {
  it("accepts well-formed rows and trims labels", () => {
    const r = validateRubric([
      { label: "  Q1  ", max_points: "2", kind: "objective" },
      { label: "Q2", max_points: "2.5", kind: "open" },
    ]);
    expect(r).toEqual({
      ok: true,
      value: [
        { label: "Q1", max_points: 2, kind: "objective" },
        { label: "Q2", max_points: 2.5, kind: "open" },
      ],
    });
  });

  it.each([
    ["no rows", [], /at least one criterion/],
    ["empty label", [{ label: " ", max_points: "2", kind: "open" as const }], /write a label/],
    ["zero points", [{ label: "Q", max_points: "0", kind: "open" as const }], /more than 0/],
    ["negative points", [{ label: "Q", max_points: "-1", kind: "open" as const }], /more than 0/],
    ["blank points", [{ label: "Q", max_points: "", kind: "open" as const }], /more than 0/],
    ["not a 0.5 step", [{ label: "Q", max_points: "1.3", kind: "open" as const }], /multiple of 0.5/],
    ["too many points", [{ label: "Q", max_points: "1000", kind: "open" as const }], /at most 100/],
  ])("rejects %s", (_name, rows, message) => {
    const r = validateRubric(rows);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.join(" ")).toMatch(message);
  });
});

describe("validateAnswerKey (A2, C20)", () => {
  const objective: Criterion = { id: "c1", position: 0, label: "Q1", max_points: 2, kind: "objective" };
  const open: Criterion = { id: "c2", position: 1, label: "Q2", max_points: 5, kind: "open" };
  const row = (criterion: Criterion, patch: Partial<KeyRow> = {}): KeyRow => ({
    criterion,
    content: "",
    expectedType: "choice",
    value: "",
    tolerance: "0",
    ...patch,
  });

  it("builds choice, numeric and open entries", () => {
    expect(validateAnswerKey([row(objective, { value: " B " }), row(open, { content: "A boundary" })])).toEqual({
      ok: true,
      value: [
        { criterion_id: "c1", content: "", expected: { type: "choice", value: "B" } },
        { criterion_id: "c2", content: "A boundary", expected: null },
      ],
    });
    expect(validateAnswerKey([row(objective, { expectedType: "numeric", value: "3.5", tolerance: "0.01" })])).toEqual({
      ok: true,
      value: [{ criterion_id: "c1", content: "", expected: { type: "numeric", value: 3.5, tolerance: 0.01 } }],
    });
  });

  it("rejects missing answers and negative tolerance", () => {
    expect(validateAnswerKey([row(objective)]).ok).toBe(false);
    expect(validateAnswerKey([row(open)]).ok).toBe(false);
    expect(validateAnswerKey([row(objective, { expectedType: "numeric", value: "x" })]).ok).toBe(false);
    expect(validateAnswerKey([row(objective, { expectedType: "numeric", value: "1", tolerance: "-1" })]).ok).toBe(false);
  });
});
