/**
 * Client-side checks for the rubric and answer-key editors (A2).
 *
 * These only help the instructor; the server is the authority (C02 and the
 * §3.1 CHECK max_points > 0). The output validator (§7) needs every criterion's
 * maximum, which is why rubrics are structured rows, never only a PDF.
 */
import type { AnswerKeyEntry, Criterion, CriterionInput, CriterionKind, ExpectedAnswer } from "./types/content";

export const MAX_LABEL = 500;
export const MAX_POINTS = 100; // ASSUMED upper bound; §3.1 only requires > 0

export interface RubricRow {
  label: string;
  max_points: string; // as typed in the input
  kind: CriterionKind;
}

export type Validation<T> = { ok: true; value: T } | { ok: false; errors: string[] };

export function validateRubric(rows: readonly RubricRow[]): Validation<CriterionInput[]> {
  const errors: string[] = [];
  if (rows.length === 0) errors.push("Add at least one criterion.");
  const value: CriterionInput[] = [];
  rows.forEach((row, i) => {
    const n = i + 1;
    const label = row.label.trim();
    const points = Number(row.max_points);
    if (!label) errors.push(`Criterion ${n}: write a label.`);
    else if (label.length > MAX_LABEL) errors.push(`Criterion ${n}: the label is longer than ${MAX_LABEL} characters.`);
    if (row.max_points.trim() === "" || !Number.isFinite(points) || points <= 0) {
      errors.push(`Criterion ${n}: maximum points must be more than 0.`);
    } else if (points > MAX_POINTS) {
      errors.push(`Criterion ${n}: maximum points can be at most ${MAX_POINTS}.`);
    } else if ((points * 2) % 1 !== 0) {
      // §7: scores move in steps of 0.5, so maximums do too.
      errors.push(`Criterion ${n}: maximum points must be a multiple of 0.5.`);
    }
    value.push({ label, max_points: points, kind: row.kind });
  });
  return errors.length ? { ok: false, errors } : { ok: true, value };
}

export interface KeyRow {
  criterion: Criterion;
  content: string;
  expectedType: ExpectedAnswer["type"];
  value: string;
  tolerance: string;
}

export function validateAnswerKey(rows: readonly KeyRow[]): Validation<AnswerKeyEntry[]> {
  const errors: string[] = [];
  const value: AnswerKeyEntry[] = [];
  rows.forEach((row, i) => {
    const n = i + 1;
    if (row.criterion.kind === "open") {
      if (!row.content.trim()) errors.push(`Criterion ${n}: describe what a full-marks answer contains.`);
      value.push({ criterion_id: row.criterion.id, content: row.content, expected: null });
      return;
    }
    let expected: ExpectedAnswer | null = null;
    if (row.expectedType === "choice") {
      if (!row.value.trim()) errors.push(`Criterion ${n}: enter the correct choice.`);
      else expected = { type: "choice", value: row.value.trim() };
    } else {
      const v = Number(row.value);
      const t = Number(row.tolerance || "0");
      if (row.value.trim() === "" || !Number.isFinite(v)) errors.push(`Criterion ${n}: enter the correct number.`);
      else if (!Number.isFinite(t) || t < 0) errors.push(`Criterion ${n}: tolerance must be 0 or more.`);
      else expected = { type: "numeric", value: v, tolerance: t };
    }
    value.push({ criterion_id: row.criterion.id, content: row.content, expected });
  });
  return errors.length ? { ok: false, errors } : { ok: true, value };
}

/** Formats a timestamp for display in the viewer's locale. */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** Value for <input type="datetime-local"> from an ISO string, in local time. */
export function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
