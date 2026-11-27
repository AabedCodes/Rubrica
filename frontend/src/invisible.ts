/**
 * Makes invisible characters visible on the review screen (A5, C36, T-04).
 *
 * A submission can hide instructions from a human reader while the grader
 * still reads them: white-on-white text in a PDF (that becomes ordinary text
 * after extraction), zero-width characters, bidirectional overrides that
 * reorder what is displayed, Unicode "tag" characters. The review screen shows
 * the extracted text exactly as the grader read it, with each of these
 * replaced by a visible marker, so the instructor sees what the model saw.
 */

/** Characters that render as nothing, or change how neighbours render. */
// \p{Cf} covers zero-width characters, bidi controls, the BOM, soft hyphen and
// tag characters; \p{Co} private use. The rest are blank-looking spaces,
// fillers and variation selectors. Control characters except tab, LF and CR.
const INVISIBLE =
  // Escapes only, never literal characters, so the source itself stays readable. The lint rules below
  // exist to catch accidental control and invisible characters; here matching them is the purpose.
  // eslint-disable-next-line no-control-regex, no-misleading-character-class -- this regex detects exactly these characters
  /[\p{Cf}\p{Co}\u00A0\u034F\u115F\u1160\u17B4\u17B5\u202F\u205F\u3000\u3164\uFFA0\u180B-\u180F\u2000-\u200A\uFE00-\uFE0F\u{E0100}-\u{E01EF}\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]/gu;

const NAMES: Record<number, string> = {
  0x00a0: "no-break space",
  0x00ad: "soft hyphen",
  0x034f: "combining grapheme joiner",
  0x061c: "Arabic letter mark",
  0x180e: "Mongolian vowel separator",
  0x200b: "zero-width space",
  0x200c: "zero-width non-joiner",
  0x200d: "zero-width joiner",
  0x200e: "left-to-right mark",
  0x200f: "right-to-left mark",
  0x202a: "left-to-right embedding",
  0x202b: "right-to-left embedding",
  0x202c: "pop directional formatting",
  0x202d: "left-to-right override",
  0x202e: "right-to-left override",
  0x2060: "word joiner",
  0x2066: "left-to-right isolate",
  0x2067: "right-to-left isolate",
  0x2068: "first strong isolate",
  0x2069: "pop directional isolate",
  0xfeff: "zero-width no-break space (BOM)",
};

export type Segment = { kind: "text"; text: string } | { kind: "mark"; code: string; name: string };

export function codePointLabel(cp: number): string {
  return `U+${cp.toString(16).toUpperCase().padStart(4, "0")}`;
}

export function describeCodePoint(cp: number): string {
  if (NAMES[cp]) return NAMES[cp];
  if (cp >= 0xe0000 && cp <= 0xe007f) return "tag character";
  if (cp >= 0xfe00 && cp <= 0xfe0f) return "variation selector";
  if (cp < 0x20 || (cp >= 0x7f && cp <= 0x9f)) return "control character";
  if ((cp >= 0xe000 && cp <= 0xf8ff) || cp >= 0xf0000) return "private-use character";
  return "invisible or formatting character";
}

/** Splits text into visible runs and one marker per invisible character. */
export function markInvisible(text: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const match of text.matchAll(INVISIBLE)) {
    const index = match.index;
    if (index > last) out.push({ kind: "text", text: text.slice(last, index) });
    const cp = match[0].codePointAt(0)!;
    out.push({ kind: "mark", code: codePointLabel(cp), name: describeCodePoint(cp) });
    last = index + match[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

export function countInvisible(text: string): number {
  return [...text.matchAll(INVISIBLE)].length;
}
