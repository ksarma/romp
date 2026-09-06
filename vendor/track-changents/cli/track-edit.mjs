#!/usr/bin/env node
// Agent CLI: make a TRACKED edit to a vault note in the snapshot store. Use this
// instead of the Edit tool for changes you want to appear as tracked
// suggestions — the PostToolUse hook does not run for headless agents, so this
// records the change explicitly. It reads the file FIRST (capturing the correct
// pre-edit baseline), applies old->new, and appends a snapshot attributed to
// your session, so the user sees your change colored by you.
//
//   node ~/.claude/hooks/track-edit.mjs --file <abs path> --old "<exact text>" --new "<replacement>"
//
// `--old` must be an exact, UNIQUE substring of the note. To CREATE a file
// that doesn't exist yet, pass --old '' (explicitly empty) with the full
// content in --new — the guard hook blocks raw Write on tracked paths, so
// creation has to work here too. Pass `--thread <id>`
// when you're editing IN REPLY to a comment/change you were pinged about (the id
// is in the ping) — your edit then also folds into that thread's conversation as
// a revision turn, even if it lands away from the comment's anchor.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  findVaultRoot, recordAgentEdit, addThreadEditTurn, storePathFor, loadStore, saveStore, reviveThreadInto,
  isNonTextPath,
} from '../store-io.mjs';
import { parseArgs } from './cli-args.mjs';

// ── pure core (exported for tests) ──────────────────────────────────

// Apply a unique old->new replacement to `text`. Returns { text, from, to } (the
// change span, so the caller can record it as an attributed op) or { error }.
export function applyTrackedEdit(text, oldStr, newStr) {
  if (oldStr == null || oldStr === '') return { error: 'An --old span is required.' };
  if (newStr == null) return { error: 'A --new replacement is required.' };
  const idx = text.indexOf(oldStr);
  if (idx === -1) return { error: `--old text not found in the note:\n  ${oldStr}` };
  if (text.indexOf(oldStr, idx + 1) !== -1) {
    return { error: '--old text is not unique — include more surrounding words.' };
  }
  if (oldStr === newStr) return { error: 'The --old and --new text are identical.' };
  return { text: text.slice(0, idx) + newStr + text.slice(idx + oldStr.length), from: idx, to: idx + oldStr.length };
}

// Decode a file's bytes as UTF-8 text, or return null when they are not text: a
// NUL byte or an invalid sequence means a binary file, and applying old→new to a
// lossy decode (what readFileSync(abs, 'utf8') returns, replacement characters
// and all) and writing it back would destroy the file. A leading BOM is kept,
// as readFileSync's decode kept it, so the written text equals the read text
// outside the edited span.
export function decodeTextOrNull(buf) {
  if (buf.includes(0)) return null;
  try { return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(buf); } catch { return null; }
}

// ── CLI ─────────────────────────────────────────────────────────────

// Author identity comes from the environment: TRACKCHANGES_SESSION (set by
// an editor-side dispatcher) or ROMP_SESSION_NAME (romp's generic session-name
// surface, exported for every spawned session). No terminal lookup: sessions
// are manager-spawned and headless (user decision 2026-08-15 — tmux is not
// an identity source; it produced 'unknown' authors that broke reply routing).
function sessionLabel() {
  return process.env.TRACKCHANGES_SESSION || process.env.ROMP_SESSION_NAME || 'unknown';
}

function fail(msg) {
  process.stderr.write(msg.endsWith('\n') ? msg : msg + '\n');
  process.exit(1);
}

function run(argv) {
  const args = parseArgs(argv);
  if (!args.file) fail('--file <absolute note path> is required.');
  const abs = path.resolve(args.file);
  const vaultRoot = process.env.TRACKCHANGES_ROOT || findVaultRoot(abs);
  if (!vaultRoot) fail(`Not inside an Obsidian vault: ${abs}`);
  // A tracked edit is a text operation; on an image, a PDF or any other binary it
  // would rewrite the file from a lossy decode. Refuse by name before reading a
  // byte (this also covers creating one), and by content after the read below.
  if (isNonTextPath(abs)) {
    fail(`Refusing to edit ${abs}: ${path.extname(abs)} is not a text format, and track-edit `
      + `rewrites a file from its UTF-8 text, which would destroy this one. Nothing was written. `
      + `Regenerate the file with a normal write instead.`);
  }
  let text;
  let res;
  if (!fs.existsSync(abs)) {
    // CREATE path: the guard hook blocks the Write tool on tracked paths and
    // points here, so this CLI must be able to start a file or new tracked
    // notes need an untracked seed write (and the first content is usually
    // frontmatter — see the parser note in cli-args.mjs). Contract: an
    // explicit EMPTY --old ("I expect no file") plus the full content in
    // --new, recorded as one insertion against an empty baseline.
    if (args.old === undefined || args.new === undefined) {
      fail(`${abs} does not exist. To CREATE it as a tracked file, pass --old '' `
        + `(explicitly empty) and the full content in --new.`);
    }
    if (args.old !== '') {
      fail(`${abs} does not exist, so there is no text for --old to match. `
        + `To CREATE it, pass --old '' (explicitly empty) and the full content in --new.`);
    }
    if (args.new === '') fail('Refusing to create an empty file.');
    try { fs.mkdirSync(path.dirname(abs), { recursive: true }); } catch { /* surfaces on write */ }
    text = '';
    res = { text: args.new, from: 0, to: 0 };
  } else {
    let buf;
    try { buf = fs.readFileSync(abs); } catch { fail(`Could not read ${abs}`); }
    text = decodeTextOrNull(buf);
    if (text == null) {
      fail(`Refusing to edit ${abs}: its contents are not UTF-8 text (${buf.includes(0) ? 'it contains a NUL byte' : 'invalid UTF-8'}), `
        + `so a tracked edit would rewrite it from a lossy decode and destroy it. Nothing was written. `
        + `Regenerate the file with a normal write instead.`);
    }
    res = applyTrackedEdit(text, args.old, args.new);
    if (res.error) fail(res.error);
  }
  const author = sessionLabel();
  // The session's STABLE id (romp exports ROMP_SID): names get renamed,
  // ids do not — the panel resolves current names through this
  // (user ask 2026-08-26).
  const authorId = process.env.ROMP_SID || null;
  const now = Date.now();
  // Record the change as an attributed op against the PRE-edit text (recordAgentEdit
  // creates the store on first edit and stacks against any existing suggestions).
  // Do this BEFORE writing the note, so a watcher (e.g. an open Obsidian editor)
  // that sees the note change on disk already finds a matching sidecar — closing the
  // read-after-write window. recordAgentEdit derives the new text and never touches
  // the note file itself.
  // Snapshot the sidecar so the note write below can be rolled back. Recording
  // happens first (see above), so a failed note write would otherwise leave an op
  // describing text that is not in the file.
  const storePath = storePathFor(vaultRoot, abs);
  let priorStore = null;
  try { priorStore = fs.readFileSync(storePath, 'utf8'); } catch { priorStore = null; }

  let recorded = null;
  try {
    recorded = recordAgentEdit(vaultRoot, abs, text, { from: res.from, to: res.to, insert: args.new }, author, now, authorId);
  } catch (e) {
    if (e && e.name === 'StaleTextError') {
      fail(`${e.message}\n\nNothing was written. Re-read ${abs} and reapply your change `
        + `against the current text.`);
    }
    fail(`Could not record tracked edit: ${e && e.message}`);
  }
  try {
    fs.writeFileSync(abs, res.text, 'utf8');
  } catch {
    try {
      if (priorStore == null) fs.unlinkSync(storePath);
      else fs.writeFileSync(storePath, priorStore, 'utf8');
    } catch { /* best effort */ }
    fail(`Could not write ${abs} — the tracked edit was rolled back.`);
  }
  // If this edit answers a comment/change thread, fold it into that conversation.
  if (args.thread) {
    try {
      const linked = addThreadEditTurn(vaultRoot, abs, args.thread, author, args.old, args.new, now, res.text,
        recorded && recorded.lastOpId, authorId);
      if (!linked) {
        // The review may have CLOSED under this edit (last change
        // accepted → store parked as .superseded, thread dropped) —
        // revive the thread and retry, so the conversation continues
        // (agent-session report 2026-08-27). The live sidecar now holds
        // the op recordAgentEdit just saved (and any other pending
        // change), so the thread is revived INTO it: reviving into a
        // fresh store and saving that over the sidecar erased them all.
        const live = loadStore(storePath, res.text);
        if (live && reviveThreadInto(vaultRoot, abs, args.thread, live)) {
          saveStore(vaultRoot, storePath, live, res.text);
          addThreadEditTurn(vaultRoot, abs, args.thread, author, args.old, args.new, now, res.text,
            recorded && recorded.lastOpId, authorId);
        }
      }
    } catch (e) { /* best effort */ }
  }
  process.stdout.write('Tracked edit applied.\n');
}

const invokedDirectly = (() => {
  try {
    return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch { return false; }
})();

if (invokedDirectly) run(process.argv.slice(2));
