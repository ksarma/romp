// The paint-reference strip, executed under node (paint-refs.ts): remoteUrlRef's rule over every spelling the reader follows,
// and dropRemoteRefs over a fake element tree (attributes removed, style declarations dropped one by one, the root and HTML
// elements read too, the count). The browser half, the chat page rendering a message whose svg carries these references
// while a server logs what arrives, is its own leg. Synthetic values only: hosts under .invalid, the page on 127.0.0.1.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { URL_ATTRS, URL_PROPERTIES, cssUrls, remoteUrlRef, dropRemoteRefs } from "./paint-refs";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a fake enumerates its primitives alone

const ORIGIN = "http://127.0.0.1:7777", BASE = ORIGIN + "/chat?x=1", KERNEL = "http://127.0.0.1:8888";
const OWN = [ORIGIN, KERNEL];

// ── remoteUrlRef: the rule, one row per spelling ────────────────────────────────────────────────────────

/** [value, remote under the page's origins and base, why]. */
const CASES: Array<[string, boolean, string]> = [
  // STAYS
  ["url(#g)", false, "a same-document reference (the local gradient)"],
  ['url("#g")', false, "quoted, the same"],
  ["url(data:image/svg+xml,%3Csvg%2F%3E)", false, "a data: URL"],
  ['url("data:image/png;base64,iVBORw0KGgo=")', false, "a quoted data: URL"],
  ["url(" + ORIGIN + "/own.svg#p)", false, "this origin, absolute"],
  ["url(own.svg#p)", false, "relative: resolves against the base to this origin"],
  ["url(/file?path=p.svg#p)", false, "an absolute path on this origin"],
  ["url(" + KERNEL + "/file?path=p.svg#p)", false, "the kernel's origin, the second of the page's own"],
  ["url(blob:" + ORIGIN + "/0000-1111)", false, "a blob: URL of this origin (its origin is its inner URL's)"],
  ["url(   /file?path=a.svg#p   )", false, "whitespace inside the parens is not the URL's"],
  ["url(/*x*/p.svg)", false, "inside an unquoted url token `/*` is URL text, not a comment: a same-origin path, as the browser reads it"],
  ["red", false, "a colour: no URL at all"],
  ["none", false, "no URL"],
  // DROPS
  ["url(https://remote.invalid/p.svg#p)", true, "another host"],
  ["url(//remote.invalid/p.svg#p)", true, "protocol-relative: another host"],
  ["url(https://127.0.0.1:7777/p.svg#p)", true, "another scheme on the same host and port: another origin"],
  ["url(http://127.0.0.1:9999/p.svg#p)", true, "another port on the same host"],
  ["url(javascript:alert(1))", true, "javascript: (the reader stops the url token at the inner paren; an opaque origin)"],
  ['url("javascript:alert(1)")', true, "quoted javascript:"],
  ["url(about:blank)", true, "about: (an opaque origin)"],
  ['url("https://[bad/p.svg")', true, "unparsable: fails closed"],
  ['url("http://remote invalid/p.svg")', true, "unparsable (a space in the host): fails closed"],
  ["\\75 rl(https://remote.invalid/p.svg#p)", true, "the escaped spelling \\75 rl( is url( to the browser"],
  ["u\\72 l(https://remote.invalid/p.svg#p)", true, "an escape inside the name"],
  ["\\75\r\nrl(https://remote.invalid/p.svg#p)", true, "an escape whose one whitespace is a CRLF pair (preprocessed to one newline)"],
  ["/* c */url(https://remote.invalid/p.svg#p)", true, "a comment before the function is skipped"],
  ['url(/* c */"https://remote.invalid/p.svg")', true, "a comment inside url( before a string: the browser reads a bad url, the reader reads the string and judges it (over-reading costs an attribute)"],
  ["URL(https://remote.invalid/p.svg#p)", true, "upper-case URL("],
  ["url(\n  https://remote.invalid/p.svg#p  \n)", true, "whitespace and newlines inside the value"],
  ['image-set("own.png" 1x, "https://remote.invalid/a.png" 2x)', true, "an image-set with one remote member: the value is judged by any remote member"],
  ["image-set(url(https://remote.invalid/a.png) 1x)", true, "an image-set candidate as a url"],
  ["url(#m), url(https://remote.invalid/b.svg#m)", true, "two mask layers, the second remote"],
  ["url(https://remote.invalid/p.svg#p) red", true, "a paint with a fallback colour"],
  ["blur(2px) url(https://remote.invalid/f.svg#f)", true, "a filter list"],
  ["url(blob:https://remote.invalid/0000)", true, "a blob: URL of another origin"],
];

test("remoteUrlRef: every spelling the reader follows, judged by the rule (# and data: and the page's own origins stay; another host, scheme or port, protocol-relative, javascript:, about:, unparsable and any value with one remote member drop)", () => {
  // guards the STAYS/DROPS rule row by row: a row that flips is a reference kept that fetches, or a local paint removed
  for (const [value, remote, why] of CASES) assert.equal(remoteUrlRef(value, OWN, BASE), remote, JSON.stringify(value) + ": " + why);
  // the reader is cssUrls, one tokenizer for the gate and the strip: every DROPS row names at least one URL to it
  for (const [value, remote] of CASES) if (remote) assert.ok(cssUrls(value).length > 0, JSON.stringify(value) + ": cssUrls reads a URL out of it");
});

test("remoteUrlRef with no page (node: no origins, no base): # and data: stay, every relative and absolute reference drops; an opaque origin in the list never admits javascript: or about:", () => {
  // guards the fail-closed side of the rule where the sanitizer runs with nothing to resolve against: dropping a same-origin
  // paint costs a colour, keeping an unresolved one could cost a request
  assert.equal(remoteUrlRef("url(#g)", [], ""), false, "a same-document reference is decided before any parse, so it stays with no base");
  assert.equal(remoteUrlRef("url(data:image/svg+xml,%3Csvg%2F%3E)", [], ""), false, "a data: URL parses with no base and stays");
  assert.equal(remoteUrlRef("url(own.svg#p)", [], ""), true, "a relative reference with no base is unparsable: it drops");
  assert.equal(remoteUrlRef("url(" + ORIGIN + "/own.svg#p)", [], ""), true, "no origin is own: every absolute reference drops");
  assert.equal(remoteUrlRef("url(javascript:x)", ["null"], ""), true, "the opaque origin `null` is never own, even when a caller lists it");
  assert.equal(remoteUrlRef("url(about:blank)", ["null"], BASE), true);
});

// ── dropRemoteRefs over a fake tree ─────────────────────────────────────────────────────────────────────

/** A fake element: what dropRemoteRefs reads (querySelectorAll("*"), getAttribute) and writes (setAttribute, removeAttribute),
 *  through the shim, so a failing dump shows the serial and the tag. The tests read `attrs` directly. */
type Fake = { tagName: string; attrs: Record<string, string>; children: Fake[]; writes: number;
  getAttribute(n: string): string | null; setAttribute(n: string, v: string): void; removeAttribute(n: string): void; querySelectorAll(sel: string): Fake[] };
function el(tag: string, attrs: Record<string, string> = {}, kids: Fake[] = []): Fake {
  const e: Fake = {
    tagName: tag, attrs: { ...attrs }, children: kids, writes: 0,
    getAttribute(n) { return Object.prototype.hasOwnProperty.call(e.attrs, n) ? e.attrs[n] : null; },
    setAttribute(n, v) { e.attrs[n] = v; e.writes++; },
    removeAttribute(n) { delete e.attrs[n]; e.writes++; },
    querySelectorAll(sel) { assert.equal(sel, "*", "the strip walks every element"); const out: Fake[] = []; const walk = (x: Fake) => { for (const k of x.children) { out.push(k); walk(k); } }; walk(e); return out; },
  };
  return hideEdges(e);
}
const R = (s: string) => "url(https://remote.invalid/" + s + ")";
const asNode = (f: Fake) => f as unknown as ParentNode;

test("dropRemoteRefs removes each remote attribute of URL_ATTRS on every element, the root included, HTML elements too, and leaves every other attribute and every local reference; the fallback colour goes with its url()", () => {
  // guards the attribute arm: the attribute goes whole (no rewrite to the fallback), the element stays, and the names are read on
  // every element, the root itself included
  const withFallback = el("rect", { fill: R("p.svg#p") + " red", width: "4" });
  const local = el("rect", { fill: "url(#g)", stroke: "url(data:image/svg+xml,%3Csvg%2F%3E)", "clip-path": "url(/file?path=c.svg#c)", mask: "url(" + ORIGIN + "/m.svg#m)" });
  const markers = el("path", { d: "M0 0L4 4", "marker-start": R("ms.svg#m"), "marker-mid": R("mm.svg#m"), "marker-end": R("me.svg#m") });
  const cursor = el("rect", { cursor: R("c.svg#c") + ", auto" });
  const html = el("span", { fill: R("h.svg#p"), mask: 'image-set("https://remote.invalid/h.png" 1x)', class: "x" });
  const root = el("svg", { fill: R("root.svg#p"), filter: "blur(2px) " + R("f.svg#f"), width: "12" }, [el("g", {}, [withFallback, local, markers, cursor]), html]);
  const n = dropRemoteRefs(asNode(root), OWN, BASE);
  assert.deepEqual(root.attrs, { width: "12" }, "the root element itself: its remote fill and filter are removed");
  assert.deepEqual(withFallback.attrs, { width: "4" }, "a fallback colour after a remote url() goes with the attribute");
  assert.deepEqual(local.attrs, { fill: "url(#g)", stroke: "url(data:image/svg+xml,%3Csvg%2F%3E)", "clip-path": "url(/file?path=c.svg#c)", mask: "url(" + ORIGIN + "/m.svg#m)" }, "every local reference stays, untouched");
  assert.equal(local.writes, 0, "and nothing was written to it");
  assert.deepEqual(markers.attrs, { d: "M0 0L4 4" }, "the three marker attributes go");
  assert.deepEqual(cursor.attrs, {}, "cursor, the ninth name, is read too (the sanitizer drops it today; the set is what the engines read)");
  assert.deepEqual(html.attrs, { class: "x" }, "an HTML element's paint attributes go too: the names are read on every element");
  assert.equal(n, 9, "the count: two on the root, one fallback fill, three markers, one cursor, two on the span, and no local one");
  assert.equal(dropRemoteRefs(asNode(root), OWN, BASE), 0, "a second pass finds nothing");
});

test("dropRemoteRefs on a style attribute: each remote declaration of a URL_PROPERTIES property goes and the rest stays, the attribute goes when nothing is left, a declaration's comment, escape or case is read as the browser reads it, and a remote reference the declarations cannot account for removes the attribute whole", () => {
  // guards the style arm: the declaration is the unit (colorOnlyStyle's shape), each judged on its own as the browser splits them,
  // and a remote reference outside a URL property's declaration fails closed
  const cases: Array<[string, string | null, number, string]> = [
    ["color: red; mask-image: " + R("m.png"), "color: red", 1, "the remote mask-image goes, the colour stays"],
    ["background-image: " + R("b.png"), null, 1, "nothing left: the attribute goes"],
    ["fill: url(#g); stroke: " + R("s.svg#s") + "; color: blue", "fill: url(#g); color: blue", 1, "a local fill stays beside a removed stroke"],
    ["COLOR: red; Background: red " + R("b.png") + " no-repeat", "COLOR: red", 1, "a property name is case-insensitive; the kept text is as written"],
    ["/* c */ list-style: square " + R("l.png") + "; color: red", "color: red", 1, "a comment before the name"],
    ["b\\61 ckground-image: " + R("b.png") + "; color: red", "color: red", 1, "an escaped property name is the property it spells"],
    ["cursor: " + R("c.svg") + ", auto; -webkit-mask-box-image: " + R("w.png") + " 10 / 10px", null, 2, "two remote declarations, both go"],
    ["content: \"a;b\" " + R("x.png") + "; color: red", "color: red", 1, "a `;` inside a string does not split the declaration"],
    ["background: url(a;b) , " + R("y.png") + "; color: red", "color: red", 1, "a `;` inside a url token does not split"],
    ["background-image: url(x\"y); mask-image: " + R("m.png"), "background-image: url(x\"y)", 1, "a bad url runs to its `)`, as the browser's does: the next declaration is its own"],
    ["color: " + R("x.png") + "; background-color: red", null, 1, "a remote reference in a property outside URL_PROPERTIES (the browser ignores it): the attribute goes whole, fail closed"],
    ["--paint: " + R("v.svg#p") + "; fill: var(--paint)", null, 1, "a custom property holding a remote url(): the attribute goes whole"],
    ["color: red; background-color: #abc", "color: red; background-color: #abc", 0, "nothing remote: untouched"],
    ["fill: url(" + ORIGIN + "/own.svg#p); color: red", "fill: url(" + ORIGIN + "/own.svg#p); color: red", 0, "this origin's own: untouched"],
  ];
  for (const [style, after, count, why] of cases) {
    const e = el("rect", { style, width: "4" });
    const n = dropRemoteRefs(asNode(el("svg", {}, [e])), OWN, BASE);
    assert.equal(e.getAttribute("style"), after, JSON.stringify(style) + ": " + why);
    assert.equal(e.getAttribute("width"), "4", "the element's other attributes stay");
    assert.equal(n, count, JSON.stringify(style) + ": the count");
    if (count === 0) assert.equal(e.writes, 0, JSON.stringify(style) + ": an untouched style is not rewritten");
  }
});

test("URL_ATTRS and URL_PROPERTIES are the derived sets: nine attributes and thirty-four properties, sorted, without duplicates; every attribute name is also a property", () => {
  // guards the data against an edit that drops or adds a name by hand: the sets change only with a new derivation (the header),
  // and paint-refs-census.test.ts holds the sanitizer's surviving attributes to them
  assert.deepEqual([...URL_ATTRS], ["clip-path", "cursor", "fill", "filter", "marker-end", "marker-mid", "marker-start", "mask", "stroke"]);
  assert.equal(URL_PROPERTIES.length, 34, "the union over the three engines: Chromium's 30, Firefox's one more, WebKit's three more");
  assert.deepEqual([...URL_PROPERTIES], [...new Set(URL_PROPERTIES)].sort(), "sorted, no duplicates");
  for (const a of URL_ATTRS) assert.ok(URL_PROPERTIES.includes(a), a + ": a presentation attribute is the property of the same name");
  for (const p of ["-moz-border-image", "-webkit-backdrop-filter", "mask-border", "mask-border-source", "background-image", "mask-image", "list-style-image", "content", "offset-path"]) {
    assert.ok(URL_PROPERTIES.includes(p), p + " is in the union");
  }
});
