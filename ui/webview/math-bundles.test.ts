// Decision 1 of plans/markdown-viewer.md (math everywhere; ruling 2026-09-07): KaTeX and the math grammar ship in the
// files and feed bundles too, so a file's math renders wherever the file is shown. Before Slice 4 the grammar reached
// render.js alone (chat-md.ts, imported by render.ts), and the same note showed KaTeX in the chat page's viewer and
// literal TeX in the Files pane and the feed. The check is the plan's own: a metafile of each bundle built with the
// shipped config (editor-lazy.test.ts's precedent) holds math.ts, md-config.ts and katex among its inputs. The
// sizes are recorded in the plan's Slice 4 build note, not pinned: they move with every dependency bump.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { createRequire } from "node:module";
import * as path from "node:path";

const pkgRequire = createRequire(path.join(process.cwd(), "package.json"));   // npm test runs in vscode-extension

test("files.js, feed.js and render.js each bundle math.ts, md-config.ts and katex; the viewer never imports render.ts to get them", { timeout: 120000 }, async () => {
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  for (const entry of ["files", "feed", "render"]) {
    const r = await esbuild.build({ ...(webview as object), entryPoints: [`../ui/webview/${entry}.ts`], write: false, metafile: true, logLevel: "silent" });
    const inputs = Object.keys(r.metafile!.inputs);
    assert.ok(inputs.includes("../ui/webview/math.ts"), entry + ".js bundles math.ts (the grammar and the fill)");
    assert.ok(inputs.includes("../ui/webview/md-config.ts"), entry + ".js bundles md-config.ts (the one configuration)");
    assert.ok(inputs.some((k) => /node_modules\/katex\/dist\/katex\.(mjs|js)$/.test(k)), entry + ".js bundles KaTeX: " + inputs.filter((k) => k.includes("katex")).join(","));
    assert.ok(inputs.includes("../ui/webview/figure-gate.ts"), entry + ".js bundles the figure gate (file-view.ts imports it)");
    if (entry !== "render") assert.ok(!inputs.includes("../ui/webview/render.ts"), entry + ".js carries the chat's render.ts nowhere (code-block.test.ts pins the imports)");
    const js = r.outputFiles!.find((f) => f.path.endsWith(".js"))!.text;
    assert.ok(js.includes("md-math-inline") && js.includes("KaTeX parse error"), entry + ".js carries the placeholder class and KaTeX's own text");
  }
});

test("feed.css built as the webview build builds it carries KaTeX's layout classes inline and emits the fonts, as styles.css does", { timeout: 120000 }, async () => {
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
  for (const sheet of ["feed", "styles"]) {
    const r = await esbuild.build({ ...(webview as object), entryPoints: [`../ui/webview/${sheet}.css`], write: false, metafile: true, logLevel: "silent" });
    const css = r.outputFiles!.find((f) => f.path.endsWith(".css"))!.text;
    assert.ok(css.includes(".katex-html"), sheet + ".css inlines katex.min.css (esbuild resolves the @import through nodePaths)");
    assert.ok(!css.includes('@import "katex'), sheet + ".css leaves no @import behind for the page to fetch");
    assert.ok(Object.keys(r.metafile!.inputs).some((k) => k.endsWith("katex/dist/katex.min.css")), sheet + ".css: the KaTeX sheet is an input");
    const fonts = r.outputFiles!.filter((f) => /\/fonts\/KaTeX_[^/]+\.woff2$/.test(f.path)).length;
    assert.ok(fonts >= 20, sheet + ".css emits the woff2 fonts under fonts/ (the same hashed names from both sheets, so one copy on disk): " + fonts);
  }
});
