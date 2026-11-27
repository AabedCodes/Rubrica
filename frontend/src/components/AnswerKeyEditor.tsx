import { useState } from "react";
import type { AnswerKey, AnswerKeyEntry, Criterion } from "../types/content";
import { validateAnswerKey, type KeyRow } from "../rubric";
import { ErrorNotice } from "./ErrorNotice";

function initialRows(criteria: readonly Criterion[], key: AnswerKey | null): KeyRow[] {
  return criteria.map((criterion) => {
    const entry = key?.entries.find((e) => e.criterion_id === criterion.id);
    const expected = entry?.expected ?? null;
    return {
      criterion,
      content: entry?.content ?? "",
      expectedType: expected?.type ?? "choice",
      value: expected ? String(expected.value) : "",
      tolerance: expected?.type === "numeric" ? String(expected.tolerance) : "0",
    };
  });
}

/**
 * Answer-key editor (A2). Objective criteria take an expected choice or a
 * number with a tolerance, which code marks without a model (C20). Saved keys
 * are drafts (D6); the key is never shown to students (T-01).
 */
export function AnswerKeyEditor({
  criteria,
  answerKey,
  onSave,
}: {
  criteria: readonly Criterion[];
  answerKey: AnswerKey | null;
  onSave: (entries: AnswerKeyEntry[]) => Promise<AnswerKey>;
}) {
  const [rows, setRows] = useState<KeyRow[]>(() => initialRows(criteria, answerKey));
  const [status, setStatus] = useState(answerKey?.status ?? null);
  const [errors, setErrors] = useState<string[]>([]);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (criteria.length === 0) return <p className="muted">Save a rubric first; the key has one entry per criterion.</p>;

  const update = (i: number, patch: Partial<KeyRow>) => setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <form
      aria-label="Answer key"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const result = validateAnswerKey(rows);
        if (!result.ok) {
          setErrors(result.errors);
          return;
        }
        setErrors([]);
        setSaveError(null);
        setBusy(true);
        onSave(result.value)
          .then((key) => setStatus(key.status))
          .catch((err: unknown) => setSaveError(err))
          .finally(() => setBusy(false));
      }}
    >
      <p className="muted">
        Key status: <strong>{status ?? "not saved"}</strong>.{" "}
        {status === "draft" && "Saved keys are drafts until accepted with re-authentication (route not defined in §10 yet)."}
      </p>
      {rows.map((row, i) => (
        <fieldset key={row.criterion.id} className="criterion-row">
          <legend>
            Criterion {i + 1}: {row.criterion.label}
          </legend>
          {row.criterion.kind === "objective" ? (
            <>
              <label>
                Answer type
                <select
                  value={row.expectedType}
                  onChange={(e) => update(i, { expectedType: e.target.value === "numeric" ? "numeric" : "choice" })}
                >
                  <option value="choice">Exact choice</option>
                  <option value="numeric">Number with tolerance</option>
                </select>
              </label>
              <label>
                Correct answer
                <input value={row.value} onChange={(e) => update(i, { value: e.target.value })} />
              </label>
              {row.expectedType === "numeric" && (
                <label>
                  Tolerance
                  <input type="number" min={0} step="any" value={row.tolerance} onChange={(e) => update(i, { tolerance: e.target.value })} />
                </label>
              )}
              <label>
                Note (optional)
                <input value={row.content} onChange={(e) => update(i, { content: e.target.value })} />
              </label>
            </>
          ) : (
            <label>
              What a full-marks answer contains
              <textarea rows={3} value={row.content} onChange={(e) => update(i, { content: e.target.value })} />
            </label>
          )}
        </fieldset>
      ))}
      {errors.length > 0 && (
        <ul className="error" role="alert">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      {saveError !== null && <ErrorNotice error={saveError} />}
      <button type="submit" disabled={busy}>
        Save answer key
      </button>
    </form>
  );
}
