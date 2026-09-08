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
import { userContentTarget, USER_CONTENT_PREFIX } from "./md-sanitize";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

// isolate the global anchor-click handler
const HANDLER = (RENDER.match(/closest\?\.\(LINK_SEL\)[\s\S]*?\}, true\);/) || [""])[0];

test("the chat has a global link click handler", () => {
  assert.ok(HANDLER, "found the anchor-click handler");
  assert.match(HANDLER, /e\.preventDefault\(\)/);
});

// The handler owns every element a sanitized message can carry a navigating href on, not only <a href>: an SVG
// <a xlink:href> survives the sanitizer's svg profile and is no `a[href]` (`[href]` matches only the null-namespace
// attribute, and XLink's is namespaced), and an image map's <area href> did too until the sanitizer forbade map, area
// and usemap (md-sanitize.ts); the selector keeps the area as a second guard. A click on either used to run the
// default action and navigate the chat document itself (the 2026-09-07 review of the markdown viewer's Slice 1).
// md-sanitize-chat-links-browser.test.ts clicks both over the real bundle; this pins the selector and the href read
// at the source, where the pin runs without a browser.
test("the selector names the anchor in any namespace and the image map's area, and the href read falls back to xlink:href", () => {
  // both come from md-links.ts, the module the viewer's mdBlock reads them from too (md-sanitize-viewer-links.test.ts),
  // so the chat and the viewer cannot drift apart on which elements are links; render.ts keeps no copy of its own
  assert.match(RENDER, /import \{[^}]*\bLINK_SEL\b[^}]*\blinkHref\b[^}]*\} from "\.\/md-links";/, "the delegate imports the shared selector and href read");
  assert.doesNotMatch(RENDER, /const LINK_SEL =|const XLINK_NS =|function linkHref\(/, "no local copy in render.ts");
  assert.equal(LINK_SEL, "a[*|href], area[href]", "a[*|href] covers href and xlink:href; area[href] the image map, which the sanitizer now drops (a second guard)");
  assert.equal(XLINK_NS, "http://www.w3.org/1999/xlink");
  const stub = (attrs: Record<string, string>, xlink?: string) => ({
    getAttribute: (n: string) => (n in attrs ? attrs[n] : null),
    getAttributeNS: (ns: string | null, n: string) => (ns === XLINK_NS && n === "href" && xlink !== undefined ? xlink : null),
  });
  assert.equal(linkHref(stub({ href: "https://example.invalid/a" }, "https://example.invalid/x")), "https://example.invalid/a", "the plain attribute first");
  assert.equal(linkHref(stub({}, "https://example.invalid/x")), "https://example.invalid/x", "then SVG's XLink spelling");
  assert.equal(linkHref(stub({})), "", "neither: the empty string, which the delegate makes inert (nothing to open, nothing for the browser to follow)");
  assert.match(HANDLER, /let href = linkHref\(a\);/, "read once, as written; a `let`, since a scheme-less href is replaced further down by the address the browser would follow");
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

// An in-page anchor in a message: the sanitizer prefixes an author's id and name user-content- (md-sanitize.ts,
// GitHub's rule; once, a value already carrying it is left as written) and leaves the href as written, and the browser's
// default lookup reads the bare name, so a footnote's back link or a `[section](#install)` over the reply's own
// `<a name>`, which scrolled the transcript on the base, did nothing once the prefix landed (the 2026-09-07 review of
// Slice 1). The handler now resolves a `#` href the way GitHub's page script does, through the one lookup the viewer's
// fragmentTarget reads too (md-sanitize.ts userContentTarget): the message's own body first, then the document; found,
// scrollIntoView and preventDefault; not found, the click is the browser's, as before. The click it stands aside for is
// the platform's own tab gesture (md-links.ts browserTabClick: Shift; Cmd on macOS, Ctrl elsewhere), since a Super-click
// off macOS is a plain click to the browser and standing aside for it left the default lookup to find nothing (review
// round 2). The real clicks run in md-sanitize-chat-links-browser.test.ts and md-sanitize-chat-modified-click-browser.test.ts.
test("a `#` href in a message is resolved under the user-content- prefix, in the message first and then the document, before the scheme test", () => {
  assert.match(RENDER, /import \{[^}]*\buserContentTarget\b[^}]*\} from "\.\/md-sanitize";/, "the lookup is the sanitizer's own, shared with the viewer's fragmentTarget");
  const at = HANDLER.indexOf('if (href.startsWith("#")) {');
  assert.ok(at > 0, "the fragment branch exists");
  assert.ok(HANDLER.indexOf("let href = linkHref(a);") > -1 && at > HANDLER.indexOf("let href = linkHref(a);") && at < HANDLER.indexOf("/^[a-z][a-z0-9+.-]*:/i.test(href)"), "after the href is read, before the scheme test that used to leave every fragment to the browser");
  const branch = HANDLER.slice(at, HANDLER.indexOf("/^[a-z][a-z0-9+.-]*:/i.test(href)"));
  assert.match(RENDER, /import \{[^}]*\bbrowserTabClick\b[^}]*\} from "\.\/md-links";/, "the browser's-tab test is md-links.ts's browserTabClick (Shift; Cmd on macOS, Ctrl elsewhere), executed in md-links.test.ts");
  assert.match(RENDER, /^const IS_MAC = typeof navigator !== "undefined" && \/Mac\|iP\(\?:hone\|ad\|od\)\/\.test\(navigator\.platform \|\| ""\);$/m, "the platform read is the one the editor's save chord and the track decorations use");
  assert.match(branch, /if \(browserTabClick\(e, IS_MAC\)\) return;/, "a click the browser answers with a tab or window keeps the browser's; Super-click on Linux and Windows is a plain click to the browser and is resolved (the round-2 review; md-sanitize-chat-modified-click-browser.test.ts clicks each key)");
  assert.doesNotMatch(branch, /e\.ctrlKey \|\| e\.metaKey \|\| e\.shiftKey/, "no any-modifier read in the fragment branch: Meta off macOS is not a tab gesture");
  assert.match(branch, /const msg = a\.closest\("\.md"\);\n\s*if \(!msg\) return;/, "a link outside a message body (the file viewer's own section links) is not this handler's");
  assert.match(branch, /let frag = href\.slice\(1\);\n\s*try \{ frag = decodeURIComponent\(frag\); \} catch \{[^}]*\}/, "the fragment is decoded, a malformed escape kept as written (the viewer's scrollToFragment rule)");
  assert.match(branch, /const target = frag \? userContentTarget\(msg, frag\) \|\| userContentTarget\(document, frag\) : undefined;/, "the message's own body first, then the whole document");
  assert.match(branch, /if \(!target\) return;\n\s*e\.preventDefault\(\);\n\s*target\.scrollIntoView\(\{ block: "start" \}\);\n\s*return;/, "found: scrolled to and the default cancelled; not found: left to the browser");
  assert.doesNotMatch(branch, /location\.hash|stopPropagation/, "the hash is not touched (the target is not a page location) and the event still reaches the body's delegates");
  // the scheme test that follows no longer hands a scheme-less href to the browser's default action: DOMPurify keeps `//host`,
  // `/\host`, a C0 control before `https:` and a tab or newline inside the scheme, each of which navigated the chat document
  // cross-origin in the same frame. The href is resolved against the document as that action would resolve it (the browser's
  // own URL parser) and opened by the delegate when it is a web URL; an empty href opens nothing; a non-web result (VS Code's
  // webview scheme) or a parse failure stays the browser's. md-url-view.test.ts pins the whole block;
  // md-sanitize-chat-schemeless-browser.test.ts clicks each shape over the real bundle.
  assert.doesNotMatch(HANDLER, /\/i\.test\(href\)\) return;/, "no scheme-less href is left to the default action any more");
  const schemeless = HANDLER.slice(HANDLER.indexOf("/^[a-z][a-z0-9+.-]*:/i.test(href)) {"), HANDLER.indexOf("e.preventDefault();\n  e.stopPropagation();"));
  assert.match(schemeless, /if \(!href\) \{ e\.preventDefault\(\); return; \}/, "an empty href is made inert");
  assert.match(schemeless, /new URL\(href, document\.baseURI\)/, "resolved against the document, by the browser's own parser");
  assert.match(schemeless, /if \(!url \|\| \(url\.protocol !== "http:" && url\.protocol !== "https:"\)\) return;\n\s*href = url\.href;/, "a web URL is opened at the resolved address; anything else stays the browser's");
});

test("userContentTarget: an id under the prefix or bare, then an <a name> under either, in document order; nothing otherwise", () => {
  // a stand-in with what the lookup reads: querySelectorAll over "[id]" and "a[name]", getAttribute
  type Fake = { tag: string; attrs: Record<string, string>; getAttribute(n: string): string | null };
  const fake = (tag: string, attrs: Record<string, string>): Fake => ({ tag, attrs, getAttribute: (n) => (n in attrs ? attrs[n] : null) });
  const root = (els: Fake[]) => ({
    querySelectorAll: (sel: string) => (sel === "[id]" ? els.filter((e) => "id" in e.attrs) : sel === "a[name]" ? els.filter((e) => e.tag === "a" && "name" in e.attrs) : []),
  }) as unknown as ParentNode;
  assert.equal(USER_CONTENT_PREFIX, "user-content-", "GitHub's prefix, the one SANITIZE_NAMED_PROPS writes");
  const fn1 = fake("sup", { id: "user-content-fn1" }), install = fake("a", { name: "user-content-install" }), bare = fake("p", { id: "plain" }), typed = fake("p", { id: "user-content-x" });
  const dupName = fake("a", { name: "user-content-dup" }), dupId = fake("div", { id: "user-content-dup" });
  const r = root([fn1, install, bare, dupName, dupId, typed]);
  assert.equal(userContentTarget(r, "fn1"), fn1, "an author's id, under the prefix the sanitizer gave it");
  assert.equal(userContentTarget(r, "install"), install, "an author's <a name>, under the prefix");
  assert.equal(userContentTarget(r, "plain"), bare, "a bare id (the viewer's minted md- ids, the page's own) still answers");
  // an author who typed the prefix (`id="user-content-x"`): DOMPurify's SANITIZE_NAMED_PROPS adds it once and leaves a value
  // that already starts with it as written, so the element reaches the DOM as user-content-x, the id a bare `x` would have
  // got. A `#user-content-x` link lands on it through the bare arm, `#x` through the prefixed arm (a typed prefix reaches
  // what the bare id reaches, no more), and a doubly prefixed ask finds nothing; file-view-links.test.ts pins the viewer's
  // fragmentTarget the same way.
  assert.equal(userContentTarget(r, "user-content-x"), typed, "an author who typed the prefix: the sanitizer left it as written, and the bare arm finds it");
  assert.equal(userContentTarget(r, "x"), typed, "the same element answers the bare ask, through the prefixed arm");
  assert.equal(userContentTarget(r, "user-content-user-content-x"), undefined, "the prefix is added once: a doubly prefixed ask finds nothing");
  assert.equal(userContentTarget(r, "dup"), dupId, "an id wins over a name, whatever the document order (the browser's fragment rule)");
  assert.equal(userContentTarget(r, "nowhere"), undefined);
  assert.equal(userContentTarget(r, ""), undefined, "an empty fragment names nothing (the prefix alone matches no element here)");
});
