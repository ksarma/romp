// The viewer's links after the sanitize: every element a note can follow a link from, not only <a href>
// (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does; the 2026-09-07 review). DOMPurify's html profile
// keeps an image map (<map>, <area href>, usemap) and its svg profile keeps an inline SVG <a> spelled `href` or
// `xlink:href`. mdBlock's link passes (file-view.ts) ran over `a[href]`: an <area> is not an anchor, `[href]`
// matches only the null-namespace attribute, and `a.target = "_blank"` on an SVGAElement is a silent no-op (its
// `target` is a read-only SVGAnimatedString, and the bundle is not strict there), so a click on any of the three
// took the Files document to the URL in the same frame, the defect class the slice closes for <form>. Now one
// shared selector (LINK_SEL, md-links.ts) and one href reader (linkHref) serve mdBlock and the chat's click
// delegate, and the viewer stamps target and rel with setAttribute. Executed here: linkHref. Pinned at the source
// (file-view.ts has no jsdom harness, as every viewer test notes): the selector in both of mdBlock's passes, the
// attribute writes, the xlink normalisation before the doc gate, and the chat delegate keying on the same
// selector. The clicks themselves run in headless Chromium: md-sanitize-viewer-links-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { LINK_SEL, XLINK_NS, linkHref } from "./md-links";

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

test("LINK_SEL names every element a sanitized note can follow a link from: an anchor in any href namespace, and an area", () => {
  assert.equal(LINK_SEL, "a[*|href], area[href]");
  // `*|href` covers a[href] too (any namespace includes none), so a plain `a[href]` alongside it would be redundant
  assert.doesNotMatch(LINK_SEL, /(^|, )a\[href\]/);
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
  assert.match(MD_FN, /a\.setAttribute\("title", joined\);/, "the sibling link's tooltip is set as an attribute");
  assert.match(MD_FN, /SVGAnimatedString/, "the reason is written down beside the write");
});

test("an SVG anchor's xlink:href is copied to a plain href before either pass, so the delegates and the browser read one attribute", () => {
  const norm = MD_FN.indexOf('querySelectorAll("a[*|href]:not([href])")');
  const docGate = MD_FN.indexOf("if (doc) {");
  const sanitize = MD_FN.indexOf("sanitizeMd(");
  assert.ok(norm > -1, "the normalisation pass exists");
  assert.ok(sanitize < norm && norm < docGate, "after the sanitize (the attribute must survive DOMPurify first), before the doc gate (both passes see it)");
  assert.match(MD_FN, /querySelectorAll\("a\[\*\|href\]:not\(\[href\]\)"\)\.forEach\(\(a\) => \{ a\.setAttribute\("href", linkHref\(a\)\); \}\);/);
});

test("the chat's click delegate keys on the SAME selector, whether it imports LINK_SEL or spells it locally", () => {
  assert.match(RENDER, /closest\?\.\(LINK_SEL\)/, "the delegate uses LINK_SEL");
  const local = RENDER.match(/const LINK_SEL = "([^"]+)";/);
  const imported = /import \{[^}]*\bLINK_SEL\b[^}]*\} from "\.\/md-links";/.test(RENDER);
  assert.ok(local || imported, "LINK_SEL is defined in render.ts or imported from md-links.ts");
  if (local) assert.equal(local[1], LINK_SEL, "a local copy must not drift from the shared one (md-links.ts)");
});
