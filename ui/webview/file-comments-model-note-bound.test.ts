// The Send confirm's note bound (plans/file-review.md decision 40: at most 4000 characters, the kernel refuses the same
// bound) measured in the kernel's unit. The kernel counts code points (`len(note)` over the JSON-decoded string); a JS
// `note.length` counts UTF-16 code units, two for an emoji or any other astral character, so the panel used to refuse a
// note of 2001 emoji as "4002 characters" that the kernel would have taken as 2001. noteTooLong now counts code points
// (noteLength), so the two sides refuse the same notes and name the same number. Synthetic text only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { SEND_NOTE_MAX, noteTooLong, noteLength } from "./file-comments-model";

const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const SMILE = "\u{1F600}";                              // one character, two UTF-16 code units

test("noteLength counts code points, not UTF-16 code units: an astral character is one", () => {
  assert.equal(SMILE.length, 2, "the premise: JS length counts the surrogate pair twice");
  assert.equal(noteLength(SMILE), 1);
  assert.equal(noteLength(""), 0);
  assert.equal(noteLength("plain text"), 10);
  assert.equal(noteLength("a" + SMILE + "b"), 3);
  assert.equal(noteLength("\uD83D"), 1, "a lone surrogate is one code point on both sides (json.loads gives one str character)");
});

test("the bound is in characters as the kernel counts them: 2001 emoji pass (the kernel would accept them), 4001 are refused as 4001 and not as 8002", () => {
  assert.equal(noteTooLong(SMILE.repeat(2001)), null, "4002 code units, 2001 characters: the finding's note, once refused as '4002 characters'");
  assert.equal(noteTooLong(SMILE.repeat(SEND_NOTE_MAX)), null, "exactly at the bound");
  assert.equal(noteTooLong(SMILE.repeat(SEND_NOTE_MAX + 1)),
    "Nothing sent: the note is " + (SEND_NOTE_MAX + 1) + " characters, and a send carries at most " + SEND_NOTE_MAX + ". Shorten it.");
  // ASCII as before
  assert.equal(noteTooLong("x".repeat(SEND_NOTE_MAX)), null);
  assert.equal(noteTooLong("x".repeat(SEND_NOTE_MAX + 1)), "Nothing sent: the note is 4001 characters, and a send carries at most 4000. Shorten it.");
});

test("the kernel's side measures the same way: its check and its refusal read len(note), Python's code-point count", () => {
  assert.match(KERNEL, /\n_SEND_NOTE_MAX = 4000\n/);
  assert.match(KERNEL, /\n\s+if len\(note\) > _SEND_NOTE_MAX:\n/);
  assert.match(KERNEL, /% \(len\(note\), _SEND_NOTE_MAX\)/, "the refusal names the same count it compared");
});
