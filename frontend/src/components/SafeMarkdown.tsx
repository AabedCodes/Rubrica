/**
 * Renders model-written text (feedback, chat replies, rationales) safely (A3, C07).
 *
 * The text may carry instructions injected into the model. Three independent
 * layers keep it from turning into HTML in the browser; this is the browser one:
 *   1. D's server-side sink strips images and raw HTML.
 *   2. E's CSP blocks remote images and inline scripts (01-interfaces.md §10).
 *   3. This component never creates HTML from model text:
 *      - raw HTML is dropped, not parsed (`skipHtml`)              -> T-10
 *      - images become plain text; no <img>, so no request         -> T-09
 *      - links survive only as http(s) to an allowed host          -> T-09, T-10
 *      - everything outside a short element allow-list is reduced to its text
 *
 * Every model-written string in the app goes through this component or is
 * shown as plain text. Never use dangerouslySetInnerHTML (ESLint fails on it).
 */
import ReactMarkdown, { type Components, type UrlTransform } from "react-markdown";

/** Elements Markdown may produce. Anything else is unwrapped to its text. */
export const ALLOWED_ELEMENTS: readonly string[] = [
  "p", "br", "hr", "em", "strong", "code", "pre", "blockquote",
  "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
  "a",
  "img", // kept only so the `img` override below can replace it with text
];

const SAFE_PROTOCOLS = new Set(["http:", "https:"]);

function parseUrl(value: string): URL | null {
  try {
    return new URL(value, window.location.origin);
  } catch {
    return null;
  }
}

/** Blanks every URL that isn't http(s), before any element sees it. */
export const safeUrlTransform: UrlTransform = (url) => {
  const parsed = parseUrl(url);
  return parsed && SAFE_PROTOCOLS.has(parsed.protocol) ? url : "";
};

/** Returns the absolute URL if it is http(s) and its host is allowed, else null. */
export function allowedHref(href: string | undefined, allowedHosts: ReadonlySet<string>): string | null {
  if (!href) return null;
  const parsed = parseUrl(href);
  if (!parsed || !SAFE_PROTOCOLS.has(parsed.protocol)) return null;
  return allowedHosts.has(parsed.host) ? parsed.toString() : null;
}

export interface SafeMarkdownProps {
  text: string;
  /**
   * Hosts whose links stay clickable. Defaults to our own host only.
   * TODO(A6): add course-approved hosts once there is a place to configure them.
   */
  allowedHosts?: readonly string[];
}

export function SafeMarkdown({ text, allowedHosts }: SafeMarkdownProps) {
  const hosts = new Set(allowedHosts ?? [window.location.host]);

  const components: Components = {
    img: ({ alt }) => <span className="removed">[image removed{alt ? `: ${alt}` : ""}]</span>,
    a: ({ href, children }) => {
      const ok = allowedHref(href, hosts);
      return ok ? (
        <a href={ok} rel="noopener noreferrer nofollow" target="_blank">
          {children}
        </a>
      ) : (
        <span className="link-removed" title={href || undefined}>
          {children}
        </span>
      );
    },
  };

  return (
    <div className="safe-markdown">
      <ReactMarkdown
        skipHtml
        allowedElements={ALLOWED_ELEMENTS}
        unwrapDisallowed
        urlTransform={safeUrlTransform}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
