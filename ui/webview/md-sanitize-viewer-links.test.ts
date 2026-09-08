// The viewer's links after the sanitize: every element a note can follow a link from, not only <a href>
// (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does; the 2026-09-07 review). DOMPurify's svg profile
// keeps an inline SVG <a> spelled `href` or `xlink:href`, and its html profile kept an image map (<map>, <area href>,
// usemap) until the slice forbade all three (md-sanitize.ts: a prefixed map name can never bind, and GitHub drops
// them). mdBlock's link passes (file-view.ts) ran over `a[href]`: an <area> is not an anchor, `[href]` matches only
// the null-namespace attribute, and `a.target = "_blank"` on an SVGAElement is a silent no-op (its `target` is a
// read-only SVGAnimatedString, and the bundle is not strict there), so a click on any of the three took the Files
// document to the URL in the same frame, the defect class the slice closes for <form>. Now one shared selector
// (LINK_SEL, md-links.ts) and one href reader (linkHref) serve mdBlock and the chat's click delegate, and the viewer
// stamps target and rel with setAttribute. Executed here: linkHref. Pinned at the source (file-view.ts has no jsdom
// harness, as every viewer test notes): the selector in both of mdBlock's passes, the attribute writes, the xlink
// normalisation before the doc gate (the XLink spelling copied to a plain href and then REMOVED: a stamp that takes
// `href` off a path link or a dead link must leave the browser nothing to follow, and it follows xlink:href when href
// is absent; round 3 of the review), and the chat delegate keying on the same selector. The clicks themselves run in
// headless Chromium: md-sanitize-viewer-links-browser.test.ts, a file document (whose stamps are linkMarkdownAnchors',
// file-view-links.ts), a URL document (mdBlock's own stamps, with no delegate in front: the property write there
// navigates the page in the same frame, and that leg says so) and the same file document in the chat page's viewer,
// under the chat's delegate.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { LINK_SEL, XLINK_NS, linkHref } from "./md-links";
import { MD_FORBID_TAGS, MD_FORBID_ATTR } from "./md-sanitize";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const VIEW = read("file-view.ts");
const RENDER = read("render.ts");
// mdBlock, from its declaration to the next exported function
const MD_FN = VIEW.split("function mdBlock(")[1].split("export function rewriteFigureSrcs")[0];

/** A stub element carrying only the attributes linkHref reads: `href` in no namespace, `xlink:href` in XLink. */
function stub(attrs: { href?: string; xlink?: string }) {
  return {
    getAttribute: (name: string) => (name === "href" && attrs.href !== undefined ? attrs.href : null),
    getAttributeNS: (ns: string | null, name: string) => (ns === XLINK_NS && name === "href" && attrs.xlink !== undefined ? attrs.xlink : null),
  };
}

test("linkHref: href, else xlink:href, else empty; href wins when both are present, as it does in the browser", () => {
  assert.equal(linkHref(stub({ href: "https://example.invalid/a" })), "https://example.invalid/a");
  assert.equal(linkHref(stub({ xlink: "https://example.invalid/x" })), "https://example.invalid/x");
  assert.equal(linkHref(stub({ href: "sibling.md", xlink: "https://example.invalid/x" })), "sibling.md");
  assert.equal(linkHref(stub({ href: "" })), "", "an empty href is an empty link, not a fall-through to xlink");
  assert.equal(linkHref(stub({})), "");
  assert.equal(XLINK_NS, "http://www.w3.org/1999/xlink");
});

test("LINK_SEL names every element a sanitized note can follow a link from: an anchor in any href namespace, and an area as a second guard behind the sanitizer's forbid", () => {
  assert.equal(LINK_SEL, "a[*|href], area[href]");
  // `*|href` covers a[href] too (any namespace includes none), so a plain `a[href]` alongside it would be redundant
  assert.doesNotMatch(LINK_SEL, /(^|, )a\[href\]/);
  // the image map itself is dropped by the sanitizer (GitHub's rule; the prefixed map name could never bind to an
  // author's usemap), so no <area> reaches either delegate: in a file document the module that dresses the file's links
  // walks `a` alone, and a surviving <area href> navigated the pane again after the #347 fold (the fold's own leg caught it)
  for (const tag of ["map", "area"]) assert.ok(MD_FORBID_TAGS.includes(tag), tag + " is forbidden");
  assert.ok(MD_FORBID_ATTR.includes("usemap"), "usemap is forbidden");
});

test("mdBlock's two link passes select LINK_SEL and read linkHref; no `a[href]` pass is left in the viewer", () => {
  assert.match(VIEW, /import \{[^}]*\bLINK_SEL\b[^}]*\} from "\.\/md-links";/, "the viewer imports the shared selector");
  assert.match(VIEW, /import \{[^}]*\blinkHref\b[^}]*\} from "\.\/md-links";/, "…and the shared href reader");
  assert.equal((MD_FN.match(/querySelectorAll\(LINK_SEL\)/g) || []).length, 2, "the doc-relative pass and the final target pass");
  assert.doesNotMatch(MD_FN, /querySelectorAll\("a\[href\]"\)/, "the selector that missed <area> and xlink:href is gone");
  assert.doesNotMatch(MD_FN, /as HTMLAnchorElement/, "a link is typed as the element it may be: HTML or SVG");
  assert.match(MD_FN, /const href = linkHref\(a\);/, "the doc-relative pass reads the href through linkHref");
  assert.match(MD_FN, /if \(linkHref\(a\)\.startsWith\("#"\)\) \{ a\.dataset\.act = "fv-anchor"; return; \}/, "…and so does the fragment test");
});

test("target and rel are written with setAttribute: the `target` property is read-only on an SVGAElement and the write was a silent no-op", () => {
  assert.match(MD_FN, /a\.setAttribute\("target", "_blank"\);\s*\n\s*a\.setAttribute\("rel", "noopener"\);/);
  assert.doesNotMatch(MD_FN, /\ba\.target\s*=/, "no property write on target");
  assert.doesNotMatch(MD_FN, /\ba\.rel\s*=/, "no property write on rel");
  assert.doesNotMatch(MD_FN, /\ba\.title\s*=/, "no property write on title either (an SVG <a> has none)");
  // the file kind's links are dressed by file-view-links.ts linkMarkdownAnchors (fork PR #347), which writes every attribute as one too
  assert.doesNotMatch(read("file-view-links.ts").split("export function linkMarkdownAnchors(")[1], /\ba\.(title|target|rel|className)\s*=/, "no property write in the module's pass either (an SVG <a> has none of them)");
  assert.match(MD_FN, /SVGAnimatedString/, "the reason is written down beside the write");
});

test("an SVG anchor's xlink:href is moved to a plain href before either pass (copied when the anchor has none, then removed), so the delegates and the browser read one attribute", () => {
  const norm = MD_FN.indexOf('querySelectorAll("a[*|href]").forEach((a) => {');
  const docGate = MD_FN.indexOf('if (doc && doc.kind === "url") {');   // mdBlock's first doc gate (fork PR #347 split the two kinds)
  const sanitize = MD_FN.indexOf("sanitizeMd(");
  assert.ok(norm > -1, "the normalisation pass exists");
  assert.ok(sanitize < norm && norm < docGate, "after the sanitize (the attribute must survive DOMPurify first), before the doc gate (both passes see it)");
  assert.match(VIEW, /import \{[^}]*\bXLINK_NS\b[^}]*\} from "\.\/md-links";/, "the namespace is the shared constant, not a second spelling");
  // the copy only when no href is present (an author's href beside the xlink wins, as in the browser), then the removal on every
  // anchor that carried the XLink spelling: linkMarkdownAnchors takes `href` off a path link and a dead link, and the browser
  // follows xlink:href when href is absent, so an xlink:href left in place navigated the Files document from a dead SVG link
  // and let the chat's delegate (a[*|href]) open a path link's relative target as a URL document (round 3 of the review)
  assert.match(MD_FN, /querySelectorAll\("a\[\*\|href\]"\)\.forEach\(\(a\) => \{\n\s*const xl = a\.getAttributeNS\(XLINK_NS, "href"\);\n\s*if \(xl === null\) return;[^\n]*\n\s*if \(!a\.hasAttribute\("href"\)\) a\.setAttribute\("href", xl\);\n\s*a\.removeAttributeNS\(XLINK_NS, "href"\);\n\s*\}\);/,
    "copy when absent, then remove the XLink spelling, on one pass");
  assert.doesNotMatch(MD_FN, /a\[\*\|href\]:not\(\[href\]\)/, "the copy-only pass is gone: it left xlink:href for the browser to follow once href came off");
  // a stand-in element runs the pass's logic as written: an xlink-only anchor gains href and loses xlink; one with both keeps its
  // own href and loses xlink; an href-only anchor is untouched
  const pass = MD_FN.slice(norm + 'querySelectorAll("a[*|href]").forEach('.length);
  const fnSrc = pass.slice(0, pass.indexOf("\n  });") + "\n  }".length);
  const fn = new Function("XLINK_NS", "return " + fnSrc)(XLINK_NS) as (a: unknown) => void;
  const el = (attrs: Record<string, string | undefined>) => {
    const own = { ...attrs };
    return {
      own,
      getAttributeNS: (ns: string | null, n: string) => (ns === XLINK_NS && n === "href" ? own["xlink:href"] ?? null : null),
      hasAttribute: (n: string) => own[n] !== undefined,
      setAttribute: (n: string, v: string) => { own[n] = v; },
      removeAttributeNS: (ns: string | null, n: string) => { if (ns === XLINK_NS && n === "href") delete own["xlink:href"]; },
    };
  };
  const only = el({ "xlink:href": "sibling.md" }); fn(only);
  assert.deepEqual(only.own, { href: "sibling.md" }, "xlink-only: the href copied, the XLink spelling gone");
  const both = el({ href: "a.md", "xlink:href": "b.md" }); fn(both);
  assert.deepEqual(both.own, { href: "a.md" }, "both present: the author's href wins (the browser's rule), the XLink spelling gone");
  const plain = el({ href: "c.md" }); fn(plain);
  assert.deepEqual(plain.own, { href: "c.md" }, "href alone: untouched");
});

test("the chat's click delegate keys on the SAME selector, whether it imports LINK_SEL or spells it locally", () => {
  assert.match(RENDER, /closest\?\.\(LINK_SEL\)/, "the delegate uses LINK_SEL");
  const local = RENDER.match(/const LINK_SEL = "([^"]+)";/);
  const imported = /import \{[^}]*\bLINK_SEL\b[^}]*\} from "\.\/md-links";/.test(RENDER);
  assert.ok(local || imported, "LINK_SEL is defined in render.ts or imported from md-links.ts");
  if (local) assert.equal(local[1], LINK_SEL, "a local copy must not drift from the shared one (md-links.ts)");
});
