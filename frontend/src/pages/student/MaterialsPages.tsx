import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { ExtractedTextView } from "../../components/ExtractedTextView";
import { studentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import { MAX_PDF_BYTES } from "../../types/content";

const PARSE: Record<string, string> = { queued: "Waiting for the parser", parsed: "Text extracted", failed: "Parsing failed" };

/** Instructor materials (A6, C04): upload, see parse status, read the extracted text, publish. */
export function MaterialsPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => studentRoutes(api).materials(courseId), [api, courseId]);
  const { state, reload } = useLoad(loader);
  const [title, setTitle] = useState("");
  const [thirdParty, setThirdParty] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <section>
      <h1>Course materials</h1>
      <p className="muted">
        Published material is searchable by the course's AI agents. Read the extracted text before publishing: hidden text is
        marked (C04).
      </p>
      <form
        aria-label="Upload material"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          if (!file || fileError || !title.trim()) return;
          const form = new FormData();
          form.set("title", title.trim());
          form.set("source_kind", thirdParty ? "third_party" : "instructor");
          form.set("file", file);
          setBusy(true);
          setError(null);
          studentRoutes(api)
            .uploadMaterial(courseId, form)
            .then(() => {
              setTitle("");
              setFile(null);
              reload();
            })
            .catch((err: unknown) => setError(err))
            .finally(() => setBusy(false));
        }}
      >
        <label>
          Title
          <input value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="inline">
          <input type="checkbox" checked={thirdParty} onChange={(e) => setThirdParty(e.target.checked)} /> Third-party source (not
          written by the course team)
        </label>
        <label>
          PDF
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              setFile(f);
              if (f && f.type !== "application/pdf") setFileError("Only PDF files can be uploaded.");
              else if (f && f.size > MAX_PDF_BYTES) setFileError("The PDF is larger than 10 MB.");
              else setFileError(null);
            }}
          />
        </label>
        {fileError && (
          <p className="error" role="alert">
            {fileError}
          </p>
        )}
        {error !== null && <ErrorNotice error={error} />}
        <button type="submit" disabled={busy || !file || !!fileError || !title.trim()}>
          Upload
        </button>
      </form>

      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Source</th>
              <th>Parse status</th>
              <th>Status</th>
              <th>Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((m) => (
              <tr key={m.id}>
                <td>
                  <Link to={`/courses/${encodeURIComponent(courseId)}/materials/${encodeURIComponent(m.id)}`}>{m.title}</Link>
                </td>
                <td>{m.source_kind === "third_party" ? "Third-party source" : "Instructor material"}</td>
                <td>{PARSE[m.parse_status] ?? m.parse_status}</td>
                <td>{m.status === "published" ? "Published" : "Not published"}</td>
                <td>{formatDate(m.uploaded_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** One material: the exact text ingestion will index, with hidden characters marked, and Publish (re-auth). */
export function MaterialPage() {
  const { courseId = "", materialId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const r = studentRoutes(api);
    const material = (await r.materials(courseId)).find((m) => m.id === materialId);
    if (!material) throw new Error("not found");
    const text = material.parse_status === "parsed" ? (await r.materialText(materialId)).text : null;
    return { material, text };
  }, [api, courseId, materialId]);
  const { state, reload } = useLoad(loader);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { material: m, text } = state.data;

  return (
    <section>
      <p>
        <Link to={`/courses/${encodeURIComponent(courseId)}/materials`}>← Back to materials</Link>
      </p>
      <div className="page-head">
        <h1>{m.title}</h1>
        <span className="badge">{m.source_kind === "third_party" ? "Third-party source" : "Instructor material"}</span>
        <span className="badge">{m.status === "published" ? "Published" : "Not published"}</span>
      </div>
      {text === null ? <p>{PARSE[m.parse_status]}</p> : <ExtractedTextView text={text} />}
      {error !== null && <ErrorNotice error={error} />}
      {m.status === "pending" && text !== null && (
        <>
          <p className="effect">
            Publishing makes this text searchable by the course's AI agents: chat answers and grading context
            {m.source_kind === "third_party" ? ", labelled as a third-party source" : ""}. Anything hidden in it, including the
            marked characters above, becomes part of what they read. Needs your authenticator code.
          </p>
          <button
            type="button"
            className="primary"
            disabled={busy}
            onClick={() => {
              setBusy(true);
              setError(null);
              studentRoutes(api)
                .publishMaterial(m.id)
                .then(() => reload())
                .catch((err: unknown) => setError(err))
                .finally(() => setBusy(false));
            }}
          >
            Publish material
          </button>
        </>
      )}
    </section>
  );
}
