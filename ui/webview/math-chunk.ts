// KaTeX in its own bundle (dist/math-chunk.js), loaded on demand: math.ts's fill asks for it the first time a page meets a
// formula, through a script tag whose URL it derives from the page's own bundle tag (chunk-url.ts), so a page that shows no
// math never downloads KaTeX, and the pages that do (the chat, the feed, the Files, Waiting and Artifacts panes, the VS Code
// webviews) share one cached copy instead of carrying one each inside render.js, feed.js, files.js, waiting.js and
// artifacts.js. The contract is the global below and nothing else: no main-bundle source imports this module or katex
// (math-lazy.test.ts reads every import and every bundle's inputs). A test bundle that wants the synchronous fill imports
// this module for its side effect.
import katex from "katex";

(globalThis as { __rompKatex?: unknown }).__rompKatex = katex;
