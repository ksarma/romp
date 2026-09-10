// The list layout's saved line under the header wears the arrivals line's dress (plans/file-review.md decision 43 and "The
// seen follow-on (2026-09-09)" under Slice 2; the review of 2026-09-09, round 2). In the list under a narrow column the panel
// stands the saved line under the header (file-comments.ts savedLineHead), right after the arrivals line when one stands: two
// one-line notices under the header, each a button pointing at a card. The first round carried the acknowledgment's dress (.fc-note,
// 0.86em, the inherited weight) into the head unchanged, where the arrivals line wears the fold toggles' (.fc-sec, 0.82em, 600),
// so the two rows stacked at different sizes and weights, against ui/CLAUDE.md's font rule (similar kinds of information wear
// the same size). The sheets now dress the head's copy as its neighbour (.fc-head > .fc-saved) and leave the margin layout's
// copy, beside the acknowledgment at the panel's foot, in its dress. Two legs: the declared rules in both sheets (the feed page
// loads only feed.css), and the rendered rows in a real engine, Chromium and Firefox, at a 600px viewer: an arrival standing
// behind the changes' fold through the save's clicks, and a whole-file comment saved whose card lands below the aside's box.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: invented
// prose, placeholder ids, the session name "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const read = (f: string): string => fs.readFileSync(path.join(UI, f), "utf8");
const FEED = read("feed.css");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", FEED]] as const;
const PANEL = read("file-comments.ts");

// ── the declared rules ───────────────────────────────────────────────────────────────────────────
function block(css: string): string {
  const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = css.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers");
  return css.slice(a, b);
}
/** The one rule declared under `head` (at a line start) in `css`: its declarations by property. */
function rule(css: string, head: string): Map<string, string> {
  const key = "\n" + head + " {";
  const at = css.indexOf(key);
  assert.ok(at >= 0, "a rule for " + head);
  assert.equal(css.indexOf(key, at + 1), -1, "one rule for " + head);
  const body = css.slice(at + key.length, css.indexOf("}", at));
  const out = new Map<string, string>();
  for (const d of body.split(";")) { const i = d.indexOf(":"); if (i > 0) out.set(d.slice(0, i).trim(), d.slice(i + 1).trim()); }
  return out;
}

for (const [name, css] of SHEETS) {
  test(name + ": under the header the saved line wears the arrivals row's size, weight and padding, .fc-sec's — and the base rule keeps the acknowledgment's size for the margin layout's foot", () => {
    const b = block(css);
    const sec = rule(b, ".fc-sec"), saved = rule(b, ".fc-saved"), head = rule(b, ".fc-head > .fc-saved"), note = rule(b, ".fc-note");
    assert.equal(sec.get("font-size"), "0.82em", "the fixture: the arrivals line's dress is .fc-sec's");
    assert.equal(sec.get("font-weight"), "600");
    assert.equal(head.get("font-size"), sec.get("font-size"), "the head's copy is the arrivals row's size");
    assert.equal(head.get("font-weight"), sec.get("font-weight"), "…and its weight");
    assert.equal(head.get("padding"), sec.get("padding"), "…and its padding, so the two rows stand the same height");
    assert.deepEqual(Array.from(head.keys()).sort(), ["font-size", "font-weight", "padding"], "the dress alone: the colour (--green through .fc-sent) and the button's shape stay the base rule's");
    assert.equal(saved.get("font-size"), note.get("font-size"), "the base rule is the acknowledgment's size, kept beside it at the margin layout's foot");
    assert.equal(saved.get("font-size"), "0.86em");
    assert.equal(saved.get("font-weight"), undefined, "…at the note's weight, inherited");
    assert.ok(b.indexOf("\n.fc-head > .fc-saved {") > b.indexOf("\n.fc-saved {"), "the head's rule follows the base rule it refines");
  });
}

test("the placement the rule dresses: the list layout stands the line under the header right after the arrivals line, the margin layout never puts it there, and both lines are text buttons — the arrivals line in .fc-sec's classes, the saved line in the note's (one button for both layouts: the head's dress is the sheets' by place, not a class of its own)", () => {
  assert.match(PANEL, /private savedLineHead\(\): HTMLElement \| null \{\n\s*return this\.margin \? null : this\.savedButton\(\);/, "the head's copy is the list layout's alone");
  assert.match(PANEL, /private savedLine\(\): HTMLElement \| null \{\n\s*return this\.margin \? this\.savedButton\(\) : null;/, "the Send section's copy is the margin layout's alone");
  assert.match(PANEL, /if \(this\.arrivals\.size\) head\.appendChild\(this\.arrivalLine\(\)\);\n(?:\s*\/\/[^\n]*\n)*\s*const saved = this\.savedLineHead\(\);\n\s*if \(saved\) head\.appendChild\(saved\);\n\s*return head;/,
    "the saved line is the head's last child, right after the arrivals line");
  assert.match(PANEL, /btn\(this\.arrivalText\(\), "fcarrivals", "fc-sec fc-arrivals"\)/, "the arrivals line is a .fc-sec button");
  assert.match(PANEL, /btn\(savedWhereWords\(this\.savedOut\.side\), "fcsavedgo", "fc-note fc-sent fc-saved"\)/, "the saved line is one button in the note's classes");
  // the class strings holding the token (fc-saved-hidden, the filter's row, is another class): one, the button's own
  assert.deepEqual(PANEL.match(/"[^"\n]*\bfc-saved(?![\w-])[^"\n]*"/g), ['"fc-note fc-sent fc-saved"'], "no second dress for the line in the panel: the head's is the sheets'");
});

// ── the rendered rows, in a real engine ──────────────────────────────────────────────────────────
/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "saved-dress-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card (the container the narrow fold queries), the body, the rendered
 *  prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const one = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [one(".fileview"), one(".fileview-body"), one(".fileview-md"), one(".fileview-md p"), one(".fileview-btn"), block(FEED)].join("\n");
}
// a 600px viewer: under the sheet's 680px container query the body row stacks (flex-direction column), and the panel reads the
// list layout from that (file-comments.ts marginMode)
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --text-muted: #888; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --err: #e55; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --overlay-10: rgba(255,255,255,0.1); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --box-border: #555; --input-bg: #111; }
${sheet()}
#wrap { width: 600px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/saved-dress.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const COMMENT = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: "Paragraph 2 of the report", prefix: "", suffix: " says something" }, replies: [], resolved: false };
/** An insertion of the session's over paragraph `i`'s first words: each in its own paragraph, so each is its own group. */
const hunk = (id: string, i: number, ts: number): Record<string, unknown> => {
  const w = "Paragraph " + i + " of the report", at = SRC.indexOf(w);
  return { id, author: "api", ts, kind: "ins", curFrom: at, curTo: at + w.length, baseFrom: at, baseTo: at, oldText: "", newText: w, anchor: null };
};
const sug = (...ids: string[]) => ids.map((id) => ({ id, authorId: SID }));
const base = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: sug("h1", "h2", "h3"), comments: [COMMENT] },
  hunks: [hunk("h1", 20, T0 + 100), hunk("h2", 22, T0 + 200), hunk("h3", 24, T0 + 300)], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
};
// the session's answer: a fourth change in a fourth paragraph — the fourth group, behind the "… 1 more change" fold (GROUP_LIMIT
// is three), so no gesture of the person's finds its card on screen and the arrival stands through the save's clicks
const ARRIVED = { ...base, store: { ...base.store, suggestions: sug("h1", "h2", "h3", "h4") }, hunks: [...base.hunks, hunk("h4", 26, T0 + 20000)], storeMtimeNs: "1757145600000000004" };
const NOTE = "Add the run's date.";
/** The reply to the save of a whole-file comment: the store with the fresh comment, its card after the changes and the comment. */
const withSaved = (id: string): Record<string, unknown> =>
  ({ ...ARRIVED, verb: "comment", storeMtimeNs: "1757145600000000005", store: { ...ARRIVED.store, comments: [COMMENT, { id, author: "you", ts: T0 + 50000, body: NOTE, replies: [], resolved: false }] } });

/** Mount the panel over the rendered document, answer its status asks with `status`, open it, and let the paint and the pass run.
 *  The viewer's onSaved hooks are kept (w.__saved) so a test can make the panel re-ask status the way the viewer's save does. */
function mount(page: any, status: Record<string, unknown>): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = []; w.__rendered = rendered;
    const saved: Array<(info: unknown) => void> = []; w.__saved = saved;
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: (cb: (info: unknown) => void) => { saved.push(cb); }, onClose: () => { /* inert */ },
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
  }, [SRC, status, ABS, SID]);
}
/** Answer the panel's LAST posted request with `status` (a fileCommentsResult), and let the render and the pass run. */
const answer = (page: any, status: Record<string, unknown>): Promise<void> => page.evaluate(async (status: Record<string, unknown>) => {
  const w = window as any;
  const last = w.__posted[w.__posted.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } }));
  const settle = () => new Promise<void>((r) => setTimeout(r, 0));
  await settle(); await settle();
  await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
}, status);
/** A status landing as the viewer's own save makes one land: the onSaved hooks make the panel re-ask, and `status` answers. */
const land = async (page: any, status: Record<string, unknown>): Promise<void> => {
  await page.evaluate(() => { for (const cb of (window as any).__saved) cb({ mtimeNs: "1757145600000000001", logged: true }); });
  await answer(page, status);
};
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).click(); }, sel);
const lastVerb = (page: any): Promise<string | null> => page.evaluate(() => { const p = (window as any).__posted; const l = p[p.length - 1]; return l ? l.verb || null : null; });

type Row = { text: string; fontSize: number; fontWeight: string; color: string; height: number; index: number; inHead: boolean };
type Rows = { layout: string; headKids: string[]; headPx: number; arrivals: Row | null; saved: Row | null; card: { top: number; bottom: number } | null; box: { top: number; bottom: number } };
/** The two rows under the header as the engine draws them, the head's children, and the saved card's box against the aside's. */
const rows = (page: any, cardId: string | null): Promise<Rows> => page.evaluate((cardId: string | null) => {
  const main = document.getElementById("main")!;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const head = aside.querySelector(".fc-head") as HTMLElement;
  const kids = Array.from(head.children) as HTMLElement[];
  const row = (act: string) => {
    const e = aside.querySelector('[data-act="' + act + '"]') as HTMLElement | null;
    if (!e) return null;
    const cs = getComputedStyle(e);
    return { text: e.textContent || "", fontSize: parseFloat(cs.fontSize), fontWeight: cs.fontWeight, color: cs.color, height: e.getBoundingClientRect().height, index: kids.indexOf(e), inHead: e.parentElement === head };
  };
  const card = cardId ? aside.querySelector('.fc-card[data-id="' + cardId + '"]') : null;
  const cr = card ? card.getBoundingClientRect() : null, br = aside.getBoundingClientRect();
  return {
    layout: getComputedStyle(main).flexDirection, headKids: kids.map((k) => k.className), headPx: parseFloat(getComputedStyle(head).fontSize),
    arrivals: row("fcarrivals"), saved: row("fcsavedgo"), card: cr ? { top: cr.top, bottom: cr.bottom } : null, box: { top: br.top, bottom: br.bottom },
  };
}, cardId);

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: string, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/saved-dress.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the list layout, an arrival standing and a comment just saved whose card lands below the aside's box — the arrivals line and the saved line stand as neighbours under the header at ONE size, weight and row height (before: 0.82em/600 over 0.86em/400, a taller row under a shorter one); the colours keep their meanings`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, base);
      let s = await rows(page, null);
      assert.equal(s.layout, "column", "the fixture: the 600px viewer stacks the body row, the list layout");
      assert.equal(s.arrivals, null, "the first status: no arrivals line");
      await land(page, ARRIVED);
      s = await rows(page, null);
      assert.ok(s.arrivals && s.arrivals.inHead, "the fixture: the arrival's line stands under the header: " + JSON.stringify(s.arrivals));
      assert.equal(s.arrivals!.text, "api made 1 change since you last looked");
      // Comment on this file, the words typed, Save: three gestures, none of which finds the arrival's card (behind the fold)
      await click(page, '.fileview-aside [data-act="fcfile"]');
      await frames(page);
      await page.focus(".fileview-aside .fc-composer .fc-input");
      await page.keyboard.type(NOTE);
      await click(page, '.fileview-aside [data-act="fcsave"]');
      await frames(page);
      assert.equal(await lastVerb(page), "comment", "the save's request went");
      const id = (T0 + 50000) + "-1";
      await answer(page, withSaved(id));
      s = await rows(page, id);
      assert.ok(s.card && s.card.bottom > s.box.bottom, "the fixture: the saved card lands below the aside's box: " + JSON.stringify(s.card) + " under " + JSON.stringify(s.box));
      assert.ok(s.arrivals && s.arrivals.inHead, "the arrival stands through the save: " + JSON.stringify(s.arrivals));
      assert.equal(s.arrivals!.text, "api made 1 change since you last looked");
      assert.ok(s.saved && s.saved.inHead, "the saved line stands under the header: " + JSON.stringify(s.saved));
      assert.equal(s.saved!.text, "Saved · the card is below");
      assert.equal(s.saved!.index, s.arrivals!.index + 1, "right after the arrivals line: " + JSON.stringify(s.headKids));
      assert.equal(s.saved!.index, s.headKids.length - 1, "the head's last row");
      // one dress for the two rows
      assert.ok(Math.abs(s.saved!.fontSize - s.arrivals!.fontSize) < 0.01, "one size: " + s.saved!.fontSize + " vs " + s.arrivals!.fontSize);
      assert.ok(Math.abs(s.saved!.fontSize - 0.82 * s.headPx) < 0.05, "the arrivals row's 0.82em of the head's " + s.headPx + "px (before: 0.86em): " + s.saved!.fontSize);
      assert.equal(s.saved!.fontWeight, s.arrivals!.fontWeight, "one weight");
      assert.equal(s.saved!.fontWeight, "600", "the arrivals row's (before: the inherited 400)");
      assert.ok(Math.abs(s.saved!.height - s.arrivals!.height) <= 0.5, "one row height: " + s.saved!.height + " vs " + s.arrivals!.height);
      // the colours are meanings, not dress: the accent for what arrived, the acknowledgment's green for what was saved
      assert.equal(s.arrivals!.color, "rgb(156, 210, 255)");
      assert.equal(s.saved!.color, "rgb(119, 204, 119)");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const own = fs.readFileSync(path.join(UI, "feed-css-saved-line-head-dress.test.ts"), "utf8");
  const prose = own.split("\n").filter((l) => l.trim().startsWith("//") || /^\s*test\(/.test(l)).join("\n");
  assert.doesNotMatch(prose, /\bfleet\b/i);
  assert.doesNotMatch(prose, /\b(suggestion|diff|annotation)\b/i);
  assert.doesNotMatch(own, /\/home\/[a-z]/, "no home path");
});
