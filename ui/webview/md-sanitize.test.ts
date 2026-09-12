// The shared markdown sanitizer's pure parts, in node. DOMPurify itself needs a window, so the sanitize call and
// the DOM post-passes are proven in headless Chromium: md-sanitize-browser.test.ts opens a note in the real file
// viewer, md-sanitize-postpass-browser.test.ts runs the chat's pipeline, md-sanitize-chat-fragment-browser.test.ts
// clicks a message's own `#` link over the real chat bundle. Here: the colour grammar an inline `style` is held to,
// the profile's forbidden tags and attributes, the three hook bodies (the style rewrite, the comment drop, the body
// title's drop), the hooks' install guard, and the source pins that
// make md-sanitize.ts the ONE sanitizer the dashboard has (the chat's md() and userMd(), the viewer's mdBlock). The
// design is plans/markdown-viewer.md, Slice 1 (sanitize as GitHub does; the colour-only rule is its decision 6), and
// the last test holds SECURITY.md's output-sanitization bullet to the math renderer's trust boundary and its bounds
// (KaTeX after DOMPurify).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MD_FORBID_TAGS, MD_FORBID_ATTR, MD_PURIFY, USER_CONTENT_PREFIX, colorOnlyStyle, isLiteralColor, styleAttributeHook, dropCommentChildren, dropBodyTitle, installMdSanitizeHooks } from "./md-sanitize";
import { hideEdges, sameNodes } from "../test-dom-shim";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const ROOT = path.resolve(UI, "..", "..");
const repo = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");

// ── the colour grammar ──────────────────────────────────────────────────────────────────────────────

test("a literal colour: a keyword, #hex of 3 to 8 digits, or rgb/rgba/hsl/hsla over plain numeric arguments", () => {
  for (const v of ["red", "Red", "transparent", "currentcolor", "inherit", "#abc", "#abcd", "#aabbcc", "#AABBCCDD",
                   "rgb(200, 0, 0)", "rgb(200 0 0)", "rgb(200 0 0 / 50%)", "rgba(1,2,3,.5)", "rgba(1, 2, 3, 0.5)",
                   "hsl(120, 50%, 50%)", "hsl(120deg 50% 50%)", "hsla(120 50% 50% / 0.4)", "hsl(none 50% 50%)", "rgb(+10 -0 0.5)"]) {
    assert.ok(isLiteralColor(v), "accepted: " + v);
  }
});

test("not a literal colour: other functions, nested parentheses, escapes, quotes, !important, wrong arity", () => {
  for (const v of ["url(x)", "url(javascript:alert(1))", "var(--x)", "expression(alert(1))", "calc(1px)", "rgb(var(--x))",
                   "rgb(1,2)", "rgb(1,2,3,4,5)", "rgb()", "red !important", "red\"", "'red'", "#ab", "#abcdefabc", "#ggg",
                   "rgb(1,2,3)) ;", "red;color:blue", "rgb(1,2,3/**/)", "r\\65d", "rgb(1 2 3) x", "rgb(1px 2 3)", "red blue", "", " "]) {
    assert.ok(!isLiteralColor(v), "rejected: " + JSON.stringify(v));
  }
});

test("colorOnlyStyle keeps color and background-color with literal values, in order, and nothing else", () => {
  assert.equal(colorOnlyStyle("color: rgb(200, 0, 0); font-size: 80px"), "color: rgb(200, 0, 0)");
  assert.equal(colorOnlyStyle("position:fixed;inset:0;background:red"), "", "`background` is not `background-color`: the shorthand takes images and positions");
  assert.equal(colorOnlyStyle("COLOR: Red; Background-Color: #abc"), "color: Red; background-color: #abc", "property names case-folded, values as written");
  assert.equal(colorOnlyStyle("color: red !important"), "");
  assert.equal(colorOnlyStyle("color: url(javascript:alert(1))"), "");
  assert.equal(colorOnlyStyle("color: red; color: blue"), "color: red; color: blue", "a repeated property is two valid declarations");
  assert.equal(colorOnlyStyle("color"), "");
  assert.equal(colorOnlyStyle("color:"), "");
  assert.equal(colorOnlyStyle(""), "");
  assert.equal(colorOnlyStyle("background-color: rgb(0 0 0 / 50%)"), "background-color: rgb(0 0 0 / 50%)");
  assert.equal(colorOnlyStyle("color: red; background: url(x); background-color: var(--y); display: none"), "color: red");
  assert.equal(colorOnlyStyle("color: red; }; .fileview { display: none"), "color: red", "a declaration that tries to close the block is an invalid declaration");
  assert.equal(colorOnlyStyle("color: rgb(1,2,3); font-family: x; color: hsl(1 2% 3%)"), "color: rgb(1,2,3); color: hsl(1 2% 3%)");
});

// ── the hook ────────────────────────────────────────────────────────────────────────────────────────

test("the style hook rewrites a style attribute to its colours, drops it when none remain, and leaves other attributes to DOMPurify", () => {
  const kept = { attrName: "style", attrValue: "color: red; position: fixed; inset: 0", keepAttr: true };
  styleAttributeHook(kept);
  assert.deepEqual(kept, { attrName: "style", attrValue: "color: red", keepAttr: true });
  const dropped = { attrName: "style", attrValue: "position:fixed;inset:0;background:red", keepAttr: true };
  styleAttributeHook(dropped);
  assert.equal(dropped.keepAttr, false, "nothing survived: the attribute goes");
  const other = { attrName: "href", attrValue: "position:fixed", keepAttr: true };
  styleAttributeHook(other);
  assert.deepEqual(other, { attrName: "href", attrValue: "position:fixed", keepAttr: true }, "not a style attribute: untouched (DOMPurify's own URI rules apply)");
  const upper = { attrName: "style", attrValue: "COLOR: #fff", keepAttr: true };
  styleAttributeHook(upper);
  assert.equal(upper.attrValue, "color: #fff");
});

// A stand-in node for the two element-hook bodies, which read nodeType, childNodes, namespaceURI, parentNode and
// ownerDocument and call removeChild and appendChild (the DOM's names; the hooks run inside DOMPurify's walk, over real nodes;
// here the bodies are proven pure, as the style hook's is above), built through the shared shim like every ui test fake:
// hideEdges stamps the serial and hides the childNodes list, the parent, the document and the methods, so a failing assertion
// over a fake dumps its numbers and never its tree (ui/test-dom-shim.ts; the ratchet in ui/test-dom-shim.test.ts reads the
// longhand `childNodes: kids` as the edge the call must cover). `removed` counts the removeChild calls, so a test can say the
// hook touched nothing. appendChild MOVES an attached node, as the DOM's does (the old parent's removeChild first: the removal
// DOMPurify's NodeIterator steps over), and remove() is the node's own, so the hook's earlier cut runs over the same fakes.
const TEXT = 3, ELEMENT = 1, COMMENT = 8, FRAGMENT = 11;
type FakeNode = {
  nodeType: number; namespaceURI: string | undefined; childNodes: FakeNode[]; parentNode: FakeNode | null; ownerDocument: FakeDocument; removed: number;
  removeChild(c: FakeNode): FakeNode; appendChild(c: FakeNode): FakeNode; remove(): void;
};
/** The fakes' one document: mints the fragment dropBodyTitle asks for and keeps every one, so a test can read where a title went. */
type FakeDocument = { fragments: FakeNode[]; createDocumentFragment(): FakeNode };
const fakeDocument: FakeDocument = hideEdges({ fragments: [] as FakeNode[], createDocumentFragment() { const f = fakeNode(FRAGMENT); fakeDocument.fragments.push(f); return f; } });
function fakeNode(nodeType: number, kids: FakeNode[] = [], namespaceURI?: string): FakeNode {
  const n: FakeNode = {
    nodeType, namespaceURI, childNodes: kids, parentNode: null, ownerDocument: fakeDocument, removed: 0,
    removeChild(c) { const i = n.childNodes.indexOf(c); if (i < 0) throw new Error("not a child"); n.childNodes.splice(i, 1); c.parentNode = null; n.removed++; return c; },
    appendChild(c) { if (c.parentNode) c.parentNode.removeChild(c); c.parentNode = n; n.childNodes.push(c); return c; },
    remove() { if (n.parentNode) n.parentNode.removeChild(n); },
  };
  for (const k of kids) k.parentNode = n;
  return hideEdges(n);
}

/** DOMPurify 3.4.10's `_forceRemove`, transcribed over the fakes (purify.es.mjs): detach the node through its parent, and when
 *  that throws (a parentless node: `getParentNode(node)` is null, so `.removeChild` is a TypeError) fall back to the node's own
 *  remove(), a no-op with no parent, and throw when the node is still parentless. The three branches of `_sanitizeElements`
 *  after the uponSanitizeElement hook that drop a node all end here (the markup guard, the disallowed-tag branch, the namespace
 *  check), so this is the call the hook's removal must leave survivable; the node test has no window for the real one, and
 *  md-sanitize-body-title-browser.test.ts runs the real one over the same configs. */
function forceRemove(node: FakeNode): void {
  try { (node.parentNode as FakeNode).removeChild(node); }
  catch (_) {
    node.remove();
    if (!node.parentNode) throw new TypeError("a node selected for removal could not be detached from its tree and cannot be safely returned; refusing to sanitize in place");
  }
}

test("the fakes go through the shim: a fake node enumerates as its serial, its numbers and its namespace, the childNodes edge, the parent, the document and the methods hidden, so a failing assertion over one dumps no tree", () => {
  const el = fakeNode(ELEMENT, [fakeNode(COMMENT), fakeNode(TEXT)]);
  assert.deepEqual(Object.keys(el).sort(), ["_nid", "nodeType", "removed"], "no namespace given: the undefined placeholder hides with the objects");
  assert.deepEqual(Object.keys(fakeNode(ELEMENT, [], "ns")).sort(), ["_nid", "namespaceURI", "nodeType", "removed"], "a namespace is a string and stays");
  for (const edge of ["childNodes", "parentNode", "ownerDocument"]) assert.equal(Object.getOwnPropertyDescriptor(el, edge)!.enumerable, false, edge + " is an own property, hidden from enumeration");
  assert.equal(el.childNodes.length, 2, "and still there to read");
  assert.ok(el.childNodes[0].parentNode === el, "a child knows its parent");
  assert.deepEqual(Object.keys(fakeDocument).sort(), ["_nid"], "the document hides its fragments and its method");
});

test("dropCommentChildren: an element loses every comment child and nothing else, in one pass over a snapshot of its children", () => {
  const nested = fakeNode(ELEMENT, [fakeNode(COMMENT)]);
  const el = fakeNode(ELEMENT, [fakeNode(COMMENT), fakeNode(TEXT), fakeNode(COMMENT), fakeNode(COMMENT), nested, fakeNode(TEXT), fakeNode(COMMENT)]);
  dropCommentChildren(el as unknown as Node);
  assert.deepEqual(el.childNodes.map((c) => c.nodeType), [TEXT, ELEMENT, TEXT], "the comments are gone, the text and the element stay in order");
  assert.equal(el.removed, 4, "adjacent comments are both removed: the walk is over a snapshot, not the live list a removal shifts");
  assert.deepEqual(nested.childNodes.map((c) => c.nodeType), [COMMENT], "a comment inside a child element is that element's, dropped when DOMPurify's walk reaches it");
  dropCommentChildren(el as unknown as Node);
  assert.equal(el.removed, 4, "a second pass finds nothing to remove");
});

test("dropCommentChildren leaves a non-element alone and cannot throw on a clobbered childNodes", () => {
  const text = fakeNode(TEXT, [fakeNode(COMMENT)]);   // a text node holds no children in the DOM; the hook must not act on the type
  dropCommentChildren(text as unknown as Node);
  assert.equal(text.removed, 0);
  const comment = fakeNode(COMMENT, [fakeNode(COMMENT)]);
  dropCommentChildren(comment as unknown as Node);
  assert.equal(comment.removed, 0);
  // a form whose <input name="childNodes"> shadows the list: DOMPurify removes a clobbered form for the names it
  // probes, and childNodes is not one of them, so the hook reads what it is given and steps back
  const clobbered = hideEdges({ nodeType: ELEMENT, childNodes: { nodeName: "INPUT" }, removeChild() { throw new Error("must not be called"); } });
  assert.deepEqual(Object.keys(clobbered).sort(), ["_nid", "nodeType"], "the clobbered stand-in goes through the shim too");
  assert.doesNotThrow(() => dropCommentChildren(clobbered as unknown as Node));
  const empty = fakeNode(ELEMENT);
  dropCommentChildren(empty as unknown as Node);
  assert.equal(empty.removed, 0);
});

test("dropBodyTitle: an HTML `<title>` leaves the tree WITH its text, into a fragment of its own document, before DOMPurify judges it, and the allowedTags set the hook is handed is left as it was; an svg's `<title>`, every other element, and a non-element the walk names title are untouched (the Slice 5 review, round 5: the svg profile kept a body title as a hidden element whose text the reader and the paint read as shown; the PR's review, round 1: the first cut set `title` off in that set, DOMPurify's live per-call set, so the write stood on every later element of the call)", () => {
  const HTML_NS = "http://www.w3.org/1999/xhtml", SVG_NS = "http://www.w3.org/2000/svg";
  const title = (ns: string) => fakeNode(ELEMENT, [fakeNode(TEXT)], ns);
  const data = (tagName: string) => ({ tagName, allowedTags: { title: true, p: true, svg: true } });
  // <p>a</p><title>T</title><p>b</p><svg><title>S</title></svg>, each element as the walk meets it
  let d = data("title");
  const a = fakeNode(ELEMENT, [fakeNode(TEXT)], HTML_NS), t1 = title(HTML_NS), b = fakeNode(ELEMENT, [fakeNode(TEXT)], HTML_NS);
  const svgTitle = title(SVG_NS), svg = fakeNode(ELEMENT, [svgTitle], SVG_NS);
  const body = fakeNode(ELEMENT, [a, t1, b, svg], HTML_NS);
  const before = fakeDocument.fragments.length;
  dropBodyTitle(t1 as unknown as Node, d);
  sameNodes(body.childNodes, [a, b, svg], "a body title: out of the body before DOMPurify judges it");
  assert.equal(fakeDocument.fragments.length, before + 1, "into one fresh fragment of the node's own document");
  const frag = fakeDocument.fragments[before];
  assert.ok(t1.parentNode === frag, "the fragment is the title's parent now: every DOMPurify branch after the hook detaches through the parent");
  sameNodes(frag.childNodes, [t1], "the fragment holds the title alone");
  assert.deepEqual(t1.childNodes.map((c) => c.nodeType), [TEXT], "its text went with it: nothing is unwrapped into the body");
  assert.deepEqual(d.allowedTags, { title: true, p: true, svg: true }, "the set DOMPurify hands the hook is untouched: it is the live set for the rest of the call");
  dropBodyTitle(svgTitle as unknown as Node, d);
  assert.ok(svgTitle.parentNode === svg, "an svg title: the drawing's own element, kept where it is");
  assert.equal(svg.removed, 0);
  assert.equal(fakeDocument.fragments.length, before + 1, "and no fragment minted for it");
  assert.deepEqual(d.allowedTags, { title: true, p: true, svg: true });
  d = data("p");
  dropBodyTitle(a as unknown as Node, d);
  assert.ok(a.parentNode === body, "another element: untouched");
  assert.equal(fakeDocument.fragments.length, before + 1);
  d = data("title");
  const text = fakeNode(TEXT, [], HTML_NS), holder = fakeNode(ELEMENT, [text], HTML_NS);
  dropBodyTitle(text as unknown as Node, d);
  assert.ok(text.parentNode === holder, "a non-element the walk names title: untouched");
  assert.equal(holder.removed, 0);
  assert.equal(fakeDocument.fragments.length, before + 1);
  assert.deepEqual(d.allowedTags, { title: true, p: true, svg: true });
});

test("dropBodyTitle under every profile: with `title` NOT allowed (the html profile alone) or forbidden (FORBID_TAGS, a set the hook is never handed), DOMPurify's own force-remove of the moved title detaches it from the fragment, no throw, and the title is gone with its text; under the default profile the body title is out of the body and the svg's stays (the PR's review, round 2: the second cut's remove() left the title parentless, and 3.4.10's _forceRemove throws for a parentless node, so the hook was safe only while `title` stayed allowed)", () => {
  const HTML_NS = "http://www.w3.org/1999/xhtml", SVG_NS = "http://www.w3.org/2000/svg";
  const title = (ns: string) => fakeNode(ELEMENT, [fakeNode(TEXT)], ns);
  const data = (allowed: Record<string, boolean>) => ({ tagName: "title", allowedTags: allowed });
  const before = fakeDocument.fragments.length;
  // the hazard the transcription carries: a parentless node is what makes _forceRemove throw
  assert.throws(() => forceRemove(title(HTML_NS)), TypeError, "the transcribed _forceRemove throws for a parentless node, as 3.4.10's does");
  // under the html profile alone (`title` is in DOMPurify's svg list and not its html list) or with `title` in FORBID_TAGS,
  // DOMPurify's disallowed-tag branch force-removes the title the hook has moved, and that removal must find a parent
  const configs: Array<[string, Record<string, boolean>]> = [
    ["a profile without svg, title off the allowed set", { p: true }],
    ["title forbidden: on the allowed set, listed in FORBID_TAGS", { title: true, p: true }],
  ];
  for (const [why, allowed] of configs) {
    const t = title(HTML_NS), p = fakeNode(ELEMENT, [fakeNode(TEXT)], HTML_NS);
    const root = fakeNode(ELEMENT, [p, t], HTML_NS);
    dropBodyTitle(t as unknown as Node, data(allowed));
    sameNodes(root.childNodes, [p], why + ": the title is out of the body before DOMPurify judges it");
    assert.ok(t.parentNode !== null && t.parentNode.nodeType === FRAGMENT, why + ": and has a parent, the fragment");
    assert.doesNotThrow(() => forceRemove(t), why + ": DOMPurify's own removal of the disallowed title detaches it from the fragment (before: the node's own remove() left it parentless, and _forceRemove threw a TypeError)");
    assert.equal(t.parentNode, null, why + ": detached");
    assert.deepEqual(t.childNodes.map((c) => c.nodeType), [TEXT], why + ": the text is the title's still, in no tree");
  }
  assert.equal(fakeDocument.fragments.length, before + 2, "one fragment per moved title");
  // the default profile keeps an allowed title where it stands, so the moved title's fate is the fragment's: out of the body,
  // its text with it, the svg's title where it was; and the other two dropping branches (the markup guard, the namespace
  // check) are the same _forceRemove, so the moved title would survive them too, were either to fire for a title (neither
  // does: the guard reads escaped innerHTML, an HTML title passes the check)
  const t = title(HTML_NS), svgTitle = title(SVG_NS), svg = fakeNode(ELEMENT, [svgTitle], SVG_NS), p = fakeNode(ELEMENT, [fakeNode(TEXT)], HTML_NS);
  const body = fakeNode(ELEMENT, [p, t, svg], HTML_NS);
  const d = data({ title: true, p: true, svg: true });
  dropBodyTitle(t as unknown as Node, d);
  dropBodyTitle(svgTitle as unknown as Node, d);
  sameNodes(body.childNodes, [p, svg], "the default profile: the body title is out of the body, the svg stays");
  assert.ok(svgTitle.parentNode === svg, "and the svg's title stays inside it");
  assert.deepEqual(t.childNodes.map((c) => c.nodeType), [TEXT], "the body title's text went with it");
  assert.doesNotThrow(() => forceRemove(t), "a force-remove of the moved title, were a branch to fire for it, detaches from the fragment");
  assert.deepEqual(d.allowedTags, { title: true, p: true, svg: true }, "the set is untouched under every profile");
  assert.equal(fakeDocument.fragments.length, before + 3);
});

test("installMdSanitizeHooks registers its two hooks ONCE however often it is called: the style rewrite on uponSanitizeAttribute, the comment drop and the body title's drop on uponSanitizeElement", () => {
  // The guard is module-global and never reset, so this test must be the module's FIRST installer: node runs a
  // file's tests in order, and nothing above calls installMdSanitizeHooks or sanitizeMd (which would need a window).
  const calls: { name: string; fn: Function }[] = [];
  const fake = { addHook: (name: string, fn: Function) => { calls.push({ name, fn }); } } as unknown as Parameters<typeof installMdSanitizeHooks>[0];
  installMdSanitizeHooks(fake);
  installMdSanitizeHooks(fake);
  installMdSanitizeHooks(fake);
  assert.equal(calls.length, 2, "idempotent: a second registration would run the rewrite twice per attribute and the drop twice per element");
  assert.deepEqual(calls.map((c) => c.name), ["uponSanitizeAttribute", "uponSanitizeElement"]);
  const ev = { attrName: "style", attrValue: "font-size: 80px; color: rgb(200, 0, 0)", keepAttr: true, allowedAttributes: {}, forceKeepAttr: undefined };
  calls[0].fn.call(fake, {} as Element, ev, {});
  assert.equal(ev.attrValue, "color: rgb(200, 0, 0)");
  assert.equal(ev.keepAttr, true);
  // the element hook is the comment drop: DOMPurify calls it with the node, the tag data and the config, and only the
  // node matters to it
  const el = fakeNode(ELEMENT, [fakeNode(TEXT), fakeNode(COMMENT), fakeNode(ELEMENT)]);
  const allowed: Record<string, boolean> = { title: true, p: true };
  calls[1].fn.call(fake, el as unknown as Node, { tagName: "p", allowedTags: allowed }, {});
  assert.deepEqual(el.childNodes.map((c) => c.nodeType), [TEXT, ELEMENT], "the comment child is gone before DOMPurify's markup guard reads the element's innerHTML");
  assert.deepEqual(allowed, { title: true, p: true }, "a paragraph leaves the allowed set alone");
  // the same hook drops a body title: an HTML-namespace `title` leaves the body whole, for a fragment of its document, and the set
  // DOMPurify judges by is left alone
  const title = fakeNode(ELEMENT, [fakeNode(TEXT)], "http://www.w3.org/1999/xhtml"), body = fakeNode(ELEMENT, [title]);
  calls[1].fn.call(fake, title as unknown as Node, { tagName: "title", allowedTags: allowed }, {});
  assert.equal(body.childNodes.length, 0, "the body title's drop rides the same element hook (dropBodyTitle)");
  assert.equal(title.parentNode && title.parentNode.nodeType, FRAGMENT, "into a fragment, a parent DOMPurify's own removal can detach it from under any profile");
  assert.deepEqual(allowed, { title: true, p: true }, "and writes nothing in the set: DOMPurify hands the hook its live per-call set");
  assert.deepEqual(title.childNodes.map((c) => c.nodeType), [TEXT], "the title's own text goes with the element; nothing is unwrapped");
});

// ── the profile ─────────────────────────────────────────────────────────────────────────────────────

test("the profile: html + svg, data: on img, no data-*, the forbidden tags, prefixed ids and names; input stays for the task checkbox", () => {
  assert.deepEqual(MD_PURIFY.USE_PROFILES, { html: true, svg: true });
  assert.deepEqual(MD_PURIFY.ADD_DATA_URI_TAGS, ["img"]);
  assert.equal(MD_PURIFY.ALLOW_DATA_ATTR, false);
  assert.equal(MD_PURIFY.SANITIZE_NAMED_PROPS, true, "an author's id and name are prefixed user-content- (GitHub's rule), never dropped");
  assert.equal(USER_CONTENT_PREFIX, "user-content-", "the prefix DOMPurify writes; the lookups compare against it");
  assert.deepEqual(MD_PURIFY.FORBID_TAGS, [...MD_FORBID_TAGS]);
  for (const tag of ["style", "dialog", "form", "button", "select", "option", "optgroup", "textarea", "fieldset", "legend", "label", "datalist", "output", "meter", "progress", "map", "area"]) {
    assert.ok(MD_FORBID_TAGS.includes(tag), tag + " is forbidden");
  }
  assert.ok(!MD_FORBID_TAGS.includes("input"), "input is allowed by the profile; sanitizeMd's post-pass keeps only a disabled checkbox");
  assert.ok(!MD_FORBID_TAGS.includes("details") && !MD_FORBID_TAGS.includes("summary"), "details/summary are prose structure GitHub keeps");
  assert.deepEqual(MD_PURIFY.FORBID_ATTR, [...MD_FORBID_ATTR]);
  assert.deepEqual([...MD_FORBID_ATTR], ["background", "usemap"], "two forbidden attributes: a background image fetches on render with no click; usemap binds an image map, which is dropped");
});

// ── source pins: one sanitizer ──────────────────────────────────────────────────────────────────────

test("md-sanitize.ts holds the dashboard's ONLY DOMPurify.sanitize call; render.ts and file-view.ts import sanitizeMd and no dompurify of their own", () => {
  const sources = fs.readdirSync(UI).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts") && !f.endsWith(".d.ts"));
  const callers = sources.filter((f) => /DOMPurify\.sanitize\(/.test(read(f)));
  assert.deepEqual(callers, ["md-sanitize.ts"], "every other module goes through sanitizeMd");
  const SAN = read("md-sanitize.ts");
  assert.equal((SAN.match(/DOMPurify\.sanitize\(/g) || []).length, 1);
  assert.match(SAN, /export function sanitizeMd\(dirty: string, own\?: \(body: HTMLElement\) => void\): HTMLElement \{\n\s*installMdSanitizeHooks\(\);\n\s*const clean = DOMPurify\.sanitize\(dirty, \{ \.\.\.MD_PURIFY, RETURN_DOM: true \}\) as HTMLElement;/,
    "the hook is installed before the first sanitize, and the profile is spread with RETURN_DOM; the caller's own pass is optional (the chat's md() and userMd() pass none)");
  assert.match(SAN, /keepOnlyInertCheckboxes\(clean\);\n\s*if \(own\) own\(clean\);\n\s*for \(const pass of postPasses\) pass\(clean\);\n\s*return clean;/,
    "the input post-pass, then the caller's own pass (the viewer's heading ids, read from the text as written), then every registered post-pass (the math fill), on the sanitized DOM before it is handed back");
  assert.match(SAN, /export function registerMdPostPass\(pass: \(root: ParentNode\) => void\): void \{\n\s*if \(!postPasses\.includes\(pass\)\) postPasses\.push\(pass\);\n\}/, "the registry: idempotent, a pass registered twice runs once (md-sanitize-katex-browser.test.ts executes it)");
  assert.match(SAN, /const postPasses: Array<\(root: ParentNode\) => void> = \[\];/, "the registry is a module array of passes over the sanitized body, empty until a grammar module registers one");
  const importers = sources.filter((f) => /from "dompurify"/.test(read(f)));
  assert.deepEqual(importers, ["md-sanitize.ts"]);
  assert.match(read("render.ts"), /import \{[^}]*\bsanitizeMd\b[^}]*\} from "\.\/md-sanitize";/);
  assert.match(read("file-view.ts"), /import \{ sanitizeMd, revealFragmentTarget \} from "\.\/md-sanitize";/);   // plus the reveal step the viewer's scrollToFragment shares with the chat's `#` delegate
  assert.equal((read("render.ts").match(/sanitizeMd\(/g) || []).length, 2, "md() and userMd()");
  assert.equal((read("file-view.ts").match(/sanitizeMd\(/g) || []).length, 1, "mdBlock");
});

test("the math fill is registered as a sanitizeMd post-pass by the module that installs the grammar, so no renderer calls it by hand", () => {
  const grammar = read("md-config.ts");   // the one configuration: the grammar and its fill travel together (Slice 4 of plans/markdown-viewer.md)
  assert.match(grammar, /import \{ mathBlock, mathInline, renderMathPlaceholders \} from "\.\/math";/);
  assert.match(grammar, /import \{ registerMdPostPass \} from "\.\/md-sanitize";/);
  assert.match(grammar, /^registerMdPostPass\(renderMathPlaceholders\);$/m);
  assert.doesNotMatch(read("render.ts"), /renderMathPlaceholders\(|from "\.\/math"/, "render.ts renders no math of its own: the fill rides every sanitizeMd call");
  assert.doesNotMatch(read("file-view.ts"), /renderMathPlaceholders|from "\.\/math"|from "\.\/chat-md"/, "the viewer imports no grammar of its own: md-config.ts, which it applies, carries the grammar and its fill into every bundle that hosts it (Slice 4 of plans/markdown-viewer.md)");
});

test("the feed bundle carries the sanitizer, the grammar, the fill and KaTeX: every bundle that hosts the viewer renders math (Slice 4 of plans/markdown-viewer.md, decision 1)", () => {
  // What the import pins above promise, checked on the built graph: esbuild's metafile lists every module the feed
  // entry pulls in. file-view.ts brings md-sanitize.ts (the viewer renders notes in the feed page too) and md-config.ts,
  // which brings math.ts and the katex package (before Slice 4 the feed bundle had none of the three and a note's
  // formulas showed as bare TeX there); chat-md.ts, the chat's own user-bubble renderer, and render.ts stay the chat
  // bundle's alone (math-bundles.test.ts holds the same for files.js and render.js).
  const EXT = process.cwd();                                      // npm test runs in vscode-extension
  const esbuild = createRequire(path.join(EXT, "package.json"))("esbuild");   // the extension's esbuild, wherever this bundle was written
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, "feed.ts")], bundle: true, write: false, metafile: true, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  const inputs = Object.keys(r.metafile.inputs as Record<string, unknown>).map((f) => f.replace(/\\/g, "/"));
  assert.ok(inputs.some((f) => f.endsWith("ui/webview/md-sanitize.ts")), "the feed bundle sanitizes through md-sanitize.ts (via file-view.ts)");
  assert.ok(inputs.some((f) => f.endsWith("ui/webview/file-view.ts")));
  assert.ok(inputs.some((f) => f.endsWith("ui/webview/md-config.ts")), "the one configuration, the grammar and its fill's registration");
  assert.ok(inputs.some((f) => f.endsWith("ui/webview/math.ts")), "the math grammar and the fill");
  assert.ok(inputs.some((f) => /node_modules\/katex\//.test(f)), "KaTeX, the library behind the fill");
  const stray = inputs.filter((f) => /ui\/webview\/(chat-md|render)\.ts$/.test(f));
  assert.deepEqual(stray, [], "the chat's own renderers ride in no other bundle");
});

test("the submit backstop: one preventDefault listener on the viewer body in openFileView AND openUrlView, installed before any render swaps the body's children", () => {
  const VIEW = read("file-view.ts");
  const local = VIEW.split("export function openFileView(")[1].split("\nexport function ")[0];
  const url = VIEW.split("export function openUrlView(")[1].split("\nexport function ")[0];
  for (const [name, fn] of [["openFileView", local], ["openUrlView", url]] as const) {
    assert.equal((fn.match(/body\.addEventListener\("submit", \(ev\) => \{ ev\.preventDefault\(\); \}\);/g) || []).length, 1, name + " installs the backstop once per open");
    assert.ok(fn.indexOf('body.addEventListener("submit"') < fn.indexOf("body.replaceChildren("), name + ": installed before any render swaps the body's children");
    // the same stable body carries the click listener: openFileView's one listener (file-view-links.test.ts; fork PR #347),
    // openUrlView's delegate for its fv-anchor stamp
    assert.ok(fn.includes("delegate(body, {") || fn.includes('body.addEventListener("click"'), name + ": the same stable body carries the click listener");
  }
});

test("contain: layout on .fileview-md in BOTH sheets, byte-equal, with the media caps; the rules and the table's are in the parity list", () => {
  const rule = (css: string, head: string) => { const at = css.indexOf(head); assert.ok(at >= 0, head + " present"); return css.slice(at, css.indexOf("}", at) + 1); };
  const chat = rule(read("styles.css"), ".fileview-md {"), feed = rule(read("feed.css"), ".fileview-md {");
  assert.equal(chat, feed);
  assert.match(chat, /contain: layout;/);
  assert.doesNotMatch(chat, /contain: (paint|strict|content|size)/, "layout only: paint containment would clip the body's scroll and a table's own horizontal scroll");
  const MEDIA = ":where(.fileview-md) svg, :where(.fileview-md) canvas, :where(.fileview-md) video {";
  assert.equal(rule(read("styles.css"), MEDIA), rule(read("feed.css"), MEDIA));
  assert.match(rule(read("styles.css"), MEDIA), /max-width: 100%;/);
  // a table wider than the column scrolls on its own: under layout containment the body cannot scroll to it. The rules are
  // Slice 3's (plans/markdown-viewer.md): the table box scrolls sideways inside the pane-wide break-out `.fileview-md > table`
  // gives a direct child, so the scroll is asserted here and the rules' bytes are held by the parity list
  const TABLE = ".fileview-md table {", WIDE = ".fileview-md > table {";
  assert.equal(rule(read("styles.css"), TABLE), rule(read("feed.css"), TABLE));
  assert.match(rule(read("styles.css"), TABLE), /overflow-x: auto;/);
  assert.equal(rule(read("styles.css"), WIDE), rule(read("feed.css"), WIDE));
  const parity = read("fileview-parity.test.ts");
  assert.match(parity, /"\.fileview-md \{"/);
  assert.ok(parity.includes(JSON.stringify(MEDIA)), "the media cap is pinned byte-equal too");
  assert.ok(parity.includes(JSON.stringify(TABLE)) && parity.includes(JSON.stringify(WIDE)), "and the table rules");
});

// ── the documents ───────────────────────────────────────────────────────────────────────────────────

/** A phrase as a document wraps it: any run of whitespace between words. */
const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+"));

test("the guide says what a file's own HTML may do, in the terms the code enforces", () => {
  const guide = fs.readFileSync(path.join(ROOT, "docs", "guide.md"), "utf8");
  const at = guide.indexOf("**A file's own HTML.**");
  assert.ok(at >= 0, "the guide has the paragraph");
  const para = guide.slice(at, guide.indexOf("\n\n", at));
  assert.match(para, /`<style>`/);
  assert.match(para, /user-content-/);
  assert.match(para, /`color` and `background-color`/);
  assert.match(para, /`background=`/);
  assert.match(para, prose("cannot be ticked"));
  assert.match(para, prose("HTML comment is dropped"), "the comment rule: dropped before the element holding it is judged, so the prose around it stays (dropCommentChildren)");
  assert.match(para, prose("An HTML `<title>` is dropped with its text"), "the body title rule: dropped with its text, since the browser shows one nowhere outside the page's head (dropBodyTitle)");
  assert.match(para, prose("the `<title>` of an inline `svg`, the drawing's tooltip, stays"), "and its one exception, dropBodyTitle's namespace test: an svg's own <title> is kept (review round 6: the sentence had said every <title> is dropped, while the same paragraph says an inline svg is kept)");
  assert.doesNotMatch(para, /\u2014/, "no em dash");
});

test("SECURITY.md's output-sanitization bullet names KaTeX as the renderer that writes after DOMPurify, under trust: false and the plan's bounds", () => {
  // On main KaTeX's markup was part of marked's output and went through DOMPurify with the rest. This slice renders
  // the fill AFTER the sanitizer (renderMathPlaceholders writes katex.render's DOM into the sanitized body), so what
  // keeps a formula from minting a link or a style is KaTeX's `trust: false` and the bounds math.ts sets, not
  // DOMPurify. SECURITY.md is the document the repo points security readers at, and its bullet went on saying every
  // rendered fragment of model output passes through DOMPurify (review round 6, 2026-09-08). The precedent is
  // security-pdf.test.ts, which holds the same bullet to the PDF renderer's posture: the bullet, the plan section it
  // points at, the code, and the pins it names move together.
  const security = repo("SECURITY.md");
  assert.match(security, /markdown through marked and\s+DOMPurify/, "SECURITY.md still names the sanitizer beside the PDF renderer");
  const hardened = security.slice(security.indexOf("\n## What is already hardened\n"));
  const at = hardened.indexOf("- **Output sanitization:**");
  assert.ok(at >= 0, "SECURITY.md's hardened list has an Output sanitization bullet");
  const rest = hardened.slice(at);
  const end = rest.indexOf("\n- ", 1);
  const bullet = end === -1 ? rest : rest.slice(0, end);
  assert.match(bullet, /KaTeX/, "the bullet names the renderer that writes to the sanitized DOM after DOMPurify");
  assert.match(bullet, prose("after DOMPurify has run"), "and says when it writes");
  assert.match(bullet, /`trust: false`/, "and the option its safety rests on");
  for (const bound of ["the sizes a formula asks for", "macro expansion", "one formula", "one message or note", "shown as its source"]) {
    assert.match(bullet, prose(bound), `the bullet names the bound: ${bound}`);
  }
  assert.match(bullet, prose('stated under "Slice 1" in `plans/markdown-viewer.md`'), "where the bounds are stated, by file and heading");
  assert.match(bullet, prose("checked against the code by `ui/webview/render-math.test.ts` and `ui/webview/md-sanitize-postpass-browser.test.ts`"), "and where they are checked, by path");
  assert.doesNotMatch(bullet, /\u2014/, "the bullet's prose carries no em dash");

  // the plan section the bullet points at exists and states each bound the bullet summarizes
  const plan = repo("plans", "markdown-viewer.md");
  const start = plan.indexOf("\n### Slice 1: sanitize as GitHub does\n");
  assert.ok(start >= 0, "the plan has the Slice 1 heading the bullet points at");
  const body = plan.slice(start + 1);
  const next = body.slice(1).search(/\n##/);
  const slice1 = next === -1 ? body : body.slice(0, next + 1);
  for (const term of ["trust: false", "`maxSize`", "`maxExpand`", "`MATH_TEX_MAX_CHARS`", "`MATH_TEX_BUDGET_CHARS`"]) {
    assert.ok(slice1.includes(term), `the plan's Slice 1 states the bound the bullet summarizes: ${term}`);
  }

  // the code has the boundary the bullet describes: DOMPurify first, the registered fill on its output, under the option
  const san = read("md-sanitize.ts");
  assert.ok(san.indexOf("DOMPurify.sanitize(dirty") < san.indexOf("for (const pass of postPasses) pass(clean);"), "the fill runs on the DOM DOMPurify has already returned");
  const math = read("math.ts");
  assert.match(math, /trust: false/, "math.ts renders under trust: false");
  for (const c of ["MATH_TEX_MAX_CHARS", "MATH_TEX_BUDGET_CHARS", "MATH_MAX_SIZE_EM"]) assert.match(math, new RegExp("export const " + c + " = "), c + " is math.ts's constant");
  assert.match(math, /maxExpand/, "and computes KaTeX's expansion count per formula (render-math.test.ts pins the function and the call)");

  // the pins the bullet names are on disk and hold what it says
  assert.match(read("render-math.test.ts"), /trust: false/, "render-math.test.ts pins the option against math.ts");
  assert.ok(read("md-sanitize-postpass-browser.test.ts").includes("\\\\href{javascript:alert(1)}{x}"), "the browser leg renders a hand-written \\href through the real pipeline and finds no link");
});
