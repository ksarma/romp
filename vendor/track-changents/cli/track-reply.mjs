#!/usr/bin/env node
// Agent CLI: post a text reply INTO an existing thread (a change-thread or a
// comment) in the snapshot store, so the agent's reply nests in the conversation
// the reviewer started — instead of becoming a stray new comment. The thread id
// is handed to you in the ping you received.
//
//   node ~/.claude/hooks/track-reply.mjs --file <abs path> --thread <id> --note "<text>"
//
// (To respond with an actual edit, use track-edit.mjs — that edit shows in the
// same thread because the thread is keyed to the change's location.)

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  findVaultRoot, storePathFor, loadStore, saveStore, reviveThreadFromSuperseded, reviveThreadInto,
} from '../store-io.mjs';
import { parseArgs } from './cli-args.mjs';

// ── pure core (exported for tests) ──────────────────────────────────

export function addReply(store, threadId, author, body, now, authorId) {
  if (!body || !body.trim()) return { error: 'A --note is required.' };
  const c = (store.comments || []).find((x) => String(x.id) === String(threadId));
  if (!c) return { error: `No thread found with id "${threadId}".` };
  if (!Array.isArray(c.replies)) c.replies = [];
  c.replies.push({ author: author || 'unknown', ...(authorId ? { authorId } : {}), ts: now || 0, body: body.trim() });
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

function fail(msg) {
  process.stderr.write(msg.endsWith('\n') ? msg : msg + '\n');
  process.exit(1);
}

function run(argv) {
  const args = parseArgs(argv);
  if (!args.file) fail('--file <absolute note path> is required.');
  if (!args.thread) fail('--thread <id> is required.');
  const abs = path.resolve(args.file);
  const vaultRoot = process.env.TRACKCHANGES_ROOT || findVaultRoot(abs);
  if (!vaultRoot) fail(`Not inside an Obsidian vault: ${abs}`);
  let text = null;
  try { text = fs.readFileSync(abs, 'utf8'); } catch { /* store still loadable without it */ }
  const storePath = storePathFor(vaultRoot, abs);
  let store = loadStore(storePath, text);
  if (!store) {
    // The review may have just CLOSED (last change accepted → store
    // parked as .superseded) while this reply was in flight — revive
    // the thread rather than stranding the conversation.
    store = reviveThreadFromSuperseded(vaultRoot, abs, args.thread, text);
  }
  if (!store) fail(`No tracking store for ${abs}`);
  let res = addReply(store, args.thread, sessionLabel(), args.note, Date.now(), process.env.ROMP_SID || null);
  if (res.error && /thread/i.test(String(res.error))) {
    // Live store exists but the THREAD was resolved away — revive it INTO
    // the live store. Replacing the store with a revived one (as before)
    // saved a copy with an empty suggestion list over the live sidecar and
    // erased every pending change and every other comment in it.
    if (reviveThreadInto(vaultRoot, abs, args.thread, store)) {
      res = addReply(store, args.thread, sessionLabel(), args.note, Date.now(), process.env.ROMP_SID || null);
    }
  }
  if (res.error) fail(res.error);
  try { saveStore(vaultRoot, storePath, store, text); } catch { fail(`Could not write the store for ${abs}`); }
  process.stdout.write('Reply posted to thread.\n');
}

const invokedDirectly = (() => {
  try {
    return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch { return false; }
})();

if (invokedDirectly) run(process.argv.slice(2));
