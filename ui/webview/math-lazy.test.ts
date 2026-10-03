// KaTeX on demand (iOS item 6, 2026-10-02): the four bundles that carry the math grammar and the fill (render.js, feed.js,
// files.js, waiting.js) no longer carry KaTeX, about 86 KB served in each; KaTeX is its own entry, dist/math-chunk.js, which
// math.ts loads by script tag at the first formula a page meets (chunk-url.ts derives the tag's URL and nonce from the page's
// own bundle tag). The editor and PDF chunks are the precedent (editor-lazy.test.ts, pdf-lazy.test.ts): the contract is a
// global the chunk registers, so the pins here are the ones that keep the main bundles free of the library. Each bundle is
// built with the shipped webview config and read through esbuild's metafile, which names every input that reached it; the
// import scan reads code lines only, so a comment may name the package and an import, `import type` included, may not.
// The executed loading paths (the pending formula, the one request, the swap, the failures, a webview-shaped page) are in
// math-chunk-load-browser.test.ts, the viewer's hold in file-view-math-hold-browser.test.ts, and the served chat in
// tests/test_math_chunk_served.py.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const pkgRequire = createRequire(path.join(EXT, "package.json"));
const WEBVIEW = path.resolve(EXT, "..", "ui", "webview");
const W = (f: string) => fs.readFileSync(path.join(WEBVIEW, f), "utf8");
const ESBUILD = fs.readFileSync(path.join(EXT, "esbuild.js"), "utf8");
/** Code lines only: a comment may name the package (headers do); an import may not. */
const code = (s: string) => s.split("\n").filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join("\n");
const KATEX_INPUT = /node_modules\/katex\/dist\/katex\.(mjs|js)$/;
/** The bundles that import md-config.ts, and so math.ts: the ones that carried KaTeX before this change. */
const HOSTS = ["render", "feed", "files", "waiting"];

async function build(entry: string): Promise<{ inputs: string[]; js: string }> {
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  const r = await esbuild.build({ ...(webview as object), entryPoints: ["../ui/webview/" + entry], write: false, metafile: true, logLevel: "silent" });
  return { inputs: Object.keys(r.metafile!.inputs), js: r.outputFiles!.find((f) => f.path.endsWith(".js"))!.text };
}

test("the KaTeX chunk is its own webview entry, registering the library as the one global math.ts reads", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/math-chunk\.ts",/, "esbuild.js lists math-chunk.ts among the webview entries");
  const chunk = W("math-chunk.ts");
  assert.match(code(chunk), /^import katex from "katex";$/m);
  assert.match(code(chunk), /^\(globalThis as \{ __rompKatex\?: unknown \}\)\.__rompKatex = katex;$/m);
  assert.match(W("math.ts"), /const k = \(globalThis as \{ __rompKatex\?: MathEngine \}\)\.__rompKatex;/, "math.ts reads the same global");
  assert.match(W("math.ts"), /const tag = chunkScript\("math-chunk\.js"\);/, "and asks for the chunk by the entry's output name");
});

test("render.js, feed.js, files.js and waiting.js carry the grammar and the fill but no KaTeX; math-chunk.js carries KaTeX", { timeout: 180000 }, async () => {
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

test("no source that reaches a main bundle imports katex or the chunk, a type import included: the contract is the global", { timeout: 180000 }, async () => {
  // the population is derived, not listed: the whole webview build's metafile names every input of every output, so the sources
  // that reach a bundle other than the chunk are exactly its inputs under ui/webview; a type import leaves no trace in a
  // metafile, so each of those sources is read too (code lines only)
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  const r = await esbuild.build({ ...(webview as object), write: false, metafile: true, logLevel: "silent" });
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
