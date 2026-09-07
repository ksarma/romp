// The plan's record of its own tests and docs (plans/file-review.md, the Tests and Docs sections) is the map the
// next slice's implementer reads: open the file the section names, extend it; trust the document the section
// says states a boundary. A map that names a file the pin is not in, or a document that does not say what the
// plan says it says, costs that reader the search the section was meant to save. Slice 4's review (2026-09-06)
// found both: the PDF chunk's lazy-discipline pin credited to editor-lazy.test.ts when it shipped in
// pdf-lazy.test.ts, and SECURITY.md and the pdf-chunk.ts header recorded as stating the PDF trust boundary when
// neither did. This file holds the two sections to the tree, the way file-review-posture.test.ts holds the
// Security posture section to the code: every test file the Tests section names exists; the file a bullet
// credits with the PDF chunk staying lazy holds that test; and each of the Docs section's two Slice 4 items is
// in its file unless the section says it is not yet landed, and absent while it does — so whichever side moves
// first, the plan or the file, the test names the other. Prose is matched across line wraps. Synthetic
// throughout — nothing here opens a PDF.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const PLAN = read("plans", "file-review.md");
const SECURITY = read("SECURITY.md");
const CHUNK = read("ui", "webview", "pdf-chunk.ts");

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** A phrase as the plan wraps it: any run of whitespace between words. */
const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map(escapeRe).join("\\s+"));
/** The plan section under `heading`, up to the next `## ` heading. */
function section(doc: string, heading: string): string {
  const start = doc.indexOf("\n" + heading + "\n");
  assert.notEqual(start, -1, heading + " is a heading in the plan");
  const body = doc.slice(start + heading.length + 2);
  const end = body.search(/\n## /);
  return end === -1 ? body : body.slice(0, end);
}
/** A markdown list's bullets, each joined across its wrapped (indented) lines; prose between lists is dropped. */
const bullets = (s: string) => s.split(/\n(?=- )/).map((b) => b.replace(/\s+/g, " ").trim()).filter((b) => b.startsWith("- "));
/** The test files a run of prose names in backticks: a bare `*.test.ts` is a webview test, anything else a repo path. */
const testFiles = (s: string) =>
  Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|py|bats))`/g), (m) => m[1]).map((n) => (n.includes("/") ? n : path.join("ui", "webview", n)));

const TESTS = section(PLAN, "## Tests");
const DOCS = section(PLAN, "## Docs");

// ── the Tests section ─────────────────────────────────────────────────────────────────────────────────────────

test("every test file the Tests section names exists in the tree", () => {
  const named = new Set(testFiles(TESTS));
  assert.ok(named.size >= 5, "the section names its test files in backticks");
  for (const rel of named) {
    assert.ok(fs.existsSync(path.join(ROOT, rel)), `the Tests section names ${rel}, which does not exist — name the file the tests are in`);
  }
});

test("the file the Tests section credits with the PDF chunk staying lazy is the one that holds that test", () => {
  const claim = prose("PDF chunk staying lazy");
  // the bullet describing THIS file repeats the claim's words without making the claim; every other bullet makes it
  const credited = bullets(TESTS).filter((b) => claim.test(b) && !b.startsWith("- `ui/webview/file-review-docs.test.ts`"));
  assert.equal(credited.length, 1, "exactly one bullet of the Tests section claims the PDF chunk staying lazy");
  // a bullet leads with the file it describes; the lazy-discipline pin must be in THAT file, not a neighbour
  const [subject] = testFiles(credited[0]);
  assert.ok(subject, "the bullet that claims it leads with a test file");
  assert.ok(fs.existsSync(path.join(ROOT, subject)), `${subject} exists`);
  assert.match(read(...subject.split("/")), /test\("no main-bundle source imports pdfjs-dist or the chunk/,
    `${subject} is credited with the PDF chunk staying lazy but holds no such test — the pin lives where "no main-bundle source imports pdfjs-dist or the chunk" is`);
});

// ── the Docs section's Slice 4 items ──────────────────────────────────────────────────────────────────────────

/** SECURITY.md's output-sanitization bullet, joined across its wrapped lines. */
const SECURITY_BULLET = bullets(SECURITY).find((b) => b.startsWith("- **Output sanitization:**"));
/** pdf-chunk.ts's header: its leading comment, up to the first line of code. */
const CHUNK_HEADER = (() => {
  const out: string[] = [];
  for (const l of CHUNK.split("\n")) { if (l.startsWith("//") || l.trim() === "") out.push(l); else break; }
  return out.join("\n");
})();

/** One recorded item: how the Docs section claims it, how it marks it not yet landed, and whether its file carries it. */
const ITEMS: Array<{ name: string; claim: RegExp; owed: RegExp; present: boolean; expects: string }> = [
  {
    name: "SECURITY.md's output-sanitization bullet",
    claim: prose("`SECURITY.md`'s output-sanitization bullet names the PDF renderer"),
    owed: /`SECURITY\.md`(?:'s output-sanitization bullet)? is not yet landed/,
    present: SECURITY_BULLET !== undefined && /pdf\.js/.test(SECURITY_BULLET) && /sink/.test(SECURITY_BULLET),
    expects: "pdf.js, and pixels as its only sink",
  },
  {
    name: "the pdf-chunk.ts header",
    claim: prose("the `pdf-chunk.ts` header says the same in a sentence"),
    owed: /`pdf-chunk\.ts` header is not yet landed/,
    present: /origin/.test(CHUNK_HEADER) && /sink/.test(CHUNK_HEADER),
    expects: "the dashboard's origin, and pixels as its only sink",
  },
];

test("the Docs section records both Slice 4 items, and says where the record is held", () => {
  assert.ok(SECURITY_BULLET, "SECURITY.md has an Output sanitization bullet, the one the plan's record is about");
  for (const item of ITEMS) assert.match(DOCS, item.claim, `the Docs section records ${item.name}`);
  assert.match(DOCS, /`ui\/webview\/file-review-docs\.test\.ts`/, "the section names this file as the record's pin");
});

for (const item of ITEMS) {
  test(`${item.name}: in its file unless the Docs section calls it not yet landed, and absent while it does`, () => {
    if (item.owed.test(DOCS)) {
      assert.equal(item.present, false,
        `${item.name} now states the boundary (${item.expects}), but the plan's Docs section still calls it not yet landed — drop that clause so the record matches the file`);
    } else {
      assert.equal(item.present, true,
        `the plan's Docs section says ${item.name} states the boundary, but it does not name ${item.expects} — land the statement, or record it as not yet landed (the words "is not yet landed" after the item)`);
    }
  });
}
