// The URL math.ts loads the KaTeX chunk from (chunk-url.ts; iOS item 6, 2026-10-02): the page's own bundle tag with the
// file name swapped, the directory and the query (the kernel's ?v= token) kept, and the tag's nonce copied, since the VS Code
// webviews' Content-Security-Policy allows a script by nonce alone (extension.ts buildHtml). Pure: the tags and the page are
// plain stand-ins with the two properties and the one query the helper reads. math-lazy.test.ts pins the bundles.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { chunkSrcFor, chunkScript, BUNDLE_SRC } from "./chunk-url";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const W = (f: string) => fs.readFileSync(path.join(WEBVIEW, f), "utf8");
const HOSTS = ["render", "feed", "files", "waiting"];

test("the chunk's URL is the bundle's own with the file name swapped: the kernel's ?v= token and the webview's resource root are kept", () => {
  const K = "http://TESTHOST:29855/dist/", V = "?v=1759363200";
  for (const b of HOSTS) assert.equal(chunkSrcFor(K + b + ".js" + V, "math-chunk.js"), K + "math-chunk.js" + V, b + ".js");
  const R = "https://file+.vscode-resource.vscode-cdn.net/ext/dist/";
  assert.equal(chunkSrcFor(R + "render.js", "math-chunk.js"), R + "math-chunk.js", "the VS Code webview: no query, same directory");
  assert.equal(chunkSrcFor(K + "feed.js#x", "math-chunk.js"), K + "math-chunk.js#x");
  assert.equal(chunkSrcFor(K + "settings-page.js" + V, "math-chunk.js"), K + "math-chunk.js" + V, "any bundle name: the tag is the page's own");
  assert.equal(chunkSrcFor("http://TESTHOST:29855/chat", "math-chunk.js"), null, "a path that is no .js file gives no URL");
  assert.equal(chunkSrcFor("", "math-chunk.js"), null);
});

test("chunkScript takes the tag the bundle ran from, copies its nonce, falls back to a bundle by name, and gives null with neither", () => {
  const tag = (src: string, nonce = "") => ({ src, nonce }) as unknown as HTMLScriptElement;
  const page = (srcs: string[]) => ({ querySelectorAll: (sel: string) => (sel === "script[src]" ? srcs.map((s) => tag(s)) : []) }) as unknown as Document;
  const K = "http://TESTHOST:29855/dist/";
  assert.deepEqual(chunkScript("math-chunk.js", tag(K + "files.js?v=3", "n0nce"), page([])), { src: K + "math-chunk.js?v=3", nonce: "n0nce" },
    "the webview's CSP allows a script by nonce alone, so the chunk tag carries the bundle tag's");
  assert.deepEqual(chunkScript("math-chunk.js", tag(""), page(["/media/x.js", K + "waiting.js?v=4"])), { src: K + "math-chunk.js?v=4", nonce: "" },
    "an inline own script (a test that inlines its bundle) falls back to the page's bundle tag by name");
  assert.deepEqual(chunkScript("math-chunk.js", null, page([K + "feed.js?v=5"])), { src: K + "math-chunk.js?v=5", nonce: "" });
  assert.equal(chunkScript("math-chunk.js", null, page(["/media/x.js"])), null, "no bundle tag: no URL, and math.ts fails loudly");
  assert.equal(chunkScript("math-chunk.js", null, null), null);
  for (const b of HOSTS) assert.ok(BUNDLE_SRC.test(K + b + ".js?v=1"), b + ".js is a fallback bundle");
  assert.ok(!BUNDLE_SRC.test(K + "render.js.map"), "a source map is not a bundle");
  // the own tag is read once, at module init, while the bundle's classic script runs
  assert.match(W("chunk-url.ts"), /^const OWN: HTMLScriptElement \| null = typeof document !== "undefined" \? \(document\.currentScript as HTMLScriptElement \| null\) : null;$/m);
  assert.match(W("math.ts"), /sc\.src = tag\.src;\n\s*if \(tag\.nonce\) sc\.nonce = tag\.nonce;/, "math.ts puts the derived src and the nonce on its tag");
});
