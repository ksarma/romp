// viewer-resize-bench: the REAL markdown viewer (ui/webview/file-view.ts, and through it the real Comments panel) on the
// Files pane surface, inside a same-origin iframe of a shell page that copies the dashboard's pane row, driven through
// the four interactions that were slow on 2026-09-09 (a big reviewed markdown file with many comments and tracked
// changes, the Comments panel open): (1) MOUNT: openFileView to the rendered document, then the panel opening until every
// card has its place; (2) SCROLL: N animation frames of `scrollPx` each on the viewer body, then a settle; (3) DRAG: the
// pane divider, N steps of a few px, one per animation frame, written the way the shell writes them (two flex-grow custom
// properties on the row, kernel/kernel.py setGrow), then a settle; then one single big resize back and a 1px nudge;
// (4) ADD: one more comment landing through the panel's own refresh (the poll sees the sidecar's mtime move, asks status,
// the poster answers with N+1 comments), timed from the reply to the cards being placed.
//
// Per interaction: rAF-to-rAF frame times (ms), CDP Performance.getMetrics deltas (LayoutCount, LayoutDuration,
// RecalcStyleCount, RecalcStyleDuration, ScriptDuration, TaskDuration, Nodes, JSHeapUsedSize; the Performance domain counts
// the whole local frame tree, so the pane's layouts are in), and the long-animation-frame entries (blocking ms, script
// attribution) from the shell window and from the pane document. Measured 2026-09-09 (a busy rAF and a busy
// ResizeObserver callback inside the iframe): Chromium reports a long frame whose work ran in a same-origin iframe to the
// TOP-LEVEL window only, attributed by callback type (FrameRequestCallback, ResizeObserverCallback); the iframe's own
// observer sees nothing. So `loaf_shell` carries the entries and `loaf_pane` stays empty by design; on the dashboard the
// same rule sends the Files pane's long frames to the shell page, which has no observer, which is why no pane recorded
// the incident's frames. With --cpu-profile a V8 profile of the whole run is written under the output dir and folded to
// self time by function, each bundle line mapped to its source file through esbuild's module banners (top 25 printed;
// per-interaction top 12 in the JSON). The `nudge` interaction (a 1px width change) stands for one full panel pass
// (paintAll, seat, placeCards) over a reflow that moves nothing; `add` is one pass plus the aside's rebuild. A run that
// exceeds --timeout-s is killed and recorded as a timeout: that is a reproduction, not a failure of the bench. One JSON per
// run under <out>/runs/, one summary line on stdout.
//
// The document is SYNTHETIC (a seeded generator: lorem-like prose, headings, lists, code fences, tables, a little inline
// math, a few links); the comments anchor to unique passages in it and the tracked changes sit on words of it. No real
// file, transcript or session data is ever read. Paths and the sid are the legs' conventions (/repo/notes-api, the
// placeholder sid).
//
// Run it through tools/viewer-resize-bench.mjs (which bundles this file with esbuild and runs it from
// <tree>/vscode-extension, the cwd real-viewer-leg.ts resolves the tree under test from):
//   nice -n 19 node tools/viewer-resize-bench.mjs --size medium --comments 200 --hunks 200 --panel open --cpu-profile
//   nice -n 19 node tools/viewer-resize-bench.mjs --tree ../romp-perf-viewer-resize-box1 --size large --variant fence
// The .mjs prints the full option list with --help.
import * as fs from "node:fs";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { pageHtml, frames, REPORT, SID, ORIGIN, STATUS, MT, requireCjs, EXT } from "../ui/webview/real-viewer-leg";

// ── options ─────────────────────────────────────────────────────────────────────────────────────────
type Opts = {
  size: string; lines: number; variant: string; fenceShare: number; fenceLines: number; tables: number; tableRows: number; tableCols: number;
  headingEvery: number; listEvery: number; seed: number;
  comments: number; hunks: number; panel: "open" | "closed"; add: boolean;
  steps: number; w0: number; w1: number; settle: number; scrollFrames: number; scrollPx: number;
  viewport: { width: number; height: number }; cpuThrottle: number; cpuProfile: boolean; samplingUs: number;
  timeoutS: number; label: string; outDir: string; interactions: Set<string>; tree: string;
};
const SIZES: Record<string, number> = { small: 300, medium: 3000, large: 15000 };
const VARIANTS: Record<string, Partial<Opts>> = {
  mixed: { fenceShare: 0.25, fenceLines: 20, tables: 20, tableRows: 8, tableCols: 5 },
  prose: { fenceShare: 0, fenceLines: 20, tables: 0, tableRows: 8, tableCols: 5 },
  fence: { fenceShare: 0.6, fenceLines: 40, tables: 4, tableRows: 8, tableCols: 5 },
  table: { fenceShare: 0.05, fenceLines: 20, tables: 80, tableRows: 20, tableCols: 6 },
};
export function parseOpts(argv: string[]): Opts {
  const o: Opts = {
    size: "medium", lines: 0, variant: "mixed", fenceShare: 0.25, fenceLines: 20, tables: 20, tableRows: 8, tableCols: 5,
    headingEvery: 6, listEvery: 5, seed: 7,
    comments: 0, hunks: 0, panel: "open", add: true,
    steps: 60, w0: 1000, w1: 700, settle: 10, scrollFrames: 60, scrollPx: 200,
    viewport: { width: 1600, height: 900 }, cpuThrottle: 1, cpuProfile: false, samplingUs: 1000,
    timeoutS: 240, label: "", outDir: path.join(process.env.HOME || "", ".local", "state", "romp-perf", "viewer-resize"),
    interactions: new Set(["mount", "scroll", "drag", "big", "nudge", "add"]), tree: path.resolve(EXT, ".."),
  };
  const num = (v: string, name: string): number => { const n = Number(v); if (!Number.isFinite(n)) throw new Error(`--${name} needs a number, got ${v}`); return n; };
  let variantSet = false;
  const rest: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) throw new Error(`unexpected argument ${a}`);
    const eq = a.indexOf("=");
    const k = eq >= 0 ? a.slice(2, eq) : a.slice(2);
    const flag = k === "cpu-profile" || k === "no-add" || k === "help";
    const v = eq >= 0 ? a.slice(eq + 1) : flag ? "" : argv[++i];
    if (v === undefined) throw new Error(`--${k} needs a value`);
    rest[k] = v;
  }
  if ("variant" in rest) { variantSet = true; o.variant = rest.variant; if (!VARIANTS[o.variant]) throw new Error(`--variant one of ${Object.keys(VARIANTS).join(", ")}`); }
  Object.assign(o, VARIANTS[o.variant]);
  for (const [k, v] of Object.entries(rest)) {
    switch (k) {
      case "size": o.size = v; break;
      case "lines": o.lines = num(v, k); break;
      case "variant": break;
      case "fence-share": o.fenceShare = num(v, k); break;
      case "fence-lines": o.fenceLines = num(v, k); break;
      case "tables": o.tables = num(v, k); break;
      case "table-rows": o.tableRows = num(v, k); break;
      case "table-cols": o.tableCols = num(v, k); break;
      case "heading-every": o.headingEvery = num(v, k); break;
      case "list-every": o.listEvery = num(v, k); break;
      case "seed": o.seed = num(v, k); break;
      case "comments": o.comments = num(v, k); break;
      case "hunks": o.hunks = num(v, k); break;
      case "panel": if (v !== "open" && v !== "closed") throw new Error("--panel open|closed"); o.panel = v; break;
      case "no-add": o.add = false; break;
      case "steps": o.steps = num(v, k); break;
      case "w0": o.w0 = num(v, k); break;
      case "w1": o.w1 = num(v, k); break;
      case "settle": o.settle = num(v, k); break;
      case "scroll-frames": o.scrollFrames = num(v, k); break;
      case "scroll-px": o.scrollPx = num(v, k); break;
      case "viewport": { const m = /^(\d+)x(\d+)$/.exec(v); if (!m) throw new Error("--viewport WxH"); o.viewport = { width: Number(m[1]), height: Number(m[2]) }; break; }
      case "cpu-throttle": o.cpuThrottle = num(v, k); break;
      case "cpu-profile": o.cpuProfile = true; break;
      case "sampling-us": o.samplingUs = num(v, k); break;
      case "timeout-s": o.timeoutS = num(v, k); break;
      case "label": o.label = v; break;
      case "out-dir": o.outDir = v; break;
      case "interactions": o.interactions = new Set(v.split(",").map((s) => s.trim()).filter(Boolean)); break;
      case "tree": break;   // consumed by the launcher; the tree under test is the cwd's (real-viewer-leg.ts)
      case "help": break;
      default: throw new Error(`unknown option --${k}`);
    }
  }
  if (!o.lines) { o.lines = SIZES[o.size] ?? Number(o.size); if (!Number.isFinite(o.lines) || o.lines <= 0) throw new Error("--size small|medium|large|<lines>"); }
  // a variant's table count is per 15000 lines (the large size); a smaller document keeps the same density, at least one
  if (!("tables" in rest) && o.tables > 0) o.tables = Math.max(1, Math.round((o.tables * o.lines) / 15000));
  if (!variantSet) o.variant = "mixed";
  if (!o.add) o.interactions.delete("add");
  if (o.panel === "closed") o.interactions.delete("add");
  return o;
}

// ── the synthetic document ──────────────────────────────────────────────────────────────────────────
/** mulberry32: a small seeded PRNG, so a run at the same knobs renders the same bytes. */
function prng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const WORDS = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua "
  + "enim ad minim veniam quis nostrud exercitation ullamco laboris nisi aliquip ex ea commodo consequat duis aute irure in "
  + "reprehenderit voluptate velit esse cillum fugiat nulla pariatur excepteur sint occaecat cupidatat non proident sunt culpa "
  + "qui officia deserunt mollit anim id est laborum cache latency baseline variance epoch batch gradient checkpoint metric").split(" ");
export type Paragraph = { index: number; start: number; quote: string; suffix: string; wordStart: number; wordEnd: number };
export type Doc = { text: string; paragraphs: Paragraph[]; stats: { lines: number; chars: number; paragraphs: number; fences: number; fenceLines: number; tables: number; headings: number; lists: number } };

/** Generate about `lines` lines of markdown. Paragraph i opens with a unique sentence ("Item i of the note ..."), which the
 *  comments quote; the word after that sentence carries the tracked change. Fences take `fenceShare` of the lines in
 *  fences of `fenceLines` lines; `tables` tables of rows x cols are spread evenly; a heading every `headingEvery`
 *  paragraphs, a list every `listEvery`, a little inline math and a display block now and then, a link every fifth. */
export function makeDoc(o: { lines: number; fenceShare: number; fenceLines: number; tables: number; tableRows: number; tableCols: number; headingEvery: number; listEvery: number; seed: number }): Doc {
  const rnd = prng(o.seed);
  const pick = () => WORDS[Math.floor(rnd() * WORDS.length)];
  const sentence = (n: number) => { const ws: string[] = []; for (let i = 0; i < n; i++) ws.push(pick()); ws[0] = ws[0][0].toUpperCase() + ws[0].slice(1); return ws.join(" ") + "."; };
  const parts: string[] = [];
  const paragraphs: Paragraph[] = [];
  let len = 0, lines = 0;
  const stats = { lines: 0, chars: 0, paragraphs: 0, fences: 0, fenceLines: 0, tables: 0, headings: 0, lists: 0 };
  const push = (s: string) => { parts.push(s); len += s.length; for (let i = 0; i < s.length; i++) if (s.charCodeAt(i) === 10) lines++; };
  // proportional control: paragraphs until the line target is reached; a fence whenever the fence lines so far fall under
  // their share of the lines so far; table t once the text has reached the t-th share of the target, so tables spread evenly
  const target = Math.max(20, o.lines);
  const wantFence = () => o.fenceShare > 0 && o.fenceLines > 0 && stats.fenceLines < o.fenceShare * lines;
  const wantTable = () => o.tables > 0 && tablesOut < o.tables && tablesOut < Math.ceil((o.tables * lines) / target);
  push("# Experiments note (synthetic)\n\n");
  let section = 0, fencesOut = 0, tablesOut = 0;
  for (let i = 0; lines < target || i < 4; i++) {
    if (i % o.headingEvery === 0) { section++; push(`${section % 4 === 1 ? "##" : "###"} Section ${section}: ${sentence(3).slice(0, -1)}\n\n`); stats.headings++; }
    const start = len;
    const quote = `Item ${i} of the note ${sentence(4).toLowerCase()}`;
    const word = pick() + pick();                                          // a made-up word, so the change sits on a unique token
    const tail = sentence(6 + Math.floor(rnd() * 8)) + " " + sentence(5 + Math.floor(rnd() * 6));
    let body = quote + " " + word + " " + tail;
    if (i % 7 === 3) body += " The bound is $\\alpha_i \\le \\frac{1}{n}$ for every $i$.";
    if (i % 5 === 2) body += ` See [the API notes](https://example.invalid/notes-api/${i}).`;
    const wordStart = start + quote.length + 1;
    paragraphs.push({ index: i, start, quote, suffix: (" " + word + " " + tail).slice(0, 24), wordStart, wordEnd: wordStart + word.length });
    push(body + "\n\n");
    stats.paragraphs++;
    if (i % o.listEvery === 4) { const n = 3 + Math.floor(rnd() * 3); for (let k = 0; k < n; k++) push(`- ${sentence(4 + Math.floor(rnd() * 5))}\n`); push("\n"); stats.lists++; }
    if (i % 11 === 6) push("$$\nE = \\sum_i w_i x_i + \\lambda \\lVert w \\rVert^2\n$$\n\n");
    if (wantFence()) {
      push("```python\n");
      for (let k = 0; k < o.fenceLines; k++) {
        const kind = k % 4;
        push(kind === 0 ? `def step_${fencesOut}_${k}(x, y):\n` : kind === 1 ? `    total = x * ${Math.floor(rnd() * 100)} + y  # ${pick()} ${pick()}\n`
          : kind === 2 ? `    if total > ${Math.floor(rnd() * 1000)}: return "${pick()}"\n` : `    return [total, ${rnd().toFixed(4)}, "${pick()}_${pick()}"]\n`);
      }
      push("```\n\n"); fencesOut++; stats.fences++; stats.fenceLines += o.fenceLines;
    }
    if (wantTable()) {
      const head = Array.from({ length: o.tableCols }, (_, c) => (c === 0 ? "run" : pick()));
      push("| " + head.join(" | ") + " |\n|" + head.map(() => " ---: ").join("|") + "|\n");
      for (let r = 0; r < o.tableRows; r++) push("| " + Array.from({ length: o.tableCols }, (_, c) => (c === 0 ? `r${tablesOut}-${r}` : (rnd() * 100).toFixed(2))).join(" | ") + " |\n");
      push("\n"); tablesOut++; stats.tables++;
    }
  }
  const text = parts.join("");
  stats.lines = lines; stats.chars = text.length;
  return { text, paragraphs, stats };
}

const T0 = 1757145600000;
/** `n` comments spread evenly over the paragraphs, each quoting its paragraph's opening sentence. `phase` shifts the pick
 *  so a later batch (the ADD interaction) lands on paragraphs the first batch left alone. */
export function makeComments(doc: Doc, n: number, phase = 0.5): Array<Record<string, unknown>> {
  const P = doc.paragraphs.length;
  const out: Array<Record<string, unknown>> = [];
  for (let k = 0; k < n; k++) {
    const p = doc.paragraphs[Math.min(P - 1, Math.floor(((k + phase) * P) / Math.max(n, 1)))];
    out.push({ id: `${T0 + k}-${k}`, author: "you", ts: T0 + k, body: `Note ${k}: check this claim against the run log.`,
      anchor: { quote: p.quote, prefix: "", suffix: p.suffix }, anchorAt: p.start, replies: [], resolved: false });
  }
  return out;
}
/** `m` tracked changes (ins, del, sub in turn) on the made-up word after the opening sentence of evenly spread paragraphs. */
export function makeHunks(doc: Doc, m: number): Array<Record<string, unknown>> {
  const P = doc.paragraphs.length;
  const out: Array<Record<string, unknown>> = [];
  for (let k = 0; k < m; k++) {
    const p = doc.paragraphs[Math.min(P - 1, Math.floor(((k + 0.25) * P) / Math.max(m, 1)))];
    const word = doc.text.slice(p.wordStart, p.wordEnd);
    const kind = k % 3 === 0 ? "ins" : k % 3 === 1 ? "del" : "sub";
    const base = { id: `h${k}`, author: "api", ts: T0 - 30000 + k, kind, anchor: null };
    if (kind === "ins") out.push({ ...base, curFrom: p.wordStart, curTo: p.wordEnd, baseFrom: p.wordStart, baseTo: p.wordStart, oldText: "", newText: word });
    else if (kind === "del") out.push({ ...base, curFrom: p.wordStart, curTo: p.wordStart, baseFrom: p.wordStart, baseTo: p.wordStart + 7, oldText: "removed", newText: "" });
    else out.push({ ...base, curFrom: p.wordStart, curTo: p.wordEnd, baseFrom: p.wordStart, baseTo: p.wordStart + 5, oldText: "older", newText: word });
  }
  return out;
}
export function makeStatus(comments: Array<Record<string, unknown>>, hunks: Array<Record<string, unknown>>, storeMtimeNs: string): Record<string, unknown> {
  return { ...STATUS, fileMtimeNs: MT, storeMtimeNs, store: { ...STATUS.store, comments }, hunks,
    unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null } };
}

// ── the pages ───────────────────────────────────────────────────────────────────────────────────────
const PANE_URL = ORIGIN + "/pane";
/** The shell: the dashboard's pane row reduced to a filler pane, a gutter and the Files pane holding the viewer's iframe.
 *  Widths follow two flex-grow custom properties on the row, written the way kernel.py's setGrow writes them. */
export function shellHtml(w0: number, viewportW: number): string {
  return `<!DOCTYPE html><html><head><meta charset=utf-8><style>
html,body{margin:0;height:100%;overflow:hidden;background:#1e1e1e}
.row{display:flex;height:100%}
#left-pane{flex:var(--g-left,60) 1 0}#files-pane{flex:var(--g-files,40) 1 0}
.gv{flex:0 0 7px;background:linear-gradient(90deg,transparent 3px,#333 3px,#333 4px,transparent 4px)}
.pane{position:relative;min-width:0;min-height:0;overflow:hidden}
.pane>iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
</style></head><body><div class=row id=row><div class=pane id=left-pane></div><div class=gv></div><div class=pane id=files-pane><iframe name=files src="${PANE_URL}"></iframe></div></div>
<script>
var row = document.getElementById("row");
window.__total = ${viewportW} - 7;
window.__setFiles = function (px) { row.style.setProperty("--g-left", String(window.__total - px)); row.style.setProperty("--g-files", String(px)); };
window.__setFiles(${w0});
window.__loaf = [];
try { new PerformanceObserver(function (list) { list.getEntries().forEach(function (e) { window.__loaf.push({ start: e.startTime, dur: e.duration, block: e.blockingDuration, scripts: (e.scripts || []).map(function (s) { return { url: String(s.sourceURL || "").split("/").pop(), fn: s.sourceFunctionName, inv: s.invoker, type: s.invokerType, dur: s.duration }; }) }); }); }).observe({ type: "long-animation-frame", buffered: true }); } catch (e) {}
// the divider drag: on grab the shell reads the pane widths once (mousedown), then writes two grows per mousemove with
// nothing folded or deferred; here one write per animation frame, the fastest cadence a mousemove reaches the shell at
window.__sweep = function (w0, w1, steps, settle) {
  return new Promise(function (res) {
    var ts = []; var i = 0;
    function step(t) {
      ts.push(t);
      if (i <= steps) window.__setFiles(Math.round(w0 + (w1 - w0) * i / steps));
      i++;
      if (i < steps + 1 + settle) requestAnimationFrame(step); else res(ts);
    }
    requestAnimationFrame(step);
  });
};
</script></body></html>`;
}
/** The pane: the leg's page (styles.css + files-pane.css under body.fileview-pane, the viewer bundle, the file table, the
 *  status-answering poster) plus what the bench needs: HEAD answers for the poll's three targets from a table (so the
 *  poll sees nothing move until the bench moves the sidecar), a capturing listener stamping every status reply, a
 *  long-animation-frame observer, and a marks table in epoch milliseconds. */
export function paneHtml(text: string, status: Record<string, unknown>, storePath: string, configPath: string): string {
  const base = pageHtml("pane", { [REPORT]: text }, MT);
  const extra = `<script>
window.__status = ${JSON.stringify(status).replace(/</g, "\\u003c")};
(function () {
  var prev = window.fetch;
  window.__heads = {}; window.__heads[${JSON.stringify(REPORT)}] = window.__mtime; window.__heads[${JSON.stringify(storePath)}] = window.__status.storeMtimeNs; window.__heads[${JSON.stringify(configPath)}] = window.__status.configMtimeNs;
  window.fetch = async function (url, init) {
    var m = /[?&]path=([^&]*)/.exec(String(url)); var p = m ? decodeURIComponent(m[1]) : "";
    if (init && init.method === "HEAD" && window.__heads[p] !== undefined) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": window.__heads[p] } });
    return prev.apply(this, arguments);
  };
})();
window.__replies = [];
window.addEventListener("message", function (e) { var m = e.data; if (m && m.type === "fileCommentsResult") window.__replies.push({ t: performance.timeOrigin + performance.now(), n: m.store && m.store.comments ? m.store.comments.length : -1 }); }, true);
window.__loaf = [];
try { new PerformanceObserver(function (list) { list.getEntries().forEach(function (e) { window.__loaf.push({ start: e.startTime, dur: e.duration, block: e.blockingDuration, render: e.renderStart, styleLayout: e.styleAndLayoutStart, scripts: (e.scripts || []).map(function (s) { return { url: String(s.sourceURL || "").split("/").pop(), fn: s.sourceFunctionName, inv: s.invoker, type: s.invokerType, dur: s.duration, pos: s.sourceCharPosition }; }) }); }); }).observe({ type: "long-animation-frame", buffered: true }); } catch (e) {}
window.__epoch = function () { return performance.timeOrigin + performance.now(); };
</script>`;
  // at the LAST closing pair: the viewer bundle inlined above holds that string too (DOMPurify's wrapper), and a replace of
  // the first occurrence put this script inside a JavaScript string literal, where its </script> ended the bundle early
  const at = base.lastIndexOf("</body></html>");
  return base.slice(0, at) + extra + base.slice(at);
}

// ── measurement helpers ─────────────────────────────────────────────────────────────────────────────
type Metrics = Record<string, number>;
const METRIC_KEYS = ["LayoutCount", "LayoutDuration", "RecalcStyleCount", "RecalcStyleDuration", "ScriptDuration", "TaskDuration", "Nodes", "JSHeapUsedSize", "Documents", "Frames", "JSEventListeners"];
async function metrics(cdp: any): Promise<Metrics> {
  const r = await cdp.send("Performance.getMetrics");
  const out: Metrics = {};
  for (const m of r.metrics) if (METRIC_KEYS.includes(m.name)) out[m.name] = m.value;
  return out;
}
/** Deltas: counts as counts, durations in ms (CDP reports seconds), sizes in MB; Nodes and heap also as the after value. */
function delta(a: Metrics, b: Metrics): Record<string, number> {
  const ms = (k: string) => Math.round((b[k] - a[k]) * 1000 * 10) / 10;
  return { layouts: b.LayoutCount - a.LayoutCount, layout_ms: ms("LayoutDuration"), restyles: b.RecalcStyleCount - a.RecalcStyleCount, restyle_ms: ms("RecalcStyleDuration"),
    script_ms: ms("ScriptDuration"), task_ms: ms("TaskDuration"), nodes_delta: b.Nodes - a.Nodes, nodes: b.Nodes, heap_mb: Math.round(b.JSHeapUsedSize / 1048576 * 10) / 10, heap_delta_mb: Math.round((b.JSHeapUsedSize - a.JSHeapUsedSize) / 1048576 * 10) / 10 };
}
const r1 = (x: number) => Math.round(x * 10) / 10;
function frameStats(ts: number[]): { frames: number; total_ms: number; p50_ms: number; p90_ms: number; max_ms: number; over_50ms: number; over_16ms: number; per_frame_ms: number[] } {
  const d: number[] = []; for (let i = 1; i < ts.length; i++) d.push(ts[i] - ts[i - 1]);
  const s = [...d].sort((a, b) => a - b); const q = (p: number) => (s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : 0);
  return { frames: d.length, total_ms: r1(d.reduce((a, b) => a + b, 0)), p50_ms: r1(q(0.5)), p90_ms: r1(q(0.9)), max_ms: r1(s.length ? s[s.length - 1] : 0), over_50ms: d.filter((x) => x > 50).length, over_16ms: d.filter((x) => x > 16.7).length, per_frame_ms: d.map(r1) };
}
const drainLoaf = (target: any): Promise<any[]> => target.evaluate(() => (window as any).__loaf.splice(0));
/** The shell window's long frames, summed: their count, their blocking ms (the part of each over 50 ms), the longest. */
const loafSum = (xs: any[]): { loaf_n: number; loaf_block_ms: number; loaf_worst_ms: number } => ({ loaf_n: xs.length, loaf_block_ms: r1(xs.reduce((a, e) => a + (e.block || 0), 0)), loaf_worst_ms: r1(xs.reduce((a, e) => Math.max(a, e.dur || 0), 0)) });
const epochNow = (target: any): Promise<number> => target.evaluate(() => performance.timeOrigin + performance.now());

// ── profile folding ─────────────────────────────────────────────────────────────────────────────────
type Fold = { key: string; self_ms: number; total_ms: number; samples: number };
/** Self time by function (and total time, counted once per distinct function on the stack), optionally restricted to a
 *  window in epoch ms; `align` maps the profile's clock (microseconds from startTime) onto epoch ms. */
export function foldProfile(profile: any, align: { startEpochMs: number }, win: { from: number; to: number } | null = null, locate: ((docLine: number) => string | null) | null = null): Fold[] {
  const nodes = new Map<number, any>(); const parent = new Map<number, number>();
  for (const n of profile.nodes) { nodes.set(n.id, n); for (const c of n.children || []) parent.set(c, n.id); }
  const key = (n: any): string => {
    const cf = n.callFrame; const url = String(cf.url || "").split("/").pop() || ""; const line = cf.lineNumber + 1;
    const src = url === "pane" && locate ? locate(line) : null;    // the inline bundle: V8's line is the pane document's
    return `${cf.functionName || "(anonymous)"}@${url}:${line}${src ? " (" + src + ")" : ""}`;
  };
  const acc = new Map<string, Fold>();
  const bump = (k: string, self: number, total: number, sample: number) => { const f = acc.get(k) || { key: k, self_ms: 0, total_ms: 0, samples: 0 }; f.self_ms += self; f.total_ms += total; f.samples += sample; acc.set(k, f); };
  let t = profile.startTime;
  const deltas = profile.timeDeltas;
  for (let i = 0; i < profile.samples.length; i++) {
    t += deltas[i];
    const dur = (i + 1 < deltas.length ? deltas[i + 1] : 0) / 1000;   // this sample lasts until the next one
    const at = align.startEpochMs + (t - profile.startTime) / 1000;
    if (win && (at < win.from || at > win.to)) continue;
    const leaf = nodes.get(profile.samples[i]); if (!leaf) continue;
    bump(key(leaf), dur, 0, 1);
    const seen = new Set<string>();
    for (let id: number | undefined = leaf.id; id !== undefined; id = parent.get(id)) { const k = key(nodes.get(id)); if (seen.has(k)) continue; seen.add(k); bump(k, 0, dur, 0); }
  }
  return [...acc.values()].sort((a, b) => b.self_ms - a.self_ms).map((f) => ({ ...f, self_ms: r1(f.self_ms), total_ms: r1(f.total_ms) }));
}
/** A locator from a line of the pane document to the source file of the bundled module it sits in: esbuild writes a
 *  `// <path>` banner at every module's start in an unminified bundle, and the viewer bundle is the page's first script.
 *  Lines outside the bundle are the harness's own scripts. */
export function bannerLocator(html: string): (docLine: number) => string | null {
  const open = html.indexOf("<script>"); if (open < 0) return () => null;
  const start = html.slice(0, open).split("\n").length;                          // the bundle's first line (1-based)
  const close = html.indexOf("</script>", open);
  const end = close < 0 ? Infinity : html.slice(0, close).split("\n").length;
  const banners: Array<[number, string]> = [];
  html.split("\n").forEach((l, i) => { const m = /^\s*\/\/ ((?:\.\.\/)*[\w./@-]+\.(?:ts|js|mjs|cjs))$/.exec(l); if (m && i + 1 >= start && i + 1 <= end) banners.push([i + 1, m[1]]); });
  return (docLine: number) => {
    if (docLine < start || docLine > end) return "harness";
    let file: string | null = null;
    for (const [line, f] of banners) { if (line > docLine) break; file = f; }
    return file;
  };
}
function renderFold(rows: Fold[], top: number): string {
  const lines = [`  ${"self ms".padStart(9)} ${"total ms".padStart(9)} ${"samples".padStart(8)}  function@file:line`];
  for (const f of rows.slice(0, top)) lines.push(`  ${String(f.self_ms).padStart(9)} ${String(f.total_ms).padStart(9)} ${String(f.samples).padStart(8)}  ${f.key}`);
  return lines.join("\n");
}

// ── the run ─────────────────────────────────────────────────────────────────────────────────────────
function gitRev(tree: string): { rev: string; dirty: number } {
  try { return { rev: execFileSync("git", ["-C", tree, "rev-parse", "--short", "HEAD"], { encoding: "utf8" }).trim(), dirty: execFileSync("git", ["-C", tree, "status", "--porcelain"], { encoding: "utf8" }).split("\n").filter(Boolean).length }; }
  catch { return { rev: "unknown", dirty: -1 }; }
}

export async function main(argv: string[]): Promise<number> {
  const o = parseOpts(argv);
  const started = new Date();
  const id = started.toISOString().replace(/[:.]/g, "-").slice(0, 19) + "-" + [o.size === "small" || o.size === "medium" || o.size === "large" ? o.size : `${o.lines}l`, o.variant, `c${o.comments}`, `h${o.hunks}`, o.panel, o.label].filter(Boolean).join("-");
  fs.mkdirSync(path.join(o.outDir, "runs"), { recursive: true });
  if (o.cpuProfile) fs.mkdirSync(path.join(o.outDir, "profiles"), { recursive: true });
  const doc = makeDoc(o);
  const comments = makeComments(doc, o.comments);
  const hunks = makeHunks(doc, o.hunks);
  const status = makeStatus(comments, hunks, String(STATUS.storeMtimeNs));
  const storePath = String(STATUS.storePath), configPath = String(STATUS.root) + "/.trackchanges/config.json";
  const git = gitRev(o.tree);
  const result: Record<string, unknown> = {
    id, started: started.toISOString(), tree: o.tree, tree_rev: git.rev, tree_dirty_files: git.dirty, node: process.version,
    knobs: { ...o, interactions: [...o.interactions], outDir: undefined },
    doc: doc.stats, comments: o.comments, hunks: o.hunks, panel: o.panel, comments_plus_hunks: o.comments + o.hunks,
    interactions: {} as Record<string, unknown>, errors: [] as string[], console_errors: [] as string[], timed_out: false, phase: "launch",
  };
  const inter = result.interactions as Record<string, unknown>;
  const errors = result.errors as string[];
  const consoleErrors = result.console_errors as string[];
  let phase = "launch";
  const setPhase = (p: string) => { phase = p; result.phase = p; };

  const pw = requireCjs("playwright");
  const browser = await pw.chromium.launch({ headless: true });
  let profile: any = null; let profileAlign: { startEpochMs: number } | null = null;
  let paneText = "";                                   // the pane document, for the profile's bundle-line to source-file map
  const windows: Record<string, { from: number; to: number }> = {};
  const body = async () => {
    const page = await browser.newPage({ viewport: o.viewport });
    page.on("pageerror", (e: Error) => errors.push(e.message));
    page.on("console", (m: any) => { if (m.type() === "error") consoleErrors.push(String(m.text()).slice(0, 300)); });
    const shell = shellHtml(o.w0, o.viewport.width);
    const pane = paneHtml(doc.text, status, storePath, configPath); paneText = pane;
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
      const u = new URL(route.request().url());
      route.fulfill({ status: 200, contentType: "text/html", body: u.pathname === "/pane" ? pane : shell });
    });
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Performance.enable");
    if (o.cpuThrottle !== 1) await cdp.send("Emulation.setCPUThrottlingRate", { rate: o.cpuThrottle });
    setPhase("goto");
    await page.goto(ORIGIN + "/");
    const frame = page.frame({ name: "files" });
    if (!frame) throw new Error("the Files iframe did not attach");
    await frame.waitForFunction(() => !!(window as any).FV && !!(window as any).__heads, null, { timeout: 60000 });
    await frames(page, 2);
    if (o.cpuProfile) {
      await cdp.send("Profiler.enable");
      await cdp.send("Profiler.setSamplingInterval", { interval: o.samplingUs });
      const a = await epochNow(frame); await cdp.send("Profiler.start"); const b = await epochNow(frame);
      profileAlign = { startEpochMs: (a + b) / 2 };
      (result as any).profile_start_bracket_ms = r1(b - a);
    }
    /** Cards placed: `replies` status replies have landed (the probe's and the open's, or the add's), the aside is up in the
     *  margin layout, every card has its `top`, and the card count has held for two more frames (the panel groups the
     *  changes into cards by passage, so the count is not comments + hunks). Returns the epoch ms of the first frame the
     *  condition held at, plus the count found. */
    const waitPlaced = (replies: number, nComments: number | null): Promise<{ at: number; cards: number }> => frame.evaluate(([replies, nComments]: [number, number | null]) => new Promise<{ at: number; cards: number }>((res) => {
      let firstOk = 0, held = 0, lastCount = -1;
      const tick = () => {
        const w = window as any;
        const landed = nComments === null ? w.__replies.length >= replies : w.__replies.some((x: any) => x.n === nComments);
        const cards = document.querySelectorAll(".fc-sec-cards .fc-card[data-id]");
        const margin = !!document.querySelector(".fc-panel.fc-margin");
        const ok = landed && !!document.querySelector(".fileview-aside") && margin && Array.from(cards).every((c) => (c as HTMLElement).style.top !== "");
        if (ok && cards.length === lastCount) { if (!firstOk) firstOk = performance.timeOrigin + performance.now(); held++; }
        else { firstOk = ok ? performance.timeOrigin + performance.now() : 0; held = 0; }
        lastCount = cards.length;
        if (ok && held >= 2) res({ at: firstOk, cards: cards.length }); else requestAnimationFrame(tick);
      };
      tick();
    }), [replies, nComments]);

    // (1) MOUNT
    {   // (1) MOUNT: always taken, the other interactions need the document
      setPhase("mount");
      const m0 = await metrics(cdp);
      const t = await frame.evaluate(([p, sid]: [string, string]) => new Promise<{ open: number; rendered: number; painted: number }>((res) => {
        const open = performance.timeOrigin + performance.now();
        (window as any).FV.openFileView(p, sid, null);
        const poll = () => {
          if (document.querySelector(".fileview-md > p")) {
            const rendered = performance.timeOrigin + performance.now();     // the render task has ended; this frame paints it
            requestAnimationFrame(() => res({ open, rendered, painted: performance.timeOrigin + performance.now() }));   // the frame after the first paint
          } else requestAnimationFrame(poll);
        };
        requestAnimationFrame(poll);
      }), [REPORT, SID]);
      const m1 = await metrics(cdp);
      const mount: Record<string, unknown> = { open_to_rendered_ms: r1(t.rendered - t.open), open_to_first_paint_ms: r1(t.painted - t.open), document: delta(m0, m1) };
      windows.mount = { from: t.open, to: t.painted };
      if (o.panel === "open") {
        setPhase("open-panel");
        await frame.waitForFunction(() => { const u = document.querySelector(".fileview-fc"); return !!u && !(u as HTMLElement).hidden; }, null, { timeout: 60000 });
        const m2 = await metrics(cdp);
        const c0 = await epochNow(frame);
        await frame.click(".fileview-fc button");
        const placed = await waitPlaced(2, null);   // the probe's reply and the open's
        const m3 = await metrics(cdp);
        mount.click_to_cards_placed_ms = r1(placed.at - c0);
        mount.panel = delta(m2, m3);
        mount.cards_found = placed.cards;
        mount.marks_found = await frame.evaluate(() => document.querySelectorAll(".fileview-body .fc-hl, .fileview-body .fc-ins, .fileview-body .fc-del").length);
        windows.open_panel = { from: c0, to: placed.at };
        await frames(frame, 5);
      } else {
        await frames(frame, 5);
      }
      mount.loaf_pane = await drainLoaf(frame); mount.loaf_shell = await drainLoaf(page); Object.assign(mount, loafSum(mount.loaf_shell as any[]));
      mount.body_width_px = await frame.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).clientWidth);
      inter.mount = mount;
    }
    await frames(frame, 5);

    // (2) SCROLL
    if (o.interactions.has("scroll")) {
      setPhase("scroll");
      const m0 = await metrics(cdp);
      const from = await epochNow(frame);
      const ts: number[] = await frame.evaluate(([n, px, settle]: [number, number, number]) => new Promise<number[]>((res) => {
        const body = document.querySelector(".fileview-body") as HTMLElement; body.scrollTop = 0;
        const ts: number[] = []; let i = 0;
        const step = (t: number) => { ts.push(t); if (i < n) body.scrollTop += px; i++; if (i < n + settle) requestAnimationFrame(step); else res(ts); };
        requestAnimationFrame(step);
      }), [o.scrollFrames, o.scrollPx, o.settle]);
      const to = await epochNow(frame);
      const m1 = await metrics(cdp);
      const loafShell = await drainLoaf(page);
      inter.scroll = { ...frameStats(ts), ...delta(m0, m1), ...loafSum(loafShell), loaf_pane: await drainLoaf(frame), loaf_shell: loafShell, scroll_top_after: await frame.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop) };
      windows.scroll = { from, to };
      await frame.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
      await frames(frame, 5);
    }

    // (3) DRAG, then one big resize back, then a 1px nudge
    const sweep = async (name: string, w0: number, w1: number, steps: number) => {
      setPhase(name);
      await drainLoaf(frame); await drainLoaf(page);
      const m0 = await metrics(cdp);
      const from = await epochNow(page);
      const ts: number[] = await page.evaluate(([a, b, s, settle]: [number, number, number, number]) => (window as any).__sweep(a, b, s, settle), [w0, w1, steps, o.settle]);
      const to = await epochNow(page);
      const m1 = await metrics(cdp);
      const paints = await frame.evaluate(() => (window as any).__paints);
      const loafShell = await drainLoaf(page);
      inter[name] = { w0, w1, steps, ...frameStats(ts), ...delta(m0, m1), ...loafSum(loafShell), paints_total: paints, loaf_pane: await drainLoaf(frame), loaf_shell: loafShell,
        body_width_px: await frame.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).clientWidth) };
      windows[name] = { from, to };
      await frames(frame, 5);
    };
    if (o.interactions.has("drag")) await sweep("drag", o.w0, o.w1, o.steps);
    if (o.interactions.has("big")) await sweep("big", o.interactions.has("drag") ? o.w1 : o.w0, o.w0, 1);
    if (o.interactions.has("nudge")) await sweep("nudge", o.w0, o.w0 - 1, 1);

    // (4) ADD a comment: the sidecar moves, the poll asks, the poster answers with N+1
    if (o.interactions.has("add") && o.panel === "open") {
      setPhase("add");
      const added = [...comments, ...makeComments(doc, 1, 0.37).map((c) => ({ ...c, id: `${T0 + 999999}-add`, ts: T0 + 999999, body: "A new note the reader just added." }))];
      const next = makeStatus(added, hunks, "1757145600000000012");
      await drainLoaf(frame); await drainLoaf(page);
      const m0 = await metrics(cdp);
      const t0 = await epochNow(frame);
      await frame.evaluate(([s, sp]: [Record<string, unknown>, string]) => { (window as any).__status = s; (window as any).__heads[sp] = (s as any).storeMtimeNs; (window as any).__replies.length = 0; }, [next, storePath]);
      const placed = await waitPlaced(0, o.comments + 1);
      const reply: number = await frame.evaluate((n: number) => (window as any).__replies.find((x: any) => x.n === n).t, o.comments + 1);
      const m1 = await metrics(cdp);
      const loafShell = await drainLoaf(page);
      inter.add = { poll_wait_ms: r1(reply - t0), reply_to_cards_placed_ms: r1(placed.at - reply), cards_found: placed.cards, ...delta(m0, m1), ...loafSum(loafShell), loaf_pane: await drainLoaf(frame), loaf_shell: loafShell };
      windows.add = { from: reply, to: placed.at };
    }

    if (o.cpuProfile) {
      setPhase("profile");
      const r = await cdp.send("Profiler.stop");
      profile = r.profile;
    }
    setPhase("done");
  };

  let timer: NodeJS.Timeout | null = null;
  const t0 = Date.now();
  try {
    await Promise.race([
      body(),
      new Promise<void>((_, rej) => { timer = setTimeout(() => rej(new Error("timeout")), o.timeoutS * 1000); }),
    ]);
  } catch (e) {
    const msg = String((e as Error).message || e);
    if (msg === "timeout") { result.timed_out = true; result.timeout_phase = phase; result.timeout_after_s = o.timeoutS; }
    else { errors.push("bench: " + msg); result.failed_phase = phase; }
  } finally {
    if (timer) clearTimeout(timer);
    result.elapsed_s = r1((Date.now() - t0) / 1000);
    // a frozen renderer can hold browser.close() too: give it five seconds, then kill the browser by its own pid
    try {
      const p = browser.process();
      if (result.timed_out && p) p.kill("SIGKILL");
      else { const closed = await Promise.race([browser.close().then(() => true), new Promise<boolean>((r) => setTimeout(() => r(false), 5000))]); if (!closed && p) p.kill("SIGKILL"); }
    } catch { /* the browser is gone either way */ }
  }

  if (profile && profileAlign) {
    const file = path.join(o.outDir, "profiles", id + ".cpuprofile");
    fs.writeFileSync(file, JSON.stringify(profile));
    result.profile_file = file;
    const locate = bannerLocator(paneText);
    const all = foldProfile(profile, profileAlign, null, locate);
    result.profile_top = all.slice(0, 40);
    const per: Record<string, Fold[]> = {};
    for (const [k, w] of Object.entries(windows)) per[k] = foldProfile(profile, profileAlign, w, locate).slice(0, 12);
    result.profile_by_interaction = per;
    result.profile_windows_epoch_ms = windows;
  }
  const file = path.join(o.outDir, "runs", id + ".json");
  fs.writeFileSync(file, JSON.stringify(result, null, 1));
  result.file = file;

  // the one-line summary
  const f = (x: unknown) => (typeof x === "number" ? String(x) : "-");
  const m = inter.mount as any, s = inter.scroll as any, d = inter.drag as any, b = inter.big as any, n = inter.nudge as any, a = inter.add as any;
  const parts = [`viewer-resize-bench ${id}`, `tree=${git.rev}${git.dirty ? "+" + git.dirty : ""}`, `lines=${doc.stats.lines} variant=${o.variant} comments=${o.comments} hunks=${o.hunks} panel=${o.panel}`];
  if (result.timed_out) parts.push(`TIMEOUT at ${result.timeout_phase} after ${o.timeoutS}s`);
  if (errors.length) parts.push(`errors=${errors.length}`);
  if (m) parts.push(`nodes=${f(m.document?.nodes)} mount: render=${f(m.open_to_rendered_ms)}ms paint=${f(m.open_to_first_paint_ms)}ms layouts=${f(m.document?.layouts)}/${f(m.document?.layout_ms)}ms` + (m.panel ? ` cards=${f(m.click_to_cards_placed_ms)}ms (${f(m.cards_found)} cards, ${f(m.marks_found)} marks, layouts=${f(m.panel.layouts)}/${f(m.panel.layout_ms)}ms)` : ""));
  if (s) parts.push(`scroll: p50=${s.p50_ms}ms max=${s.max_ms}ms >50ms=${s.over_50ms}/${s.frames} layouts=${s.layouts}/${s.layout_ms}ms script=${s.script_ms}ms`);
  if (d) parts.push(`drag: p50=${d.p50_ms}ms max=${d.max_ms}ms total=${d.total_ms}ms >50ms=${d.over_50ms}/${d.frames} layouts=${d.layouts}/${d.layout_ms}ms style=${d.restyle_ms}ms script=${d.script_ms}ms loaf-block=${d.loaf_block_ms}ms`);
  if (b) parts.push(`big: total=${b.total_ms}ms max=${b.max_ms}ms layouts=${b.layouts}/${b.layout_ms}ms`);
  if (n) parts.push(`nudge: total=${n.total_ms}ms max=${n.max_ms}ms layouts=${n.layouts}/${n.layout_ms}ms script=${n.script_ms}ms`);
  if (a) parts.push(`add: reply->placed=${a.reply_to_cards_placed_ms}ms layouts=${a.layouts}/${a.layout_ms}ms script=${a.script_ms}ms`);
  parts.push(`json=${file}`);
  console.log(parts.join(" | "));
  if (profile) { console.log(`cpu profile: ${result.profile_file}\nself time by function, top 25 (whole run):`); console.log(renderFold(result.profile_top as Fold[], 25)); }
  return result.timed_out ? 3 : errors.length ? 2 : 0;
}

if (require.main === module) {
  // an explicit exit: a browser that would not close keeps Playwright's connection handles alive, and the run is recorded
  main(process.argv.slice(2)).then((code) => { process.exit(code); }, (e) => { console.error(String((e as Error).stack || e)); process.exit(1); });
}
