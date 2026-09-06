// The guide's PDFs paragraph (docs/guide.md, the Files section; plans/file-review.md Slice 4) pinned to the
// code it describes. The paragraph states a number the code owns (the pages cap, pdf-cap.ts PDF_MAX_BYTES),
// a fallback the viewer builds (file-view.ts), an omission the build makes (esbuild.js copies only pdf.js's
// worker; the chunk hands getDocument no font, CMap or wasm URL), and two behaviors of the panel (a region
// comment names its page; a PDF region may be re-placed on another page). None of those was tied to the
// prose before: a cap change that updated every code-side pin would have left the guide stating the old
// number (the 2026-09-06 review). Every fact here reads the guide AND its source, so the two move together.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { PDF_MAX_BYTES } from "./pdf-cap";
import { regionDesc } from "./region-geometry";

const root = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const GUIDE = root("docs", "guide.md");
const VIEW = root("ui", "webview", "file-view.ts");
const CHUNK = root("ui", "webview", "pdf-chunk.ts");
const PANEL = root("ui", "webview", "file-comments.ts");
const ESBUILD = root("vscode-extension", "esbuild.js");

const flat = (t: string) => t.replace(/\s+/g, " ").trim();   // the guide wraps at 80 columns
const FILES = GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges"));
/** The PDFs paragraph: from its bold lead to the blank line that ends it. */
function pdfParagraph(files: string): string {
  const at = files.indexOf("**PDFs.**");
  assert.ok(at >= 0, "the Files section has a PDFs paragraph");
  const end = files.indexOf("\n\n", at);
  return flat(files.slice(at, end < 0 ? undefined : end));
}
const PARA = pdfParagraph(FILES);

test("the PDFs paragraph sits in the Files section between Figures and Track changes", () => {
  const figures = FILES.indexOf("**Figures.**"), pdfs = FILES.indexOf("**PDFs.**"), track = FILES.indexOf("**Track changes**");
  assert.ok(figures >= 0 && pdfs > figures && track > pdfs, "images, then PDFs, then the changes a session makes");
  assert.equal(FILES.indexOf("**PDFs.**", pdfs + 1), -1, "one PDFs paragraph");
});

test("the cap the guide states is PDF_MAX_BYTES, as a whole number of MB, and the paragraph's only figure", () => {
  const capMb = PDF_MAX_BYTES / (1024 * 1024);
  assert.equal(capMb, Math.round(capMb), "the guide says the cap as a whole number of MB; a fractional cap needs its sentence rewritten");
  const figures = PARA.match(/\d+(?:\.\d+)?\s?[KMG]i?B\b/g) || [];
  assert.deepEqual(figures, [capMb + " MB"], "the paragraph names the cap once and no other size");
  assert.ok(PARA.includes("Pages are drawn only up to " + capMb + " MB of PDF; above that,"), "the cap is stated as what happens above it");
  // and the code's cap is the one the paragraph is checked against: file-view refuses on PDF_MAX_BYTES, not a literal
  assert.match(VIEW, /if \(blob\.size > PDF_MAX_BYTES\) \{ fallback\(pdfCapMessage\(blob\.size, PDF_MAX_BYTES\)\); return; \}/);
  assert.doesNotMatch(VIEW, /\b25 \* 1024 \* 1024\b/, "file-view carries no cap literal of its own");
});

test("the fallback the guide describes is the one the viewer builds: the browser's frame, a line above it saying why, whole-file comments still working", () => {
  assert.ok(PARA.includes("A PDF opens in the browser's own PDF viewer."), "the frame is the default");
  assert.ok(PARA.includes("While **Comments** is open, the viewer draws the pages itself instead"), "the pages only with the panel open");
  assert.match(VIEW, /if \(isPdf && asideOpen\) \{ showPdfPages\(\); return; \}/, "the panel open is the event that picks the pages over the frame");
  assert.ok(PARA.includes("or when the page renderer cannot be loaded or the file cannot be opened, the browser's viewer stays with a line above it saying why, and a comment on the whole file still works."));
  assert.match(VIEW, /rej\(new Error\("the PDF renderer failed to load"\)\)/, "a chunk that fails to load is one of the fallback's reasons");
  assert.match(VIEW, /note\.textContent = why \+ " — showing the browser's PDF viewer instead; comments on the whole file still work\.";/,
    "the line above the frame says why, and that whole-file comments still work — the guide's two promises");
  assert.match(VIEW, /const note = el\("div", "fileview-err"\);/, "in the error dress, so it is loud");
});

test("the renderer's omissions the guide names are the build's: only the worker is copied from pdf.js, and getDocument gets no font, CMap or wasm URL", () => {
  assert.ok(PARA.includes("The renderer ships without pdf.js's standard fonts, CMaps, and JPEG 2000 decoder"));
  assert.ok(PARA.includes("a PDF that does not embed its fonts may show some text in a system font"));
  assert.ok(PARA.includes("a JPEG 2000 image may render blank; the pages still draw."));
  const copies = ESBUILD.match(/node_modules\/pdfjs-dist\/[^"']+/g) || [];
  assert.deepEqual(copies, ["node_modules/pdfjs-dist/build/pdf.worker.mjs"],
    "the build ships one pdf.js asset, the worker — shipping the fonts, the CMaps or the OpenJPEG wasm means rewriting the guide's sentence");
  assert.match(CHUNK, /pdfjsLib\.getDocument\(\{ data: new Uint8Array\(bytes\.slice\(0\)\) \}\)/, "getDocument is handed the bytes and nothing else");
  assert.doesNotMatch(CHUNK, /standardFontDataUrl|cMapUrl|wasmUrl|useSystemFonts/, "no asset URL is configured, so the omission the guide states is real");
});

test("a region comment names its page, and a PDF region may be placed again on another page", () => {
  assert.ok(PARA.includes("the comment names its page, and its card shows that part of the page"));
  assert.equal(regionDesc({ x: 0.1, y: 0.2, w: 0.3, h: 0.4 }, 3).endsWith(" of page 3"), true, "the card's reference ends in the page");
  assert.ok(PARA.includes("A rectangle drawn on one page can be placed again on another."));
  // onRegionDrawn: a re-place is refused only when the target has NO page and is a different picture — a PDF page
  // (page !== null) is never refused, so any page takes the new rectangle, with the page riding in the new target
  assert.match(PANEL, /if \(page === null && own !== img\) \{/, "the refusal is for figures; a PDF page passes");
  assert.match(PANEL, /void this\.mutate\("retarget", \{ commentId: c\.commentId, target: regionTarget\(region, c\.src, page\) \}, "card:" \+ c\.commentId\);/,
    "the new target carries the page it was drawn on");
});

test("the paragraph speaks the person's words and carries no identifiers; so does this file", () => {
  assert.doesNotMatch(PARA, /\b(thread|suggestion|annotation)s?\b/i);
  assert.doesNotMatch(PARA, /\b(chunk|esbuild|pdf\.js's chunk|pdfjs-dist|iframe|canvas)\b/i, "the guide names no build or DOM machinery");
  // this file's assertion messages print to the person on failure, so it scans itself, with the guard's own
  // regex line set aside (the precedent is file-comments.test.ts)
  const SELF = root("ui", "webview", "guide-pdf.test.ts").split("\n").filter((l) => !l.includes("/fleet/i")).join("\n");
  for (const [name, text] of [["guide.md PDFs", PARA], ["guide-pdf.test.ts", SELF]] as const) {
    assert.doesNotMatch(text, /fleet/i, name + ": no new prose with the banned word");
    assert.doesNotMatch(text, /\/home\/[a-z]/, name + ": no absolute home paths");
  }
});
