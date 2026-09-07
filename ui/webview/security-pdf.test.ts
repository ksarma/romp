// SECURITY.md's output-sanitization bullet names the file viewer's PDF renderer (plans/file-review.md, Docs:
// with Slice 4 the bullet says that pdf.js parses a PDF on the dashboard's origin, in a Worker, with pixels
// as its only sink, as the plan's Security posture states it). SECURITY.md is the document the repo points
// security readers at, and before this pin nothing read it: the posture section was held against the code by
// file-review-posture.test.ts, the guide's PDF paragraph by guide-pdf.test.ts, and the security policy could
// keep saying DOMPurify and the CSP were the whole story (the 2026-09-06 review). Every fact here reads
// SECURITY.md AND the plan section it summarizes, so the two move together: a property the posture gains or
// loses must be reflected in the bullet, and the pin the bullet names must exist and read that section.
// Prose is matched across line wraps. Synthetic throughout — nothing here opens a PDF.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const SECURITY = read("SECURITY.md");
const PLAN = read("plans", "file-review.md");
const POSTURE_TEST = read("ui", "webview", "file-review-posture.test.ts");

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** A phrase as either document wraps it: any run of whitespace between words. */
const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map(escapeRe).join("\\s+"));
/** The section under `heading`, up to the next `## ` heading. */
function section(doc: string, heading: string, where: string): string {
  const start = doc.indexOf("\n" + heading + "\n");
  assert.notEqual(start, -1, `${heading} is a heading in ${where}`);
  const body = doc.slice(start + heading.length + 2);
  const end = body.search(/\n## /);
  return end === -1 ? body : body.slice(0, end);
}
/** One `- **Lead:**` bullet of a list: from its lead to the next bullet or the section's end. */
function bullet(sec: string, lead: string, where: string): string {
  const start = sec.indexOf("- **" + lead);
  assert.notEqual(start, -1, `${where} has a "${lead}" bullet`);
  const rest = sec.slice(start);
  const end = rest.indexOf("\n- ", 1);
  return end === -1 ? rest : rest.slice(0, end);
}

const HARDENED = section(SECURITY, "## What is already hardened", "SECURITY.md");
const BULLET = bullet(HARDENED, "Output sanitization:", "SECURITY.md's hardened list");
const POSTURE = section(PLAN, "## Security posture", "the plan");
const DOCS = section(PLAN, "## Docs", "the plan");

test("the plan's Docs section promises the bullet, and the bullet is where it says: SECURITY.md's output sanitization", () => {
  assert.match(DOCS, prose("`SECURITY.md`'s output-sanitization bullet names the PDF renderer"), "the promise this file holds SECURITY.md to");
  assert.match(DOCS, prose("in a Worker, with pixels as its only sink"), "and what the promise asks the bullet to say");
  assert.match(BULLET, prose("markdown through marked and DOMPurify, source through highlight.js"), "the other untrusted files the viewer renders on the origin, by library");
  assert.equal(HARDENED.indexOf("- **Output sanitization:", HARDENED.indexOf("- **Output sanitization:") + 1), -1, "one output-sanitization bullet");
  assert.match(BULLET, /DOMPurify/, "the bullet still names the sanitizer the dashboard's HTML passes through");
  assert.match(BULLET, /nonce CSP/, "and the VS Code webview's CSP");
});

test("the bullet names the PDF renderer in the posture's terms: pdf.js, on the dashboard's origin, in a Worker, pixels the only sink", () => {
  assert.match(BULLET, /pdf\.js/, "the renderer by name");
  assert.match(BULLET, prose("in a Worker on the dashboard's origin"), "where it parses");
  assert.match(BULLET, prose("with pixels as its only sink"), "what it may write");
  assert.match(BULLET, prose("no text layer, annotation layer, form field, link, or script from the file reaches the DOM"), "what the sink rules out");
  // each of those is the posture's statement, not the bullet's own: the plan says the same in its words
  assert.match(POSTURE, prose("PDF parsing moves into the dashboard's origin"));
  assert.match(POSTURE, /module Worker/);
  assert.match(POSTURE, prose("Pixels are the only sink"));
  assert.match(POSTURE, prose("no PDF content becomes DOM, a form field, a link, or a script"));
  assert.match(BULLET, prose("with the panel closed a PDF opens in the browser's own viewer"), "and what a PDF opens in when the renderer is not in play");
});

test("the bullet lists every property the posture bounds the widening with, so a posture that gains or loses one fails here", () => {
  const leads = Array.from(POSTURE.matchAll(/^- \*\*([^*]+)\*\*/gm), (m) => m[1]);
  // the property list SECURITY.md summarizes: the posture's bold bullets, in its order, each named in the bullet
  const summarized: Array<[string, RegExp]> = [
    ["`getDocument` receives `data`, never a URL.", /handed bytes, never a URL, so it fetches nothing/],
    ["No eval path.", /the installed build has no eval path/],
    ["Pixels are the only sink.", /only its core is bundled/],
    ["Two caps, refused by name before any work.", /a size cap and a page cap/],
    ["The fallback is the old boundary.", /browser's viewer as the fallback/],
  ];
  assert.deepEqual(leads, summarized.map(([lead]) => lead),
    "the posture's bounding properties are the five SECURITY.md summarizes — a new or renamed one needs the bullet's list updated with it");
  for (const [lead, inBullet] of summarized) {
    assert.match(BULLET.replace(/\s+/g, " "), inBullet, `the bullet names the posture's "${lead}" property`);
  }
});

test("the bullet says where the properties are stated and pinned, and both exist and are the posture's", () => {
  assert.match(BULLET, prose('stated under "Security posture" in `plans/file-review.md`'), "the statement, by file and heading");
  assert.match(BULLET, prose("checked against the code by `ui/webview/file-review-posture.test.ts`"), "the pin, by path");
  assert.ok(fs.existsSync(path.join(ROOT, "ui", "webview", "file-review-posture.test.ts")), "the pin the bullet names is on disk");
  assert.match(POSTURE_TEST, /section\(PLAN, "## Security posture"\)/, "and it reads the section the bullet points at");
  assert.match(POSTURE, /`ui\/webview\/file-review-posture\.test\.ts`/, "the section names the same pin");
});

test("the bullet speaks plainly and carries no identifiers; so does this file", () => {
  assert.doesNotMatch(BULLET, /\b(chunk|esbuild|pdfjs-dist|iframe|getDocument)\b/, "the security policy names no build or API machinery");
  // this file's assertion messages print to the person on failure, so it scans itself, with the guard's own
  // regex line set aside (the precedent is guide-pdf.test.ts)
  const SELF = read("ui", "webview", "security-pdf.test.ts").split("\n").filter((l) => !l.includes("/fleet/i")).join("\n");
  for (const [name, text] of [["SECURITY.md output sanitization", BULLET], ["security-pdf.test.ts", SELF]] as const) {
    assert.doesNotMatch(text, /fleet/i, name + ": no new prose with the banned word");
    assert.doesNotMatch(text, /\/home\/[a-z]/, name + ": no absolute home paths");
  }
});
