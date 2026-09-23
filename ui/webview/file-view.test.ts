// The file viewer — a modal over the CHAT pane (the user 2026-08-15; the first cut filled the FEED
// pane, and reading a file cost the cards). Clicking a file path in the chat used to post `openFile`,
// which the kernel served by running an opener on ITS OWN machine — the wrong screen when the
// dashboard is read from another device, and nothing at all on a kernel with no desktop, because the
// opener was macOS-only (the user 2026-08-08). The bytes have to reach the browser, so the click routes
// to a viewer fed by the same /file route the image previews use — now in the SAME document as the
// click, so the chat needs no shell relay. The FEED still hosts the viewer too: the file BROWSER
// (file-browse.ts) opens files through the same module in its own document, which is why the feed
// sheet mirrors the viewer CSS instead of dropping it. Source pins (no jsdom for these modules) +
// executed replicas of the pure helpers.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const FEED = web("feed.ts");
const FEED_CSS = web("feed.css");
const CHAT_CSS = web("styles.css");

test("openPath routes by HOST: the in-pane viewer modal on the web (or the Files pane, by the ladder), the editor in VS Code", () => {
  assert.match(RENDER, /function openPath\(path: string, sid\?: string \| null, ev\?: MouseEvent \| null, at: At \| null = null\): void/);   // ev: the click, for a PDF's modified-click tab; at: the target a todo link named (Slice 6 of plans/markdown-viewer.md, item 4; a `#slug` is its heading arm, so upstream's separate frag does not ride here)
  // web → the ladder decides at the click (file-route.ts fileLinkRoute, its table in file-route.test.ts): "here" opens
  // the viewer in THIS document through the gesture reader; "pane" hands a plain click to the shell for the Files pane
  assert.match(RENDER, /const route = fileLinkRoute\(window\.parent !== window, panesOn\.files === true, panesAvail\.files !== false\);/,
    "…and whether the Files control exists at all (its gear setting, T317): hidden, the pane road falls back to here");
  assert.match(RENDER, /openFileClick\(ev, path, to, route === "pane" \? \(\) => \{/);   // via the gesture reader: a plain click is openFileView or the relay (pdf-new-tab.test.ts)
  assert.match(RENDER, /import \{ openFileClick, type At \} from "\.\/file-view";/);   // the gesture reader is the chat's only way in; openFileView is not imported
  assert.match(RENDER, /window\.parent\.postMessage\(\{ romp: "viewFile", path, sid: to, pane: "pane", at,\n\s*identity: s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : null \}, "\*"\);/);   // the relay carries the target too (Slice 6, item 4), where upstream's carries frag
  assert.equal((RENDER.match(/romp: "viewFile"/g) || []).length, 1, "one relay, aimed at the Files pane; the feed is never a file's target");
  assert.doesNotMatch(RENDER, /pane: "feed"/);
  // VS Code keeps the host editor, whose arm reads a line target; a heading or an offset posts nothing extra
  assert.match(RENDER, /const m: Record<string, unknown> = sid \? \{ type: "openFile", path, id: sid \} : \{ type: "openFile", path \};\n\s*if \(at && "line" in at\) m\.line = at\.line;\n\s*vscodeApi\.postMessage\(m\);/);
});

// The Files-pane bit openPath routes by is the SHELL's pane set, cached from the shell's own broadcast —
// {romp:"panes", on:{key:bool}} on every toggle (the shell's apply()) and on this iframe's load (kernel.py
// _LANDING_COLLAPSE_JS; pinned in tests/test_pane_state_broadcast.py) — never a per-click read of the
// parent's DOM or a poll. Whole-set replace, so a key the shell stops naming cannot linger as on. The same
// message carries a second set since T317, avail:{key:bool}, which panes EXIST to bring forward (the Files
// control's gear row): read the other way round, only an explicit false hides, absent is available.
test("the chat caches the shell's pane set (and which panes exist) from its romp:panes broadcast, and openPath reads the Files bits from it", () => {
  assert.match(RENDER, /let panesOn: Record<string, boolean> = \{\};/);
  assert.match(RENDER, /let panesAvail: Record<string, boolean> = \{\};/, "…and the second set, which panes EXIST to bring forward (T317)");
  assert.match(RENDER, /if \(m\.romp === "panes"\) \{\n\s*if \(m\.on && typeof m\.on === "object"\) \{\n\s*const on: Record<string, boolean> = \{\};\n\s*for \(const k of Object\.keys\(m\.on\)\) on\[k\] = m\.on\[k\] === true;\n\s*panesOn = on;\n\s*\}\n(?:\s*\/\/[^\n]*\n)*\s*const avail: Record<string, boolean> = \{\};\n\s*if \(m\.avail && typeof m\.avail === "object"\) for \(const k of Object\.keys\(m\.avail\)\) avail\[k\] = m\.avail\[k\] !== false;\n\s*panesAvail = avail;\n\s*return;\n\s*\}/);
  assert.match(RENDER, /fileLinkRoute\(window\.parent !== window, panesOn\.files === true, panesAvail\.files !== false\)/);
  assert.equal((RENDER.match(/panesOn\.files/g) || []).length, 2,
    "two readers: openPath's route decision, and browseRouteNow for a folder click (2026-09-06)");
  assert.equal((RENDER.match(/panesAvail\.files/g) || []).length, 2, "the same two read the control's existence (T317)");
  // executed: the listener's fold, as the source spells it — strict booleans in, unknown keys dropped on the next set
  const fold = (on: Record<string, unknown>): Record<string, boolean> => {
    const out: Record<string, boolean> = {};
    for (const k of Object.keys(on)) out[k] = on[k] === true;
    return out;
  };
  assert.deepEqual(fold({ chat: true, feed: false, files: true }), { chat: true, feed: false, files: true });
  assert.deepEqual(fold({ files: "yes" }), { files: false }, "only a real true counts as on");
  assert.equal(fold({ chat: true }).files, undefined, "a set that stops naming a pane leaves it off (=== true fails)");
  // ...and the avail fold beside it, as the source spells it: only an explicit false hides a control
  const foldAvail = (avail: Record<string, unknown>): Record<string, boolean> => {
    const out: Record<string, boolean> = {};
    for (const k of Object.keys(avail)) out[k] = avail[k] !== false;
    return out;
  };
  assert.deepEqual(foldAvail({ files: false }), { files: false }, "only an explicit false hides a control");
  assert.deepEqual(foldAvail({ files: "yes" }), { files: true }, "anything else reads as available");
  assert.equal(foldAvail({}).files !== false, true, "a control the shell does not name is available (openPath reads !== false)");
});

test("every file-link surface in the chat goes through openPath — no direct openFile posts left", () => {
  for (const call of [/openPath\(path, null, e\);/, /openPath\(open, relative \? \(sid \?\? activeId\) : null, e, linkTarget\(a\)\);/,
                      /openPath\(p, id \|\| null, e\);/]) assert.match(RENDER, call);   // each with its click (a PDF's modified-click tab)
  // the ONLY openFile postMessage left in render.ts is openPath's own fallback branch
  assert.equal((RENDER.match(/type: "openFile"/g) || []).length, 2,
               "both remaining mentions are the two arms of openPath's fallback");
});

test("the VIEWER's shell relay serves the Files pane only; the BROWSER's stays, and the feed pane is only juggled for it", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  // the viewer lives in the clicking document (the user 2026-08-15: a file view must never touch the feed), so
  // the shell forwards a viewFile click to ONE place, the Files pane, and only when the click names it; the
  // pane stays up, so the viewer has nothing to restore and nothing to announce. The arm itself is the kernel's
  // and is pinned and run in the Python lane (tests/test_files_pane.py Relay, tests/test_pane_state_broadcast.py)
  assert.doesNotMatch(KERNEL, /postMessage\(\{romp:'viewFile',path:m\.path,sid:m\.sid\},'\*'\)/, "no forward into the feed");
  assert.doesNotMatch(VIEW, /viewFileClosed/, "nothing to restore → nothing to announce");
  // the file BROWSER still lives in the FEED pane, so its ask still relays through the shell from
  // any pane, still turns a toggled-off feed on, and still restores it on browseClosed — that
  // machinery is the browser's, not the viewer's
  assert.match(KERNEL, /if\(m\.romp==='browseFiles'\)\{var bf=document\.getElementById\('f-feed'\);/);
  assert.match(KERNEL, /window\.__rompFeedWasOff=true;/);
  assert.match(KERNEL, /m\.romp==='browseClosed'/);
  assert.match(KERNEL, /window\.__rompMobileTab&&window\.__rompMobileTab\('feed'\)/, "phone: one pane at a time");
});

test("the viewer is a singleton MODAL over its pane: ~95% card, dimmed backdrop, ✕/Esc/backdrop close", () => {
  assert.match(VIEW, /document\.getElementById\("romp-fileview"\)\?\.remove\(\);/, "re-opening replaces, never stacks");
  // the backdrop closes on ITS OWN clicks only — content clicks don't (the lightbox contract)
  assert.match(VIEW, /wrap\.onclick = \(ev\) => \{ if \(ev\.target === wrap\) closeFileView\(\); \};/);
  assert.match(VIEW, /close\.addEventListener\("click", closeFileView\);/);
  assert.match(VIEW, /if \(e\.key !== "Escape" \|\| !document\.getElementById\("romp-fileview"\)\) return;/);
  // the panels treatment on the CHAT sheet: dimmed rgba(0,0,0,0.55) backdrop, the content behind visible
  assert.match(CHAT_CSS, /#romp-fileview \{ position: fixed; inset: 0; z-index: 1200; background: var\(--overlay-dim\);/);
  assert.match(CHAT_CSS, /\.fileview \{ width: 95%; height: 95%;/);
  // …and mirrored on the FEED sheet, which still hosts the viewer when the file BROWSER opens a file
  // (one treatment, two sheets — the hljs-palette precedent below)
  assert.match(FEED_CSS, /#romp-fileview \{ position: fixed; inset: 0;/);
  assert.match(FEED_CSS, /\.fileview \{ width: 95%; height: 95%;/);
  assert.match(FEED, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/,
    "the feed boots the listener with the WS poster (saves ride it — the raw-mode slice)");
});

// ── selection → quote chip (the user 2026-08-23, the three-verbs consolidation): the viewer's
// separate review layer (per-file comment store, marks, one-shot Submit — romp:fileviewComments +
// buildReviewMessage) is GONE. Selecting a passage now seeds the chat composer's own labeled quote
// chip, exactly like a VS Code editor highlight, and batching rides the chip + ⌘⏎ staging flow the
// chat already has. "Comment" means only the transcript's live threads now. ──

test("selecting in the viewer seeds the composer's editor chip — the editorSelection shape, path:line label", () => {
  // mouseup posts to the composer's window — this document's when it holds one (the browseFiles
  // precedent — no import cycle with render.ts), else the shell's chat pane (composerWindow, below) —
  // and render.ts's existing editorSelection handler owns the chip end to end
  // one handler for the mouse's settle point and the phone's (touchend), since Slice 1 of
  // plans/file-review.md — the comments panel's floating Comment button rides the same gesture
  // the handler reads the event's target since the text-size change (review 2026-09-07): a press on a title-bar button
  // with a passage still selected in the body settles no selection (file-view-text-size.test.ts pins the gate)
  assert.match(VIEW, /const onSelect = \(ev: Event\) => \{/);
  assert.match(VIEW, /box\.addEventListener\("mouseup", onSelect\);\n\s*box\.addEventListener\("touchend", onSelect\);/);
  assert.match(VIEW, /seedTarget\.postMessage\(\{ type: "editorSelection", text: picked, sid: sid \|\| undefined, src: quoteSrcLabel\(path, doc, picked\) \}, "\*"\);/);
  // a collapsed or out-of-viewer selection seeds nothing, and CodeMirror selections are edits
  assert.match(VIEW, /if \(!sel \|\| sel\.isCollapsed \|\| !sel\.anchorNode \|\| !box\.contains\(sel\.anchorNode\)\) return;/);
  assert.match(VIEW, /if \(editing\) return;/);
});

test("the chip lands in the session the file was opened FOR — the posted sid beats activeId-at-gesture", () => {
  // the modal stays up across a tab switch (nothing closes it on focus), so seeding into activeId
  // would put session A's path:line quote into session B's composer — the 2026-08-19 routing rule
  // the retired review layer already learned once. Host (VS Code) posts carry no sid → activeId.
  assert.match(RENDER, /const to = typeof m\.sid === "string" && m\.sid \? m\.sid : activeId;/);
  assert.match(RENDER, /if \(to\) seedEditorQuote\(to, m\.text, typeof m\.src === "string" \? m\.src : undefined\);/);
});

test("the label's line is minted against a FRESH read, and a failed re-read falls back to the snapshot", () => {
  // agents edit these same trees while you read: the open-time snapshot's numbering may have moved,
  // so the line is anchored at selection time — and a failed re-read must not fabricate drift
  // nobody observed (the retired Submit guard's rule), so it anchors the snapshot instead. The
  // snapshot is viewText, not text: the SVG Source view's snapshot is the decoded blob and `text`
  // stays null in media mode, so falling back to it would strip every SVG quote's line label.
  assert.match(VIEW, /const seq = \+\+seedSeq;/);
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)\n\s*\.then\(\(r\) => \(r\.ok \? r\.text\(\) : Promise\.reject\(new Error\(String\(r\.status\)\)\)\)\)\n\s*\.catch\(\(\) => viewText\(\)\)/);
  assert.match(VIEW, /const viewText = \(\): string \| null => \(svgSource && svgText !== null \? svgText : text\);/);
  assert.match(VIEW, /if \(seq !== seedSeq\) return;/, "two racing reads: the last gesture wins");
});

test("a viewer whose document has no composer seeds THROUGH the shell: the Files pane and the feed reach the chat's chip", () => {
  // Until 2026-09-03 the seed gated on a composer in the SAME document, so the feed-hosted viewer (the
  // file browser's document) was dead air by design: the guide's promise that any passage selected in
  // the viewer lands in the composer was false there, and each selection still paid the fresh read. The
  // Files pane hosts the viewer without a composer too, and a pane that cannot quote is a step down from
  // the chat modal — so the TARGET is resolved: this window when it holds the composer, else the
  // same-origin shell, which forwards the unchanged message into the chat pane. No composer and no shell
  // (VS Code's cross-origin parent, a standalone pane) still stands the gesture down before the fresh
  // read (the no-sink gating).
  assert.match(VIEW, /function composerWindow\(\): Window \| null \{\n\s*if \(document\.getElementById\("composer-input"\)\) return window;\n\s*try \{ if \(window\.parent !== window && window\.parent\.document\.getElementById\("chat-pane"\)\) return window\.parent; \}\n\s*catch \{[^}]*\}\n\s*return null;\n\}/);
  assert.match(VIEW, /const seedTarget = composerWindow\(\);\n\s*if \(!seedTarget\) return;/);
  // the shell's arm: the SAME message, forwarded whole into the chat frame — sid intact, so the chip
  // lands in the session the file was opened for (the 2026-08-19 routing rule holds across documents)
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /if\(m\.type==='editorSelection'&&typeof m\.text==='string'\)\{var fc=document\.getElementById\('f-chat'\);[\s\S]{0,700}?try\{fc&&fc\.contentWindow&&fc\.contentWindow\.postMessage\(m,'\*'\);\}catch\(e\)\{\}\}/);
  // …and a chat pane toggled OFF is brought forward first, the browseFiles arm's rule for the feed: a chip
  // seeded into a hidden composer is a silent gesture (review fold on #970, 2026-09-07)
  assert.match(KERNEL, /if\(!document\.body\.classList\.contains\('po-chat'\)\)\{try\{window\.__rompPaneToggle&&window\.__rompPaneToggle\('chat',true\);\}catch\(e\)\{\}\}\n\s*try\{fc&&fc\.contentWindow&&fc\.contentWindow\.postMessage\(m,'\*'\);/);
  // …and the chat's existing window-message handler is the receiver: nothing new listens in feed.ts
  assert.match(RENDER, /else if \(m\.type === "editorSelection" && typeof m\.text === "string" && m\.text\.trim\(\)\) \{/);
  assert.doesNotMatch(FEED, /editorSelection/);
  // the review layer is gone from every module and both sheets, and the orphaned store is swept
  for (const source of [VIEW, RENDER, FEED, CHAT_CSS, FEED_CSS]) {
    assert.doesNotMatch(source, /setCommentSink|buildReviewMessage|fv-hl|fileview-submit/);
  }
  assert.match(VIEW, /localStorage\.removeItem\("romp:fileviewComments"\)/);
});

// executed: composerWindow's ladder, lifted from the source (a hand copy would drift), run against
// shimmed window/document pairs for each hosting situation. The window stand-ins fake no DOM, but a window's parent is an
// edge to another stand-in (itself when unframed, the shell when framed), so hideEdges (ui/test-dom-shim.ts) hides it: a
// failing assert.equal over a window dumps the window's own primitives, never the chain
const unframedWindow = (): any => { const w: any = {}; w.parent = w; return hideEdges(w); };
const framedWindow = (parent: object): any => hideEdges({ parent });
test("composerWindow, executed: own composer → the same-origin shell's chat pane → nothing", () => {
  const m = VIEW.match(/function composerWindow\(\): Window \| null \{[\s\S]*?\n\}/);
  assert.ok(m, "composerWindow found");
  const body = m![0].replace(/^function composerWindow\(\): Window \| null /, "");
  const run = new Function("window", "document", "return (function()" + body + ")();") as (w: unknown, d: unknown) => unknown;
  const doc = (ids: string[]) => ({ getElementById: (id: string) => (ids.includes(id) ? {} : null) });
  const self = unframedWindow();
  assert.equal(run(self, doc(["composer-input"])), self, "the chat document: its own window");
  const shell = { document: doc(["chat-pane"]) };
  const framed = framedWindow(shell);
  assert.equal(run(framed, doc([])), shell, "a pane inside the shell: the shell, which forwards into the chat");
  assert.equal(run(framed, doc(["composer-input"])), framed, "a composer at hand always wins over the relay");
  assert.equal(run(framedWindow({ get document() { throw new Error("cross-origin"); } }), doc([])), null,
    "VS Code's cross-origin parent is not the shell — the gesture stands down");
  assert.equal(run(framedWindow({ document: doc([]) }), doc([])), null, "a same-origin parent that is not the shell");
  assert.equal(run(self, doc([])), null, "unframed and composer-less: nowhere to seed");
});

// executed: the body's width observer (watchBodyWidth), lifted from the source with its type annotations stripped (the
// composerWindow lift above; a hand copy would drift), run over a fake ResizeObserver and stand-in nodes whose edges hide
// through the shared shim's hideEdges (the ratchet in ui/test-dom-shim.test.ts: a fake's enumerable children edge is the
// shape a failing assertion's dump walks). Both sheets'
// `.fileview-md > table` read --fv-body-w for a top-level table's cap and its shift into the gutters; what the function
// promises them is run here: nothing before the first report, the body's content width on EACH TOP-LEVEL TABLE (never a
// nested one, never the prose) after one, the same width on the fresh tables a paint brings (the returned stamp: mdBlock
// rebuilds the root and no report follows a paint), a repeated width no write, one watch at a time, and no watch at all
// without ResizeObserver.
test("watchBodyWidth, executed: --fv-body-w lands on each top-level table after a report and, through the stamp, on a fresh root's tables; a nested table and the prose get nothing; a repeated width writes nothing; the next watch and the drop disconnect; no ResizeObserver, no writes", () => {
  const head = "function watchBodyWidth(body: HTMLElement, onWidth?: (width: number) => void): () => void {";   // the seam's reflow hangs on onWidth (undefined here: the stamp alone runs)
  const at = VIEW.indexOf("let dropWidthWatch: () => void = ");
  const end = VIEW.indexOf("\n}\n", VIEW.indexOf(head, at)) + 3;
  assert.ok(at >= 0 && VIEW.indexOf(head, at) > at && end > at, "watchBodyWidth and its module-level drop found, the drop first");
  const js = VIEW.slice(at, end)
    .replace(/: \(\) => void/g, "")                                    // the let's type and the function's return type
    .replace("(body: HTMLElement, onWidth?: (width: number) => void)", "(body, onWidth)")
    .replace("const stamp = (): void =>", "const stamp = () =>")
    .replace(/ as HTMLElement\)/g, ")");
  assert.doesNotMatch(js, /HTMLElement|: void/, "every annotation the lift knows is gone (a new one needs its strip here)");
  type Node = { tagName: string; className: string; children: Node[]; clientWidth: number; writes: number; style: { setProperty(k: string, v: string): void; getPropertyValue(k: string): string }; querySelector(sel: string): Node | null };
  const node = (tagName: string, className = "", children: Node[] = []): Node => {
    const props = new Map<string, string>();
    const n: Node = { tagName, className, children, clientWidth: 0, writes: 0,
      style: { setProperty: (k, v) => { props.set(k, v); n.writes++; }, getPropertyValue: (k) => props.get(k) ?? "" },
      querySelector: (sel) => { const walk = (m: Node): Node | null => { for (const c of m.children) { if (c.className === sel.slice(1)) return c; const d = walk(c); if (d) return d; } return null; }; return walk(n); } };
    return hideEdges(n);   // the shared rule (ui/test-dom-shim.ts): children, style and querySelector hide, so a failing dump names the node's primitives alone
  };
  type Rec = { cb: (entries: Array<{ contentRect: { width: number } }>) => void; targets: unknown[]; live: boolean };
  const observers: Rec[] = [];
  class FakeResizeObserver {
    private rec: Rec;
    constructor(cb: Rec["cb"]) { this.rec = { cb, targets: [], live: true }; observers.push(this.rec); }
    observe(t: unknown): void { this.rec.targets.push(t); }
    disconnect(): void { this.rec.live = false; }
  }
  const report = (entries: Array<{ contentRect: { width: number } }>) => { const live = observers.filter((o) => o.live); assert.equal(live.length, 1, "one live observer"); live[0].cb(entries); };
  const run = new Function("ResizeObserver", js + "\nreturn { watchBodyWidth, drop: () => dropWidthWatch() };") as (ro: unknown) => { watchBodyWidth: (body: Node) => () => void; drop: () => void };
  /** A rendered root as mdBlock leaves it: prose, a table inside a paragraph (as inside a quote or a list item), two top-level tables. */
  const fresh = () => { const nested = node("TABLE"); const p = node("P", "", [nested]); const t1 = node("TABLE"); const t2 = node("TABLE"); return { md: node("DIV", "fileview-md", [p, t1, t2]), p, nested, t1, t2 }; };
  const w = (n: Node) => n.style.getPropertyValue("--fv-body-w");
  const lib = run(FakeResizeObserver);
  let root = fresh();
  const body = node("DIV", "fileview-body", [root.md]);
  const stamp = lib.watchBodyWidth(body);
  assert.equal(observers.length, 1); assert.deepEqual(observers[0].targets, [body], "the body is what the observer watches");
  stamp();
  assert.equal(w(root.t1) + w(root.t2), "", "before the first report nothing is written: the sheet's fallback holds (the cap is the column)");
  report([{ contentRect: { width: 900 } }]);
  assert.equal(w(root.t1), "900px"); assert.equal(w(root.t2), "900px");
  assert.equal(w(root.nested), "", "a table inside a paragraph is not the document's own: it keeps the prose width");
  assert.equal(w(root.p), "", "the prose is never written to (the property is non-inherited; a write there would reach nothing anyway)");
  // a paint: mdBlock rebuilt the root, no report follows; renderBody's stamp writes the width last reported on the fresh tables
  root = fresh(); body.children = [root.md];
  assert.equal(w(root.t1), "", "a fresh root starts unset");
  stamp();
  assert.equal(w(root.t1), "900px"); assert.equal(w(root.t2), "900px"); assert.equal(w(root.nested), "");
  // a report of the width already held is a no-op: a root rebuilt between the two reports is not touched by it
  root = fresh(); body.children = [root.md];
  report([{ contentRect: { width: 900 } }]);
  assert.equal(w(root.t1), "", "a repeated width writes nothing");
  report([{ contentRect: { width: 700 } }]);
  assert.equal(w(root.t1), "700px"); assert.equal(w(root.t2), "700px");
  assert.equal(root.t1.writes, 1, "one write per change");
  // the last of a callback's entries is the newest; a callback with no entry reads the body itself
  report([{ contentRect: { width: 300 } }, { contentRect: { width: 800 } }]);
  assert.equal(w(root.t1), "800px", "the last of the entries is the width kept");
  body.clientWidth = 640; report([]);
  assert.equal(w(root.t1), "640px", "a callback with no entry reads the body's clientWidth");
  // one watch at a time: the next open's watch drops the last, and the close drops the watch up
  const body2 = node("DIV", "fileview-body", []);
  lib.watchBodyWidth(body2);
  assert.equal(observers[0].live, false, "the second watch disconnects the first observer");
  assert.equal(observers.length, 2); assert.deepEqual(observers[1].targets, [body2]);
  lib.drop();
  assert.equal(observers[1].live, false, "the drop disconnects");
  assert.doesNotThrow(() => lib.drop(), "a second drop is nothing to do");
  // no ResizeObserver (a stand-in, an old engine): no observer, and the stamp writes nothing
  const bare = run(undefined);
  root = fresh(); const body3 = node("DIV", "fileview-body", [root.md]);
  bare.watchBodyWidth(body3)();
  assert.equal(observers.length, 2, "no observer was made"); assert.equal(w(root.t1) + w(root.t2), "", "nothing written: the sheet's fallback holds");
});

test("the width watch is wired: each viewer opens one on the body it builds, each rendered paint stamps the fresh root's tables, and the close drops it", () => {
  const opens = VIEW.match(/const body = el\("div", "fileview-body"\);\n\s*const stampBodyWidth = watchBodyWidth\(body\);/g) || [];
  assert.equal(opens.length, 1, "openUrlView watches its body as it builds it");
  assert.equal((VIEW.match(/const stampBodyWidth = watchBodyWidth\(body, \(w\) => \{/g) || []).length, 1,
    "openFileView watches its body where the reflow's per-frame fold lives, the fold on the watch's onWidth (the seam re-places the comments panel's cards once per animation frame)");
  assert.match(VIEW, /body\.replaceChildren\(rendered \? mdBlock\(text, \{ kind: "file", path, sid: sid \|\| null \}\) : codeBlock\(text, path, true\)\);[^\n]*\n\s*renderFell = null;\n\s*\} catch \(err\) \{\n[^\n]*\n[^\n]*\n[^\n]*\n\s*\}\n(?:\s*if \(text === ""\) body\.prepend\([^\n]*\);[^\n]*\n)?\s*viewError = null;[^\n]*\n\s*folds\.restore\(\); restoreHeldFolds\(\);[^\n]*\n\s*stampBodyWidth\(\);/,
    "openFileView: every paint stamps its fresh tables after the folds' restore, the keeper's and then a record's held past a Raw first paint, after the try's close (Slice 7 of plans/markdown-viewer.md, item 1: the swap sits inside the try; the fallback paint takes the same stamp; the review's round 2 made the catch three lines, the record after the fallback swap) (mdBlock rebuilt the root; no report follows a paint; the stamp returns at once on a Raw paint, which has no .fileview-md)");
  // openUrlView stamps between the folds' restore and the seat, the local viewer's order: the seat and the fragment landing
  // measure the fresh root, and a stamp after them would change the layout they had measured (review round 1 of the 4d-3
  // fold, correctness-1). A source pin, not an executed case: the stand-ins have no layout, so neither the seat nor the
  // landing reads a width there; the URL viewer's place keeping runs in file-view-url-place-bottom-browser.test.ts.
  assert.match(VIEW, /folds\.restore\(\);[^\n]*\n\s*if \(fmt\.md === "rendered"\) stampBodyWidth\(\);[^\n]*\n\s*shownText = text;\n\s*seat\(kept\);[^\n]*\n\s*landFragment\(\);/,
    "openUrlView: the stamp after the folds' restore and before the seat and the fragment landing, as the local viewer orders it (a Raw paint has no tables to stamp)");
  assert.doesNotMatch(VIEW, /landFragment\(\);[^\n]*\n\s*if \(fmt\.md === "rendered"\) stampBodyWidth\(\);/, "and never after the landing");
  const closeAt = VIEW.indexOf("export function closeFileView(): void {");
  const close = VIEW.slice(closeAt, VIEW.indexOf("\n}\n", closeAt));
  assert.match(close, /\n\s*dropWidthWatch\(\);/, "closeFileView drops the watch with the viewer");
});

test("it waits with the romp loader and fails with the kernel's own words, never a blank pane", () => {
  assert.match(VIEW, /romp-swirl-glyph\.svg/, "loading-state rule: the swirl goes up first");
  assert.match(VIEW, /fileview-dot/);
  // a 404/413/415 body IS the explanation (the 413 names the size and the cap) — show it, don't swallow
  // it. The status rides along since 2026-08-09, so the catch can decide whether to offer the download.
  assert.match(VIEW, /if \(!r\.ok\) return r\.text\(\)\.then\(\(t\) => \{\s*\n\s*throw Object\.assign\(new Error\(t \|\| \("HTTP " \+ r\.status\)\), \{ status: r\.status \}\);\s*\n\s*\}\);/);
  assert.match(VIEW, /const why = el\("div", "fileview-err"\);/);
  // a reply that lands after the user closed OR REPLACED the viewer paints nothing: the landing and the failure path both
  // read `stands` (the wrap connected, this fetch the newest), never the viewer id, which a replace-open moves to the new
  // viewer (the Slice 3 review, round 3; file-view-landing-order-browser.test.ts)
  assert.equal((VIEW.match(/if \(!stands\(\)\) return;/g) || []).length, 3, "the landing, the failure path, and `land` itself, which parks nothing for an answer that does not stand (the review's round 5: it records a parked landing for the bar's raise to wait on)");
});

test("it reuses fileUrl, so a REMOTE session's file is relayed from the host that owns it", () => {
  assert.match(VIEW, /import \{ fileUrl \} from "\.\/preview";/);
  assert.match(VIEW, /import \{ openPdfTab, wantsOwnTab \} from "\.\/preview";/);   // + the PDF tab opener and its gesture test (2026-09-06/07)
  assert.match(VIEW, /import \{ openFileTab, canPreview \} from "\.\/preview";/);   // + any file's own tab, for the links inside a shown file (file-view-links.test.ts)
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)/);
});

// executed: the extension→language map must never GUESS. highlightAuto on a config file or a log picks a
// language at random and paints it as information the file does not contain.
test("langFor maps known extensions and returns null rather than guessing", () => {
  const LANG: Record<string, string> = {
    py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
    cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
    yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
    html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
    md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
    rs: "rust", go: "go", c: "c", h: "c", java: "java", sql: "sql", toml: "ini", ini: "ini",   // viewer-grammars.ts
  };
  // the map above is the module's, row for row (a drift here is a drift in what a file opens as)
  const src = VIEW.slice(VIEW.indexOf("const LANG: Record<string, string> = {"), VIEW.indexOf("};", VIEW.indexOf("const LANG: Record<string, string> = {")));
  for (const [ext, lang] of Object.entries(LANG)) assert.match(src, new RegExp("\\b" + ext + ': "' + lang + '"'), ext + " is in file-view.ts's LANG");
  assert.match(VIEW, /^import "\.\/viewer-grammars";/m, "the six grammars the new rows name are registered by the module the viewer imports");
  const langFor = (p: string): string | null => LANG[p.slice(p.lastIndexOf(".") + 1).toLowerCase()] || null;
  assert.equal(langFor("kernel/kernel.py"), "python");
  assert.equal(langFor("ui/webview/render.TS"), "typescript");   // case-insensitive
  assert.equal(langFor("notes.md"), "markdown");
  assert.equal(langFor("src/main.rs"), "rust");
  assert.equal(langFor("Cargo.toml"), "ini", "toml is hljs's ini grammar");
  assert.equal(langFor("include/api.h"), "c");
  for (const p of ["server.log", "Makefile", "a.conf", "data.csv", "x.cfg", "x.zig", "x.hs"]) {
    assert.equal(langFor(p), null, p + " has no registered grammar → plain, not a guess");
  }
  // the module's map holds the same row: the copy above is the executed shape, this the source
  assert.match(VIEW, /rs: "rust", go: "go", c: "c", h: "c", java: "java", sql: "sql", toml: "ini", ini: "ini",/);
  assert.match(VIEW, /^import "\.\/viewer-grammars";/m, "the six grammars register through the viewer's own module");
  assert.doesNotMatch(VIEW, /hljs\.highlightAuto\(/, "auto-detection is what this map exists to avoid");
});

// ── formatting (the user 2026-08-09): the hljs palette, Raw ⇄ Rendered for markdown, and word wrap ──

// A. The viewer wraps every token in .hljs-* spans, and it renders in BOTH documents — the chat (file
// links) and the feed (the file browser) — so both sheets must carry the SAME palette (one treatment,
// two sheets — the .romp-acted precedent). This pins every rule in both and catches drift.
test("the hljs token palette lives in feed.css too, identical to the chat's", () => {
  const STYLES = CHAT_CSS;
  // tokenized 2026-09-02 (the light theme re-inks the same names; theme-parity.test.ts holds the
  // token set + its contrast in both themes) — the dark :root values are the exact hexes these
  // rules always carried: fg #d8c6a8, kw #c98a6a, str #9fb878, num #d4a36a, cmt #978f81 (raised from
  // #6f6a5f, which sat at 2.85:1 on a code block), title #e1c08d, meta #9a8f7a, attr #cdaf7e
  const rules = [
    /\.hljs \{ color: var\(--hl-fg\); background: transparent; \}/,
    /\.hljs-keyword, \.hljs-built_in, \.hljs-literal, \.hljs-type \{ color: var\(--hl-kw\); \}/,
    /\.hljs-string, \.hljs-attr, \.hljs-regexp \{ color: var\(--hl-str\); \}/,
    /\.hljs-number \{ color: var\(--hl-num\); \}/,
    /\.hljs-comment, \.hljs-quote \{ color: var\(--hl-cmt\); font-style: italic; \}/,
    /\.hljs-title, \.hljs-title\.function_, \.hljs-section \{ color: var\(--hl-title\); \}/,
    /\.hljs-name, \.hljs-tag \{ color: var\(--hl-kw\); \}/,
    /\.hljs-params, \.hljs-variable, \.hljs-property \{ color: var\(--hl-fg\); \}/,
    /\.hljs-meta \{ color: var\(--hl-meta\); \}/,
    /\.hljs-attribute \{ color: var\(--hl-attr\); \}/,
    /\.hljs-addition \{ color: var\(--hl-str\); \}/,
    /\.hljs-deletion \{ color: var\(--err\); \}/,
    /--hl-fg: #d8c6a8; --hl-kw: #c98a6a; --hl-str: #9fb878; --hl-num: #d4a36a;/,
    /--hl-cmt: #978f81; --hl-title: #e1c08d; --hl-meta: #9a8f7a; --hl-attr: #cdaf7e;/,   // --hl-cmt raised to 4.79:1 on a code block (was #6f6a5f, 2.85:1); theme-parity.test.ts holds the pair
  ];
  for (const r of rules) {
    assert.match(FEED_CSS, r, "feed.css is missing a palette rule: " + r.source);
    assert.match(STYLES, r, "styles.css drifted from the shared palette: " + r.source);
  }
});

// B, executed: the persisted view-format prefs. RENDERED is the markdown default (the user's explicit
// call, 2026-08-09) and any malformed stored value reads as the defaults — a corrupt entry may cost the
// preference, never the viewer (feed-view-state's parseViewState contract).
test("format prefs: rendered is the markdown default, and a corrupt entry reads as the defaults", () => {
  // wrap is GONE from the format state (the user 2026-08-24) — a stored wrap key from the toggle
  // era parses away silently
  type Fmt = { md: "rendered" | "raw" };
  const parseFmt = (raw: string | null): Fmt => {
    const def: Fmt = { md: "rendered" };
    if (!raw) return def;
    try {
      const o = JSON.parse(raw) as { md?: unknown };
      if (!o || typeof o !== "object") return def;
      return { md: o.md === "raw" ? "raw" : "rendered" };
    } catch { return def; }
  };
  assert.deepEqual(parseFmt(null), { md: "rendered" }, "first open: rendered");
  assert.deepEqual(parseFmt('{"md":"raw","wrap":true}'), { md: "raw" }, "the toggle-era wrap key parses away");
  assert.deepEqual(parseFmt("not json"), { md: "rendered" });
  assert.deepEqual(parseFmt('{"md":"purple","wrap":"yes"}'), { md: "rendered" },
                   "foreign values fall to the defaults field by field");
  // replica ↔ source
  assert.match(VIEW, /const def: FileViewFmt = \{ md: "rendered" \};/);
  assert.match(VIEW, /return \{ md: o\.md === "raw" \? "raw" : "rendered" \};/);
  // …and the prefs persist in localStorage, the feed-view-state call: per-BROWSER view state that must
  // survive a kernel restart without a round-trip to the thing that just restarted
  assert.match(VIEW, /const FMT_KEY = "romp:fileviewFmt";/);
  assert.match(VIEW, /localStorage\.getItem\(FMT_KEY\)/);
  assert.match(VIEW, /localStorage\.setItem\(FMT_KEY, JSON\.stringify\(f\)\)/);
});

// B: the toggle itself — markdown only, and the rendered path is sanitized. These are arbitrary bytes
// off a disk and marked emits raw HTML verbatim, so DOMPurify sits between it and the DOM, through the
// ONE sanitizer the chat's md() uses too (sanitizeMd, md-sanitize.ts); what it does to a file's own HTML
// is executed in headless Chromium by md-sanitize-browser.test.ts.
test("Raw ⇄ Rendered exists for markdown ONLY, and nothing reaches innerHTML unsanitized", () => {
  assert.match(VIEW, /const isMd = langFor\(path\) === "markdown";/);
  // the two buttons are built inside the isMd gate — a .py file shows no Rendered/Raw toggle
  assert.match(VIEW, /if \(isMd\) \{\s*\n\s*const seg = el\("span", "fileview-seg"\);[\s\S]{0,400}?for \(const mode of \["rendered", "raw"\] as const\)/,
    "the pair is built inside the isMd gate, into ONE segmented wrapper (T367)");
  assert.match(VIEW, /const rendered = isMd && fmt\.md === "rendered";/, "non-md never renders as prose");
  assert.match(VIEW, /import \{ sanitizeMd, revealFragmentTarget \} from "\.\/md-sanitize";/);   // the sanitizer, and the shared reveal step scrollToFragment runs before its scroll
  assert.doesNotMatch(VIEW, /from "dompurify"/, "the viewer spells no profile of its own: every option comes through md-sanitize.ts");
  // the sanitized <body>'s children are adopted as they are (no re-parse of a serialized string); the heading ids are minted
  // inside the call, as the caller's own pass, so they are read from the text as written, before the math fill (md-url-view.test.ts);
  // these two are presence pins; where the figure chain sits relative to the adoption is file-view-seam.test.ts's to check, on
  // comment-stripped code (the round-1 ruling of the fork PR's review: one order pin, the seam's, not an index compare per module)
  assert.match(VIEW, /const clean = sanitizeMd\(dirty, mintHeadingIds, \{ remoteRefs: "keep" \}\);/);   // the heading ids as the viewer's own pass, and the paint pass off: the gate judges the same references
  assert.match(VIEW, /box\.replaceChildren\(\.\.\.Array\.from\(clean\.childNodes\)\);/);
  // a note's links open a NEW tab rather than navigating the hosting pane's document away. A file on disk hands its
  // anchors to file-view-links.ts (linkMarkdownAnchors, fork PR #347: a web link stamped, a sibling file opened in
  // the viewer); a URL document, or a caller with no location, stamps every link element in mdBlock's own pass. Both
  // write the ATTRIBUTE: an SVG <a>'s `target` property is a read-only SVGAnimatedString, so a property write was
  // dropped without a word (md-sanitize-viewer-links.test.ts). Read from mdBlock and the module's walk, never the
  // whole file: the GitHub button and the URL viewer's Open link stamp `_blank` too, and a whole-file pin matched
  // those and stayed green with mdBlock's own stamps deleted (review of Slice 1, round 2).
  const mdFn = VIEW.split("function mdBlock(")[1].split("export function rewriteFigureSrcs")[0];
  assert.match(mdFn, /if \(doc && doc\.kind === "file"\) \{/, "the file kind has its own arm");
  assert.match(mdFn, /\n {4}linkMarkdownAnchors\(box, doc\.path\);/, "a file's links: the module's walk, on every render (no `rendered` gate since Slice 7 of plans/markdown-viewer.md, item 1: mdBlock has no fallback to skip)");
  assert.match(mdFn, /a\.setAttribute\("target", "_blank"\);\s*\n\s*a\.setAttribute\("rel", "noopener"\);/, "a URL document's links: stamped here, as attributes");
  assert.doesNotMatch(mdFn, /\ba\.(target|rel)\s*=/, "no property write on either");
  const linkFn = web("file-view-links.ts").split("export function linkMarkdownAnchors(")[1];
  assert.match(linkFn, /a\.setAttribute\("target", "_blank"\);\s*\n\s*a\.setAttribute\("rel", "noopener"\);/, "…and the module stamps a web link the same way");
  // fenced blocks highlight only a NAMED, registered language (the same no-guessing rule as langFor); then EVERY fence, named or
  // not, gets the chat's rows and Copy button (code-block.ts; Slice 3 of plans/markdown-viewer.md), the raw text captured first (code-block.test.ts pins the pass)
  assert.match(VIEW, /if \(lang && hljs\.getLanguage\(lang\)\) \{/);
  assert.match(VIEW, /^import \{ wrapCodeLines, addCopyBtn \} from "\.\/code-block";/m);
  // Copy hands the clipboard the fence's text as the note holds it (fence-source.ts; the raw text has marked's four spaces for
  // each leading tab), the raw text when the fence was not found in the note
  assert.match(VIEW, /const raw = codeEl\.textContent \|\| "";[\s\S]{0,600}codeEl\.innerHTML = hljs\.highlight\(raw, \{ language: lang \}\)\.value;[\s\S]{0,200}wrapCodeLines\(codeEl\);\s*\n\s*if \(host\) addCopyBtn\(host, toCopy\);/);
  // the two calls close the forEach's callback, outside the language branch (indentation and the `});` anchor it there)
  assert.match(VIEW, /\n    wrapCodeLines\(codeEl\);\n    if \(host\) addCopyBtn\(host, toCopy\);\n  \}\);/);
  assert.match(VIEW, /const toCopy = \(queued && queued\.length \? queued\.shift\(\) : null\) \?\? raw;/);
  // the prose typography exists on BOTH sheets (the chat's .md block is the reference aesthetic)
  assert.match(FEED_CSS, /\.fileview-md \{/);
  assert.match(FEED_CSS, /\.fileview-md pre code \{/);
  assert.match(CHAT_CSS, /\.fileview-md \{/);
  assert.match(CHAT_CSS, /\.fileview-md pre code \{/);
  // toggles acknowledge in the same synchronous tick: click → save → renderBody, which flips .on
  assert.match(VIEW, /b\.addEventListener\("click", \(\) => \{ fmt\.md = mode; saveFmt\(fmt\); renderBody\(\); \}\);/);
  assert.match(VIEW, /b\.classList\.toggle\("on", on\);/);
  assert.match(FEED_CSS, /\.fileview-btn\.on \{ color: var\(--accent\); border-color: var\(--accent\);/);
  assert.match(CHAT_CSS, /\.fileview-btn\.on \{ color: var\(--accent\); border-color: var\(--accent\);/);
});

// C, executed: wrap mode's numbering. A flat gutter misaligns the moment one logical line wraps onto
// several visual lines, so wrap mode restructures — each logical line is a .fv-cl row numbered by a CSS
// counter — instead of shipping a drifting column. hljs spans can cross newlines, so each row must
// re-open what the previous row left unclosed (render.ts's wrapCodeLines balance walk). Since Slice 7 of
// plans/markdown-viewer.md (item 7) a line ends at a CRLF, a lone CR or an LF (RAW_ROW_SPLIT, tried in that
// order so a CRLF is one ending), so a CR-only file gives one row per line where it gave ONE row (the HTML
// parser turned its CRs into breaks inside it) and no row's text carries a "\r".
test("wrap mode: per-line rows split on CRLF, a lone CR and LF, spans rebalanced across any of them, no phantom trailing row", () => {
  const RAW_ROW_SPLIT = /\r\n|\r|\n/;
  const wrapNumberedHtml = (html: string): string => {
    const lines = html.split(RAW_ROW_SPLIT);
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    let open: string[] = [];
    return lines.map((ln) => {
      const prefix = open.join("");
      const re = /<span[^>]*>|<\/span>/g; let m; const stack = open.slice();
      while ((m = re.exec(ln))) { if (m[0] === "</span>") stack.pop(); else stack.push(m[0]); }
      const suffix = "</span>".repeat(Math.max(0, stack.length));
      open = stack;
      return `<span class="fv-cl"><span class="fv-ct">${prefix}${ln}${suffix}</span></span>`;
    }).join("");
  };
  // a string token spanning a newline: closed at the end of row 1, re-opened at the start of row 2
  const out = wrapNumberedHtml('<span class="hljs-string">"a\nb"</span>\nplain');
  const rows = out.split('<span class="fv-cl">').filter(Boolean);
  assert.equal(rows.length, 3, "three logical lines, three rows");
  for (const row of rows) {
    const opens = (row.match(/<span[^>]*>/g) || []).length;
    const closes = (row.match(/<\/span>/g) || []).length;
    // +1: the .fv-cl open itself was consumed as the split delimiter
    assert.equal(opens + 1, closes, "a row must close every span it opens: " + row);
  }
  assert.match(rows[0], /<span class="hljs-string">"a<\/span>/);
  assert.match(rows[1], /^<span class="fv-ct"><span class="hljs-string">b"<\/span>/);
  assert.equal((wrapNumberedHtml("a\n").match(/fv-cl/g) || []).length, 1,
               "a trailing newline is not a phantom row — same rule as the gutter");
  // the three endings (Slice 7, item 7): one row per line, whichever ending the file has, and no CR left in a row
  const texts = (html: string): string[] => wrapNumberedHtml(html).split('<span class="fv-cl">').filter(Boolean).map((r) => r.replace(/<[^>]*>/g, ""));
  assert.deepEqual(texts("a\rb\rc\r"), ["a", "b", "c"], "a CR-only file: three rows (before: one row holding the three CRs)");
  assert.deepEqual(texts("a\r\nb\r\nc\r\n"), ["a", "b", "c"], "a CRLF file: three rows, a CRLF one ending, no phantom trailing row (before: three rows each ending in a CR)");
  assert.deepEqual(texts("one\rtwo\r\nthree\nfour"), ["one", "two", "three", "four"], "a mixed file: one row per line, the last line without an ending kept");
  assert.deepEqual(texts("\r\r"), ["", ""], "two empty CR-ended lines: two rows, the trailing ending popped once");
  for (const html of ["a\rb\rc\r", "a\r\nb\r\nc\r\n", "one\rtwo\r\nthree\nfour"]) assert.doesNotMatch(wrapNumberedHtml(html), /[\r\n]/, "no row's markup carries a CR or an LF: " + JSON.stringify(html));
  // a string token spanning a lone CR: closed at the end of row 1, re-opened at the start of row 2, as across an LF
  const cr = wrapNumberedHtml('<span class="hljs-string">"a\rb"</span>\rplain').split('<span class="fv-cl">').filter(Boolean);
  assert.equal(cr.length, 3, "three logical lines, three rows");
  for (const row of cr) {
    const opens = (row.match(/<span[^>]*>/g) || []).length;
    const closes = (row.match(/<\/span>/g) || []).length;
    assert.equal(opens + 1, closes, "a row must close every span it opens across a CR: " + row);
  }
  assert.match(cr[0], /<span class="hljs-string">"a<\/span>/);
  assert.match(cr[1], /^<span class="fv-ct"><span class="hljs-string">b"<\/span>/);
  assert.match(cr[2], /^<span class="fv-ct">plain<\/span>/);
  // replica ↔ source
  assert.match(VIEW, /return `<span class="fv-cl"><span class="fv-ct">\$\{prefix\}\$\{ln\}\$\{suffix\}<\/span><\/span>`;/);
  assert.match(VIEW, /\nconst RAW_ROW_SPLIT = \/\\r\\n\|\\r\|\\n\/;\n/, "one module-level regex, CRLF first, then a lone CR, then LF (contract C6)");
  assert.match(VIEW, /function wrapNumberedHtml\(html: string\): string \{\n  const lines = html\.split\(RAW_ROW_SPLIT\);\n  if \(lines\.length && lines\[lines\.length - 1\] === ""\) lines\.pop\(\);/, "the rows split on it, the trailing empty piece popped as before");
  assert.match(VIEW, /const wrap = el\("div", "fileview-code"\);\n  const lines = text\.split\(RAW_ROW_SPLIT\);\n  if \(lines\.length && lines\[lines\.length - 1\] === ""\) lines\.pop\(\);/, "the gutter branch's count splits the same way, so the two stay in step");
  // the regex is declared with the module's constants, above the openFileView closure whose scrollToOffset reads it (the Slice 7
  // review's round 1 hoisted it from beside the two builders), so the Raw view's slice starts at the builders
  assert.ok(VIEW.indexOf("\nconst RAW_ROW_SPLIT =") > 0 && VIEW.indexOf("\nconst RAW_ROW_SPLIT =") < VIEW.indexOf("\nexport function openFileView("), "declared above the closure that uses it");
  const rawView = VIEW.slice(VIEW.indexOf("\n// Wrap mode's numbering."), VIEW.indexOf("\n// Land an in-document fragment on its target."));
  assert.ok(rawView.includes("function wrapNumberedHtml(") && rawView.includes("function codeBlock("), "the slice holds both functions");
  assert.doesNotMatch(rawView, /split\("\\n"\)/, "no LF-only split left in the Raw view's builders");
});

// C: the seam's scrollToOffset reads the row through the anchor map's verified row map (Slice 7 of plans/markdown-viewer.md,
// item 7; contract C6), so it follows the split above whatever the file's endings; the LF-only counter it kept is gone.
test("source: scrollToOffset finds the row through rawRowForOffset and, when the map refuses, counts the row over the source with the viewer's own split; the LF counter is gone", () => {
  const closure = VIEW.split("    scrollToOffset: (n) => {")[1].split("\n    },")[0];
  assert.match(closure, /^\n      const src = viewText\(\);\n      const code = body\.querySelector\("code\.hljs"\);\n      if \(src === null \|\| !code\) return;\n      const rows = code\.querySelectorAll\("\.fv-cl"\);\n      if \(!rows\.length\) return;\n/, "the guards as before");
  assert.match(closure, /\n      const row = rawRowForOffset\(code, src, n\);\n      const target = row \?\? rows\[Math\.min\(src\.slice\(0, Math\.max\(0, n\)\)\.split\(RAW_ROW_SPLIT\)\.length - 1, rows\.length - 1\)\];\n      \(target as HTMLElement\)\.scrollIntoView\(\{ block: "center" \}\);$/, "the map first; the count over the source with the same split, clamped to the last row, when it refuses");
  assert.doesNotMatch(closure, /match\(\/\\n\/g\)/, "the second line counter is gone (before: LF alone, so every offset in a CR-only file landed on row 0)");
  assert.doesNotMatch(VIEW, /match\(\/\\n\/g\) \|\| \[\]\)\.length;\s*\/\/ one \.fv-cl per logical line/, "nowhere else either");
  assert.match(VIEW, /^import \{ rawRowForOffset \} from "\.\/anchor-map";/m, "imported on a line of its own (the existing anchor-map import line keeps its pin)");
  assert.equal((VIEW.match(/rawRowForOffset\(/g) || []).length, 1, "one call, the seam's");
});

// C: the toggle and the CSS that carries the honest gutter answer
test("long lines ALWAYS soft-wrap — the dedicated toggle button is gone (the user 2026-08-24)", () => {
  assert.doesNotMatch(VIEW, /wrapBtn/, "no wrap chrome anywhere in the modal");
  assert.match(VIEW, /codeBlock\(text, path, true\)/, "the pre view is born wrapped");
  // wrap mode returns BEFORE the sibling gutter is built — a misaligned column cannot exist
  assert.match(VIEW, /if \(wrapLines\) \{[\s\S]*?return wrap;\s*\}\s*const gutter = el\("div", "fileview-gutter"\);/);
  // plain files wrap too: no grammar → the text is HTML-escaped before the line walk
  assert.match(VIEW, /code\.innerHTML = wrapNumberedHtml\(hl !== null \? hl : escapeHtml\(text\)\);/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) {
    assert.match(SHEET, /\.fileview-pre\.fileview-wrap \{ white-space: pre-wrap/);
    assert.match(SHEET, /\.fileview-wrap \.fv-cl::before \{[\s\S]*?counter-increment: fvln/);
    assert.match(SHEET, /\.fileview-wrap \.fv-cl::before \{[\s\S]*?user-select: none/);
  }
});

test("a file opened FROM the listing offers the way back — close only the viewer, listing intact beneath", () => {
  // the one-directional stack: the browser sits beneath, so closing just the viewer IS the back;
  // presence-gated on the browser's DOM id (import-free), absent for path-link opens
  assert.match(VIEW, /if \(document\.getElementById\("romp-filebrowse"\)\) \{/);
  assert.match(VIEW, /back\.textContent = "‹ Files"; back\.title = "Back to the file listing";/);
  assert.match(VIEW, /back\.addEventListener\("click", \(\) => closeFileView\(\)\);/);
});

// ── download (the user 2026-08-09): any linked file can be SAVED, including everything the pane cannot
// show — the kernel's ?download=1 serves anything on disk (the rationale lives with _file_download in
// kernel.py: the view allowlists are a rendering choice, not a security boundary). ──

test("the title bar offers Download as the lightbox's tray glyph, in the file group beside Copy path, at the same-origin download URL (T367)", () => {
  // the URL is fileUrl + the download switch: same origin, cookie-authed, and federation-aware for
  // free — fileUrl already routes a remote session's file through the /remote/<host>/file relay
  assert.match(VIEW, /const dlUrl = fileUrl\(path, sid\) \+ "&download=1";/);
  assert.match(VIEW, /dl\.innerHTML = ICON_DOWNLOAD;/, "the one tray drawing (icons.ts), not a word");
  assert.match(VIEW, /dl\.title = "Download"; dl\.setAttribute\("aria-label", "Download"\);/, "the word rides the title and aria-label");
  assert.doesNotMatch(VIEW, /dl\.textContent = "Download";/);
  // in the file group beside Copy path (a glyph too), wearing the same button class
  assert.match(VIEW, /fileGroup\.appendChild\(dl\);/);
  assert.match(VIEW, /const copy = el\("button", "fileview-btn fileview-icon"\) as HTMLButtonElement;/);
  assert.match(VIEW, /fileGroup\.appendChild\(copy\);/);
  // the wider gaps apply only where groups exist: the close cross after a GROUP sibling, never the file browser's row or
  // the URL viewer's flat row (review)
  for (const css of [CHAT_CSS, FEED_CSS]) {
    assert.match(css, /\.fileview-acts > \.fileview-group \+ \.fileview-group, \.fileview-acts > \.fileview-group ~ \.fileview-close \{ margin-left: 10px; \}/);
    assert.doesNotMatch(css, /\.fileview-acts > \.fileview-close \{/, "an unscoped close margin would move the file browser's and the URL viewer's cross");
  }
  assert.match(VIEW, /const dl = el\("button", "fileview-btn"\) as HTMLButtonElement;/, "no new styling, no new font size");
});

test("startDownload hands the URL to the browser's downloader and never wipes the pane", () => {
  // an <a download> click: the BROWSER owns the request (its progress UI, its save location), and the
  // kernel's attachment disposition means the page never navigates — the viewer stays put
  assert.match(VIEW, /const a = document\.createElement\("a"\);\s*\n\s*a\.href = url;\s*\n\s*a\.download = "";/);
  assert.match(VIEW, /document\.body\.appendChild\(a\);\s*\n\s*a\.click\(\);\s*\n\s*a\.remove\(\);/);
  assert.doesNotMatch(VIEW, /location\.href\s*=/, "no navigation — a wiped pane is the failure mode this avoids");
  // …and the click acknowledges itself (ui/CLAUDE.md): the download UI can take a beat over a tunnel
  assert.match(VIEW, /btn\.textContent = "Downloading…";/);
});

// executed: which fetch failures still deserve a Download offer? Exactly the ones that mean the file
// EXISTS — 413 (too large to render) and 415 (on disk but not viewable: a .zip, a binary named like
// text). A 404 is genuinely missing, and offering to download it would be a lie.
test("offersDownload: 413 and 415 offer, 404 and everything else do not", () => {
  const offersDownload = (status: number | undefined): boolean => status === 413 || status === 415;
  assert.equal(offersDownload(413), true, "too big to render ≠ too big to save");
  assert.equal(offersDownload(415), true, "exists-but-unviewable is the case the button exists for");
  assert.equal(offersDownload(404), false, "genuinely missing → nothing to offer");
  assert.equal(offersDownload(403), false);
  assert.equal(offersDownload(undefined), false, "a network failure carries no status and no offer");
  // replica ↔ source
  assert.match(VIEW, /return status === 413 \|\| status === 415;/);
});

test("a refusal renders the kernel's words PLUS the way out — gated on offersDownload", () => {
  // the status rides the thrown error so the catch can tell "there but unshowable" from "not there"
  assert.match(VIEW, /throw Object\.assign\(new Error\(t \|\| \("HTTP " \+ r\.status\)\), \{ status: r\.status \}\);/);
  // the offer appends to the SAME error pane that shows the kernel's message — an offer, not a dead end
  assert.match(VIEW, /if \(offersDownload\(\(err as \{ status\?: number \}\)\.status\)\) \{/);
  assert.match(VIEW, /const offer = el\("button", "fileview-btn fileview-err-dl"\) as HTMLButtonElement;/);
  assert.match(VIEW, /why\.appendChild\(offer\);/);
  assert.match(VIEW, /offer\.addEventListener\("click", \(\) => startDownload\(dlUrl, offer\)\);/);
  assert.match(FEED_CSS, /\.fileview-err-dl \{ display: block; margin-top: 10px; \}/);
  assert.match(CHAT_CSS, /\.fileview-err-dl \{ display: block; margin-top: 10px; \}/);
});

test("Edit is consent-gated, and the gate is the KERNEL's flag, not the button (the user 2026-08-22)", () => {
  // the click asks the kernel's live flag first — never a cached copy, another machine may have flipped it
  assert.match(VIEW, /fetch\(kernelUrl\("\/version"\), \{ cache: "no-store" \}\)/);
  assert.match(VIEW, /\.fileEditing;/);
  // no flag → a plain-words popup; only a YES posts the opt-in, and it broadcasts (KERNEL_SETTING)
  // — stamped with the gesture's own time, so a copy queued for a down host and flushed hours
  // later can never outrank a newer pick at the kernel (the store orders applies by gt)
  // the popup is ensureEditingAllowed's, shared with the comments panel's verbs since Slice 1 of
  // plans/file-review.md (decision 5: one consent; its copy says saves AND comments write disk)
  assert.match(VIEW, /const COPY = "Allow editing files from the dashboard\?\\n\\n"/);
  assert.match(VIEW, /Saves and comments write straight to disk on the file's machine/);
  assert.match(VIEW, /if \(!window\.confirm\(COPY\)\) return false;/);
  assert.match(VIEW, /post\(\{ type: "setFileEditing", enabled: true, gt: gclock\.stamp\("file-editing"\) \}\);/,
    "…minted through the gesture clock, above every stamp the /version read just reported");
  assert.match(VIEW, /const gclock = require\("\.\/gesture-clock\.js"\);/, "the viewer loads the clock");
  assert.match(VIEW, /gclock\.learnAll\(v\.settingsGt\);/, "the consent check's /version read teaches the clock");
  assert.match(VIEW, /void ensureEditingAllowed\(sid\)\.then\(\(ok\) => \{\n\s*if \(!ok\) return;/, "the Edit click asks through the shared helper");
  // the popup's promise of a gear off-switch is real, and the save route refuses server-side
  const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");
  assert.ok(GEAR.includes("'setFileEditing'"), "the gear can turn it back off");
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /if not _file_editing_on\(\):/);
  assert.match(KERNEL, /dashboard file editing is off on this machine/);
});

// executed: the Escape handler's LIFECYCLE. Each open registers its own document-level onKey
// closure; the REPLACE path (the conflict-Reload re-open) used to leave the old viewer's handler
// registered, and with a new viewer up its `!getElementById` guard no longer no-ops — the stale
// closure (editing still true from before the replace) ran exitEdit against the NEW viewer's
// world and nulled the module-level editHooks an in-flight save was waiting on, so the fileSaved
// ack matched nothing and Save wedged at "Saving…" (Reload → re-edit → Escape mid-save). The
// model replays that journey against both lifecycles.
test("replace-open drops the previous viewer's Escape handler — a stale closure cannot null a new save's hooks", () => {
  const sim = (dropOnReplace: boolean) => {
    const listeners: Array<() => void> = [];
    let editHooks: { reqId: number } | null = null;     // module-level, as in the source
    let live: (() => void) | null = null;
    const dropOnKey = () => {
      if (live) { const i = listeners.indexOf(live); if (i >= 0) listeners.splice(i, 1); live = null; }
    };
    const open = () => {
      if (dropOnReplace) dropOnKey();                   // the fix: the replace path unregisters
      editHooks = null;                                 // the replace path's existing module drops
      const v = { editing: false, dirty: false };
      const exitEdit = () => { v.editing = false; editHooks = null; };  // source: exitEdit nulls the hooks
      const onKey = () => {                             // Escape peels edit mode behind confirmDiscard
        if (v.editing && !v.dirty) exitEdit();          // !dirty short-circuits the confirm — no user gate
      };
      listeners.push(onKey); live = onKey;
      return v;
    };
    const a = open();
    a.editing = true; a.dirty = true;                   // mid-edit when the agent's write conflicts
    a.dirty = false;                                    // Reload's confirmed discard clears it pre-replace
    const b = open();                                   // the replace-open (openFileView over viewer A)
    b.editing = true; b.dirty = true;                   // re-edit…
    editHooks = { reqId: 7 };                           // …Save in flight ("Saving…")
    for (const fn of [...listeners]) fn();              // Escape mid-save; the user keeps B's edits
    return { ackLands: editHooks !== null, liveHandlers: listeners.length };
  };
  assert.equal(sim(false).ackLands, false,
    "pre-fix lifecycle: A's stale closure nulls the hooks and B's ack is dropped — the wedge");
  const fixed = sim(true);
  assert.equal(fixed.ackLands, true, "with the replace-path drop only the live viewer's handler runs");
  assert.equal(fixed.liveHandlers, 1, "one viewer, one document-level handler");
  // replica ↔ source: ONE live handler tracked at module level, dropped by BOTH exits after their
  // dirty guards — closeFileView and the replace path — and re-pointed at each open's own closure
  assert.match(VIEW, /let onKeyLive: \(\(e: KeyboardEvent\) => void\) \| null = null;/);
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /dropOnKey\(\);/, "closeFileView unregisters the handler it would strand");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.ok(openFn.indexOf("dropOnKey();") > openFn.indexOf("closeGuard && !closeGuard()) return false;"),
    "the drop sits AFTER the dirty-guard veto — a kept viewer keeps its handler");
  assert.ok(openFn.indexOf("dropOnKey();") < openFn.indexOf('document.getElementById("romp-fileview")?.remove();'),
    "…and with the replace path's other module-level drops, before the old viewer is torn down");
  assert.match(openFn, /document\.addEventListener\("keydown", onKey\);\s*\n\s*onKeyLive = onKey;/);
});

// executed: the consent gate is enforced by the file-OWNING kernel, but the Edit click's /version
// read sees only the LOCAL flag — a mesh kernel attached AFTER the one yes never heard the
// broadcast, so it refuses every save with copy pointing at a popup the local flag keeps from ever
// re-showing. The failed handler therefore recognizes the gate refusal, re-offers the SAME consent
// naming the machine that refused, and a yes re-broadcasts setFileEditing (KERNEL_SETTING reaches
// every attached kernel, the late one included) and retries the save — the broadcast and the save
// ride the same ordered socket, so the flag lands first.
test("a save refused by the OWNING kernel's edit gate re-offers the consent and re-broadcasts", () => {
  const gateRefusal = (err: string): boolean => /file editing is off/.test(err);
  assert.equal(gateRefusal("cannot save ~/notes-api/app.py: dashboard file editing is off on this "
    + "machine — the viewer's Edit button asks to turn it on"), true);
  assert.equal(gateRefusal("~/notes-api/app.py changed on disk since you opened it — reload before "
    + "editing (someone else, likely an agent, wrote it)"), false,
    "a conflict keeps its Reload offer — never a consent popup");
  assert.equal(gateRefusal("cannot save ~/notes-api/app.py: the file is not UTF-8 on disk — saving "
    + "would silently re-encode bytes you never touched"), false);
  // replica ↔ source: the failed handler carries the branch, names the host, re-posts, retries
  assert.match(VIEW, /if \(\/file editing is off\/\.test\(err\)\) \{/);
  assert.match(VIEW, /import \{[^}]*\bhostOf\b[^}]*\} from "\.\/host-prefix";/,   // beside the session chip's helpers since 2026-09-03
    "the popup names the refusing machine — the host prefix the viewer's sid already carries");
  // the arm hands the refusal to ensureEditingAllowed's re-consent path (shared with the comment
  // verbs since Slice 1) and retries on a yes; the helper re-posts the SAME opt-in the first popup
  // sends — gesture-stamped like it — before the caller's retry rides the same socket
  // `code` (Slice 5): the comments host's refusal code when the save went through the panel: the moved fences offer
  // Reload, and so does a held sidecar lock ("busy", since 2026-09-11: another writer was mid-write; a reload shows
  // what it wrote). The arm is scoped by its CLOSING line, used as a split anchor, so the anchor's own match is
  // asserted first: when that line was rewritten to add "busy", the old anchor matched nothing, the split returned
  // one part (the whole rest of the file) and the arm-scoped assert below passed against text anywhere in it.
  const ARM_OPEN = "failed: (err, code) => {";
  const ARM_CLOSE = 'showSaveError(err, code === "store-moved" || code === "file-moved" || code === "config-moved" || code === "busy");\n      },';
  assert.equal(VIEW.split(ARM_OPEN).length, 2, "one save-failed arm takes a refusal code");
  const armParts = VIEW.split(ARM_OPEN)[1].split(ARM_CLOSE);
  assert.equal(armParts.length, 2, "the failed arm closes on its showSaveError line, found exactly once: a drifted anchor widens the scope to the whole file, silently");
  const failedArm = armParts[0];
  assert.ok(!failedArm.includes("editHooks = hooks;"), "the scope ends at the arm, before the hooks object is installed");
  assert.match(failedArm, /void ensureEditingAllowed\(sid, err\)\.then\(\(ok\) => \{ if \(ok\) doSave\(\); else showSaveError\(err\); \}\);/);
  const helper = VIEW.split("export async function ensureEditingAllowed(")[1].split("\n}")[0];
  assert.match(helper, /if \(!\/file editing is off\/\.test\(refusal\)\) return false;/, "only the gate's own text re-offers");
  assert.match(helper, /"Editing is off on " \+ \(host \? "“" \+ host \+ "”" : "this machine"\)/, "names the refusing machine");
  assert.equal((helper.match(/post\(\{ type: "setFileEditing", enabled: true, gt: gclock\.stamp\("file-editing"\) \}\);/g) || []).length, 2,
    "both paths post the one opt-in, stamped through the gesture clock");
  assert.ok(helper.indexOf('post({ type: "setFileEditing"') < helper.indexOf("return true;"), "the opt-in is posted before the caller may retry");
  // the two sides of the text match are pinned TOGETHER so drift fails loudly, and the broadcast
  // route the re-offer relies on is federation's, not a new one
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /dashboard file editing is off on this machine/);
  const FED = web("federation.ts");
  assert.ok(FED.includes('"setFileEditing"'), "setFileEditing is a KERNEL_SETTING…");
  assert.match(FED, /if \(KERNEL_SETTING\.has\(msg\.type\)\) return \[LOCAL, \.\.\.\(knownHosts \|\| \[\]\)\]/,
    "…and KERNEL_SETTING broadcasts to every attached kernel");
});

// ── inline images + PDFs: a clicked .png used to open as line-numbered mojibake — the fetch pipeline
// called r.text() unconditionally on any 200. The viewer branches on the KERNEL'S OWN Content-Type
// verdict (the authoritative-source rule; the kernel derives mime locally and the relay re-derives
// it, so the header is a verdict, never an echo — no client-side extension re-test), takes the
// already-fetched bytes as a blob (no second request), and renders media as media. ──

// executed: the routing replica — which body call a 200 gets, by the kernel's header alone
test("the media branch keys on the kernel's Content-Type verdict, never the extension", () => {
  const mediaKind = (ct: string): "img" | "pdf" | null =>
    ct.startsWith("image/") ? "img" : ct.startsWith("application/pdf") ? "pdf" : null;
  assert.equal(mediaKind("image/png"), "img");
  assert.equal(mediaKind("image/svg+xml"), "img", "SVG is an image here — the <img> surface");
  assert.equal(mediaKind("application/pdf"), "pdf");
  assert.equal(mediaKind("text/plain; charset=utf-8"), null, "text keeps the r.text() pipeline unchanged");
  assert.equal(mediaKind(""), null, "no header → the text path, exactly the pre-image behavior");
  // replica ↔ source: the flags read the kernel's header, and blob is taken ONLY for media
  assert.match(VIEW, /const ct = r\.headers\.get\("Content-Type"\) \|\| "";/);
  assert.match(VIEW, /isImage = ct\.startsWith\("image\/"\);/);
  assert.match(VIEW, /isPdf = ct\.startsWith\("application\/pdf"\);/);
  assert.match(VIEW, /return isImage \|\| isPdf \? r\.blob\(\) : r\.text\(\);/);
  // never a client-side extension re-test: preview.ts's extension probe stays out of this module
  assert.doesNotMatch(VIEW, /previewKind\(/);
  assert.doesNotMatch(VIEW, /IMG_EXT/);
});

test("a 200 image renders ONE <img> at an object URL; the quote gesture stays off RENDERED media", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  // the blob becomes an object URL only AFTER the still-this-viewer, still-the-newest-fetch check (`stands`: the wrap
  // connected, so a close or a REPLACE both count, and this fetch the newest out): a viewer closed or replaced
  // mid-flight creates nothing to leak. The check reads the wrap, not the viewer id: after a replace-open the id sits on
  // the new viewer and passed for the old one (the Slice 3 review, round 3; file-view-landing-order-browser.test.ts)
  assert.match(openFn, /const stands = \(\): boolean => wrap\.isConnected && my === fetchSeq;/, "the landing's guard: the wrap connected and this fetch the newest");
  const standsAt = openFn.indexOf("if (!stands()) return;");
  assert.ok(standsAt >= 0 && standsAt < openFn.indexOf("URL.createObjectURL"), "no URL is minted for a viewer that is already gone");
  assert.doesNotMatch(openFn.slice(openFn.indexOf("const fetchFile = "), openFn.indexOf("URL.createObjectURL")), /document\.getElementById\("romp-fileview"\)/, "the landing never reads the viewer id: a replace-open moves it to the new viewer");
  // renderBody's img/PDF arm renders and returns — an <img>/iframe body has no honest text to
  // quote (affordance honesty: no real target, no affordance), so the mouseup seed gates off
  // RENDERED media too. The SVG SOURCE view is the deliberate exception — a text view, covered by
  // the media-gate test below.
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  const armAt = mediaBranch.indexOf("const shown = isPdf");
  assert.ok(armAt >= 0, "the img/PDF render arm exists");
  const renderedArm = mediaBranch.slice(armAt);
  assert.match(renderedArm, /body\.replaceChildren\(shown\);/, "…and the built element is what reaches the body");
  assert.match(mediaBranch, /imgBlock\(objUrl, path, imgFailed\)/);
  assert.match(VIEW, /if \(\(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\)\) return;/);
  // the romp loader holds the body until the bytes land (the loading-state rule)
  assert.match(mediaBranch, /if \(objUrl === null\) return;/);
  // the <img> itself: one element, src = the object URL, capped like the lightbox's image on BOTH
  // sheets (the viewer mounts in both documents — the .romp-acted precedent)
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.match(imgFn, /el\("img", "fileview-img"\)/);
  assert.match(imgFn, /img\.src = objUrl;/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) {
    assert.match(SHEET, /\.fileview-img \{[^}]*object-fit: contain[^}]*\}/);
    assert.match(SHEET, /\.fileview-imgbox \{/);
  }
});

// ── media gating is RENDERED-media gating (re-homed from the retired review layer's
// suite): the gate's rationale — "no honest text to quote" — is true of the img/PDF
// surfaces only. The SVG SOURCE view is codeBlock output, real text nodes, so a selection there
// seeds a labeled quote chip exactly as in any text view; a blanket media gate would make an
// .svg's XML unquotable. ──
test("the quote seed gates off RENDERED media only — the SVG Source view is a text view like any other", () => {
  // executed: the seed offer across the view states (the no-target gate holds throughout — a
  // reachable composer, own document or the chat's through the shell, is what makes a gesture; it
  // plays the role the old comment sink did: no real target, no gesture)
  const seedable = (target: boolean, isImage: boolean, isPdf: boolean, srcView: boolean): boolean =>
    target && !((isImage || isPdf) && !srcView);
  assert.equal(seedable(true, true, false, true), true, "SVG Source view: the selection seeds a chip");
  assert.equal(seedable(true, true, false, false), false, "the img view has no honest text to quote");
  assert.equal(seedable(true, false, true, false), false, "the PDF iframe owns its own surface");
  assert.equal(seedable(false, true, false, true), false, "no composer reachable still gates everything off");
  assert.equal(seedable(true, false, false, false), true, "plain text views are untouched");
  // source: the media arm of the gesture's gate carves out the Source view. Since Slice 1 of
  // plans/file-review.md it sits BEFORE the selection read and the seam's selection hooks, and the
  // no-target (composer) gate comes after the hooks — the hooks are how the comments panel's
  // floating Comment works in a Files pane with no chat pane anywhere (upstream gates on the
  // composer first; the through-the-shell test above pins the composer gate itself)
  const gesture = VIEW.split("const onSelect = (ev: Event) => {")[1].split("const seedTarget = composerWindow();")[0];
  assert.match(gesture, /if \(\(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\)\) return;/);
  assert.ok(gesture.indexOf("!(svgSource && svgText !== null)) return;") < gesture.indexOf("for (const cb of selHooks)"),
    "media is gated before any hook sees a selection");
  assert.match(gesture, /for \(const cb of selHooks\) \{ try \{ cb\(sel\); \}/, "the seam's hooks run before the composer gate");
  // anchoring reads the text THE VIEW SHOWS — the Source view's decoded XML, never the text
  // pipeline's null — so a quote on the XML earns its path:line label (viewText, pinned with the
  // fresh-read test above); renderBody's Source arm builds those text nodes through codeBlock
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  const srcArm = (mediaBranch.split("if (svgSource && svgText !== null) {")[1] || "").split("\n      }")[0];
  assert.ok(srcArm, "the Source-view arm exists inside the media branch");
  assert.match(srcArm, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\);/);
});

test("image mode hides Edit; Download, Copy path, GitHub, ✕ and the dir-link survive", () => {
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  // (Wrap needs no hiding — the toggle button is gone everywhere, its stored key pinned away above)
  // Edit was ALREADY gated on the kernel's text verdict — an image/* response sets isText false, so
  // the existing arm hides it; both halves stay pinned (file-edit.test.ts pins the isText line too)
  assert.match(VIEW, /isText = \(r\.headers\.get\("Content-Type"\) \|\| ""\)\.startsWith\("text\/plain"\)/);
  assert.match(VIEW, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtimeNs;/);
  // the media branch touches NONE of the keepers — they are built unconditionally before the fetch
  // (the dir-link rides the title bar, outside renderBody entirely)
  for (const keeper of ["dl.", "copy.", "close.", "gh."])
    assert.ok(!mediaBranch.includes(keeper), keeper + " must not be re-hidden for images");
  // markdown's Rendered/Raw segs exist only for .md files (the isMd gate, pinned above), and an .md
  // is never served image/* — so the segs cannot coexist with an image body by construction
});

test("SVG renders via <img> ONLY — never innerHTML, never an iframe: its scripts must never run", () => {
  // the kernel serves .svg as image/svg+xml on purpose (an <img> never runs SVG scripts — kernel.py's
  // preview comment), and the relay re-derives the type locally; the viewer must keep that surface
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.doesNotMatch(imgFn, /innerHTML/, "the XSS property: SVG bytes never become live DOM");
  assert.doesNotMatch(imgFn, /iframe/, "an iframed SVG is a document — scripts would run");
  assert.match(imgFn, /el\("img", "fileview-img"\)/);
  // THE MEDIA BRANCH ITSELF is the surface a mutation actually hits (a proven mutation: a
  // `body.innerHTML = svgText` swapped into the branch kept every test green — the innerHTML pin
  // above covers only imgBlock, and a codeBlock string pin matched its own commented-out corpse).
  // So the branch source is audited directly: no HTML-parsing sink of ANY kind, in code or comment.
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.ok(mediaBranch.length > 0, "media-branch anchors moved — re-anchor this extraction");
  assert.doesNotMatch(mediaBranch, /innerHTML/, "the XSS property, on the branch that holds the bytes");
  assert.doesNotMatch(mediaBranch, /insertAdjacentHTML/);
  assert.doesNotMatch(mediaBranch, /outerHTML|document\.write|DOMParser|createContextualFragment/);
  // …its only writes to the body element are replaceChildren of BUILT elements (the safe sink) —
  // a new sink added to the branch must show up here and be argued for
  const sinks = mediaBranch.match(/body\.\w+\s*[(=]/g) || [];
  assert.ok(sinks.length > 0 && sinks.every((s) => /^body\.replaceChildren\s*\($/.test(s)),
    "the media branch's only body writes are replaceChildren(...): " + JSON.stringify(sinks));
  // …and the Source toggle's codeBlock render — the same escape/highlight path every text file
  // takes (textContent / escapeHtml), never a parse into live DOM — is LIVE CODE, not a comment
  const live = mediaBranch.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
  assert.match(live, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\)/,
    "the SVG Source view renders through codeBlock, uncommented (born wrapped, like every code view)");
  assert.match(VIEW, /isSvgImage = ct === "image\/svg\+xml";/, "the toggle keys on the kernel's verdict too");
  assert.match(VIEW, /mediaBlob\.text\(\)/, "the source view decodes the SAME fetched bytes — no second request");
});

// executed: the object-URL lifecycle (the Escape-handler test's shape) — every teardown revokes
test("the object URL is revoked on close AND on replace-open — none leaks, one live at a time", () => {
  const sim = () => {
    let live: string | null = null;
    let seq = 0;
    const revoked: string[] = [];
    const dropMediaUrl = () => { if (live) { revoked.push(live); live = null; } };
    const openView = () => { dropMediaUrl(); live = "blob:" + ++seq; };  // replace-teardown, then the fetch lands
    const closeView = () => dropMediaUrl();
    openView();          // an image opens
    openView();          // Reload / a second click replaces it — blob:1 must go
    closeView();         // ✕ — blob:2 must go
    return { revoked, live };
  };
  const r = sim();
  assert.deepEqual(r.revoked, ["blob:1", "blob:2"], "the replaced URL AND the closed URL both go");
  assert.equal(r.live, null, "nothing outlives the viewer");
  // replica ↔ source: ONE module-level registration, dropped by BOTH exits (the editHooks/gitHooks/
  // onKeyLive precedent), revoking through URL.revokeObjectURL
  assert.match(VIEW, /let mediaUrlLive: string \| null = null;/);
  assert.match(VIEW, /URL\.revokeObjectURL\(mediaUrlLive\)/);
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /dropMediaUrl\(\);/, "close revokes");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /dropMediaUrl\(\);/, "the replace path revokes (the conflict Reload re-opens through here)");
  assert.ok(openFn.indexOf("dropMediaUrl();") < openFn.indexOf('document.getElementById("romp-fileview")?.remove();'),
    "…before the old viewer is torn down, beside the other module-level drops");
  assert.match(openFn, /mediaUrlLive = objUrl;/, "the minted URL is exactly what the teardowns revoke");
});

test("an oversize image lands on the kernel's words + Download — a 413 never reaches the media branch", () => {
  // executed: the pipeline model — !ok throws (status attached) BEFORE any Content-Type branching
  const route = (ok: boolean, ct: string): "error" | "img" | "pdf" | "text" => {
    if (!ok) return "error";
    return ct.startsWith("image/") ? "img" : ct.startsWith("application/pdf") ? "pdf" : "text";
  };
  assert.equal(route(false, "text/plain"), "error",
    "the kernel 413s an oversize image with a text/plain body naming the size and the cap");
  assert.equal(route(true, "image/png"), "img");
  const offersDownload = (status: number | undefined): boolean => status === 413 || status === 415;
  assert.equal(offersDownload(413), true, "…and the error pane still offers the Download the view could not be");
  // source ordering: the throw sits before the media flags are ever assigned
  assert.ok(VIEW.indexOf("if (!r.ok) return r.text().then((t) => {")
            < VIEW.indexOf('isImage = ct.startsWith("image/");'));
});

test("a PDF takes the lightbox's exact iframe treatment, aimed at the already-fetched blob", () => {
  const PREVIEW = web("preview.ts");
  // the reference: openLightbox's pdf arm is a PLAIN iframe — className, src, title, no sandbox
  // attributes to mirror or forget
  assert.match(PREVIEW, /frame\.className = "romp-lightbox-frame";\s*\n\s*frame\.src = fileUrl\(path, sid\);\s*\n\s*frame\.title = path;/);
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.match(pdfFn, /el\("iframe", "fileview-frame"\)/);
  assert.match(pdfFn, /frame\.src = objUrl;/, "the blob URL — the bytes were already fetched once");
  assert.match(pdfFn, /frame\.title = path;/);
  assert.doesNotMatch(pdfFn, /sandbox/, "the lightbox sets none; inventing one here would be a different surface");
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.match(mediaBranch, /isPdf \? pdfBlock\(objUrl, path\) : imgBlock\(objUrl, path, imgFailed\)/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) assert.match(SHEET, /\.fileview-frame \{[^}]*height: 100%/);
});

// ── decode failure: a zero-byte or mid-write/truncated image is a 200 whose BYTES will not decode —
// the browser fires the img's error event and used to leave its mute broken-image glyph: no reason,
// no way out. The viewer answers with the 413/415 pane idiom instead: plain words naming what
// happened, the path, and the Download the view could not be. The img's own error event is the
// exact deciding signal (never a timer, never a byte sniff). The PDF iframe has NO equivalent
// failure event — the browser's own viewer owns that surface and reports inside it — so this
// covers images only, deliberately. ──

test("an image 200 that fails to DECODE swaps to the failure pane: plain words + Download, never a mute glyph", () => {
  // executed: the handler's continuation — an object URL of garbage bytes fires `error` once, and
  // the pane replaces the glyph; a decodable image never invokes it
  const sim = (decodes: boolean) => {
    let pane: string[] = [];
    let armed: (() => void) | null = null;
    const imgBlock = (onDecodeFail: () => void): string => { armed = onDecodeFail; return "img"; };
    const imgFailed = () => { pane = ["this image failed to decode: it may be mid-write or truncated", "Download"]; };
    pane = [imgBlock(imgFailed)];              // the media branch renders the img, handler armed
    if (!decodes) armed!();                    // garbage bytes: the browser fires the img's error event
    return pane;
  };
  assert.deepEqual(sim(true), ["img"], "a decodable image just shows");
  assert.deepEqual(sim(false),
    ["this image failed to decode: it may be mid-write or truncated", "Download"],
    "garbage bytes land on words + the way out");
  // source: the handler rides the img itself, armed BEFORE src so no event can slip past it
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.match(imgFn, /^\(objUrl: string, path: string, onDecodeFail: \(\) => void\)/);
  assert.match(imgFn, /img\.addEventListener\("error", onDecodeFail, \{ once: true \}\);\s*\n\s*img\.src = objUrl;/);
  // …and the continuation builds the EXACT failure idiom the 413/415 catch renders: fileview-err
  // words + the path hint + the fileview-err-dl Download wired through startDownload
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const failFn = (openFn.split("const imgFailed = ")[1] || "").split("\n  };")[0];
  assert.ok(failFn, "imgFailed lives in the open viewer's closure — it needs body and dlUrl");
  assert.match(failFn, /el\("div", "fileview-err"\)/);
  assert.match(failFn, /why\.textContent = DECODE_FAILED;/, "the sentence is the exported constant (hoisted in the Slice 7 review's round 1 for the guide's pin)");
  assert.match(VIEW, /\nexport const DECODE_FAILED = "this image failed to decode: it may be mid-write or truncated";\n/, "its export line, the words the guide's pin reads");
  assert.match(failFn, /el\("div", "fileview-err-hint"\)/);
  assert.match(failFn, /hint\.textContent = path;/);
  assert.match(failFn, /el\("button", "fileview-btn fileview-err-dl"\)/);
  assert.match(failFn, /startDownload\(dlUrl, offer\)/);
  assert.match(failFn, /body\.replaceChildren\(why\);/);
  // a decode failure that settles after the viewer was closed or replaced paints nothing
  assert.match(failFn, /if \(!wrap\.isConnected\) return;/);
  // the PDF arm stays bare — an iframe fires no decode-failure event to key on
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.doesNotMatch(pdfFn, /addEventListener/, "no synthetic failure signal invented for the iframe");
});

// executed: the gutter is a SIBLING of the code, so selecting the code copies it without line numbers
test("the line gutter numbers every line and drops a trailing newline's phantom line", () => {
  const lines = (text: string): string[] => {
    const l = text.split("\n");
    if (l.length && l[l.length - 1] === "") l.pop();
    return l;
  };
  assert.deepEqual(lines("a\nb\nc\n").length, 3, "a trailing newline is not a fourth line");
  assert.deepEqual(lines("a\nb\nc").length, 3);
  assert.deepEqual(lines(""), []);
  assert.match(VIEW, /gutter\.textContent = lines\.map\(\(_, i\) => String\(i \+ 1\)\)\.join\("\\n"\);/);
  assert.match(VIEW, /wrap\.appendChild\(gutter\); wrap\.appendChild\(pre\);/, "sibling, not inside the pre");
  assert.match(FEED_CSS, /\.fileview-gutter \{[\s\S]*?user-select: none;/);
  assert.match(CHAT_CSS, /\.fileview-gutter \{[\s\S]*?user-select: none;/);
});

// ── the session chip (the user 2026-09-03): the title bar names the session the file was opened
// from. The viewer knows only a sid — and its openers mostly know no more (the relay branch and the
// conflict Reload live inside this module, the file browser hands over a bare sid) — so the identity
// is RESOLVED from the sid through a lookup each hosting document registers once at boot. The DOM
// build itself runs for real in fileview-chip.test.ts; these are the source pins. ──

test("the title bar carries a session chip resolved from the sid — never invented, absent when unknown", () => {
  assert.match(VIEW, /import \{ hostOf, bareId, hostNameNodes \} from "\.\/host-prefix";/);
  assert.match(VIEW, /export interface FileViewIdentity \{ name: string; color: \{ bg: string; fg: string \} \| null \}/);
  assert.match(VIEW, /let identityOf: \(sid: string\) => FileViewIdentity \| null = \(\) => null;/,
    "unregistered → nothing to show, not a guess");
  assert.match(VIEW, /export function setFileViewIdentity\(fn: typeof identityOf\): void \{ identityOf = fn; \}/);
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /const owner = sid \? identityOf\(sid\) : null;/, "no sid → the resolver is not even asked");
  assert.match(openFn, /if \(owner\) \{\n\s*sess = el\("span", "fileview-sess"\);/, "no identity → no chip element at all");
  assert.match(openFn, /sess\.replaceChildren\(\.\.\.hostNameNodes\(owner\.name, sid\)\);/, "host: quiet for a remote session");
  assert.match(openFn, /if \(owner\.color\) \{ sess\.style\.background = owner\.color\.bg; sess\.style\.color = owner\.color\.fg; \}/,
    "the session's identity colour, inline — an uncolored stub keeps the sheet's neutral pill");
  assert.match(openFn, /sess\.title = "Opened from the " \+ owner\.name \+ " session";/,
    "capitalized like this bar's other tooltips; 'session' so a name like web is not read as a place");
  assert.match(openFn, /bar\.appendChild\(name\); if \(sess\) bar\.appendChild\(sess\); bar\.appendChild\(acts\);/,
    "between the path and the actions");
  // the signatures every opener and the relay pin depend on are as they were, plus the optional opts:
  // todoId provenance (plans/file-review.md Slice 0: the Waiting-on-you detail link) and `at`, where the open lands
  // (Slice 6 of plans/markdown-viewer.md, item 4: a line, a source offset or a heading; the former `line` and `frag`
  // options are two of its arms, replaced, not aliased, and upstream's T351 `frag` is the heading arm); every existing
  // caller moved with it (file-view-seam.test.ts)
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null; at\?: At \| null; place\?: RememberedPlace \| null \}\): boolean \{/);
  // (the optional onRelay — the Files pane's own relay contract, 2026-09-03 — leaves the poster's shape alone)
  // The host's onLeave (Slice 6 of plans/markdown-viewer.md, item 3) hands the pane the reader's place in a file as they
  // leave it, which the pane hands back as the open's `place`.
  assert.match(VIEW, /export function initFileView\(poster: \(m: Record<string, unknown>\) => void,\n\s*onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown; todoId\?: unknown; at\?: unknown \}\) => void,\n\s*host\?: \{ openFile\?: \(path: string, sid: string \| null, at: At \| null\) => void; onLeave\?: \(path: string, sid: string \| null, rec: RememberedPlace\) => void \}\): void \{/);
});

test("both hosting documents register a resolver beside their initFileView boot", () => {
  // the chat document: the tab set, the way renderTabs names a tab (the session first, then the
  // kernel's tab meta, which keeps a dormant session's name and colour)
  assert.match(RENDER, /import \{ initFileView, setFileViewIdentity, hostStub \} from "\.\/file-view";/);
  assert.match(RENDER, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);\n(\/\/.*\n)*setFileViewIdentity\(\(id\) => \{\n\s*const s = sessions\.get\(id\) \?\? tabMeta\.get\(id\);\n\s*return s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : hostStub\(id\);\n\}\);/);
  // the feed document: its session list (the same tab set, relayed per frame), else a card carrying
  // the session's name and colour — never sessionColors, which is keyed by NAME, not sid
  assert.match(FEED, /import \{ initFileView, setFileViewIdentity, hostStub \} from "\.\/file-view";/);
  assert.match(FEED, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);.*\n(\/\/.*\n)*setFileViewIdentity\(\(id\) => \{\n\s*const s = sessionsMeta\.find\(\(x\) => x\.sid === id\) \?\? asks\.find\(\(a\) => a\.sid === id\);\n\s*return s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : hostStub\(id\);\n\}\);/);
  const feedReg = FEED.split("setFileViewIdentity(")[1].split("});")[0];
  assert.doesNotMatch(feedReg, /sessionColors/, "a name-keyed index cannot answer a sid");
});

// executed: the ladder each document's resolver runs — its own lists, then the kernel's
// _peer_identity fallback (a remote sid's host + the sid's first 8 characters, uncolored), then no
// chip at all. Synthetic rows: the notes-api world, TESTHOST for the remote kernel.
test("resolver ladder: a named session, then a host-prefixed 8-char stub, then no chip", () => {
  type Id = { name: string; color: { bg: string; fg: string } | null };
  const hostOf = (id: string) => { const i = id.indexOf(":"); return i > 0 ? id.slice(0, i) : ""; };
  const bareId = (id: string) => { const i = id.indexOf(":"); return i > 0 ? id.slice(i + 1) : id; };
  const hostStub = (sid: string): Id | null => {
    const bare = bareId(sid);
    if (!bare) return null;
    const host = hostOf(sid);
    return { name: (host ? host + ":" : "") + bare.slice(0, 8), color: null };
  };
  const WEB = "11111111-2222-3333-4444-555555555555";
  const API = "22222222-3333-4444-5555-666666666666";
  const TESTS = "33333333-4444-5555-6666-777777777777";
  const rows = new Map<string, Id>([
    [WEB, { name: "web", color: { bg: "#3a7bd5", fg: "#ffffff" } }],
    ["TESTHOST:" + API, { name: "TESTHOST:api", color: { bg: "#d53a7b", fg: "#ffffff" } }],   // federation prefixes sid AND name
    [TESTS, { name: "", color: null }],                                                        // a placeholder tab, name not yet known
  ]);
  const resolve = (id: string): Id | null => {
    const s = rows.get(id);
    return s && s.name ? { name: s.name, color: s.color ?? null } : hostStub(id);
  };
  assert.deepEqual(resolve(WEB), { name: "web", color: { bg: "#3a7bd5", fg: "#ffffff" } });
  assert.deepEqual(resolve("TESTHOST:" + API), { name: "TESTHOST:api", color: { bg: "#d53a7b", fg: "#ffffff" } },
    "a remote row keeps its host: prefix — hostNameNodes renders it as quiet metadata");
  assert.deepEqual(resolve("44444444-5555-6666-7777-888888888888"), { name: "44444444", color: null },
    "an unknown local sid → the kernel's 8-character stub, uncolored");
  assert.deepEqual(resolve("TESTHOST:44444444-5555-6666-7777-888888888888"), { name: "TESTHOST:44444444", color: null },
    "an unknown remote sid → host: + stub, so the host still reads as metadata");
  assert.deepEqual(resolve(TESTS), { name: "33333333", color: null },
    "a row with no name yet is not a name — the stub, never an empty chip");
  assert.equal(resolve(""), null, "no sid → no chip");
  assert.equal(resolve("TESTHOST:"), null, "a host with no sid names nothing");
  // replica ↔ source
  assert.match(VIEW, /export function hostStub\(sid: string\): FileViewIdentity \| null \{\n\s*const bare = bareId\(sid\);\n\s*if \(!bare\) return null;\n\s*const host = hostOf\(sid\);\n\s*return \{ name: \(host \? host \+ ":" : ""\) \+ bare\.slice\(0, 8\), color: null \};\n\}/);
});

test("the chip's dress is in BOTH sheets: a fixed-width pill that never yields to the path", () => {
  for (const css of [CHAT_CSS, FEED_CSS]) {
    // A BLOCK container, not inline-flex: text-overflow acts on block containers only — on a flex container
    // the text sits in an anonymous flex item the property cannot reach, and an over-long name hard-clipped
    // at max-width (the review of #970). 0.82em of --fs, the size the bar's buttons wear, so the chip scales
    // with its neighbours; a px value did not.
    assert.match(css, /\.fileview-sess \{ flex: 0 0 auto; display: block; max-width: 38%;[^}]*font-size: 0\.82em;[^}]*overflow: hidden; white-space: nowrap; text-overflow: ellipsis;/);
    const sess = css.slice(css.indexOf(".fileview-sess {"), css.indexOf("}", css.indexOf(".fileview-sess {")));
    assert.doesNotMatch(sess, /inline-flex|align-items|font-size: [\d.]+px/, "no flex container around the text, no px size");
    // color:inherit so the host: token takes the pill's own fg — the global .host-prefix{color:var(--dim)}
    // otherwise wins over the inline foreground and the token is near-invisible on a coloured pill
    // (~1:1 contrast for a remote session's chip). opacity keeps it quiet without dimming to gray.
    assert.match(css, /\.fileview-sess \.host-prefix \{ color: inherit; opacity: 0\.75; \}/, "the host: token uses the pill's fg, quiet");
  }
});

// ── the window stand-ins are projections (ui/test-dom-shim.ts): a failing assertion dumps a window's own primitives, never its parent chain ──
test("a window stand-in enumerates no parent edge, and a dump of it names neither the parent nor its document", () => {
  const shell = { document: { getElementById: () => null } };
  for (const n of [unframedWindow(), framedWindow(shell), framedWindow({ get document() { throw new Error("cross-origin"); } })]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable(n[k])), "a window stand-in keeps an enumerable edge: " + Object.keys(n).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parent") && !dump.includes("document"), "a window stand-in dumps its parent chain:\n" + dump);
  }
  const self = unframedWindow();
  assert.ok(self.parent === self && framedWindow(shell).parent === shell, "the parent is still reachable: itself when unframed, the shell when framed");
});

test("source: where an open lands (Slice 6 of plans/markdown-viewer.md, item 4): the At union and readAt's three arms; the delegate hands a path link's line or fragment on as `at`; the offset is spent at the first text landing and scrolled the next frame, the block centred in Rendered through the anchor map's table and the row in Raw through the seam's scrollToOffset, an offset past the end saying so; a missing heading says so", () => {
  assert.match(VIEW, /export type At = \{ line: number \} \| \{ offset: number \} \| \{ heading: string \};/);
  assert.match(VIEW, /export function readAt\(x: unknown\): At \| null \{\n\s*if \(!x \|\| typeof x !== "object"\) return null;\n\s*const o = x as Record<string, unknown>;\n\s*if \(typeof o\.line === "number" && Number\.isInteger\(o\.line\) && o\.line > 0\) return \{ line: o\.line \};\n\s*if \(typeof o\.offset === "number" && Number\.isInteger\(o\.offset\) && o\.offset >= 0\) return \{ offset: o\.offset \};\n\s*if \(typeof o\.heading === "string" && o\.heading\) return \{ heading: o\.heading \};\n\s*return null;\n\}/,
    "validated at the receiver: the message crossed a frame boundary");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /const at: At \| null = opts\?\.at \?\? null;/);
  assert.match(openFn, /openLinkedFile\(p, sid \|\| null, ln > 0 \? \{ line: ln \} : x\.dataset\.frag \? \{ heading: x\.dataset\.frag \} : null\);/, "the body's delegate: data-line as { line }, data-frag as { heading }, a bare path as null");
  assert.match(openFn, /let pendingOffset: number \| null = at !== null && "offset" in at && at\.offset >= 0 \? Math\.floor\(at\.offset\) : null;/);
  assert.match(openFn, /renderBody\(\);\n(?:\s*\/\/[^\n]*\n)*\s*if \(notUtf8 && !latin1LineStands\(\)\) noteBar\(LATIN1_NOTICE\);\n\s*landTarget\(\);/, "the landing spends the target and takes the keyboard through one gate over a body with a box (review round 5); the Latin-1 line's raise stands between the paint and the spend (Slice 7, item 5), guarded by the standing line (the review's round 1)");
  assert.match(openFn, /const landTarget = \(\): void => \{\n\s*if \(unmeasurable\(\)\) return;\n\s*if \(pendingLine !== null\) \{ const n = pendingLine; pendingLine = null; scrollToLine\(n\); \}\n\s*if \(pendingOffset !== null\) \{ const n = pendingOffset; pendingOffset = null; requestAnimationFrame\(\(\) => \{ if \(wrap\.isConnected\) scrollToSourceOffset\(n\); \}\); \}\n\s*if \(pendingHeading !== null && \(!isMd \|\| fmt\.md === "rendered"\)\) spendHeading\(\);\n\s*keyboardOnLanding\(\);\n\s*\};/,
    "spent at the landing like the line, scrolled the next frame (the heading landing's timing), before the keyboard");
  const sso = openFn.slice(openFn.indexOf("const scrollToSourceOffset = "), openFn.indexOf("let pendingOffset"));
  assert.match(sso, /if \(n > src\.length\) noteBar\("Offset " \+ n \+ " is past the end of this file, which has " \+ src\.length \+ \(src\.length === 1 \? " character" : " characters"\) \+ "; showing the last " \+ \(rendered \? "block\." : "line\."\)\);/, "the line rule's shape");
  assert.match(sso, /if \(!rendered\) \{ ctx\.scrollToOffset\(at\); return; \}/, "Raw: the seam's own row mapping");
  assert.match(sso, /const spans = sourceBlockSpans\(src\);[\s\S]*const held = blockHolding\(spans, at\);[\s\S]*renderedBlockElements\(md, src, k\)\[0\];[\s\S]*revealFragmentTarget\(target\);[^\n]*\n(?:\s*if \(own && target\.localName === "details"[^\n]*\n)?\s*target\.scrollIntoView\(\{ block: "center" \}\);/, "Rendered: the block table, the reader's place's reading of it, the paired element, a fold above it opened (and the block's own fold since review round 2), centred");
  assert.match(VIEW, /import \{ sourceBlockSpans, renderedBlockElements \} from "\.\/anchor-map";/);
  assert.match(VIEW, /import \{ readPlace, seatPlaceOutcome, followPlace, blockHolding, blockIndexAt, type Place \} from "\.\/reader-place";/, "followPlace: the boxless leave follows the last measured place into the text a reload landed under the hide (the review's round 6)");
  assert.match(openFn, /if \(!wrap\.isConnected \|\| scrollToFragment\(body, h\)\) return;\n(?:\s*\/\/[^\n]*\n)*\s*if \(sectionHidden\(body, h\)\) \{ noteBar\(HIDDEN_SECTION\); return; \}\n(?:\s*\/\/[^\n]*\n)*[\s\S]{0,300}noteBar\('No section named "' \+ shown \+ '" in this file\.'\);/, "a heading the note lacks: the notice, never a silent open at the top; one it has under a plain hidden wrapper, which scrollToFragment lands nothing on: the ruled words (the PR review's round 1)");
  assert.doesNotMatch(openFn, /opts\?\.frag|opts\.line|pendingFrag/, "the former options are gone, not aliased");
});

test("source: changed on disk (Slice 6 of plans/markdown-viewer.md, item 5): the probe's HEAD through the panel's two readings, its listeners on the window's focus and the document's visibilitychange, registered as probeLive and dropped by both exits and the URL view's replace; the bar's words and its Reload through fetchFile; a landing settles the bar and the failure landing re-arms its own button; no timer anywhere in it", () => {
  assert.match(VIEW, /import \{ headVerdict, mtimeMoved, ABSENT \} from "\.\/file-comments-model";/, "the panel's pure readings, imported as they are (not the poll, not its stopped set), and its token for a 404 (the bar's deletion words; the PR review's round 1)");
  assert.match(VIEW, /export const CHANGED_ON_DISK = "Changed on disk\.";/, "the bar's words (C4)");
  assert.match(VIEW, /let probeLive: \(\(\) => void\) \| null = null;\nfunction dropProbe\(\): void \{\n\s*if \(probeLive\) \{ const f = probeLive; probeLive = null; f\(\); \}\n\}/, "one live probe, the onKey idiom");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const probe = openFn.slice(openFn.indexOf("let probeOut = false;"), openFn.indexOf("// The fetch pipeline, as a function:"));
  assert.match(probe, /if \(takingKeyboard \|\| probeOut \|\| probeStopped \|\| editing \|\| !mtimeNs \|\| !wrap\.isConnected \|\| document\.hidden\) return;[^\n]*\n\s*probeOut = true;/, "the gate: not the viewer's own focus call (a cross-frame open's landing fires the window's focus inside body.focus(); review round 1), one in flight, not retired, no editor, a fetched file, the viewer up, the document visible");
  assert.match(openFn, /if \(a && a !== document\.body && !bar\.contains\(a\)\) return;\n\s*if \(typingInPeerFrame\(\)\) return;\n\s*takingKeyboard = true;\n\s*const opts: FocusOptions & \{ focusVisible: boolean \} = \{ preventScroll: true, focusVisible: ring \?\? \(a === null \|\| a === document\.body \? ringWithNoHolder\(\) : ringOf\(a\)\) \};\n\s*try \{ body\.focus\(opts\); \} finally \{ takingKeyboard = false; \}/, "takeKeyboard's gate reads this document's holder, then the focused sibling frame's (review round 2: the chat composer beside a Files iframe), marks its own focus call for the probe's gate, and names the ring through focusVisible from the holder it takes the keyboard from, the ring a closer read before removing that holder (review round 3: Chromium's script-focus heuristic framed the note on every pointer open), or, with no holder, the kind of this document's last press (review round 4: Enter on a file browser row, whose rows are not focusable, lost the ring)");
  assert.match(VIEW, /function ringOf\(a: Element \| null\): boolean \{\n\s*if \(a === null \|\| a === document\.body\) return false;\n\s*try \{ return a\.matches\(":focus-visible"\); \} catch \{ return false; \}\n\}/, "ringOf, module-level since review round 4 (the replace path reads it before the old card goes): no holder or the document's body wears no ring; a matches() without the selector reads none");
  assert.match(VIEW, /function ringInOld\(old: Element \| null\): boolean \| null \{\n\s*const a = document\.activeElement;\n\s*return old && a && old\.contains\(a\) \? ringOf\(a\) : null;\n\}/, "the ring of a holder inside the card a replace-open removes; null when the holder is elsewhere or there is none");
  assert.match(openFn, /closeAsks = \[\];\n\s*const priorRing = ringInOld\(document\.getElementById\("romp-fileview"\)\);[^\n]*\n\s*runLeave\(\);/, "read once the close guard has passed and BEFORE the removal and every step that could move the focus (review round 4: Enter on a Tab-focused path link in the note replaced the viewer, and the link was gone at the landing, so the new body got no ring)");
  assert.match(openFn, /const keyboardOnLanding = \(\): void => \{ if \(!keyboardPending\) return; keyboardPending = false; takeKeyboard\(priorRing \?\? undefined\); \};/, "the open's first landing passes the removed holder's ring when there was one, else takeKeyboard reads its own");
  assert.match(VIEW, /let lastInputKey = false;\n(?:[^\n]*\n){0,2}function watchInputKind\(\): void \{\n\s*document\.addEventListener\("keydown", \(e: KeyboardEvent\) => \{ if \(!MODIFIER_KEYS\.has\(e\.key\)\) lastInputKey = true; \}, true\);\n\s*document\.addEventListener\("pointerdown", \(\) => \{ lastInputKey = false; \}, true\);\n\}/, "the kind of the document's last press, on the two events themselves (a modifier alone is no key press); no timer, no flag set by the viewer's own code");
  assert.match(VIEW, /function ringWithNoHolder\(\): boolean \{\n\s*if \(!lastInputKey\) return false;\n\s*try \{ return typeof document\.hasFocus !== "function" \|\| document\.hasFocus\(\); \} catch \{ return false; \}\n\}/, "a key, and this document holding the page's focus (a relayed open's click was in another frame, whose press this record never saw)");
  assert.match(VIEW, /window\.addEventListener\("pagehide", \(\) => \{ if \(leaveLive\) leaveLive\(\); \}\);\n\s*watchInputKind\(\);/, "installed once by initFileView beside the module's other document listeners");
  assert.match(openFn, /const ring = held && ringOf\(a\);[^\n]*\n\s*pop\.remove\(\);[\s\S]{0,120}if \(held\) takeKeyboard\(ring\);/, "the Outline's closer reads the ring off the popover or the button before the removal and passes it");
  assert.match(openFn, /diskBar\.ring = diskBar\.held && ringOf\(document\.activeElement\);/, "the disk bar's Reload records the ring at the click, before the disable drops the focus");
  assert.match(probe, /fetch\(fileUrl\(path, sid\), \{ method: "HEAD", cache: "no-store" \}\)\.then\(\(r\) => \{\n\s*const v = headVerdict\(r\.status, r\.headers\.get\("X-Romp-Mtime-Ns"\)\);\n\s*if \(v\.kind === "stop"\) \{ probeStopped = true; return; \}/, "the same URL the GET used, read as the poll reads its own; a 413/415 retires it");
  assert.match(probe, /const moved = v\.value;\n\s*if \(!mtimeMoved\(mtimeNs, moved\)\) return;/, "a string compare, the contract the panel and the save fence keep");
  assert.match(probe, /const was = mtimeNs;[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*raiseHold\.defer\(\(\) => \{\n\s*const go = \(\): void => \{ if \(!editing && wrap\.isConnected && mtimeNs === was\) raiseDiskBar\(words\); \};\n\s*const landing = parkedLanding;[^\n]*\n\s*if \(landing\) void landing\.then\(go\); else go\(\);\n\s*\}\);/, "the raise waits out a press on the body row and re-checks its guards at the release (review round 3: a raise mid-drag moved the body under the pointer and the selection ended on other text), after a landing parked under the same press has settled (round 5: the row's hold released first and the raise inserted a bar the landing then removed); the guard is that the body still shows the file the HEAD compared against, any landing since making the HEAD's evidence stale (round 6: a parked landing that brought a second write, newer than the HEAD's answer, read as moved against that answer and raised a false bar over the newest file)");
  assert.match(openFn, /const parked = hold\.held\(\);\n\s*const p = hold\.defer\(\(\) => run\(parked\)\);\n\s*if \(parked\) noteParkedLanding\(p\);/, "a landing the card's hold parks is the one the raise waits for, and the run is told it was parked (the PR review's round 2: the Outline's re-open after a parked landing's paint reads it)");
  assert.match(openFn, /const raiseHold = pressHold\(main\);/, "a hold of its own, on the body ROW the bar is inserted above (the body and the Comments aside): the landing's parks one run at a time, and a raise must never displace a parked landing (review round 4: held on the body alone, a press on a card's head or a drag in the reply box in the aside had the bar land under it, the click lost and the drag selecting nothing)");
  assert.equal((openFn.match(/const hold = pressHold\(box\);/g) || []).length, 1, "the landing's hold is on the CARD (the PR review's round 1: the Outline popover is a card child outside the body, and a landing under a press on one of its rows painted at once and removed the pressed row before the mouseup, the pick lost)");
  assert.equal((openFn.match(/pressHold\(body\)/g) || []).length, 0, "…and no longer on the body alone");
  assert.ok(openFn.indexOf("const raiseHold = pressHold(main);") > openFn.indexOf('const main = el("div", "fileview-main");'), "the row exists when the hold takes it");
  assert.match(probe, /\.catch\(\(\) => \{[^\n]*\}\)\n\s*\.finally\(\(\) => \{ probeOut = false; \}\);/, "a network failure says nothing; the flight ends either way");
  assert.match(probe, /window\.addEventListener\("focus", onWindowFocus\);\n\s*document\.addEventListener\("visibilitychange", onVisibility\);\n\s*probeLive = \(\) => \{ window\.removeEventListener\("focus", onWindowFocus\); document\.removeEventListener\("visibilitychange", onVisibility\); \};/, "the two events, registered for the exits");
  assert.match(probe, /const onVisibility = \(\): void => \{ if \(!document\.hidden\) probe\(\); \};/, "to visible only");
  assert.match(probe, /const raiseDiskBar = \(words: string\): void => \{\n\s*if \(diskBarUp\(\)\) return;[^\n]*\n\s*const bar2 = noteBar\(words\);/, "the one notice row, the conflict bar's shape, with the verdict's words (the PR review's round 1: a 404 is a deletion)");
  assert.match(probe, /const words = moved === ABSENT && r\.headers\.get\(REASON_HEADER\) === REASON_MISSING \? DELETED_ON_DISK : CHANGED_ON_DISK;[^\n]*\n\s*const was = mtimeNs;/, "the words are read off the HEAD's verdict AND the kernel's reason: a 404 says deleted only when the header says the file is gone (the PR review's round 2: the route also 404s a re-aimed relative path and a detached host), any other move says changed");
  assert.match(VIEW, /export const REASON_HEADER = "X-Romp-Reason";\nexport const REASON_MISSING = "missing";/, "the kernel's one-word cause: the header, and the one value that means gone");
  assert.match(probe, /raiseDiskBar\(words\); \};/, "the release's raise carries them");
  assert.match(VIEW, /export const DELETED_ON_DISK = "Deleted on disk\.";/, "the deletion's words, the manager's");
  assert.match(VIEW, /import \{ headVerdict, mtimeMoved, ABSENT \} from "\.\/file-comments-model";/, "the model's own token for a 404, not a string of the viewer's");
  assert.match(openFn, /else if \(diskBar && diskBar\.under === mtimeNs && mtimeNs\) raiseDiskBar\(diskBar\.words\);/, "the editor's exit re-raises the bar with the words it had");
  assert.match(probe, /re\.type = "button"; re\.textContent = "Reload";/);
  assert.match(probe, /re\.disabled = true; re\.textContent = "Reloading";[^\n]*\n\s*fetchFile\(\);\n\s*diskBar\.asked = fetchSeq;/, "acknowledged at the click; the reload is fetchFile, which keeps the place; its landing is remembered");
  assert.match(probe, /const ownAsk = \(my: number\): boolean => diskBar !== null && diskBar\.asked > 0 && my >= diskBar\.asked;\n\s*const settleDiskBar = \(my: number\): void => \{\n\s*if \(diskBar && \(mtimeMoved\(diskBar\.under, mtimeNs\) \|\| ownAsk\(my\)\)\) dropDiskBar\(\);/, "the clearing event: a landing under another mtime, or the bar's own ask's landing, which any newer fetch's landing stands for once it overtook the ask (review round 2: the overtaken bar dead-ended at Reloading over the poll's 404 pane)");
  assert.match(probe, /diskBar\.held = bar2\.contains\(document\.activeElement\);[^\n]*\n\s*diskBar\.ring = diskBar\.held && ringOf\(document\.activeElement\);[^\n]*\n\s*re\.disabled = true; re\.textContent = "Reloading";/, "who holds the keyboard is read at the click, BEFORE the disable, and whether with the ring (a browser drops the focus off a disabled control at once; review round 1: read at the landing it was always the document's body; review round 3: the ring for the landing's hand-over)");
  assert.match(probe, /const held = diskBar!\.held \|\| diskBar!\.el\.contains\(document\.activeElement\);\n\s*const ring = diskBar!\.ring \|\| ringOf\(document\.activeElement\);[^\n]*\n\s*diskBar!\.el\.remove\(\); note = null;\n\s*if \(held\) takeKeyboard\(ring\);/, "the drop: the keyboard the bar's Reload held at its click goes to the body, with the ring the click recorded or a holder still in the bar wears (the brief's call-site list named the button; review round 3)");
  assert.match(probe, /const d = diskBar;\n\s*if \(!d \|\| !ownAsk\(my\) \|\| !diskBarUp\(\)\) return;/, "the re-arm answers the bar's ask or a newer fetch's failure, while the bar stands");
  assert.match(probe, /if \(d\.held && keyboardIdle\(\)\) d\.btn\.focus\(\{ preventScroll: true \}\);/, "a failed Reload puts the click's keyboard back on the re-armed button only while nothing holds it (review round 2: it took the keyboard from a box the reader had moved to during the flight, and Space fired Reload again)");
  assert.match(openFn, /const keyboardIdle = \(\): boolean => \{ const a = document\.activeElement; return \(a === null \|\| a === document\.body\) && !typingInPeerFrame\(\); \};/, "idle: this document's body or nothing, and no box being typed in a sibling frame");
  assert.match(openFn, /isSvgImage = got\.isSvgImage; textBytes = got\.bytes;\n\s*settleDiskBar\(my\);/, "right after the landing applies the mtime, text and media alike (the byte count with them since the review's round 1)");
  assert.match(openFn, /body\.replaceChildren\(why\);\n\s*syncOutline\(\);[^\n]*\n\s*viewError = msg;[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*rearmDiskBar\(my\);/, "the failure landing fires the seam's hooks after the pane's paint and the Outline sync (Slice 7 of plans/markdown-viewer.md, item 3: error() set first, so a hook reads the pane's words) and re-arms the bar's own button AFTER both (review round 3: read before the paint, an element of the old body's content the reader had focused during the flight stood the re-arm down, and the paint's removal then left the keyboard on the document's body; the hooks move no keyboard, so the re-arm still reads it last)");
  assert.doesNotMatch(openFn, /rearmDiskBar\(my\);[^\n]*\n\s*(?:viewError = msg;|fireRendered\(\);)/, "never the hooks after the re-arm");
  assert.doesNotMatch(openFn, /rearmDiskBar\(my\);[^\n]*\n\s*const why = el\("div", "fileview-err"\);/, "never before the pane");
  assert.doesNotMatch(probe, /setTimeout|setInterval|requestAnimationFrame/, "no timer: the events are the reader's return, the answer and the landing");
  // the exits: closeFileView, the replace path, openUrlView's replace, each right after dropOnKey
  const closeFn = VIEW.split("export function closeFileView")[1].split("\n}\n")[0];
  assert.ok(closeFn.indexOf("dropProbe();") > closeFn.indexOf("dropOnKey();") && closeFn.indexOf("dropOnKey();") >= 0, "closeFileView drops the probe after the Escape handler");
  assert.ok(openFn.indexOf("dropProbe();") > openFn.indexOf("dropOnKey();") && openFn.indexOf("dropProbe();") < openFn.indexOf('document.getElementById("romp-fileview")?.remove();'), "the replace path drops it before the old card goes");
  const urlFn = VIEW.split("export function openUrlView")[1].split("\n}\n")[0];
  assert.ok(urlFn.indexOf("dropProbe();") > urlFn.indexOf("gitHooks = null;") && urlFn.indexOf("dropProbe();") < urlFn.indexOf("dropOnKey();"), "the URL viewer's replace path drops it too (before dropOnKey: file-comments.test.ts pins dropOnKey and runCloseHooks adjacent there)");
});

test("source: review round 2 of Slice 6 (plans/markdown-viewer.md): the keyboard rule reaches a sibling frame's typing target through the top window and never a flag; the memory's key carries the session for a relative path; the fetch failure's pane closes the Outline popover; a heading target on a non-markdown file is spent at its first text paint; the editor's entry keeps the text view's place for a leave while it is up; a fold that is the remembered block, or the offset's block, is opened only when its content was showing", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  // the sibling frame: read when this document does not hold the focus, down the focused iframes to the element, a typing target keeps the keyboard, a throw takes as before
  assert.match(VIEW, /function typingInPeerFrame\(\): boolean \{\n\s*try \{\n\s*if \(typeof document\.hasFocus !== "function" \|\| document\.hasFocus\(\)\) return false;\n\s*const top = window\.top;\n\s*if \(!top \|\| top === window\) return false;\n\s*let a: Element \| null = top\.document\.activeElement;/, "the read starts at the top window's active element");
  assert.match(VIEW, /const inner = \(a as HTMLIFrameElement\)\.contentDocument;\n\s*if \(!inner \|\| inner === document\) return false;\n\s*a = inner\.activeElement;/, "…and walks the focused iframes down to their own active element");
  assert.match(VIEW, /return a !== null && isTypingTarget\(a\);\n\s*\} catch \{ return false; \}/, "a typing target there keeps the keyboard; frames the read cannot see take it as before");
  assert.match(VIEW, /function isTypingTarget\(a: Element\): boolean \{\n\s*if \(a\.localName === "textarea" \|\| a\.localName === "select"\) return true;[^\n]*\n\s*if \(a\.localName === "input"\) return !NON_TEXT_INPUTS\.has\(\(a\.getAttribute\("type"\) \|\| "text"\)\.toLowerCase\(\)\);\n\s*return \(a as HTMLElement\)\.isContentEditable === true;/, "a textarea, a select (type-ahead in a dropdown is typing too, as render.ts's own isTypingTarget reads it; review round 3), a text-like input or a contenteditable");
  assert.equal((VIEW.match(/typingInPeerFrame\(\)/g) || []).length, 3, "read in takeKeyboard's gate and keyboardIdle, defined once: every hand-over runs through the one gate");
  // the memory's key: the session folded in for a relative path alone
  assert.match(VIEW, /export function placeKey\(path: string, sid: string \| null \| undefined\): string \{\n\s*if \(!\/\^\[\/~\]\/\.test\(path\)\) return path \+ "\\u0000" \+ \(sid \?\? ""\);\n\s*const host = hostOf\(sid \?\? ""\);\n\s*return host \? host \+ "\\u0000" \+ path : path;\n\}/, "the kernel's rule for a relative path (neither /- nor ~-rooted): the session's cwd resolves it, so the session is part of the file's identity; an absolute or ~ path is one file for every session of THIS kernel, and a session attached from another kernel (a host-prefixed sid, hostOf) reads that kernel's disk, so its key carries the host (the PR review's round 1: two kernels' files under one key)");
  assert.match(openFn, /const memKey = placeKey\(path, sid\);[^\n]*\n\s*let pendingPlace: RememberedPlace \| null = at === null \? newerPlace\(opts\?\.place, rememberedPlaces\.get\(memKey\)\) : null;/, "read by the key");
  assert.match(openFn, /rememberedPlaces\.set\(memKey, rec\);/, "written by the key");
  assert.doesNotMatch(openFn, /rememberedPlaces\.(get|set)\(path/, "never by the bare path");
  // the failure pane's paint closes the popover, as every other body paint does
  assert.match(openFn, /closeOutline\(\);[^\n]*\n\s*dropLatin1Line\(\);[^\n]*\n\s*body\.replaceChildren\(why\);\n\s*syncOutline\(\);/, "the fetch pipeline's catch: close, drop a standing Latin-1 line (the Slice 7 review's round 2), paint the pane, hide the button");
  // a heading target on a file that is not markdown: judged at its first text paint (a note's Raw view still waits for the Rendered toggle)
  assert.match(openFn, /if \(\(rendered \|\| !isMd\) && pendingHeading !== null\) spendHeading\(\);/, "the spend");
  assert.match(openFn, /const spendHeading = \(\): void => \{\n\s*if \(renderFell !== null\) return;[^\n]*\n\s*const h = pendingHeading; pendingHeading = null;\n\s*if \(h === null\) return;\n\s*requestAnimationFrame\(\(\) => \{\n\s*if \(wrap\.isConnected && unmeasurable\(\)\) \{ pendingHeading = h; return; \}[^\n]*\n\s*if \(!wrap\.isConnected \|\| scrollToFragment\(body, h\)\) return;/, "spent at the paint, landed a frame later; a frame over a boxless body parks it again for the show's repaint (review round 5); never spent over the rows a failed render fell back to, where the target waits for the Rendered retry (Slice 7 of plans/markdown-viewer.md, item 1, the review's round 1)");
  // the editor's entry keeps the text view's place; the leave writes it while the editor is up; the exit clears it
  assert.match(openFn, /let editPlace: RememberedPlace \| null = null;/);
  assert.match(openFn, /if \(refused\) \{ noteBar\(refused\); return; \}\n\s*editPlace = liveRecord\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(isMd && fmt\.md === "rendered"\) \{ fmt\.md = "raw"; saveFmt\(fmt\); \}/, "read past the guard and before the Raw switch: the view the reader read");
  assert.match(openFn, /leaveLive = \(\) => \{\n\s*const rec = editing \? editPlace : liveRecord\(\);\n\s*if \(!rec\) return;/, "the leave's record");
  assert.match(openFn, /editing = false; dirty = false; ta = null;\n\s*editPlace = null;/, "the exit clears it");
  // the remembered block's own fold opens only when the depth passes its shut box; the offset's block that is a fold opens
  assert.match(openFn, /if \(e\.localName === "details" && !e\.hasAttribute\("open"\) && \(otherView \? !p\.atTop && p\.top < body\.clientHeight : !restored && depth > 0 && depth >= e\.getBoundingClientRect\(\)\.height - 0\.5\)\) e\.setAttribute\("open", ""\);/, "a depth inside the summary's height says nothing (it straddles the edge the same open or shut); a record read in Raw, where every row shows, names the fold's rows unless the body stood at the file's very top or the block starts below the body's height (review round 3; round 4 keyed the rule on the block's top sign for a Raw record at the file's top, which had unfolded the front matter; round 5 reads the record's own atTop flag, since the sign also shut a callout whose rows the reader had in view under the blank row at the edge); a fold the record's own state put back is left as it says by the depth rule alone (round 4: it re-opened a fold left shut at another width), and the other-view rule runs over it, a Raw record's carried folds being older evidence than its place (round 6: a Rendered read with the callout shut, Edit, a Raw read into its rows and a Rendered reopen kept it shut over the passage)");
  assert.match(openFn, /revealFragmentTarget\(target\);[^\n]*\n\s*if \(own && target\.localName === "details" && !target\.hasAttribute\("open"\)\) target\.setAttribute\("open", ""\);[^\n]*\n\s*target\.scrollIntoView\(\{ block: "center" \}\);/, "the offset's block that IS a fold is opened before the scroll (revealFragmentTarget opens ancestors alone), and only the offset's OWN block: a stand-in for a block with no element (a comment after a shut callout, the trailing blank line) leaves the fold as authored (review round 3)");
});

test("source: review round 3 of Slice 6 (plans/markdown-viewer.md): the record carries the Rendered view's open folds by ordinal, read at the leave and put back before the seat at the same mtime; a heading target on a picture or a PDF is judged at its first paint with bytes; the Outline lists no heading under a plain hidden wrapper, names its current row for assistive technology and hands Tab back to its button", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  // the record's ninth field: numbers, never text; read off the Rendered body at the leave (liveRecord) and at Edit through it
  assert.match(VIEW, /export type RememberedPlace = \{ start: number; end: number; top: number; atTop: boolean; view: "rendered" \| "raw"; mtimeNs: string; scrollTop: number; t: number; folds\?: number\[\] \};/);
  assert.match(VIEW, /export function openFoldOrdinals\(body: HTMLElement\): number\[\] \| null \{\n\s*const md = body\.querySelector\("\.fileview-md"\);\n\s*if \(!md\) return null;/, "the ordinals of the open <details> under the Rendered box; null without one (a Raw read)");
  assert.match(openFn, /const rec = rememberedPlaceOf\(p, mtimeNs, boxless \? placeScrollTop : body\.scrollTop\);\n\s*const folds = openFoldOrdinals\(body\) \?\? heldFolds\(\);[^\n]*\n\s*return folds \? \{ \.\.\.rec, folds \} : rec;/, "the live record carries them when the Rendered body is up, else the folds a Raw first paint holds (heldFolds), and reads the last measured scrollTop under a boxless body (review round 5)");
  // put back before the seat, at the record's mtime alone, in the Rendered view alone
  assert.match(openFn, /const restoreFolds = \(rec: RememberedPlace\): boolean => \{\n\s*if \(!rec\.folds \|\| rec\.mtimeNs !== mtimeNs \|\| ctx\.mode\(\) !== "rendered"\) return false;/, "the gate: fold state present, the same bytes, the Rendered view; says whether it applied (review round 4)");
  assert.match(openFn, /Array\.from\(md\.querySelectorAll\("details"\)\)\.forEach\(\(d, i\) => \{ if \(open\.has\(i\)\) d\.setAttribute\("open", ""\); else d\.removeAttribute\("open"\); \}\);\n\s*return true;\n\s*\};/, "applied: every fold as the record says");
  assert.match(openFn, /if \(unmeasurable\(\)\) return;\n\s*const rec = pendingPlace; pendingPlace = null;\n\s*const restored = restoreFolds\(rec\);\n\s*if \(!restored && rec\.folds && rec\.mtimeNs === mtimeNs && ctx\.mode\(\) !== "rendered"\) pendingFolds = rec;[^\n]*\n\s*const kept = placeFromRemembered\(rec, shownText\);/, "a boxless body keeps the record pending (review round 4: a paint under a hidden pane spent it); the folds before the block is read and seated, held past a Raw first paint for the first Rendered one (round 4: Edit saves the Raw preference, and the toggle after the reopen painted every fold as authored)");
  assert.match(openFn, /const unmeasurable = \(\): boolean => typeof body\.getClientRects === "function" && body\.getClientRects\(\)\.length === 0;/, "no box at all: the pane's document is display:none (a stand-in without getClientRects is measured as before)");
  assert.match(openFn, /paintedWidth = seenWidth;\n\s*if \(!textShowing\(\)\) return;\n\s*fireRenderedKeepingSelection\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(unmeasurable\(\)\) return;\n(?:\s*\/\/[^\n]*\n)*\s*const moved = placeFrame !== 0;\n\s*const restored = scrollUnread && body\.scrollTop > 0 && place !== null && place\.source === shownText && body\.clientWidth === placeWidth && !\(moved && body\.scrollTop < placeScrollTop\);\n\s*if \(restored\) notePlace\(\); else seat\(place\);[^\n]*\n\s*landRemembered\(\); landTarget\(\);/, "the width hook's repaint (the ResizeObserver's report of the width moving from 0 at the show) seats the pending record and spends the pending target and keyboard (round 5); the report of the box going fires its reflow for the panel's hooks and seats nothing (round 5); the show's report over a scroll the hide kept from being read reads the offset the browser restored instead of seating over it, while the text and the width are the place's and the body is not back at 0 (round 6), unless the restore itself moved the body, its scroll event's read pending, to below the place last measured, where the place is seated (the closing pass); the flag falls with the measurement either branch makes");
  assert.match(openFn, /folds\.restore\(\); restoreHeldFolds\(\);[^\n]*\n\s*stampBodyWidth\(\);/, "the held folds go back right after foldKeeper's restore (whose note in such an open was taken over the Raw body) and before the hooks measure and the seat writes");
  assert.match(openFn, /const restoreHeldFolds = \(\): void => \{ if \(!pendingFolds \|\| ctx\.mode\(\) !== "rendered"\) return; const r = pendingFolds; pendingFolds = null; restoreFolds\(r\); \};/, "a Rendered paint alone spends them, once; restoreFolds' own mtime gate stands");
  assert.match(openFn, /if \(kept\) revealRemembered\(kept, depth, ctx\.mode\(\) !== rec\.view, restored\);/, "the fallback rules learn whether the record is the other view's and whether its folds were put back");
  // a picture that loads after the seat: the seat written again at its load, heard on the body in the capture phase, while the body stands where the seat left it
  assert.match(openFn, /else body\.scrollTop = rec\.scrollTop;\n\s*notePlace\(\);\n\s*armReseat\(rec, kept, depth\);\n\s*\};/, "armed right after the remembered seat");
  assert.match(openFn, /const stands = body\.scrollTop === at\.scrollTop \|\| \(now !== null && at\.place !== null && now\.start === at\.place\.start && Math\.abs\(now\.top - at\.place\.top\) < 0\.5\);\n\s*if \(!stands\) \{ retire\(\); return; \}/, "the guard: the same scrollTop (no anchoring moved it) or the same top block at the same offset (anchoring moved the scrollTop, not the reader); a reader's scroll retires it");
  assert.match(openFn, /body\.addEventListener\("load", onLoad, true\);\n\s*dropReseat = retire;/, "the picture's own load, in the capture phase (an img's load does not bubble); no timer");
  assert.match(openFn, /closeOutline\(\);[^\n]*\n\s*if \(dropReseat\) dropReseat\(\);/, "every paint retires it");
  assert.match(openFn, /ctx\.onClose\(\(\) => \{ if \(dropReseat\) dropReseat\(\); \}\);/, "…and the close");
  const reseat = openFn.slice(openFn.indexOf("const armReseat = "), openFn.indexOf("ctx.onClose(() => { if (dropReseat) dropReseat(); });"));
  assert.doesNotMatch(reseat, /setTimeout|setInterval|requestAnimationFrame/, "no timer in the re-seat");
  // a picture or a PDF: every target judged at the landing over a body with a box, the heading's notice the text branch's (the PR
  // review's round 1 moved the spend out of renderBody's media branch into landMedia, with the line and the offset beside it)
  const media = openFn.slice(openFn.indexOf("if (isImage || isPdf) {"), openFn.indexOf("folds.note();"));
  assert.doesNotMatch(media, /pendingHeading|pendingLine|pendingOffset|noteBar\(/, "renderBody's media branch judges no target: the landing does (landMedia)");
  assert.match(openFn, /const spendOnMedia = \(\): void => \{\n\s*const kind = isPdf \? "a PDF" : "a picture";\n\s*if \(pendingLine !== null\) \{ const n = pendingLine; pendingLine = null; noteBar\("No line " \+ n \+ " in this file: it is " \+ kind \+ "\."\); \}\n\s*if \(pendingOffset !== null\) \{ const n = pendingOffset; pendingOffset = null; noteBar\("No offset " \+ n \+ " in this file: it is " \+ kind \+ "\."\); \}\n\s*if \(pendingHeading !== null\) \{\n\s*const h = pendingHeading; pendingHeading = null;[\s\S]{0,300}noteBar\('No section named "' \+ shown \+ '" in this file\.'\);\n\s*\}\n\s*\};/, "the line, the offset and the heading each named in the notice bar's one-line shape, the kind of file with them (a picture, a PDF); nothing scrolls");
  // the Outline: no row for a heading under a plain hidden wrapper; ids and aria-activedescendant; Tab to the button
  assert.match(VIEW, /function underHidden\(el: Element, root: Element\): boolean \{[\s\S]{0,400}h\.toLowerCase\(\) !== "until-found"\) return true;/, "a plain hidden, not until-found (which a landing lifts)");
  assert.match(openFn, /\.filter\(\(h\) => !underHidden\(h, md\)\) : \[\];/, "headingsOf leaves it out, so the button's visibility and the rows agree");
  assert.match(openFn, /r\.setAttribute\("role", "menuitem"\); r\.dataset\.id = h\.id; r\.id = "fileview-outline-" \+ seq \+ "-" \+ i;/, "a row has an id of its own");
  assert.match(openFn, /const r = rows\[cur\]; r\.classList\.add\("current"\);\n\s*pop\.setAttribute\("aria-activedescendant", r\.id\);/, "the popover names the current row on every move");
  assert.match(openFn, /const words = headingWords\(h\)\.replace\(/, "the row's words read each picture's alt in place");
  assert.match(VIEW, /function headingWords\(n: Node\): string \{\n\s*if \(n\.nodeType === 3\) return \(n as Text\)\.data;\n\s*const e = n as Element;\n\s*if \(e\.localName === "img"\) return " " \+ \(e\.getAttribute\("alt"\) \|\| ""\) \+ " ";/);
  assert.match(openFn, /else if \(e\.key === "Tab"\) \{ closeOutlineKeeping\(false\); outlineBtn\.focus\(\{ preventScroll: true \}\); \}/, "Tab: close, the keyboard back on the button, the key's default left to run (no take())");
});

test("source: the PR review's round 1 of Slice 6 (plans/markdown-viewer.md): the notice bar is a polite live region; a heading target under a plain hidden wrapper says so in the manager's words; the pane toggled off and on re-takes the keyboard the hide dropped at the show's repaint; the Outline button wears the bar's selected dress while its popover is up, Escape puts the keyboard back on it and the current row at the open is the section under the reader's eye; a media landing runs through the box guard and the show's repaint lands what it left pending", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  // item 11: the live-region role, after the insert (styles-fileview-err-sizes.test.ts pins the four lines before it contiguous)
  assert.match(openFn, /bar2\.textContent = msg;\n\s*box\.insertBefore\(bar2, main\);\n\s*bar2\.setAttribute\("role", "status"\);/, "noteBar's div announces itself: the changed-on-disk bar is raised with no gesture");
  // the hidden section: the ruled words, from spendHeading's frame when scrollToFragment landed nothing on a heading the note has
  assert.match(VIEW, /export const HIDDEN_SECTION = "That section is hidden in the rendered view; opened at the top\.";/, "the manager's words, exactly");
  assert.match(VIEW, /function sectionHidden\(box: HTMLElement, fragment: string\): boolean \{[\s\S]{0,500}return !!target && underHidden\(target, root\);\n\}/, "found, under a plain hidden wrapper");
  assert.match(VIEW, /if \(!target\) return false;\n\s*if \(underHidden\(target, box\.querySelector\("\.fileview-md"\) \|\| box\)\) return false;[^\n]*\n\s*revealFragmentTarget\(target\);/, "scrollToFragment lands nothing on a boxless target, so the caller can say why");
  // the pane toggled off and on: the body's own focus and blur keep the record, the show's repaint hands the keyboard back through the gate
  assert.match(openFn, /let bodyHeld = false;\n\s*body\.addEventListener\("focus", \(\) => \{ bodyHeld = true; \}\);\n\s*body\.addEventListener\("blur", \(\) => \{ if \(!unmeasurable\(\)\) bodyHeld = false; \}\);\n\s*const retakeAfterHide = \(\): void => \{\n\s*if \(!bodyHeld \|\| unmeasurable\(\) \|\| document\.activeElement === body\) return;\n\s*bodyHeld = false;\n\s*takeKeyboard\(\);\n\s*\};/, "a blur while the body has a box is the reader's move and clears the record; the fixup's finds none and keeps it; the re-take runs through takeKeyboard's gate, so a typing box elsewhere keeps the keyboard");
  assert.match(openFn, /landRemembered\(\); landTarget\(\);[^\n]*\n\s*retakeAfterHide\(\);/, "after the text landing's pendings at the show's repaint");
  assert.match(openFn, /if \(mediaShowing\(\)\) \{ paintedWidth = seenWidth; landMedia\(\); retakeAfterHide\(\); return; \}\n\s*paintedWidth = seenWidth;\n\s*if \(!textShowing\(\)\) return;/, "the show's repaint over a media body lands what the boxless paint left pending and re-takes the keyboard, ahead of the text block (which the place and text-size suites pin contiguous)");
  assert.match(openFn, /const mediaShowing = \(\): boolean => !editing && ctx\.mode\(\) === "media" && objUrl !== null;/, "a media body with its bytes landed");
  assert.match(openFn, /const landMedia = \(\): void => \{\n\s*if \(unmeasurable\(\)\) return;[^\n]*\n\s*spendOnMedia\(\);\n\s*keyboardOnLanding\(\);\n\s*\};/, "the media landing: the text landing's box guard, the notices, the keyboard");
  assert.match(openFn, /svgText = null;[^\n]*\n\s*renderBody\(\);\n\s*landMedia\(\);/, "the blob landing runs through it (before: keyboardOnLanding alone, spent under a boxless body)");
  assert.doesNotMatch(openFn, /renderBody\(\);\n\s*keyboardOnLanding\(\);/, "no landing spends the keyboard outside a box guard");
  // the Outline: the dress, Escape, the current row
  assert.match(openFn, /outlineBtn\.setAttribute\("aria-expanded", "true"\); outlineBtn\.classList\.add\("on"\);\n\s*box\.appendChild\(pop\);\n\s*const br = outlineBtn\.getBoundingClientRect\(\)/, "the open: the bar's selected dress beside the aria, put on BEFORE the button's box is read (bold widens the button, and a re-wrapped actions row moves it down a line; the popover is placed against the dressed button)");
  assert.match(openFn, /outline = pop;\n\s*setCur\(underEye\(\)\);\n\s*pop\.focus\(\{ preventScroll: true \}\);/, "the section under the reader's eye current at the open");
  assert.match(openFn, /outlineBtn\.setAttribute\("aria-expanded", "false"\); outlineBtn\.classList\.remove\("on"\);/, "the close takes the dress off");
  assert.match(openFn, /if \(e\.key === "Escape"\) \{ take\(\); closeOutlineKeeping\(false\); outlineBtn\.focus\(\{ preventScroll: true \}\); \}/, "Escape: the menu-button pattern, the keyboard back on the button (the Tab branch's shape)");
  assert.match(openFn, /const underEye = \(\): number => \{\n\s*const edge = body\.getBoundingClientRect\(\)\.top;\n\s*let at = 0, margin = -1;\n\s*heads\.forEach\(\(h, i\) => \{\n\s*const r = h\.getBoundingClientRect\(\);\n\s*if \(r\.height === 0 && r\.width === 0\) return;[^\n]*\n\s*if \(margin < 0\) margin = typeof getComputedStyle === "function" \? parseFloat\(getComputedStyle\(h\)\.scrollMarginTop\) \|\| 0 : 0;\n\s*if \(r\.top <= edge \+ margin \+ 0\.5\) at = i;\n\s*\}\);\n\s*return at;\n\s*\};/, "the last heading with a box whose top is at or above the body's edge, the landing's own margin allowed; the first row with none");
  assert.doesNotMatch(openFn, /setCur\(0\);\n\s*pop\.focus/, "never the first row by default");
});

// ── item 1 of Slice 7 of plans/markdown-viewer.md: the render catch moves to the callers, and says what happened ─────────
test("source: mdBlock keeps no try, no catch and no fallback; both viewers' renderBody wrap the block's build and the swap in one try whose catch records the message, paints the RENDER_FELL line and then the Raw rows; mode() reads the record; the line's words are exported", () => {
  // mdBlock: the parse and the sanitize at the function's own level (a two-space indent, inside no try), no fallback write, no flag
  const mdFn = VIEW.split("function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {")[1].split("\n}\n")[0];
  assert.match(mdFn, /\n {2}const base = marked\.defaults\.walkTokens;\n(?: {2}\/\/[^\n]*\n)* {2}const dirty = viewerHtml\(text, \(t\) => \{\n/, "the parse at the function's own level: the exported recipe (marked's lexer, the literal-tags rule, this walk, marked's parser; md-literal-tags.test.ts pins its steps), the walk handed to it");
  const recipe = VIEW.split("export function viewerHtml(text: string, walk?: (token: Token) => void): string {")[1].split("\n}\n")[0];
  assert.match(recipe, /\n {2}return marked\.parser\(tokens, opts\);$/, "the parser at the recipe's own level");
  assert.doesNotMatch(recipe, /try \{/, "inside no try: a throw from the lexer or the parser propagates to mdBlock and on to the caller");
  assert.match(mdFn, /\n {2}const clean = sanitizeMd\(dirty, mintHeadingIds, \{ remoteRefs: "keep" \}\);/, "the sanitize at the function's own level: a throw propagates");
  assert.match(mdFn, /\n {2}box\.replaceChildren\(\.\.\.Array\.from\(clean\.childNodes\)\);\n/, "the adoption at the function's own level too: a throw from either propagates (a presence pin; its place after the figure chain is file-view-seam.test.ts's to pin)");
  assert.doesNotMatch(mdFn, /\n {2}try \{/, "no try at the function's own level (the fence highlight's and the URL parse's inner ones stand)");
  assert.doesNotMatch(mdFn, /box\.textContent = text;|let rendered|rendered = false|if \(rendered/, "no fallback write and no `rendered` flag: the caller keeps the content, and both link passes run on every render");
  assert.match(mdFn, /\n {4}linkMarkdownAnchors\(box, doc\.path\);\n/, "the anchors' pass, ungated");
  assert.match(mdFn, /\n {2}if \(doc && doc\.kind === "file"\) linkifyFileText\(box, doc\.path\);\n {2}return box;$/, "the text pass, gated on the file kind alone");
  assert.match(VIEW, /\n\/\/ No catch here \(plans\/markdown-viewer\.md Slice 7, item 1\)[^\n]*\n(?:\/\/[^\n]*\n)*function mdBlock\(/, "mdBlock's header says where a throw goes");
  // the local viewer's text paint, inside perfTimed (contract C7): try, the swap, the record cleared; catch, the record set, the line then the rows
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /perfTimed\("paint", \(\) => \{[^\n]*\n\s*if \(text === null\) return;[^\n]*\n\s*const kept = keptPlace\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*try \{\n/, "the place read, then the try");
  assert.match(openFn, /try \{\n\s*body\.replaceChildren\(rendered \? mdBlock\(text, \{ kind: "file", path, sid: sid \|\| null \}\) : codeBlock\(text, path, true\)\);[^\n]*\n\s*renderFell = null;\n\s*\} catch \(err\) \{\n\s*const fell = fellMessage\(err\);\n\s*body\.replaceChildren\(renderFellLine\(fell\), codeBlock\(text, path, true\)\);\n\s*renderFell = fell;[^\n]*\n\s*\}\n(?:\s*if \(text === ""\) body\.prepend\([^\n]*\);[^\n]*\n)?\s*viewError = null;[^\n]*\n\s*folds\.restore\(\); restoreHeldFolds\(\);[^\n]*\n\s*stampBodyWidth\(\);[^\n]*\n\s*syncOutline\(\);[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*shownText = text;\n\s*seat\(kept\);/,
    "the swap inside the try; the message through fellMessage (an Error's message with marked's report-this sentence cut, else the value's string); the line first, then codeBlock's rows, then the record, once the fallback stands (the review's round 2: recorded before the swap, a fallback throw left mode() saying raw over a standing box); the rest of the pass runs as for any text paint (the folds, the stamp, the Outline, the hooks once, shownText, the seat); A6's empty-file line may follow the try");
  assert.match(openFn, /\n\s*let renderFell: string \| null = null;/, "per-open state");
  assert.match(openFn, /mode: \(\) => \(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\) \? "media" : isMd && fmt\.md === "rendered" && renderFell === null \? "rendered" : "raw",/, "mode() answers raw while the record stands (the Rendered button stays pressed: fmt.md is untouched)");
  assert.match(openFn, /const rendered = isMd && fmt\.md === "rendered";/, "the paint's own choice still follows the buttons: the Rendered click tries again, the Raw click paints rows and clears the record");
  // the URL viewer: the same try, the document's rows under the same line
  const urlFn = VIEW.split("export function openUrlView")[1].split("\nfunction startDownload(")[0];
  assert.match(urlFn, /\n\s*let renderFell: string \| null = null;/, "its own per-open record");
  assert.match(urlFn, /const kept = keptPlace\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*try \{\n\s*body\.replaceChildren\(fmt\.md === "rendered"\n\s*\? mdBlock\(text, \{ kind: "url", href: loc \}\)[^\n]*\n\s*: codeBlock\(text, parts\.base, true\)\);[^\n]*\n\s*renderFell = null;\n\s*\} catch \(err\) \{\n\s*const fell = fellMessage\(err\);\n\s*body\.replaceChildren\(renderFellLine\(fell\), codeBlock\(text, parts\.base, true\)\);\n\s*renderFell = fell;\n\s*\}\n(?:\s*if \(text === ""\) body\.prepend\([^\n]*\);[^\n]*\n)?\s*folds\.restore\(\);/,
    "the URL viewer's renderBody: build and swap in one try, the line then the rows then the record in its catch (the local viewer's order), the folds' restore after (A6's empty-file line may stand between)");
  assert.equal((VIEW.match(/renderFellLine\(fell\)/g) || []).length, 2, "the two viewers' catches, and nothing else, paint the line");
  assert.equal((VIEW.match(/renderFellLine\(renderFell\)/g) || []).length, 0, "neither paints from the record: the record is written after the swap (the review's round 2)");
  // the line: the exported sentence (contract C5), the message in parentheses, the period; the pane dress, no hint, no button
  assert.match(VIEW, /\nexport const RENDER_FELL = "This file could not be shown as rendered Markdown, so its text is shown as written";\n/);
  assert.match(VIEW, /\nfunction renderFellLine\(msg: string\): HTMLElement \{\n\s*const why = el\("div", "fileview-err"\);\n\s*why\.textContent = RENDER_FELL \+ " \(" \+ msg \+ "\)\.";\n\s*return why;\n\}\n/);
  // the fetch chain's own catch stands for a refused fetch and for a throw from the fallback itself
  assert.match(openFn, /\}\)\)\.catch\(\(err\) => land\(\(\) => \{\n\s*if \(!stands\(\)\) return;/, "the chain's .catch, unchanged");
});

test("source: a Latin-1 file's line (Slice 7 of plans/markdown-viewer.md, item 5): the verdict is its own flag off the header's VALUE \"0\" with the text/plain type, never !isText; applied with the other verdicts at the landing; the raise is one noteBar of the exported LATIN1_NOTICE between the text paint and landTarget, so a target's notice wins the row and a reload's landing raises it again after settleDiskBar; the Edit gate is unchanged", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(VIEW, /\nexport const LATIN1_NOTICE = "This file is not UTF-8 on disk, so it can be read here but not edited: a save would rewrite its bytes as UTF-8\.";\n/, "the exported sentence (contract C5)");
  assert.match(openFn, /type Verdict = \{ isText: boolean; notUtf8: boolean; mtimeNs: string; isImage: boolean; isPdf: boolean; isSvgImage: boolean; bytes: number \| null \};/, "one more field in the verdict shape (and the body's byte count since the review's round 1, item 6's BOM-only line)");
  assert.match(openFn, /v = \{ isText: false, notUtf8: false, mtimeNs: "", isImage: false, isPdf: false, isSvgImage: false, bytes: null \};/, "initialised with the others");
  assert.match(openFn, /\n\s*v\.notUtf8 = ct\.startsWith\("text\/plain"\) && r\.headers\.get\("X-Romp-Text-Utf8"\) === "0";\n/, "the header's value \"0\" with the text type: an image or a PDF carries no header, and an old kernel sends none");
  assert.doesNotMatch(openFn, /notUtf8 = !isText|notUtf8 = !v\.isText|notUtf8 = !got\.isText|notUtf8 = !\(/, "never the text verdict's negation");
  assert.match(openFn, /\n\s*let notUtf8 = false;/, "per-open state, beside isText");
  assert.match(openFn, /isText = got\.isText; notUtf8 = got\.notUtf8; mtimeNs = got\.mtimeNs; isImage = got\.isImage; isPdf = got\.isPdf; isSvgImage = got\.isSvgImage; textBytes = got\.bytes;\n\s*settleDiskBar\(my\);/, "applied with the other verdicts (the byte count among them), before the bar's settle");
  const landing = openFn.slice(openFn.indexOf("const got = v!;"), openFn.indexOf("})).catch((err) => land(() => {"));
  assert.match(landing, /text = t;[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*const reopenOutline = parked && outline !== null;\n(?:\s*\/\/[^\n]*\n)*\s*if \(pendingLine !== null && isMd && fmt\.md === "rendered"\) fmt\.md = "raw";\n\s*renderBody\(\);\n(?:\s*\/\/[^\n]*\n)*\s*if \(notUtf8 && !latin1LineStands\(\)\) noteBar\(LATIN1_NOTICE\);\n\s*landTarget\(\);/,
    "the text landing: the paint, the raise, then the target's spend (the past-the-end line notice, raised inside landTarget, takes the row from the line; the offset and missing-section notices land a frame later and take it the same way); the parked landing's Outline re-open flag is read before the paint (the PR review's round 2)");
  assert.ok(landing.indexOf("settleDiskBar(my);") >= 0 && landing.indexOf("settleDiskBar(my);") < landing.indexOf("if (notUtf8 && !latin1LineStands()) noteBar(LATIN1_NOTICE);"), "the changed-on-disk bar's settle precedes the raise, so a Reload's landing brings the line back over the dropped bar");
  // the guard (the Slice 7 review's round 1): a landing that finds the line standing with the same words leaves the element as it is,
  // so a role=status bar is not re-announced at every poll-driven reload; the drop knows the line by the same words
  assert.match(openFn, /\n  const latin1LineStands = \(\): boolean => note !== null && note\.textContent === LATIN1_NOTICE;\n/, "the standing-line read: the notice with the line's own words");
  assert.equal((openFn.match(/latin1LineStands\(\)/g) || []).length, 1, "read at the landing's raise alone: the format pick's raise already requires no notice at all (note === null), and the drop keeps its own read");
  assert.equal((openFn.match(/noteBar\(LATIN1_NOTICE\)/g) || []).length, 2, "two raise sites: the text landing (a reload's landing runs it again) and the format pick over a replaced failure pane (pickFormat; the review's round 3, pinned below); nothing else re-raises it");
  assert.equal((VIEW.match(/LATIN1_NOTICE/g) || []).length, 7, "the constant's definition, the flag's comment, the verdict's comment, the landing's raise, the format pick's raise over a replaced failure pane (pickFormat; the review's round 3), the landing's clear (dropLatin1Line, which knows the line by its words; the review's round 1) and the standing-line read the raise is guarded by (latin1LineStands; the manager's round 1); no other reader in the viewer");
  assert.match(openFn, /\n  const pickFormat = \(mode: "rendered" \| "raw"\): void => \{\n\s*const overPane = viewError !== null;[^\n]*\n\s*fmt\.md = mode; saveFmt\(fmt\); renderBody\(\);\n\s*if \(overPane && notUtf8 && viewError === null && note === null\) noteBar\(LATIN1_NOTICE\);\n\s*\};\n/, "the format pick (the review's round 3): the pane the paint replaces is read before the paint, and the line is raised again only when the paint stood over a pane (error() cleared), the header said Latin-1 and no other notice holds the row (a re-armed changed-on-disk bar keeps it)");
  assert.match(openFn, /b\.addEventListener\("click", \(\) => \{ pickFormat\(mode\); takeKeyboard\(\); \}\);/, "the bar's buttons pick through it, then take the keyboard");
  assert.match(openFn, /setMode: \(mode\) => \{ if \(!isMd \|\| editing\) return; pickFormat\(mode\); \},/, "and so does the seam's setMode (the Comments panel's switch to Raw)");
  assert.equal((openFn.match(/pickFormat\(mode\)/g) || []).length, 2, "the two picks, and no other caller");
  assert.match(openFn, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtimeNs;/, "the gate is unchanged: the line explains it and does not replace it");
  assert.match(openFn, /isText = \(r\.headers\.get\("Content-Type"\) \|\| ""\)\.startsWith\("text\/plain"\)\n\s+&& r\.headers\.get\("X-Romp-Text-Utf8"\) !== "0";/, "and the text verdict's two lines stand as file-edit.test.ts pins them");
});

test("source: the Slice 7 review's round 1 (plans/markdown-viewer.md, the Slice 7 note): the open's `{ offset }` spender reads the paint's own word, mode(), for the view, so over the rows a failed render fell back to it takes the Raw branch (the row through the seam's scrollToOffset, the notice naming a line) instead of the pressed button's; a text or media landing whose header does not say Latin-1 drops a standing Latin-1 line right after the disk bar's settle (dropLatin1Line, the one notice shown alone with its words), leaving any other notice, and the failure pane's paint drops it too (the review's round 2); spendHeading's guard is pinned with the spend above", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const sso = openFn.slice(openFn.indexOf("const scrollToSourceOffset = "), openFn.indexOf("let pendingOffset"));
  assert.match(sso, /const src = viewText\(\);\n\s*if \(src === null\) return;\n(?:\s*\/\/[^\n]*\n)*\s*const rendered = ctx\.mode\(\) === "rendered";\n\s*if \(n > src\.length\) noteBar\(/, "the view as the paint left it: mode() folds isMd, the button and renderFell (before: `isMd && fmt.md === \"rendered\"`, true over the fallback rows, so the Rendered branch found no .fileview-md and returned with nothing scrolled and a notice naming a block)");
  assert.doesNotMatch(sso.replace(/\/\/[^\n]*/g, ""), /fmt\.md/, "the spender's code never reads the button itself (its comment names the old read)");
  assert.match(openFn, /\n  const dropLatin1Line = \(\): void => \{\n\s*if \(note !== null && note\.textContent === LATIN1_NOTICE\) \{ note\.remove\(\); note = null; \}\n\s*\};\n/, "the clear: the standing notice when it is the line, known by its words (the one notice shown alone with them); a target's notice, a warning or the disk bar with its button is left");
  const landing = openFn.slice(openFn.indexOf("const got = v!;"), openFn.indexOf("})).catch((err) => land(() => {"));
  assert.match(landing, /settleDiskBar\(my\);[^\n]*\n\s*if \(!notUtf8\) dropLatin1Line\(\);[^\n]*\n\s*if \(t instanceof Blob\) \{/, "right after the disk bar's settle and before the branches, so a UTF-8 text landing and a media landing both drop it, and the \"0\" landing's raise below stands as before");
  assert.equal((openFn.match(/dropLatin1Line\(\)/g) || []).length, 2, "two call sites: the landing, and the fetch chain's catch (the review's round 2: a Latin-1 line stood over a 404 or 413 pane saying the file could not be read)");
  const chainCatch = openFn.slice(openFn.indexOf("})).catch((err) => land(() => {"), openFn.indexOf("fetchFile();\n  return true;"));
  assert.match(chainCatch, /closeOutline\(\);[^\n]*\n\s*dropLatin1Line\(\);[^\n]*\n\s*body\.replaceChildren\(why\);/, "in the catch: after the popover's close and before the pane's swap, so the pane never stands under the line");
  assert.match(openFn, /if \(notUtf8 && !latin1LineStands\(\)\) noteBar\(LATIN1_NOTICE\);\n\s*landTarget\(\);/, "the raise stands where it was, guarded by the standing line (the manager's round 1)");
});

test("source: the Slice 7 review's round 2 (plans/markdown-viewer.md, the Slice 7 note): both render catches record renderFell AFTER the fallback swap through one helper, fellMessage, which cuts marked's appended report-this sentence and names an Error with nothing else left by its name; the landing hold's comment names the passes after the try that can throw through into the chain's catch and not the hooks, whose own throws fireRendered swallows", () => {
  assert.ok(VIEW.includes("const MARKED_REPORT_TAIL = /\\n?Please report this to https:\\/\\/github\\.com\\/markedjs\\/marked\\.?\\s*$/;"), "the sentence marked 12's onError appends to every message it rethrows, keyed on its text alone");
  assert.ok(VIEW.includes('function fellMessage(err: unknown): string {\n  if (!(err instanceof Error)) return String(err);\n  return err.message.replace(MARKED_REPORT_TAIL, "") || err.name || "Error";\n}\n'), "an Error's message with the sentence cut, its name when nothing is left (String(err) for an empty message answers the name too), any other thrown value's string");
  assert.equal((VIEW.match(/fellMessage\(err\)/g) || []).length, 2, "both catches, the local viewer's and the URL viewer's, and nothing else");
  assert.doesNotMatch(VIEW, /renderFell = err instanceof Error/, "no catch records the raw message, and none records before its fallback swap");
  // the hold's comment above fetchFile: fireRendered wraps every hook in its own try, so a hook's throw never reaches the chain's catch
  assert.match(VIEW, /const fireRendered = \(why: FileViewRenderWhy = "paint"\) => \{ for \(const cb of renderHooks\) \{ try \{ cb\(why\); \} catch \{[^\n]*\} \} \};/, "each hook in its own try");
  const hold = VIEW.slice(VIEW.indexOf("// The landing runs through the hold's defer"), VIEW.indexOf("const fetchFile = () => {"));
  assert.match(hold, /the passes after the try that can throw through \(the folds' restore, the width stamp,\n\s*\/\/ the Outline's sync, the seat\)/, "the passes named are the ones whose throw reaches the catch");
  assert.match(hold, /Never a hook's own throw: fireRendered runs each hook in its own\n\s*\/\/ try and swallows it/, "and the hooks are named as the exception");
  assert.doesNotMatch(hold, /the folds' restore, the hooks, the seat/, "round 1's list, which named the hooks as a rejecting pass, is gone (the review's round 2)");
});

test("source: an empty file's line (Slice 7 of plans/markdown-viewer.md, item 6): EMPTY_FILE is contract C5's text, the one constant with its own period; emptyFileLine builds the pane-dress div holding it alone; each viewer's text paint prepends it to the body when the text is \"\", right after the try's close and before the folds' restore, so it stands above whichever root the try left and the hooks, the Outline and the seat read the paint with it; the landing applies \"\" as it came (never null) and the Edit gate is unchanged, so Edit shows", () => {
  assert.match(VIEW, /\nexport const EMPTY_FILE = "This file is empty\.";\n/, "contract C5's text, exported for the guide's pin");
  assert.match(VIEW, /\nfunction emptyFileLine\(\): HTMLElement \{\n\s*const why = el\("div", "fileview-err"\);\n\s*why\.textContent = EMPTY_FILE;\n\s*return why;\n\}\n/, "the line: the pane dress, the sentence alone, no hint, no button");
  assert.match(VIEW, /\nexport const BOM_ONLY_FILE = "This file holds only a byte order mark\.";\n/, "the BOM-only file's sentence (the manager's round 1 words), exported for the guide's pin, in the empty line's shape");
  assert.match(VIEW, /\nfunction bomOnlyLine\(\): HTMLElement \{\n\s*const why = el\("div", "fileview-err"\);\n\s*why\.textContent = BOM_ONLY_FILE;\n\s*return why;\n\}\n/, "its line: the empty file's shape");
  assert.match(VIEW, /\n\s*if \(text === ""\) body\.prepend\(textBytes !== null && textBytes > 0 \? bomOnlyLine\(\) : emptyFileLine\(\)\);/, "the local viewer's text paint: the empty text from more than zero bytes was a BOM alone (the answer's Content-Length); absent, the empty file's words");
  assert.match(VIEW, /\n\s*if \(text === ""\) body\.prepend\(bytes > 0 \? bomOnlyLine\(\) : emptyFileLine\(\)\);/, "the URL viewer's: the streamed read's own byte count (readTextCapped)");
  assert.equal((VIEW.match(/if \(text === ""\) body\.prepend\(/g) || []).length, 2, "the two viewers' text paints, and nothing else, prepend a line");
  assert.equal((VIEW.match(/emptyFileLine\(/g) || []).length, 3, "the builder and its two calls: no other site paints the sentence");
  assert.equal((VIEW.match(/bomOnlyLine\(/g) || []).length, 3, "the same for the BOM-only line");
  assert.doesNotMatch(VIEW, /BOM_ONLY_FILE[^\n]*\n[^\n]*textBytes === 3|textBytes === 3/, "keyed on bytes decoding to nothing yet numbering more than zero, the theorem, never on the number three");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const urlFn = VIEW.split("export function openUrlView")[1].split("\nfunction startDownload(")[0];
  assert.match(openFn, /\n\s*const len = r\.headers\.get\("Content-Length"\);\n\s*v\.bytes = len !== null && \/\^\\d\+\$\/\.test\(len\) \? Number\(len\) : null;\n/, "the byte count read off the kernel's Content-Length with the other headers, null when absent or not a number");
  assert.match(openFn, /\n\s*let textBytes: number \| null = null;/, "per-open state, applied at the landing with the verdicts");
  assert.match(openFn, /body\.replaceChildren\(renderFellLine\(fell\), codeBlock\(text, path, true\)\);\n\s*renderFell = fell;[^\n]*\n\s*\}\n\s*if \(text === ""\) body\.prepend\(textBytes !== null && textBytes > 0 \? bomOnlyLine\(\) : emptyFileLine\(\)\);[^\n]*\n\s*viewError = null;[^\n]*\n\s*folds\.restore\(\); restoreHeldFolds\(\);/,
    "the local viewer: after the try's close (the swap stood, or the catch painted its line and rows and recorded the message, the review's round 2) and before the folds' restore (contract C7's optional line): a prepend, so the line is the body's first child above the root, outside code.hljs and .fileview-md");
  assert.match(urlFn, /body\.replaceChildren\(renderFellLine\(fell\), codeBlock\(text, parts\.base, true\)\);\n\s*renderFell = fell;\n\s*\}\n\s*if \(text === ""\) body\.prepend\(bytes > 0 \? bomOnlyLine\(\) : emptyFileLine\(\)\);[^\n]*\n\s*folds\.restore\(\);/,
    "the URL viewer: the same place (a document read through capped-read.ts can be empty)");
  assert.match(openFn, /\n\s*text = t;\n/, "the landing applies the text as it came: \"\" stays \"\"");
  assert.doesNotMatch(openFn, /text = t \|\| null|text = t === "" \? null|text = t \? t : null/, "never null for an empty file: null means not landed, to the seam and the panel");
  assert.match(openFn, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtimeNs;/, "the Edit gate unchanged: \"\" is text under an mtime, so Edit shows and the editor mounts over it");
  assert.match(VIEW, /\n {3}\*  An empty file answers "" \(never null: the body shows the EMPTY_FILE line above its empty root, and that is the content\) \*\//, "text()'s doc says so");
  assert.doesNotMatch(VIEW, /emptyFileLine\(\)[^\n]*fv-cl|"fileview-err fv-cl"/, "the line is never a row");
  assert.doesNotMatch(VIEW, /text\.length === 0|text\.trim\(\) === ""|!text\.length/, "keyed on the text the landing applied being the empty string, never a trim or a timer (the byte count decides only WHICH words the empty text gets)");
});

// executed: openFileView's verdict, the head of the function lifted from file-view.ts (plain JS up to the guard's
// reset) and run over a document that does or does not hold a viewer and a close guard that does or does not
// veto. The Files pane's recent list records an open only when this answers true (files.ts openHere), so a
// dirty-edit veto that answered true would list a file that never opened.
test("openFileView answers false when the dirty-edit guard keeps the previous viewer, and falls through otherwise", () => {
  const at = VIEW.indexOf("export function openFileView(");
  const head = VIEW.slice(VIEW.indexOf("): boolean {", at) + "): boolean {".length, VIEW.indexOf("closeGuard = null;", at) + "closeGuard = null;".length);
  assert.match(head, /if \(document\.getElementById\("romp-fileview"\) && closeGuard && !closeGuard\(\)\) return false;/);
  const run = (viewerUp: boolean, guard: (() => boolean) | null) => {
    let asked = 0;
    const document = { getElementById: (id: string) => (viewerUp && id === "romp-fileview" ? {} : null) };
    const closeGuard = guard ? () => { asked++; return guard(); } : null;
    const out = (new Function("document", "closeGuard", "return (function () {" + head + " return { through: true, guard: closeGuard }; })();") as
      (d: unknown, g: unknown) => false | { through: true; guard: unknown })(document, closeGuard);
    return { out, asked };
  };
  const veto = run(true, () => false);
  assert.equal(veto.out, false, "a viewer up whose guard refuses: the open did not happen");
  assert.equal(veto.asked, 1, "the guard was asked once");
  const ok = run(true, () => true);
  assert.deepEqual(ok.out, { through: true, guard: null }, "the guard allowed it: the head falls through and the guard is dropped for the new viewer");
  const none = run(false, () => false);
  assert.deepEqual(none.out, { through: true, guard: null }, "no viewer up: nothing to ask, the guard is not consulted");
  assert.equal(none.asked, 0);
  assert.deepEqual(run(true, null).out, { through: true, guard: null }, "a viewer with no guard (nothing edited) is replaced");
  // and the other end of the function: a completed open answers true
  assert.match(VIEW, /\n  fetchFile\(\);\n  return true;\n\}/, "openFileView ends by answering true (this fork's open ends in the fetch, after the changed-on-disk probe's install)");
});
