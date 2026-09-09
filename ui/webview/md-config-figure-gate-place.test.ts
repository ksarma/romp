// The reader's place when the top-visible block is an html block holding a GATED figure (reader-place.ts ownedElements
// and noteText; figure-gate.ts; plans/markdown-viewer.md Slice 4, decision 8; the Slice 4 review). An html block's
// pairing is trusted only when the block's own source, parsed by DOMParser, yields as many elements with the same text
// as the rendered elements carry. The gate wraps a remote figure in a `span.fv-gate` placeholder whose label reads
// "Image from host. Click to load.", text the viewer wrote and the block's source never held: read through textContent,
// a `<p><img src="https://remote.test/...">` block's rendered `<p>` read the label against a parse reading nothing, the
// pairing was refused, readPlace answered null, and a Raw switch from the figure at the edge seated nothing (the return
// trip landed fourteen paragraphs past the figure in the review's measurement). The rendered side is now read as the
// anchor map reads it, the viewer's controls skipped (anchor-map.ts CONTROL_CLASSES), so the gated block reads as its
// block, whether the placeholder sits inside the block's `<p>` or IS the block's element (a bare `<img>` line), and so
// does an html `<pre><code>` the viewer parked a Copy button in (the same rule, the fence's control). The skip is the
// controls' alone: text in the rendered element that is not the block's still refuses the pairing.
// The stand-in is a minimal tree with a box per element (the file-view-place-blocks.test.ts shape, cut to what these
// scenes read), and its DOMParser parses the block's source into the same kind of tree; the placeholder is built here as
// figure-gate.ts builds it (its classes and action imported from the module). The real thing, over the real bundle in
// headless Chromium, is md-config-figure-gate-place-browser.test.ts. Synthetic fixtures only: hosts under .test.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { readPlace } from "./reader-place";
import { sourceBlockSpans, renderedBlockIndex } from "./anchor-map";
import { GATE_CLASS, GATE_LABEL_CLASS, GATE_ACT } from "./figure-gate";

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
class FakeNode {
  nodeType = 0;
  parentNode: FakeNode | null = null;
  childNodes: FakeNode[] = [];
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as FakeText).data : this.childNodes.map((c) => c.textContent).join(""); }
}
class FakeText extends FakeNode { nodeType = 3; constructor(public data: string) { super(); } }
class FakeElement extends FakeNode {
  nodeType = 1;
  attrs = new Map<string, string>();
  scrollTop = 0;
  /** the box a test gives the element; none means no layout */
  box: { top: number; bottom: number } | null = null;
  constructor(public tagName: string) { super(); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  appendChild(n: FakeNode): FakeNode { this.childNodes.push(n); n.parentNode = this; return n; }
  /** `tag`, `.class` or `tag.class`, the shapes reader-place.ts asks for */
  matches(sel: string): boolean {
    const m = /^([a-z]+)?((?:\.[\w-]+)*)$/.exec(sel);
    if (!m) throw new Error("stand-in: unsupported selector " + sel);
    if (m[1] && m[1].toUpperCase() !== this.tagName) return false;
    const classes = (this.getAttribute("class") || "").split(/\s+/);
    return (m[2].match(/\.[\w-]+/g) || []).every((c) => classes.includes(c.slice(1)));
  }
  querySelector(sel: string): FakeElement | null {
    for (const c of this.childNodes) {
      if (!(c instanceof FakeElement)) continue;
      if (c.matches(sel)) return c;
      const d = c.querySelector(sel); if (d) return d;
    }
    return null;
  }
  getBoundingClientRect(): { top: number; bottom: number; left: number; right: number; width: number; height: number } {
    const b = this.box || { top: 0, bottom: 0 };
    return { top: b.top, bottom: b.bottom, left: 0, right: this.box ? 400 : 0, width: this.box ? 400 : 0, height: b.bottom - b.top };
  }
}
const el = (tag: string, attrs: Record<string, string> = {}, kids: FakeNode[] = []): FakeElement => {
  const e = new FakeElement(tag.toUpperCase());
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  for (const k of kids) e.appendChild(k);
  return e;
};
const txt = (s: string): FakeText => new FakeText(s);
const VOID = new Set(["br", "hr", "img", "source", "track", "wbr"]);
/** An html block's source as a tree: tags and text, void elements not nesting; a newline right after <pre> dropped, as an
 *  HTML parser drops it. Entities are not decoded: none of these scenes carries one. */
function parseHTML(html: string): FakeNode[] {
  const root = el("root");
  let cur: FakeElement = root;
  const re = /<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[3] !== undefined) { cur.appendChild(txt(m[3])); continue; }
    const tag = m[1].toLowerCase();
    if (m[0][1] === "/") { if (cur.tagName === tag.toUpperCase() && cur.parentNode) cur = cur.parentNode as FakeElement; continue; }
    const e = el(tag);
    const attrRe = /([\w-]+)(?:="([^"]*)")?/g; let a: RegExpExecArray | null;
    while ((a = attrRe.exec(m[2]))) e.setAttribute(a[1], a[2] === undefined ? "" : a[2]);
    cur.appendChild(e);
    if (!VOID.has(tag)) { cur = e; if (tag === "pre" && html[re.lastIndex] === "\n") re.lastIndex++; }
  }
  return root.childNodes.slice();
}
/** The browser's DOMParser over parseHTML: what reader-place.ts parses an html block's source with. */
class FakeDOMParser {
  parseFromString(html: string, _type: string): { body: FakeElement } {
    const body = el("body");
    for (const n of parseHTML(html)) body.appendChild(n);
    return { body };
  }
}
if (typeof (globalThis as { DOMParser?: unknown }).DOMParser !== "function") (globalThis as { DOMParser?: unknown }).DOMParser = FakeDOMParser;
const El = (n: FakeNode) => n as unknown as Element;
const H = (n: FakeNode) => n as unknown as HTMLElement;

// ── the scenes ─────────────────────────────────────────────────────────────────────────────────────
const PARA = (i: number): string => `Paragraph ${i}: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor.`;
const HOST = "remote.test";
const SRC = `https://${HOST}/a.png`;
/** The placeholder as figure-gate.ts gate() leaves it around the media element: the classes and the action are the
 *  module's; every fetching attribute moved to data-fv-gated-*; the label the viewer's. */
const gated = (media: FakeElement, kind = "Image"): FakeElement => el("span", { class: GATE_CLASS, "data-act": GATE_ACT, role: "button", tabindex: "0", "data-fv-hosts": HOST, "data-fv-host": HOST, title: "Load from " + HOST },
  [media, el("span", { class: GATE_LABEL_CLASS }, [txt(`${kind} from ${HOST}. Click to load.`)])]);
const gatedImg = (): FakeElement => el("img", { width: "120", height: "80", alt: "fig", "data-fv-gated-src": SRC });

/** `.fileview-body > div.fileview-md > [h1, p1, p2, X, p3, p4]`, each box 40px tall with an 8px gap, stacked so that
 *  X (the fourth element) straddles the body's top edge at 100 (its box 80..120): the scene of a reader 20px into it. */
function scene(block: FakeElement): { body: FakeElement; md: FakeElement; blocks: FakeElement[] } {
  const body = el("div", { class: "fileview-body" }); body.box = { top: 100, bottom: 700 }; body.scrollTop = 500;
  const md = el("div", { class: "fileview-md" });
  const blocks = [el("h1", { id: "md-report" }, [txt("Report")]), el("p", {}, [txt(PARA(1))]), el("p", {}, [txt(PARA(2))]), block, el("p", {}, [txt(PARA(3))]), el("p", {}, [txt(PARA(4))])];
  let y = 100 - 3 * 48 - 20;
  for (const b of blocks) { b.box = { top: y, bottom: y + 40 }; y += 48; md.appendChild(b); }
  body.appendChild(md);
  return { body, md, blocks };
}
const docWith = (html: string): string => "# Report\n\n" + PARA(1) + "\n\n" + PARA(2) + "\n\n" + html + "\n\n" + PARA(3) + "\n\n" + PARA(4) + "\n";

test("readPlace: an html block whose figure the gate wrapped reads as its block, the placeholder's label skipped as the anchor map skips it: inside the block's <p>, as the block's own element (a bare <img> line), and a Copy button in an html <pre><code> the same way; text in the element that is not the block's still refuses the pairing", () => {
  const scenes: Array<[string, string, FakeElement]> = [
    ["a gated picture inside the block's <p>", `<p><img src="${SRC}" width="120" height="80" alt="fig"></p>`, el("p", {}, [gated(gatedImg())])],
    ["a gated bare <img> line: the placeholder is the block's element", `<img src="${SRC}" width="120" height="80" alt="fig">`, gated(gatedImg())],
    ["a gated picture beside the block's own text", `<p>Figure 1. <img src="${SRC}" alt="fig"> The caption.</p>`, el("p", {}, [txt("Figure 1. "), gated(el("img", { alt: "fig", "data-fv-gated-src": SRC })), txt(" The caption.")])],
    ["a gated video (its label says Video)", `<video src="https://${HOST}/clip.mp4" width="160" height="90"></video>`, gated(el("video", { width: "160", height: "90", "data-fv-gated-src": `https://${HOST}/clip.mp4` }), "Video")],
    ["an html <pre><code> with the viewer's Copy button", "<pre><code>x = 1\ny = 2</code></pre>", el("pre", { class: "has-copy" }, [el("code", {}, [txt("x = 1\ny = 2")]), el("button", { class: "code-copy", type: "button" }, [txt("Copy")])])],
  ];
  for (const [what, html, rendered] of scenes) {
    const doc = docWith(html);
    const spans = sourceBlockSpans(doc);
    const b = spans.findIndex((sp) => doc.slice(sp.start, sp.end) === html);
    assert.ok(b > 0, what + ": the fixture holds the html block as one block");
    const s = scene(rendered);
    assert.equal(renderedBlockIndex(El(s.md), doc, El(rendered)), b, what + ": the anchor map pairs the rendered element to the block (the pairing itself was never the failure)");
    const place = readPlace(H(s.body), doc);
    assert.ok(place, what + ": a place (the textContent compare read the viewer's label against a parse of the source and refused the block)");
    assert.equal(doc.slice(place!.start, place!.end), html, what + ": the html block");
    assert.equal(place!.top, -20, what + ": the block's box, the reader 20px into it");
    assert.equal(place!.height, 40, what + ": the block's height");
  }
  // the skip is the controls' alone: a rendered element carrying text the block's source does not hold is still no place
  // (the header's swallowed-run rule; here a placeholder AND a stray text node against a source of the picture alone)
  const html = `<p><img src="${SRC}" alt="fig"></p>`;
  const doc = docWith(html);
  const s = scene(el("p", {}, [gated(el("img", { alt: "fig", "data-fv-gated-src": SRC })), txt("Swallowed text the block never held.")]));
  assert.equal(readPlace(H(s.body), doc), null, "text beside the placeholder that is not the block's: the pairing is refused as before");
  // and a paragraph before such a block reads as ever
  const s2 = scene(el("p", {}, [gated(gatedImg())]));
  s2.blocks.forEach((k, i) => { k.box = { top: 100 - 2 * 48 - 20 + i * 48, bottom: 100 - 2 * 48 - 20 + i * 48 + 40 }; });
  const q = readPlace(H(s2.body), doc);
  assert.ok(q, "paragraph 2 at the edge: a place");
  assert.equal(doc.slice(q!.start, q!.end), PARA(2));
});
