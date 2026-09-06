// The CodeMirror editing substrate (the user 2026-08-22): file-view's edit mode swaps the raw
// textarea for CodeMirror 6, loaded as its OWN on-demand bundle. The load-bearing constraints:
// the main bundles stay byte-stable (nothing imports the chunk — lazy discipline), the save path
// is untouched (same string to the same saveFile op behind the same consent gate + ns conflict
// floor), and byte fidelity survives round-trips (UTF-8-only arming, CRLF restore, no invented
// or stripped trailing newline). Pure units run the real langNameFor; the rest are source pins.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { langNameFor, extensionsFor, trackSetup } from "./editor-chunk";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";

const W = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = W("file-view.ts");
const CHUNK = W("editor-chunk.ts");
const RENDER = W("render.ts");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");
const WEBVIEW_DIR = path.resolve(process.cwd(), "..", "ui", "webview");
/** Every source that can reach a shipped bundle: the .ts files under ui/webview that are not tests. */
const BUNDLE_SOURCES = fs.readdirSync(WEBVIEW_DIR).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts") && !f.endsWith(".d.ts"));
// The two files that ARE the editor bundle: everything else is a main-bundle source and must not reach them.
const CHUNK_FILES = new Set(["editor-chunk.ts", "track-decorations.ts"]);
// esbuild.js exports its configs when require()d (it builds only as a script), so a test can bundle one entry
// with the real options; esbuild itself resolves from this package, the way the build does.
const pkgRequire = createRequire(path.resolve(process.cwd(), "package.json"));

// ── long lines wrap while editing, as they do in the read view (the user 2026-09-04) ─────────────
// The read view has always soft-wrapped since 2026-08-24 (no toggle — the user's call then); edit mode
// did not: CodeMirror's default is a horizontal scroll and the textarea fallback wore white-space: pre.
// Both now wrap the same way the view does. Executed against the real extension set: EditorState
// needs no DOM, so the state the editor mounts is built here and inspected.

test("the editor's state carries lineWrapping — a display facet, so the buffer is untouched", () => {
  const noop = () => {};
  const doc = "a line long enough to wrap\r\n".replace(/\r\n/g, "\n") + "x".repeat(400) + "\n";
  const state = EditorState.create({ doc, extensions: extensionsFor("ts", { onChange: noop, onSave: noop }) });
  // EditorView.lineWrapping IS contentAttributes.of({class: "cm-lineWrapping"}) — the class the view's
  // stylesheet keys pre-wrap on; its presence in the facet is the wrapping, before any DOM exists
  const attrs = state.facet(EditorView.contentAttributes);
  assert.ok(attrs.some((a) => typeof a === "object" && a !== null && (a as { class?: string }).class === "cm-lineWrapping"),
    "lineWrapping is in the mounted extension set");
  assert.equal(state.doc.toString(), doc, "wrapping is visual: the document is byte-identical, newlines included");
  // the pure set is what mount() builds the view from — the executed check above is the shipped set (the
  // third argument is the track option's setup, null for an untracked file: the set is otherwise the same)
  assert.match(CHUNK, /let state = EditorState\.create\(\{ doc: opts\.text, extensions: extensionsFor\(opts\.ext, opts, track\) \}\);/);
  assert.match(CHUNK, /\.\.\.langExt\(ext\),\n(?:\s*\/\/[^\n]*\n)*\s*EditorView\.lineWrapping,\n\s*rompTheme\(\),/,
    "lineWrapping sits in extensionsFor, unconditionally — no toggle, like the view");
  // a plain-text file (no highlighter) wraps too
  const plain = EditorState.create({ doc: "x", extensions: extensionsFor("", { onChange: noop, onSave: noop }) });
  assert.ok(plain.facet(EditorView.contentAttributes).some((a) => (a as { class?: string }).class === "cm-lineWrapping"));
});

test("the textarea fallback wraps the same way: wrap=soft, and both sheets say pre-wrap", () => {
  // SOFT: visual only — the value keeps its own newlines, so nothing marks the buffer dirty and the
  // CRLF restore sees the same text (wrap=hard would insert line breaks into the value)
  assert.match(VIEW, /ta\.spellcheck = false;\n(?:\s*\/\/[^\n]*\n)*\s*ta\.wrap = "soft";/);
  assert.doesNotMatch(VIEW, /ta\.wrap = "hard"/);
  // the sheet does the wrapping: white-space: pre on a textarea defeats wrap=soft; pre-wrap + the read
  // view's own overflow-wrap so an unbroken token wraps too (.fileview-pre.fileview-wrap's exact pair)
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = W(sheet);
    assert.match(css, /\.fileview-editor \{[^}]*white-space: pre-wrap; overflow-wrap: anywhere; tab-size: 4; \}/, sheet);
    assert.doesNotMatch(css, /\.fileview-editor \{[^}]*white-space: pre;/, sheet + " must not keep the no-wrap rule");
    assert.match(css, /\.fileview-pre\.fileview-wrap \{ white-space: pre-wrap; overflow-wrap: anywhere;/, sheet + ": the read view's pair, mirrored");
  }
});

// ── lazy discipline: the chunk rides its own entry; no main-bundle source may import it ──────────

test("the chunk is its own esbuild entry, and no main-bundle source imports CodeMirror", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/editor-chunk\.ts"/);
  // the contract is the window global, never an import — an import would drag CodeMirror into the
  // main render/feed bundles and break byte-stability for people who never edit
  assert.match(CHUNK, /if \(typeof window !== "undefined"\) \(window as any\)\.__rompEditor = \{ mount, langNameFor \};/);
  for (const f of ["file-view.ts", "render.ts", "feed.ts", "preview.ts"]) {
    assert.doesNotMatch(W(f), /@codemirror|from "\.\/editor-chunk"/,
      f + " must not import the editor — the lazy chunk is reached only via the window global");
  }
  // …and the test's own import of langNameFor is fine: tests bundle to out-tests, never to dist.
});

// ── Slice 5: the track option lives INSIDE the chunk's bundle, and nowhere else ──────────────────
// Two bundles that each carry @codemirror/state cannot share a page (fields and facets compare by identity),
// so the track field, the marks and the click handling are bundled inside editor-chunk.ts and reached
// through the typed `track` mount option (plans/file-review.md, decision 14) — never a second chunk.

test("no main-bundle source imports CodeMirror, the derived marks module, or the vendored Obsidian modules", () => {
  assert.ok(BUNDLE_SOURCES.includes("file-view.ts") && BUNDLE_SOURCES.includes("render.ts") && BUNDLE_SOURCES.includes("files.ts"),
    "the sweep sees the main-bundle entries");
  for (const f of BUNDLE_SOURCES) {
    if (CHUNK_FILES.has(f)) continue;
    assert.doesNotMatch(W(f), /@codemirror|from "\.\/editor-chunk"|track-decorations|vendor\/track-changents\/obsidian/,
      f + " is a main-bundle source: the editor, its marks and the vendored CodeMirror modules stay in the lazy chunk");
  }
  // the engine itself is fair game for the main bundles (anchor-map.ts reads anchors through it); the
  // Obsidian-side modules are CodeMirror code and belong to the chunk alone
});

test("track-decorations.ts is imported by editor-chunk.ts and by no other bundle source", () => {
  const importers = BUNDLE_SOURCES.filter((f) => /from "\.\/track-decorations"/.test(W(f)));
  assert.deepEqual(importers, ["editor-chunk.ts"]);
  // and the derived module never reaches for Obsidian: every host need is a parameter (the five callbacks)
  assert.doesNotMatch(W("track-decorations.ts"), /require\(['"]obsidian['"]\)|from ['"]obsidian['"]/);
});

test("the chunk exports the track mount option and handle (decision 14), typed, consumed through mount() only", () => {
  // the option and the handle, as file-view.ts will pass and read them
  assert.match(CHUNK, /export interface TrackOpts \{\n\s*\/\*\*[^\n]*\*\/\n\s*suggestions: unknown\[\];/);
  assert.match(CHUNK, /authorColor\?: \(author: string\) => string \| null;/);
  assert.match(CHUNK, /onLedger\?: \(ledger: TrackLedger\) => void;/);
  assert.match(CHUNK, /export interface TrackLedgerEntry \{ id: string; oldText: string; newText: string \}/);
  assert.match(CHUNK, /export interface TrackLedger \{ accepted: TrackLedgerEntry\[\]; rejected: TrackLedgerEntry\[\] \}/);
  assert.match(CHUNK, /export interface TrackHandle \{ suggestions\(\): unknown\[\]; ledger\(\): TrackLedger \}/);
  assert.match(CHUNK, /export interface EditorHandle \{\n\s*value\(\): string;\n\s*focus\(\): void;\n\s*destroy\(\): void;\n\s*track\?: TrackHandle;\n\}/);
  assert.match(CHUNK, /track\?: TrackOpts;/);
  // the handle reads the LIVE state, so a save gets the records as remapped by every keystroke since the mount
  assert.match(CHUNK, /handle\.track = \{ suggestions: \(\) => track\.suggestions\(view\.state\), ledger: \(\) => track\.ledger\(view\.state\) \};/);
  // the window global is unchanged: the option rides the mount call, not a new global
  assert.match(CHUNK, /__rompEditor = \{ mount, langNameFor \};/);
  // the vendored field, unchanged, and the derived marks — bundled by relative path, no alias in the source
  assert.match(CHUNK, /from "\.\.\/\.\.\/vendor\/track-changents\/obsidian\/src\/track-cm\.js";/);
  assert.match(CHUNK, /from "\.\/track-decorations";/);
  assert.doesNotMatch(CHUNK, /@ts-ignore/, "the vendored modules are typed through vendor-track-changents.d.ts");
  // keymap-free: the track extensions add no key bindings; the one keymap stays the editor's own
  assert.equal((CHUNK.match(/keymap\.of\(/g) || []).length, 1);
  // executed: the same extension set, with a setup, carries the field; without one it is the plain editor
  const noop = () => {};
  const t = trackSetup({ suggestions: [{ id: "c1", author: "web", ts: 1, kind: "ins", from: 4, newText: "big ", oldText: "" }] });
  const tracked = EditorState.create({ doc: "The big cat.", extensions: extensionsFor("md", { onChange: noop, onSave: noop }, t) }).update(t.seed).state;
  assert.deepEqual(t.suggestions(tracked).map((s) => s.id), ["c1"]);
  assert.deepEqual(t.ledger(tracked), { accepted: [], rejected: [] });
  const plain = EditorState.create({ doc: "The big cat.", extensions: extensionsFor("md", { onChange: noop, onSave: noop }) });
  assert.equal(plain.doc.toString(), tracked.doc.toString(), "the option adds no text: the buffer is the file");
});

test("exactly one copy of @codemirror/state (and commands, view) ends up in the built editor chunk", async () => {
  // The real hazard: @codemirror/state and /commands ship dual builds, and esbuild resolves an ESM `import`
  // to dist/index.js but a CommonJS require() (the vendored track-cm.js) to dist/index.cjs — two copies, and
  // the vendored field is an "Unrecognized extension value" to the chunk's EditorState. esbuild.js's alias
  // collapses both to the ESM file; this bundles the chunk with the shipped config and reads the metafile.
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  const r = await esbuild.build({ ...(webview as object), entryPoints: ["../ui/webview/editor-chunk.ts"], write: false, metafile: true, logLevel: "silent" });
  const inputs = Object.keys(r.metafile!.inputs);
  const copies = (pkg: string) => inputs.filter((k) => k.includes(`node_modules/@codemirror/${pkg}/`)).sort();
  assert.deepEqual(copies("state"), ["node_modules/@codemirror/state/dist/index.js"]);
  assert.deepEqual(copies("commands"), ["node_modules/@codemirror/commands/dist/index.js"]);
  assert.deepEqual(copies("view"), ["node_modules/@codemirror/view/dist/index.js"]);
  // the vendored modules ride inside the chunk; track-cm.js's require('track-changents/engine') resolves by
  // self-reference through the vendored package.json, with no alias for it
  for (const f of ["obsidian/src/track-cm.js", "obsidian/src/track-logic.js", "engine.js", "display.js"]) {
    assert.ok(inputs.includes(`../vendor/track-changents/${f}`), `the chunk bundles vendor/track-changents/${f}`);
  }
  assert.ok(inputs.includes("../ui/webview/track-decorations.ts"));
  assert.ok(!inputs.some((k) => k.includes("track-snapshot")), "the vendored source of the derived module is a citation, never bundled");
  // and both builds carry the alias: the test bundle's executed track tests need one copy for the same reason
  assert.equal((ESBUILD.match(/alias: oneCodeMirror,/g) || []).length, 2, "the webview build and the test build");
  assert.match(ESBUILD, /module\.exports = \{ extension, webview, testBuild, oneCodeMirror \};/);
  assert.match(ESBUILD, /if \(require\.main === module\) \{/);
});

test("file-view loads the chunk from its own bundle's URL (same dir, same ?v= token), latch cleared on failure", () => {
  assert.match(VIEW, /\.find\(\(u\) => \/\\\/\(render\|feed\|files\)\\\.js\/\.test\(u\)\)/);
  assert.match(VIEW, /sc\.src = self\.replace\(\/\\\/\(render\|feed\|files\)\\\.js\/, "\/editor-chunk\.js"\);/);
  assert.match(VIEW, /sc\.onerror = \(\) => \{ edChunk = null; rej\(/,
    "a failed load clears the latch so a later edit retries fresh");
});

// executed: the derivation's two literals, lifted from the source and run against each hosting page's
// script tags as its _*_page emits them (the shim is inline — no src — and federation.js precedes the
// bundle). The Files pane loads /dist/files.js, which the pattern did not name: every Edit there rejected
// with the raw "no bundle script tag" error and fell to the textarea (the 2026-09-03 review).
test("the derivation recognizes every hosting page's bundle — render.js, feed.js, files.js — and nothing else", () => {
  const find = VIEW.match(/\.find\(\(u\) => (\/[^\n]+?\/)\.test\(u\)\)/);
  const repl = VIEW.match(/sc\.src = self\.replace\((\/[^\n]+?\/), "\/editor-chunk\.js"\);/);
  assert.ok(find && repl, "the find and replace literals sit where the pins above expect them");
  const findRe = new Function("return " + find![1])() as RegExp;
  const replRe = new Function("return " + repl![1])() as RegExp;
  assert.equal(String(findRe), String(replRe), "one pattern finds the bundle and rewrites it");
  const derive = (srcs: string[]) => { const self = srcs.find((u) => findRe.test(u)); return self ? self.replace(replRe, "/editor-chunk.js") : null; };
  const K = "http://TESTHOST:29855/dist/", V = "?v=1725300000";
  assert.equal(derive([K + "federation.js" + V, K + "files.js" + V]), K + "editor-chunk.js" + V, "the Files pane (_files_page)");
  assert.equal(derive([K + "federation.js" + V, K + "feed.js" + V]), K + "editor-chunk.js" + V, "the feed (_feed_page)");
  assert.equal(derive([K + "federation.js" + V, K + "palette-main.js" + V, K + "render.js" + V]), K + "editor-chunk.js" + V, "the chat (_chat_page)");
  // the VS Code webview's resource URI keeps its directory the same way
  const R = "https://file+.vscode-resource.vscode-cdn.net/ext/dist/";
  assert.equal(derive([R + "render.js"]), R + "editor-chunk.js");
  assert.equal(derive([K + "federation.js" + V]), null, "federation.js alone is no hosting bundle — and 'fed' is not feed");
  assert.equal(derive([K + "files-pane.css" + V, K + "waiting.js" + V]), null, "the Waiting pane hosts no viewer");
});

test("the chunk wait wears the romp loader, and a failed load falls back LOUDLY to the textarea", () => {
  assert.match(VIEW, /const wait = el\("div", "fileview-load"\);/);
  assert.match(VIEW, /editing in the plain fallback editor/);
  assert.match(VIEW, /const enterFallback = \(\) => \{/);
  assert.match(VIEW, /ta = el\("textarea", "fileview-editor"\) as HTMLTextAreaElement;/,
    "the textarea survives as the fallback surface");
  assert.match(VIEW, /if \(!editing \|\| my !== editSeq\) return;/,
    "a stale chunk resolution (edit left while loading) must not mount over the viewer");
});

// ── the save path is NOT the editor's: same string, same op, same guards ─────────────────────────

test("both surfaces hand the SAME string to the SAME saveFile op — the gate and floor are untouched", () => {
  assert.match(VIEW, /const bufValue = \(\): string \| null => \(cm \? cm\.value\(\) : ta \? ta\.value : null\);/);
  assert.match(VIEW, /const content = eolCRLF \? buf\.replace\(\/\\n\/g, "\\r\\n"\) : buf;/,
    "the CRLF restore stays file-view's, whichever surface owns the buffer");
  assert.match(VIEW, /post\(\{ type: "saveFile", path, sid: sid \|\| undefined, content, baseMtimeNs: mtimeNs, reqId: saveSeq \}\);/);
  // in-flight typing survives the ack from EITHER surface
  assert.match(VIEW, /if \(bufValue\(\) !== null && bufValue\(\) !== norm\(content\)\) \{/);
  // leaving edit mode releases the CodeMirror view
  assert.match(VIEW, /cm\?\.destroy\(\); cm = null;/);
});

test("the chunk is the text surface only: Mod-s routes to the caller's save, no save wiring of its own", () => {
  assert.match(CHUNK, /key: "Mod-s", run: \(\) => \{ opts\.onSave\(\); return true; \}/);
  // ban from CODE, not comments — the header legitimately NAMES the save op it must never touch
  const code = CHUNK.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  assert.doesNotMatch(code, /saveFile|baseMtimeNs|fetch\(/);
  // local word completion only — no servers, per the no-LSP decision
  assert.match(CHUNK, /autocompletion\(\{ override: \[completeAnyWord\] \}\)/);
});

// ── byte fidelity: the mount contract and the curation, as executed logic ────────────────────────

test("langNameFor curates exactly the in-repo set, plain text otherwise", () => {
  assert.equal(langNameFor("ts"), "javascript");
  assert.equal(langNameFor("PY"), "python");
  assert.equal(langNameFor("bats"), "shell");
  assert.equal(langNameFor("yml"), "yaml");
  assert.equal(langNameFor("md"), "markdown");
  assert.equal(langNameFor("rs"), null, "uncurated extensions edit as plain text — never a guess");
  assert.equal(langNameFor(""), null);
});

test("the CRLF restore + trailing-newline behavior round-trips byte-identically", () => {
  // the exact expression doSave applies to the buffer (pinned above); executed here on both shapes
  const save = (buf: string, eolCRLF: boolean) => (eolCRLF ? buf.replace(/\n/g, "\r\n") : buf);
  const norm = (s: string) => s.replace(/\r\n/g, "\n");
  const crlf = "line one\r\nline two\r\n";
  assert.equal(save(norm(crlf), true), crlf, "an untouched CRLF file round-trips byte-identical");
  const noTail = "no trailing newline";
  assert.equal(save(norm(noTail), false), noTail, "no newline is invented at EOF");
  const tail = "kept\n";
  assert.equal(save(norm(tail), false), tail, "an existing trailing newline is kept");
});

test("edit arming stays the kernel's verdict: UTF-8-only and the ns mtime anchor", () => {
  assert.match(VIEW, /r\.headers\.get\("X-Romp-Text-Utf8"\) !== "0";/);
  assert.match(VIEW, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtimeNs;/);
});

// ── the theme stays the dashboard's own look ─────────────────────────────────────────────────────

test("the editor declares its font and reuses the panel palette — no new fonts or sizes", () => {
  assert.match(CHUNK, /fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"/);
  assert.match(CHUNK, /fontSize: "13px"/);
  assert.match(CHUNK, /color-mix\(in srgb, var\(--accent, #9cd2ff\) 22%, transparent\)/,
    "selection wears the romp accent, nothing new (via the token, so the light theme re-inks it)");
  // and the CodeMirror-side dark branch (its base theme for panels/popups) reads the LIVE body
  // class per mount — hardcoded { dark: true } kept the search panel near-black under
  // body.theme-light (the user 2026-09-02)
  assert.match(CHUNK, /document\.body\.classList\.contains\("theme-light"\)/);
  assert.match(CHUNK, /\{ dark: !light \}/);
});
