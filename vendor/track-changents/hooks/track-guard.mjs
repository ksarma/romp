#!/usr/bin/env node
// PreToolUse GUARD (the only track-changes hook). When an agent tries to edit a
// TRACKED file with the raw Edit / Write / MultiEdit tools, block the call and
// tell the agent to use track-edit instead — so the change lands as a reviewable
// tracked suggestion in the sidecar, not a silent write to the clean file.
//
// A file is tracked iff it is in its repo's .trackchanges/config.json path list
// (engine.isTracked, via store-io). UNTRACKED files — the default for everything
// — pass straight through, so this is a cheap no-op for normal editing. There is
// no session gate and no auto-capture: the deliberate path is the CLIs, and
// this guard just stops the raw tools from bypassing them on a tracked file.
//
// Blocks via exit code 2 with the reason on stderr (the PreToolUse "deny" that
// feeds the reason back to the model).

import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../store-io.mjs';

const TRACK_TOOLS = new Set(['Edit', 'Write', 'MultiEdit']);

// Returns a block reason string when the edit must be denied, or null to allow.
export function evaluate(raw) {
  let payload;
  try { payload = JSON.parse(raw); } catch { return null; }
  if (!payload || !TRACK_TOOLS.has(payload.tool_name)) return null;
  const file = payload.tool_input && payload.tool_input.file_path;
  if (!file) return null;
  // An image, a PDF or another binary cannot take a tracked edit (track-edit
  // refuses it: a text rewrite would destroy the file), so steering the agent
  // there would only strand it. Let the raw write through; the file is
  // regenerated, not edited. Checked by name first, before any disk walk.
  if (isNonTextPath(file)) return null;
  let root;
  try { root = process.env.TRACKCHANGES_ROOT || findVaultRoot(file); } catch { return null; }
  if (!root) return null;
  let tracked = false;
  try { tracked = isTrackedFile(root, file); } catch { return null; }
  if (!tracked) return null;
  // Same for a binary under a text-looking name (an extensionless blob, a
  // .dat): sniffed only now that the file is known to be tracked, so the
  // common untracked case costs no read.
  if (hasNulBytes(file)) return null;
  return `Track-changes is ON for this file, so ${payload.tool_name} is blocked here `
    + `(it would write the file silently). Make the change with track-edit so it lands as a `
    + `reviewable tracked suggestion:\n`
    + `  node ~/.claude/hooks/track-edit.mjs --file "${file}" --old "<exact unique text>" --new "<replacement>"`;
}

const invokedDirectly = (() => {
  try { return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url); }
  catch { return false; }
})();

if (invokedDirectly) {
  // romp-only (vendor/track-changents/patches/0004): romp's installer registers this guard
  // machine-wide, so it runs on every Edit/Write in every Claude Code session on the
  // machine — but it must act only in sessions romp launched. Both romp backends put
  // the session's stable id in its environment as ROMP_SID and hook commands inherit
  // that environment; no ROMP_SID means not a romp session, so pass the call through
  // before stdin is read. evaluate() above is unchanged.
  if (!process.env.ROMP_SID) process.exit(0);
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (c) => { raw += c; });
  process.stdin.on('end', () => {
    let reason = null;
    try { reason = evaluate(raw); } catch { reason = null; }
    if (reason) { process.stderr.write(reason + '\n'); process.exit(2); }
    process.exit(0);
  });
}
