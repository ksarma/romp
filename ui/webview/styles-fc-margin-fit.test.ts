// The margin layout's sections in styles.css add up to the panel (plans/file-review.md, "The margin-layout follow-on
// (2026-09-07)"). Under `.fc-panel.fc-margin { overflow: hidden }` the aside never scrolls as a whole — the track is the
// scroller, locked to the body, and a panel that scrolled would carry every card off its mark — so whatever the head,
// the composer, the Send section and the Log add up to beyond the track's floor has to come out of THEM. The first cut
// let only the Send section with its confirm up and the Log with rows yield (feed-css-margin-footers.test.ts holds that
// pair); every other growth — the composer, the Track file/folder choice, the Reject all confirm, a refusal row under
// the foot, the tooling warning — kept its section at flex 0 0 auto, so on a short panel Send and the Log toggle ran
// past the aside's bottom with no scrollbar to reach them, and a Tab onto one scrolled the overflow-hidden aside
// programmatically: the head went under the top edge and every card sat above its mark by that amount until the next
// pass (the 2026-09-07 review, round 2). The sheet now lets every section but the track shrink and scroll inside
// itself, the grown ones first. The static leg holds the sheet to that shape (CI installs no browser); the browser legs
// mount the worktree's panel under styles.css's own rules in Chromium and Firefox at the review's panel heights and
// measure: nothing past the aside's edge, the Log toggle under the pointer, Send under the pointer once its own section
// is scrolled, the collapsed sections uncut, and a focus or a real Tab onto Send or the Log leaving the aside unscrolled
// and every card where it was. Skips LOUDLY without a playwright browser. Synthetic values only: invented prose,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

/** The one rule whose head is `sel` in styles.css. */
function rule(sel: string): string {
  const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(STYLES);
  assert.ok(m, "a rule for " + sel + " in styles.css");
  return m![1];
}
const BLOCK_A = "/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)";
const BLOCK_B = "/* ── end file comments panel ── */";
const SECTIONS = [".fc-margin > .fc-sec-head", ".fc-margin > .fc-composer", ".fc-margin > .fc-sec-send", ".fc-margin > .fc-sec-log"];

/** A selector list split at its top-level commas: the ones inside :has() and :not() belong to the selector. */
function splitSelectors(list: string): string[] {
  const out: string[] = []; let depth = 0, cur = "";
  for (const ch of list) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
}
/** The margin block's rules, comments stripped: each as its selector list and its declarations. */
function marginRules(): Array<{ selectors: string[]; decls: Map<string, string> }> {
  const a = STYLES.indexOf(BLOCK_A), b = STYLES.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers");
  const start = STYLES.indexOf("\n.fc-panel.fc-margin {", a);
  assert.ok(start > a && start < b, "the margin rules follow the root rule inside the block");
  const text = STYLES.slice(start, b).replace(/\/\*[\s\S]*?\*\//g, "");
  const out: Array<{ selectors: string[]; decls: Map<string, string> }> = [];
  for (const m of text.matchAll(/([^{}]+?)\s*\{([^}]*)\}/g)) {
    const selectors = splitSelectors(m[1]);
    const decls = new Map<string, string>();
    for (const d of m[2].split(";")) { const i = d.indexOf(":"); if (i > 0) decls.set(d.slice(0, i).trim(), d.slice(i + 1).trim()); }
    out.push({ selectors, decls });
  }
  return out;
}
/** Every declaration the block gives the exact selector `sel` (later rules win, as in the sheet); `base` leaves out the
 *  grown tier's rules (the ones with a flex-shrink of their own), which the composer is always in. */
function given(sel: string, base = false): Map<string, string> {
  const merged = new Map<string, string>();
  for (const r of marginRules()) if (r.selectors.includes(sel) && !(base && r.decls.has("flex-shrink"))) for (const [k, v] of r.decls) merged.set(k, v);
  return merged;
}

// ── the static leg: every section but the track shrinks and scrolls inside itself; the grown ones give first ───────────

test("styles.css: the head, the composer, the Send section and the Log all shrink and scroll inside themselves under .fc-margin", () => {
  for (const sel of SECTIONS) {
    const d = given(sel, true);
    assert.ok(d.size > 0, "rules for " + sel);
    assert.equal(d.get("overflow"), "auto", sel + " scrolls inside itself when it outgrows its room");
    assert.equal(d.get("min-height"), "0", sel + " can shrink to nothing before the aside overflows");
    assert.equal(d.get("flex"), "0 1 auto", sel + " is its content's height with a shrink, never flex 0 0 auto (the section that could not give ran past the aside)");
  }
});

test("styles.css: the grown tier — the composer, and each other section while it holds more than its controls — gives first, down to a floor", () => {
  const grown = [".fc-margin > .fc-composer", ".fc-margin > .fc-sec-head:has(", ".fc-margin > .fc-sec-send:has(", ".fc-margin > .fc-sec-log:has("];
  for (const g of grown) {
    const rules = marginRules().filter((r) => r.selectors.some((s) => g.endsWith("(") ? s.startsWith(g) : s === g)).filter((r) => r.decls.has("flex-shrink"));
    assert.ok(rules.length >= 1, "a flex-shrink rule for " + g);
    for (const r of rules) {
      const shrink = parseFloat(r.decls.get("flex-shrink")!);
      assert.ok(shrink >= 1000, g + " shrinks at least a thousand times as readily as a collapsed section (flex 0 1 auto): " + r.decls.get("flex-shrink"));
      assert.ok(r.decls.has("min-height") && r.decls.get("min-height") !== "0", g + " keeps a floor, so a grown section never vanishes before the collapsed ones give: " + r.decls.get("min-height"));
    }
  }
  // the head's, the Send section's and the Log's tiers key on the section holding anything beyond its controls — a
  // structural test, so a new kind of row counts as growth without a rule of its own
  const tier = marginRules().filter((r) => r.decls.has("flex-shrink")).flatMap((r) => r.selectors).join(" | ");
  assert.match(tier, /\.fc-sec-head:has\(\.fc-head > :nth-child\(n\+2\):not\(\.fc-filter\)\)/, "the head beyond its button row and the filter's row (All · Comments · Changes, a control row, not growth): " + tier);
  assert.match(tier, /\.fc-sec-send:has\(.*?\.fc-foot > :nth-child\(n\+2\)/, "the foot beyond Accept all · Reject all: " + tier);
  assert.match(tier, /\.fc-sec-send:has\(> :not\(\.fc-foot, \.fc-send\)/, "rows moved into the footer: " + tier);
  assert.match(tier, /\.fc-sec-log:has\(\.fc-log > :nth-child\(n\+2\)\)/, "the Log beyond its toggle: " + tier);
});

test("styles.css: the track keeps its floor and the aside itself still clips — the fit comes from the sections, never from a panel that scrolls", () => {
  const track = given(".fc-margin > .fc-sec-cards");
  assert.equal(track.get("flex"), "1 1 0");
  assert.equal(track.get("min-height"), "30%");
  assert.equal(rule(".fc-panel.fc-margin"), ".fc-panel.fc-margin { overflow: hidden; padding: 0; gap: 0; }");
});

// ── the browser legs ─────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-fit-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, body and prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const a = STYLES.indexOf(BLOCK_A), b = STYLES.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in styles.css");
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), rule(".fileview-err"), STYLES.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel
// mounts. The card is 1000px wide (the margin layout; the fold is width-only) and as tall as the leg asks — the review's
// heights: a landscape phone's 330px, a short pane's 500px, and 200px, where the collapsed controls alone outgrow the
// room — inside a 700px viewport, so whatever the aside clips lies inside the viewport and a hit test there says whether
// a control reaches past the aside's box.
const page = (height: number): string => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: ${height}px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-fit.js"></script></body></html>`;

// ── the document, its comments and one change (synthetic) ──────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: "Paragraph " + i + " of the report", prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
const WHOLE = { id: (T0 - 5000) + "-0", author: "you", ts: T0 - 5000, body: "Add a summary at the top.", replies: [], resolved: false };
const COMMENTS = [WHOLE, comment(3, 1), comment(4, 2), comment(30, 3)];
const INS_AT = SRC.indexOf("Paragraph 6 of the report");
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + 9, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: "Paragraph", anchor: null };
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS },
  hunks: [HUNK], log: [],
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Box = { top: number; bottom: number; height: number; left: number; right: number };
type Sec = { box: Box; scrollHeight: number; clientHeight: number; overflowY: string };
/** The aside as laid out: its box and scroll state, each section's, the head's top, the Send button and the Log toggle,
 *  and every placed card's top against its mark's (the levelness the pass produced, whatever it is — a scrolled aside
 *  moves all of them by the same amount). */
type Fit = {
  margin: boolean; aside: Box; asideScrollTop: number; asideScrollHeight: number; asideClientHeight: number;
  sections: Record<string, Sec>; headTop: number; send: Box | null; log: Box | null; deltas: Record<string, number>; posted: number;
  warn: boolean; choice: boolean; refusal: boolean; confirm: boolean; composer: boolean;
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any, patch: Record<string, unknown>): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = [];
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: () => { /* inert */ },
      post: (m: any) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
      aside: (node: HTMLElement | null) => { const main = document.getElementById("main")!; main.querySelector(".fileview-aside")?.remove(); if (node) { node.classList.add("fileview-aside"); main.appendChild(node); } },
      setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
    };
    const unit = w.__romp.fileCommentsAction.mount(ctx) as HTMLElement;
    document.body.appendChild(unit);
    const settle = () => new Promise<void>((r) => setTimeout(r, 0));
    const reply = async () => { const last = posted[posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } })); await settle(); await settle(); };
    await reply();                                                // the probe
    (unit.querySelector("button") as HTMLButtonElement).click();  // open
    await reply();
    for (const cb of rendered) cb();                              // the viewer's onRendered: the paint pass over the body
    await settle();
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));   // the observers' frame
  }, [SRC, { ...STATUS, ...patch }, ABS, SID]);
}
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const click = (page: any, act: string): Promise<void> => page.evaluate((act: string) => { (document.querySelector('.fileview-aside [data-act="' + act + '"]') as HTMLElement).click(); }, act);
/** The host refuses the last request (a bulk decision here): the row lands under the foot. */
const refuse = (page: any): Promise<void> => page.evaluate(async () => {
  const posted = (window as any).__posted; const last = posted[posted.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: last.reqId, code: "failed", error: "nothing was written (a synthetic refusal)" } }));
  await new Promise<void>((r) => setTimeout(r, 0)); await new Promise<void>((r) => setTimeout(r, 0));
});
const fit = (page: any): Promise<Fit> => page.evaluate(() => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const body = document.getElementById("body")!;
  const box = (el: Element): Box => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right }; };
  const sections: Record<string, Sec> = {};
  for (const [name, sel] of [["head", ".fc-sec-head"], ["composer", ".fc-composer"], ["cards", ".fc-sec-cards"], ["send", ".fc-sec-send"], ["log", ".fc-sec-log"]]) {
    const s = aside.querySelector(sel) as HTMLElement | null;
    if (s && !s.hidden) sections[name] = { box: box(s), scrollHeight: s.scrollHeight, clientHeight: s.clientHeight, overflowY: getComputedStyle(s).overflowY };
  }
  const deltas: Record<string, number> = {};
  for (const card of Array.from(aside.querySelectorAll(".fc-card[data-id]")) as HTMLElement[]) {
    const m = body.querySelector('[data-act="fcopen"][data-id="' + card.dataset.id + '"]');
    if (m) deltas[card.dataset.id!] = card.getBoundingClientRect().top - m.getBoundingClientRect().top;
  }
  const one = (sel: string): Box | null => { const e = aside.querySelector(sel); return e ? box(e) : null; };
  return {
    margin: aside.classList.contains("fc-margin"), aside: box(aside), asideScrollTop: aside.scrollTop, asideScrollHeight: aside.scrollHeight, asideClientHeight: aside.clientHeight,
    sections, headTop: box(aside.querySelector(".fc-sec-head")!).top, send: one('[data-act="fcsend"]'), log: one('[data-act="fclog"]'), deltas, posted: (window as any).__posted.length,
    warn: !!aside.querySelector(".fc-sec-head .fc-warn"), choice: !!aside.querySelector(".fc-sec-head .fc-choice"), refusal: !!aside.querySelector(".fc-sec-send .fc-foot .fc-err"),
    confirm: !!aside.querySelector('.fc-sec-send [data-act="fcrejectallgo"]'), composer: !!aside.querySelector(".fc-composer:not([hidden])"),
  };
});
/** Whether the element under (x, y) is, or is inside, a match for `sel`. */
const hit = (page: any, x: number, y: number, sel: string): Promise<boolean> => page.evaluate(([x, y, sel]: [number, number, string]) => {
  const e = document.elementFromPoint(x, y);
  return !!(e && e.closest(sel));
}, [x, y, sel]);
/** Scroll a section the least that brings the control into its box — the control's own scroll of its section, wherever it
 *  stands: at the section's start (the Reject all confirm, in the foot at the top of the Send section) or at its end (Send). */
const toView = (page: any, sec: string, sel: string): Promise<void> => page.evaluate(([sec, sel]: [string, string]) => {
  const s = document.querySelector(".fileview-aside " + sec) as HTMLElement, e = document.querySelector(".fileview-aside " + sel) as HTMLElement;
  const sr = s.getBoundingClientRect(), r = e.getBoundingClientRect();
  if (r.top < sr.top) s.scrollTop += r.top - sr.top; else if (r.bottom > sr.bottom) s.scrollTop += r.bottom - sr.bottom;
}, [sec, sel]);
const boxOf = (page: any, sel: string): Promise<Box> => page.evaluate((sel: string) => { const r = (document.querySelector(".fileview-aside " + sel) as HTMLElement).getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right }; }, sel);
const active = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement as HTMLElement | null; return a ? (a.dataset.act || a.tagName) : "none"; });
const inside = (b: Box, of: Box, what: string): void => assert.ok(b.top >= of.top - 0.5 && b.bottom <= of.bottom + 0.5, what + " is inside the aside's box: " + b.top + ".." + b.bottom + " vs " + of.top + ".." + of.bottom);
/** The collapsed tier gives: with the grown sections at their floors and the track at its, the room left falls short of the
 *  collapsed sections' content, and they give the difference in proportion to their content, scrolling inside themselves
 *  — the two-tier rule's last step. Since the filter follow-on the head is three rows at 340px (the toggles wrap; All ·
 *  Comments · Changes stands under them), and at 330px that row is what brings the composer-open and confirm states here:
 *  with a two-row head the head, Send and the Log were uncut in both. `atMost`: the give the state can ask, the filter
 *  row's height and a little. */
const gaveShare = (f: Fit, names: string[], when: string, atMost: number): void => {
  const secs = names.map((n) => { const s = f.sections[n]; assert.ok(s, "the " + n + " section"); return { n, s }; });
  const content = secs.reduce((a, x) => a + x.s.scrollHeight, 0), room = secs.reduce((a, x) => a + x.s.clientHeight, 0);
  const short = content - room;
  assert.ok(short >= 0 && short <= atMost, when + ": the collapsed sections are short of their content by " + short + "px, within " + atMost);
  for (const { n, s } of secs) {
    assert.equal(s.overflowY, "auto", when + ": the " + n + " section scrolls inside itself");
    // within 2px: the shrink runs on the content boxes (no padding), and both heights are integers
    assert.ok(s.scrollHeight - s.clientHeight <= short * s.scrollHeight / content + 2, when + ": the " + n + " section gave no more than its share: " + (s.scrollHeight - s.clientHeight) + " of " + short);
  }
};
const uncut = (f: Fit, name: string): void => { const s = f.sections[name]; assert.ok(s, "the " + name + " section"); assert.ok(s.scrollHeight <= s.clientHeight + 1, "the " + name + " section kept its content's height (nothing to scroll): " + s.scrollHeight + " in " + s.clientHeight); };
const gave = (f: Fit, name: string): void => { const s = f.sections[name]; assert.ok(s, "the " + name + " section"); assert.equal(s.overflowY, "auto", "the " + name + " section is a scroll container of its own"); assert.ok(s.scrollHeight > s.clientHeight + 1, "the " + name + " section gave and scrolls inside itself: " + s.scrollHeight + " in " + s.clientHeight); };
/** Nothing past the aside's edge: the sections add up to the aside, so there is nothing for a focus to scroll to. */
const fits = (f: Fit, when: string): void => {
  assert.ok(f.asideScrollHeight <= f.asideClientHeight + 1, when + ": the sections add up to the aside, nothing past its edge: " + f.asideScrollHeight + " in " + f.asideClientHeight);
  assert.equal(f.asideScrollTop, 0, when + ": the aside is not scrolled");
  for (const [name, s] of Object.entries(f.sections)) inside(s.box, f.aside, when + ": the " + name + " section");
  assert.ok(f.sections.cards.box.height >= 0.3 * f.aside.height - 1, when + ": the track keeps its floor: " + f.sections.cards.box.height + " of " + f.aside.height);
};
/** The control at `sel` is under the pointer: as it stands, or once its own section is scrolled to bring it into view
 *  (toView). The first cut scrolled the section to its END, which reaches a control at the section's end alone: since the
 *  composer follow-on the grown sections hold more (the chord hint wraps the composer's button row at 340px; the Send
 *  caption), so the Send section shrinks further and its end no longer shows the confirm row at its top. */
async function reachable(page: any, sel: string, sec: string, f: Fit, what: string): Promise<void> {
  let b = await boxOf(page, sel);
  let cx = (b.left + b.right) / 2, cy = (b.top + b.bottom) / 2;
  // whole in its section's box, or scrolled there: a control the section's edge cuts (the Log toggle's bottom at 200px, the
  // filter row's at 330px with the composer open, since the filter follow-on made the head a row taller) still hits at its
  // center, and the first cut scrolled only on a miss, so it read a cut control as in reach
  const sb = await boxOf(page, sec);
  if (!(await hit(page, cx, cy, sel)) || b.top < sb.top - 0.5 || b.bottom > sb.bottom + 0.5) {
    await toView(page, sec, sel);
    await frames(page);
    b = await boxOf(page, sel); cx = (b.left + b.right) / 2; cy = (b.top + b.bottom) / 2;
  }
  inside(b, f.aside, what);
  assert.equal(await hit(page, cx, cy, sel), true, what + " is under the pointer at " + cx + "," + cy);
}
const same = (a: Record<string, number>, b: Record<string, number>, when: string): void => {
  assert.ok(Object.keys(a).length >= 2, "cards with marks to compare: " + Object.keys(a).length);
  for (const [k, v] of Object.entries(a)) assert.ok(Math.abs(v - b[k]) <= 0.5, when + ": card " + k + " stands where it was against its mark: " + v + " then " + b[k]);
};

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: string, height: number, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const pg = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    pg.on("pageerror", (e: Error) => { errors.push(e.message); });
    await pg.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: page(height) });
      if (u.pathname === "/dist/margin-fit.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await pg.goto("http://romp.test/page");
    await pg.waitForFunction(() => !!(window as any).__romp);
    await body(pg);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: a 330px panel — the composer, then the Reject all confirm, come out of their own sections; Send and the Log toggle stay in reach`, async (t) => {
    await inBrowser(t, name, 330, async (pg) => {
      await mount(pg, {});
      let f = await fit(pg);
      assert.equal(f.margin, true, "the margin layout is on at 1000px");
      fits(f, "closed");
      for (const s of ["head", "send", "log"]) uncut(f, s);
      // Comment on this file: the composer opens at the top. The review measured the Log toggle 11px past the aside here.
      await click(pg, "fcfile");
      await frames(pg);
      f = await fit(pg);
      assert.equal(f.composer, true, "the composer is open");
      fits(f, "composer open");
      gave(f, "composer");
      // the composer at its floor, and the room short of the head's, Send's and the Log's content by the filter row's height:
      // they give it in proportion (gaveShare), and the head's buttons, the filter's, Send and the Log toggle stay in reach
      gaveShare(f, ["head", "send", "log"], "composer open", 30);
      await reachable(pg, '[data-act="fcfile"]', ".fc-sec-head", f, "Comment on this file");
      await reachable(pg, '[data-act="fcfilter"][data-key="all"]', ".fc-sec-head", f, "the filter's All");
      await reachable(pg, '[data-act="fclog"]', ".fc-sec-log", f, "the Log toggle");
      await reachable(pg, '[data-act="fcsend"]', ".fc-sec-send", f, "the Send button");
      // Reject all: its confirm row joins the foot. The review measured Send 37px and the Log 68px past the aside here.
      await click(pg, "fcrejectall");
      await frames(pg);
      f = await fit(pg);
      assert.equal(f.confirm, true, "the Reject all confirm is up");
      fits(f, "composer and confirm");
      gave(f, "composer"); gave(f, "send");
      gaveShare(f, ["head", "log"], "composer and confirm", 30);   // the Send section at its floor too: a few px short, the head's and the Log's share
      await reachable(pg, '[data-act="fcfilter"][data-key="all"]', ".fc-sec-head", f, "the filter's All");
      await reachable(pg, '[data-act="fclog"]', ".fc-sec-log", f, "the Log toggle");
      await reachable(pg, '[data-act="fcsend"]', ".fc-sec-send", f, "the Send button");
      await reachable(pg, '[data-act="fcrejectallgo"]', ".fc-sec-send", f, "the confirm's Reject all");
    });
  });

  test(`in ${name}: a 500px panel with every row up — a focus and a Tab onto Send and the Log leave the aside unscrolled and every card on its mark`, async (t) => {
    await inBrowser(t, name, 500, async (pg) => {
      // the review's state: the tooling warning in the head, the file untracked (the Track choice offers file or folder),
      // the composer open, a refused Accept all's row under the foot, and the Reject all confirm
      await mount(pg, { agentTooling: "absent", trackedBy: null });
      await click(pg, "fcfile");
      await click(pg, "fctrack");
      await click(pg, "fcacceptall");
      await refuse(pg);
      await click(pg, "fcrejectall");
      await frames(pg);
      const f = await fit(pg);
      assert.equal(f.margin, true);
      assert.deepEqual({ warn: f.warn, choice: f.choice, refusal: f.refusal, confirm: f.confirm, composer: f.composer }, { warn: true, choice: true, refusal: true, confirm: true, composer: true }, "every growth the review named is up");
      fits(f, "every row up");
      gave(f, "head"); gave(f, "composer"); gave(f, "send");
      uncut(f, "log");
      await reachable(pg, '[data-act="fclog"]', ".fc-sec-log", f, "the Log toggle");
      await reachable(pg, '[data-act="fcsend"]', ".fc-sec-send", f, "the Send button");
      // a focus onto the Log toggle (the review's probe): the aside does not scroll, the head stays at the top, the cards stay
      await pg.evaluate(() => { (document.querySelector('.fileview-aside [data-act="fclog"]') as HTMLElement).focus(); });
      await frames(pg);
      let g = await fit(pg);
      assert.equal(await active(pg), "fclog", "the Log toggle has the keyboard");
      assert.equal(g.asideScrollTop, 0, "the aside did not scroll for the focus");
      assert.ok(Math.abs(g.headTop - g.aside.top) <= 0.5, "the head is still at the aside's top: " + g.headTop + " vs " + g.aside.top);
      same(f.deltas, g.deltas, "after the focus");
      // a real Tab from the confirm's Cancel walks the footer to Send and on to the Log: the same holds at each stop
      await pg.focus('.fileview-aside [data-act="fcrejectallcancel"]');
      for (let i = 0; i < 4; i++) {
        await pg.keyboard.press("Tab");
        g = await fit(pg);
        assert.equal(g.asideScrollTop, 0, "the aside did not scroll for the Tab onto " + await active(pg));
        same(f.deltas, g.deltas, "after the Tab onto " + await active(pg));
        if (await active(pg) === "fclog") break;
      }
      assert.equal(await active(pg), "fclog", "the Tabs reached the Log toggle");
    });
  });

  test(`in ${name}: a 200px panel — the collapsed controls alone outgrow the room, and still nothing leaves the aside; each control is a scroll of its own section away`, async (t) => {
    await inBrowser(t, name, 200, async (pg) => {
      await mount(pg, {});
      const f = await fit(pg);
      assert.equal(f.margin, true);
      fits(f, "200px");
      await reachable(pg, '[data-act="fcfile"]', ".fc-sec-head", f, "Comment on this file");
      await reachable(pg, '[data-act="fcsend"]', ".fc-sec-send", f, "the Send button");
      await reachable(pg, '[data-act="fclog"]', ".fc-sec-log", f, "the Log toggle");
    });
  });
}
