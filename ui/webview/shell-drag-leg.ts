// shell-drag-leg: the dashboard shell's pane row and its divider drag, EXTRACTED from kernel/kernel.py (the _LANDING_JS
// script and the pane-row CSS strings) and mounted in a page of their own. Two users: the browser leg that pins the drag's
// behaviour (shell-gutter-drag-browser.test.ts) and tools/viewer-resize-bench.ts (--shell real), which puts the real
// viewer's pane inside that row and drives the drag the way a pointer does. The kernel source is read from the cwd's tree
// (npm test runs in vscode-extension; real-viewer-leg.ts resolves the same way), or from the kernel.py text a caller
// passes, so a bench can run the shell of another commit over the same viewer. The row here holds the five panes and the
// four gutters with the real ids and the real CSS; only the Files pane carries an iframe (the leg gives it about:blank,
// the bench the viewer page). Synthetic values only; no session data.
import * as fs from "node:fs";
import * as path from "node:path";
import { EXT } from "./real-viewer-leg";   // the cwd's tree, the one place that says so (no environment variable; its header)

export const KERNEL_PY = path.resolve(EXT, "..", "kernel", "kernel.py");
export const readKernel = (file: string = KERNEL_PY): string => fs.readFileSync(file, "utf8");

/** The shell's landing script (kernel.py `_LANDING_JS`): the pane grows, the gutters, the timeline band's autosize. */
export function landingJs(py: string): string {
  const m = /_LANDING_JS = """\n([\s\S]*?)^"""/m.exec(py);
  if (!m) throw new Error("_LANDING_JS not found in kernel.py: re-anchor");
  return m[1];
}

/** The pane row's CSS: every string literal from the `#chat-pane{flex:...}` rule through `.pane>iframe{...}` (the grows,
 *  the hidden panes and gutters, the gutter look, body.drag, the ghost line, the pane box). Python comments are skipped. */
export function paneRowCss(py: string): string {
  const a = py.indexOf('"#chat-pane{flex:var(--g-chat');
  const b = a < 0 ? -1 : py.indexOf('".pane>iframe{', a);
  if (a < 0 || b < 0) throw new Error("the pane row CSS was not found in kernel.py: re-anchor");
  const from = py.lastIndexOf("\n", a) + 1, to = py.indexOf("\n", b);
  const out: string[] = [];
  for (const line of py.slice(from, to).split("\n")) { const m = /^\s*"((?:[^"\\]|\\.)*)"/.exec(line); if (m) out.push(m[1]); }
  return out.join("");
}

export type ShellOpts = {
  py: string;                 // kernel.py's text
  viewportW: number;          // the page width the caller opens at; the row is that wide
  filesW: number;             // the Files pane's initial width in px (the chat pane takes the rest)
  filesSrc: string;           // the Files iframe's src
  head?: string;              // extra markup for <head>
  script?: string;            // extra script after the shell's own
};
/** A page holding the shell's pane row (chat and files shown, the three others and their gutters hidden by the real
 *  body.po-* rules), the landing script, and two helpers: `__setFiles(px)` writes the two grows the way setGrow does, and
 *  `__mouse(type, x, y)` dispatches a synthetic mousedown on gv-d or a mousemove/mouseup on the window, the targets the
 *  landing script listens on; `__gutter()` is gv-d's centre. */
export function shellPage(o: ShellOpts): string {
  const css = paneRowCss(o.py), js = landingJs(o.py);
  return `<!DOCTYPE html><html><head><meta charset=utf-8><style>
html,body{margin:0;height:100%;overflow:hidden;background:#1e1e1e}
.col{display:flex;flex-direction:column;height:100%;box-sizing:border-box}
.row{display:flex;flex:1 1 auto;min-height:0}
${css}
</style>${o.head || ""}</head><body class="po-chat po-files"><div class=col><div class=row>
<div class=pane id=chat-pane></div><div class=gv id=gv-a></div><div class=pane id=fleet-pane></div><div class=gv id=gv-b></div><div class=pane id=feed-pane></div><div class=gv id=gv-c></div><div class=pane id=waiting-pane></div><div class=gv id=gv-d></div><div class=pane id=files-pane><iframe id=f-files name=files src="${o.filesSrc}"></iframe></div>
</div><div id=gv-ghost></div><div class=gh id=gh></div><div class=pane id=tl-pane></div></div>
<script>${js}</script>
<script>
var row = document.querySelector(".row");
window.__total = ${o.viewportW} - 7;
window.__setFiles = function (px) { row.style.setProperty("--g-chat", String(window.__total - px)); row.style.setProperty("--g-files", String(px)); };
window.__setFiles(${o.filesW});
window.__gutter = function () { var g = document.getElementById("gv-d").getBoundingClientRect(); return { x: g.left + g.width / 2, y: g.top + Math.min(60, g.height / 2) }; };
window.__mouse = function (type, x, y) {
  var ev = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0, buttons: type === "mouseup" ? 0 : 1 });
  (type === "mousedown" ? document.getElementById("gv-d") : window).dispatchEvent(ev);
};
${o.script || ""}
</script></body></html>`;
}
