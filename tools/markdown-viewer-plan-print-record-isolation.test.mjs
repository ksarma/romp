// The print follow-on's two plan modules under tools/ (tools/markdown-viewer-plan-print.test.mjs and
// tools/markdown-viewer-plan-print-record.test.mjs) run in CI's shell job from the repo root with NO node_modules
// (.github/workflows/ci.yml, `node --test tools/*.test.mjs vendor/track-changents/hooks/*.test.mjs`), so the property the job
// depends on is that each LOADS AND PASSES WITH NO node_modules REACHABLE. On 2026-09-21 the record module reached the
// compiler through a createRequire of vscode-extension's package and the job went red at load; the guard added then keyed on
// two spellings (createRequire, require() and a single-quoted static import line, and the round-7 review found a path-built
// dynamic import, a double-quoted static import, a two-line import and a side-effect import each green under it and red in
// the job (tests-4, extra6-2, extra10-1). This module keys the guard ON THE PROPERTY (the maintainer's cluster-F ruling,
// 2026-09-21): it builds a temp MIRROR of the repo (every top-level entry a symlink but .git; vscode-extension a real directory
// of symlinks to everything BUT node_modules; tools a real directory of symlinks with the module under test COPIED in, since
// node resolves a symlinked main module to its real path, which would put the real tree and its node_modules back under it),
// runs `node --test <mirror>/tools/<module>` as a CHILD PROCESS with NODE_TEST_CONTEXT deleted from its environment (node --test
// sets it in its children, and a grandchild --test that inherits it reports through the runner's protocol and exits 0 whatever
// it found: the first prototype stayed green under every plant for that reason), and holds the child's exit to 0. No text of
// the module is read, so no spelling satisfies it. The four spellings the review found, and the createRequire road that bit,
// are kept as executed PLANTS: a synthetic module carrying each road is written into a mirror without node_modules and run the
// same way, its child expected to exit non-zero naming the missing module (ERR_MODULE_NOT_FOUND, or Cannot find module for the
// require road), and into a mirror WITH node_modules linked, where each plant loads and passes, which is what makes it the
// shape the job alone catches. The record module keeps its static-specifier pin beside this guard as a diagnostic that names
// the offending specifier; the property is this module's. The census module (ui/webview/file-print.test.ts) builds a compiler
// program and is permanently a vscode-extension-leg module under npm test, where node_modules stands: its header says so, and
// this guard is why no part of it moves under tools/. Synthetic: only the repo's own text and a temp directory. This module
// names the two print modules and never itself. Run: node --test tools/markdown-viewer-plan-print-record-isolation.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const MODULES = ['markdown-viewer-plan-print.test.mjs', 'markdown-viewer-plan-print-record.test.mjs'];
const NODE_MODULES = path.join(REPO, 'vscode-extension', 'node_modules');

/** A temp mirror of the repo: the module named is a real copy under tools/, node_modules is absent, or a symlink to the real one
 *  when `withNodeModules`. `extra` writes synthetic files into the mirror's tools/ (the plants). */
function mirror(moduleFile, { withNodeModules = false, extra = {} } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'print-record-isolation-'));
  const link = (from, to) => fs.symlinkSync(from, to);
  for (const e of fs.readdirSync(REPO)) { if (e === '.git' || e === 'vscode-extension' || e === 'tools') continue; link(path.join(REPO, e), path.join(root, e)); }
  fs.mkdirSync(path.join(root, 'vscode-extension'));
  for (const e of fs.readdirSync(path.join(REPO, 'vscode-extension'))) { if (e === 'node_modules') continue; link(path.join(REPO, 'vscode-extension', e), path.join(root, 'vscode-extension', e)); }
  if (withNodeModules) link(NODE_MODULES, path.join(root, 'vscode-extension', 'node_modules'));
  fs.mkdirSync(path.join(root, 'tools'));
  for (const e of fs.readdirSync(path.join(REPO, 'tools'))) {
    if (e === moduleFile) fs.copyFileSync(path.join(REPO, 'tools', e), path.join(root, 'tools', e));   // a real copy: node realpaths a symlinked main module
    else link(path.join(REPO, 'tools', e), path.join(root, 'tools', e));
  }
  for (const [name, text] of Object.entries(extra)) fs.writeFileSync(path.join(root, 'tools', name), text);
  return root;
}
/** `node --test <mirror>/tools/<file>` as a child, the runner's context deleted so the child's exit is its own verdict. */
function runChild(root, file) {
  const env = { ...process.env, NODE_OPTIONS: '' };
  delete env.NODE_TEST_CONTEXT;   // set by node --test in this process; a grandchild --test under it reports through the runner's protocol and exits 0 whatever it found
  const r = spawnSync(process.execPath, ['--test', path.join(root, 'tools', file)], { cwd: root, encoding: 'utf8', timeout: 300000, env });
  const tail = (r.stdout + '\n' + r.stderr).split('\n').filter((l) => /Cannot find|ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND|^# (pass|fail)|^not ok/.test(l)).join('\n');
  return { status: r.status, tail };
}

for (const m of MODULES) {
  test(m + ' loads and passes with no node_modules reachable, the shell job\'s condition, run as a child from a mirror of the repo without vscode-extension/node_modules (the property, not a spelling: no text of the module is read)', () => {
    const root = mirror(m);
    try {
      assert.ok(!fs.existsSync(path.join(root, 'vscode-extension', 'node_modules')), 'the mirror has no node_modules');
      const r = runChild(root, m);
      assert.equal(r.status, 0, m + ' from a tree without node_modules: exit ' + r.status + '\n' + r.tail);
    } finally { fs.rmSync(root, { recursive: true, force: true }); }
  });
}

// the roads the round-7 review found green under the spelling guard and red in the job, each a synthetic module carrying one of
// them (the compiler's own file under vscode-extension/node_modules, a real target when node_modules stands), run from both
// mirrors: red without node_modules naming the missing module, green with them, so each is the job's shape and no other
const TS_FILE = "../vscode-extension/node_modules/typescript/lib/typescript.js";
const HEAD = "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\nimport path from 'node:path';\nimport { pathToFileURL, fileURLToPath } from 'node:url';\nimport { createRequire } from 'node:module';\nconst HERE = path.dirname(fileURLToPath(import.meta.url));\n";
const BODY = "test('the plant runs', () => { assert.ok(typeof tsRoad !== 'undefined' && tsRoad !== null, 'the compiler loaded'); });\n";
const PLANTS = [
  { name: 'dyn-path', road: "const tsRoad = await import(pathToFileURL(path.join(HERE, '..', 'vscode-extension', 'node_modules', 'typescript', 'lib', 'typescript.js')).href);\n", refuses: /ERR_MODULE_NOT_FOUND|Cannot find module/ },
  { name: 'static-dq', road: 'import * as tsRoad from "' + TS_FILE + '";\n', refuses: /ERR_MODULE_NOT_FOUND|Cannot find module/ },
  { name: 'static-twoline', road: "import\n  * as tsRoad from '" + TS_FILE + "';\n", refuses: /ERR_MODULE_NOT_FOUND|Cannot find module/ },
  { name: 'static-sideeffect', road: "import '" + TS_FILE + "';\nconst tsRoad = true;\n", refuses: /ERR_MODULE_NOT_FOUND|Cannot find module/ },
  { name: 'createRequire', road: "const tsRoad = createRequire(path.join(HERE, '..', 'vscode-extension', 'package.json'))('typescript');\n", refuses: /Cannot find module 'typescript'/ },
];
const TS_PRESENT = fs.existsSync(path.join(NODE_MODULES, 'typescript', 'lib', 'typescript.js'));

test('the plants: a path-built dynamic import, a double-quoted static import, a two-line import, a side-effect import and the createRequire road that bit the job on 2026-09-21, each a synthetic module run as a child from a mirror without node_modules, exits non-zero naming the missing module (FAILS BEFORE the property guard: each was green under the spelling pins while red in the job); and from a mirror with node_modules linked each loads and passes, so each is the job\'s own shape (skipped where this tree has no compiler to link, the mirror without one still refusing)', () => {
  const files = Object.fromEntries(PLANTS.map((p) => ['print-isolation-plant-' + p.name + '.test.mjs', HEAD + p.road + BODY]));
  const bare = mirror(MODULES[0], { extra: files });
  try {
    for (const p of PLANTS) {
      const r = runChild(bare, 'print-isolation-plant-' + p.name + '.test.mjs');
      assert.notEqual(r.status, 0, p.name + ': red without node_modules');
      assert.match(r.tail, p.refuses, p.name + ': the child names the missing module: ' + r.tail);
    }
  } finally { fs.rmSync(bare, { recursive: true, force: true }); }
  if (!TS_PRESENT) return;   // a tree with no compiler installed (the shell job's own): the refusing half above ran; the passing half needs the module to link
  const linked = mirror(MODULES[0], { withNodeModules: true, extra: files });
  try {
    for (const p of PLANTS) {
      const r = runChild(linked, 'print-isolation-plant-' + p.name + '.test.mjs');
      assert.equal(r.status, 0, p.name + ': green with node_modules linked, so the road is the one the job alone catches: ' + r.tail);
    }
  } finally { fs.rmSync(linked, { recursive: true, force: true }); }
});

test('this module names the two print modules and never itself, and the shell job runs every tools module', () => {
  const self = path.basename(fileURLToPath(import.meta.url));
  assert.ok(!MODULES.includes(self), 'no recursion: the guard is not among the modules it runs');
  for (const m of MODULES) assert.ok(fs.existsSync(path.join(REPO, 'tools', m)), m + ' stands under tools/');
  assert.ok(fs.readFileSync(path.join(REPO, '.github', 'workflows', 'ci.yml'), 'utf8').includes('run: node --test tools/*.test.mjs'), 'the shell job runs the tools modules, this one among them, from a tree with no node_modules');
});
