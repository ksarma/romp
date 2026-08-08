// The file viewer that lives in the FEED pane (the user 2026-08-08).
//
// Clicking a file path in the chat used to post `openFile`, which the kernel served by running an
// opener on ITS machine. Read the dashboard from another device — a laptop across the internet, a
// phone — and that is the wrong screen entirely; on a kernel with no desktop it did nothing at all,
// silently, which is how the user found it. The only place a file can actually be shown is the browser
// you are looking at, so the bytes come over the same `/file` route the image thumbnails already use
// (federation-aware via fileUrl, so a remote session's file is relayed from the host that owns it).
//
// It takes over the FEED pane rather than floating a modal: the cards are the thing you are least
// likely to be reading while you follow a path out of a transcript, and a full pane gives long source
// somewhere to scroll. The shell brings that pane forward if it was toggled off and puts it back on
// close, so the viewer never silently rearranges the layout you chose.
import hljs from "highlight.js/lib/core";
import { fileUrl } from "./preview";

// hljs is registered per-bundle; the feed had none until this viewer needed it. Same language set the
// chat registers, so a file reads identically in either place.
import bash from "highlight.js/lib/languages/bash";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import cssLang from "highlight.js/lib/languages/css";
import markdown from "highlight.js/lib/languages/markdown";
import diff from "highlight.js/lib/languages/diff";
import yaml from "highlight.js/lib/languages/yaml";

for (const [name, lang] of Object.entries({
  bash, sh: bash, shell: bash, python, py: python, javascript, js: javascript,
  typescript, ts: typescript, json, xml, html: xml, css: cssLang, markdown, md: markdown,
  diff, yaml, yml: yaml,
})) {
  try { hljs.registerLanguage(name, lang as any); } catch { /* dup alias */ }
}

// Extension → the hljs language to force. Anything absent is shown unhighlighted rather than guessed:
// highlightAuto on a config file or a log picks a language at random and paints it misleadingly, and a
// wrong highlight reads as information the file does not contain.
const LANG: Record<string, string> = {
  py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
  cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
  yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
  html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
  md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
};

function langFor(path: string): string | null {
  const ext = path.slice(path.lastIndexOf(".") + 1).toLowerCase();
  return LANG[ext] || null;
}

function el(tag: string, cls?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

// The shell restores the pane's previous visibility on this, so it must fire on EVERY close path.
function tellShellClosed(): void {
  try {
    if (window.parent !== window) window.parent.postMessage({ romp: "viewFileClosed" }, "*");
  } catch { /* no shell (standalone /feed) — nothing to restore */ }
}

export function closeFileView(): void {
  const box = document.getElementById("romp-fileview");
  if (!box) return;
  box.remove();
  document.body.classList.remove("fileview-open");
  tellShellClosed();
}

/** Show `path` in the feed pane. Re-opening replaces whatever is up — never stacks. */
export function openFileView(path: string, sid?: string | null): void {
  document.getElementById("romp-fileview")?.remove();
  const box = el("div", "fileview");
  box.id = "romp-fileview";
  document.body.classList.add("fileview-open");

  const bar = el("div", "fileview-bar");
  // Directory then basename as TWO elements, because only the directory may be truncated: the filename
  // is what identifies the file, so it never shrinks however deep the path is. (A single text node with
  // the rtl-ellipsis trick would truncate the right end — exactly the wrong half.)
  const name = el("div", "fileview-name");
  name.title = path;                                   // the full path, one hover away
  const cut = path.lastIndexOf("/");
  const dir = el("span", "fileview-dir");
  dir.textContent = cut >= 0 ? path.slice(0, cut + 1) : "";
  const base = el("span", "fileview-base");
  base.textContent = path.slice(cut + 1);
  name.appendChild(dir); name.appendChild(base);
  const acts = el("div", "fileview-acts");
  const copy = el("button", "fileview-btn") as HTMLButtonElement;
  copy.type = "button"; copy.textContent = "Copy path"; copy.title = path;
  copy.addEventListener("click", () => {
    navigator.clipboard?.writeText(path).then(
      () => { copy.textContent = "Copied"; setTimeout(() => { copy.textContent = "Copy path"; }, 1200); },
      () => { copy.textContent = "Copy failed"; });
  });
  const close = el("button", "fileview-btn fileview-close") as HTMLButtonElement;
  close.type = "button"; close.textContent = "✕"; close.title = "Close (Esc)";
  close.setAttribute("aria-label", "Close the file viewer");
  close.addEventListener("click", closeFileView);
  acts.appendChild(copy); acts.appendChild(close);
  bar.appendChild(name); bar.appendChild(acts);

  const body = el("div", "fileview-body");
  // Per the loading-state rule the first thing up is the romp loader, not a blank pane — a file coming
  // over an ssh tunnel to a phone is a real wait.
  const load = el("div", "fileview-load");
  load.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
    + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
  body.appendChild(load);

  box.appendChild(bar); box.appendChild(body);
  document.body.appendChild(box);

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "Escape" || !document.getElementById("romp-fileview")) return;
    e.preventDefault();
    closeFileView();
    document.removeEventListener("keydown", onKey);
  };
  document.addEventListener("keydown", onKey);

  fetch(fileUrl(path, sid), { cache: "no-store" }).then((r) => {
    // Every failure says WHY, in the pane, rather than leaving a blank one: the kernel distinguishes
    // "not a type I serve" from "too big" from "not text after all", and that is exactly what the
    // person who clicked needs to know (a 413 names the size and the cap).
    if (!r.ok) return r.text().then((t) => { throw new Error(t || ("HTTP " + r.status)); });
    return r.text();
  }).then((text) => {
    if (!document.getElementById("romp-fileview")) return;    // closed while it was in flight
    body.replaceChildren(codeBlock(text, path));
  }).catch((err) => {
    if (!document.getElementById("romp-fileview")) return;
    const why = el("div", "fileview-err");
    why.textContent = String(err && err.message || err);
    const hint = el("div", "fileview-err-hint");
    hint.textContent = path;
    why.appendChild(hint);
    body.replaceChildren(why);
  });
}

// Line-numbered <pre>. The gutter is a sibling column rather than text in the same <pre>, so selecting
// the code and copying it does NOT drag the line numbers along with it.
function codeBlock(text: string, path: string): HTMLElement {
  const wrap = el("div", "fileview-code");
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();   // a trailing newline is not a line
  const gutter = el("div", "fileview-gutter");
  gutter.textContent = lines.map((_, i) => String(i + 1)).join("\n");
  gutter.setAttribute("aria-hidden", "true");
  const pre = el("pre", "fileview-pre");
  const code = el("code", "hljs");
  const lang = langFor(path);
  if (lang) {
    try { code.innerHTML = hljs.highlight(text, { language: lang }).value; }
    catch { code.textContent = text; }                 // a broken grammar must never cost the content
  } else {
    code.textContent = text;
  }
  pre.appendChild(code);
  wrap.appendChild(gutter); wrap.appendChild(pre);
  return wrap;
}

/** Listen for the shell's relay of a chat file-link click. Called once, from the feed's boot. */
export function initFileView(): void {
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (m && m.romp === "viewFile" && typeof m.path === "string" && m.path) {
      openFileView(m.path, typeof m.sid === "string" ? m.sid : null);
    }
  });
}
