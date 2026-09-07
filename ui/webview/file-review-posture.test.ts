// The plan's Security posture (plans/file-review.md) states Slice 4's one widening of the browser side — PDF
// parsing moves from the browser's process-isolated PDF viewer into the dashboard's authenticated origin (pdf.js
// in a same-origin Worker, pages painted on the main thread) — and lists the properties that bound it, each one
// something a pdfjs-dist upgrade or a later slice could quietly undo: `getDocument` fed bytes rather than a URL,
// no eval path in the installed build, pdf.js's core alone with no text/annotation/form/XFA/scripting layer, the
// two caps, the frame as the fallback, the worker asset behind `_authorize`. A statement like that is only worth
// reading while it is true, so this file holds each one against the code and the installed dependency: the
// section drifts from what ships, or the build gains a sink the section says it lacks, and a test here names
// which. Prose is matched across line wraps; code pins read code lines only, so a comment may NAME a thing the
// code must never use. Synthetic throughout — nothing here opens a PDF.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { PDF_MAX_BYTES } from "./pdf-cap";   // the viewer's cap, pure; the chunk's default must be the same number

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const PLAN = read("plans", "file-review.md");
const CHUNK = read("ui", "webview", "pdf-chunk.ts");
const VIEW = read("ui", "webview", "file-view.ts");
const KERNEL = read("kernel", "kernel.py");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");
const PDFJS_DIR = path.resolve(process.cwd(), "node_modules", "pdfjs-dist");
const PDFJS_PKG = JSON.parse(fs.readFileSync(path.join(PDFJS_DIR, "package.json"), "utf8")) as { version: string; main: string };
/** The two files the chunk ships: the main build it bundles (the package's entry) and the worker esbuild copies. */
const PDF_MAIN = fs.readFileSync(path.join(PDFJS_DIR, PDFJS_PKG.main), "utf8");
const PDF_WORKER = fs.readFileSync(path.join(PDFJS_DIR, "build", "pdf.worker.mjs"), "utf8");

/** The plan section under `heading`, up to the next `## ` heading. */
function section(doc: string, heading: string): string {
  const start = doc.indexOf("\n" + heading + "\n");
  assert.notEqual(start, -1, heading + " is a heading in the plan");
  const body = doc.slice(start + heading.length + 2);
  const end = body.search(/\n## /);
  return end === -1 ? body : body.slice(0, end);
}
const POSTURE = section(PLAN, "## Security posture");
/** Code lines only: a comment may name what the code must not use. */
const code = (s: string) => s.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** A phrase as the plan wraps it: any run of whitespace between words. */
const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map(escapeRe).join("\\s+"));
/** From `start` to the first line that is exactly `close` (a function's own closing brace at its indent). */
function block(src: string, start: string, close: string, where: string): string {
  const i = src.indexOf(start);
  assert.notEqual(i, -1, `${start.trim()} is in ${where}`);
  const rest = src.slice(i);
  const end = rest.indexOf("\n" + close + "\n");
  assert.notEqual(end, -1, `${start.trim()} in ${where} closes with ${JSON.stringify(close)}`);
  return rest.slice(0, end);
}

// ── the statement itself ──────────────────────────────────────────────────────────────────────────────────────

test("the posture section states the widening: PDF parsing on the dashboard's origin, not in the browser's viewer", () => {
  assert.doesNotMatch(POSTURE, /^\s*Unchanged in kind/, "the section can no longer open by calling the whole posture unchanged");
  assert.match(POSTURE, prose("PDF parsing moves into the dashboard's origin"));
  assert.match(POSTURE, prose("the browser's own PDF viewer in a process of its own"), "what the parsing used to run in");
  assert.match(POSTURE, /`\/dist\/pdf-worker\.js`/, "the worker asset by path");
  assert.match(POSTURE, prose("served behind `_authorize`"), "and how it is served");
  assert.match(POSTURE, /module Worker/, "where pdf.js parses");
  assert.match(POSTURE, /`FontFace`/, "embedded fonts reach the main thread through it");
  assert.match(POSTURE, prose("A PDF is untrusted input"), "the trust statement about the bytes");
  assert.match(POSTURE, /`ui\/webview\/file-review-posture\.test\.ts`/, "the section names this file as its pin");
});

// ── each bounding property, held against the code ─────────────────────────────────────────────────────────────

test("getDocument receives data, never a URL, and the chunk fetches nothing", () => {
  assert.match(POSTURE, prose("`getDocument` receives `data`, never a URL"));
  const c = code(CHUNK);
  assert.match(c, /getDocument\(\{ data: /, "the one getDocument call is fed bytes");
  assert.doesNotMatch(c, /getDocument\([^)]*\burl\b/, "never a URL: pdf.js would fetch it itself");
  assert.doesNotMatch(c, /\bfetch\s*\(/, "the chunk issues no request of its own");
  assert.doesNotMatch(c, /XMLHttpRequest/, "the chunk issues no request of its own");
  // the viewer hands over the /file response it already holds — no second request for the pages
  const pages = block(VIEW, "  const showPdfPages = () => {", "  };", "file-view.ts");
  assert.match(pages, /blob\.arrayBuffer\(\)/, "the bytes are the held blob's");
  assert.doesNotMatch(code(pages), /\bfetch\s*\(/, "no second request for the same bytes");
});

test("no eval path in the installed pdfjs-dist, whose major the section names", () => {
  assert.match(POSTURE, /`isEvalSupported`/, "the switch earlier majors had, named so an upgrade knows what to look for");
  for (const [name, src] of [["build/pdf.mjs", PDF_MAIN], ["build/pdf.worker.mjs", PDF_WORKER]] as const) {
    assert.doesNotMatch(src, /(^|[^\w$.])eval\s*\(/m, `${name}: a global eval call — re-verify the posture and restate it`);
    assert.doesNotMatch(src, /\bnew\s+Function\s*\(/, `${name}: a Function constructor — re-verify the posture and restate it`);
    assert.doesNotMatch(src, /isEvalSupported/, `${name}: the eval switch is back — re-verify the posture and restate it`);
  }
  assert.match(ESBUILD, /\{ in: "node_modules\/pdfjs-dist\/build\/pdf\.worker\.mjs", out: "pdf-worker" \}/,
    "the worker this test scanned is the one esbuild ships");
  const named = /installed pdfjs-dist \((\d+)\.x\)/.exec(POSTURE);
  assert.ok(named, "the section names the installed major, since the eval statement is a property of the version");
  assert.equal(PDFJS_PKG.version.split(".")[0], named[1],
    `pdfjs-dist ${PDFJS_PKG.version} is installed but the section describes ${named[1]}.x — re-verify the eval statement and restate it`);
});

test("pixels are the only sink: pdf.js's core alone, no layer, form, XFA or scripting option, the default annotation mode", () => {
  for (const phrase of ["no text layer", "no annotation layer", "no forms", "no XFA", "no scripting manager"]) {
    assert.match(POSTURE, prose(phrase), `the section lists: ${phrase}`);
  }
  assert.match(POSTURE, /`AnnotationMode\.ENABLE`/, "the section names the painting default it relies on");
  const c = code(CHUNK);
  const specs = Array.from(c.matchAll(/from\s+"([^"]+)"/g), (m) => m[1]).filter((s) => s.startsWith("pdfjs-dist"));
  assert.ok(specs.length > 0, "the chunk imports pdf.js");
  assert.deepEqual(new Set(specs), new Set(["pdfjs-dist"]), "the package's core entry only — never pdfjs-dist/web or another build");
  for (const banned of ["TextLayer", "AnnotationLayer", "XfaLayer", "enableXfa", "enableScripting", "annotationMode",
    "PDFScriptingManager", "pdf_viewer", "isEvalSupported"]) {
    assert.doesNotMatch(c, new RegExp("\\b" + banned + "\\b"), `${banned} in the chunk's code widens the sink list — state it in the posture first`);
  }
  // no other webview module reaches for pdf.js at all (the lazy discipline is pinned elsewhere; this is the sink list's side)
  const dir = path.join(ROOT, "ui", "webview");
  for (const f of fs.readdirSync(dir)) {
    if (!f.endsWith(".ts") || f.endsWith(".test.ts") || f === "pdf-chunk.ts") continue;
    assert.doesNotMatch(code(fs.readFileSync(path.join(dir, f), "utf8")), /from\s+"pdfjs-dist/, `${f} imports pdf.js`);
  }
  // pdf.js's own default for page.render(), which the chunk leaves alone: appearance streams as pixels
  assert.match(PDF_MAIN, /annotationMode = AnnotationMode\.ENABLE/,
    "pdf.js's render() default is no longer AnnotationMode.ENABLE — the section's statement about painting needs re-deriving");
});

test("two caps: the section's numbers are the code's", () => {
  const mb = /(\d+) MB of bytes/.exec(POSTURE);
  const pages = /([\d,]+)\s+pages once the document/.exec(POSTURE);
  assert.ok(mb, "the section states the byte cap in MB");
  assert.ok(pages, "the section states the page cap");
  const bytes = Number(mb[1]) * 1024 * 1024;
  const count = Number(pages[1].replace(/,/g, ""));
  assert.equal(PDF_MAX_BYTES, bytes, "the viewer's cap is the section's");
  assert.match(CHUNK, new RegExp(`export const DEFAULT_MAX_BYTES = ${mb[1]} \\* 1024 \\* 1024;`), "the chunk's default byte cap is the section's");
  assert.match(CHUNK, new RegExp(`export const DEFAULT_MAX_PAGES = ${count};`), "the chunk's default page cap is the section's");
  assert.match(VIEW, /maxBytes: PDF_MAX_BYTES/, "the viewer passes its cap to the chunk");
  assert.match(VIEW, /blob\.size > PDF_MAX_BYTES/, "and refuses before the chunk loads");
});

test("the fallback is the old boundary: the browser's own viewer in the frame", () => {
  assert.match(POSTURE, prose("gets today's frame, the browser's own viewer"));
  const pages = block(VIEW, "  const showPdfPages = () => {", "  };", "file-view.ts");
  assert.match(pages, /const fall = pdfBlock\(url, path\);/, "a fresh frame when none is kept");
  assert.match(pages, /\.catch\(\(err\) => fallback\(/, "every failure on the pages path lands in the fallback");
  const frame = block(VIEW, "function pdfBlock(objUrl: string, path: string): HTMLElement {", "}", "file-view.ts");
  assert.match(frame, /el\("iframe", "fileview-frame"\)/, "pdfBlock is the frame the viewer had before Slice 4");
});

test("the worker asset is served behind _authorize, on the chunk's own origin", () => {
  const getRoute = block(KERNEL, "    def do_GET(self):", "    def do_POST(self):", "kernel.py");
  const auth = getRoute.indexOf("self._authorize(q)");
  const dist = getRoute.indexOf('p.startswith("/dist/")');
  assert.ok(auth !== -1 && dist !== -1, "do_GET has both the gate and the /dist route");
  assert.ok(auth < dist, "the /dist route sits past the gate: pdf-worker.js needs the cookie like every asset");
  const c = code(CHUNK);
  assert.match(c, /GlobalWorkerOptions\.workerSrc = url/, "the chunk points pdf.js at a worker URL");
  assert.match(c, /workerUrlFor\(own\)/, "derived from its own script src — same origin, same directory");
  assert.match(PDF_MAIN, /new Worker\(workerSrc, \{\s*type: "module"\s*\}\)/, "pdf.js spawns a module Worker from it");
});
