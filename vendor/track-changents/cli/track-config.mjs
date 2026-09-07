#!/usr/bin/env node
// Agent CLI: report whether TRACKED-CHANGES is ON for a specific file.
// The tracked-changes skill runs this BEFORE editing to pick its mode:
//   "on"  → make changes with track-edit / track-comment / track-reply
//   "off" → edit normally with the Edit / Write tools
// Scope is the per-vault .trackchanges/config.json tracked-path list the editor's
// toggle maintains; a file is ON iff it is listed or under a listed folder/. An
// absent file or empty list means OFF. Prints "on" or "off" to stdout (exit 0
// when on, 1 when off) so the skill can branch either way.
//
//   node ~/.claude/hooks/track-config.mjs --file <abs path>

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { findVaultRoot, isTrackedFile } from '../store-io.mjs';
import { parseArgs } from './cli-args.mjs';

function run(argv) {
  const args = parseArgs(argv);
  if (!args.file) {
    process.stderr.write('--file <absolute path> is required.\n');
    process.exit(2);
  }
  const abs = path.resolve(args.file);
  const root = process.env.TRACKCHANGES_ROOT || findVaultRoot(abs);
  const on = root ? isTrackedFile(root, abs) : false;
  process.stdout.write(on ? 'on\n' : 'off\n');
  process.exit(on ? 0 : 1);
}

const invokedDirectly = (() => {
  try {
    return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch { return false; }
})();

if (invokedDirectly) run(process.argv.slice(2));
