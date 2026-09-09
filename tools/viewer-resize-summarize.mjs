#!/usr/bin/env node
// Folds the run records of tools/viewer-resize-bench.mjs into one markdown table per metric group and writes it, with the
// per-run JSON paths, to <out>/MEASURE.md. Rows are runs (filtered by --prefix on the run label; default m1-), columns are
// the document, mount, scroll, drag, big-resize, nudge and add metrics the run records hold. Every number is copied from
// the run JSON named in the paths table; nothing is recomputed except the profile share, which sums the top self-time
// rows of the run's CPU profile by source file.
// Usage: node tools/viewer-resize-summarize.mjs [--out-dir DIR] [--prefix m1-] [--write]   (without --write: stdout only)
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

const argv = process.argv.slice(2);
let outDir = path.join(os.homedir(), ".local", "state", "romp-perf", "viewer-resize");
let prefix = "m1-";
let write = false;
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--out-dir") outDir = path.resolve(argv[++i]);
  else if (argv[i] === "--prefix") prefix = argv[++i];
  else if (argv[i] === "--write") write = true;
}
const runsDir = path.join(outDir, "runs");
const runs = fs.readdirSync(runsDir).filter((f) => f.endsWith(".json")).map((f) => {
  const r = JSON.parse(fs.readFileSync(path.join(runsDir, f), "utf8"));
  r.__path = path.join(runsDir, f);
  return r;
}).filter((r) => (r.knobs?.label || "").startsWith(prefix));

const treeName = (r) => (r.knobs.label.includes("box1") ? "32018f7a" : r.tree_rev);
const sizeRank = (r) => r.doc?.lines ?? 0;
runs.sort((a, b) => treeName(a).localeCompare(treeName(b)) * -1 || sizeRank(a) - sizeRank(b) ||
  (a.knobs.variant || "").localeCompare(b.knobs.variant || "") || (a.comments - b.comments) || (a.hunks - b.hunks) ||
  (a.panel || "").localeCompare(b.panel || ""));

const n = (v, d = 0) => (v === undefined || v === null || Number.isNaN(v) ? "-" : Number(v).toFixed(d));
const ms = (v) => n(v, v !== undefined && v !== null && Math.abs(v) < 10 ? 1 : 0);
const label = (r) => r.knobs.label.replace(prefix, "");
const status = (r) => (r.timed_out ? `TIMEOUT@${r.phase}` : (r.errors?.length ? `${r.errors.length} pageerror` : "ok"));

function profileShare(r) {
  // self-time share of the whole-run profile by source file, from the top rows the run kept
  const rows = r.profile_top || [];
  if (!rows.length) return "-";
  const total = rows.reduce((s, x) => s + (x.self_ms || 0), 0);
  const by = new Map();
  for (const x of rows) {
    const src = (x.key || x.fn || "").match(/\(([^)]*)\)/)?.[1] || (x.file ?? "").toString() || "(native/idle)";
    const k = src.split("/").pop() || "(native/idle)";
    by.set(k, (by.get(k) || 0) + (x.self_ms || 0));
  }
  return [...by.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => `${k} ${n(100 * v / total)}%`).join(", ");
}

const I = (r, k) => r.interactions?.[k] || {};
const head1 = ["run", "tree", "lines", "chars", "fences/fenceLines", "tables", "cmts", "hunks", "panel", "doc nodes", "nodes after panel",
  "mount: open→paint ms", "mount: click→cards ms (cards/marks)", "mount layouts / ms", "mount restyle ms", "mount script ms", "mount heap MB",
  "scroll p50/max ms", "scroll layouts", "status"];
const head2 = ["run", "tree", "lines", "cmts", "hunks", "panel", "drag p50 / p90 / max ms", "drag total ms (frames)", "drag >50ms", "drag layouts / ms",
  "drag restyle ms", "drag script ms", "drag LoAF n / worst block ms / total block ms", "drag heap MB", "big max ms (layouts)", "nudge max ms (script ms)",
  "add reply→placed ms", "status"];
const head3 = ["run", "tree", "elapsed s", "profile: self share by file (top rows)", "profile", "json"];

function row1(r) {
  const m = I(r, "mount"), s = I(r, "scroll");
  return [label(r), treeName(r), r.doc.lines, r.doc.chars, `${r.doc.fences}/${r.doc.fenceLines}`, r.doc.tables, r.comments, r.hunks, r.panel,
    m.document?.nodes ?? "-", m.panel?.nodes ?? "-", ms(m.open_to_first_paint_ms),
    m.click_to_cards_placed_ms !== undefined ? `${ms(m.click_to_cards_placed_ms)} (${m.cards_found}/${m.marks_found})` : "-",
    `${(m.document?.layouts ?? 0) + (m.panel?.layouts ?? 0)} / ${ms((m.document?.layout_ms ?? 0) + (m.panel?.layout_ms ?? 0))}`,
    ms((m.document?.restyle_ms ?? 0) + (m.panel?.restyle_ms ?? 0)), ms((m.document?.script_ms ?? 0) + (m.panel?.script_ms ?? 0)),
    ms(m.panel?.heap_mb ?? m.document?.heap_mb),
    s.frames ? `${ms(s.p50_ms)} / ${ms(s.max_ms)}` : "-", s.frames ? s.layouts : "-", status(r)];
}
function row2(r) {
  const d = I(r, "drag"), b = I(r, "big"), g = I(r, "nudge"), a = I(r, "add");
  return [label(r), treeName(r), r.doc.lines, r.comments, r.hunks, r.panel,
    d.frames ? `${ms(d.p50_ms)} / ${ms(d.p90_ms)} / ${ms(d.max_ms)}` : "-", d.frames ? `${ms(d.total_ms)} (${d.frames})` : "-",
    d.frames ? `${d.over_50ms}/${d.frames}` : "-", d.frames ? `${d.layouts} / ${ms(d.layout_ms)}` : "-", d.frames ? ms(d.restyle_ms) : "-",
    d.frames ? ms(d.script_ms) : "-", d.frames ? `${d.loaf_n} / ${ms(d.loaf_worst_ms)} / ${ms(d.loaf_block_ms)}` : "-", d.frames ? ms(d.heap_mb) : "-",
    b.frames ? `${ms(b.max_ms)} (${b.layouts})` : "-", g.frames ? `${ms(g.max_ms)} (${ms(g.script_ms)})` : "-",
    a.reply_to_cards_placed_ms !== undefined ? ms(a.reply_to_cards_placed_ms) : "-", status(r)];
}
function row3(r) {
  return [label(r), treeName(r), n(r.elapsed_s), profileShare(r), r.profile_file ? path.basename(r.profile_file) : "-", r.__path];
}
const table = (head, rows) => [`| ${head.join(" | ")} |`, `| ${head.map(() => "---").join(" | ")} |`, ...rows.map((x) => `| ${x.join(" | ")} |`)].join("\n");

const out = [];
out.push(`# Viewer resize bench: measurements (${new Date().toISOString()})`);
out.push("");
out.push(`${runs.length} runs with label prefix \`${prefix}\` under \`${runsDir}\`. Bench: tools/viewer-resize-bench.mjs; matrix: tools/viewer-resize-matrix.sh. Trees: eee97565 = origin/main (HEAD of branch perf-viewer-resize); 32018f7a = the incident bundle (box 1), run from a detached worktree with --tree.`);
out.push("");
out.push("Columns: lines/chars = the synthetic document (doc.lines, doc.chars); doc nodes = CDP Nodes after the document rendered (mount.document.nodes); nodes after panel = after the Comments panel opened (mount.panel.nodes); open→paint = openFileView to the first rAF after `.fileview-md > p` appeared (mount.open_to_first_paint_ms); click→cards = panel button click to every card having a top (mount.click_to_cards_placed_ms); mount layouts/ms = LayoutCount / LayoutDuration summed over the document render and the panel open; scroll = 60 frames of 200 px plus 10 settle frames, panel open; drag = 60 width steps 1000→700 px (one per rAF) plus 10 settle frames; LoAF = long-animation-frame entries seen by the shell window (the pane's own long frames are attributed there); big = one resize 700→1000 px; nudge = one 1 px step (one full panel pass); add = one comment added through the status poster, reply to cards placed. Frame times are rAF-to-rAF in the shell. ms are rounded.");
out.push("");
out.push("## Table 1: document, mount, scroll");
out.push("");
out.push(table(head1, runs.map(row1)));
out.push("");
out.push("## Table 2: drag, big resize, nudge, add");
out.push("");
out.push(table(head2, runs.map(row2)));
out.push("");
out.push("## Table 3: run records");
out.push("");
out.push(table(head3, runs.map(row3)));
out.push("");
const text = out.join("\n");
if (write) { fs.writeFileSync(path.join(outDir, "MEASURE.md"), text + "\n"); console.log(`wrote ${path.join(outDir, "MEASURE.md")} (${runs.length} runs)`); }
else process.stdout.write(text + "\n");
