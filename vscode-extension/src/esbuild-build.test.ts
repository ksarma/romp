// esbuild.js's write step and its failure line, driven against synthetic entries in a scratch dir.
//
// The kernel rebuilds the served bundles in place by running `node esbuild.js` and, when that fails, puts
// the last 300 characters of its stderr in the notice that says the UI is stale. Two properties of the
// script are what that path relies on, and both broke the same way on the first build-required dependency
// the in-place rebuild could meet (pdfjs-dist, 2026-09-06, on a node_modules that predated it):
//   1. a failed build leaves dist/ exactly as it was — esbuild writes each build()'s outputs as that build
//      finishes, so the extension bundle used to land before the webview bundle failed, the kernel's cache
//      token (newest mtime under dist/) jumped, every open dashboard got a reload prompt for a build that
//      had not happened, and the drift pass read dist as newer than the sources it had just failed to build;
//   2. the last stderr line names the cause and, for a missing package, the cure — it used to be the tail
//      of a stack through esbuild's transport (`at Socket.emit`, `errors: [Getter/Setter]`).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createRequire } from "node:module";

// npm test runs in vscode-extension/, where esbuild.js lives. Required at run time rather than imported so
// the bundler leaves it alone: it loads the real esbuild package (a native binary) from node_modules.
const ESBUILD_JS = path.join(process.cwd(), "esbuild.js");
const { buildAll, failureSummary } = createRequire(__filename)(ESBUILD_JS);

const MISSING_PKG = "no-such-package-for-this-test";

function scratch(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "romp-esbuild-"));
}

// A minimal browser bundle config in the shape of esbuild.js's own: bundled, silent (the test asserts on the
// summary line, not esbuild's logger), outputs under <dir>/dist.
function cfg(dir: string, entry: string, out: string, extra: Record<string, unknown> = {}) {
  return { entryPoints: [path.join(dir, entry)], bundle: true, format: "iife", platform: "browser",
           outfile: path.join(dir, "dist", out), logLevel: "silent", ...extra };
}

async function failureOf(p: Promise<unknown>): Promise<any> {
  try { await p; } catch (e) { return e; }
  throw new Error("expected the build to fail");
}

test("a failed build writes nothing: an earlier bundle that built is not written and a stale dist is untouched", async () => {
  const d = scratch();
  try {
    fs.writeFileSync(path.join(d, "good.ts"), "export const n: number = 1;\nconsole.log(n);\n");
    fs.writeFileSync(path.join(d, "bad.ts"), `import "${MISSING_PKG}";\n`);
    // the finding's shape: dist holds an old build of the FIRST bundle, and the SECOND bundle fails
    fs.mkdirSync(path.join(d, "dist"));
    fs.writeFileSync(path.join(d, "dist", "good.js"), "OLD");
    const oldTime = new Date("2026-01-01T00:00:00Z");
    fs.utimesSync(path.join(d, "dist", "good.js"), oldTime, oldTime);

    const e = await failureOf(buildAll([cfg(d, "good.ts", "good.js"), cfg(d, "bad.ts", "bad.js")]));
    assert.ok(Array.isArray(e.errors) && e.errors.length === 1, "an esbuild BuildFailure with the one unresolved import");

    assert.deepEqual(fs.readdirSync(path.join(d, "dist")), ["good.js"], "no new file under dist");
    assert.equal(fs.readFileSync(path.join(d, "dist", "good.js"), "utf8"), "OLD", "the bundle that built was not written");
    assert.equal(fs.statSync(path.join(d, "dist", "good.js")).mtime.getTime(), oldTime.getTime(),
                 "its mtime stands: the kernel's cache token is the newest mtime under dist/, so a rewrite here " +
                 "means a reload prompt for a build that did not happen");
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
});

test("a build that succeeds writes every output of every bundle: code, sourcemaps, and file-loader assets in their subdir", async () => {
  const d = scratch();
  try {
    fs.writeFileSync(path.join(d, "note.txt"), "asset\n");
    fs.writeFileSync(path.join(d, "one.ts"), 'import u from "./note.txt";\nconsole.log(u);\n');
    fs.writeFileSync(path.join(d, "two.ts"), "console.log(2);\n");
    // the KaTeX-font shape: a `file` loader with assets under a subdirectory of dist
    const withAsset = cfg(d, "one.ts", "one.js", { loader: { ".txt": "file" }, assetNames: "assets/[name]-[hash]", sourcemap: true });
    const written: string[] = await buildAll([withAsset, cfg(d, "two.ts", "two.js", { sourcemap: true })]);

    const dist = path.join(d, "dist");
    for (const f of ["one.js", "one.js.map", "two.js", "two.js.map"]) {
      assert.ok(fs.existsSync(path.join(dist, f)), f + " written");
    }
    const assets = fs.readdirSync(path.join(dist, "assets"));
    assert.equal(assets.length, 1, "the asset landed in its subdirectory");
    assert.ok(/^note-[A-Z0-9]+\.txt$/i.test(assets[0]), assets[0]);
    assert.equal(fs.readFileSync(path.join(dist, "assets", assets[0]), "utf8"), "asset\n");
    // the return value is the written paths, one per output file
    const expected = ["one.js", "one.js.map", "two.js", "two.js.map", path.join("assets", assets[0])].map((f) => path.join(dist, f)).sort();
    assert.deepEqual([...written].sort(), expected);
    assert.ok(fs.readFileSync(path.join(dist, "two.js"), "utf8").includes("console.log(2)"), "the bundle is the built code");
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
});

test("failureSummary: an unresolvable package names it and the npm install cure, in one line the kernel's tail can carry whole", async () => {
  const d = scratch();
  try {
    fs.writeFileSync(path.join(d, "bad.ts"), `import "${MISSING_PKG}";\n`);
    // both faces of the pdfjs-dist failure: the source import of a bare specifier, and a node_modules/ path
    // named as an entry point of its own (the worker file) — two entry points, so outdir, as esbuild.js has
    const worker = "node_modules/" + MISSING_PKG + "/worker.mjs";   // 53 characters: shown whole, like the real 45-character pdf.worker path
    const c = { ...cfg(d, "bad.ts", "bad.js"), outfile: undefined, outdir: path.join(d, "dist"),
                entryPoints: [path.join(d, "bad.ts"), worker] };
    const e = await failureOf(buildAll([c]));
    assert.equal(e.errors.length, 2);

    const line: string = failureSummary(e, "dist/");
    assert.ok(!line.includes("\n"), "one line");
    assert.ok(line.length <= 300, "the kernel shows the last 300 characters of stderr; the whole line must fit: " + line.length);
    assert.ok(line.startsWith("esbuild.js: build failed with 2 errors; dist/ is unchanged."), line);
    assert.ok(line.includes(`"${MISSING_PKG}"`), "names the package: " + line);
    assert.ok(line.includes(`"${worker}"`), "names the worker path: " + line);
    assert.ok(line.includes("npm install"), "names the cure: " + line);
    assert.ok(!line.includes("Getter/Setter") && !line.includes(" at "), "no stack: " + line);
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
});

test("failureSummary: a relative import that does not exist, or a syntax error, gets the error and no npm cure", async () => {
  const d = scratch();
  try {
    fs.writeFileSync(path.join(d, "rel.ts"), 'import "./nowhere";\n');
    const rel: string = failureSummary(await failureOf(buildAll([cfg(d, "rel.ts", "rel.js")])), "dist/");
    assert.ok(rel.includes('"./nowhere"'), rel);
    assert.ok(!rel.includes("npm install"), "a relative import is a source error, not a missing dependency: " + rel);

    fs.writeFileSync(path.join(d, "syntax.ts"), "const = ;\n");
    const syn: string = failureSummary(await failureOf(buildAll([cfg(d, "syntax.ts", "syntax.js")])), "dist/");
    assert.ok(syn.startsWith("esbuild.js: build failed with 1 error; dist/ is unchanged."), syn);
    assert.ok(syn.includes("syntax.ts:1"), "the error's location: " + syn);
    assert.ok(!syn.includes("npm install"), syn);
    assert.ok(syn.length <= 300);
  } finally {
    fs.rmSync(d, { recursive: true, force: true });
  }
});

test("failureSummary: without the output-dir clause (watch and test modes), and for a non-esbuild error", () => {
  const e = Object.assign(new Error("Build failed with 1 error"), { errors: [{ text: 'Could not resolve "./x"', location: null }], warnings: [] });
  assert.equal(failureSummary(e, null), 'esbuild.js: build failed with 1 error. Unresolved: "./x".');
  assert.equal(failureSummary(new Error("boom")), "esbuild.js: build failed: boom");
});

test("failureSummary stays within the kernel's 300-character tail: long specifiers are shortened, a long list is counted", () => {
  const failure = (specs: string[]) => Object.assign(new Error("Build failed"), {
    errors: specs.map((s) => ({ text: `Could not resolve "${s}"`, location: null })), warnings: [] });
  const long = "node_modules/" + "a-very-long-package-name-".repeat(3) + "build/worker.mjs";
  assert.ok(long.length > 60);
  const one = failureSummary(failure([long]), "dist/");
  assert.ok(one.includes('"' + long.slice(0, 57) + '..."'), "a long specifier is cut with an ellipsis: " + one);
  assert.ok(one.includes("npm install"), one);
  const many = failureSummary(failure(["p1", "p2", "p3", "p4", "p5"]), "dist/");
  assert.ok(many.includes('"p1", "p2" (+3 more)'), "two named, the rest counted: " + many);
  assert.ok(!many.includes('"p3"'), many);
  for (const line of [one, many]) assert.ok(line.length <= 300 && !line.includes("\n"), line);
});

test("requiring esbuild.js runs no build: main() is gated on being the script", () => {
  // The tests above required the module and drove buildAll against scratch dirs; had main() run on require it
  // would have built the real bundles into the real dist/ (seconds, and a dist mtime bump) — pinned at the
  // source so a refactor cannot quietly drop the gate.
  const src = fs.readFileSync(ESBUILD_JS, "utf8");
  assert.ok(src.includes("if (require.main === module) {"), "main() runs only under `node esbuild.js`");
  assert.ok(src.includes("module.exports = { buildAll, failureSummary };"));
  assert.ok(src.includes("await buildAll([extension, webview]);"), "the production path IS the atomic write");
});
