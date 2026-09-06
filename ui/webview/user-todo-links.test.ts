// A user todo's note links to files the way a transcript does (the user 2026-09-02), on EVERY surface
// that shows the note (plans/file-review.md, Slice 0): the chat's todo card and its Reply modal, and the
// cross-session Waiting-on-you pane's row fold and Reply modal — which used to render the detail as
// plain text, because the pane is its own iframe and render.ts (the chat's entry) exports nothing. The
// matcher now lives in path-links.ts, which MARKS and binds nothing: each link is a .file-uri-link span
// carrying data-act="openpath", data-path, data-rel and data-sid; the hosting document decides the
// click. Relative paths resolve against the TODO'S OWN session (the one that flagged the need, whose
// working directory the note was written from), not whichever tab happens to be active.
//
// The matcher runs for real here over a small DOM stand-in (the github-link.test.ts idiom — there is no
// jsdom); the two hosts' wiring is pinned at source, and waiting.ts's posted payload is executed out of
// its function body (the files.test.ts idiom).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const RENDER = read("render.ts");
const WAITING = read("waiting.ts");
const LINKS = read("path-links.ts");
const FILES = read("files.ts");
const VIEW = read("file-view.ts");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

// synthetic world: the notes-api demo, a placeholder sid
const SID = "11111111-2222-3333-4444-555555555555";

// ── a DOM stand-in just big enough for the walk: elements with class/dataset/title, text nodes, a
// tree walker over text nodes in document order, closest() over tag names and one class, replaceWith
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
  constructor(public tagName: string) {}
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
  get texts(): string[] { return this.childNodes.filter((c): c is TextNode => c instanceof TextNode).map((c) => c.data); }
}
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = {
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => s,
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
};

test("path-links.ts marks and binds nothing: the span carries the act, the target, the relativity and the session", async () => {
  const pl = await import("./path-links");
  assert.equal(pl.PATH_LINK_ACT, "openpath");
  assert.doesNotMatch(LINKS, /addEventListener|onclick|postMessage|openPath\(|openFileView/, "no click, no route — the host decides");
  const rel = pl.openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  assert.equal(rel.className, "file-uri-link");
  assert.equal(rel.textContent, "docs/design.md", "shown as written");
  assert.equal(rel.title, "Open docs/design.md");
  assert.deepEqual(rel.dataset, { act: "openpath", path: "docs/design.md", rel: "1", sid: SID });
  // a file:// URI names an absolute path: no relativity, and the session only when the caller named one
  const uri = pl.fileUriLink("file:///tmp/notes-api/out%20dir/a.png") as unknown as Elm;
  assert.equal(uri.textContent, "file:///tmp/notes-api/out%20dir/a.png");
  assert.deepEqual(uri.dataset, { act: "openpath", path: "/tmp/notes-api/out dir/a.png" });
  // a shortened mention the kernel FIXED opens the fixed target and says so on hover
  const fixed = pl.openPathLink("deep.py", "kernel/sub/deep.py", true) as unknown as Elm;
  assert.deepEqual(fixed.dataset, { act: "openpath", path: "kernel/sub/deep.py", rel: "1" });
  assert.equal(fixed.title, "Open kernel/sub/deep.py");
});

test("the walk, executed over a todo's note: paths become marked spans with the todo's sid, prose stays prose", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = new Elm("div"); d.className = "ut-detail";
  d.textContent = "Please read docs/design.md and/or /tmp/notes-api/out.png (see file:///tmp/notes-api/notes.md).";
  const hits = linkifyPathTokens(d as unknown as HTMLElement, SID);
  assert.deepEqual(hits.map((h) => h.open), ["docs/design.md", "/tmp/notes-api/out.png", "/tmp/notes-api/notes.md"]);
  assert.deepEqual(hits.map((h) => h.verified), [false, false, false], "no kernel verdict on a note — shape-only");
  const spans = d.spans;
  assert.equal(spans.length, 3);
  assert.deepEqual(spans.map((s) => s.dataset.act), ["openpath", "openpath", "openpath"]);
  assert.deepEqual(spans.map((s) => s.dataset.sid), [SID, SID, undefined], "a bare path carries the todo's session; a URI is absolute");
  assert.deepEqual(spans.map((s) => s.dataset.rel), ["1", "1", undefined]);
  // "and/or" stayed prose; the sentence's closing ")." stayed outside the last link
  assert.deepEqual(d.texts, ["Please read ", " and/or ", " (see ", ")."]);
  assert.equal(d.textContent, "Please read docs/design.md and/or /tmp/notes-api/out.png (see file:///tmp/notes-api/notes.md).", "the text reads exactly as written");
  // a note with no path is left alone entirely — no fragment splice, no spans
  const plain = new Elm("div"); plain.textContent = "Pick one of the two designs and/or say why.";
  assert.deepEqual(linkifyPathTokens(plain as unknown as HTMLElement, SID), []);
  assert.deepEqual(plain.texts, ["Pick one of the two designs and/or say why."]);
});

test("the kernel's pathLinks verdict narrows the walk and fixes the target; file:// is never gated", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = new Elm("p");
  d.textContent = "see render.js and sub/deep.py, or file:///tmp/notes-api/x.md";
  const hits = linkifyPathTokens(d as unknown as HTMLElement, null, { "sub/deep.py": "kernel/sub/deep.py" });
  assert.deepEqual(hits.map((h) => [h.open, h.verified]), [["kernel/sub/deep.py", true], ["/tmp/notes-api/x.md", false]]);
  assert.deepEqual(d.texts, ["see render.js and ", ", or "], "render.js (no verdict) stays prose");
  assert.equal(d.spans[0].textContent, "sub/deep.py", "shown as written…");
  assert.equal(d.spans[0].dataset.path, "kernel/sub/deep.py", "…opens the kernel's fixed target");
  assert.equal(d.spans[0].dataset.sid, undefined, "no session named → none on the span (the host falls to its active one)");
});

test("the shape gates run for real: the exported matchers, not replicas", async () => {
  const { looksLikeFilePath, looksLikeBareFileName, fileUriToPath, CLICKABLE_PATH_RE, TRAILING_PUNCT_RE } = await import("./path-links");
  for (const p of ["design/plan.md", "ui/webview/render.ts", "/Users/x/a.md", "~/notes.md", "./foo.txt", "../a/b.py"]) assert.equal(looksLikeFilePath(p), true, p);
  for (const p of ["and/or", "TCP/IP", "24/7", "read/write", "https://example.com/page.html", "bin/romp-kernel"]) assert.equal(looksLikeFilePath(p), false, p);
  for (const p of ["power2_watts.pdf", "kernel.py", "notes.md"]) assert.equal(looksLikeBareFileName(p), true, p);
  for (const p of ["np.array", "romp.kernelPort", "0.4.293", ".gitignore", "analysis/foo.py"]) assert.equal(looksLikeBareFileName(p), false, p);
  assert.equal(fileUriToPath("file:///a/b%20c.md"), "/a/b c.md");
  assert.deepEqual("see design/plan.md for details".match(CLICKABLE_PATH_RE), ["design/plan.md"]);
  assert.equal("a/b.md.".replace(TRAILING_PUNCT_RE, ""), "a/b.md");
});

test("render.ts imports the matcher and binds the click itself — the chat's routing is unchanged", () => {
  assert.match(RENDER, /import \{ openPathLink, linkifyPathTokens \} from "\.\/path-links";/);
  for (const gone of ["const CLICKABLE_PATH_RE", "function looksLikeFilePath(", "function looksLikeBareFileName(", "function fileUriToPath(", "function openPathLink("]) {
    assert.ok(!RENDER.includes(gone), gone + " lives in path-links.ts now, once");
  }
  // one binder: data-rel → the named session first (a todo's note), the active tab otherwise; a URI sends none
  assert.match(RENDER, /function bindPathLink\(a: HTMLElement\): HTMLElement \{\n\s*const open = a\.dataset\.path \|\| "", relative = a\.dataset\.rel === "1", sid = a\.dataset\.sid \?\? null;/);
  assert.match(RENDER, /openPath\(open, relative \? \(sid \?\? activeId\) : null\);/);
  // every span the walk and the spaced pass emit is bound; the hits feed the figure pass as before
  assert.match(RENDER, /for \(const \{ el: link, open, verified \} of linkifyPathTokens\(root, sid, pathLinks\)\) \{\n\s*bindPathLink\(link\);/);
  assert.match(RENDER, /const link = bindPathLink\(openPathLink\(tok, tok, true, sid\)\);\n\s*code\.replaceChildren\(link\);/);
});

test("the chat's todo card and its Reply modal still link the note against the todo's session", () => {
  const card = RENDER.slice(RENDER.indexOf('const d = el("div", "ut-detail" + (utDetailOpen.has(t.id)'), RENDER.indexOf("row.appendChild(d);"));
  assert.match(card, /d\.textContent = t\.detail \|\| "";/);                           // the note stays plain text…
  assert.match(card, /linkifyFileUris\(d, undefined, undefined, undefined, undefined, renderingSid \|\| null\);/);   // …with paths linked after
  assert.match(RENDER, /reply\.dataset\.sid = renderingSid \|\| "";/);               // the buttons act where the paths resolve
  const modal = RENDER.slice(RENDER.indexOf("function showUserTodoReply(sid: string, todoId: string, todoText: string, todoDetail = \"\")"),
                             RENDER.indexOf("input.className = \"ut-reply-input\""));
  assert.match(modal, /dd\.textContent = todoDetail; linkifyFileUris\(dd, undefined, undefined, undefined, undefined, sid\);/);
  // the one-line text is the fold's click target, never linkified (click safety, ui/CLAUDE.md)
  const row = RENDER.slice(RENDER.indexOf('const txt = el("span", "ut-text");'), RENDER.indexOf('const reply = el("button", "ut-btn ut-reply");'));
  assert.match(row, /txt\.textContent = t\.text;/);
  assert.doesNotMatch(row, /linkifyFileUris\(/);
});

test("waiting.ts links the detail at BOTH sites — the row fold and the Reply modal — with the todo's sid, only when framed", () => {
  assert.match(WAITING, /import \{ linkifyPathTokens \} from "\.\/path-links";/);
  // the gate: a pane the shell does not frame has no Files pane to send a click to → plain text
  assert.match(WAITING, /const framed = window\.parent !== window;\nfunction linkDetailPaths\(node: HTMLElement, sid: string\): void \{\n\s*if \(!framed\) return;\n\s*linkifyPathTokens\(node, sid\);\n\}/);
  // the row: text first, then the links, on the fold body (never on the one-line .ut-text, the fold's click target)
  const row = WAITING.slice(WAITING.indexOf("function rowEl("), WAITING.indexOf("function hostLine("));
  assert.match(row, /d\.textContent = w\.todo\.detail \|\| "";\n\s*linkDetailPaths\(d, w\.sid\);/);
  const txt = row.slice(row.indexOf('const txt = el("span", "ut-text");'), row.indexOf('const age = el("span", "wt-age");'));
  assert.doesNotMatch(txt, /linkDetailPaths|linkifyPathTokens/);
  // the modal: the same call on the quoted detail, and its own delegate (the overlay lives outside #waiting-list)
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  assert.match(modal, /dd\.textContent = todoDetail;\n\s*linkDetailPaths\(dd, sid\);/);
  assert.match(modal, /delegate\(dd, \{ openpath: \(x\) => \{ const p = x\.dataset\.path; if \(p\) openTodoPath\(p, sid, todoId\); \} \}\);/);
  assert.equal((WAITING.match(/linkDetailPaths\(/g) || []).length, 3, "defined once, applied at the two sites");
});

test("the list's delegate routes openpath from the ROW's sid and todo id, never the span's — click-safe across the per-frame rebuild", () => {
  const map = WAITING.slice(WAITING.indexOf("delegate(list, {"), WAITING.indexOf("// A tap anywhere that is NOT an armed Dismiss"));
  // both ids come from the enclosing .ut-item: path-links.ts stamps data-sid on a bare path's span and NOT
  // on a file:// URI's (an absolute path names no session), so a handler gated on the span's sid dropped
  // every URI click (the 2026-09-06 review; waiting-detail-link.test.ts clicks all three shapes for real)
  assert.match(map, /\n    openpath: \(x\) => \{\n\s*const row = x\.closest<HTMLElement>\("\.ut-item"\);\n\s*const p = x\.dataset\.path, sid = row\?\.dataset\.sid, tid = row\?\.dataset\.tid;\n\s*if \(p && sid && tid\) openTodoPath\(p, sid, tid\);\n\s*\},/);
  const handler = map.slice(map.indexOf("\n    openpath: (x) => {"), map.indexOf("\n    },", map.indexOf("\n    openpath: (x) => {")));
  assert.doesNotMatch(handler, /x\.dataset\.sid/, "the span's own sid is not the gate — a URI span has none");
  // the row carries both ids the handler reads
  assert.match(WAITING, /item\.dataset\.sid = w\.sid; item\.dataset\.tid = w\.todo\.id;/);
  // no per-node click binding anywhere near the links
  const row = WAITING.slice(WAITING.indexOf("function rowEl("), WAITING.indexOf("function hostLine("));
  assert.doesNotMatch(row, /addEventListener/);
});

test("the posted payload, executed: viewFile to the Files pane with the todo's session, its chip identity and the todo id", () => {
  const body = WAITING.split("function openTodoPath(path: string, sid: string, todoId: string): void {")[1].split("\n}")[0];
  const fn = new Function("rows", "window", "path", "sid", "todoId", body) as
    (rows: unknown[], w: unknown, path: string, sid: string, todoId: string) => void;
  const posted: [unknown, string][] = [];
  const win = { parent: { postMessage: (m: unknown, origin: string) => posted.push([m, origin]) } };
  const rows = [{ sid: SID, name: "api", color: { bg: "#123456", fg: "#ffffff" }, todos: [] },
                { sid: "11111111-2222-3333-4444-666666666666", name: "", color: null, todos: [] }];
  fn(rows, win, "docs/design.md", SID, "t1");
  assert.deepEqual(posted, [[{ romp: "viewFile", pane: "pane", path: "docs/design.md", sid: SID,
                              identity: { name: "api", color: { bg: "#123456", fg: "#ffffff" } }, todoId: "t1" }, "*"]]);
  // a row with no name sends null (looked up, never invented — the viewer falls to the kernel's stub)
  fn(rows, win, "/tmp/notes-api/a.md", "11111111-2222-3333-4444-666666666666", "t2");
  assert.equal((posted[1][0] as any).identity, null);
  assert.equal((posted[1][0] as any).todoId, "t2");
});

test("the shell forwards todoId into the Files pane; files.ts hands it to the viewer; the viewer's action ctx carries it", () => {
  // the landing shell's pane branch (kernel.py) — the feed route forwards path + sid only, as before
  assert.ok(KERNEL.includes("postMessage({romp:'viewFile',path:m.path,sid:m.sid,identity:m.identity||null,todoId:m.todoId||null},'*')"), "pane branch forwards todoId");
  assert.ok(KERNEL.includes("postMessage({romp:'viewFile',path:m.path,sid:m.sid},'*')"), "feed route unchanged");
  assert.match(FILES, /openHere\(m\.path, typeof m\.sid === "string" \? m\.sid : null, asIdentity\(m\.identity\), typeof m\.todoId === "string" \? m\.todoId : null\);/);
  assert.match(FILES, /function openHere\(path: string, sid: string \| null, identity: FileViewIdentity \| null, todoId: string \| null = null\): void \{/);
  assert.match(FILES, /if \(!openFileView\(path, sid, \{ todoId \}\)\) return;/);
  assert.doesNotMatch(FILES, /rememberRecent\([^)]*todoId/, "the recent list does not remember the user todo — a re-open is no longer that todo");
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null \}\): boolean \{/);
  assert.match(VIEW, /export interface FileViewActionCtx \{ path: string; sid: string \| null; todoId\?: string \| null; \}/);
  assert.match(VIEW, /const n = a\.mount\(\{ path, sid: sid \|\| null, todoId: opts\?\.todoId \?\? null \}\);/);
  assert.match(VIEW, /openFileView\(path, sid, opts\);/, "the conflict Reload keeps the provenance");
  assert.match(VIEW, /onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown; todoId\?: unknown \}\) => void\): void \{/);
});

test("a relative path resolves against the todo's session ON THE KERNEL: the sid rides the viewer's /file fetch", () => {
  // waiting.ts posts the todo's sid → files.ts opens with it → fileUrl carries it → /file resolves through
  // _resolve_open_path (~ expanded, relative → that session's cwd). No client-side guessing anywhere.
  const PREVIEW = read("preview.ts");
  assert.match(PREVIEW, /export function fileUrl\(path: string, sid\?: string \| null\): string \{[\s\S]*?"&sid=" \+ encodeURIComponent\(bare\)/);
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)/);
  assert.ok(KERNEL.includes('fp = _resolve_open_path((q.get("path") or [""])[0], (q.get("sid") or [None])[0])'), "/file resolves against the sid's cwd");
  assert.ok(KERNEL.includes("def _resolve_open_path(p, sid=None):"));
});
