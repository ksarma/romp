// Links in the chat must follow on click (the user 2026-06-25). On the web dashboard the old handler only
// ever postMessage'd the host an openLink — but the kernel has no openLink handler, so a link click did
// nothing on the web dashboard. Now the click handler splits by host: a web origin (http/https) opens the
// link in the viewer's own browser via window.open; a VS Code webview (vscode-webview: origin) still routes
// to the host extension's openExternal. The chat renderer has no jsdom harness, so pin it at the source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { LINK_SEL, XLINK_NS, linkHref } from "./md-links";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

// isolate the global anchor-click handler
const HANDLER = (RENDER.match(/closest\?\.\(LINK_SEL\)[\s\S]*?\}, true\);/) || [""])[0];

test("the chat has a global link click handler", () => {
  assert.ok(HANDLER, "found the anchor-click handler");
  assert.match(HANDLER, /e\.preventDefault\(\)/);
});

// The handler owns every element a sanitized message can carry a navigating href on, not only <a href>: an image
// map's <area href> and an SVG <a xlink:href> both survive the sanitizer's html + svg profiles, and neither is an
// `a[href]` (an area is not an anchor; `[href]` matches only the null-namespace attribute, and XLink's is namespaced),
// so a click on either used to run the default action and navigate the chat document itself (the 2026-09-07 review
// of the markdown viewer's Slice 1). md-sanitize-chat-links-browser.test.ts clicks both over the real bundle; this
// pins the selector and the href read at the source, where the pin runs without a browser.
test("the selector names the anchor in any namespace and the image map's area, and the href read falls back to xlink:href", () => {
  // both come from md-links.ts, the module the viewer's mdBlock reads them from too (md-sanitize-viewer-links.test.ts),
  // so the chat and the viewer cannot drift apart on which elements are links; render.ts keeps no copy of its own
  assert.match(RENDER, /import \{[^}]*\bLINK_SEL\b[^}]*\blinkHref\b[^}]*\} from "\.\/md-links";/, "the delegate imports the shared selector and href read");
  assert.doesNotMatch(RENDER, /const LINK_SEL =|const XLINK_NS =|function linkHref\(/, "no local copy in render.ts");
  assert.equal(LINK_SEL, "a[*|href], area[href]", "a[*|href] covers href and xlink:href; area[href] the image map");
  assert.equal(XLINK_NS, "http://www.w3.org/1999/xlink");
  const stub = (attrs: Record<string, string>, xlink?: string) => ({
    getAttribute: (n: string) => (n in attrs ? attrs[n] : null),
    getAttributeNS: (ns: string | null, n: string) => (ns === XLINK_NS && n === "href" && xlink !== undefined ? xlink : null),
  });
  assert.equal(linkHref(stub({ href: "https://example.invalid/a" }, "https://example.invalid/x")), "https://example.invalid/a", "the plain attribute first");
  assert.equal(linkHref(stub({}, "https://example.invalid/x")), "https://example.invalid/x", "then SVG's XLink spelling");
  assert.equal(linkHref(stub({})), "", "neither: the empty string, which the scheme test rejects");
  assert.match(HANDLER, /const href = linkHref\(a\);/);
  assert.doesNotMatch(HANDLER, /a\.getAttribute\("href"\)/, "the handler never reads the null-namespace attribute alone");
});

test("web dashboard (http/https origin) opens the link in the viewer's browser", () => {
  assert.match(HANDLER, /location\.protocol === "http:" \|\| location\.protocol === "https:"/);
  assert.match(HANDLER, /window\.open\(href, "_blank", "noopener,noreferrer"\)/);
});

test("VS Code webview still routes the link to the host (openExternal)", () => {
  assert.match(HANDLER, /vscodeApi\.postMessage\(\{ type: "openLink", href \}\)/);
});

// A control the file-comments panel paints INTO a linked figure in the viewer (a region's rectangle, the overlay a
// press is handed on from, a framed picture) is the panel's activation: its delegate opens the card and cancels the
// anchor. This handler runs first, at the capture phase, and used to open the tab instead (twice with the panel open)
// while no card opened (the 2026-09-06 review of Slice 3). It now asks the panel's registry (panelMark, exact: the
// elements the panel made, never a class or data-act the file's own markup may wear) before it touches the event.
// file-comments-regions-review-3.test.ts drives the panel under a copy of this handler; this pins the handler's side.
test("a click on a file-comments mark inside a linked figure is left to the panel: panelMark is asked before preventDefault", () => {
  assert.match(RENDER, /^import \{ panelMark \} from "\.\/file-comments";$/m, "the registry is the panel's own export");
  assert.match(HANDLER, /if \(panelMark\(e\.target as Element \| null\)\) return;/);
  const ask = HANDLER.indexOf("panelMark(");
  const cancel = HANDLER.indexOf("e.preventDefault()");
  const scheme = HANDLER.indexOf("/^[a-z][a-z0-9+.-]*:/i.test(href)");
  assert.ok(ask > -1 && cancel > -1 && ask < cancel, "the panel's marks are excused before the event is cancelled");
  assert.ok(scheme > -1 && ask < scheme, "…and before the href is even read: whatever the link, the mark is the panel's");
});

test("the web path is checked before the vscode path (web origin wins)", () => {
  const web = HANDLER.indexOf("window.open(href");
  const code = HANDLER.indexOf('type: "openLink"');
  assert.ok(web > -1 && code > -1 && web < code, "window.open branch precedes the openLink branch");
});
