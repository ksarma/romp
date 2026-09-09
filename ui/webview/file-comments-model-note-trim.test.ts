// The Send confirm's note is trimmed twice on its way to the session: the panel puts the note on the wire through trimNote
// (doSend; `this.sendNote.trim()` until the review's consolidation; pinned in file-comments-send-note.test.ts) and the
// kernel's send op strips what arrives with Python's
// `str.strip()` before it measures the note against _SEND_NOTE_MAX, places it and logs it. The two trims do not remove
// the same characters: JavaScript's trim() drops a byte-order mark (U+FEFF) that Python keeps, and Python's strip()
// drops NEL (U+0085) and the four ASCII information separators (U+001C to U+001F) that JavaScript keeps. Before trimNote
// the panel measured the JS-trimmed text, so a note of NEL plus 4000 letters was refused here as "4001 characters" while
// the kernel would have counted 4000 and taken it, and a note of one NEL alone read here as words to send when the kernel
// read it as none (the review of the arrivals slice, 2026-09-09). trimNote is the composition the kernel actually reads,
// strip(trim(text)), so noteTooLong's count is the kernel's count on every input; this file pins the composition against
// a real Python interpreter where one is installed, and the character sets it assumes against the engine and a literal.
// Synthetic text only; no non-ASCII string literal in this file (every probe character is built from its code point).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { SEND_NOTE_MAX, noteTooLong, noteLength, trimNote } from "./file-comments-model";

const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const PANEL = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments.ts"), "utf8");

const ch = (cp: number): string => String.fromCodePoint(cp);
const hex = (cp: number): string => cp.toString(16).toUpperCase().padStart(4, "0");
const NEL = ch(0x85), BOM = ch(0xfeff), FS = ch(0x1c), US = ch(0x1f), NBSP = ch(0xa0), IDEO = ch(0x3000);
const SMILE = ch(0x1f600);                                   // one character, two UTF-16 code units
const TOO_LONG = "Nothing sent: the note is " + (SEND_NOTE_MAX + 1) + " characters, and a send carries at most " + SEND_NOTE_MAX + ". Shorten it.";

/** Python's `str.isspace()` set (what `str.strip()` removes), Python 3.4 onward: general category Zs, or bidirectional
 *  class WS, B or S. 29 code points. */
const PY_SPACE: number[] = [
  0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680,
  0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a,
  0x2028, 0x2029, 0x202f, 0x205f, 0x3000,
];
/** ECMAScript's WhiteSpace plus LineTerminator, what `String.prototype.trim` removes: the same set less the separators
 *  and NEL, plus the byte-order mark. 25 code points. */
const JS_SPACE: number[] = PY_SPACE.filter((c) => !(c >= 0x1c && c <= 0x1f) && c !== 0x85).concat([0xfeff]);
const UNION: number[] = PY_SPACE.concat([0xfeff]);

/** Every code point, as the character before or after a letter: what a leading probe removes. Leading NEL shields the
 *  probe from the JS trim (NEL is not JS whitespace), so what trimNote removes after it is Python's set alone. */
function scan(strips: (probe: string) => boolean): number[] {
  const out: number[] = [];
  for (let c = 0; c < 0x110000; c++) if (c !== 0x78 && strips(ch(c))) out.push(c);   // 0x78 is the letter x itself
  return out;
}

test("the character sets the composition assumes: Python's 29 (the literal, probed through trimNote past a leading NEL) and the engine's 25", () => {
  assert.deepEqual(scan((p) => trimNote(NEL + p + "x") === "x"), PY_SPACE, "the model's Python set is exactly str.isspace()");
  assert.deepEqual(scan((p) => (p + "x").trim() === "x"), JS_SPACE.slice().sort((a, b) => a - b), "the engine's trim set is what the comment claims");
  assert.deepEqual(scan((p) => trimNote(p + "x") === "x"), UNION.slice().sort((a, b) => a - b), "a leading character goes if either side strips it");
});

test("trimNote is the kernel's reading: the JS trim, then Python's strip, in that order", () => {
  assert.equal(trimNote("  two words \n"), "two words");
  assert.equal(trimNote("one\n\ntwo"), "one\n\ntwo", "inner whitespace is not touched");
  assert.equal(trimNote(NEL + " x"), "x", "Python's strip runs past a NEL to the space behind it");
  assert.equal(trimNote(BOM + "x" + BOM), "x", "JS drops the byte-order marks");
  assert.equal(trimNote(FS + US + "x" + NEL), "x", "Python drops the separators and NEL");
  assert.equal(trimNote(NEL + BOM + "x"), BOM + "x", "a NEL shielded the mark from the JS trim; the kernel keeps the mark, and so does this");
  assert.equal(trimNote(SMILE + NBSP), SMILE, "an astral character is not a surrogate to split");
  for (const blank of [NEL, FS + US, BOM, IDEO + NEL + BOM, " ".repeat(40), ""]) assert.equal(trimNote(blank), "", hex(blank.codePointAt(0) ?? 0) + ": no note");
});

test("noteTooLong counts what the kernel counts, so a note the kernel takes is not refused here and one it refuses is", () => {
  assert.equal(noteTooLong(NEL + "x".repeat(SEND_NOTE_MAX)), null, "the finding's note: once refused here as 4001, taken by the kernel as 4000");
  assert.equal(noteTooLong("x".repeat(SEND_NOTE_MAX) + US), null);
  assert.equal(noteTooLong(BOM + "x".repeat(SEND_NOTE_MAX)), null, "the JS trim drops the mark on both paths");
  assert.equal(noteTooLong(NEL + BOM + "x".repeat(SEND_NOTE_MAX)), TOO_LONG, "the mark the kernel keeps counts, here too");
  assert.equal(noteTooLong(NEL + "x".repeat(SEND_NOTE_MAX + 1) + NEL), TOO_LONG);
  assert.equal(noteTooLong(" ".repeat(SEND_NOTE_MAX + 50)), null, "whitespace alone is no note");
  assert.equal(noteTooLong(SMILE.repeat(SEND_NOTE_MAX) + NEL), null, "code points, after the trim");
  assert.equal(noteLength(NEL + "x"), 2, "noteLength counts the text it is given; the trim is noteTooLong's");
});

test("at source: the kernel strips with bare str.strip() and the panel's wire carries the JS-trimmed text or trimNote, the two inputs the composition is exact for", () => {
  assert.match(KERNEL, /\n\s+else:\n\s+note = note\.strip\(\)\n\s+if len\(note\) > _SEND_NOTE_MAX:\n/, "the send op's strip, before the bound");
  assert.match(PANEL, /\n\s+const note = (this\.sendNote\.trim\(\)|trimNote\(this\.sendNote\));\n\s+const long = noteTooLong\(note\);\n/, "doSend's wire text");
});

// ── against a real Python ─────────────────────────────────────────────────────────────────────────
const PYTHON = spawnSync("python3", ["-c", "import sys; sys.exit(0)"]).status === 0;
const PY_DRIVER = [
  "import sys, json",
  "inp = json.loads(sys.stdin.read())",
  "out = {'isspace': [c for c in range(0x110000) if chr(c).isspace()],",
  "       'strip': [c for c in range(0x110000) if chr(c).strip() == ''],",
  "       'stripped': [[s.strip(), len(s.strip())] for s in inp]}",
  "sys.stdout.write(json.dumps(out))",
].join("\n");

/** The texts a person might paste or type, edged every way the two sides disagree on: each union character alone and
 *  doubled at either end of a letter, every ordered pair at either end, and a few whole notes. */
function battery(): string[] {
  const out: string[] = ["", "x", "  two words \n", "one\n\ntwo", SMILE, "x".repeat(SEND_NOTE_MAX), NEL + BOM + "x" + BOM + NEL, ch(0xd800) + "x" + ch(0xdc00)];
  for (const a of UNION) {
    const A = ch(a);
    out.push(A, A + "x", "x" + A, A + "x" + A, A + A + "x", "x" + A + A, A + SMILE + A);
    for (const b of UNION) { const B = ch(b); out.push(A + B + "x", "x" + A + B, A + B); }
  }
  return out;
}

test("Python agrees on every input: strip(trim(text)) is trimNote(text) and its len is noteLength of it; trimNote is a fixed point of strip", { skip: PYTHON ? false : "python3 not installed on this machine" }, () => {
  const raws = battery();
  const asks: string[] = [];
  for (const raw of raws) asks.push(raw.trim(), trimNote(raw));            // the wire as doSend sends it; the wire were it trimNote
  const r = spawnSync("python3", ["-c", PY_DRIVER], { input: JSON.stringify(asks), encoding: "utf8", timeout: 60000, maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, r.stderr);
  const got = JSON.parse(r.stdout) as { isspace: number[]; strip: number[]; stripped: [string, number][] };
  assert.deepEqual(got.isspace, PY_SPACE, "the interpreter's isspace set is the literal");
  assert.deepEqual(got.strip, PY_SPACE, "str.strip() removes exactly the isspace set");
  assert.equal(got.stripped.length, asks.length);
  for (let i = 0; i < raws.length; i++) {
    const want = trimNote(raws[i]);
    const [wire, wireLen] = got.stripped[2 * i];
    const [fixed, fixedLen] = got.stripped[2 * i + 1];
    const label = [...raws[i]].map((c) => hex(c.codePointAt(0)!)).join(" ");
    assert.equal(wire, want, "the kernel's reading of the wire is trimNote: " + label);
    assert.equal(wireLen, noteLength(want), "and the kernel's count is noteLength of it: " + label);
    assert.equal(fixed, want, "trimNote is unchanged by the kernel's strip: " + label);
    assert.equal(fixedLen, noteLength(want), label);
  }
});
