#!/usr/bin/env node
// Agent CLI for the snapshot track-changes model: attach a comment (an anchored
// yellow highlight + note) to a span of a vault note, written into the side
// store. Edits are tracked automatically by the track-post hook, but a comment
// isn't an Edit the hook can infer, so an editor agent adds one with this:
//
//   node ~/.claude/hooks/track-comment.mjs --file <abs path> --anchor "<exact span>" --note "<text>"
//
// The anchor must be an exact substring of the note's CURRENT text; the plugin
// re-locates it (by quote + surrounding context) as later edits move it.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  findVaultRoot, storePathFor, relPathFor, loadStore, saveStore, STORE_VERSION,
  withStoreLock, StoreLockError,
} from '../store-io.mjs';
import { parseArgs } from './cli-args.mjs';

// ── pure core (exported for tests) ──────────────────────────────────

function makeAnchor(text, from, to, ctx = 24) {
  return {
    quote: text.slice(from, to),
    prefix: text.slice(Math.max(0, from - ctx), from),
    suffix: text.slice(to, to + ctx),
  };
}

// Append a comment anchored to `anchorQuote` (must occur in `text`). Returns
// { store } or { error }.
export function addComment(store, text, anchorQuote, note, author, now, authorId) {
  if (!anchorQuote) return { error: 'An --anchor span is required.' };
  if (!note || !note.trim()) return { error: 'A --note is required.' };
  const idx = text.indexOf(anchorQuote);
  if (idx === -1) return { error: `Anchor text not found in the note:\n  ${anchorQuote}` };
  const anchor = makeAnchor(text, idx, idx + anchorQuote.length);
  store.comments.push({
    id: `${now}-${idx}`,
    author: author || 'unknown', ...(authorId ? { authorId } : {}),
    ts: now || 0,
    anchor,
    body: note.trim(),
    replies: [],
    resolved: false,
  });
  return { store };
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

// A failure is thrown, not exited on the spot, so a lock held at that moment is released on the
// way out (process.exit skips every finally); the entry point prints it and exits 1.
class CliFailure extends Error {}
function fail(msg) {
  throw new CliFailure(msg);
}

function run(argv) {
  const args = parseArgs(argv);
  if (!args.file) fail('--file <absolute note path> is required.');
  const abs = path.resolve(args.file);
  const vaultRoot = process.env.TRACKCHANGES_ROOT || findVaultRoot(abs);
  if (!vaultRoot) fail(`Not inside an Obsidian vault: ${abs}`);
  const storePath = storePathFor(vaultRoot, abs);
  // One writer per sidecar (store-io's withStoreLock): the note read, the load, the comment and
  // the save run under the sidecar's lock, so a host or another CLI writing the same sidecar
  // cannot land between this load and this rename and have its write erased by it. A lock still
  // held after the wait fails with one line and nothing written.
  try {
    withStoreLock(storePath, () => commentUnderLock(args, abs, vaultRoot, storePath));
  } catch (e) {
    if (e instanceof StoreLockError) fail(e.message);
    throw e;
  }
  process.stdout.write('Comment added.\n');
}

function commentUnderLock(args, abs, vaultRoot, storePath) {
  let text;
  try { text = fs.readFileSync(abs, 'utf8'); } catch { fail(`Could not read ${abs}`); }

  let store = loadStore(storePath, text);
  if (!store) {
    store = { v: STORE_VERSION, path: relPathFor(vaultRoot, abs), suggestions: [], comments: [] };
  }
  const res = addComment(store, text, args.anchor, args.note, sessionLabel(), Date.now(), process.env.ROMP_SID || null);
  if (res.error) fail(res.error);
  try { saveStore(vaultRoot, storePath, store, text); } catch { fail(`Could not write the store for ${abs}`); }
}

const invokedDirectly = (() => {
  try {
    return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch { return false; }
})();

if (invokedDirectly) {
  try {
    run(process.argv.slice(2));
  } catch (e) {
    if (!(e instanceof CliFailure)) throw e;
    process.stderr.write(e.message.endsWith('\n') ? e.message : e.message + '\n');
    process.exit(1);
  }
}
