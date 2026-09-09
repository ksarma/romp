#!/usr/bin/env node
// Launcher for tools/viewer-resize-bench.ts: the headless-Chromium bench of the real markdown viewer and Comments panel
// under the four interactions of the 2026-09-09 incident (mount with the panel open, a scroll sweep, a divider drag, an
// added comment). The bench itself is TypeScript because it imports ui/webview/real-viewer-leg.ts, the module the browser
// legs mount the real viewer with; this file bundles it with esbuild the way vscode-extension/esbuild.js bundles the test
// legs (cjs, platform node) and runs the bundle with cwd = <tree>/vscode-extension, the directory real-viewer-leg.ts
// resolves the tree under test from (its EXT = process.cwd(); no environment variable). So --tree runs the SAME bench over
// another checkout, a detached worktree at the incident's commit, say:
//   git -C ~/code/romp-perf-viewer-resize worktree add --detach ../romp-perf-viewer-resize-box1 32018f7a
//   (cd ~/code/romp-perf-viewer-resize-box1/vscode-extension && npm ci)
//   nice -n 19 node tools/viewer-resize-bench.mjs --tree ../romp-perf-viewer-resize-box1 --size large --comments 200
// The tree under test needs its own vscode-extension/node_modules (playwright, esbuild and the viewer's dependencies
// resolve from there); never commit a node_modules symlink. The bench source always comes from THIS repository.
//
// The process lowers its own priority to nice 19 (os.setPriority), which the bundler, the bench and Chromium inherit.
// Outputs: <out>/build/viewer-resize-bench.cjs (the bundle), <out>/runs/<id>.json, <out>/profiles/<id>.cpuprofile;
// <out> defaults to $HOME/.local/state/romp-perf/viewer-resize (--out-dir). See --help for the knobs.
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..");

const HELP = `usage: nice -n 19 node tools/viewer-resize-bench.mjs [options]

document (synthetic, seeded):
  --size small|medium|large|<lines>   about 300 / 3000 / 15000 lines (default medium)
  --lines N                           an exact line target (overrides --size)
  --variant mixed|prose|fence|table   presets for the knobs below (default mixed)
  --fence-share F  --fence-lines N    share of lines inside code fences; lines per fence
  --tables N  --table-rows R  --table-cols C
  --heading-every N  --list-every N   a heading / a list every N paragraphs
  --seed N                            PRNG seed (default 7)
review state (answered by the status poster, the panel's real path):
  --comments N                        comments anchored to unique passages, spread evenly (default 0)
  --hunks N                           tracked changes (ins, del, sub in turn) on words, spread evenly (default 0)
  --panel open|closed                 open the Comments panel after the mount (default open)
  --no-add                            skip the added-comment interaction
interactions:
  --interactions mount,scroll,drag,big,nudge,add   which to run (default all; mount always runs)
  --steps N  --w0 PX  --w1 PX         drag: N steps from pane width w0 to w1, one per animation frame (60, 1000, 700)
  --settle N                          frames measured after the last step (default 10)
  --scroll-frames N  --scroll-px PX   scroll sweep: N frames of PX each (60, 200)
environment:
  --viewport WxH                      the shell page (default 1600x900)
  --cpu-throttle R                    CDP Emulation.setCPUThrottlingRate (default 1)
  --cpu-profile  --sampling-us N      V8 profile of the whole run, written under <out>/profiles (1000 us)
  --timeout-s N                       kill the browser and record a timeout after N s (default 240)
  --label TEXT  --out-dir DIR  --tree DIR
`;

function main() {
  const argv = process.argv.slice(2);
  if (argv.includes("--help") || argv.includes("-h")) { process.stdout.write(HELP); return 0; }
  let tree = REPO;
  let outDir = path.join(os.homedir(), ".local", "state", "romp-perf", "viewer-resize");
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--tree") tree = path.resolve(argv[i + 1] || "");
    else if (argv[i].startsWith("--tree=")) tree = path.resolve(argv[i].slice(7));
    else if (argv[i] === "--out-dir") outDir = path.resolve(argv[i + 1] || "");
    else if (argv[i].startsWith("--out-dir=")) outDir = path.resolve(argv[i].slice(10));
  }
  const ext = path.join(tree, "vscode-extension");
  if (!fs.existsSync(path.join(ext, "package.json"))) { console.error(`no vscode-extension/package.json under ${tree}`); return 2; }
  if (!fs.existsSync(path.join(ext, "node_modules", "playwright")) || !fs.existsSync(path.join(ext, "node_modules", "esbuild"))) {
    console.error(`${ext}/node_modules lacks playwright or esbuild: run \`npm ci\` there first`); return 2;
  }
  try { os.setPriority(process.pid, 19); } catch { /* already at 19 or not permitted: the caller's nice stands */ }
  const require = createRequire(path.join(ext, "package.json"));
  const esbuild = require("esbuild");
  const buildDir = path.join(outDir, "build");
  fs.mkdirSync(buildDir, { recursive: true });
  const outfile = path.join(buildDir, "viewer-resize-bench.cjs");
  esbuild.buildSync({
    entryPoints: [path.join(HERE, "viewer-resize-bench.ts")],
    nodePaths: [path.join(ext, "node_modules")],
    bundle: true, format: "cjs", platform: "node", target: "node18", outfile, sourcemap: "inline", logLevel: "warning",
  });
  const r = spawnSync(process.execPath, [outfile, ...argv], { cwd: ext, stdio: "inherit", env: process.env });
  return r.status === null ? 1 : r.status;
}

process.exitCode = main();
