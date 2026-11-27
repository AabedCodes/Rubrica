import { countInvisible, markInvisible } from "../invisible";

/**
 * Exactly the text the AI grader read (A5, C36). Monospace, whitespace kept,
 * and every invisible character replaced by a visible marker, so hidden
 * instructions (white-on-white text, zero-width or bidi characters) show up.
 * Rendered as React text nodes only: nothing in it is ever treated as HTML.
 */
export function ExtractedTextView({ text }: { text: string }) {
  const hidden = countInvisible(text);
  return (
    <section aria-label="Text the grader read" className="extracted">
      <p className="note">
        This is the text the AI grader read, including any text that was hidden in the original file.
        {hidden > 0 && (
          <strong>
            {" "}
            {hidden} invisible character{hidden === 1 ? " is" : "s are"} marked like ⟦U+200B⟧.
          </strong>
        )}
      </p>
      <pre className="extracted-text">
        {markInvisible(text).map((seg, i) =>
          seg.kind === "text" ? (
            seg.text
          ) : (
            <mark key={i} className="invisible-mark" title={seg.name} aria-label={`${seg.name} (${seg.code})`}>
              ⟦{seg.code}⟧
            </mark>
          ),
        )}
      </pre>
    </section>
  );
}
