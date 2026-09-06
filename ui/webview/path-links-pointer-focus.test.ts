// path-links.ts's link is a tab stop that a MOUSE PRESS never focuses (fixed 2026-09-06, review round 2).
//
// The span the chat's transcript links were made of had no tabindex, so a click left focus on the body;
// Slice 0 made it a tab stop (Tab reaches it, Enter or Space clicks it), and a tabindex span is focusable
// by the pointer too. The chat's keyboard model reads that difference: Enter with nothing focused drops the
// cursor into the message box (render.ts, the user 2026-06-26), and the viewer a click opens takes no focus
// — so click a link, Escape the viewer, press Enter to reply, and the link's own Enter handler re-opened the
// file instead; a selection dragged FROM a link met the same fate. And in Chromium the focus change itself
// killed that drag's selection. So the press drops the tabindex attribute before the browser's default
// action looks for something to focus, and puts it back on the events that end the press on this span.
//
// The handlers run for real over a DOM stand-in (the path-links.test.ts idiom — no jsdom) that plays the
// browser's part: after the mousedown listeners, focus goes to the target if it is focusable, else to the
// body. What the stand-in cannot show — that the click still fires, that the selection the press starts is
// kept — was checked in headless Chromium and Firefox against a page shaped like the chat (the review's
// probe); the source pins at the end guard the two choices that would break it.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const LINKS = fs.readFileSync(path.join(UI, "path-links.ts"), "utf8");

// synthetic world: the notes-api demo, a placeholder sid
const SID = "11111111-2222-3333-4444-555555555555";

// ── a DOM stand-in: attributes, focus, the handler properties the span sets ────────────────────────
type Handler = ((e: unknown) => void) | null;
class TextNode {
  parentElement: Elm | null = null;
  constructor(public data: string) {}
  replaceWith(frag: Frag): void {
    const p = this.parentElement!;
    const i = p.childNodes.indexOf(this);
    const kids = frag.childNodes.map((c) => (typeof c === "string" ? new TextNode(c) : c));
    for (const k of kids) k.parentElement = p;
    p.childNodes.splice(i, 1, ...kids);
  }
}
class Frag { childNodes: (Elm | TextNode | string)[] = []; appendChild(c: Elm | TextNode | string) { this.childNodes.push(c); } }
class Elm {
  className = ""; title = ""; dataset: Record<string, string> = {}; parentElement: Elm | null = null;
  childNodes: (Elm | TextNode)[] = [];
  attrs: Record<string, string> = {};
  role: string | null = null;
  onkeydown: Handler = null; onmousedown: Handler = null; onmouseup: Handler = null;
  onmouseleave: Handler = null; oncontextmenu: Handler = null; ondragstart: Handler = null; onfocus: Handler = null;
  clicks = 0;
  constructor(public tagName: string) {}
  // tabIndex reflects the attribute, as the IDL attribute does: absent → -1 (not focusable for a span)
  get tabIndex(): number { return "tabindex" in this.attrs ? Number(this.attrs.tabindex) : -1; }
  set tabIndex(v: number) { this.attrs.tabindex = String(v); }
  hasAttribute(n: string): boolean { return n in this.attrs; }
  getAttribute(n: string): string | null { return n in this.attrs ? this.attrs[n] : null; }
  removeAttribute(n: string): void { delete this.attrs[n]; }
  get focusable(): boolean { return this.hasAttribute("tabindex"); }
  focus(): void { if (this.focusable) doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = body; }
  click(): void { this.clicks++; }
  set textContent(s: string) { const t = new TextNode(s); t.parentElement = this; this.childNodes = [t]; }
  get textContent(): string { return this.childNodes.map((c) => (c instanceof TextNode ? c.data : c.textContent)).join(""); }
  appendChild(c: Elm | TextNode): Elm | TextNode { c.parentElement = this; this.childNodes.push(c); return c; }
  closest(sel: string): Elm | null {
    const alts = sel.split(",").map((s) => s.trim());
    for (let n: Elm | null = this; n; n = n.parentElement) {
      for (const a of alts) {
        if (a.startsWith(".") ? n.className.split(/\s+/).includes(a.slice(1)) : n.tagName === a) return n;
      }
    }
    return null;
  }
  get spans(): Elm[] { return this.childNodes.filter((c): c is Elm => c instanceof Elm); }
}
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
const body = new Elm("body");
const doc = {
  body,
  activeElement: body as Elm,
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => s,
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
};
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = doc;

// the browser's part of a press: the span's mousedown listener, then the default action — focus the
// target if it is focusable, else the body (a span with no focusable ancestor, as in the chat)
function mousedown(a: Elm): void {
  a.onmousedown?.({ currentTarget: a, preventDefault: () => { throw new Error("mousedown.preventDefault() would also stop a selection from starting on the link"); } });
  if (a.focusable) { if (doc.activeElement !== a) { doc.activeElement = a; a.onfocus?.({ currentTarget: a }); } } else doc.activeElement = body;
}
const fire = (a: Elm, h: Handler) => h?.({ currentTarget: a });
function keydown(a: Elm, key: string): boolean {
  let prevented = false;
  a.onkeydown!({ key, currentTarget: a, preventDefault: () => { prevented = true; } });
  return prevented;
}
// render.ts's Enter gate, the part the finding is about: with a control focused the window handler yields
const enterReachesComposer = () => doc.activeElement === body;

test("a click leaves focus on the body, as a click on plain text does — Enter then reaches the composer, not the link", async () => {
  const { openPathLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  assert.equal(a.getAttribute("tabindex"), "0", "a tab stop to begin with");
  mousedown(a);
  assert.equal(a.hasAttribute("tabindex"), false, "not focusable while the button is down…");
  assert.equal(doc.activeElement, body, "…so the browser's default action focuses the body, not the link");
  fire(a, a.onmouseup);
  assert.equal(a.getAttribute("tabindex"), "0", "the tab stop is back on mouseup");
  assert.equal(doc.activeElement, body, "and focus stayed on the body");
  // the click's host handler opened the viewer; Escape closed it without moving focus; now Enter:
  assert.equal(enterReachesComposer(), true, "nothing focused → render.ts's Enter drops into the message box");
  assert.equal(a.clicks, 0, "the link's own Enter handler was never reached — the file does not re-open");
});

test("a keyboard focus meets no press and stays: Tab onto the link, Enter opens, Escape, Enter opens again", async () => {
  const { openPathLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  a.focus();
  assert.equal(doc.activeElement, a, "Tab reaches it");
  assert.equal(keydown(a, "Enter"), true); assert.equal(a.clicks, 1);
  assert.equal(doc.activeElement, a, "the viewer takes no focus; the link keeps it");
  assert.equal(keydown(a, "Enter"), true); assert.equal(a.clicks, 2, "an <a>'s behaviour: Enter re-activates a focused link");
  assert.equal(keydown(a, " "), true); assert.equal(a.clicks, 3);
  assert.equal(a.getAttribute("tabindex"), "0", "no press, no change to the tab stop");
  a.blur();
});

test("a link focused by Tab and then clicked ends unfocused: the press blurs it, the browser fires no focus for it", async () => {
  const { openPathLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  a.focus();
  assert.equal(doc.activeElement, a);
  mousedown(a);
  assert.equal(doc.activeElement, body, "the press ended the keyboard focus");
  fire(a, a.onmouseup);
  assert.equal(a.getAttribute("tabindex"), "0");
  assert.equal(enterReachesComposer(), true);
  assert.equal(a.clicks, 0);
});

test("a selection dragged from the link: the press goes on elsewhere, mouseleave restores the tab stop, focus is the body's", async () => {
  const { openPathLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  mousedown(a);
  assert.equal(doc.activeElement, body);
  fire(a, a.onmouseleave);                    // the pointer left the link, button still down; the mouseup lands elsewhere
  assert.equal(a.getAttribute("tabindex"), "0", "back in the tab order before the press even ends");
  assert.equal(doc.activeElement, body, "restoring the attribute focuses nothing");
  assert.equal(enterReachesComposer(), true, "Enter with the selection seeds the quote (render.ts), not the file");
  assert.equal(a.clicks, 0);
});

test("a menu or a native drag that takes the pointer restores the tab stop too, and a late mouseup is harmless", async () => {
  const { openPathLink } = await import("./path-links");
  for (const ending of ["oncontextmenu", "ondragstart"] as const) {
    const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
    mousedown(a);
    assert.equal(a.hasAttribute("tabindex"), false);
    fire(a, a[ending]);
    assert.equal(a.getAttribute("tabindex"), "0", ending + " puts the tab stop back — the mouseup may never reach the page");
    fire(a, a.onmouseup);                      // if it does arrive after all: still exactly one tab stop, still "0"
    assert.equal(a.getAttribute("tabindex"), "0");
    assert.equal(doc.activeElement, body);
  }
  // a release with nothing to restore does nothing — the four endings share one idempotent handler
  const b = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  fire(b, b.onmouseup); fire(b, b.onmouseleave);
  assert.equal(b.getAttribute("tabindex"), "0");
  assert.equal(b.onmouseup, b.onmouseleave); assert.equal(b.onmouseup, b.oncontextmenu); assert.equal(b.onmouseup, b.ondragstart);
});

test("every link the walk emits — a bare path's and a file:// URI's — carries the press handlers", async () => {
  const { linkifyPathTokens, fileUriLink } = await import("./path-links");
  const d = new Elm("div"); d.className = "assistant md";
  d.textContent = "read docs/design.md and file:///tmp/notes-api/out.png";
  linkifyPathTokens(d as unknown as HTMLElement, SID);
  const all = [...d.spans, fileUriLink("file:///tmp/notes-api/a.pdf") as unknown as Elm];
  assert.equal(all.length, 3);
  for (const s of all) {
    assert.equal(typeof s.onmousedown, "function"); assert.equal(typeof s.onmouseup, "function");
    mousedown(s);
    assert.equal(doc.activeElement, body, s.textContent + ": a click does not focus it");
    fire(s, s.onmouseup);
    assert.equal(s.getAttribute("tabindex"), "0", s.textContent + ": still a tab stop");
  }
});

test("source pins: the press drops the attribute (not tabIndex = -1, which a click still focuses) and prevents nothing", () => {
  const press = LINKS.match(/function pathLinkPress\(e: MouseEvent\): void \{[\s\S]*?\n\}/)?.[0] ?? "";
  assert.ok(press, "pathLinkPress exists");
  assert.match(press, /a\.removeAttribute\("tabindex"\);/, "a span without the attribute is not focusable; tabIndex = -1 still is, by the pointer");
  assert.doesNotMatch(press, /preventDefault/, "mousedown.preventDefault() would also keep a selection from starting on the link");
  assert.doesNotMatch(press, /tabIndex = -1/);
  assert.match(LINKS, /a\.onmousedown = pathLinkPress;/);
  assert.match(LINKS, /a\.onmouseup = a\.onmouseleave = a\.oncontextmenu = a\.ondragstart = pathLinkRelease;/);
  assert.doesNotMatch(LINKS, /a\.onfocus = /, "not a blur on the focus event: in Chromium that clears the selection the press made");
  assert.match(LINKS, /function pathLinkRelease\(e: Event\): void \{\n\s*const a = e\.currentTarget as HTMLElement;\n\s*if \(!a\.hasAttribute\("tabindex"\)\) a\.tabIndex = 0;/);
});
