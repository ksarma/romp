// KaTeX on demand (iOS item 6, 2026-10-02): the bundles that carry the math grammar and the fill (render.js, feed.js,
// files.js, waiting.js and artifacts.js; HOSTS below, which the census here holds to the build's own list) no longer carry
// KaTeX, about 86 KB served in each; KaTeX is its own entry, dist/math-chunk.js, which math.ts loads by script tag at the
// first formula a page meets (chunk-url.ts derives the tag's URL and nonce from the page's own bundle tag). The editor and
// PDF chunks are the precedent (editor-lazy.test.ts, pdf-lazy.test.ts): the contract is a global the chunk registers, so
// the pins here are the ones that keep the main bundles free of the library. Each bundle is built with the shipped webview
// config and read through esbuild's metafile, which names every input that reached it; the import scan reads code lines
// only, so a comment may name the package and an import, `import type` included, may not.
// The executed loading paths (the pending formula, the one request, the swap, the failures, a webview-shaped page) are in
// math-chunk-load-browser.test.ts, the viewer's hold in file-view-math-hold-browser.test.ts, and the served chat in
// tests/test_math_chunk_served.py.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { BUNDLE_SRC } from "./chunk-url";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const pkgRequire = createRequire(path.join(EXT, "package.json"));
const WEBVIEW = path.resolve(EXT, "..", "ui", "webview");
const W = (f: string) => fs.readFileSync(path.join(WEBVIEW, f), "utf8");
const ESBUILD = fs.readFileSync(path.join(EXT, "esbuild.js"), "utf8");
/** Code lines only: a comment may name the package (headers do); an import may not. */
const code = (s: string) => s.split("\n").filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join("\n");
const KATEX_INPUT = /node_modules\/katex\/dist\/katex\.(mjs|js)$/;
/** The bundles that import md-config.ts, and so math.ts: the ones that carried KaTeX before this change. The census below derives
 *  them from the whole build, so a page bundle that comes to import the grammar fails it until it is named here and in
 *  chunk-url.ts's BUNDLE_SRC. */
const HOSTS = ["render", "feed", "files", "waiting", "artifacts"];

async function build(entry: string): Promise<{ inputs: string[]; js: string }> {
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  const r = await esbuild.build({ ...(webview as object), entryPoints: ["../ui/webview/" + entry], write: false, metafile: true, logLevel: "silent" });
  return { inputs: Object.keys(r.metafile!.inputs), js: r.outputFiles!.find((f) => f.path.endsWith(".js"))!.text };
}

let whole: Promise<import("esbuild").BuildResult> | null = null;
/** The whole webview build, every entry, with a metafile: built once for the two tests that read every output. */
function wholeBuild(): Promise<import("esbuild").BuildResult> {
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  if (!whole) whole = esbuild.build({ ...(webview as object), write: false, metafile: true, logLevel: "silent" });
  return whole;
}

test("the KaTeX chunk is its own webview entry, registering the library as the one global math.ts reads", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/math-chunk\.ts",/, "esbuild.js lists math-chunk.ts among the webview entries");
  const chunk = W("math-chunk.ts");
  assert.match(code(chunk), /^import katex from "katex";$/m);
  assert.match(code(chunk), /^\(globalThis as \{ __rompKatex\?: unknown \}\)\.__rompKatex = katex;$/m);
  assert.match(W("math.ts"), /const k = \(globalThis as \{ __rompKatex\?: MathEngine \}\)\.__rompKatex;/, "math.ts reads the same global");
  assert.match(W("math.ts"), /const tag = chunkScript\("math-chunk\.js"\);/, "and asks for the chunk by the entry's output name");
});

test("every bundle in HOSTS (render.js, feed.js, files.js, waiting.js, artifacts.js) carries the grammar and the fill but no KaTeX; math-chunk.js carries KaTeX", { timeout: 180000 }, async () => {
  for (const entry of HOSTS) {
    const { inputs, js } = await build(entry + ".ts");
    assert.deepEqual(inputs.filter((k) => k.includes("katex")), [], entry + ".js has no KaTeX input");
    assert.ok(inputs.includes("../ui/webview/math.ts"), entry + ".js bundles math.ts (the grammar and the fill)");
    assert.ok(inputs.includes("../ui/webview/chunk-url.ts"), entry + ".js bundles the chunk loader's URL rule");
    assert.ok(!inputs.includes("../ui/webview/math-chunk.ts"), entry + ".js does not bundle the chunk");
    assert.ok(!js.includes("KaTeX parse error"), entry + ".js carries none of KaTeX's own text");
  }
  const { inputs, js } = await build("math-chunk.ts");
  assert.ok(inputs.some((k) => KATEX_INPUT.test(k)), "math-chunk.js bundles KaTeX: " + inputs.join(","));
  assert.ok(js.includes("KaTeX parse error") && js.includes("__rompKatex"), "math-chunk.js carries KaTeX and registers it");
  assert.ok(!inputs.includes("../ui/webview/math.ts"), "the chunk carries KaTeX alone, not the grammar");
});

test("HOSTS is every bundle the build gives the math grammar, and chunk-url.ts's fallback knows each of them by name", { timeout: 180000 }, async () => {
  // derived, not listed: a page bundle takes md-config.ts, and the grammar with it, from any source that imports it, the viewer
  // included (the Artifacts pane's bundle took it by importing file-view.ts), and the pins above and the fallback cover only the
  // bundles they name
  const r = await wholeBuild();
  const hosts = Object.entries(r.metafile!.outputs)
    .filter(([out, meta]) => out.endsWith(".js") && Object.prototype.hasOwnProperty.call(meta.inputs, "../ui/webview/md-config.ts"))
    .map(([out]) => path.basename(out, ".js")).sort();
  assert.ok(hosts.includes("render") && hosts.includes("files"), "the derivation finds the chat's and the Files pane's bundles: " + hosts.join(","));
  assert.deepEqual(hosts, [...HOSTS].sort(), "HOSTS names every webview bundle that bundles md-config.ts, and only those");
  for (const b of hosts) {
    assert.ok(BUNDLE_SRC.test("/dist/" + b + ".js?v=1"), b + ".js is in chunk-url.ts's BUNDLE_SRC, the fallback for a page whose bundle ran from no src");
  }
});

test("no source that reaches a main bundle imports katex or the chunk, a type import included: the contract is the global", { timeout: 180000 }, async () => {
  // the population is derived, not listed: the whole webview build's metafile names every input of every output, so the sources
  // that reach a bundle other than the chunk are exactly its inputs under ui/webview; a type import leaves no trace in a
  // metafile, so each of those sources is read too (code lines only)
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const r = await wholeBuild();
  const reached = new Set<string>();
  let outputs = 0;
  for (const [out, meta] of Object.entries(r.metafile!.outputs)) {
    if (!out.endsWith(".js") || out.endsWith("math-chunk.js")) continue;
    outputs++;
    for (const inp of Object.keys(meta.inputs)) {
      assert.ok(!KATEX_INPUT.test(inp) && !inp.includes("node_modules/katex/"), out + " carries KaTeX through " + inp);
      assert.notEqual(inp, "../ui/webview/math-chunk.ts", out + " carries the chunk");
      reached.add(inp);
    }
  }
  const jsEntries = (webview.entryPoints as Array<string | { in: string; out: string }>).filter((e) => typeof e !== "string" || /\.ts$/.test(e)).length;
  assert.equal(outputs, jsEntries - 1, "every script entry's output but the chunk's was read");
  const sources = [...reached].filter((k) => k.startsWith("../ui/webview/") && /\.(ts|js)$/.test(k)).map((k) => k.slice("../ui/webview/".length)).sort();
  for (const must of ["math.ts", "md-config.ts", "render.ts", "file-view.ts", "feed.ts", "files.ts", "waiting.ts", "chunk-url.ts"]) {
    assert.ok(sources.includes(must), must + " is among the sources that reach a main bundle");
  }
  for (const f of sources) {
    assert.doesNotMatch(code(W(f)), /from "katex"|import\("katex"\)|require\("katex"\)|from "\.\/math-chunk"|require\("\.\/math-chunk"\)|import "\.\/math-chunk"/,
      f + " must not import KaTeX or the chunk: an import would drag KaTeX back into a main bundle");
  }
  const src = path.join(EXT, "src");
  for (const f of fs.readdirSync(src).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts"))) {
    assert.doesNotMatch(code(fs.readFileSync(path.join(src, f), "utf8")), /from "katex"/, "src/" + f);
  }
});
