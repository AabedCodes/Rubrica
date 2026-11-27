import { useState } from "react";
import type { Criterion, CriterionInput } from "../types/content";
import { validateRubric, type RubricRow } from "../rubric";
import { ErrorNotice } from "./ErrorNotice";

const toRow = (c: Criterion): RubricRow => ({ label: c.label, max_points: String(c.max_points), kind: c.kind });
const EMPTY: RubricRow = { label: "", max_points: "", kind: "open" };

/**
 * Rubric editor (A2): rows of {label, max_points, kind}, the structure the
 * output validator needs (§7, C02). Read-only once the assignment is published.
 */
export function RubricEditor({
  criteria,
  readOnly,
  onSave,
}: {
  criteria: readonly Criterion[];
  readOnly: boolean;
  onSave: (rows: CriterionInput[]) => Promise<void>;
}) {
  const [rows, setRows] = useState<RubricRow[]>(() => (criteria.length ? criteria.map(toRow) : [{ ...EMPTY }]));
  const [errors, setErrors] = useState<string[]>([]);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  if (readOnly) {
    return (
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Criterion</th>
            <th>Kind</th>
            <th>Max points</th>
          </tr>
        </thead>
        <tbody>
          {criteria.map((c, i) => (
            <tr key={c.id}>
              <td>{i + 1}</td>
              <td>{c.label}</td>
              <td>{c.kind === "objective" ? "Objective (marked by code)" : "Open (graded against the rubric)"}</td>
              <td>{c.max_points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  const update = (i: number, patch: Partial<RubricRow>) => {
    setSaved(false);
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  };

  return (
    <form
      aria-label="Rubric"
      noValidate // our own messages below; native bubbles would hide them
      onSubmit={(event) => {
        event.preventDefault();
        const result = validateRubric(rows);
        if (!result.ok) {
          setErrors(result.errors);
          return;
        }
        setErrors([]);
        setSaveError(null);
        setBusy(true);
        onSave(result.value)
          .then(() => setSaved(true))
          .catch((err: unknown) => setSaveError(err))
          .finally(() => setBusy(false));
      }}
    >
      {rows.map((row, i) => (
        <fieldset key={i} className="criterion-row">
          <legend>Criterion {i + 1}</legend>
          <label>
            Label
            <input value={row.label} maxLength={500} onChange={(e) => update(i, { label: e.target.value })} />
          </label>
          <label>
            Max points
            <input
              type="number"
              inputMode="decimal"
              min={0.5}
              step={0.5}
              value={row.max_points}
              onChange={(e) => update(i, { max_points: e.target.value })}
            />
          </label>
          <label>
            Kind
            <select value={row.kind} onChange={(e) => update(i, { kind: e.target.value === "objective" ? "objective" : "open" })}>
              <option value="open">Open (graded against the rubric)</option>
              <option value="objective">Objective (marked by code against the key)</option>
            </select>
          </label>
          <button type="button" onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))} disabled={rows.length === 1}>
            Remove criterion {i + 1}
          </button>
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
      {saved && <p role="status">Rubric saved.</p>}
      <div className="actions actions-left">
        <button type="button" onClick={() => setRows((rs) => [...rs, { ...EMPTY }])}>
          Add criterion
        </button>
        <button type="submit" disabled={busy}>
          Save rubric
        </button>
      </div>
    </form>
  );
}
