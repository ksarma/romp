// The host script speaks CONTEXT.md's vocabulary for the decisions a `save` carries (plans/file-review.md,
// Slice 5; the review of 2026-09-06). `accepted` and `rejected` are the decisions taken in the editor,
// each {id, oldText, newText}, and doSave writes them into the comments log as its accept and reject
// entries. CONTEXT.md lists "ledger" under _Avoid_ for the comments log, and the kernel and the editor
// chunk were renamed to `decisions` for that reason (tests/test_kernel_file_comments_vocabulary.py,
// ui/webview/editor-chunk-decisions.test.ts) — but this script, the one process that writes those
// decisions into the log, kept calling them a ledger in doSave's prose, so a reader met "the ledger"
// and "the log" side by side for one set of decisions, told apart only by the word the glossary bans
// for one of them. It says `decisions` now, the plan's word.
// The avoid-words are read from CONTEXT.md's Comments log entry rather than hard-coded, so a new
// avoid-word fails here too; the scan covers the whole script, which is comments-log code end to end.
// The script's test modules are outside the scan, as the kernel's test scans kernel.py alone.
// Run: node --test tools/file-comments-host-vocabulary.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST_REL = path.join('tools', 'file-comments-host.mjs');
const HOST = fs.readFileSync(path.join(REPO, HOST_REL), 'utf8');
const CONTEXT = fs.readFileSync(path.join(REPO, 'CONTEXT.md'), 'utf8');

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped — the parse
// tests/test_guide_waiting_on_you_hidden_todos.py's _avoid_words does.
function avoidWords(contextMd, term) {
  const entry = new RegExp(`^\\*\\*${esc(term)}\\*\\*:\\n([\\s\\S]*?)(?=\\n\\n|(?![\\s\\S]))`, 'm').exec(contextMd);
  assert.ok(entry, `CONTEXT.md entry ${term} not found`);
  const avoid = /^_Avoid_:(.*)$/m.exec(entry[1]);
  assert.ok(avoid, `CONTEXT.md entry ${term} has no _Avoid_ line`);
  return avoid[1].replace(/\([^)]*\)/g, '').split(',').map((w) => w.trim()).filter(Boolean);
}

// One function's source: its `function name(` line to the next column-0 line.
function func(src, name) {
  const at = src.indexOf(`\nfunction ${name}(`);
  assert.ok(at >= 0, `${name} is defined`);
  const start = at + 1;
  const m = /^\S/m.exec(src.slice(src.indexOf('\n', start) + 1));
  return src.slice(start, m ? src.indexOf('\n', start) + 1 + m.index : src.length);
}

const AVOID = avoidWords(CONTEXT, 'Comments log');

test('CONTEXT.md lists ledger under Avoid for the comments log', () => {
  // The premise, checked against its source: if CONTEXT.md drops "ledger" from the avoid list the scan
  // below is no longer the glossary's rule, and this says so before that one passes vacuously.
  assert.ok(AVOID.includes('ledger'), `Comments log avoids: ${AVOID.join(', ')}`);
});

test('the host script uses none of the words CONTEXT.md avoids for the comments log', () => {
  // Single-word entries only: a phrase like "log alone" names a usage, not a token, and the script
  // says "the comments log" where it means the log (CONTEXT.md's own spelling).
  const words = AVOID.filter((w) => !w.includes(' '));
  assert.ok(words.length);
  const hits = [];
  HOST.split('\n').forEach((line, i) => {
    for (const word of words) {
      if (new RegExp(`\\b${esc(word)}\\b`, 'i').test(line)) {
        hits.push(`${HOST_REL}:${i + 1} says ${JSON.stringify(word)} (CONTEXT.md, Comments log, Avoid): ${line.trim()}`);
      }
    }
  });
  assert.deepEqual(hits, []);
});

test('the save path calls the two lists decisions', () => {
  // The plan's word, positively: the checker of the lists' shape, the verb's doc, and the check that
  // roots each decided id all describe `accepted` and `rejected` as decisions.
  assert.match(HOST, /\/\/ The decisions taken in the editor, `\[\{id, oldText, newText\}\]`/);
  assert.match(HOST, /`accepted` and `rejected` the decisions taken in the editor/);
  const save = func(HOST, 'doSave');
  assert.match(save, /\bdecisions\b/);
  assert.match(save, /from these decisions\)/, 'the count the kernel tells the session comes from the decisions');
  assert.ok(save.includes("logEntry('accept', { changes: accepted })") && save.includes("logEntry('reject', { changes: rejected })"),
    'the decisions are what the accept and reject log entries carry');
  assert.match(func(HOST, 'requireDecisions'), /^function requireDecisions\(list, name, submitted, taken\)/);
});
