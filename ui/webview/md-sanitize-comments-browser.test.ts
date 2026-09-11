// An html comment beside a literal `<word` in one paragraph or table cell, over the REAL viewer module (file-view.ts)
// and the shared sanitizer (md-sanitize.ts) in headless Chromium. DOMPurify drops every comment on its own, but its
// walk judges a parent before it reaches the comment inside, and the parent's markup guard (SAFE_FOR_XML, its mXSS
// defence) removes an element with child nodes, no element child, and BOTH a textContent and an innerHTML that read as
// markup (`/<[/\w!]/`). marked emits an inline comment verbatim and `&lt;x&gt;` as the entity, so a `<p>` or a `<td>`
// holding both matched the guard from two different children and vanished whole with its prose: the note's paragraph
// rendered nothing, the table row rendered with one cell, and a comment on either painted nothing (the Slice 5 review,
// round 4, 2026-09-11; identical on main). The sanitizer now empties an element of its comments on the
// uponSanitizeElement hook, before the guard reads it (dropCommentChildren), so the element stays; the comment-only
// and entity-only controls render as they always did, and no comment node survives anywhere. The first test opens the
// viewer on a synthetic note and reads the rendered DOM; the second runs sanitizeMd on the strings the chat's md()
// would hand it (render.ts sets a message's innerHTML from the sanitized body's), the same hook on the same instance.
// Skips with a stated reason when no playwright browser is installed (CI installs none). Synthetic values only: an
// invented note under a TESTHOST path, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace(/^@import [^\n]*\n/m, "");

const SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
const NOTE_PATH = "/tmp/TESTHOST/notes-api/report.md";

// the viewer, opened the way a path click opens it, and the sanitizer as the chat calls it
const ENTRY = `
import { openFileView } from "./file-view";
import { sanitizeMd } from "./md-sanitize";
(window as any).__openNote = (p: string, sid: string) => { openFileView(p, sid); };
(window as any).__sanitize = (html: string) => sanitizeMd(html).innerHTML;
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-comments-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}</style></head><body>
<script>window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/viewer.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function withNote(t: any, note: string, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this machine; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/viewer") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/viewer.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/file" && u.searchParams.get("path") === NOTE_PATH) {
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: note });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/viewer");
    await page.waitForFunction(() => typeof (window as any).__openNote === "function", null, { timeout: 10000 });
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).__openNote(p, sid); }, [NOTE_PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md table", { state: "attached", timeout: 10000 });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

// The note: the failing shapes (a comment AND a literal `<word` in one paragraph, in one cell; the review's corpus cell
// among them), the wider trigger (a `<K` from `Map<K, V>`), a comment whose own text is markup (DOMPurify's risky
// comment, removed under its own rule before this fix and under the hook now), and the controls that always rendered
// (a comment alone, an entity alone).
const NOTE = [
  "# Report", "",
  "P1 a <!-- c --> b &lt;x&gt; para", "",
  "P2 a <!-- c --> b para", "",
  "P3 a b &lt;x&gt; para", "",
  "P4 a <!-- c --> Map<K, V> para", "",
  "P5 a <!-- <b>hidden</b> --> b &lt;x&gt; para", "",
  "| h1 | h2 |", "|---|---|",
  "| R1 a <!-- c --> b &lt;x&gt; | n1 |",
  "| R2 a <!-- c --> b | n2 |",
  "| R3 a b &lt;x&gt; | n3 |",
  "| cell346 cell346a0 <!-- cell346b0 --> cell346c0 &lt;cell346a1&gt; | nz346 |",
  "| plain | nz1 |", "",
  "Tail.", "",
].join("\n");

const squash = (s: string | null) => (s || "").replace(/\s+/g, " ").trim();

test("a paragraph or a table cell holding an html comment and a literal <word renders whole in the viewer, its comment gone and its prose kept", { timeout: 60000 }, async (t) => {
  await withNote(t, NOTE, async (page, errors) => {
    const facts = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const ps = Array.from(md.querySelectorAll("p")).map((p) => (p.textContent || "").replace(/\s+/g, " ").trim());
      const rows = Array.from(md.querySelectorAll("tbody tr")).map((tr) => Array.from(tr.children).map((td) => (td.textContent || "").replace(/\s+/g, " ").trim()));
      const it = document.createNodeIterator(md, NodeFilter.SHOW_COMMENT);
      let comments = 0;
      while (it.nextNode()) comments++;
      return { ps, rows, comments, hidden: md.innerHTML.includes("hidden") };
    });
    assert.deepEqual(facts.ps, [
      "P1 a b <x> para",
      "P2 a b para",
      "P3 a b <x> para",
      "P4 a Map<K, V> para",
      "P5 a b <x> para",
      "Tail.",
    ], "every paragraph renders: the comment is gone from each and the literal <word stays as text");
    assert.deepEqual(facts.rows, [
      ["R1 a b <x>", "n1"],
      ["R2 a b", "n2"],
      ["R3 a b <x>", "n3"],
      ["cell346 cell346a0 cell346c0 <cell346a1>", "nz346"],
      ["plain", "nz1"],
    ], "every row keeps both cells: the first cell is no longer removed whole for holding a comment beside an entity");
    assert.equal(facts.comments, 0, "no comment node survives the sanitize, at any depth");
    assert.equal(facts.hidden, false, "a comment whose text is markup is gone with the rest, its text never rendered");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("sanitizeMd as the chat calls it: the comment goes and the element stays, for a paragraph, a cell, a risky comment and the body's own comments", { timeout: 60000 }, async (t) => {
  await withNote(t, NOTE, async (page, errors) => {
    const out = await page.evaluate(() => {
      const san = (window as any).__sanitize as (html: string) => string;
      return {
        para: san("<p>a <!-- c --> b &lt;x&gt; para</p>"),
        cell: san("<table><tbody><tr><td>a <!-- c --> b &lt;x&gt;</td><td>n</td></tr></tbody></table>"),
        risky: san("<p>a <!-- <img src=x> --> b &lt;x&gt;</p>"),
        top: san("<!-- top --><p>x</p><!-- tail -->"),
        commentOnly: san("<p>a <!-- c --> b</p>"),
        entityOnly: san("<p>a b &lt;x&gt;</p>"),
        entityThenComment: san("<p>&lt;x&gt; a <!-- c --></p>"),
      };
    });
    assert.equal(out.para, "<p>a  b &lt;x&gt; para</p>", "the paragraph stays, with the comment's place blank and the entity as text");
    assert.equal(out.cell, "<table><tbody><tr><td>a  b &lt;x&gt;</td><td>n</td></tr></tbody></table>", "the cell stays beside its neighbour");
    assert.equal(out.risky, "<p>a  b &lt;x&gt;</p>", "a comment whose own text is markup goes, and the paragraph around it stays");
    assert.equal(out.top, "<p>x</p>", "the body's own comments go too");
    assert.equal(out.commentOnly, "<p>a  b</p>", "the comment-only control is what it always was");
    assert.equal(out.entityOnly, "<p>a b &lt;x&gt;</p>", "the entity-only control is what it always was");
    assert.equal(out.entityThenComment, "<p>&lt;x&gt; a </p>", "the order of the two children makes no difference");
    assert.deepEqual(errors, [], "no page error");
  });
});
