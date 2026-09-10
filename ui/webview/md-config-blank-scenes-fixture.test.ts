// The shape of the blank-scene fixture the trim's browser leg reads (anchor-map-fixtures/blank-scenes.json, the union of the blank
// scenes the Slice 4 review's rounds 7 to 12 collected). That leg (md-config-paint-trim-browser.test.ts) records no expected marks
// and reads the answer off the browser's layout, so a scene whose markdown does not render the shape its name claims passes it
// vacuously: the leg requires a non-empty paint, not that the paint reached the scene's construct, and a top-level block the
// pairing refused holds no mark and counts as no bare blank. Pinned here, with no browser:
// 1. Every scene is markdown holding the paragraph 'Intro para.' and then the paragraph 'After para.', each once (the leg's range
//    reads the paint's ends off those two strings) and ending at the latter, laid out at a positive integer width; names are unique.
// 2. A carriage return in a scene is always the CRLF pair. marked's lexer rewrites `\r\n|\r` to `\n`, so a lone CR before a CRLF is
//    two line feeds, a blank line, and a blank line ends an html block (CommonMark's type 6): round 13 found the scene 'CRLF newline
//    inside an html block between inline children' written `\r\r\n` inside its div, which marked split into a div and a paragraph
//    the pairing refused, so the scene painted the one mark 'Intro para.' and exercised nothing. A scene named for CRLF holds the
//    pair and one named for a form feed holds one.
// 3. The fixture's note is prose, an array of strings.
// Synthetic prose, no paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

type Scene = { name: string; width: number; markdown: string };
const FIX = path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", "blank-scenes.json"); // npm test runs in vscode-extension
const DOC = JSON.parse(fs.readFileSync(FIX, "utf8")) as { note: string[]; scenes: Scene[] };
const SCENES = DOC.scenes;
/** A slice of a scene for a message, every control and non-ASCII character spelt as its escape (a CR is invisible otherwise). */
const show = (s: string): string => JSON.stringify(s).replace(/[^\x20-\x7e]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));

test("every scene holds 'Intro para.' then 'After para.' once each and ends at the latter, at a positive integer width, under a unique name; the note is prose", () => {
  assert.ok(Array.isArray(DOC.note) && DOC.note.length > 0 && DOC.note.every((l) => typeof l === "string"), "the note is an array of strings");
  assert.ok(SCENES.length >= 90, "the fixture holds the union: " + SCENES.length + " scenes");
  const names = new Set<string>();
  SCENES.forEach((sc, i) => {
    const what = "scene " + i + " (" + sc.name + ")";
    assert.deepEqual(Object.keys(sc).sort(), ["markdown", "name", "width"], what + ": a name, a width and markdown, nothing else");
    assert.ok(typeof sc.name === "string" && sc.name.length > 0, what + ": named");
    assert.ok(!names.has(sc.name), what + ": the name is unique");
    names.add(sc.name);
    assert.ok(Number.isInteger(sc.width) && sc.width > 0, what + ": a positive integer width: " + String(sc.width));
    const intro = sc.markdown.indexOf("Intro para."), after = sc.markdown.indexOf("After para.");
    assert.ok(intro >= 0 && after > intro, what + ": 'Intro para.' before 'After para.'");
    assert.equal(sc.markdown.indexOf("Intro para.", intro + 1), -1, what + ": 'Intro para.' once");
    assert.equal(sc.markdown.indexOf("After para.", after + 1), -1, what + ": 'After para.' once");
    assert.ok(sc.markdown.endsWith("After para."), what + ": ends at 'After para.'");
  });
});

test("a carriage return in a scene is always the CRLF pair (to marked a lone CR is a line ending, and two in a row are the blank line that ends an html block); a scene named for CRLF holds the pair, one named for a form feed holds one", () => {
  const loneCr: string[] = [];
  SCENES.forEach((sc, i) => {
    const m = /\r(?!\n)/.exec(sc.markdown);
    if (m) loneCr.push("scene " + i + " (" + sc.name + ") at offset " + m.index + ": " + show(sc.markdown.slice(Math.max(0, m.index - 12), m.index + 6)));
  });
  assert.deepEqual(loneCr, [], "no lone CR in any scene: marked rewrites \\r\\n|\\r to \\n, so a CR before a CRLF is a blank line, and a blank line ends the html block the scene meant to paint inside");
  const crlf = SCENES.filter((sc) => /\bCRLF\b/.test(sc.name)), ff = SCENES.filter((sc) => /\bform feed\b/.test(sc.name));
  assert.ok(crlf.length >= 2, "the union names CRLF scenes: " + crlf.length);
  for (const sc of crlf) assert.ok(sc.markdown.includes("\r\n"), sc.name + ": holds a CRLF pair");
  assert.ok(ff.length >= 2, "the union names form-feed scenes: " + ff.length);
  for (const sc of ff) assert.ok(sc.markdown.includes("\f"), sc.name + ": holds a form feed");
});
