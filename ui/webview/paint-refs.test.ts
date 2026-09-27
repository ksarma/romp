// The paint-reference strip, executed under node (paint-refs.ts): remoteUrlRef's rule over every spelling the reader follows,
// and dropRemoteRefs over a fake element tree (attributes removed, style declarations dropped one by one, the root and HTML
// elements read too, the count). The browser half, the chat page rendering a message whose svg carries these references
// while a server logs what arrives, is its own leg. Synthetic values only: hosts under .invalid, the page on 127.0.0.1.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { URL_ATTRS, URL_PROPERTIES, DATA_RASTER_TYPES, cssUrls, dataMediaType, dataUrlIsRaster, dataDocumentRef, remoteUrlRef, dropDataDocuments, dropRemoteRefs } from "./paint-refs";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a fake enumerates its primitives alone

const ORIGIN = "http://127.0.0.1:7777", BASE = ORIGIN + "/chat?x=1", KERNEL = "http://127.0.0.1:8888";
const OWN = [ORIGIN, KERNEL];

// ── remoteUrlRef: the rule, one row per spelling ────────────────────────────────────────────────────────

/** [value, remote under the page's origins and base, why]. */
const CASES: Array<[string, boolean, string]> = [
  // STAYS
  ["url(#g)", false, "a same-document reference (the local gradient)"],
  ['url("#g")', false, "quoted, the same"],
  ["url(data:image/gif;base64,R0lGODlhAQABAAAAACw=)", false, "a data: URL of a raster type"],
  ['url("data:image/png;base64,iVBORw0KGgo=")', false, "a quoted data: URL of a raster type"],
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
  ['url("data:image/svg+xml,%3Csvg%2F%3E#p")', true, "a data: SVG document with its fragment (Firefox loads it as a resource document, which fetches its own @import)"],
  ["url(data:,x)", true, "a data: URL with no type: text/plain, not a raster"],
  ["url(#m), url(data:text/xml,x#m)", true, "a local layer beside a data: XML document: the value is judged by its document member"],
];

test("remoteUrlRef: every spelling the reader follows, judged by the rule (#, a raster data: URL and the page's own origins stay; another host, scheme or port, protocol-relative, javascript:, about:, a data: URL of any other type, unparsable and any value with one remote member drop)", () => {
  // guards the STAYS/DROPS rule row by row: a row that flips is a reference kept that fetches, or a local paint removed
  for (const [value, remote, why] of CASES) assert.equal(remoteUrlRef(value, OWN, BASE), remote, JSON.stringify(value) + ": " + why);
  // the reader is cssUrls, one tokenizer for the gate and the strip: every DROPS row names at least one URL to it
  for (const [value, remote] of CASES) if (remote) assert.ok(cssUrls(value).length > 0, JSON.stringify(value) + ": cssUrls reads a URL out of it");
});

test("remoteUrlRef with no page (node: no origins, no base): # and a raster data: URL stay, a data: SVG document and every relative and absolute reference drop; an opaque origin in the list never admits javascript: or about:", () => {
  // guards the fail-closed side of the rule where the sanitizer runs with nothing to resolve against: dropping a same-origin
  // paint costs a colour, keeping an unresolved one could cost a request
  assert.equal(remoteUrlRef("url(#g)", [], ""), false, "a same-document reference is decided before any parse, so it stays with no base");
  assert.equal(remoteUrlRef("url(data:image/png;base64,iVBORw0KGgo=)", [], ""), false, "a raster data: URL parses with no base and stays");
  assert.equal(remoteUrlRef("url(data:image/svg+xml,%3Csvg%2F%3E#p)", [], ""), true, "a data: SVG document parses with no base and drops: its type is not a raster");
  assert.equal(remoteUrlRef("url(own.svg#p)", [], ""), true, "a relative reference with no base is unparsable: it drops");
  assert.equal(remoteUrlRef("url(" + ORIGIN + "/own.svg#p)", [], ""), true, "no origin is own: every absolute reference drops");
  assert.equal(remoteUrlRef("url(javascript:x)", ["null"], ""), true, "the opaque origin `null` is never own, even when a caller lists it");
  assert.equal(remoteUrlRef("url(about:blank)", ["null"], BASE), true);
});

// ── the data: rule: the media type's essence, read as the Fetch standard's data: URL processor reads it ──────

/** [data: URL, the essence dataMediaType reads (null: the processor fails), why]. */
const ESSENCES: Array<[string, string | null, string]> = [
  ["data:image/png,x", "image/png", "the plain spelling"],
  ["data:IMAGE/PNG,x", "image/png", "case: the essence is lower-cased"],
  ["data:Image/Svg+Xml,x", "image/svg+xml", "case on a document type too"],
  ["data:image/png;charset=x,x", "image/png", "a parameter is outside the essence"],
  ["data:image/png;base64,iVBORw0KGgo=", "image/png", "base64 is outside the essence"],
  ["data:image/png;BASE64,iVBORw0KGgo=", "image/png", "in any case"],
  ["data:image/png ; base64,iVBORw0KGgo=", "image/png", "spaces before the parameters are trimmed"],
  ["data:image/svg+xml;charset=utf-8;base64,PHN2Zy8+", "image/svg+xml", "parameters before base64"],
  ["data: image/png ,x", "image/png", "ASCII whitespace around the type is stripped (the URL parser keeps the spaces)"],
  ["data:image/png\t,x", "image/png", "a tab is removed by the URL parser before the processor reads anything"],
  ['data:image/png;x="a,b",x', "image/png", "the first comma ends the type, whatever quotes surround it"],
  ["data:,x", "text/plain", "a missing type is text/plain"],
  ["data:;base64,AAAA", "text/plain", "only base64: text/plain"],
  ["data:;charset=utf-8,x", "text/plain", "only a parameter: text/plain"],
  ["data:image%2Fpng,x", "text/plain", "a percent-encoded slash is no slash: the type does not parse, so text/plain"],
  ["data:image/png x,x", "text/plain", "a space inside the subtype is no token: text/plain"],
  ["data:image/png?x,y", "text/plain", "the query is read as the processor reads it (the serialized URL): `png?x` is no token"],
  ["data:image/,x", "text/plain", "an empty subtype: text/plain"],
  ["data:/png,x", "text/plain", "an empty type: text/plain"],
  ["data:text;x/y,z", "text/plain", "a `;` before the slash: no type"],
  ["data:image/svg+xml;image/png,x", "image/svg+xml", "a raster name in a parameter does not make the type a raster"],
  ["data:text/plain;type=image/png,x", "text/plain", "nor in a parameter's value"],
  ["data:application/xhtml+xml,x", "application/xhtml+xml", "XHTML"],
  ["data:text/xml,x", "text/xml", "XML"],
  ["data:application/xml,x", "application/xml", "XML"],
  ["data:image/png", null, "no comma: the processor fails and the browser loads nothing"],
  ["data:image/png#a,b", null, "a comma in the fragment is not the processor's: no comma"],
  ["data:image/svg+xml,%3Csvg%2F%3E#p", "image/svg+xml", "the fragment is not read"],
];

test("dataMediaType reads the essence as the Fetch data: URL processor does: case, parameters and base64 outside it, whitespace trimmed, a missing or unparsable type text/plain, the serialized URL with its query and without its fragment, null with no comma", () => {
  // guards the parse the allowlist is keyed on: a spelling read differently from the browser is a document the rule keeps
  for (const [url, essence, why] of ESSENCES) assert.equal(dataMediaType(new URL(url)), essence, JSON.stringify(url) + ": " + why);
});

test("DATA_RASTER_TYPES is the raster allowlist the rulings name, sorted; dataUrlIsRaster keeps a data: URL by its parsed essence alone: every raster type in any case and with parameters, and nothing else (svg, xhtml, xml, text/plain, html, a missing or unparsable type, no comma)", () => {
  // guards the allowlist by the parsed essence: the list is the data, and the verdict follows the essence, not the spelling
  assert.deepEqual([...DATA_RASTER_TYPES], ["image/avif", "image/bmp", "image/gif", "image/jpeg", "image/png", "image/vnd.microsoft.icon", "image/webp", "image/x-icon"]);
  for (const t of DATA_RASTER_TYPES) {
    for (const spelling of ["data:" + t + ",x", "data:" + t.toUpperCase() + ";base64,AAAA", "data: " + t + " ;charset=x,x"]) {
      assert.equal(dataUrlIsRaster(new URL(spelling)), true, JSON.stringify(spelling) + ": a raster type, kept whatever the spelling");
      assert.equal(remoteUrlRef('url("' + spelling + '")', [], ""), false, JSON.stringify(spelling) + ": remoteUrlRef keeps it");
    }
  }
  const DOCUMENTS = ["image/svg+xml", "application/xhtml+xml", "text/xml", "application/xml", "text/html", "text/plain", "application/octet-stream", "image/svg"];
  for (const t of DOCUMENTS) {
    for (const spelling of ["data:" + t + ",x#p", "data:" + t.toUpperCase() + ";base64,AAAA#p", "data:" + t + ";charset=utf-8,x#p"]) {
      assert.equal(dataUrlIsRaster(new URL(spelling)), false, JSON.stringify(spelling) + ": not a raster type, dropped whatever the spelling");
      assert.equal(remoteUrlRef('url("' + spelling + '")', [], ""), true, JSON.stringify(spelling) + ": remoteUrlRef drops it");
    }
  }
  for (const [url, essence] of ESSENCES) {
    const kept = essence !== null && DATA_RASTER_TYPES.includes(essence);
    assert.equal(dataUrlIsRaster(new URL(url)), kept, JSON.stringify(url) + ": the verdict is the essence's (" + String(essence) + ")");
    const q = url.includes('"') ? "'" : '"';   // a CSS string in the quote the URL does not hold
    assert.equal(remoteUrlRef("url(" + q + url + q + ")", [], ""), !kept, JSON.stringify(url) + ": remoteUrlRef follows the same verdict");
  }
});

test("dropRemoteRefs on data: references: a document-capable one goes from an attribute and from a style declaration, a raster one stays, and a value with both goes whole", () => {
  // guards the rule on every surface the pass runs (sanitizeMd's default pass and stripRemoteLoads' paint arm both call this):
  // the attribute and the declaration are the units, as for a reference to another origin
  const svgDoc = "url(data:image/svg+xml,%3Csvg%2F%3E#p)";
  const doc = el("rect", { fill: svgDoc, stroke: 'url("data:application/xhtml+xml,x#p")', mask: "url(data:image/png;base64,iVBORw0KGgo=)", width: "4" });
  const mixed = el("rect", { mask: "url(data:image/png;base64,iVBORw0KGgo=), url(data:text/xml,x#m)", "clip-path": "url(data:,x#c)" });
  const styled = el("span", { style: "mask-image: url(data:image/svg+xml,%3Csvg%2F%3E); background-image: url(data:image/png;base64,iVBORw0KGgo=); color: red" });
  const n = dropRemoteRefs(asNode(el("svg", {}, [doc, mixed, styled])), OWN, BASE);
  assert.deepEqual(doc.attrs, { mask: "url(data:image/png;base64,iVBORw0KGgo=)", width: "4" }, "the svg and xhtml documents go, the raster mask stays");
  assert.deepEqual(mixed.attrs, {}, "a raster layer beside an xml document goes with it; a missing type (text/plain) goes");
  assert.deepEqual(styled.attrs, { style: "background-image: url(data:image/png;base64,iVBORw0KGgo=); color: red" }, "the svg mask-image declaration goes, the raster background and the colour stay");
  assert.equal(n, 5, "the count: two on the first rect, two on the second, one declaration");
});

// ── the data: half alone, for the file viewer (dataDocumentRef, dropDataDocuments) ──────────────────────────

test("dataDocumentRef holds a value naming a data: URL that is not a raster, by the parsed essence, and nothing else: the CASES rows remoteUrlRef drops for a data: document and no other row, every ESSENCES spelling by its essence with a base and without, and a reference to another origin, a relative one, a raster data: URL, # and an unparsable URL left alone", () => {
  // guards the viewer's half of the rule: the file viewer keeps references to another origin for its gate, so this judge must
  // hold a data: document and nothing else, by the same parse as remoteUrlRef's
  const DOC_ROWS = ['url("data:image/svg+xml,%3Csvg%2F%3E#p")', "url(data:,x)", "url(#m), url(data:text/xml,x#m)"];
  assert.deepEqual(CASES.filter(([v]) => DOC_ROWS.includes(v)).map(([v]) => v), DOC_ROWS, "the three data: document rows are CASES rows");
  for (const [value, remote] of CASES) {
    assert.equal(dataDocumentRef(value, BASE), DOC_ROWS.includes(value), JSON.stringify(value) + ": held only for a data: document row; every other row, a raster data: URL and every reference to another origin among them, is left alone");
    if (DOC_ROWS.includes(value)) assert.equal(remote, true, JSON.stringify(value) + ": a value the data: half holds is one remoteUrlRef drops too");
  }
  for (const [url, essence] of ESSENCES) {
    const q = url.includes('"') ? "'" : '"';
    const value = "url(" + q + url + q + ")";
    const isDoc = !(essence !== null && DATA_RASTER_TYPES.includes(essence));   // no comma (null) is held too: the browser loads nothing, so dropping it costs nothing, as remoteUrlRef drops it
    assert.equal(dataDocumentRef(value, BASE), isDoc, JSON.stringify(url) + ": held exactly when the parsed essence is not a raster (" + String(essence) + ")");
    assert.equal(dataDocumentRef(value, ""), isDoc, JSON.stringify(url) + ": the same with no base, since a data: URL is absolute");
  }
  const LEFT: Array<[string, string]> = [
    [R("p.svg#p"), "a reference to another origin: the viewer's gate judges it"],
    ["url(//remote.invalid/p.svg#p)", "protocol-relative: another origin, the gate's"],
    ["url(own.svg#p)", "relative: this origin"],
    ["url(#g)", "a same-document reference"],
    ["url(data:image/png;base64,iVBORw0KGgo=)", "a raster data: URL"],
    ["url(DATA:IMAGE/GIF;charset=x,x)", "a raster data: URL in any case, with a parameter"],
    ["url(http://[::1/x)", "unparsable: names nothing the browser can load"],
    ["url(javascript:x)", "another scheme"],
    ["red", "no URL"],
  ];
  for (const [value, why] of LEFT) assert.equal(dataDocumentRef(value, BASE), false, JSON.stringify(value) + ": " + why);
  for (const [value, why] of [
    ["url(data:image/svg+xml,%3Csvg%2F%3E#p)", "a data: SVG document with its fragment"],
    ["url(data:application/xhtml+xml,x#p)", "XHTML"],
    ["url(data:text/xml,x#p)", "XML"],
    ["url(data:,x#p)", "a missing type: text/plain, not a raster"],
    ["url(data:image/png;base64,AAAA), url(data:image/svg+xml,x#m)", "a raster layer beside a document: the value holds one"],
    [R("m.png") + ", url(data:application/xml,x#m)", "another origin's layer beside a document: the document decides"],
  ] as Array<[string, string]>) assert.equal(dataDocumentRef(value, BASE), true, JSON.stringify(value) + ": " + why);
});

test("dropDataDocuments removes a data: document from an attribute and from a style declaration as dropRemoteRefs does, and leaves every reference to another origin, every same-origin one, # and a raster data: URL untouched for the viewer's gate", () => {
  // guards the viewer's drop (md-sanitize.ts sanitizeMd under remoteRefs: "keep"): the data: documents go, and what the gate is
  // for, a reference to another origin, is left in place for it to move aside behind a click
  const svgDoc = "url(data:image/svg+xml,%3Csvg%2F%3E#p)";
  const doc = el("rect", { fill: svgDoc, stroke: 'url("data:application/xhtml+xml,x#p")', mask: "url(data:image/png;base64,iVBORw0KGgo=)", width: "4" });
  const remote = el("rect", { fill: R("p.svg#p"), "clip-path": "url(own.svg#c)", filter: "url(#f)", mask: 'image-set("https://remote.invalid/m.png" 1x)' });
  const mixed = el("rect", { mask: R("m.png") + ", url(data:text/xml,x#m)", "marker-end": "url(data:,x#e)" });
  const styled = el("span", { style: "mask-image: url(data:image/svg+xml,%3Csvg%2F%3E); background-image: " + R("b.png") + "; color: red" });
  const root = el("svg", { fill: "url(data:application/xml,x#p)", width: "12" }, [doc, remote, mixed, styled]);
  const n = dropDataDocuments(asNode(root), BASE);
  assert.deepEqual(root.attrs, { width: "12" }, "the root element itself: its data: document goes");
  assert.deepEqual(doc.attrs, { mask: "url(data:image/png;base64,iVBORw0KGgo=)", width: "4" }, "the svg and xhtml documents go, the raster mask stays");
  assert.deepEqual(remote.attrs, { fill: R("p.svg#p"), "clip-path": "url(own.svg#c)", filter: "url(#f)", mask: 'image-set("https://remote.invalid/m.png" 1x)' }, "a reference to another origin, a same-origin one and # stay, for the gate");
  assert.equal(remote.writes, 0, "and nothing was written to that element");
  assert.deepEqual(mixed.attrs, {}, "a value holding a document goes whole, another origin's layer with it; a missing type (text/plain) goes");
  assert.deepEqual(styled.attrs, { style: "background-image: " + R("b.png") + "; color: red" }, "the svg mask-image declaration goes; another origin's background and the colour stay");
  assert.equal(n, 6, "the count: the root's fill, two on the first rect, two on the third, one declaration");
  assert.equal(dropDataDocuments(asNode(root), BASE), 0, "a second pass finds nothing");
  // the same tree through dropRemoteRefs: every data: document it removes, dropDataDocuments removed too
  const again = el("svg", {}, [el("rect", { fill: svgDoc, stroke: R("s.svg#s") })]);
  dropRemoteRefs(asNode(again), OWN, BASE);
  assert.deepEqual(again.children[0].attrs, {}, "dropRemoteRefs removes both: the data: half is a part of its rule");
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
  const local = el("rect", { fill: "url(#g)", stroke: "url(data:image/png;base64,iVBORw0KGgo=)", "clip-path": "url(/file?path=c.svg#c)", mask: "url(" + ORIGIN + "/m.svg#m)" });
  const markers = el("path", { d: "M0 0L4 4", "marker-start": R("ms.svg#m"), "marker-mid": R("mm.svg#m"), "marker-end": R("me.svg#m") });
  const cursor = el("rect", { cursor: R("c.svg#c") + ", auto" });
  const html = el("span", { fill: R("h.svg#p"), mask: 'image-set("https://remote.invalid/h.png" 1x)', class: "x" });
  const root = el("svg", { fill: R("root.svg#p"), filter: "blur(2px) " + R("f.svg#f"), width: "12" }, [el("g", {}, [withFallback, local, markers, cursor]), html]);
  const n = dropRemoteRefs(asNode(root), OWN, BASE);
  assert.deepEqual(root.attrs, { width: "12" }, "the root element itself: its remote fill and filter are removed");
  assert.deepEqual(withFallback.attrs, { width: "4" }, "a fallback colour after a remote url() goes with the attribute");
  assert.deepEqual(local.attrs, { fill: "url(#g)", stroke: "url(data:image/png;base64,iVBORw0KGgo=)", "clip-path": "url(/file?path=c.svg#c)", mask: "url(" + ORIGIN + "/m.svg#m)" }, "every local reference stays, untouched");
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
