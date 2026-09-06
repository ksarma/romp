// The editor chunk keeps aliases for the old spelling of its decisions (editor-chunk.ts, the naming note above the
// track option): one per caller that has not moved, each line marked "old spelling", and the note promises that
// every alias goes with its last caller. This file makes the promise mechanical and closes the other half of the
// 2026-09-06 review's concern, that the identifier precedent spreads: the record these aliases name is what the host
// writes into the comments log, and CONTEXT.md lists the old word under Avoid for that log, so a third module
// adopting `onLedger` or `track.ledger()` would put two records of one set of decisions a banned word apart again.
// Three pins: the old identifiers appear in no webview module but editor-chunk.ts and file-view.ts, and there only
// on marked lines; each alias the chunk still carries has a caller outside the chunk, or the failure names the line
// to delete; and the alias no file ever imported (the one that stood in for TrackDecision) is gone. The word itself
// is not banned from the webview (the goal tree's per-session record in render.ts wears it as its own name); this
// file looks only for the shapes of the chunk's aliases.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(WEBVIEW, f), "utf8");
const CHUNK = "editor-chunk.ts";
const VIEW = "file-view.ts";
const SELF = "editor-chunk-aliases.test.ts";   // this file names every alias, so it is no caller of any
const files = fs.readdirSync(WEBVIEW).filter((f) => f.endsWith(".ts"));
const modules = files.filter((f) => !f.endsWith(".test.ts"));
const others = files.filter((f) => f !== CHUNK && f !== SELF);   // every module and test but the chunk: its callers
const chunk = read(CHUNK);

/** The chunk's aliases: the declaration line each wears in the chunk, and the shape a CALLER wears — an import of
 *  the type or the const, the option passed, the handle's no-argument read, the setup's read of a state. */
const ALIASES: { alias: string; line: RegExp; caller: RegExp }[] = [
  { alias: "TrackLedger", line: /^export type TrackLedger = TrackDecisions;/, caller: /\bTrackLedger\b/ },
  { alias: "EMPTY_LEDGER", line: /^export const EMPTY_LEDGER = EMPTY_DECISIONS;/, caller: /\bEMPTY_LEDGER\b/ },
  { alias: "onLedger", line: /^\s*onLedger\?: TrackOpts\["onDecisions"\];/, caller: /\bonLedger\b/ },
  { alias: "TrackHandle.ledger", line: /^\s*ledger: TrackHandle\["decisions"\];/, caller: /\btrack[?!]?\.ledger\(\)|\bledger\(\): / },
  { alias: "TrackSetup.ledger", line: /^\s*ledger: TrackSetup\["decisions"\];/, caller: /\.ledger\((?!\))/ },
];
/** The lines that IMPLEMENT an alias (the reader that reads the canonical field, the listener that calls the old
 *  callback): they carry the word too, and go when their declaration does. */
const IMPLEMENTS = /ledger: \(state\) => state\.field\(decisionsField\),|if \(opts\.onLedger\) opts\.onLedger\(next\);|ledger: \(\) => track\.decisions\(view\.state\),/;
/** Any caller shape at all — what a module adopting the old spelling would write. */
const ANY_OLD = new RegExp(ALIASES.map((a) => a.caller.source).join("|"));

test("this file is in the webview tree under the name it excludes itself by", () => {
  assert.ok(files.includes(SELF), `${SELF} must be this file's name, or its own regexes count as callers`);
});

test("no webview module beyond editor-chunk.ts and file-view.ts uses the old spelling, and those two only on marked lines", () => {
  const hits: string[] = [];
  for (const f of modules) {
    read(f).split("\n").forEach((l, i) => {
      if (!ANY_OLD.test(l)) return;
      if ((f === CHUNK || f === VIEW) && /old spelling/.test(l)) return;
      hits.push(`${f}:${i + 1}: ${l.trim()}`);
    });
  }
  assert.deepEqual(hits, [], "an alias is for a caller that has not moved, never a new one: pass onDecisions and read decisions()");
});

test("every alias the chunk carries has a caller outside the chunk; one whose last caller moved goes with it", () => {
  const lines = chunk.split("\n");
  for (const a of ALIASES) {
    const at = lines.findIndex((l) => a.line.test(l));
    if (at < 0) continue;   // already gone, as an alias should be once its callers have moved
    const callers = others.filter((f) => a.caller.test(read(f)));
    assert.ok(callers.length > 0,
      `${a.alias} (editor-chunk.ts:${at + 1}) has no caller left outside the chunk: delete its declaration and the line that implements it`);
  }
});

test("the chunk's alias declarations are the listed ones and nothing new; every other line with the word implements one", () => {
  const code = chunk.split("\n").map((l, i) => [i + 1, l] as const)
    .filter(([, l]) => /ledger/i.test(l) && !l.trim().startsWith("//"));
  assert.ok(code.length > 0, "the aliases still exist (drop this file with the last of them)");
  for (const [n, l] of code) {
    const declared = ALIASES.some((a) => a.line.test(l));
    assert.ok(declared || IMPLEMENTS.test(l), `editor-chunk.ts:${n} carries an alias this file does not know, so no test checks its callers: ${l.trim()}`);
  }
  for (const a of ALIASES) {
    assert.ok(chunk.split("\n").filter((l) => a.line.test(l)).length <= 1, `${a.alias} is declared at most once`);
  }
});

test("the alias no file ever imported, the one that stood in for TrackDecision, is gone from the chunk and named nowhere else", () => {
  const gone = "TrackLedger" + "Entry";   // assembled so this file's own text is not a hit
  for (const f of files) assert.ok(!read(f).includes(gone), `${f} names the removed alias`);
});
