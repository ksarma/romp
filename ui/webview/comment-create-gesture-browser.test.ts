// The chat's comment popover with two comments on one message in flight (the user, 2026-09-24, who asked for the chat's
// case of the saving-comment leak as its own change), over the REAL render.ts bundle in headless Chromium. A create's
// draft was keyed by the message ("new:" + the turn's uuid) and not spent at the send, its retry hold
// (cmtCreateInFlight) and its working mark ("pending:" + uuid) were keyed by the message too, and the kernel's answers
// (commentCreated, commentCreateFailed) named only the message. So a second comment on the same message opened with the
// first one's words and typed name; the first comment's acknowledgment deleted the second one's draft and swapped
// whatever create dialog was open in the session for the first thread; a refused create's words came back on every
// passage of its message; and a second send on the message took over the first one's retry hold and working mark, so
// the first was never re-posted after a transient refusal, and the first one's answer retired the second's hold. The
// fix has two modes, the dialog's, taken when it opens (the user's decision, 2026-09-25). ECHO mode, for a session
// whose host is last known to echo the create id (its latest connection's connect push carries the kernel's
// createIdEcho marker, its last caps frame lists commentCreateId, or its last create answer carried the key: each
// connection's connect push, the kernel's first strip on it, is played here ahead of its sessions, as a kernel sends
// it, the local kernel's caps frame after it, and a remote host's caps frame as federation hands it on, romp:hostCaps):
// the drafts are keyed by the passage, and the hold, the working mark and the dialog an answer adopts into by the
// create id the send gesture mints, which the kernel echoes on every answer (tests/test_comment_create_idempotent.py
// pins the kernel side). MAIN mode, for any other session (a host last known not to echo it, or not known either way
// yet): the page keeps main's handling, main's frame included, the bug too, and the main-mode group below plays the
// base's repro sequences and other sequences of answers without the key with no cap and compares every frame posted and
// every outcome with the base bundle's for the same steps (the tests of main's adoption and main's warn beside an
// echo-mode dialog, which play caps frames or an answer carrying the key, compare what they do to the thread side). An
// answer whose createId names a create this page minted in echo mode goes to the echo-mode code, and any other to main's,
// federation's own relayDrop answer to the drop of a main-mode create among them, which main never got and which leaves no
// hold armed that main's did not. The fail-safe (the user, 2026-09-28): a connect push without the marker, an answer without the key,
// or a caps frame without the cap shows that a host has no echo, and every echo-mode comment still out on it is handed
// back at that moment, with no retry and no re-post: its dialog closes, and its words and typed name wait in the note,
// which says it may or may not have been saved because the kernel restarted as an older version, with Bring it back; an
// echo-mode dialog open there that has not sent turns main mode. A host's build changes only across a reconnect, and
// the tests play the orders a page sees, but for those that say where they play inputs no page gets (a published
// socket generation and a socket-flip frame that do not pair, a romp:wsup the loaded page misses, a relay's answer or a
// caps frame ahead of its connection's connect push, an answer naming a comment the page handed back): every connection's first strip is its connect
// push; the page's own socket coming back (romp:wsup, and the shim's socket-flip frame in frame order) brings no caps
// frame, since a page gets the local kernel's once, in answer to its one ready, and a relay's redial
// (romp:hostRelayUp) brings none, since it posts no ready; the exception is an open, of either, that follows one whose
// ready got no caps frame: it is no redial, it sends the ready again, and a caps frame answers it. So after a restart
// the page learns the host's build from that connection's connect push, or from the answer to a comment sent in the
// moment before it, and a remote host's caps frame comes again only when the host is detached and attached again. The
// user's rules, in echo mode: a new comment opens empty while another is out, no words are lost, and none land on
// another passage or post twice. A sent dialog closed before its answer puts its words in the note, not saved yet and
// with no Bring it back while they are out; where two sets of words compete for one passage's box, the ones not placed
// there wait in that note, with a dismiss once refused, and Bring it back on their own passage (as fork PR 915 does for
// the file viewer's comments); the note shows in a create dialog on any passage of the message, naming each comment's
// passage, and its words can be selected to copy; and a connection whose connect push carries the marker posts again
// every echo-mode create still held on its host, once, and on the page's own socket only while that socket is open, so
// a comment whose answer the dropped socket owed is settled by the answer to its re-post (the kernel's repeat memo keeps
// that to one thread while the thread is open, among its latest 256 creates, and until the kernel restarts); nothing is
// posted again before a connection's connect push. The note's changes resize an open dialog as the page's own change,
// which the popover never saves as the size the person chose.
// Skips LOUDLY without a playwright browser (CI installs none before npm test). Synthetic values only: the notes-api
// demo, placeholder uuids, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
const renderJs = (): string => requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "render.ts")] }).outputFiles[0].text;
// the web dashboard's chat page without its federation bundle: the shared skeleton, the chat's sheet, then the chat
// bundle, behind a stand-in for the kernel's shim that records every post and numbers its sockets as the shim does
// (window.__rompSockGen, published before a reopen's romp:wsup and stamped on its socket-flip frame), and says whether
// its socket is open (window.__rompSockOpen: false while it is down or closing, when the shim would queue a post for the
// next socket): SHIM_GEN. The test plays the kernel's answers, and the page's own socket's strips as the kernel sends
// them, bare: the dashboard's federation bundle hands the page a local strip naming no host (freshHost ""), which the
// page reads the same way (render.ts noteConnectPush), and a VS Code pane, the one page with no federation bundle, has
// no reconnect to play (its extension replaces the page)
const SHIM_GEN = `window.__rompSockGen=0;window.__legWs="open";window.__legFlips=[];
window.__rompSockOpen=function(){return window.__legWs==="open";};`;
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>${SHIM_GEN}window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);},getState:function(){return null;},setState:function(){}}};</script>
<script src=/dist/render.js></script></body></html>`;
const federationJs = (): string => requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "federation.ts")] }).outputFiles[0].text;
// the chat page as the kernel serves it with another host attached: the REAL federation bundle before the chat's, and a
// shim shaped like the kernel's (kernel.py's acquireVsCodeApi: postMessage hands every send to window.__rompFed.outbound,
// synchronously, when federation is loaded), recording each post first. The other host's relay cannot connect (its
// /tunnels row names a local port nothing answers on), so federation drops that host's creates inside the page's own post
const REMOTE_CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>${SHIM_GEN}window.__posts=[];window.__local=[];window.__rompApp="chat";window.__rompLocalSend=function(m){window.__local.push(m);};
window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);if(window.__rompFed){window.__rompFed.outbound(m);}else{window.__rompLocalSend(m);}},getState:function(){return null;},setState:function(){}}};</script>
<script src=/dist/federation.js></script>
<script src=/dist/render.js></script></body></html>`;
const REMOTE_TUNNELS = { tunnels: [{ host: "TESTHOST2", hasToken: true, localPort: 9 }] };
// the kernel's identity palette (render.ts paletteColors, from /palette), so a new comment's colour differs from the
// colours its session's threads already wear (pickThreadColor)
const PALETTE = { colors: ["#1EA1EB", "#E06C75", "#98C379", "#C678DD"] };
// the kernel's model list, which the page reads for the create dialog's model and effort chips (render.ts loadModelChoices)
const MODELS = { rev: 1, models: [{ label: "Opus", value: "opus" }, { label: "Sonnet", value: "sonnet" }], efforts: [{ label: "Low", value: "low" }, { label: "High", value: "high" }] };
// the chat page with the other host's frames played as federation relays them (no federation bundle): a host's caps
// frame is played as federation hands it on, the romp:hostCaps event naming the host (hostCapsFrame)
const RELAYED_CHAT_HTML = CHAT_HTML;
// how openChat serves the page: the local kernel's session (false), the other host's with the real federation bundle
// (true), or the other host's with no federation bundle ("relayed": its frames played as federation relays them, and
// each post recorded as it leaves the page, so the test plays that host's kernel)
type Remote = boolean | "relayed";

const SID = "11111111-2222-3333-4444-555555555555";
const U1 = "aaaaaaaa-0000-0000-0000-000000000001", U2 = "aaaaaaaa-0000-0000-0000-000000000002", U3 = "aaaaaaaa-0000-0000-0000-000000000003", U4 = "aaaaaaaa-0000-0000-0000-000000000004";
const A2 = "The api session cut p95 latency by forty percent and the p99 by ten percent after the cache change landed.";
const A4 = "We recommend shipping the response cache in v1.2 once the fallback path has a test.";
const EVENTS = [
  { kind: "user", md: "Summarize the latency work.", uuid: U1 },
  { kind: "assistant", md: A2, uuid: U2 },
  { kind: "user", md: "And the recommendation?", uuid: U3 },
  { kind: "assistant", md: A4, uuid: U4 },
];
const SESSION = { type: "session", id: SID, name: "api", events: EVENTS, status: { state: "idle", sinceEpoch: null }, selfHost: "TESTHOST" };
// the same session on the other host, as this page names it (host-prefixed)
const REMOTE_SID = "TESTHOST2:" + SID;
const REMOTE_SESSION = { ...SESSION, id: REMOTE_SID };
const T_OLD = { tid: "t-0001", name: "api-comment-1", anchorUuid: U4, exact: "fallback path", status: "open", createdT: 1757145600, state: "",
  unread: false, replyOwed: false, promotedName: "", msgs: [{ who: "you", text: "Which fallback?", t: 1757145600 }, { who: "agent", text: "The stale-read fallback.", t: 1757145610 }] };
const FIRST = "First note: say which cache.";
const SECOND = "Second note: and the p99?";
const OTHER = "Other words typed since.";
// the first comment's thread as the kernel's frame lists it once the create lands
const T_FIRST = { ...T_OLD, tid: "t-0002", name: "api-comment-2", anchorUuid: U2, exact: "p95 latency",
  msgs: [{ who: "you", text: FIRST, t: 1757145700 }], replyOwed: true, state: "working" };
const LAG = "that message isn't in the transcript yet; try again in a moment";   // the kernel's ANCHOR_LAG_ERR
const REFUSAL = "thread names use letters, digits, . _ - only.";                 // one of _comment_create's real refusals
// the first comment's thread and a second comment's on the same message, as the kernel's frame lists them once they land
const T_CACHE = { ...T_FIRST, tid: "t-0003", name: "api-comment-3", exact: "cache change", msgs: [{ who: "you", text: SECOND, t: 1757145800 }] };
const P95 = "p95 latency";
// the toast for a comment on "p95 latency" refused with no unsent dialog of its passage open
const TOAST_P95 = "Your comment on “p95 latency” was not saved. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.";
const WAITS = "Post or clear this comment first";
// the capability a kernel announces when its create answers echo the createId (a literal, so the leg builds over the base
// to show its reds; comments.test.ts pins comments.ts's CREATE_ID_ECHO_CAP to this name in kernel.py's KERNEL_WS_CAPS)
const ECHO_CAP = "commentCreateId";
const NAME_WAITS = "Clear the typed name first";
// the caps a kernel with the create-id echo announces, and one without it (every release before this change); openChat
// plays the local kernel's caps frame after its connect push, as the kernel's ready arm sends it, and a remote host's
// as that host's relay delivers it, unless a test says a host has announced nothing yet (null)
const ECHO_CAPS = ["tagEdit", "chatProto2", ECHO_CAP];
const OLDER_CAPS = ["tagEdit", "chatProto2"];
// each host's caps (null: no caps frame yet), and whether each host's connect push carries the createId echo's marker
// (by default when its caps announce the echo: a kernel with the echo marks every connection's first strip, and one
// without it marks none). `beside`, on a page showing this kernel's session: the other host attached too, so a test can
// open its session in a tab beside this kernel's, the page served as the relayed page is, that host's relay's connect
// push played after this kernel's (the kernel sends a connection its strip ahead of its sessions, and federation hands
// a relay's frames on in the order they arrive)
type Caps = { local?: string[] | null; remote?: string[] | null; localPush?: boolean; remotePush?: boolean; firstDialFailed?: boolean; beside?: boolean };
const capsEcho = (caps: string[] | null): boolean => Array.isArray(caps) && caps.includes(ECHO_CAP);

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Pop = { open: boolean; mode: string | null; tid: string | null; quote: string | null; value: string | null; readOnly: boolean | null;
  name: string | null; prefill: string | null; send: string | null };
const pop = (page: any): Promise<Pop> => page.evaluate(() => {
  const p = document.getElementById("cmt-pop");
  const box = p ? p.querySelector(".cmt-input") as HTMLTextAreaElement | null : null;
  const nm = p ? p.querySelector(".cmt-name") as HTMLInputElement | null : null;
  const send = p ? p.querySelector('[data-act="cmtsend"]') as HTMLButtonElement | null : null;
  return { open: !!p, mode: p ? p.dataset.mode ?? null : null, tid: p ? p.dataset.tid ?? null : null,
    quote: p ? (p.querySelector(".cmt-quote")?.textContent ?? null) : null,
    value: box ? box.value : null, readOnly: box ? box.readOnly : null,
    name: nm ? nm.value : null, prefill: nm ? nm.dataset.prefill ?? null : null,
    send: send ? (send.disabled ? "disabled" : "enabled") + (send.classList.contains("busy") ? " busy" : "") : null };
});
/** The creates the page has posted so far, in order: what the kernel would have received (`hasId`: whether the frame
 *  carries the createId key at all; a frame of either mode carries it, main's since upstream added it, so hasId cannot
 *  tell the modes apart). */
const creates = (page: any): Promise<{ exact: string; text: string; createId: string; hasId: boolean }[]> => page.evaluate(() =>
  (window as any).__posts.filter((m: any) => m.type === "commentCreate").map((m: any) => ({ exact: m.exact, text: m.text, createId: m.createId, hasId: "createId" in m })));
/** The passages a create still in flight marks as working: the text of every mark whose thread is a pending synth. */
const workingMarks = (page: any): Promise<string[]> => page.evaluate(() =>
  (Array.from(document.querySelectorAll("mark.cmt-hl")) as HTMLElement[]).filter((m) => (m.dataset.tid || "").startsWith("pending:")).map((m) => m.textContent || ""));
/** The open create dialog's mode, as it took it when it opened: "1" echo mode (its data-echo stamp), "" main mode (no
 *  stamp, as main's dialog had none); null with no create dialog open. */
const echoOf = (page: any): Promise<string | null> => page.evaluate(() => {
  const p = document.getElementById("cmt-pop");
  return p && p.dataset.mode === "create" ? p.dataset.echo || "" : null;
});
/** The working marks' thread ids: a main-mode comment's is keyed by its message, an echo-mode one's by its create id. */
const markTids = (page: any): Promise<string[]> => page.evaluate(() =>
  (Array.from(document.querySelectorAll("mark.cmt-hl")) as HTMLElement[]).map((m) => m.dataset.tid || "").filter((x) => x.startsWith("pending:")));
/** The toasts showing, by their words. */
const toasts = (page: any): Promise<string[]> => page.evaluate(() =>
  Array.from(document.querySelectorAll("#warn-toasts .warn-toast-msg")).map((t) => t.textContent || ""));
/** The notes the open dialog shows for comments waiting there: the lead line, the words, Bring it back's state ("none"
 *  where the note has no Bring it back: a comment still being sent) and title, whether it has a dismiss, and (on a
 *  coarse pointer) the reason's line, null where there is none. */
const heldNotes = (page: any): Promise<{ lead: string; words: string; back: string; title: string; dismiss: boolean; why: string | null; whyShown: boolean }[]> =>
  page.evaluate(() => (Array.from(document.querySelectorAll("#cmt-pop .cmt-held-note")) as HTMLElement[]).map((n) => {
    const back = n.querySelector('[data-act="cmtheldback"]') as HTMLButtonElement | null;
    const why = n.querySelector(".cmt-held-why") as HTMLElement | null;
    return { lead: n.querySelector(".cmt-note")?.textContent || "", words: n.querySelector(".cmt-held-words")?.textContent || "",
      back: !back ? "none" : back.disabled ? "disabled" : "enabled", title: back ? back.title : "", dismiss: !!n.querySelector('[data-act="cmtheldx"]'),
      why: why ? why.textContent : null, whyShown: !!why && !why.hidden && getComputedStyle(why).display !== "none" };
  }));
/** A note's lead line, naming the comment's own passage: still out, or refused. */
const notYet = (passage: string): string => "Your earlier comment on “" + passage + "” is not saved yet:";
const notSaved = (passage: string): string => "Your earlier comment on “" + passage + "” was not saved:";
const NOT_YET = notYet(P95);
const NOT_SAVED = notSaved(P95);
// the toast for a comment the page gave up on that the kernel saved after all, the handed-back words changed since
const SAVED_AFTER_ALL = "Your comment on “p95 latency” was saved after all. What you typed in its box since is still there.";
async function selectIn(page: any, uuid: string, needle: string): Promise<{ x: number; y: number }> {
  return page.evaluate(([uuid, needle]: [string, string]) => {
    // the shown session's turn: a session in another tab keeps its transcript in the page, hidden
    const all = Array.from(document.querySelectorAll('.turn[data-uuid="' + uuid + '"]')) as HTMLElement[];
    const turn = all.find((x) => x.offsetParent) || all[0];
    if (!turn) throw new Error("no turn " + uuid + ": " + Array.from(document.querySelectorAll(".turn")).map((t) => t.getAttribute("data-uuid")).join(","));
    const w = document.createTreeWalker(turn, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    let t: Text | null = null;
    while ((t = w.nextNode() as Text | null)) { nodes.push(t); if (t.data.indexOf(needle) >= 0) break; }
    const r = document.createRange();
    if (t) { const from = t.data.indexOf(needle); r.setStart(t, from); r.setEnd(t, from + needle.length); }
    else {
      // the passage spans text nodes (a comment's mark splits them): its offsets in the turn's text, node by node
      const all = nodes.map((n) => n.data).join(""), from = all.indexOf(needle), to = from + needle.length;
      if (from < 0) throw new Error("no text " + needle);
      let pos = 0;
      for (const n of nodes) {
        const end = pos + n.data.length;
        if (from >= pos && from < end) r.setStart(n, from - pos);
        if (to > pos && to <= end) { r.setEnd(n, to - pos); break; }
        pos = end;
      }
    }
    const s = getSelection()!; s.removeAllRanges(); s.addRange(r);
    const b = r.getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2 };
  }, [uuid, needle]);
}
/** A press outside the popover: it closes, as a new selection's mousedown closes it. */
const pressOutside = async (page: any) => { await page.mouse.move(5, 5); await page.mouse.down(); await page.mouse.up(); };
/** Two rendering frames in the page, then whether `sel` still matches: a scroll is dispatched in a frame's scroll
 *  steps, ahead of that frame's animation-frame callbacks, so one the steps before caused (a dialog's focus scrolls the
 *  transcript), or one a callback of the first frame causes, has been dispatched by the second. */
const afterTwoFrames = (page: any, sel: string): Promise<boolean> => page.evaluate((sel: string) => new Promise<boolean>((res) =>
  requestAnimationFrame(() => requestAnimationFrame(() => res(!!document.querySelector(sel))))), sel);
/** `needle` in message `uuid` selected and its menu opened with a right-click on it, once the menu has stood through two
 *  rendering frames. Any scroll closes the menu (ctx-menu.ts showMenuCard), and the scroll a closing dialog causes (the
 *  transcript's scroll position clamps as the dialog leaves) is dispatched a frame later, which under load fell after
 *  the menu opened: the click on its row then timed out on a detached menu. So the selection and the right-click wait for those frames first, and a menu such a scroll closed anyway is opened
 *  again, at most three times. */
async function openSelectionMenu(page: any, uuid: string, needle: string): Promise<void> {
  for (let i = 0; i < 3; i++) {
    await afterTwoFrames(page, "body");
    const at = await selectIn(page, uuid, needle);
    await page.mouse.click(at.x, at.y, { button: "right" });
    await page.waitForSelector(".ctx-menu .ctx-item", { timeout: 5000 });
    if (await afterTwoFrames(page, ".ctx-menu .ctx-item")) return;
  }
  throw new Error("the selection menu closed before its row could be clicked, three times running");
}
/** A comment opened as a person opens one: a press outside the popover (it closes), the passage selected, a right-click
 *  on it, the menu's Comment. */
async function commentOn(page: any, uuid: string, needle: string): Promise<void> {
  await pressOutside(page);
  await openSelectionMenu(page, uuid, needle);
  const labels = await page.evaluate(() => Array.from(document.querySelectorAll(".ctx-menu .ctx-item-label")).map((l) => l.textContent));
  if (!labels.includes("Comment")) throw new Error("the selection menu offers no Comment: " + JSON.stringify(labels));
  await page.click('.ctx-menu .ctx-item:has(.ctx-item-label:text-is("Comment"))');
  await page.waitForSelector("#cmt-pop .cmt-input", { timeout: 5000 });
  const p = await pop(page);
  assert.deepEqual([p.mode, p.quote], ["create", needle], "the precondition: a create dialog on the passage selected");
}
/** The open dialog's box emptied, whatever it opened with, and `text` typed into it. */
async function typeFresh(page: any, text: string): Promise<void> {
  await page.fill("#cmt-pop .cmt-input", "");
  await page.focus("#cmt-pop .cmt-input");
  await page.keyboard.type(text);
}
async function openChat(t: any, body: (page: any, send: (m: unknown) => Promise<void>) => Promise<void>, ctx: Record<string, unknown> = {},
                        remote: Remote = false, caps: Caps = {}): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers before npm test)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); } catch (e) { t.skip("no playwright chromium on this box; this leg needs it (CI installs none before npm test): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const fedOn = remote === true, sid = remote ? REMOTE_SID : SID;
    const js = renderJs(), fed = fedOn ? federationJs() : "";
    const page = await browser.newPage({ viewport: { width: 1100, height: 760 }, ...ctx });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8",
        body: fedOn ? REMOTE_CHAT_HTML : remote === "relayed" ? RELAYED_CHAT_HTML : CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (fedOn && u.pathname === "/dist/federation.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: fed });
      if (fedOn && u.pathname === "/tunnels") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(REMOTE_TUNNELS) });
      if (u.pathname === "/models") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MODELS) });
      if (u.pathname === "/palette") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(PALETTE) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/chat");
    // a frame dispatched as the shim delivers the kernel's: synchronously, so a re-post it causes is recorded on
    // return; the sessions it brings are kept for the strips connectPush plays, and the threads each comments frame
    // lists for the frame ackFirst plays
    const send = (m: unknown) => page.evaluate((m: any) => {
      const w = window as any;
      if (m && m.type === "session" && typeof m.id === "string" && !w.__legSids.includes(m.id)) w.__legSids.push(m.id);
      if (m && m.type === "comments" && typeof m.id === "string") (w.__legThreads = w.__legThreads || {})[m.id] = m.threads || [];
      window.dispatchEvent(new MessageEvent("message", { data: m }));
    }, m);
    const besideOn = remote === false && !!caps.beside;
    await page.evaluate(([mode, s]: [string, string]) => { const w = window as any; w.__legMode = mode; w.__legSids = [s]; },
                        [fedOn ? "fed" : remote === "relayed" || besideOn ? "relayed" : "local", sid]);
    const local = caps.local === undefined ? ECHO_CAPS : caps.local;
    const other = caps.remote === undefined ? ECHO_CAPS : caps.remote;
    // the page's first dial failing (a kernel down at load): the shim's netState down and romp:wsdown, then the first socket
    // to open, which sets netState up and fires no romp:wsup and no socket-flip frame (a first open is no reconnect)
    if (caps.firstDialFailed) await page.evaluate(() => { const w = window as any; w.__rompLocalUp = false; window.dispatchEvent(new Event("romp:wsdown")); w.__rompLocalUp = true; });
    // each connection's connect push first: the kernel's first strip on it, ahead of its sessions and of any caps frame
    // (kernel.py _tab_order_frame), carrying the createId echo's marker from a kernel with the echo
    await connectPush(page, "", caps.localPush ?? capsEcho(local));
    if (fedOn) await page.waitForFunction(() => { const f = (window as any).__rompFed; return !!f && f.hosts().includes("TESTHOST2"); }, null, { timeout: 15000 });
    if (remote) await connectPush(page, "TESTHOST2", caps.remotePush ?? capsEcho(other));
    else if (besideOn) {                                                 // the other host's relay, its strip listing its session beside this kernel's
      await page.evaluate((s: string) => { (window as any).__legSids.push(s); }, REMOTE_SID);
      await connectPush(page, "TESTHOST2", caps.remotePush ?? capsEcho(other));
    }
    await send(remote ? REMOTE_SESSION : SESSION);
    await page.waitForSelector('.turn[data-uuid="' + U2 + '"]', { timeout: 10000 });
    await send({ type: "comments", id: sid, threads: [T_OLD] });
    await page.waitForSelector('mark.cmt-hl[data-tid="' + T_OLD.tid + '"]', { timeout: 10000 });
    // the local kernel's caps frame, which its ready arm sends after the connect push (kernel.py _send_caps)
    if (local) await send({ type: "caps", caps: local, viewsSeq: null });
    // the other host's, as its relay delivers it: through the real federation bundle's inbound door, which hands it to
    // the page under that host's name, or as federation would hand it on, on the relayed page
    if (fedOn && other) await page.evaluate((c: string[]) => (window as any).__rompFed.inbound("TESTHOST2", { type: "caps", caps: c, viewsSeq: null }), other);
    if ((remote === "relayed" || besideOn) && other) await hostCapsFrame(page, other);
    await body(page, send);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}
/** The first comment, on "p95 latency" in message U2 (a typed name when `name` is given), sent with Enter and left
 *  unanswered. Returns the create id its send minted. */
async function firstCreate(page: any, name?: string): Promise<string> {
  await commentOn(page, U2, "p95 latency");
  if (name) await page.fill("#cmt-pop .cmt-name", name);
  await page.focus("#cmt-pop .cmt-input");
  await page.keyboard.type(FIRST);
  await page.keyboard.press("Enter");
  const sent = await creates(page);
  assert.deepEqual(sent.map((c) => [c.exact, c.text]), [["p95 latency", FIRST]], "the precondition: one create posted, unanswered");
  assert.ok(sent[0].createId, "the precondition: the send stamped its create id");
  assert.equal((await pop(page)).send, "disabled busy", "the precondition: the first comment's Comment button reads busy while its create is out");
  return sent[0].createId;
}
/** A second comment on the same message ("cache change" in U2), typed fresh and sent while the first is unanswered.
 *  Returns its create id. */
async function secondCreate(page: any): Promise<string> {
  await commentOn(page, U2, "cache change");
  await typeFresh(page, SECOND);
  await page.keyboard.press("Enter");
  const sent = await creates(page);
  assert.deepEqual(sent.map((c) => [c.exact, c.text]), [["p95 latency", FIRST], ["cache change", SECOND]], "the precondition: two creates posted on one message");
  assert.notEqual(sent[1].createId, sent[0].createId, "the precondition: two gestures, two create ids");
  return sent[1].createId;
}
/** The first comment's create lands: the kernel sends the comments frame first, listing every thread of the session (the
 *  ones its last comments frame listed, and the first comment's), then the ack (createId omitted for a kernel without
 *  the echo). */
async function ackFirst(page: any, send: (m: unknown) => Promise<void>, createId: string | null): Promise<void> {
  const listed: { tid: string }[] = await page.evaluate((sid: string) => ((window as any).__legThreads || {})[sid] || [], SID);
  await send({ type: "comments", id: SID, threads: [...listed.filter((x) => x.tid !== T_FIRST.tid), T_FIRST] });
  await send(createId === null ? { type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 }
                               : { type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId });
  await page.waitForFunction(() => !!document.querySelector('mark.cmt-hl[data-tid="t-0002"]'), null, { timeout: 5000 });
}
/** A real refusal, in the kernel's order: the warn toast, then the typed nack. */
async function refuse(send: (m: unknown) => Promise<void>, createId: string): Promise<void> {
  await send({ type: "warn", text: REFUSAL });
  await send({ type: "commentCreateFailed", id: SID, uuid: U2, createId, transient: false, text: REFUSAL });
}
const lagNack = (send: (m: unknown) => Promise<void>, createId: string) =>
  send({ type: "commentCreateFailed", id: SID, uuid: U2, createId, transient: true, text: LAG });
/** federation.ts's own two texts for a comment create it drops (dropWarn: the warn, then the transient refusal),
 *  evaluated from its source for `host`, so a fixture that plays them restates neither. Loud when dropWarn no longer
 *  holds exactly those two. */
function federationDropTexts(host: string): { warn: string; refusal: string } {
  const src = fs.readFileSync(path.join(UI, "federation.ts"), "utf8");
  const at = src.indexOf("  private dropWarn(host: string, msg: any): void {");
  assert.ok(at > 0, "federation.ts answers a dropped send in dropWarn");
  const body = src.slice(at, src.indexOf("\n  }\n", at));
  const texts = Array.from(body.matchAll(/text: (`[^`]*`)/g), (m) => m[1]);
  assert.equal(texts.length, 2, "dropWarn's two texts, the warn's and the transient refusal's: " + JSON.stringify(texts));
  const [warn, refusal] = texts.map((t) => String(new Function("host", "msg", "return " + t + ";")(host, { type: "commentCreate" })));
  return { warn, refusal };
}
/** The page's own socket dropping and opening again, as the shim plays it (kernel.py's shim): its netState down and
 *  romp:wsdown at the close; at the open its netState up, the socket's generation one more (window.__rompSockGen),
 *  romp:wsup, and the socket-flip frame carrying that generation ({type: "wsup", gen}) in frame order. The new socket's
 *  connect push is the test's to play (connectPush), marked or not: the kernel that answers may be another build. A
 *  host's relay opening again is federation's romp:hostRelayUp (relayUp). */
const socketDown = (page: any) => page.evaluate(() => { const w = window as any; w.__rompLocalUp = false; w.__legWs = "down"; window.dispatchEvent(new Event("romp:wsdown")); });
/** The page's own socket CLOSING (a clean close from something between the page and the kernel, its handshake under
 *  way): the shim queues a send it cannot write, for the next socket, and says its socket is not open
 *  (window.__rompSockOpen), while its netState still reads up until onclose. */
const socketClosing = (page: any) => page.evaluate(() => { (window as any).__legWs = "closing"; });
/** A socket opening while frames of a socket that dropped before them are still in the shim's queue: its netState up,
 *  its generation published and romp:wsup, fired at the open, with its socket-flip frame queued behind those frames, to
 *  be handed on later in frame order (flipFrame). socketUp plays both at once, for a queue with nothing left in it. */
const socketOpens = (page: any) => page.evaluate(() => {
  const w = window as any; w.__rompSockGen++; w.__legFlips.push(w.__rompSockGen); w.__legWs = "open";
  w.__rompLocalUp = true; window.dispatchEvent(new Event("romp:wsup"));
});
/** The oldest socket-flip frame still queued in the shim handed on, carrying its socket's generation. */
const flipFrame = (page: any) => page.evaluate(() => {
  const w = window as any;
  if (!w.__legFlips.length) throw new Error("no socket-flip frame is queued");
  window.dispatchEvent(new MessageEvent("message", { data: { type: "wsup", gen: w.__legFlips.shift() } }));
});
const socketUp = async (page: any) => { await socketOpens(page); await flipFrame(page); };
const wsup = async (page: any) => { await socketDown(page); await socketUp(page); };
/** A connection's connect push: the first strip the kernel sends on it (kernel.py _tab_order_frame: tabs-first, ahead of
 *  its sessions and of any caps frame), carrying createIdEcho when that host's kernel echoes the create id (`marked`).
 *  `host` "" is the page's own socket's, a host's name that host's relay's. Played as the page receives it: on the chat
 *  page with no federation bundle, the local kernel's strip as the kernel sends it; on the relayed page, a host's strip
 *  as federation hands it on (a merged strip over every session the page shows, naming the host whose push drove it,
 *  freshHost); with the real federation bundle, through federation's inbound door. */
const connectPush = (page: any, host: string, marked: boolean) => page.evaluate(([host, marked]: [string, boolean]) => {
  const w = window as any, sids: string[] = w.__legSids;
  const hostOfId = (id: string) => id.includes(":") ? id.slice(0, id.indexOf(":")) : "";
  const mine = sids.filter((id) => hostOfId(id) === host);
  const tabs = (ids: string[]) => ids.map((id) => ({ id, name: "api" }));
  const mark = marked ? { createIdEcho: true } : {};
  if (w.__legMode === "local" && host) throw new Error("the page with no federation bundle has no relay: " + host);
  if (w.__legMode === "fed") {
    const bare = mine.map((id) => host ? id.slice(host.length + 1) : id);
    w.__rompFed.inbound(host, { type: "tabOrder", order: bare, tabs: tabs(bare), live: bare, ...mark });
  } else if (w.__legMode === "relayed")
    window.dispatchEvent(new MessageEvent("message", { data: { type: "tabOrder", order: sids, tabs: tabs(sids), live: sids, skeleton: [], freshHost: host, ...mark } }));
  else window.dispatchEvent(new MessageEvent("message", { data: { type: "tabOrder", order: mine, tabs: tabs(mine), live: mine, selfHost: "TESTHOST", ...mark } }));
}, [host, marked]);
/** The page's own socket back on a kernel that echoes the create id (`marked`) or not: wsup, then that connection's
 *  connect push. */
const reconnect = async (page: any, marked: boolean) => { await wsup(page); await connectPush(page, "", marked); };
/** A host's relay back on a kernel that echoes the create id (`marked`) or not: romp:hostRelayUp, then that
 *  connection's connect push. */
const relayBack = async (page: any, host: string, marked: boolean) => { await relayUp(page, host); await connectPush(page, host, marked); };
/** The other host's caps frame as federation hands it to the page (federation.ts, the inbound door's romp:hostCaps). */
const hostCapsFrame = (page: any, caps: string[]) => page.evaluate((c: string[]) => {
  window.dispatchEvent(new CustomEvent("romp:hostCaps", { detail: { host: "TESTHOST2", caps: c } })); }, caps);
const relayUp = (page: any, host: string) => page.evaluate((h: string) => { window.dispatchEvent(new CustomEvent("romp:hostRelayUp", { detail: { host: h } })); }, host);
/** The create ids the next session frame re-posts (the frame-keyed retry of every create a transient nack armed). */
async function repostsOnNextFrame(page: any, send: (m: unknown) => Promise<void>): Promise<string[]> {
  const before = (await creates(page)).length;
  await send(SESSION);
  return (await creates(page)).slice(before).map((c) => c.createId);
}
/** The first comment sent under a typed name, its dialog closed, a new dialog opened on the same passage and `typed`
 *  typed into it, then the first comment refused. Returns nothing: the dialog open on the passage is the new one. */
async function refusedBesideTypedWords(page: any, send: (m: unknown) => Promise<void>, typed: string): Promise<void> {
  const first = await firstCreate(page, "cache-question");
  await commentOn(page, U2, "p95 latency");                            // the sending dialog closed; the same passage again
  await page.focus("#cmt-pop .cmt-input");
  await page.keyboard.type(typed);
  assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_YET, FIRST, "none"]],
    "the precondition: while the first comment is out it waits in the passage's note with no Bring it back");
  await refuse(send, first);
}
/** A second comment sent from the first one's passage after the first's dialog closed unanswered: the passage's box
 *  opened empty under the suggested name, the first comment's words (sent under `firstName` when given) waiting in
 *  its note, not saved yet, and the person typed SECOND. Returns the two create ids; the dialog open is the second
 *  one's, sent. */
async function secondOnSamePassage(page: any, firstName?: string): Promise<[string, string]> {
  const first = await firstCreate(page, firstName);
  await pressOutside(page);
  await commentOn(page, U2, "p95 latency");
  const back = await pop(page);
  assert.deepEqual([back.value, back.name, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], ["", back.prefill, [[NOT_YET, FIRST, "none"]]],
    "the precondition: the passage's box opens empty, the first comment waiting in its note, not saved yet");
  await page.focus("#cmt-pop .cmt-input");
  await page.keyboard.type(SECOND);
  await page.keyboard.press("Enter");
  const sent = await creates(page);
  assert.deepEqual(sent.map((c) => [c.exact, c.text]), [["p95 latency", FIRST], ["p95 latency", SECOND]], "the precondition: two creates on one passage");
  return [first, sent[1].createId];
}

test("in chromium: a second comment on a message, opened while the first comment there is still being created, opens empty under the suggested name", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page, "cache-question");
    await commentOn(page, U2, "cache change");
    const p = await pop(page);
    assert.equal(p.mode, "create", "the second Comment opened a create dialog");
    assert.deepEqual([p.value, p.name], ["", p.prefill],
      "a new comment opened on a message whose first comment is still being created opens empty and under the suggested name: the first comment's words and typed name are not the new comment's");
  });
});

test("in chromium: a second comment on the same passage, opened while the first comment's create is unanswered, opens empty under the suggested name", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page, "cache-question");
    await commentOn(page, U2, "p95 latency");
    const p = await pop(page);
    assert.equal(p.mode, "create", "the second Comment opened a create dialog");
    assert.deepEqual([p.value, p.name], ["", p.prefill],
      "a new comment opened on the passage whose first comment is still being created opens empty and under the suggested name: the send spent the first comment's words and typed name, which its create carries");
  });
});

test("in chromium: the first comment's acknowledgment leaves a second comment's dialog on the same message open, with its words", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await commentOn(page, U2, "cache change");
    await typeFresh(page, SECOND);
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid, p.value], ["create", U2, SECOND],
      "the first comment's acknowledgment leaves the second comment's dialog on the same message open with its words: an ack adopts only the dialog that sent the create it answers");
    await commentOn(page, U2, "cache change");
    assert.equal((await pop(page)).value, SECOND,
      "the second comment's words survive a close and reopen: the first comment's acknowledgment spends only the first comment's words");
  });
});

test("in chromium: the first comment's acknowledgment leaves a comment being written on another message open, with its words", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await commentOn(page, U4, "response cache");
    await typeFresh(page, SECOND);
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid, p.value], ["create", U4, SECOND],
      "the first comment's acknowledgment leaves the comment being written on another message open with its words: an ack adopts only the dialog that sent the create it answers");
  });
});

test("in chromium: a refused create's words come back in its own dialog, and a comment on another passage of the message opens empty", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await refuse(send, first);
    const own = await pop(page);
    assert.deepEqual([own.mode, own.tid, own.value, own.readOnly, own.send], ["create", U2, FIRST, false, "enabled"],
      "a refused create hands its own dialog back with its words, editable, and a live Comment button");
    await commentOn(page, U2, "ten percent");
    assert.equal((await pop(page)).value, "",
      "a comment opened on another passage of the refused comment's message opens empty: the refused words go back to their own passage only");
  });
});

test("in chromium: two creates on one message keep one retry hold each", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    const second = await secondCreate(page);
    await lagNack(send, first);
    await lagNack(send, second);
    assert.deepEqual((await repostsOnNextFrame(page, send)).sort(), [first, second].sort(),
      "each create's transient refusal re-posts that create on the next session frame: the second send on the message did not take over the first one's retry hold");
  });
});

test("in chromium: the first create's acknowledgment retires only its own hold and working mark", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await lagNack(send, first);                                          // the first parked: its retry armed
    const second = await secondCreate(page);
    await lagNack(send, second);                                         // the second parked too
    await ackFirst(page, send, first);                                   // the pusher lands the first, and acks every chat client
    assert.deepEqual(await workingMarks(page), ["cache change"],
      "the second create's working mark stays on its passage while the second create is unanswered");
    assert.deepEqual(await repostsOnNextFrame(page, send), [second],
      "the next session frame re-posts the second alone: the first's ack retired the first create's armed hold, and only it");
  });
});

test("in chromium: the first create's refusal leaves the second create's hold armed and its dialog waiting", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await lagNack(send, first);                                          // the first parked: its retry armed
    const second = await secondCreate(page);
    await lagNack(send, second);
    assert.deepEqual((await repostsOnNextFrame(page, send)).sort(), [first, second].sort(), "the precondition: the next session frame re-posts both");
    await refuse(send, first);                                           // the first's re-post refused (its name taken by then, say)
    await lagNack(send, second);                                         // the second's re-post still parked
    const p = await pop(page);
    assert.deepEqual(await repostsOnNextFrame(page, send), [second],
      "the second create's retry still re-posts it after the first create's refusal, and the first is not re-posted: the refusal dropped the first create's hold only");
    assert.deepEqual([p.mode, p.tid, p.value, p.send], ["create", U2, SECOND, "disabled busy"],
      "the first create's refusal leaves the second create's dialog waiting on its own answer: only the refused create's dialog is handed back");
  });
});

test("in chromium: Enter again in a dialog whose comment is still being created posts nothing", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page);
    assert.deepEqual(await page.evaluate(() => [(document.querySelector("#cmt-pop .cmt-input") as HTMLTextAreaElement).readOnly,
                                                (document.querySelector("#cmt-pop .cmt-name") as HTMLInputElement).readOnly]), [true, true],
      "the send makes the box and the name read-only at once: the words and name are out with the create");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");
    assert.equal((await creates(page)).length, 1, "a second Enter in a dialog whose comment is still being created posts nothing: one dialog, one create");
  });
});

test("in chromium: a warn that is not the comment's refusal leaves its dialog busy with its words, and its working mark", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await firstCreate(page, "cache-question");
    await send({ type: "warn", text: "the clipboard could not be read" });   // any warn rebuilds an open create dialog
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.readOnly, p.send], ["create", FIRST, true, "disabled busy"],
      "a warn that is not this comment's refusal leaves its dialog busy with its words: only its own answer hands it back");
    assert.equal(p.name, "cache-question", "and the rebuilt dialog shows the name its create carries (the send spent the name's draft)");
    assert.deepEqual(await workingMarks(page), ["p95 latency"], "and the comment's working mark stays while its create is out");
  });
});

test("in chromium: an acknowledgment that beat its thread's frame adopts into no dialog opened since", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: first });   // the ack first: the tid parks for the frame
    await commentOn(page, U2, "cache change");                           // the sending dialog closed; another opened
    await typeFresh(page, SECOND);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
    await page.waitForFunction(() => !!document.querySelector('mark.cmt-hl[data-tid="t-0002"]'), null, { timeout: 5000 });
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value], ["create", "cache change", SECOND],
      "the frame adopts a parked acknowledgment only into the dialog that sent the comment, never into one opened since");
  });
});

test("in chromium: a sent dialog whose acknowledgment beat its thread's frame keeps its words and typed name through a rebuild until the frame adopts it", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    // the ack with no comments frame before it (the kernel built none for the session), so the frame that lists the
    // thread comes later; meanwhile an unrelated warn rebuilds the open dialog
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: first });
    await send({ type: "warn", text: "the clipboard could not be read" });
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.name, p.readOnly, p.send], ["create", FIRST, "cache-question", true, "disabled busy"],
      "the rebuilt dialog still shows the comment's words and typed name, read-only and busy: its create is settled, and the frame that adopts it is still to come");
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
    const q = await pop(page);
    assert.deepEqual([q.mode, q.tid], ["thread", "t-0002"], "and the frame adopts its thread into that dialog");
  });
});

test("in chromium: a refused comment's words stay out of an empty dialog open on another passage of the message, and show in its note there", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await commentOn(page, U2, "cache change");
    await refuse(send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value], ["create", "cache change", ""],
      "a refusal hands the words back to their own passage only: the box of the dialog open on another passage of the message stays as it was");
    assert.deepEqual(await heldNotes(page), [{ lead: NOT_SAVED, words: FIRST, back: "none", title: "", dismiss: true, why: null, whyShown: false }],
      "the refused words show at once in that dialog's note, which names their passage, with a dismiss and no Bring it back: that fills only their own passage's box");
  });
});

test("in chromium: an acknowledgment naming a create this viewer does not hold adopts nothing and retires nothing", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    // another viewer's comment on the same message landed by the pusher, which acks every chat client
    const other = { ...T_FIRST, tid: "t-0003", name: "api-comment-3", exact: "cache change", msgs: [{ who: "you", text: "Another viewer's note.", t: 1757145800 }] };
    await send({ type: "comments", id: SID, threads: [T_OLD, other] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: "k2another0viewer" });
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid, p.value, p.send], ["create", U2, FIRST, "disabled busy"],
      "an acknowledgment for a create this viewer never sent leaves its own sent dialog waiting: it adopts only the dialog whose create it names");
    assert.deepEqual(await workingMarks(page), ["p95 latency"], "and the comment's working mark stays: another passage's thread does not supersede it");
    await lagNack(send, first);
    assert.deepEqual(await repostsOnNextFrame(page, send), [first], "and its hold stands: its own transient refusal still re-posts it");
  });
});

test("in chromium: a refused comment whose passage's dialog holds other typed words waits in a note there, and Bring it back waits for an empty box", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await refusedBesideTypedWords(page, send, OTHER);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value, p.readOnly], ["create", "p95 latency", OTHER, false],
      "the words typed in the passage's dialog stay: a refusal never overwrites what the person typed");
    assert.deepEqual(await heldNotes(page), [{ lead: NOT_SAVED, words: FIRST, back: "disabled", title: WAITS, dismiss: true, why: null, whyShown: false }],
      "the refused words wait in a note in that dialog, quoted whole, and Bring it back waits while the box holds words, saying why in its title");
    await page.fill("#cmt-pop .cmt-input", "");
    assert.equal((await heldNotes(page))[0]?.back, "enabled", "Bring it back is live once the box is empty");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const back = await pop(page);
    assert.deepEqual([back.value, back.name, back.readOnly, back.send], [FIRST, "cache-question", false, "enabled"],
      "Bring it back puts the refused words and their typed name in the box, ready to send again");
    assert.deepEqual(await heldNotes(page), [], "and the note goes");
  });
});

test("in chromium: a refused comment's note is dismissed with its words", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await refusedBesideTypedWords(page, send, OTHER);
    assert.equal((await heldNotes(page)).length, 1, "the precondition: the refused comment waits in a note");
    await page.click('#cmt-pop [data-act="cmtheldx"]');
    assert.deepEqual(await heldNotes(page), [], "the dismiss drops the note");
    assert.equal((await pop(page)).value, OTHER, "and leaves the typed words as they were");
    await commentOn(page, U2, "p95 latency");
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], [OTHER, []], "a dismissed note does not come back when the passage's dialog opens again");
  });
});

test("in chromium: on a touch screen, a waiting Bring it back says why in a line under its note", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    assert.equal(await page.evaluate(() => matchMedia("(pointer:coarse)").matches), true, "the precondition: a coarse pointer");
    await refusedBesideTypedWords(page, send, OTHER);
    const notes = await heldNotes(page);
    assert.deepEqual([notes.length, notes[0]?.back, notes[0]?.why, notes[0]?.whyShown], [1, "disabled", WAITS + ".", true],
      "a title never reaches a touch pointer, so the reason stands as a line under the note while the box holds words");
    await page.fill("#cmt-pop .cmt-input", "");
    const clear = await heldNotes(page);
    assert.deepEqual([clear[0]?.back, clear[0]?.whyShown], ["enabled", false], "and the line goes once Bring it back is live");
    await page.fill("#cmt-pop .cmt-name", "fresh-name");                 // the box empty, another name typed
    const named = await heldNotes(page);
    assert.deepEqual([named[0]?.back, named[0]?.why, named[0]?.whyShown], ["disabled", NAME_WAITS + ".", true],
      "with the box empty, a name typed there makes Bring it back wait again, and the line names what to clear: the typed name");
  }, { hasTouch: true });
});

test("in chromium: a refused comment's words come into an empty dialog open on its passage", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await commentOn(page, U2, "p95 latency");                            // the sending dialog closed; the same passage again
    assert.equal((await pop(page)).value, "", "the precondition: the passage's new dialog opens empty (the send spent its draft)");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), [[NOT_YET, FIRST, "none", false]],
      "the precondition: the first comment waits in the passage's note, not saved yet, with nothing to press while it is out");
    await refuse(send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value, p.name, p.send], ["create", "p95 latency", FIRST, "cache-question", "enabled"],
      "the refused words and their typed name come into the passage's empty box, as a refusal shows in the comment's own dialog");
    assert.deepEqual(await heldNotes(page), [], "and the note goes: its words moved into the empty box, and nothing typed was there to keep");
  });
});

test("in chromium: a refused comment with no dialog open waits in the note, shown on any passage of its message, and a toast says where", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await pressOutside(page);                                            // the dialog closed while the create is out
    await refuse(send, first);
    assert.ok((await toasts(page)).includes(TOAST_P95), "the toast names the passage and says where its words are: nothing on screen shows them");
    await commentOn(page, U2, "ten percent");
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], ["", [[NOT_SAVED, FIRST, "none"]]],
      "a dialog on another passage of the message opens empty and shows the words in its note, naming their passage, with no Bring it back: they never land on another passage");
    await commentOn(page, U2, P95);
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], ["", [[NOT_SAVED, FIRST, "enabled"]]],
      "their own passage's dialog opens empty too, the words in its note with Bring it back live: they went to the note, never into the passage's draft");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "cache-question"], "and Bring it back puts them in the box with their typed name");
  });
});

test("in chromium: a refused comment with no dialog open, whose passage holds other unsent words, waits in a note there", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await commentOn(page, U2, "p95 latency");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(OTHER);
    await pressOutside(page);                                            // unsent words left in the passage's draft
    await refuse(send, first);
    assert.ok((await toasts(page)).includes(TOAST_P95), "the toast names the passage and says where the words wait");
    await commentOn(page, U2, "p95 latency");
    assert.equal((await pop(page)).value, OTHER, "the unsent words are kept");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.words, n.back]), [[FIRST, "disabled"]], "and the refused words wait in a note beside them");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");                                  // the kept words sent
    assert.deepEqual([(await pop(page)).send, await heldNotes(page)], ["disabled busy", []], "a sent dialog shows no note: its box is out with its own create");
    await commentOn(page, U2, "p95 latency");                            // the kept words' dialog closed while they are out
    assert.deepEqual((await heldNotes(page)).map((n) => [n.words, n.back]), [[FIRST, "enabled"], [OTHER, "none"]],
      "the refused words wait for the passage's next dialog, whose box is empty, so Bring it back is live; the kept words, still being sent, wait beside them with none");
  });
});

test("in chromium: a refused comment's typed name, brought back into its passage's box, outlives the next comments frame", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await pressOutside(page);
    await refuse(send, first);
    await commentOn(page, U2, P95);
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const back = await pop(page);
    assert.deepEqual([back.value, back.name], [FIRST, "cache-question"], "the precondition: Bring it back put the words and typed name in the box");
    await pressOutside(page);                                            // left unsent: both in the passage's drafts
    await send({ type: "comments", id: SID, threads: [T_OLD] });         // any later frame for the session prunes stale drafts
    await commentOn(page, U2, P95);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "cache-question"],
      "the comment comes back with its typed name as well as its words, after a comments frame as before one: the frame keeps typed-name drafts");
  });
});

// ── no words are lost (the user, 2026-09-24): where two sets of words compete for one passage's box, the ones not
// placed in the box wait in that passage's note; and a comment still being sent waits there too, so it never posts
// twice (the user, 2026-09-25) ─────────────────────────────────────────────────────────────────────────────────────

test("in chromium: a sent comment's dialog closed before any answer puts its words in its passage's note, not saved yet, and its working mark stays", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await firstCreate(page, "cache-question");
    await send(SESSION);                                                 // the kernel's next frame for the session, and no answer yet
    const during = await pop(page);
    assert.deepEqual([during.value, during.readOnly, during.send], [FIRST, true, "disabled busy"],
      "the precondition: with no answer naming the comment, its dialog waits busy while open");
    await pressOutside(page);
    await commentOn(page, U2, "p95 latency");
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, p.readOnly], ["", p.prefill, false],
      "closing a sent dialog before its answer never hands its words back to the passage's box, where sending them again would post the comment twice: a new comment there opens empty");
    assert.deepEqual(await heldNotes(page), [{ lead: NOT_YET, words: FIRST, back: "none", title: "", dismiss: false, why: null, whyShown: false }],
      "its words wait in the passage's note, which says the comment is not saved yet and quotes it, with nothing to press while it is out");
    await send({ type: "comments", id: SID, threads: [T_OLD] });
    assert.deepEqual(await workingMarks(page), ["p95 latency"], "and its working mark stays until an answer or a reload: its hold stands");
  });
});

test("in chromium: a comment whose dialog closed before its answer leaves its passage's note when it lands, and is not posted again", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await pressOutside(page);                                            // its words go to the passage's note
    await commentOn(page, U2, "p95 latency");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words]), [[NOT_YET, FIRST]], "the precondition: the comment waits in the note of the dialog open on its passage");
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.name, await heldNotes(page)], ["create", "", p.prefill, []],
      "the landed comment's note goes from the dialog open on its passage, whose box stays empty under the suggested name");
    // those checks, and the reopen's below, are what keep it from being posted again: its words are in no box and no
    // note once it lands. An Enter in the empty box would post nothing whatever the code did, so none is asserted.
    await commentOn(page, U2, "p95 latency");
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", []], "nor does its note come back");
  });
});

test("in chromium: a sent dialog closed while an earlier refused comment waits in the note puts its words beside it, until they land", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const [first, second] = await secondOnSamePassage(page);
    await refuse(send, first);                                           // no unsent dialog of the passage open: the first's words stay in the note
    await pressOutside(page);                                            // the second's dialog closed before its answer
    await commentOn(page, U2, P95);
    assert.equal((await pop(page)).value, "", "the passage's box opens empty");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]),
      [[NOT_SAVED, FIRST, "enabled"], [NOT_YET, SECOND, "none"]],
      "the second comment's words wait in the note beside the first's, not over them, and the note says it has no answer yet");
    await send({ type: "comments", id: SID, threads: [T_OLD, { ...T_CACHE, exact: P95 }] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => n.words)], ["", [FIRST]], "when the second comment lands its note goes, and the first's stays");
  });
});

test("in chromium: a comment refused in its own dialog keeps the passage's other waiting words, in a note", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const [first, second] = await secondOnSamePassage(page, "cache-question");
    await refuse(send, first);
    assert.ok((await toasts(page)).includes(TOAST_P95),
      "the first comment's refusal, with only the second comment's sent dialog open on the passage, goes to the note, and the toast says so");
    assert.deepEqual([(await pop(page)).value, (await pop(page)).send], [SECOND, "disabled busy"], "the second comment's dialog waits on its own answer");
    await refuse(send, second);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, p.readOnly, p.send], [SECOND, p.prefill, false, "enabled"],
      "the second comment's own dialog is handed back with its words, under the suggested name it was sent with");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]),
      [[NOT_SAVED, FIRST, "disabled"]],
      "the first comment's words wait in the note beside the second's own dialog, handed back with its words: nothing overwrites them");
    await pressOutside(page);
    await commentOn(page, U2, "p95 latency");
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => n.words)], [SECOND, [FIRST]], "both are still there when the passage's dialog opens again");
    await page.fill("#cmt-pop .cmt-input", "");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const again = await pop(page);
    assert.deepEqual([again.value, again.name], [FIRST, "cache-question"], "and the first comment's typed name went into the note with its words");
  });
});

test("in chromium: a comment given up after its retries, in its own dialog, keeps the passage's other waiting words, in a note", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const [first, second] = await secondOnSamePassage(page);
    await refuse(send, first);
    await lagNack(send, second);
    for (let i = 0; i < 14; i++) {                                       // past the retry bound: the page gives the create up
      for (const cid of await repostsOnNextFrame(page, send)) await lagNack(send, cid);   // the kernel answers each re-post: still parked
    }
    const p = await pop(page);
    assert.deepEqual([p.value, p.readOnly, p.send], [SECOND, false, "enabled"], "the given-up comment's dialog is handed back with its words");
    assert.deepEqual((await heldNotes(page)).map((n) => n.words), [FIRST], "and the first comment's words wait in the note");
  });
});

test("in chromium: a comment the relay could not deliver waits busy, and is posted again once the relay's return shows the echo, at its connect push and on the next session frame", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    // what federation.ts dispatches on the page when the create's host has no open relay socket
    // (federation-send-queue.test.ts pins it): its warn, then a transient refusal naming the create, their texts
    // evaluated from dropWarn's own source
    const drop = federationDropTexts("TESTHOST2");
    await send({ type: "warn", text: drop.warn });
    await send({ type: "commentCreateFailed", id: REMOTE_SID, uuid: U2, transient: true, text: drop.refusal, createId: first, relayDrop: true });
    const p = await pop(page);
    assert.deepEqual([p.value, p.readOnly, p.send], [FIRST, true, "disabled busy"], "the dialog waits on its create");
    assert.deepEqual(await workingMarks(page), ["p95 latency"], "with its working mark");
    const before = (await creates(page)).length;
    await relayUp(page, "TESTHOST2");                                    // the host's relay opens again
    assert.equal((await creates(page)).length, before, "the relay's open posts nothing: its connect push has not shown that host's build yet");
    await connectPush(page, "TESTHOST2", true);
    assert.deepEqual((await creates(page)).slice(before).map((c) => c.createId), [first], "its connect push, carrying the echo, posts the create again");
    await send(REMOTE_SESSION);                                          // the host's next session frame
    assert.deepEqual((await creates(page)).slice(before).map((c) => c.createId), [first, first],
      "and the host's next session frame posts it again too, as the frame-keyed retry federation's refusal armed: the same gesture, which the kernel's repeat memo answers with the one thread");
  }, {}, "relayed");
});

test("in chromium: an acknowledgment with an empty create id answers another page's comment and settles nothing here", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    // a current kernel answers a create that carried no id (an older page's) with createId "", and the pusher acks
    // every chat client
    const other = { ...T_FIRST, tid: "t-0003", name: "api-comment-3", exact: "cache change", msgs: [{ who: "you", text: "An older page's note.", t: 1757145800 }] };
    await send({ type: "comments", id: SID, threads: [T_OLD, other] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: "" });
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.send], ["create", FIRST, "disabled busy"],
      "an empty create id names no echo-mode comment of this page's, which stamps every one: the answer goes to main's handling, which holds none of them, so its own dialog still waits for its own create");
    await lagNack(send, first);
    assert.deepEqual(await repostsOnNextFrame(page, send), [first], "its hold stands");
  });
});

test("in chromium: a passage longer than the comments frame's cut has its working mark replaced when its thread lands", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const U5 = "aaaaaaaa-0000-0000-0000-000000000005", U6 = "aaaaaaaa-0000-0000-0000-000000000006";
    const P600 = "Long passage " + "x".repeat(582) + " end.", P2100 = "Long passage " + "y".repeat(2082) + " end.";
    assert.deepEqual([P600.length, P2100.length], [600, 2100], "the precondition: passages of 600 and 2100 characters");
    await send({ ...SESSION, events: [...EVENTS, { kind: "assistant", md: P600, uuid: U5 }, { kind: "assistant", md: P2100, uuid: U6 }] });
    await page.waitForSelector('.turn[data-uuid="' + U6 + '"]', { timeout: 10000 });
    const landed: any[] = [T_OLD];
    for (const [uuid, passage, tid] of [[U5, P600, "t-0005"], [U6, P2100, "t-0006"]]) {
      await commentOn(page, uuid, passage);
      await page.focus("#cmt-pop .cmt-input");
      await page.keyboard.type(FIRST);
      await page.keyboard.press("Enter");
      const cid = (await creates(page)).slice(-1)[0].createId;
      // the thread's row keeps the passage cut to 2000 characters, and the comments frame sends it cut to 500
      landed.push({ ...T_FIRST, tid, anchorUuid: uuid, exact: passage.slice(0, 2000).slice(0, 500) });
      await send({ type: "comments", id: SID, threads: landed });
      await send({ type: "commentCreated", id: SID, tid, uuid, createId: cid });
      assert.deepEqual(await workingMarks(page), [],
        "a " + passage.length + "-character passage's working mark is replaced by its thread, compared on the frame's own cut of the passage");
    }
  });
});

test("in chromium: a refused comment's own dialog comes back with its typed name, and its working mark goes at once", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await refuse(send, first);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, p.readOnly, p.send], [FIRST, "cache-question", false, "enabled"],
      "a refusal hands the comment's own dialog back with its typed name as well as its words");
    assert.deepEqual(await workingMarks(page), [], "and its working mark goes with the refusal, before any comments frame");
  });
});

test("in chromium: Bring it back waits while the dialog's name box holds another typed name, and brings the comment's own back once it is cleared", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await commentOn(page, U2, "p95 latency");
    await page.fill("#cmt-pop .cmt-name", "fresh-name");
    await typeFresh(page, OTHER);
    await refuse(send, first);
    await page.fill("#cmt-pop .cmt-input", "");
    const waiting = (await heldNotes(page))[0];
    assert.deepEqual([waiting?.back, waiting?.title, (await pop(page)).name], ["disabled", NAME_WAITS, "fresh-name"],
      "with the box empty, Bring it back still waits while the name box holds a name typed there, and says the typed name is what to clear: bringing the comment back would replace it, and a typed name is never dropped");
    await page.fill("#cmt-pop .cmt-name", "");
    assert.equal((await heldNotes(page))[0]?.back, "enabled", "it is live once the name typed there is cleared");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "cache-question"], "and brings the refused words back with their own typed name");
  });
});

test("in chromium: a refused comment's note shows in a dialog on any passage of its message, naming its passage, and on no other message", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await refusedBesideTypedWords(page, send, OTHER);
    assert.equal((await heldNotes(page)).length, 1, "the precondition: the note on its passage");
    await commentOn(page, U2, "cache change");
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", [{ lead: NOT_SAVED, words: FIRST, back: "none", title: "", dismiss: true, why: null, whyShown: false }]],
      "a dialog on another passage of the message opens empty and shows the note, naming the passage it belongs to, with a dismiss and no Bring it back");
    await commentOn(page, U4, "response cache");
    assert.deepEqual(await heldNotes(page), [], "no note on another message");
  });
});

test("in chromium: a sent dialog replaced by a thread or a new comment with no press outside it (a keyboard's activation) puts its words in the note too", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page, "cache-question");
    // Enter on a focused control fires its click with no press before it, so nothing closes the sent dialog first
    await page.evaluate(() => (document.querySelector('mark.cmt-hl[data-tid="t-0001"]') as HTMLElement).click());
    let p = await pop(page);
    assert.deepEqual([p.mode, p.tid], ["thread", "t-0001"], "the precondition: a thread replaced the sent dialog");
    await commentOn(page, U2, "p95 latency");
    p = await pop(page);
    assert.deepEqual([p.value, (await heldNotes(page)).map((n) => [n.lead, n.words])], ["", [[NOT_YET, FIRST]]],
      "a thread opened over a sent dialog puts that comment's words in its passage's note");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(SECOND);
    await page.keyboard.press("Enter");                                  // another comment there, left unanswered
    assert.equal((await creates(page)).length, 2, "the precondition: a second comment sent");
    await commentFromKeyboard(page, U4, "response cache");              // the selection's menu from the keyboard, its Comment picked
    p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value], ["create", "response cache", ""], "the precondition: a new comment's dialog replaced the sent one");
    await commentOn(page, U2, "p95 latency");
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words])], ["", [[NOT_YET, FIRST], [NOT_YET, SECOND]]],
      "a new comment opened over a sent dialog puts that comment's words in its passage's note too");
  });
});

test("in chromium: a refused comment whose passage's open dialog holds another typed name waits in the note, its own name with it", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await commentOn(page, U2, "p95 latency");
    await page.fill("#cmt-pop .cmt-name", "other-name");                 // a name typed there, the box still empty
    await refuse(send, first);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], ["", "other-name"],
      "the name typed there stays, and the refused words stay out of the empty box, where they would come without their own typed name");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_SAVED, FIRST, "disabled"]],
      "they wait in the note, now refused, and Bring it back waits while the other name is there");
    await page.fill("#cmt-pop .cmt-name", "");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const back = await pop(page);
    assert.deepEqual([back.value, back.name], [FIRST, "cache-question"], "and Bring it back restores the words and their typed name once that name is cleared");
  });
});

test("in chromium: a refused comment whose words already wait in the note is not placed twice", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const [first, second] = await secondOnSamePassage(page);
    await refuse(send, first);                                           // no unsent dialog of the passage open: the first's words stay in the note
    await pressOutside(page);                                            // the second's go to the note too
    await refuse(send, second);
    assert.ok((await toasts(page)).includes(TOAST_P95), "the toast says where the refused words wait");
    await commentOn(page, U2, P95);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_SAVED, FIRST, "enabled"], [NOT_SAVED, SECOND, "enabled"]],
      "one note for each refused comment, each now saying it was not saved, with Bring it back: a refusal turns its comment's entry, and adds none");
  });
});

test("in chromium: a comment still being sent offers no Bring it back from its note, even with the box empty, and is posted once", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const [first, second] = await secondOnSamePassage(page);
    await refuse(send, first);                                           // the first's words, refused, wait in the note
    await pressOutside(page);                                            // the second's dialog closed while it is out: its words go to the note
    await commentOn(page, U2, P95);
    assert.equal((await pop(page)).value, "", "the precondition: the passage's box is empty");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), [[NOT_SAVED, FIRST, "enabled", true], [NOT_YET, SECOND, "none", false]],
      "with the box empty, the note of a comment still being sent has no Bring it back, where a refused one's is live: brought back and sent again, a comment still out would post twice");
    await send({ type: "comments", id: SID, threads: [T_OLD, { ...T_CACHE, exact: P95 }] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });
    assert.deepEqual((await heldNotes(page)).map((n) => n.words), [FIRST], "once it lands its note goes");
    // the note's lack of a Bring it back while the comment is out, and the note's going once it lands, are what keep it
    // posted once: its words never reach a box. An Enter in the emptied box would post nothing whatever the code did,
    // so none is asserted.
  });
});

test("in chromium: with the real federation bundle, a relay's connect push carrying the marker posts again the comment a drop left held, and one without it hands that comment back with no post", { timeout: 180000 }, async (t) => {
  for (const marked of [true, false]) await openChat(t, async (page, send) => {
    await commentOn(page, U2, "p95 latency");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(FIRST);
    await page.evaluate(() => {
      const w = window as any; w.__answers = [];
      window.addEventListener("message", (e: MessageEvent) => { const d = e.data;
        if (d && (d.type === "warn" || d.type === "commentCreateFailed")) w.__answers.push(d.type + (d.transient ? " transient" : "")); });
    });
    await page.keyboard.press("Enter");
    const sent = await creates(page);
    assert.equal(sent.length, 1, "the precondition: the create was posted");
    assert.deepEqual(await page.evaluate(() => (window as any).__answers), ["warn", "commentCreateFailed transient"],
      "the precondition: federation dropped the create (its host has no open relay socket) and answered it inside the send, with a warn and a transient refusal");
    const p = await pop(page);
    assert.deepEqual([p.value, p.readOnly, p.send], [FIRST, true, "disabled busy"],
      "the dialog waits busy on its create: the send stored its hold and stamped the dialog before posting, so the warn's rebuild drew the dialog sent");
    assert.deepEqual(await workingMarks(page), ["p95 latency"], "with its working mark");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");
    assert.equal((await creates(page)).length, 1, "and Enter there posts nothing more");
    // the host's relay opens again, and its kernel's first strip on it comes through federation's inbound door, which
    // hands the page a merged strip naming that host and carrying its marker when the strip did
    await relayUp(page, "TESTHOST2");
    assert.equal((await creates(page)).length, 1, "the relay's open posts nothing: its connect push has not come");
    await connectPush(page, "TESTHOST2", marked);
    const q = await pop(page);
    if (marked) {
      assert.deepEqual([(await creates(page)).map((c) => c.createId), q.readOnly, q.send], [[sent[0].createId, sent[0].createId], true, "disabled busy"],
        "a connect push carrying the marker, handed on by federation, posts the held create again as the same gesture, and its dialog waits on it");
    } else {
      assert.deepEqual([(await creates(page)).length, q.open, await workingMarks(page), (await toasts(page)).includes(HANDED_BACK_TOAST_P95)], [1, false, [], true],
        "one without it posts nothing and hands the comment back: its dialog closed, its working mark gone, a toast saying where its words wait");
      await send(REMOTE_SESSION);
      await commentOn(page, U2, P95);
      assert.deepEqual([(await creates(page)).length, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], [1, [[HANDED_BACK_P95, FIRST, "enabled"]]],
        "no session frame posts it, and a dialog on its passage shows its words in the note, with Bring it back");
    }
  }, {}, true);
});

/** A comment opened from the selection's menu opened by the keyboard (its contextmenu event, with no press before it),
 *  so nothing closes the dialog open before it. */
async function commentFromKeyboard(page: any, uuid: string, needle: string): Promise<void> {
  await selectIn(page, uuid, needle);
  await page.evaluate(() => {
    const r = getSelection()!.getRangeAt(0).getBoundingClientRect();
    document.getElementById("content")!.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: r.left + 2, clientY: r.top + 2 }));
  });
  await page.waitForSelector(".ctx-menu .ctx-item", { timeout: 5000 });
  await page.evaluate(() => (Array.from(document.querySelectorAll(".ctx-menu .ctx-item")) as HTMLElement[])
    .find((i) => i.querySelector(".ctx-item-label")?.textContent === "Comment")!.click());
}

test("in chromium: a comment opened from the keyboard over a sent dialog on the same message gets its own dialog, and Enter there never posts the sent words", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page, "cache-question");
    await commentFromKeyboard(page, U2, "cache change");                 // another passage of the same message
    let p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value, p.readOnly, p.send], ["create", "cache change", "", false, "enabled"],
      "a dialog opened on another passage of the message over a sent dialog is built for its own passage: its quote, an empty box, a live Comment");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");
    assert.equal((await creates(page)).length, 1, "and Enter there posts nothing: the sent words never land on another passage");
    await page.keyboard.type(SECOND);
    await page.keyboard.press("Enter");
    assert.deepEqual((await creates(page)).map((c) => [c.exact, c.text]), [["p95 latency", FIRST], ["cache change", SECOND]], "the precondition: its own comment sent");
    await commentFromKeyboard(page, U2, "cache change");                 // the same passage, over its own sent dialog
    p = await pop(page);
    assert.deepEqual([p.quote, p.value, p.readOnly, p.send, (await heldNotes(page)).map((n) => [n.lead, n.words])],
      ["cache change", "", false, "enabled", [[NOT_YET, FIRST], [notYet("cache change"), SECOND]]],
      "a dialog opened on the same passage over its sent dialog is built afresh too, each comment still out waiting in the note under its own passage");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");
    assert.equal((await creates(page)).length, 2, "and Enter there posts nothing: the comment still out is not posted twice");
    await commentOn(page, U2, P95);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words]), [[NOT_YET, FIRST], [notYet("cache change"), SECOND]],
      "on the first comment's passage the same note shows, each comment under its own passage");
  });
});

test("in chromium: an attachment's path never goes into a sent dialog's box or its draft, and lands in the chat's composer", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await send({ type: "droppedPath", path: "/tmp/romp-drop/shot.png" });   // a file dropped or picked while the dialog is sent
    const p = await pop(page);
    assert.deepEqual([p.value, p.readOnly], [FIRST, true], "the sent dialog's box keeps its words: the path does not go into it");
    assert.equal(await page.evaluate(() => document.querySelectorAll('#composer-files [title^="/tmp/romp-drop/shot.png"]').length), 1,
      "the file is attached to the chat's composer instead, where it shows");
    await ackFirst(page, send, first);
    await commentOn(page, U2, "p95 latency");
    assert.equal((await pop(page)).value, "", "and once the comment lands its passage opens empty: the path never reached the passage's draft");
  });
});

test("in chromium: a refused comment whose passage holds another typed name, with no dialog open, waits in the note with its own name", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await commentOn(page, U2, "p95 latency");
    await page.fill("#cmt-pop .cmt-name", "other-name");                 // a name typed on the passage, no words
    await pressOutside(page);                                            // left in the passage's name draft
    await refuse(send, first);
    assert.ok((await toasts(page)).includes(TOAST_P95), "the toast says the words wait in the note");
    await commentOn(page, U2, "p95 latency");
    let p = await pop(page);
    assert.deepEqual([p.value, p.name, (await heldNotes(page)).map((n) => [n.words, n.back])], ["", "other-name", [[FIRST, "disabled"]]],
      "the other name is kept, and the refused comment waits in the note");
    await page.fill("#cmt-pop .cmt-name", "");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "cache-question"], "and Bring it back restores its words and its typed name");
  });
});

test("in chromium: a refused comment with no typed name comes back beside a name typed in the dialog, which stays", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);                               // under the suggested name
    await commentOn(page, U2, "p95 latency");
    await page.fill("#cmt-pop .cmt-name", "fresh-name");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(OTHER);
    await refuse(send, first);
    await page.fill("#cmt-pop .cmt-input", "");
    assert.equal((await heldNotes(page))[0]?.back, "enabled", "with the box empty Bring it back is live: the comment has no typed name to replace the one typed there");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "fresh-name"], "the refused words come back, and the name typed in this dialog stays");
  });
});

test("in chromium: a comment opened from the keyboard over an unsent dialog on another passage of the same message gets its own dialog, and the words typed there stay on their passage", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await commentOn(page, U2, "p95 latency");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(OTHER);                                     // typed there, not sent
    await commentFromKeyboard(page, U2, "cache change");                 // another passage of the same message
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value], ["create", "cache change", ""],
      "the dialog is built for its own passage: its quote and an empty box, never the other passage's words");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");
    assert.equal((await creates(page)).length, 0, "and Enter there posts nothing: words typed for one passage never land on another");
    await commentOn(page, U2, "p95 latency");
    assert.equal((await pop(page)).value, OTHER, "the words typed on the first passage are still its own");
  });
});

// ── a comment whose answer never comes (the kernel restarted, or the socket dropped, before answering): the connection
// that comes back posts it again at its connect push when that push carries the marker, and the answer to that post
// settles it; meanwhile its words can be copied out of the note. Nothing is posted again before a connection's connect
// push, nor on a connection whose connect push lacks the marker, nor from a strip handed on from a dropped socket ─────

/** The create frames the page has posted so far, as [createId, words, typed name]. */
const createFrames = (page: any): Promise<[string, string, string][]> => page.evaluate(() =>
  (window as any).__posts.filter((m: any) => m.type === "commentCreate").map((m: any) => [m.createId, m.text, m.name]));
/** The first comment sent under a typed name, then its dialog closed with no answer, and the passage opened again: its
 *  words wait in the passage's note, not saved yet. Returns its create id. */
async function unansweredInNote(page: any): Promise<string> {
  const first = await firstCreate(page, "cache-question");
  await commentOn(page, U2, "p95 latency");                            // the sending dialog closed; the same passage again
  assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_YET, FIRST, "none"]],
    "the precondition: closed before any answer, the comment waits in its passage's note, not saved yet");
  return first;
}
/** A mouse drag across the words of the open dialog's note, from before their first character to past their last: what
 *  the page then has selected, the words' computed user-select, and whether the dialog moved. */
async function dragAcrossHeldWords(page: any): Promise<{ selected: string; userSelect: string; moved: boolean }> {
  const r = await page.evaluate(() => {
    const w = document.querySelector("#cmt-pop .cmt-held-words") as HTMLElement | null;
    const p = document.getElementById("cmt-pop");
    if (!w || !p) return null;
    const b = w.getBoundingClientRect();
    return { x: b.left, y: b.top, w: b.width, h: b.height, us: getComputedStyle(w).userSelect, left: p.offsetLeft, top: p.offsetTop };
  });
  assert.ok(r, "the precondition: the note's words are on screen");
  await page.mouse.move(r.x + 1, r.y + r.h / 2);
  await page.mouse.down();
  await page.mouse.move(r.x + r.w - 1, r.y + r.h / 2, { steps: 8 });
  await page.mouse.up();
  const after = await page.evaluate(() => { const p = document.getElementById("cmt-pop"); return { sel: String(getSelection() || ""), left: p ? p.offsetLeft : -1, top: p ? p.offsetTop : -1 }; });
  return { selected: after.sel, userSelect: r.us, moved: after.left !== r.left || after.top !== r.top };
}

test("in chromium: a comment whose create was never answered is posted again once, by the connect push of the page's connection when it comes back carrying the echo, and its acknowledgment settles its note", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await send(SESSION);                                                 // a frame for the session, and no answer
    assert.deepEqual([(await pop(page)).send, (await creates(page)).length], ["disabled busy", 1],
      "the precondition: no answer names the comment, so its dialog waits, and no session frame re-posts it (no transient refusal armed the retry)");
    await commentOn(page, U2, P95);                                      // the sending dialog closed; the same passage again
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_YET, FIRST, "none"]],
      "the precondition: its words wait in the passage's note, not saved yet");
    // the socket dropped before any answer, and the create never landed: the page's socket opens again (the shim's
    // romp:wsup and its socket-flip frame, at the new socket's open, before any of its frames)
    await wsup(page);
    await send(SESSION);                                                 // a frame of the new connection before its strip (the shim's FIFO keeps
    //                                                                      only the latest strip, at the end)
    // and a strip federation re-serves from its stores (a view-order write, a host's drop), which is no kernel's push
    await send({ type: "tabOrder", order: [SID], tabs: [{ id: SID, name: "api" }], live: [SID], skeleton: [], reemit: true });
    assert.deepEqual([(await creates(page)).length, await markTids(page)], [1, ["pending:" + first]],
      "the socket's open posts nothing, nor a frame before its connect push, and a re-served strip is read as no connection's push: "
      + "nothing has shown this kernel's build yet, so the comment stays out in echo mode, its working mark keyed by its id");
    await connectPush(page, "", true);                                   // the kernel's connect push, carrying the echo's marker, and no answer
    assert.deepEqual(await createFrames(page), [[first, FIRST, "cache-question"], [first, FIRST, "cache-question"]],
      "the connect push posts the held create again as the same gesture, its id, words and typed name, and nothing else: a create that never landed is made now, and answered");
    await connectPush(page, "", true);                                   // a later strip on the same connection
    await send(SESSION);
    await send({ type: "comments", id: SID, threads: [T_OLD] });
    assert.equal((await creates(page)).length, 2, "once per connection: a later strip, or a session frame, posts it no more (no transient refusal armed its retry)");
    await ackFirst(page, send, first);                                   // the answer to the re-post
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, await heldNotes(page), await workingMarks(page)], ["", p.prefill, [], []],
      "the answer to the re-post settles the comment: its note goes, its working mark goes, and the passage's box stays empty");
  });
});

test("in chromium: a relay coming back posts again only its own host's comments still held, at its connect push, and the page's own connection none of them", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(FIRST);
    await page.keyboard.press("Enter");                                  // delivered on the host's relay, whose drop lost the answer
    const sent = await creates(page);
    assert.deepEqual([sent.map((c) => c.exact), (await pop(page)).readOnly], [[P95], true],
      "the precondition: the create was posted once, from an echo-mode dialog, since the host's connect push and caps frame announced the echo: "
      + "its sent box is read-only, which a main-mode dialog's never is (the frame alone cannot tell, since main's frame carries a createId too)");
    await pressOutside(page);
    await reconnect(page, true);
    assert.equal((await creates(page)).length, 1, "the page's own socket carries the local kernel's creates, never a remote host's: nothing re-posted at its connect push");
    await relayBack(page, "TESTHOST3", true);
    assert.equal((await creates(page)).length, 1, "another host's relay coming back posts nothing either");
    await relayUp(page, "TESTHOST2");
    assert.equal((await creates(page)).length, 1, "nor does its own host's relay's open, before that connection's connect push");
    await connectPush(page, "TESTHOST2", true);
    assert.deepEqual((await creates(page)).map((c) => c.createId), [sent[0].createId, sent[0].createId],
      "its own host's connect push, carrying the echo, posts it again, as the same gesture");
    await connectPush(page, "TESTHOST2", true);                          // a later strip on the same connection
    assert.equal((await creates(page)).length, 2, "once per connection: a later strip of that host's posts it no more");
  }, {}, "relayed");
});

test("in chromium: frames still draining from the page's dropped socket post nothing again, and the next connection's connect push does", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await lagNack(send, first);                                          // parked: its frame-keyed retry is armed
    await socketDown(page);                                              // the page's own socket drops (the shim's netState down, romp:wsdown)
    // frames the dropped socket delivered before it closed, still draining from the shim's queue: a session frame, and
    // a strip (the shim keeps only a socket's latest strip in its queue, and a dropped socket's comes before the next
    // socket's flip frame)
    await send(SESSION);
    await connectPush(page, "", true);
    assert.equal((await creates(page)).length, 1,
      "nothing is posted again while the socket is down: a post would wait in the shim's queue and reach the next socket's kernel before "
      + "that connection's connect push has said whether it echoes");
    await socketUp(page);                                                // the next socket opens: its flip frame, in frame order
    assert.equal((await creates(page)).length, 1, "nor at the open");
    // that socket drops too before its connect push was read, and its strip, which had arrived, is delivered after the
    // drop: it is the dropped socket's, and is not read either
    await socketDown(page);
    await connectPush(page, "", true);
    await send(SESSION);
    assert.equal((await creates(page)).length, 1, "a strip delivered once its socket is down is that socket's: nothing is posted again");
    await socketUp(page);
    await connectPush(page, "", true);
    assert.deepEqual((await creates(page)).map((c) => c.createId), [first, first], "the next connection's connect push, carrying the marker, posts it again, once");
    await send(SESSION);
    assert.deepEqual((await creates(page)).map((c) => c.createId), [first, first, first], "and its session frames run the retry its lag refusal armed");
  });
  // a page whose first dial failed: its first socket's strip is read all the same (no strip was read before the drop,
  // and a first open fires no romp:wsup and brings no socket-flip frame, so nothing marks the connection down)
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await lagNack(send, first);
    await send(SESSION);
    assert.deepEqual((await creates(page)).map((c) => c.createId), [first, first], "the first socket's connect push was read: the retry posts the comment again");
  }, {}, false, { firstDialFailed: true });
});

test("in chromium: a mixed build is read per connection: the page's own socket's connect push and a relay's each decide for their own host's comments, the local kernel marked and the remote one not, and the reverse: the marked host's comment is posted again, and the other's is handed back as the fail-safe hands a comment back", { timeout: 360000 }, async (t) => {
  for (const [localMarked, remoteMarked] of [[true, false], [false, true]]) {
    await openChat(t, async (page, send) => {
      const why = localMarked ? "the local kernel marked, the remote one not" : "the remote host marked, the local kernel not";
      const marked: Host = localMarked ? HOSTS[0] : HOSTS[1], older: Host = localMarked ? HOSTS[1] : HOSTS[0];
      const tabOf = (h: Host) => page.click('#tabs .tab[data-id="' + h.sid + '"]');
      await send(SESSION);                                               // this kernel's session, in a tab beside the other host's
      // echo mode on both hosts (their connect pushes and caps announced the echo): the marked host's comment sent and its
      // dialog closed, then the other host's, under a typed name, its sent dialog left open
      await tabOf(marked);
      await sendOn(page, P95, SECOND);
      await pressOutside(page);
      const onMarked = (await creates(page))[0].createId;
      await tabOf(older);
      await sendOn(page, P95, FIRST, "cache-question");
      const onOlder = (await creates(page))[1].createId;
      assert.equal((await pop(page)).send, "disabled busy", "the precondition: the other host's sent dialog is open");
      await lagOf(send, marked, onMarked); await lagOf(send, older, onOlder);   // each kernel parks its comment: both retries armed
      // both connections drop and come back, each on its own kernel: the page's own socket's connect push is read for the
      // local kernel's comments alone, and the relay's for that host's alone
      const from = await postCount(page);
      await reconnect(page, localMarked);
      await relayBack(page, "TESTHOST2", remoteMarked);
      assert.deepEqual([(await creates(page)).slice(2).map((c) => c.createId), (await pop(page)).open], [[onMarked], false],
        why + ": each connection posts again only its own host's comment, and only when its own connect push carries the marker; the "
        + "other host's sent dialog, open until then, closed at that host's hand-back");
      const tids = await markTids(page);
      assert.deepEqual([tids.includes("pending:" + onMarked), tids.includes("pending:" + onOlder), tids.includes("pending:" + U2)], [true, false, false],
        why + ": the marked host's comment keeps its echo-mode working mark, keyed by its id, and the other's went with its hand-back");
      // the marked kernel parks the re-post: its lag refusal arms the frame-keyed retry, which that host's next session frame
      // runs on its own connection's reading, never the other connection's
      await lagOf(send, marked, onMarked);
      const b = (await creates(page)).length;
      await send(marked.session);
      assert.deepEqual((await creates(page)).slice(b).map((c) => c.createId), [onMarked],
        why + ": the marked host's session frame posts its comment again, read on that host's own connection, whatever the other connection read");
      const early = await carrying(page, from, onOlder, FIRST);
      assert.deepEqual(early.hits.filter((m: any) => m.createId !== onMarked), [],
        why + ": nothing the page posted since both connections came back carries the other host's comment (every frame posted: " + JSON.stringify(early.all) + ")");
      // the marked host's comment lands: its frame, then its acknowledgment naming it, so its working mark goes
      await send({ type: "comments", id: marked.sid, threads: [T_OLD, { ...T_FIRST, tid: "t-0005", name: "api-comment-5", msgs: [{ who: "you", text: SECOND, t: 1757145800 }] }] });
      await send({ type: "commentCreated", id: marked.sid, tid: "t-0005", uuid: U2, createId: onMarked });
      assert.deepEqual(await markTids(page), [], why + ": the precondition: the marked host's comment landed, and no working mark is left");
      // the other host's comment was handed back as the fail-safe hands one back: its dialog closed, its working mark
      // gone, the toast; its session frames, another return of its connection without the echo, and a dialog on its
      // passage, main mode, whose note holds its words and typed name with Bring it back enabled, which brings them back
      // intact; and nothing the page posted from the moment both connections came back (the count `from` took) carries
      // it, the marked host's own posts of its comment, checked above, being the only creates in that window
      await tabOf(older);
      await handedBackAfter(page, send, older, onOlder, from, why, true, onMarked);
      await pressOutside(page);
      await tabOf(marked);
      await commentOn(page, U2, "cache change");
      assert.equal(await echoOf(page), "1", why + ": and the marked host's next dialog is echo mode, from its own connection's connect push");
    }, {}, "relayed");
  }
});

test("in chromium: a waiting comment's words can be selected to copy, in its note not saved yet and once refused", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await unansweredInNote(page);
    const out = await dragAcrossHeldWords(page);
    assert.deepEqual([out.selected.trim(), out.userSelect, out.moved], [FIRST, "text", false],
      "a drag across the words of a comment still out selects them, so they can be copied, and does not move the dialog: its whole-box drag leaves them alone");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(OTHER);                                     // words typed in the box: the refusal leaves the comment in the note
    await refuse(send, first);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words]), [[NOT_SAVED, FIRST]], "the precondition: refused, it waits beside the typed words");
    const refused = await dragAcrossHeldWords(page);
    assert.deepEqual([refused.selected.trim(), refused.userSelect, refused.moved], [FIRST, "text", false], "a refused comment's words select the same way");
  });
});

test("in chromium: a comment refused in its own dialog, in the same words as an earlier refused comment under another typed name, leaves that comment and its name in the note", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "name-one");
    await commentOn(page, U2, "p95 latency");                            // the sending dialog closed; the same passage again
    await page.fill("#cmt-pop .cmt-name", "name-two");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(FIRST);                                     // the same words, another typed name
    await page.keyboard.press("Enter");
    const second = (await creates(page))[1].createId;
    await refuse(send, first);                                           // the second's dialog is sent, so the first waits in the note
    assert.ok((await toasts(page)).includes(TOAST_P95), "the precondition: the first comment waits in the note");
    await refuse(send, second);                                          // the second's own dialog, the draft holding the same words
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, p.readOnly, p.send], [FIRST, "name-two", false, "enabled"],
      "the second comment's own dialog comes back with its words and its typed name");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words]), [[NOT_SAVED, FIRST]],
      "the first comment, in the same words under another name, waits in the note: its typed name is not overwritten");
    await page.fill("#cmt-pop .cmt-input", "");
    const waiting = (await heldNotes(page))[0];
    assert.deepEqual([waiting?.back, waiting?.title], ["disabled", NAME_WAITS], "with the box empty its Bring it back waits on the name typed there, and says so");
    await page.fill("#cmt-pop .cmt-name", "");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const back = await pop(page);
    assert.deepEqual([back.value, back.name], [FIRST, "name-one"], "and brings the first comment back under its own typed name");
  });
});

// ── a comment's words out of reach behind an exact selection (a reselection a character longer or shorter is another
// passage): the note shows on any passage of the message, and the working mark opens the comment's passage ───────────

test("in chromium: a comment's words show in the note of a dialog on any passage of its message, naming their passage, with Bring it back only on that passage", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await commentOn(page, U2, "cut p95 latency");                        // a little longer than the comment's passage
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], ["", [[NOT_YET, FIRST, "none"]]],
      "while the comment is out, a dialog on a longer selection of its message opens empty and shows it in the note, naming the passage it belongs to");
    await commentOn(page, U2, "p95 latenc");                             // a little shorter
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])], ["", [[NOT_YET, FIRST, "none"]]],
      "and so does one on a shorter selection");
    await pressOutside(page);
    await refuse(send, first);
    assert.ok((await toasts(page)).includes(TOAST_P95), "the refusal's toast says where the words are");
    await commentOn(page, U2, "p95 latency by");
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", [{ lead: NOT_SAVED, words: FIRST, back: "none", title: "", dismiss: true, why: null, whyShown: false }]],
      "refused, it shows on another selection of the message too, naming its passage, with a dismiss and no Bring it back: its words never land on another passage");
    const copied = await dragAcrossHeldWords(page);
    assert.equal(copied.selected.trim(), FIRST, "and its words can be selected there to copy");
    await commentOn(page, U4, "response cache");
    assert.deepEqual(await heldNotes(page), [], "a dialog on another message shows no note");
    await commentOn(page, U2, P95);                                      // the comment's own passage
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_SAVED, FIRST, "enabled"]],
      "on its own passage the note offers Bring it back, live with the box empty");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [FIRST, "cache-question"], "and brings the words and their typed name back into that passage's box");
  });
});

test("in chromium: the working mark of a comment still out opens a new comment on its passage, the comment waiting in the note, never a thread to reply to", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await firstCreate(page, "cache-question");
    await pressOutside(page);                                            // its dialog closed while it is out
    const clicked = await page.evaluate(() => {
      const m = (Array.from(document.querySelectorAll("mark.cmt-hl")) as HTMLElement[]).find((x) => (x.dataset.tid || "").startsWith("pending:"));
      m?.click();
      return !!m;
    });
    assert.ok(clicked, "the precondition: the comment's working mark is on screen");
    const p = await pop(page);
    assert.deepEqual([p.mode, p.quote, p.value, p.name, p.send], ["create", P95, "", p.prefill, "enabled"],
      "a click on the mark opens the create dialog on its passage, empty under the suggested name: the comment has no thread yet, and its placeholder is none the kernel knows");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_YET, FIRST, "none"]], "with the comment waiting in its note, not saved yet");
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(SECOND);
    await page.keyboard.press("Enter");
    const posted = await page.evaluate(() => (window as any).__posts.filter((m: any) => m.type === "commentReply" || m.type === "commentCreate")
      .map((m: any) => [m.type, m.type === "commentReply" ? m.tid : m.exact, m.text]));
    assert.deepEqual(posted, [["commentCreate", "p95 latency", FIRST], ["commentCreate", "p95 latency", SECOND]],
      "what is typed there goes out as a new comment on the passage: nothing is sent as a reply to the placeholder");
  });
});

// ── what the create dialog posts: its picks ride the create ─────────────────────────────────────────────────────────

test("in chromium: the create dialog's fast pick rides the comment's posted create", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);
    await page.click('#cmt-pop .cmt-meta-row .meta-btn:has(.meta-label:text-is("Slow"))');
    await page.click('.meta-menu .meta-item:text-is("Fast")');
    await page.waitForSelector('#cmt-pop .cmt-meta-row .meta-label:text-is("Fast")', { timeout: 5000 });
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.type(FIRST);
    await page.keyboard.press("Enter");
    const posted = await page.evaluate(() => (window as any).__posts.filter((m: any) => m.type === "commentCreate").map((m: any) => [m.exact, m.text, m.fast]));
    assert.deepEqual(posted, [[P95, FIRST, "on"]], "the pick made in the dialog goes out with the comment it creates");
  });
});

// ── a press on the note's buttons survives another comment's answer (ui/CLAUDE.md, the click-safe rule) ──────────────

/** A refused first comment in the note with Bring it back live, beside a second comment still out: the first sent on
 *  "p95 latency" under a typed name, the second on "cache change", both dialogs closed, the first refused, and the
 *  first's passage opened again with its box empty. Returns the second's create id. */
async function noteBesideAnother(page: any, send: (m: unknown) => Promise<void>): Promise<string> {
  const first = await firstCreate(page, "cache-question");
  const second = await secondCreate(page);
  await pressOutside(page);
  await refuse(send, first);
  await commentOn(page, U2, P95);
  assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]),
    [[NOT_SAVED, FIRST, "enabled", true], [notYet("cache change"), SECOND, "none", false]], "the precondition: the refused first in the note, the second still out beside it");
  return second;
}
/** Presses (mouse down, not up) on the open dialog's note button `act`, marking the node so the test can tell whether it
 *  is still the same button when the press ends. The pointer is put on the button as a click would put it (scrolled
 *  into view, the button the one hit there). */
async function pressNoteButton(page: any, act: string): Promise<void> {
  const sel = '#cmt-pop [data-act="' + act + '"]';
  await page.evaluate((sel: string) => { (document.querySelector(sel) as any).__pressed = true; }, sel);
  await page.hover(sel);
  await page.mouse.down();
}
const samePressed = (page: any, act: string): Promise<boolean> => page.evaluate((act: string) =>
  (document.querySelector('#cmt-pop [data-act="' + act + '"]') as any)?.__pressed === true, act);
/** The press's release, then a zero timer queued after the release's own (pressHold runs a held repaint a tick after it). */
async function releaseAndSettle(page: any): Promise<void> {
  await page.mouse.up();
  await page.evaluate(() => new Promise((r) => setTimeout(r, 0)));
}

test("in chromium: a press on a note's Bring it back lands though another comment's acknowledgment arrives during it, and the note's repaint follows the release", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const second = await noteBesideAnother(page, send);
    await pressNoteButton(page, "cmtheldback");
    await send({ type: "comments", id: SID, threads: [T_OLD, T_CACHE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });   // the second lands during the press
    const kept = await samePressed(page, "cmtheldback");
    await releaseAndSettle(page);
    const p = await pop(page);
    assert.deepEqual([kept, p.value, p.name], [true, FIRST, "cache-question"],
      "the pressed button stands until the press ends, so its click lands: the refused words and their typed name are back in the box");
    assert.deepEqual(await heldNotes(page), [], "and the repaint the acknowledgment owed ran on the release: the landed comment's entry is gone too");
  });
});

test("in chromium: a press on a note's Dismiss lands though another comment's refusal arrives during it, and the dialog's rebuild follows the release", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const second = await noteBesideAnother(page, send);
    await pressNoteButton(page, "cmtheldx");
    await refuse(send, second);                                          // the second is refused during the press: its warn, then its nack
    const kept = await samePressed(page, "cmtheldx");
    await releaseAndSettle(page);
    assert.equal(kept, true, "the pressed button stands until the press ends: neither the warn's rebuild nor the refusal's repaint replaced it");
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])],
      ["", [[notSaved("cache change"), SECOND, "none", true]]],
      "its click lands, so the first comment is dismissed, and the rebuild owed ran on the release: the second shows refused, on its own passage");
  });
});

// ── a current kernel's answers, placed by the id they name whatever the order of the posts ─────────────────────────────

test("in chromium: a current kernel's answers settle the comment each names, in whatever order they come, and one naming no comment of this page's settles none, even on its passage", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page);
    await lagNack(send, first);                                          // the first parked, so its landing comes later, from the pusher
    const second = await secondCreate(page);                             // the second's dialog open, sent; the first's words in the note
    await send({ type: "comments", id: SID, threads: [T_OLD, T_CACHE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });   // the second lands first
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid, await workingMarks(page)], ["thread", "t-0003", [P95]],
      "the answer naming the second comment settles the second, though the first was posted before it: its dialog becomes its thread, and the first stays out with its working mark");
    // another page's comment on the first comment's passage lands, and a current kernel's pusher acks it to every chat client
    const onP95 = { ...T_FIRST, tid: "t-0004", name: "api-comment-4", msgs: [{ who: "you", text: "Another page's comment.", t: 1757145900 }] };
    await send({ type: "comments", id: SID, threads: [T_OLD, T_CACHE, onP95] });
    await send({ type: "commentCreated", id: SID, tid: "t-0004", uuid: U2, createId: "k2another0viewer" });   // a stamped create of that page
    await send({ type: "commentCreated", id: SID, tid: "t-0004", uuid: U2, createId: "" });                   // an older page's unstamped one
    await commentOn(page, U2, P95);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words]), [[NOT_YET, FIRST]],
      "acks naming another page's comment on the first's passage, by an id this page does not hold or by an empty one, settle nothing: the first still waits in the note");
    await pressOutside(page);
    await ackFirst(page, send, first);                                   // the pusher lands the first
    await commentOn(page, U2, P95);
    assert.deepEqual(await heldNotes(page), [], "and the answer naming the first settles it");
  });
});

test("in chromium: a press on a note's words holds another comment's answer's repaint of the note until the release, and the repaint then runs", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const second = await noteBesideAnother(page, send);
    await page.hover("#cmt-pop .cmt-held-note .cmt-held-words");        // the refused first comment's words: a press there clicks nothing
    await page.mouse.down();
    await send({ type: "comments", id: SID, threads: [T_OLD, T_CACHE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });   // the second lands during the press
    const during = (await heldNotes(page)).map((n) => n.words);
    await releaseAndSettle(page);
    assert.deepEqual([during, (await heldNotes(page)).map((n) => n.words)], [[FIRST, SECOND], [FIRST]],
      "while the press is under way the note stands as it was; on the release the repaint the acknowledgment owed runs, and the landed comment's entry goes");
  });
});

// ── a comment the page gave up on, which the kernel lands after all ─────────────────────────────────────────────────
/** The comment parked by transcript lag, then re-posted on each session frame and each re-post refused as busy, as the
 *  kernel answers while it keeps the create parked, until the page gives up past its retry bound (the kernel keeps a
 *  park for more pusher cycles than the page retries it). */
async function givenUp(page: any, send: (m: unknown) => Promise<void>, createId: string): Promise<void> {
  await lagNack(send, createId);
  for (let i = 0; i < 14; i++) {
    const before = (await creates(page)).length;
    await send(SESSION);
    if ((await creates(page)).length > before) await lagNack(send, createId);
  }
}

test("in chromium: a comment the page gave up on that the kernel lands after all is settled by its late acknowledgment, as main's late one settles its comment", { timeout: 180000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await pressOutside(page);                                            // closed while out: its words wait in the note
    await givenUp(page, send, first);
    await commentOn(page, U2, P95);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_SAVED, FIRST, "enabled"]],
      "the precondition: given up, its words wait in the note, refused, with Bring it back");
    await pressOutside(page);
    await ackFirst(page, send, first);                                   // the pusher lands the parked create: its frame, then its ack
    await commentOn(page, U2, P95);
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", []],
      "its late ack settles it: its note entry goes, so the landed comment is not offered to be posted again");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");             // its dialog left open
    await givenUp(page, send, first);
    let p = await pop(page);
    assert.deepEqual([p.value, p.name, p.readOnly, p.send], [FIRST, "cache-question", false, "enabled"],
      "the precondition: given up, its words are back in its own dialog, editable, its Comment button live");
    await ackFirst(page, send, first);
    p = await pop(page);
    assert.deepEqual([p.mode, p.tid], ["thread", "t-0002"], "its late ack finds them as they were handed back: the dialog adopts the thread, as main's late ack does");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await givenUp(page, send, first);
    await pressOutside(page);                                            // closed after the give-up: the words wait in the passage's draft
    await ackFirst(page, send, first);
    await commentOn(page, U2, P95);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name, await heldNotes(page)], ["", p.prefill, []],
      "its late ack clears the passage's draft, which held the words and typed name exactly as they were handed back");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");             // its dialog left open
    await givenUp(page, send, first);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: first });   // the late ack, before its thread's frame
    let p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.name], ["create", "", p.prefill],
      "a late ack that beats its thread's frame finds the words as they were handed back and clears them and the typed name");
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
    p = await pop(page);
    assert.deepEqual([p.mode, p.tid], ["thread", "t-0002"], "and the frame that lists the thread adopts it into that dialog");
  });
});

test("in chromium: a comment the page gave up on and the kernel lands after all keeps words or a typed name changed since, with a toast, and one sent again by hand stands as its own thread", { timeout: 180000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await givenUp(page, send, first);
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("End");
    await page.keyboard.type(" And the p99?");                           // the person changes the handed-back words
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, (await toasts(page)).includes(SAVED_AFTER_ALL)], ["create", FIRST + " And the p99?", true],
      "the changed words stay in the box, and a toast says the comment was saved after all");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await givenUp(page, send, first);
    await page.focus("#cmt-pop .cmt-input");
    await page.keyboard.press("Enter");                                  // sent again by hand: a gesture of its own
    const again = (await creates(page)).slice(-1)[0].createId;
    assert.notEqual(again, first, "the precondition: the second send is a new gesture, with a new id");
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.send], ["create", FIRST, "disabled busy"],
      "the first comment's late ack, played after the comment was sent again by hand, settles the first alone: the dialog that sent it "
      + "again stays busy with its words, its own answer not played here (its thread would stand beside the first's, a duplicate the "
      + "person can delete)");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await givenUp(page, send, first);
    await page.fill("#cmt-pop .cmt-name", "renamed-question");          // the person changes only the handed-back typed name
    await ackFirst(page, send, first);
    const p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.name, (await toasts(page)).includes(SAVED_AFTER_ALL)], ["create", FIRST, "renamed-question", true],
      "a typed name changed since is a change too: the box keeps the words and the new name, and a toast says the comment was saved after all");
  });
});

test("in chromium: a late acknowledgment clears a handed-back typed name left alone in an emptied box, takes words waiting in the note out of it, and finds words dismissed from the note in no box, with no toast in any of the three", { timeout: 300000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");             // its dialog left open
    await givenUp(page, send, first);                                    // its words and typed name back in its own dialog
    await page.fill("#cmt-pop .cmt-input", "");                          // the person empties the box; the handed-back name stays
    await ackFirst(page, send, first);
    let p = await pop(page);
    assert.deepEqual([p.mode, p.value, p.name, (await toasts(page)).includes(SAVED_AFTER_ALL)], ["create", "", p.prefill, false],
      "the late ack takes the handed-back typed name too, as main's late ack deletes it, so a next comment there is not sent under the "
      + "landed thread's name; and no toast says the box's words are still there, since it holds none");
    await pressOutside(page);
    await commentOn(page, U2, P95);
    p = await pop(page);
    assert.deepEqual([p.value, p.name], ["", p.prefill], "the passage's typed-name draft went with it");
  });
  await openChat(t, async (page, send) => {
    const first = await firstCreate(page, "cache-question");
    await pressOutside(page);                                            // closed while out: its words wait in the note
    await givenUp(page, send, first);                                    // given up: its note entry turns refused
    await commentOn(page, U2, P95);
    await typeFresh(page, OTHER);                                        // the person types other words on the passage, beside the note
    await pressOutside(page);
    await ackFirst(page, send, first);
    assert.ok(!(await toasts(page)).includes(SAVED_AFTER_ALL), "the late ack of words that waited in the note shows no toast: no box held them");
    await commentOn(page, U2, P95);
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], [OTHER, []], "its note entry goes, and the words typed on the passage stay in its box");
  });
  for (const open of [true, false]) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await pressOutside(page);                                          // closed while out: its words wait in the note
      await commentOn(page, U2, P95);
      await typeFresh(page, OTHER);                                      // the person types other words on the passage meanwhile
      await givenUp(page, send, first);                                  // given up: its note entry turns refused, beside those words
      assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), [[NOT_SAVED, FIRST, "disabled", true]],
        "the precondition: the comment given up waits in the note beside the words typed in the box");
      await page.click('#cmt-pop [data-act="cmtheldx"]');               // the person dismisses its words
      if (!open) await pressOutside(page);
      await ackFirst(page, send, first);
      assert.ok(!(await toasts(page)).includes(SAVED_AFTER_ALL),
        "the late ack of words dismissed from the note shows no toast that what the box holds is still there: those words were typed "
        + "before the give-up, and the comment's own words were never in that box" + (open ? "" : " (its dialog closed)"));
      if (!open) await commentOn(page, U2, P95);
      assert.deepEqual([(await pop(page)).value, await heldNotes(page)], [OTHER, []], "and the words typed on the passage stay in its box");
    });
  }
});

// ── the dialog's mode: the two modes are the user's decision of 2026-09-25; each dialog takes one when it opens, from its
// host's latest evidence ──────────────────────────────────────────────────────────────────────────────────────────────

test("in chromium: a comment dialog keeps the mode it opened with: one opened on a kernel whose connect push lacks the marker is main's for its whole life, though the kernel comes back with the echo while it is open, and one opened after that is echo mode", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // the connect push lacked the marker: main mode
    await typeFresh(page, FIRST);
    await reconnect(page, true);                                         // the kernel restarts as a build with the echo while the dialog is open
    // and a caps frame announcing it: this page's ready got no caps frame at load (no caps: null), so the shim sends
    // that ready again on the new socket, and the kernel answers it with its caps frame (kernel.py ws.onopen,
    // readyAcked)
    await send({ type: "caps", caps: ECHO_CAPS, viewsSeq: null });
    await page.keyboard.press("Enter");
    let p = await pop(page);
    assert.deepEqual([await echoOf(page), (await creates(page)).map((c) => [c.exact, c.hasId]), p.readOnly, p.send], ["", [[P95, true]], false, "disabled busy"],
      "the dialog opened on a kernel without the echo keeps main mode after the kernel shows the echo: main's frame, its createId included, "
      + "and its box stays editable while it is out, as main's did");
    await commentOn(page, U4, "response cache");
    await typeFresh(page, SECOND);
    await page.keyboard.press("Enter");
    p = await pop(page);
    assert.deepEqual([await echoOf(page), (await creates(page)).map((c) => [c.exact, c.hasId]), p.readOnly, p.send], ["1", [[P95, true], ["response cache", true]], true, "disabled busy"],
      "a dialog opened once the connect push showed the echo is echo mode: its sent box is read-only");
  }, {}, false, { local: null });
  // the connect push alone is evidence: a kernel with the echo marks its first strip before any caps frame
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter");
    assert.deepEqual([await echoOf(page), (await pop(page)).readOnly], ["1", true], "a dialog opened after a connect push carrying the marker, before any caps frame, is echo mode");
  }, {}, false, { local: null, localPush: true });
});

test("in chromium: a comment dialog on a kernel whose connect push lacks the marker and whose caps lack the echo is main's", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter");
    const p = await pop(page);
    assert.deepEqual([await echoOf(page), p.readOnly, p.send], ["", false, "disabled busy"],
      "a kernel from before the echo gets main's dialog, whose box stays editable while its comment is out");
  }, {}, false, { local: OLDER_CAPS });
});

test("in chromium: a remote host's dialog takes its mode from that host's own connect push and caps frame, never the local kernel's, and a main-mode create its relay drops gets main's warn and hand-back alone", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await page.evaluate(() => {
      const w = window as any; w.__answers = [];
      window.addEventListener("message", (e: MessageEvent) => { const d = e.data;
        if (d && (d.type === "warn" || d.type === "commentCreateFailed")) w.__answers.push(d.type + (d.relayDrop ? " relayDrop" : "")); });
    });
    const one = async (needle: string, text: string) => {
      await commentOn(page, U2, needle);
      await typeFresh(page, text);
      await page.keyboard.press("Enter");                                // the host's relay is not open: federation drops the create
    };
    await one(P95, FIRST);
    let p = await pop(page);
    assert.deepEqual([await echoOf(page), await page.evaluate(() => (window as any).__answers)], ["", ["warn", "commentCreateFailed relayDrop"]],
      "with the host's connect push lacking the marker and no caps frame from it yet, its dialog is main's, though the local kernel's connect "
      + "push and caps announce the echo; federation answers the drop of main's frame, which carries a createId, with its warn and its own "
      + "relayDrop refusal");
    assert.deepEqual([p.mode, p.value, p.readOnly, p.send, await workingMarks(page)], ["create", FIRST, false, "enabled", []],
      "main's hand-back answers the warn: the dialog is live again with its words, its working mark gone");
    const before = (await creates(page)).length;
    await send(REMOTE_SESSION);
    await commentOn(page, U2, "ten percent");
    assert.deepEqual([(await creates(page)).length - before, await echoOf(page)], [0, ""],
      "the refusal arms no retry, since main's send posts its frame before it holds its create (the host's next session frame re-posts "
      + "nothing), and it is no evidence from the host (its next dialog is still main's)");
    // the host's relay opens again, after the open that brought the host's session and its comments frame, whose ready
    // got no caps frame before that socket dropped: so this open is no redial (federation's redial gate needs a socket
    // opened before AND a ready a caps frame answered), and it posts the page's ready again and fires romp:hostRelayUp;
    // the host's connect push, then its first caps frame answering that ready, come through federation's inbound door;
    // the relay then drops again
    await relayBack(page, "TESTHOST2", false);
    await page.evaluate((c: string[]) => (window as any).__rompFed.inbound("TESTHOST2", { type: "caps", caps: c, viewsSeq: null }), OLDER_CAPS);
    await one("cache change", SECOND);
    p = await pop(page);
    assert.deepEqual([await echoOf(page), p.readOnly, p.send], ["", false, "enabled"], "the host's connect push and caps frame without the echo keep its dialogs main's");
    const again = (await creates(page)).length;
    await send(REMOTE_SESSION);
    assert.equal((await creates(page)).length - again, 0,
      "a second send on the message, whose drop's refusal finds the first send's hold, arms nothing either: main's send replaces that hold "
      + "with its own right after (the host's next session frame re-posts nothing)");
  }, {}, true, { local: ECHO_CAPS, remote: null });
  // a host whose connect push carries the marker and whose first caps frame, on its relay's first connect, announces the
  // echo (once a caps frame has answered the page's ready, the relay's later returns are redials, which post no ready and
  // bring no caps frame; this page sees the host's caps once), beside a local kernel without it
  await openChat(t, async (page) => {
    await commentOn(page, U2, "ten percent");
    await typeFresh(page, OTHER);
    await page.keyboard.press("Enter");                                  // the host's relay is not open: federation drops the create
    const p = await pop(page);
    assert.deepEqual([await echoOf(page), p.value, p.readOnly, p.send], ["1", OTHER, true, "disabled busy"],
      "when the host's own connect push and caps frame announce the echo, its dialog is echo mode, though the local kernel's lack it, and "
      + "federation's refusal of that create's drop keeps it busy on its hold");
  }, {}, true, { local: OLDER_CAPS, remote: ECHO_CAPS });
});

// ── a kernel upgraded under the page, and a host attached again ───────────────────────────────────────────────────────
// A kernel that restarts as a build with the echo is known by its connection's connect push carrying the marker, and the
// next dialog there is echo mode (echo mode's own direction, with no base run to compare). The helpers below serve the
// tests further down that attach a host again.

// the other comment's thread, on "response cache" in U4, as the kernel's frame lists it once that comment lands
const T_RESPONSE = { ...T_OLD, tid: "t-0004", name: "api-comment-4", exact: "response cache", msgs: [{ who: "you", text: SECOND, t: 1757145700 }] };
/** The other host detached and attached again, on the relayed page: federation's detach closes each of its sessions
 *  here with a frame stamped hostDrop; the new relay's first open posts the page's ready and fires romp:hostRelayUp;
 *  the host's connect push (its strip, marked when its caps announce the echo, then its session's frame) and then its
 *  caps frame answer that ready, and its pusher's next cycle sends the session's comments frame to the new socket. A
 *  redial of the same relay posts no ready, so a host's caps frame reaches the page again only this way. */
async function reattach(page: any, send: (m: unknown) => Promise<void>, caps: string[], threads: unknown[] = [T_OLD]): Promise<void> {
  await send({ type: "closed", id: REMOTE_SID, hostDrop: true });
  await relayUp(page, "TESTHOST2");
  await connectPush(page, "TESTHOST2", capsEcho(caps));
  await send(REMOTE_SESSION);
  await hostCapsFrame(page, caps);
  await send({ type: "comments", id: REMOTE_SID, threads });
}

test("in chromium: a kernel upgraded under the page is known by its connection's connect push carrying the marker, or by an answer carrying the key before that push: the next comment is echo mode", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    // the kernel's connect push and caps frame listed no echo; it restarts as a build with the echo, and the page's
    // socket opens again: the person sends a comment before that connection's connect push
    await wsup(page);
    await sendOn(page, P95, FIRST);                                      // main mode: nothing has shown the change yet
    const mainId = (await creates(page))[0].createId;
    assert.deepEqual([await echoOf(page), (await pop(page)).readOnly], ["", false], "the precondition: a main-mode comment");
    await connectPush(page, "", true);                                   // the connect push, carrying the marker
    assert.deepEqual([await echoOf(page), (await creates(page)).length], ["", 1], "the open main-mode dialog keeps its mode, and nothing is posted again: main mode has no re-post");
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });   // the upgraded kernel's ack names main's own id
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid], ["thread", "t-0002"], "main's handling settles it, as main did: an id this page never minted in echo mode is main's");
    await commentOn(page, U2, "cache change");
    await typeFresh(page, SECOND);
    await page.keyboard.press("Enter");
    assert.deepEqual([await echoOf(page), (await pop(page)).readOnly], ["1", true], "the connect push carried the marker, so the next comment is echo mode");
  }, {}, false, { local: OLDER_CAPS });
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // the host's connect push and caps frame listed no echo: main mode
    assert.equal(await echoOf(page), "", "the precondition: the host's dialog is main's");
    await pressOutside(page);
    // the host restarts as a build with the echo: its relay opens again, a redial that posts no ready and so brings no
    // caps frame; another page's comment on the host lands before this connection's connect push, and that host's
    // pusher acks it to every chat client with an empty id: only a kernel with the echo sends the key
    await relayUp(page, "TESTHOST2");
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_OTHER_PAGE] });
    await send({ type: "commentCreated", id: REMOTE_SID, tid: "t-0009", uuid: U2, createId: "" });
    await commentOn(page, U2, P95);
    assert.equal(await echoOf(page), "1", "an empty id carries the key: the host's next dialog is echo mode, before the connection's connect push");
    await pressOutside(page);
    await connectPush(page, "TESTHOST2", true);
    await send(REMOTE_SESSION);
    await commentOn(page, U2, "cache change");
    assert.equal(await echoOf(page), "1", "and its connect push, carrying the marker, says the same");
  }, {}, "relayed", { remote: OLDER_CAPS });
});

// ── an answer goes by its createId: an id this page minted in echo mode to the echo-mode code, any other to main's ─────

test("in chromium: an answer naming no create this page minted in echo mode goes to main's handling, which settles a main-mode comment as the base did, and one naming an echo-mode comment never touches main-mode state", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // the kernel had no echo: main mode
    await typeFresh(page, FIRST);
    await reconnect(page, true);                                         // it restarts as a build with the echo; the open dialog keeps its mode
    await page.keyboard.press("Enter");                                  // main's frame, to the kernel with the echo
    // the kernel echoes, and its pusher acks another page's comment on this message to every chat client, naming its id
    await send({ type: "comments", id: SID, threads: [T_OLD, T_OTHER_PAGE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0009", uuid: U2, createId: "k2another0viewer" });
    const p = await pop(page);
    assert.deepEqual([p.mode, p.tid], ["thread", "t-0009"],
      "main's handling takes it, as main took it: the main-mode dialog is swapped for the other page's thread, as the base's was");
    assert.deepEqual(await repostsOnNextFrame(page, send), [], "and main's hold on the message is settled, as main settled it");
  }, {}, false, { local: OLDER_CAPS });
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // the kernel had no echo: main mode
    await typeFresh(page, FIRST);
    await reconnect(page, true);                                         // it restarts as a build with the echo; the open dialog keeps its mode
    await page.keyboard.press("Enter");                                  // main's frame, to the kernel with the echo
    const mainId = (await creates(page))[0].createId;
    await pressOutside(page);
    await sendOn(page, "cache change", SECOND);                          // echo mode, on the same message
    const second = (await creates(page))[1].createId;
    await send({ type: "comments", id: SID, threads: [T_OLD, T_CACHE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });
    assert.deepEqual([(await pop(page)).mode, (await pop(page)).tid], ["thread", "t-0003"], "the precondition: the echo-mode comment's ack adopts its own dialog");
    // a repeat of that ack, as the kernel answers a re-post of a create it made: an answer to an echo-mode comment settled already
    await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2, createId: second });
    await commentOn(page, U2, "ten percent");
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[NOT_YET, FIRST, "none"]],
      "main's draft of the message still holds the main-mode comment's words, not saved yet: the echo-mode ack never touched it");
    await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId });   // the main-mode comment's own answer
    const before = (await creates(page)).length;
    await send(SESSION);
    assert.deepEqual((await creates(page)).slice(before).map((c) => [c.exact, c.text, c.createId]), [[P95, FIRST, mainId]],
      "and main's hold stands: its own answer arms main's retry, which re-posts main's frame, its id unchanged");
  }, {}, false, { local: OLDER_CAPS });
});

test("in chromium: a main-mode comment is never re-posted when the connection or its host's relay comes back, as on main", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);                                      // a kernel without the echo: main mode
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter");
    await pressOutside(page);
    await reconnect(page, true);                                         // the kernel comes back as a build with the echo while the comment is out
    await reconnect(page, true);
    assert.deepEqual((await creates(page)).map((c) => c.exact), [P95], "main had no re-post, and a main-mode comment gets none even at a connect push carrying the marker");
  }, {}, false, { local: null });
  await openChat(t, async (page) => {
    await commentOn(page, U2, P95);
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter");
    await pressOutside(page);
    await relayBack(page, "TESTHOST2", true);
    await hostCapsFrame(page, ECHO_CAPS);
    await relayBack(page, "TESTHOST2", true);
    assert.deepEqual((await creates(page)).map((c) => c.exact), [P95], "nor on a host whose relay comes back with the echo, twice");
  }, {}, "relayed", NO_CAPS);
});

// ── no words lost across a mode change ───────────────────────────────────────────────────────────────────────────────
/** A note's lead for the other mode's draft: an echo-mode dialog's names the message (main's draft is the message's),
 *  a main-mode dialog's the passage, with the typed name when there is one. */
const draftLead = (on: string | null, name?: string): string =>
  "Words you typed earlier in a comment on " + (on === null ? "this message" : "“" + on + "”") + (name ? ", under the name " + name : "") + ":";

test("in chromium: words typed in a main-mode dialog come into an echo-mode dialog on their passage once the kernel announces the echo, and leave main's draft", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // a kernel without the echo: main mode
    await page.fill("#cmt-pop .cmt-name", "draft-name");
    await typeFresh(page, OTHER);
    await pressOutside(page);                                            // left unsent, in main's drafts (the message's)
    await reconnect(page, true);                                         // the kernel comes back as a build with the echo
    await commentOn(page, U2, P95);
    const p = await pop(page);
    assert.deepEqual([p.value, p.name], [OTHER, "draft-name"], "the echo-mode dialog on the passage opens with the words and the typed name, moved from main's draft");
    await pressOutside(page);
    await commentOn(page, U2, "cache change");
    const q = await pop(page);
    assert.deepEqual([q.value, q.name, await heldNotes(page)], ["", q.prefill, []],
      "moved, not copied: another passage of the message opens empty, where main's draft of the message would have followed it");
    await commentOn(page, U2, P95);
    await page.keyboard.press("Enter");
    assert.deepEqual((await creates(page)).map((c) => [c.exact, c.text]), [[P95, OTHER]], "and they are sent from there as an echo-mode comment");
  }, {}, false, { local: null });
});

/** A main-mode comment on `needle` of U2 sent to a kernel with the echo: its dialog opened on a kernel without it, which
 *  came back as a build with the echo (its connect push marked) before the person sent, so main's frame went to the
 *  kernel with the echo, whose answers name its id. Returns that id. */
async function mainSentAfterUpgrade(page: any, needle: string, text: string): Promise<string> {
  await commentOn(page, U2, needle);
  await typeFresh(page, text);
  await reconnect(page, true);
  await page.keyboard.press("Enter");
  assert.equal(await echoOf(page), "", "the precondition: the dialog kept the main mode it opened with");
  const sent = await creates(page);
  return sent[sent.length - 1].createId;
}
test("in chromium: an echo-mode dialog on a message whose main-mode comment is still out shows that comment's words in its note, not saved yet, until main's handling settles it", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    const mainId = await mainSentAfterUpgrade(page, P95, FIRST);         // main mode, its words kept in main's draft until its answer
    await commentOn(page, U2, "cache change");
    assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])], ["", [[NOT_YET, FIRST, "none", false]]],
      "the echo-mode dialog on the message opens empty, and its note shows the main-mode comment's words, not saved yet, with nothing to press: bringing them back would post that comment twice");
    await send({ type: "warn", text: REFUSAL });
    await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL, createId: mainId });
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), [[draftLead(null), FIRST, "enabled", true]],
      "main's handling refused it and its words stay in main's draft, as main left them: the entry follows the draft and offers Bring it back and Dismiss now");
    await commentOn(page, U2, P95);
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], [FIRST, []],
      "and an echo-mode dialog on the passage, its own draft empty, takes them from main's draft");
  }, {}, false, { local: null });
  await openChat(t, async (page, send) => {
    const mainId = await mainSentAfterUpgrade(page, P95, FIRST);         // main mode, its dialog then closed
    await pressOutside(page);
    await reconnect(page, true);                                         // its answer lost with the socket: main mode has no re-post
    const shown = [];
    await commentOn(page, U2, P95); shown.push((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]));
    await commentOn(page, U2, "cache change"); shown.push((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]));
    for (let i = 0; i < 3; i++) await send(SESSION);
    shown.push((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]));
    assert.deepEqual([shown, (await creates(page)).length], [[[[NOT_YET, FIRST, "none"]], [[NOT_YET, FIRST, "none"]], [[NOT_YET, FIRST, "none"]]], 1],
      "echo-mode dialogs on any passage of its message show the main-mode comment waiting, and session frames change nothing: its words are in reach, and nothing is posted twice");
    // the kernel had parked the create, and its lag refusal was lost with the old socket: its pusher lands it and sends
    // the frame, then the ack to every chat client, this page's new socket included, naming main's own id (main's handling)
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });
    assert.deepEqual(await heldNotes(page), [], "main's ack retires main's hold, and the entry, which quotes the comment from that hold, goes with it");
  }, {}, false, { local: null });
  await openChat(t, async (page, send) => {
    const mainId = await mainSentAfterUpgrade(page, P95, FIRST);         // main mode
    const lag = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId };
    await send(lag);                                                     // parked: main's frame-keyed retry is armed
    await commentOn(page, U2, "cache change");
    for (let i = 0; i < 14; i++) {                                       // every re-post answered busy, until main's retry gives up
      const before = (await creates(page)).length;
      await send(SESSION);
      if ((await creates(page)).length > before) await send(lag);
    }
    assert.deepEqual([(await toasts(page)).includes(GIVE_UP), (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])], [true, [[draftLead(null), FIRST, "enabled", true]]],
      "once main's retry gives up, the words main keeps in its draft show in the open echo-mode dialog's note with Bring it back and Dismiss");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], [FIRST, []], "and Bring it back puts them in its box, the person's own act");
  }, {}, false, { local: null });
});

test("in chromium: an echo-mode dialog's note quotes a main-mode comment still out from its hold, and words typed over main's draft in another main-mode dialog since as an entry of their own, with Bring it back and Dismiss", { timeout: 120000 }, async (t) => {
  for (const act of ["cmtheldback", "cmtheldx"]) {
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST);                                    // a kernel without the echo: main mode, its words kept in main's draft until its answer
      await commentOn(page, U2, "cache change");                         // a second main-mode dialog on the message opens with them, as main's did
      assert.equal((await pop(page)).value, FIRST, "the precondition: the second main-mode dialog opens with main's draft of the message");
      await typeFresh(page, OTHER);                                      // the person types over them there, and leaves them unsent
      await pressOutside(page);
      await reconnect(page, true);                                       // the kernel comes back as a build with the echo; the comment's answer went with the old socket
      await commentOn(page, U2, "ten percent");
      assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])],
        ["", [[NOT_YET, FIRST, "none", false], [draftLead(null), OTHER, "enabled", true]]],
        "the note quotes the main-mode comment's own words from its hold, not saved yet, with nothing to press; the words typed over "
        + "main's draft since are an entry of their own, words typed earlier, with Bring it back while the box is empty, and Dismiss");
      await page.click('#cmt-pop [data-act="' + act + '"]');
      assert.deepEqual([(await pop(page)).value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])],
        [act === "cmtheldback" ? OTHER : "", [[NOT_YET, FIRST, "none"]]],
        act === "cmtheldback" ? "Bring it back puts those words in the box, and the comment still out stays in the note"
          : "Dismiss drops those words, and the comment still out stays in the note");
    }, {}, false, { local: null });
  }
});

test("in chromium: words typed in an echo-mode dialog wait in a main-mode dialog's note on their passage, and main's handling never drops them until the person brings them back", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // the host's caps announce the echo: echo mode
    await page.fill("#cmt-pop .cmt-name", "draft-name");
    await typeFresh(page, OTHER);
    await pressOutside(page);                                            // left unsent, in the passage's echo-mode drafts
    // the host is detached and attached again, on a kernel without the echo: its sessions close here, its new relay
    // opens, its connect push, then its caps frame without the cap
    await reattach(page, send, OLDER_CAPS);
    const waiting = [[draftLead(P95, "draft-name"), OTHER, "enabled", true]];
    await commentOn(page, U2, P95);
    let p = await pop(page);
    assert.deepEqual([await echoOf(page), p.value, p.name, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])], ["", "", p.prefill, waiting],
      "the main-mode dialog opens with main's own draft, empty, and shows the echo-mode words and typed name in its note, with Bring it back and Dismiss");
    await pressOutside(page);
    // main's handling: the next comments frame prunes main's typed names, and an ack without the key of another
    // comment on the message deletes main's drafts of the message
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD] });
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_OTHER_PAGE] });
    await send({ type: "commentCreated", id: REMOTE_SID, tid: "t-0009", uuid: U2 });
    await commentOn(page, U2, P95);
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), waiting,
      "neither main's prune nor main's ack reaches them: the words and the typed name still wait in the note");
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_OTHER_PAGE] });   // a frame while the dialog is open
    assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss]), waiting, "nor a frame while the main-mode dialog is open");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    p = await pop(page);
    assert.deepEqual([p.value, p.name, await heldNotes(page)], [OTHER, "draft-name", []],
      "Bring it back, the person's own act, puts them in main's box, where main's handling applies to them from then on");
    await pressOutside(page);
    await reattach(page, send, ECHO_CAPS, [T_OLD, T_OTHER_PAGE]);          // attached again, on a kernel with the echo
    await commentOn(page, U2, P95);
    p = await pop(page);
    assert.deepEqual([p.value, p.name], [OTHER, p.prefill],
      "and an echo-mode dialog on the passage takes the words from main's draft once more; the typed name, in main's keys since, went at "
      + "main's prune when the host's comments frame arrived after it was attached again, as main's own typed name goes");
  }, {}, "relayed");
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // echo mode
    await typeFresh(page, OTHER);
    await pressOutside(page);
    await reattach(page, send, OLDER_CAPS);                              // attached again, on a kernel without the echo
    await commentOn(page, U2, P95);                                      // main mode, the words in its note
    await page.click('#cmt-pop [data-act="cmtheldx"]');
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", []], "Dismiss drops the words, as the person asked");
    await pressOutside(page);
    await reattach(page, send, ECHO_CAPS);                               // and again, on a kernel with the echo
    await commentOn(page, U2, P95);
    assert.deepEqual([(await pop(page)).value, await heldNotes(page)], ["", []], "gone from the echo-mode draft too: an echo-mode dialog on the passage opens empty");
  }, {}, "relayed");
});

test("in chromium: an echo-mode dialog on a passage with words of its own takes nothing from main's draft, which waits whole in its note, its typed name with its words", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);                                      // echo mode: the kernel's connect push and caps announced the echo
    await typeFresh(page, OTHER);
    await pressOutside(page);                                            // left unsent in the passage's echo-mode draft, with no typed name
    await reconnect(page, false);                                        // the kernel restarts as a build without the echo: its connect push shows it
    await commentOn(page, U2, "cache change");                           // main mode
    await page.fill("#cmt-pop .cmt-name", "main-name");
    await typeFresh(page, SECOND);
    await pressOutside(page);                                            // left unsent in main's draft of the message, under a typed name
    await reconnect(page, true);                                         // the kernel restarts again, as a build with the echo
    await commentOn(page, U2, P95);
    const p = await pop(page);
    assert.deepEqual([await echoOf(page), p.value, p.name, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])],
      ["1", OTHER, p.prefill, [[draftLead(null, "main-name"), SECOND, "disabled"]]],
      "the passage's own words open in its box under the suggested name, and main's draft, its words and typed name together, waits in "
      + "the note, its Bring it back waiting for an empty box: main's typed name never rides the passage's own words");
    await page.fill("#cmt-pop .cmt-input", "");
    await page.click('#cmt-pop [data-act="cmtheldback"]');
    const q = await pop(page);
    assert.deepEqual([q.value, q.name, await heldNotes(page)], [SECOND, "main-name", []], "and Bring it back brings main's words with their own typed name");
  });
});

test("in chromium: a main-mode comment the page gave up on, its words brought back into an echo-mode box, is cleared from that box by its late acknowledgment when unchanged, and kept with a toast when changed", { timeout: 300000 }, async (t) => {
  for (const how of ["unchanged", "changed", "closed"]) {
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST, "cache-question");                  // a kernel without the echo: main mode
      const mainId = (await creates(page))[0].createId;
      await pressOutside(page);
      await send(LAG_NO_ID);                                           // that kernel parks it, answering without the key: main's retry is armed
      await reconnect(page, true);                                       // it restarts as a build with the echo, the park lost with it
      await commentOn(page, U2, "cache change");                         // echo mode, the main-mode comment in its note, not saved yet
      // the kernel with the echo answers each of main's re-posts, naming main's own id
      const lag = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId };
      for (let i = 0; i < 14; i++) {                                     // every re-post answered busy, until main's retry gives up
        const before = (await creates(page)).length;
        await send(SESSION);
        if ((await creates(page)).length > before) await send(lag);
      }
      assert.deepEqual([(await toasts(page)).includes(GIVE_UP), (await heldNotes(page)).map((n) => [n.lead, n.words, n.back])],
        [true, [[draftLead(null, "cache-question"), FIRST, "enabled"]]],
        "the precondition: main's retry gave up, and the words main keeps in its draft show in the note with Bring it back");
      await page.click('#cmt-pop [data-act="cmtheldback"]');
      const b = await pop(page);
      assert.deepEqual([b.value, b.name], [FIRST, "cache-question"], "the precondition: Bring it back put the words and the typed name in the echo-mode box");
      if (how === "changed") await typeFresh(page, OTHER);
      if (how === "closed") await pressOutside(page);
      // the kernel's pusher lands it after all: its frame, then main's late ack, naming main's own id
      await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
      await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });
      const p = await pop(page), saved = (await toasts(page)).includes(SAVED_AFTER_ALL);
      if (how === "unchanged") {
        assert.deepEqual([p.mode, p.tid, saved], ["thread", "t-0002", false],
          "unchanged, the words and the typed name leave the box, and the open dialog adopts the landed thread, as main's late ack does");
      } else if (how === "changed") {
        assert.deepEqual([p.mode, p.value, p.name, saved], ["create", OTHER, "cache-question", true],
          "changed since, the box keeps what the person typed, and a toast says the comment was saved after all");
      } else {
        await commentOn(page, U2, "cache change");
        const q = await pop(page);
        assert.deepEqual([q.value, q.name, await heldNotes(page), saved], ["", q.prefill, [], false],
          "with the dialog closed, the words and the typed name left in that passage's draft are cleared, unchanged as they were");
      }
    }, {}, false, { local: null });
  }
});

// ── main mode, played as the base's repro and the older-kernel sequences, asserting the base's outcomes
// ───────────────── The user decided (2026-09-25) that against a kernel that does not announce the echo the page keeps
// main's create handling exactly, including the same-message collision described at the top of this file. Each test in
// this group, titled "main mode:" (or "main mode (a):" to "(d):"), plays one sequence on a kernel from before the echo
// (its connect push without the marker, and no caps frame: main mode; where another host's session shows in a tab
// beside this kernel's, that host's relay's connect push, also without the marker, comes first too) and compares what
// the person sees and every frame the page posts, step by step, with what the same steps gave over the base bundle
// (MAIN_BASE is that run's output): the base's four repro sub-cases, (a) to (d), with (b) and (c)'s second parts; three
// single-comment sequences (one comment acknowledged, two comments one after another, one sent again after its
// refusal); four sequences of answers without the key (two lag-parked comments whose every re-post is refused as busy,
// another page's comment acknowledged on the message, a host's comment whose answer was lost with its relay, a
// lag-parked comment the pusher lands while a second one is out); and main's own lines no other test runs in main mode
// (the dialog's picks riding the frame, an ack before its frame and a second frame after it, an ack before its frame
// and then an unrelated warn, a refusal with the dialog closed, an invalid typed name, another session's comment
// acknowledged while a dialog holds typed words, the working mark's click into its placeholder's popover, whose title
// and state chip are compared too, an ack before its frame whose frame arrives while another session's dialog holds
// typed words, an attachment's path arriving while a dialog is open, a comment opened from the keyboard over a sent
// dialog on another passage of its message, and, further down, a comment opened from the keyboard on another message
// over an unsent dialog and one opened over an open thread). The harness serves the kernel's palette, so each dialog's
// colour, compared at every step, is the one pickThreadColor picked from the colours the session's threads wear, the
// working marks' included; and where the popover stands and how large it is, a create dialog's or a thread's, is
// compared at every step too. Frames are compared whole, every field, with each createId named by the order it first
// appeared, so a re-post of the same gesture reads as the same id, where the base's ids, minted at random, would never
// match. The tests titled "main mode beside an echo-mode dialog:", in a section of their own further down, play caps
// frames or an answer carrying the key, so an echo-mode dialog is open where the base's is main's, and compare only
// what main's adoption, or main's warn, does to the thread side.

const LAG_NO_ID = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG };   // a lag or busy nack without the key
const T_OTHER_PAGE = { ...T_FIRST, tid: "t-0009", name: "api-comment-9", exact: "forty percent", msgs: [{ who: "you", text: "Another page's comment.", t: 1757145900 }] };
/** Starts a main-mode test's record of posts here: the frames the page posted while it loaded are not the test's. */
const lookFromHere = (page: any) => page.evaluate(() => { (window as any).__seenAt = (window as any).__posts.length; });
/** What the person sees and what the page has posted since the last look: the dialog, its title and its colour (a create
 *  dialog's name box wears the colour picked for the comment, a thread's title the thread's), a thread popover's state
 *  chip (its parts, a working thread's timer and Stop among them, and its label), where the popover stands and how
 *  large it is (a create dialog or a thread's, rounded to whole pixels), every frame posted since, whole (each createId
 *  named "id1", "id2", ... by the order it first appeared), whether the name box refused its name, the working marks,
 *  the toasts and any note; and a create dialog's DOM (createDom). */
async function seen(page: any): Promise<unknown> {
  const posted = await page.evaluate(() => {
    const w = window as any;
    const ids: Record<string, string> = (w.__cids = w.__cids || {});
    const from = w.__seenAt || 0;
    w.__seenAt = w.__posts.length;
    return w.__posts.slice(from).map((m: any) => {
      const f = { ...m };
      if ("createId" in f) f.createId = ids[f.createId] || (ids[f.createId] = "id" + (Object.keys(ids).length + 1));
      return f;
    });
  });
  const color = await page.evaluate(() => {
    const p = document.getElementById("cmt-pop"), nb = p?.querySelector(".cmt-name") as HTMLElement | null, ti = p?.querySelector(".cmt-title") as HTMLElement | null;
    return nb ? nb.style.color : ti ? ti.style.color : null;
  });
  const rect = await page.evaluate(() => {
    const p = document.getElementById("cmt-pop");
    if (!p) return null;
    const r = p.getBoundingClientRect();
    return [r.left, r.top, r.width, r.height].map(Math.round);
  });
  // the thread popover's state chip: its parts by class (a working thread's chip, its timer and its Stop; a ready one's
  // chip alone) and the chip's label, the timer's running count left out
  const state = await page.evaluate(() => {
    const st = document.querySelector("#cmt-pop #cmt-state");
    return st ? { parts: Array.from(st.children).map((c) => c.className), chip: st.querySelector(".chip")?.textContent ?? null } : null;
  });
  return { pop: await pop(page), title: await page.evaluate(() => document.querySelector("#cmt-pop .cmt-title")?.textContent ?? null), color, state, rect,
           posted, badName: await page.evaluate(() => !!document.querySelector("#cmt-pop .cmt-name.bad")),
           marks: await workingMarks(page), toasts: await toasts(page), notes: (await heldNotes(page)).map((n) => [n.lead, n.words, n.back]),
           dom: await createDom(page) };
}
/** A create dialog's DOM, so a main-mode dialog is compared with the base's node for node and attribute for attribute:
 *  the popover's own attribute names, its children by tag and class, and a digest of its whole markup (outerHTML, with
 *  the press pulse's class taken out, which a click leaves for a moment); null with no create dialog open. A thread
 *  popover's markup holds day labels and a running timer, which move with the clock, so it is compared by the fields
 *  above alone. */
const createDom = (page: any): Promise<unknown> => page.evaluate(() => {
  const p = document.getElementById("cmt-pop");
  if (!p || p.dataset.mode !== "create") return null;
  const c = p.cloneNode(true) as HTMLElement;
  for (const x of [c, ...Array.from(c.querySelectorAll(".romp-acted"))]) { x.classList.remove("romp-acted"); if (x.getAttribute("class") === "") x.removeAttribute("class"); }
  const html = c.outerHTML;
  let h1 = 0x811c9dc5, h2 = 0x9747b28c;                   // two 32-bit FNV-1a runs, for a 64-bit digest
  for (let i = 0; i < html.length; i++) { const k = html.charCodeAt(i); h1 = Math.imul(h1 ^ k, 16777619) >>> 0; h2 = Math.imul(h2 ^ k, 16777619) >>> 0; }
  return { attrs: Array.from(c.attributes).map((a) => a.name).sort(), kids: Array.from(c.children).map((k) => k.tagName.toLowerCase() + "." + k.className),
           digest: (h1.toString(36) + "Z" + h2.toString(36)).toUpperCase() };
});
/** A comment sent from a dialog opened on `needle` of U2 (or `uuid`), the box emptied first, under a typed name when
 *  one is given. */
async function sendOn(page: any, needle: string, text: string, name?: string, uuid: string = U2): Promise<void> {
  await commentOn(page, uuid, needle);
  if (name) await page.fill("#cmt-pop .cmt-name", name);
  await typeFresh(page, text);
  await page.keyboard.press("Enter");
}
/** The dialog's own picks from the kernel's model list (MODELS): Opus for its model, High for its effort, then Fast. */
async function pickEach(page: any): Promise<void> {
  for (const [i, label] of [[0, "Opus"], [1, "High"]] as [number, string][]) {
    await page.click("#cmt-pop .cmt-meta-row .meta-btn >> nth=" + i);
    await page.click('.meta-menu .meta-item:text-is("' + label + '")');
    await page.waitForSelector('#cmt-pop .cmt-meta-row .meta-btn >> nth=' + i + ' >> .meta-label:text-is("' + label + '")', { timeout: 5000 });
  }
  await page.click('#cmt-pop .cmt-meta-row .meta-btn:has(.meta-label:text-is("Slow"))');
  await page.click('.meta-menu .meta-item:text-is("Fast")');
  await page.waitForSelector('#cmt-pop .cmt-meta-row .meta-label:text-is("Fast")', { timeout: 5000 });
}
const NO_CAPS: Caps = { local: null, remote: null };
/** The steps a main-mode test saw, each against the base's outcome for the same step (MAIN_BASE[key]). */
function sameAsBase(steps: [string, unknown][], key: string): void {
  const base = MAIN_BASE[key];
  assert.ok(base, "the base run's outcome for " + key);
  assert.deepEqual(steps.map((s) => s[0]), base.map((s) => s[0]), "the same steps as the base run");
  for (let i = 0; i < steps.length; i++) assert.deepEqual(steps[i][1], base[i][1], "main mode shows and posts what the base did at step " + steps[i][0]);
}
// main's give-up toast, read from render.ts's own retry (retryCmtCreates), so the leg restates none of main's words
const GIVE_UP = ((): string => {
  const src = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
  const at = src.indexOf("function retryCmtCreates(");
  const lit = at > 0 ? /warnToast\(("(?:[^"\\]|\\.)*")\)/.exec(src.slice(at, src.indexOf("\n}\n", at))) : null;
  assert.ok(lit, "main's frame-keyed retry gives up with a toast");
  return JSON.parse(lit![1]);
})();
// The base run's outcomes, step by step (the base bundle's), main's give-up toast named by GIVE_UP.
const MAIN_BASE: Record<string, [string, unknown][]> = {
  frame: [
    ["picked", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1A4L4KFZ18C0Z6C"}}],
    ["sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "opus", "effort": "high", "fast": "on", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "10D36W1ZVQWMN8"}}],
    ["re-posted", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "opus", "effort": "high", "fast": "on", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "10D36W1ZVQWMN8"}}],
  ],
  a: [
    ["first sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["Enter again in the sent dialog", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["second opened", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1NQT18AZ1QWC89J"}}],
    ["Enter there", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-3", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id3"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "6VMT4AZ2H1MMP"}}],
    ["another message", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000004", "quote": "response cache", "value": "", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [322, 204, 341, 157], "posted": [], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "HEI2RZZSHI5M4"}}],
  ],
  b: [
    ["second typed", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1NQT18AZ1QWC89J"}}],
    ["first acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["second reopened", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [686, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "124M999Z1XEJJO6"}}],
  ],
  bCross: [
    ["other message typed", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000004", "quote": "response cache", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [322, 204, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "3KH8V2Z1APJMXN"}}],
    ["first acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 204, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["other message reopened", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000004", "quote": "response cache", "value": "", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [322, 204, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "HEI2RZZSHI5M4"}}],
  ],
  c: [
    ["refused", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["another passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "ten percent", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [539, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "D5WE9PZ15POJK8"}}],
    ["its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  cOpen: [
    ["second typed", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1NQT18AZ1QWC89J"}}],
    ["first refused", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VGZ6DZZGCA81M"}}],
    ["its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  cName: [
    ["a comments frame while it is out", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["refused", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  d: [
    ["both sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "6VMT4AZ2H1MMP"}}],
    ["both nacked, a frame", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": ["cache change"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "6VMT4AZ2H1MMP"}}],
    ["first acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["second nacked, a frame", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
  ],
  dRefuse: [
    ["first refused", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VGZ6DZZGCA81M"}}],
    ["second nacked, a frame", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VGZ6DZZGCA81M"}}],
  ],
  single: [
    ["acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["second acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0003", "quote": "cache change", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-3", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0003"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
  ],
  resent: [
    ["refused", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["sent again", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}], "badName": false, "marks": ["p95 latency"], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["acked", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": null}],
  ],
  ackFirst: [
    ["sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["acked before its frame", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["its frame", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["a second frame", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
  ],
  ackThenWarn: [
    ["sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["acked before its frame", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["an unrelated warn", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["its frame", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": null}],
  ],
  refusedClosed: [
    ["closed", {"pop": {"open": false, "mode": null, "tid": null, "quote": null, "value": null, "readOnly": null, "name": null, "prefill": null, "send": null}, "title": null, "color": null, "state": null, "rect": null, "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": null}],
    ["refused", {"pop": {"open": false, "mode": null, "tid": null, "quote": null, "value": null, "readOnly": null, "name": null, "prefill": null, "send": null}, "title": null, "color": null, "state": null, "rect": null, "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": null}],
    ["its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  badName: [
    ["an invalid typed name", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "not a name!", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": true, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "UIKV4QZ1VFTO7R"}}],
    ["a valid one", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "a-name", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "a-name", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
  ],
  parkedTwo: [
    ["re-posts per comment", {"Second note: and the p99?": 12}],
    ["after 16 frames", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": [GIVE_UP], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "6VMT4AZ2H1MMP"}}],
    ["its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [GIVE_UP], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  otherPage: [
    ["another page's ack, its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VRUCT2ZNO8RPB"}}],
    ["its own refusal, its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": ["thread names use letters, digits, . _ - only."], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VRUCT2ZNO8RPB"}}],
  ],
  otherPageOpen: [
    ["another page's ack, the dialog open", {"pop": {"open": true, "mode": "thread", "tid": "t-0009", "quote": "forty percent", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-9", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0009"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["a second ack after its nack", {"pop": {"open": true, "mode": "thread", "tid": "t-0009", "quote": "forty percent", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-9", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
  ],
  relayLost: [
    ["re-posts per comment", {"Second note: and the p99?": 12}],
    ["its passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "activeTab", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "nonce": 4}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id2"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": [GIVE_UP], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VRUCT2ZNO8RPB"}}],
  ],
  pusherLands: [
    ["the pusher's ack of the first", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "Second note: and the p99?", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}, {"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["the second's ack", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["the next frame", {"pop": {"open": true, "mode": "thread", "tid": "t-0002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [322, 116, 770, 456], "posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
  ],
  keyboard: [
    ["keyboard over the sent dialog", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["Enter there", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "cache-question", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "cache change", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#E06C75", "createId": "id2"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
  ],
  twoSessions: [
    ["typed in a dialog on this kernel's session", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["the other session's comment acknowledged", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["its passage again", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  markClick: [
    ["sent and closed", {"pop": {"open": false, "mode": null, "tid": null, "quote": null, "value": null, "readOnly": null, "name": null, "prefill": null, "send": null}, "title": null, "color": null, "state": null, "rect": null, "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": null}],
    ["its working mark clicked", {"pop": {"open": true, "mode": "thread", "tid": "pending:aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "rgb(30, 161, 235)", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "pending:aaaaaaaa-0000-0000-0000-000000000002"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": null}],
    ["a reply typed there", {"pop": {"open": true, "mode": "thread", "tid": "pending:aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-2", "color": "rgb(30, 161, 235)", "state": {"parts": ["chip chip-working", "status-timer", "stop-btn cmt-stop"], "chip": "Working"}, "rect": [247, 116, 770, 456], "posted": [{"type": "commentReply", "id": "11111111-2222-3333-4444-555555555555", "tid": "pending:aaaaaaaa-0000-0000-0000-000000000002", "text": "Second note: and the p99?"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": null}],
  ],
  parkedOtherSession: [
    ["sent on this kernel's session", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["acknowledged before its frame", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "MZZZF1Z1742EE2"}}],
    ["typed in a dialog on the other session", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-1", "prefill": "api-comment-1", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [686, 116, 341, 157], "posted": [{"type": "activeTab", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "nonce": 4}, {"type": "clientDiag", "surface": "chat", "what": "tailchange", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "dh": 202.25, "last": "turn turn-assistant", "stick": true, "sh": 648, "ch": 648}}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VYWNOJZO2GNKK"}}],
    ["the first comment's frame", {"pop": {"open": false, "mode": null, "tid": null, "quote": null, "value": null, "readOnly": null, "name": null, "prefill": null, "send": null}, "title": null, "color": null, "state": null, "rect": null, "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["that passage again", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "cache change", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-1", "prefill": "api-comment-1", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [686, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "VYWNOJZO2GNKK"}}],
  ],
  droppedPath: [
    ["typed", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["a file's path arrives", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache. /tmp/romp-drop/shot.png ", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["its passage again", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache. /tmp/romp-drop/shot.png ", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
  ],
  keyboardOtherMessage: [
    ["typed on a passage of one message", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "13KYTFFZ1MLKYZU"}}],
    ["the keyboard's Comment on another message", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000004", "quote": "response cache", "value": "", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [273, 199, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1KSDWJUZ1WBVJ2X"}}],
    ["typed and sent there", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000004", "quote": "response cache", "value": "Second note: and the p99?", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [273, 199, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000004", "exact": "response cache", "text": "Second note: and the p99?", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["response cache"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "3KEQEYZ8VZTLJ"}}],
    ["the first passage again", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-3", "prefill": "api-comment-3", "send": "enabled"}, "title": "New comment:", "color": "rgb(224, 108, 117)", "state": null, "rect": [247, 116, 341, 157], "posted": [], "badName": false, "marks": ["response cache"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1QGS1V9Z1GXQDJY"}}],
  ],
  keyboardOverThread: [
    ["a thread opened from its mark", {"pop": {"open": true, "mode": "thread", "tid": "t-0001", "quote": "fallback path", "value": "", "readOnly": false, "name": null, "prefill": null, "send": "enabled"}, "title": "api-comment-1", "color": "", "state": {"parts": ["chip chip-ready"], "chip": "Ready"}, "rect": [322, 120, 770, 456], "posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0001"}], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": null}],
    ["the keyboard's Comment on a passage", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "enabled"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [211, 111, 341, 157], "posted": [], "badName": false, "marks": [], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "L11X95ZVPGP0C"}}],
    ["typed and sent", {"pop": {"open": true, "mode": "create", "tid": "aaaaaaaa-0000-0000-0000-000000000002", "quote": "p95 latency", "value": "First note: say which cache.", "readOnly": false, "name": "api-comment-2", "prefill": "api-comment-2", "send": "disabled busy"}, "title": "New comment:", "color": "rgb(30, 161, 235)", "state": null, "rect": [211, 111, 341, 157], "posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "badName": false, "marks": ["p95 latency"], "toasts": [], "notes": [], "dom": {"attrs": ["class", "data-mode", "data-status", "data-tid", "id", "style"], "kids": ["div.cmt-head", "div.cmt-quote", "div.cmt-composer", "div.statusline cmt-meta-row", "div.cmt-actions"], "digest": "1OK14RBZFDJ77C"}}],
  ],
  parkedEchoOtherSession: [
    ["sent on this kernel's session", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["acknowledged before its frame", {"posted": [], "busy": []}],
    ["typed in a dialog on the other session", {"posted": [{"type": "activeTab", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "nonce": 4}, {"type": "clientDiag", "surface": "chat", "what": "tailchange", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "dh": 202.25, "last": "turn turn-assistant", "stick": true, "sh": 648, "ch": 648}}], "busy": []}],
    ["the first comment's frame", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  parkedEchoSameSession: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["acknowledged before its frame, naming its id", {"posted": [], "busy": []}],
    ["typed in a dialog on another message", {"posted": [], "busy": []}],
    ["the first comment's frame", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoIdleLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoWorkingLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": ["t-0002"]}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": ["t-0002"]}],
    ["its thread opened from its mark", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
  ],
  ackEchoSameMessageLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["typed in a dialog on cache change", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoParkedLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["acknowledged before its frame", {"posted": [], "busy": []}],
    ["its frame", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoIdleRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoWorkingRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": ["t-0002"]}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": ["t-0002"]}],
    ["its thread opened from its mark", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
  ],
  ackEchoSameMessageRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": []}],
    ["typed in a dialog on cache change", {"posted": [], "busy": []}],
    ["its frame", {"posted": [], "busy": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  ackEchoParkedRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": []}],
    ["its lag refusal, naming its id", {"posted": [], "busy": []}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": []}],
    ["typed in a dialog on response cache", {"posted": [], "busy": []}],
    ["acknowledged before its frame", {"posted": [], "busy": []}],
    ["its frame", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"]}],
    ["its next frame", {"posted": [], "busy": []}],
  ],
  warnBesideSameMessageLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on cache change", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a warn that is not a comment's", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["its frame", {"posted": [], "busy": ["t-0002"], "marks": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"], "marks": []}],
  ],
  warnBesideOwnRefusalLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on cache change", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["its refusal's warn", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["its refusal, naming its id", {"posted": [], "busy": [], "marks": [], "suggested": "api-comment-2"}],
  ],
  warnBesideOtherMessageLocal: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on response cache", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a warn that is not a comment's", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["its frame", {"posted": [], "busy": ["t-0002"], "marks": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"], "marks": []}],
  ],
  warnBesideSameMessageRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on cache change", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a warn that is not a comment's", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["its frame", {"posted": [], "busy": ["t-0002"], "marks": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"], "marks": []}],
  ],
  warnBesideOwnRefusalRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on cache change", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["its refusal's warn", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": [], "suggested": "api-comment-2"}],
    ["its refusal, naming its id", {"posted": [], "busy": [], "marks": [], "suggested": "api-comment-2"}],
  ],
  warnBesideOtherMessageRemote: [
    ["sent", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}], "busy": [], "marks": ["p95 latency"]}],
    ["its lag refusal, naming its id", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["its connection's connect push, carrying the marker", {"posted": [], "busy": [], "marks": ["p95 latency"]}],
    ["typed in a dialog on response cache", {"posted": [], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a warn that is not a comment's", {"posted": [{"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["a session frame, its retry re-posting the comment", {"posted": [{"type": "commentCreate", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "uuid": "aaaaaaaa-0000-0000-0000-000000000002", "exact": "p95 latency", "text": "First note: say which cache.", "name": "cache-question", "model": "", "effort": "", "fast": "", "color": "#1EA1EB", "createId": "id1"}, {"type": "clientDiag", "surface": "chat", "what": "tailmut", "data": {"sid": "TESTHOST2:11111111-2222-3333-4444-555555555555", "where": "view", "removed": ["turn turn-assistant"], "added": ["turn turn-user injected", "turn turn-assistant", "turn turn-user injected", "turn turn-assistant"], "reAdded": false, "shBefore": 611, "shAfter": 611, "st": 0, "ch": 611}}], "busy": [], "marks": ["p95 latency"], "suggested": "api-comment-3"}],
    ["its frame", {"posted": [], "busy": ["t-0002"], "marks": []}],
    ["its acknowledgment", {"posted": [{"type": "commentSeen", "id": "TESTHOST2:11111111-2222-3333-4444-555555555555", "tid": "t-0002"}], "busy": ["t-0002"], "marks": []}],
  ],
};







test("in chromium: main mode: a comment's frame is main's, whole, its picks and a createId minted at the send and re-posted unchanged, as the base posted it", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await commentOn(page, U2, P95);
    await pickEach(page); steps.push(["picked", await seen(page)]);
    await page.fill("#cmt-pop .cmt-name", "cache-question");
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter"); steps.push(["sent", await seen(page)]);
    await send(LAG_NO_ID); await send(SESSION); steps.push(["re-posted", await seen(page)]);
    const frames = await page.evaluate(() => (window as any).__posts.filter((m: any) => m.type === "commentCreate"));
    assert.ok(frames.length === 2 && typeof frames[0].createId === "string" && frames[0].createId && frames[1].createId === frames[0].createId
              && frames[0].model && frames[0].effort && frames[0].fast === "on" && frames[0].color,
      "main's frame carries the gesture's createId, the same on its re-post, and the dialog's picks: " + JSON.stringify(frames));
    sameAsBase(steps, "frame");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode (a): a second comment on a message while the first is unanswered opens with the first's words and name, and Enter posts them on the other passage, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question"); steps.push(["first sent", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.press("Enter"); steps.push(["Enter again in the sent dialog", await seen(page)]);
    await commentOn(page, U2, "cache change"); steps.push(["second opened", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.press("Enter"); steps.push(["Enter there", await seen(page)]);
    await commentOn(page, U4, "response cache"); steps.push(["another message", await seen(page)]);
    sameAsBase(steps, "a");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode (b): the first comment's acknowledgment swaps a second dialog on its message, or on another message, for its thread and deletes its words, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await commentOn(page, U2, "cache change"); await typeFresh(page, SECOND); steps.push(["second typed", await seen(page)]);
    await ackFirst(page, send, null); steps.push(["first acked", await seen(page)]);
    await commentOn(page, U2, "cache change"); steps.push(["second reopened", await seen(page)]);
    sameAsBase(steps, "b");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await commentOn(page, U4, "response cache"); await typeFresh(page, SECOND); steps.push(["other message typed", await seen(page)]);
    await ackFirst(page, send, null); steps.push(["first acked", await seen(page)]);
    await commentOn(page, U4, "response cache"); steps.push(["other message reopened", await seen(page)]);
    sameAsBase(steps, "bCross");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode (c): a refused comment's words open on any passage of its message, and are lost to words typed in a second dialog there, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["refused", await seen(page)]);
    await commentOn(page, U2, "ten percent"); steps.push(["another passage", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage", await seen(page)]);
    sameAsBase(steps, "c");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await commentOn(page, U2, "cache change"); await typeFresh(page, SECOND); steps.push(["second typed", await seen(page)]);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["first refused", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage", await seen(page)]);
    sameAsBase(steps, "cOpen");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question");
    await send({ type: "comments", id: SID, threads: [T_OLD] }); steps.push(["a comments frame while it is out", await seen(page)]);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["refused", await seen(page)]);
    sameAsBase(steps, "cName");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode (d): a second send on a message takes over the first's retry hold and working mark, and the first's answer settles the second, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); await sendOn(page, "cache change", SECOND); steps.push(["both sent", await seen(page)]);
    await send(LAG_NO_ID); await send(LAG_NO_ID); await send(SESSION); steps.push(["both nacked, a frame", await seen(page)]);
    await ackFirst(page, send, null); steps.push(["first acked", await seen(page)]);
    await send(LAG_NO_ID); await send(SESSION); steps.push(["second nacked, a frame", await seen(page)]);
    sameAsBase(steps, "d");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); await sendOn(page, "cache change", SECOND);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["first refused", await seen(page)]);
    await send(LAG_NO_ID); await send(SESSION); steps.push(["second nacked, a frame", await seen(page)]);
    sameAsBase(steps, "dRefuse");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: one comment's answers without a create id settle it, as the base did (an ack; two comments one after another; one sent again after its refusal)", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await ackFirst(page, send, null); steps.push(["acked", await seen(page)]);
    await sendOn(page, "cache change", SECOND);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST, T_CACHE] }); await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2 });
    steps.push(["second acked", await seen(page)]);
    sameAsBase(steps, "single");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["refused", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.press("Enter"); steps.push(["sent again", await seen(page)]);
    await ackFirst(page, send, null); steps.push(["acked", await seen(page)]);
    sameAsBase(steps, "resent");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: an acknowledgment that beats its thread's frame parks, the frame adopts it once and marks it seen, and a warn before that frame shows the suggested name, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question"); steps.push(["sent", await seen(page)]);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 }); steps.push(["acked before its frame", await seen(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] }); steps.push(["its frame", await seen(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] }); steps.push(["a second frame", await seen(page)]);
    sameAsBase(steps, "ackFirst");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question"); steps.push(["sent", await seen(page)]);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 }); steps.push(["acked before its frame", await seen(page)]);
    await send({ type: "warn", text: REFUSAL }); steps.push(["an unrelated warn", await seen(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] }); steps.push(["its frame", await seen(page)]);
    sameAsBase(steps, "ackThenWarn");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: a comment refused after its dialog closed, with no other thread on its message, loses its working mark, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); await pressOutside(page); steps.push(["closed", await seen(page)]);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    steps.push(["refused", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage", await seen(page)]);
    sameAsBase(steps, "refusedClosed");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: a typed name the kernel would refuse is not posted, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await commentOn(page, U2, P95);
    await page.fill("#cmt-pop .cmt-name", "not a name!");
    await typeFresh(page, FIRST);
    await page.keyboard.press("Enter"); steps.push(["an invalid typed name", await seen(page)]);
    await page.fill("#cmt-pop .cmt-name", "a-name");
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.press("Enter"); steps.push(["a valid one", await seen(page)]);
    sameAsBase(steps, "badName");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: two lag-parked comments on a message, every re-post nacked, as the base did", { timeout: 180000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); await sendOn(page, "cache change", SECOND);
    await send(LAG_NO_ID); await send(LAG_NO_ID);
    const per: Record<string, number> = {};
    for (let i = 0; i < 16; i++) {
      const before = (await creates(page)).length;
      await send(SESSION);
      for (const c of (await creates(page)).slice(before)) { per[c.text] = (per[c.text] || 0) + 1; await send(LAG_NO_ID); }
    }
    steps.push(["re-posts per comment", per]);
    steps.push(["after 16 frames", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage", await seen(page)]);
    sameAsBase(steps, "parkedTwo");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: another page's comment acknowledged on the message, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question");
    await pressOutside(page);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_OTHER_PAGE] }); await send({ type: "commentCreated", id: SID, tid: "t-0009", uuid: U2 });
    await commentOn(page, U2, P95); steps.push(["another page's ack, its passage", await seen(page)]);
    await pressOutside(page);
    await send({ type: "warn", text: REFUSAL }); await send({ type: "commentCreateFailed", id: SID, uuid: U2, transient: false, text: REFUSAL });
    await commentOn(page, U2, P95); steps.push(["its own refusal, its passage", await seen(page)]);
    sameAsBase(steps, "otherPage");
  }, {}, false, NO_CAPS);
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_OTHER_PAGE] }); await send({ type: "commentCreated", id: SID, tid: "t-0009", uuid: U2 });
    steps.push(["another page's ack, the dialog open", await seen(page)]);
    await send(LAG_NO_ID);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_OTHER_PAGE, { ...T_OTHER_PAGE, tid: "t-0010", exact: "ten percent" }] });
    await send({ type: "commentCreated", id: SID, tid: "t-0010", uuid: U2 });
    steps.push(["a second ack after its nack", await seen(page)]);
    sameAsBase(steps, "otherPageOpen");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: a host's comment whose answer was lost with its relay, and a second one lag-nacked, as the base did", { timeout: 180000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    const repeatAck = async () => { await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_FIRST] }); await send({ type: "commentCreated", id: REMOTE_SID, tid: "t-0002", uuid: U2 }); };
    await sendOn(page, P95, FIRST, "cache-question");
    await pressOutside(page);
    await relayBack(page, "TESTHOST2", false);                           // the first's answer lost with the relay; it landed
    await send(REMOTE_SESSION);
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_FIRST] });
    await sendOn(page, "cache change", SECOND);
    await send({ ...LAG_NO_ID, id: REMOTE_SID });
    await pressOutside(page);
    const per: Record<string, number> = {};
    for (let i = 0; i < 16; i++) {
      const before = (await creates(page)).length;
      await send(REMOTE_SESSION);
      for (const c of (await creates(page)).slice(before)) {
        per[c.text] = (per[c.text] || 0) + 1;
        if (c.text === FIRST) await repeatAck(); else await send({ ...LAG_NO_ID, id: REMOTE_SID });
      }
    }
    steps.push(["re-posts per comment", per]);
    await commentOn(page, U2, P95); steps.push(["its passage", await seen(page)]);
    sameAsBase(steps, "relayLost");
  }, {}, "relayed", NO_CAPS);
});

test("in chromium: main mode: a lag-parked comment landed by the pusher while a second one on the message is out, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question");
    await send(LAG_NO_ID);                                               // the first parked
    await pressOutside(page);
    await sendOn(page, "cache change", SECOND);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] }); await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 });   // the pusher lands the first
    steps.push(["the pusher's ack of the first", await seen(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST, T_CACHE] }); await send({ type: "commentCreated", id: SID, tid: "t-0003", uuid: U2 });   // the second's own answer
    steps.push(["the second's ack", await seen(page)]);
    await send(SESSION); steps.push(["the next frame", await seen(page)]);
    sameAsBase(steps, "pusherLands");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: a comment opened from the keyboard over a sent dialog on another passage of its message keeps the old dialog, and Enter posts its words there, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST, "cache-question");
    await commentFromKeyboard(page, U2, "cache change"); steps.push(["keyboard over the sent dialog", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.press("Enter"); steps.push(["Enter there", await seen(page)]);
    sameAsBase(steps, "keyboard");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: one session's comment acknowledged while another session's create dialog holds typed words keeps that dialog, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await send(REMOTE_SESSION);                                          // the other host's session, in a tab beside this kernel's, after its relay's connect push
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await commentOn(page, U2, P95); await typeFresh(page, SECOND); steps.push(["typed in a dialog on this kernel's session", await seen(page)]);
    // a comment on the other host's session lands, on the same message: its frame, then its ack without the key
    await send({ type: "comments", id: REMOTE_SID, threads: [T_OLD, T_FIRST] }); await send({ type: "commentCreated", id: REMOTE_SID, tid: "t-0002", uuid: U2 });
    steps.push(["the other session's comment acknowledged", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage again", await seen(page)]);
    sameAsBase(steps, "twoSessions");
  }, {}, false, { ...NO_CAPS, beside: true });
});

test("in chromium: main mode: the working mark of a comment still out opens a thread popover for its placeholder, under the name its send gave it, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); await pressOutside(page); steps.push(["sent and closed", await seen(page)]);
    await page.evaluate(() => (Array.from(document.querySelectorAll("mark.cmt-hl")) as HTMLElement[]).find((x) => (x.dataset.tid || "").startsWith("pending:"))?.click());
    steps.push(["its working mark clicked", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.type(SECOND); await page.keyboard.press("Enter");
    steps.push(["a reply typed there", await seen(page)]);
    sameAsBase(steps, "markClick");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: an acknowledgment that beats its frame, adopted when the frame arrives, closes another session's create dialog and keeps its typed words for its passage, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await send(REMOTE_SESSION);                                          // the other host's session, in a tab beside this kernel's, after its relay's connect push
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); steps.push(["sent on this kernel's session", await seen(page)]);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 }); steps.push(["acknowledged before its frame", await seen(page)]);
    await pressOutside(page);
    await page.click('#tabs .tab[data-id="' + REMOTE_SID + '"]');       // the other session's tab
    await commentOn(page, U2, "cache change"); await typeFresh(page, SECOND); steps.push(["typed in a dialog on the other session", await seen(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] }); steps.push(["the first comment's frame", await seen(page)]);
    await commentOn(page, U2, "cache change"); steps.push(["that passage again", await seen(page)]);
    sameAsBase(steps, "parkedOtherSession");
  }, {}, false, { ...NO_CAPS, beside: true });
});

test("in chromium: main mode: an attachment's path goes into the open dialog's box and its draft, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page, send) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await commentOn(page, U2, P95); await typeFresh(page, FIRST); steps.push(["typed", await seen(page)]);
    await send({ type: "droppedPath", path: "/tmp/romp-drop/shot.png" }); steps.push(["a file's path arrives", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["its passage again", await seen(page)]);
    sameAsBase(steps, "droppedPath");
  }, {}, false, NO_CAPS);
});

// ── what main's warn does to the thread side, for the tests of main's warn beside an echo-mode dialog ─────────────────
/** What main's warn does to the thread side, whatever dialog is open: the frames posted since the last look, the real
 *  threads whose marks read as in flight, and the working marks of comments still out. */
async function markSide(page: any): Promise<unknown> {
  return { ...(await threadSide(page) as object), marks: await workingMarks(page) };
}

// ── the carry after main's give-up, and main's lines kept ────────────────────────────────────────────────────────────

test("in chromium: a main-mode comment the page gave up on, its words carried into an echo-mode dialog opened after the give-up, is cleared from that box by its late acknowledgment when unchanged, and kept with a toast when changed", { timeout: 300000 }, async (t) => {
  for (const [how, needle] of [["unchanged", P95], ["unchanged", "cache change"], ["changed", P95], ["reopened", "cache change"]] as [string, string][]) {
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST, "cache-question");                  // a kernel without the echo: main mode
      const mainId = (await creates(page))[0].createId;
      await pressOutside(page);
      await send(LAG_NO_ID);                                           // that kernel parks it, answering without the key: main's retry is armed
      await reconnect(page, true);                                       // it restarts as a build with the echo, the park lost with it
      if (how === "reopened") await commentOn(page, U2, needle);        // an echo-mode dialog open through the give-up, main's comment in its note
      // the kernel with the echo answers each of main's re-posts, naming main's own id
      const lag = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId };
      for (let i = 0; i < 14; i++) {                                     // every re-post answered busy, until main's retry gives up
        const before = (await creates(page)).length;
        await send(SESSION);
        if ((await creates(page)).length > before) await send(lag);
      }
      assert.ok((await toasts(page)).includes(GIVE_UP), "the precondition: main's retry gave up");
      if (how === "reopened") {
        assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[draftLead(null, "cache-question"), FIRST, "enabled"]],
          "the precondition: the open dialog's note offers the words main keeps in its draft");
        await pressOutside(page);                                        // closed without Bring it back
      }
      await commentOn(page, U2, needle);
      const b = await pop(page);
      assert.deepEqual([await echoOf(page), b.value, b.name, await heldNotes(page)], ["1", FIRST, "cache-question", []],
        "the precondition: the echo-mode dialog opened after the give-up took main's draft, the words and the typed name, into its box");
      if (how === "changed") await typeFresh(page, OTHER);
      // the kernel's pusher lands it after all: its frame, then main's late ack, naming main's own id
      await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
      await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });
      const p = await pop(page), saved = (await toasts(page)).includes(SAVED_AFTER_ALL);
      if (how === "changed") {
        assert.deepEqual([p.mode, p.value, p.name, saved], ["create", OTHER, "cache-question", true],
          "changed since, the box keeps what the person typed, and a toast says the comment was saved after all");
      } else {
        assert.deepEqual([p.mode, p.tid, saved], ["thread", "t-0002", false],
          "unchanged, the words and the typed name leave the box, and the open dialog adopts the landed thread, as main's late ack does");
        const before = (await creates(page)).length;
        await page.focus("#cmt-pop .cmt-input");
        await page.keyboard.press("Enter");
        assert.equal((await creates(page)).length, before, "and nothing posts the comment a second time");
      }
    }, {}, false, { local: null });
  }
});

test("in chromium: main mode: a comment opened from the keyboard on another message over an unsent dialog gets a dialog for its own message, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await commentOn(page, U2, P95); await typeFresh(page, FIRST); steps.push(["typed on a passage of one message", await seen(page)]);
    await commentFromKeyboard(page, U4, "response cache"); steps.push(["the keyboard's Comment on another message", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.type(SECOND); await page.keyboard.press("Enter"); steps.push(["typed and sent there", await seen(page)]);
    await commentOn(page, U2, P95); steps.push(["the first passage again", await seen(page)]);
    sameAsBase(steps, "keyboardOtherMessage");
  }, {}, false, NO_CAPS);
});

test("in chromium: main mode: a comment opened from the keyboard over an open thread gets a create dialog for its message, as the base did", { timeout: 120000 }, async (t) => {
  await openChat(t, async (page) => {
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await page.evaluate(() => (document.querySelector('mark.cmt-hl[data-tid="t-0001"]') as HTMLElement).click()); steps.push(["a thread opened from its mark", await seen(page)]);
    await commentFromKeyboard(page, U2, P95); steps.push(["the keyboard's Comment on a passage", await seen(page)]);
    await page.focus("#cmt-pop .cmt-input"); await page.keyboard.type(FIRST); await page.keyboard.press("Enter"); steps.push(["typed and sent", await seen(page)]);
    sameAsBase(steps, "keyboardOverThread");
  }, {}, false, NO_CAPS);
});

// ── the popover's size: only the person's own resize is saved ──────────────────────────────────────────────────────────
/** The size the popover's later opens take (romp:cmtPopSize), null while the person has chosen none. */
const storedSize = (page: any): Promise<string | null> => page.evaluate(() => localStorage.getItem("romp:cmtPopSize"));
/** The open popover's size in whole pixels, whether the observer took it for a resize (.sized), and whether it carries
 *  an inline size, which a create dialog opened at its content size has none of. */
const popSize = (page: any): Promise<{ w: number; h: number; sized: boolean; inline: boolean }> => page.evaluate(() => {
  const p = document.getElementById("cmt-pop")!;
  return { w: p.offsetWidth, h: p.offsetHeight, sized: p.classList.contains("sized"), inline: !!p.style.width };
});
/** The popover closed, then the first thread's opened from its mark ("fallback path", t-0001): its size, once the
 *  observer's first frames have run. */
async function threadSize(page: any): Promise<[number, number]> {
  await pressOutside(page);
  await page.click('mark.cmt-hl[data-tid="t-0001"]');
  await page.waitForSelector('#cmt-pop[data-mode="thread"]', { timeout: 5000 });
  await afterTwoFrames(page, "body");
  return page.evaluate(() => { const p = document.getElementById("cmt-pop")!; return [p.offsetWidth, p.offsetHeight]; });
}
// a thread's open geometry with nothing stored: 70% by 60% of the leg's 1100 by 760 window
const THREAD_OPEN: [number, number] = [770, 456];
/** The note's change just made, once the observer's frames have run: the dialog's size moved with it (`grew`, or else
 *  shrank), nothing was saved as the person's size, the observer did not take it for a resize, and the next thread
 *  opens at its own size. */
async function pageOwnSize(page: any, before: { h: number }, grew: boolean, what: string): Promise<void> {
  await afterTwoFrames(page, "body");
  const after = await popSize(page);
  assert.ok(grew ? after.h > before.h : after.h < before.h, "the precondition: " + what + " resized the dialog (" + before.h + " to " + after.h + ")");
  assert.deepEqual([await storedSize(page), after.sized], [null, false],
    what + " is the page's own change: its size is not saved as the one the person chose, nor taken for a resize");
  assert.deepEqual(await threadSize(page), THREAD_OPEN, "so the next thread opens at a thread's own size, after " + what);
}

test("in chromium: a note painted, cleared or repainted in an open comment dialog resizes it as the page's own change: that size is not saved as the person's, and the next thread opens at its own size, while the person's own resize is saved", { timeout: 300000 }, async (t) => {
  for (const remote of [false, "relayed"] as Remote[]) {
    const sid = remote ? REMOTE_SID : SID;
    // a second comment sent from a dialog whose note shows the first: the send clears the note
    await openChat(t, async (page) => {
      await sendOn(page, P95, FIRST);                                    // echo mode, then closed: its words wait in the note
      await pressOutside(page);
      await commentOn(page, U2, "cache change");
      assert.deepEqual((await heldNotes(page)).map((n) => n.words), [FIRST], "the precondition: the dialog's note shows the first comment");
      const before = await popSize(page);
      await typeFresh(page, SECOND);
      await page.keyboard.press("Enter");
      await pageOwnSize(page, before, false, "the send clearing the note");
      await commentOn(page, U2, "ten percent");
      assert.equal((await popSize(page)).inline, false, "and a create dialog opens at its content size, with no size of its own");
    }, {}, remote);
    // the first comment's acknowledgment takes its entry out of the note of a dialog open on the message
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST);
      const id = (await creates(page))[0].createId;
      await pressOutside(page);
      await commentOn(page, U2, "cache change");
      const before = await popSize(page);
      await send({ type: "comments", id: sid, threads: [T_OLD, T_FIRST] });
      await send({ type: "commentCreated", id: sid, tid: "t-0002", uuid: U2, createId: id });
      assert.deepEqual(await heldNotes(page), [], "the precondition: the acknowledgment took the entry out of the note");
      await pageOwnSize(page, before, false, "the acknowledgment clearing the note");
    }, {}, remote);
  }
  // main mode after a downgrade: a main-mode dialog shows its passage's echo-mode words in its note, and Dismiss drops them
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);
    await typeFresh(page, OTHER);                                        // echo mode: the passage's own draft
    await pressOutside(page);
    // the kernel restarts as a build without the echo: its connect push, without the marker, shows the downgrade
    await reconnect(page, false);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_RESPONSE] });
    await commentOn(page, U2, P95);
    assert.deepEqual([await echoOf(page), (await heldNotes(page)).map((n) => [n.lead, n.words, n.dismiss])], ["", [[draftLead(P95), OTHER, true]]],
      "the precondition: a main-mode dialog, its note showing the passage's echo-mode words with Dismiss");
    const before = await popSize(page);
    await page.click('#cmt-pop [data-act="cmtheldx"]');
    await pageOwnSize(page, before, false, "Dismiss dropping the note's entry in a main-mode dialog");
  });
  // on a touch screen, the reason under a waiting Bring it back goes as the box is emptied: the line hidden resizes the dialog
  await openChat(t, async (page, send) => {
    await refusedBesideTypedWords(page, send, OTHER);
    assert.equal((await heldNotes(page))[0]?.whyShown, true, "the precondition: the reason's line stands under the note");
    const before = await popSize(page);
    await page.fill("#cmt-pop .cmt-input", "");
    assert.equal((await heldNotes(page))[0]?.whyShown, false, "the precondition: the emptied box took the line away");
    await pageOwnSize(page, before, false, "the reason's line going");
  }, { hasTouch: true });
  // the person's own resize, a pull on the dialog's east edge while its note shows a comment, is saved, and the next
  // thread opens at the width they chose
  await openChat(t, async (page) => {
    await sendOn(page, P95, FIRST);
    await pressOutside(page);
    await commentOn(page, U2, "cache change");
    const r = await page.evaluate(() => { const b = document.getElementById("cmt-pop")!.getBoundingClientRect(); return { right: b.right, top: b.top, w: b.width, h: b.height }; });
    const y = Math.round(r.top + r.h / 2);
    await page.mouse.move(r.right - 3, y);
    await page.mouse.down();
    await page.mouse.move(r.right + 40, y, { steps: 4 });
    await page.mouse.move(r.right + 77, y, { steps: 4 });
    await page.mouse.up();
    await page.waitForFunction(() => localStorage.getItem("romp:cmtPopSize") !== null, null, { timeout: 5000 });
    const pulled = (await popSize(page)).w;
    assert.ok(Math.abs(pulled - (Math.round(r.w) + 80)) <= 2, "the pull widened the dialog by what the person moved (" + Math.round(r.w) + " to " + pulled + ")");
    const [w] = await threadSize(page);
    assert.ok(Math.abs(w - pulled) <= 2, "the person's size is saved: the next thread opens at the width they chose (" + w + ", chosen " + pulled + ")");
  });
  // a pull of the person's own and a repaint of the note in one frame, before the observer runs: the size the person
  // chose is still saved (the note's change is counted as the page's, the pull as theirs)
  await openChat(t, async (page) => {
    await sendOn(page, P95, FIRST);
    const id = (await creates(page))[0].createId;
    await pressOutside(page);
    await commentOn(page, U2, "cache change");
    await afterTwoFrames(page, "body");
    const pulled = await page.evaluate(([sid, id, uuid, threads]: [string, string, string, unknown[]]) => {
      const p = document.getElementById("cmt-pop")!;
      const w = p.offsetWidth + 60, h = p.offsetHeight;
      p.style.width = w + "px";                                          // what the native grip writes as the person pulls it
      p.style.height = h + "px";
      const deliver = (m: unknown) => window.dispatchEvent(new MessageEvent("message", { data: m }));
      deliver({ type: "comments", id: sid, threads });                   // in the same task: the first comment lands, and its
      deliver({ type: "commentCreated", id: sid, tid: "t-0002", uuid, createId: id });   // ack repaints the note
      return w;
    }, [SID, id, U2, [T_OLD, T_FIRST]]);
    assert.deepEqual(await heldNotes(page), [], "the precondition: the acknowledgment repainted the note in the pull's frame");
    await afterTwoFrames(page, "body");
    const stored = JSON.parse((await storedSize(page)) || "null");
    assert.ok(stored && Math.abs(stored.w * 1100 - pulled) <= 2, "the person's pull in that frame is saved as their size: " + JSON.stringify(stored) + " for " + pulled + "px");
  });
});

test("in chromium: a main-mode comment the page gave up on is settled in an echo-mode box by its late acknowledgment only when the words there are its own: words edited or typed over since in a main-mode dialog stay, with a toast while they sit in an open box", { timeout: 300000 }, async (t) => {
  // how main's draft came to differ from the comment's own words (FIRST under cache-question) before the give-up: edited
  // in the sent dialog, which main leaves editable; its typed name changed there; typed over in a second main-mode dialog
  // on the message; typed over and then brought back from the open echo-mode dialog's note; or edited, with the
  // echo-mode dialog closed when the acknowledgment comes
  for (const how of ["edited", "renamed", "typedOver", "broughtBack", "editedClosed"]) {
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST, "cache-question");                  // a kernel without the echo: main mode
      const mainId = (await creates(page))[0].createId;
      if (how === "edited" || how === "editedClosed") await typeFresh(page, OTHER);        // main's sent dialog: its box writes main's draft
      if (how === "renamed") await page.fill("#cmt-pop .cmt-name", "other-name");
      await pressOutside(page);
      if (how === "typedOver" || how === "broughtBack") {
        await commentOn(page, U2, "cache change");                       // a second main-mode dialog, opened on main's draft
        assert.equal((await pop(page)).value, FIRST, "the precondition: a second main-mode dialog on the message opens on main's draft");
        await typeFresh(page, OTHER);
        await pressOutside(page);
      }
      await send(LAG_NO_ID);                                           // that kernel parks it, answering without the key: main's retry is armed
      await reconnect(page, true);                                       // it restarts as a build with the echo, the park lost with it
      if (how === "broughtBack") await commentOn(page, U2, "cache change");   // an echo-mode dialog open through the give-up
      // the kernel with the echo answers each of main's re-posts, naming main's own id
      const lag = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId };
      for (let i = 0; i < 14; i++) {                                     // every re-post answered busy, until main's retry gives up
        const before = (await creates(page)).length;
        await send(SESSION);
        if ((await creates(page)).length > before) await send(lag);
      }
      assert.ok((await toasts(page)).includes(GIVE_UP), "the precondition: main's retry gave up");
      const words = how === "renamed" ? FIRST : OTHER, name = how === "renamed" ? "other-name" : "cache-question";
      if (how === "broughtBack") {
        assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[draftLead(null, name), words, "enabled"]],
          "the precondition: the open dialog's note offers the words typed over main's draft");
        await page.click('#cmt-pop [data-act="cmtheldback"]');
      } else await commentOn(page, U2, P95);                             // the echo-mode dialog takes main's draft into its box
      const b = await pop(page);
      assert.deepEqual([await echoOf(page), b.value, b.name], ["1", words, name], "the precondition: the echo-mode box holds main's draft, which is not the comment's own");
      if (how === "editedClosed") await pressOutside(page);
      // the kernel's pusher lands it after all: its frame, then main's late ack, naming main's own id
      await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
      await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });
      const saved = (await toasts(page)).includes(SAVED_AFTER_ALL);
      if (how === "editedClosed") {
        await commentOn(page, U2, P95);
        const p = await pop(page);
        assert.deepEqual([p.mode, p.value, p.name, saved], ["create", words, name, false],
          "with no dialog open the words stay in the passage's draft, and no toast, since they sit in no open box");
      } else {
        const p = await pop(page);
        assert.deepEqual([p.mode, await echoOf(page), p.value, p.name, saved], ["create", "1", words, name, true],
          "the words are not the comment's own, so they stay in the open box, which adopts nothing, and a toast says the comment was saved after all");
      }
      const before = (await creates(page)).length;
      await page.focus("#cmt-pop .cmt-input");
      await page.keyboard.press("Enter");
      assert.deepEqual((await creates(page)).slice(before).map((c) => c.text), [words], "and Enter posts those words as a comment of their own, the person's to send");
    }, {}, false, { local: null });
  }
});

// ── main mode beside an echo-mode dialog: what main's adoption and main's warn do to the thread, against the base ────
// A main-mode comment acknowledged, or a warn arriving, while an echo-mode dialog is open: on another session, whose
// host announced the echo, or on the same one, whose kernel restarted as a build with the echo, so that the first
// answer carrying the key made its host echo mode after the comment's send. The base has no echo mode, and there the
// open dialog is main's, which main's adoption swaps for the thread or closes and main's warn hands back. Here each
// skips that alone (the user's rules keep an echo-mode dialog's words where they are) and runs the rest of main's
// bookkeeping, so these tests play caps frames or an answer carrying the key, compare only the thread side with the
// base's run of the same steps (the frames posted, commentSeen among them, and the real threads whose marks read as in
// flight, where main's latch carried onto the thread shows; for the warn, also the working marks and the dialog's
// suggested name, which counts the session's threads), and then check that the echo-mode dialog and its words stayed as
// they were.

// the first comment's thread as the kernel's frame lists it with no reply owed and nothing running: its mark reads as
// in flight only while the send's gesture latch holds it
const T_FIRST_IDLE = { ...T_FIRST, replyOwed: false, state: "" };
/** What main's adoption does to the thread it adopts, whatever dialog is open: the frames the page posted since the
 *  last look (seen), and the real threads whose marks read as in flight. */
async function threadSide(page: any): Promise<unknown> {
  const s = await seen(page) as { posted: unknown };
  const busy = await page.evaluate(() => (Array.from(document.querySelectorAll("mark.cmt-hl.busy")) as HTMLElement[])
    .map((m) => m.dataset.tid || "").filter((x) => !x.startsWith("pending:")).sort());
  return { posted: s.posted, busy };
}

test("in chromium: main mode beside an echo-mode dialog: an acknowledgment that beats its frame, adopted when the frame arrives while an echo-mode dialog is open, carries its latch and marks its thread seen, as the base did, and leaves that dialog and its words as they are", { timeout: 180000 }, async (t) => {
  const kept: unknown[] = [];                                            // each case's dialog once the frames have come
  // an echo-mode dialog on another session: this kernel has no echo (main mode), the other host announced it
  await openChat(t, async (page, send) => {
    // the other host's session, in a tab beside this kernel's, after its relay's connect push, which carried the marker
    // (openChat's beside), and that host's caps frame announcing the echo, which its kernel sends after that push
    await send(REMOTE_SESSION);
    await hostCapsFrame(page, ECHO_CAPS);
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); steps.push(["sent on this kernel's session", await threadSide(page)]);
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2 }); steps.push(["acknowledged before its frame", await threadSide(page)]);
    await pressOutside(page);
    await page.click('#tabs .tab[data-id="' + REMOTE_SID + '"]');       // the other session's tab
    await commentOn(page, U2, "cache change"); await typeFresh(page, SECOND); steps.push(["typed in a dialog on the other session", await threadSide(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST_IDLE] }); steps.push(["the first comment's frame", await threadSide(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST_IDLE] }); steps.push(["its next frame", await threadSide(page)]);
    sameAsBase(steps, "parkedEchoOtherSession");
    const p = await pop(page);
    kept.push([await echoOf(page), p.value, p.quote]);
  }, {}, false, { local: OLDER_CAPS, remote: null, remotePush: true, beside: true });
  // an echo-mode dialog on the same session: this kernel restarted as a build with the echo, the comment was sent before
  // that connection's connect push, and its own acknowledgment, which beat its frame, is the first answer carrying the
  // key, which makes the host echo mode
  await openChat(t, async (page, send) => {
    await wsup(page);                                                    // the restart, its connect push still to come
    await lookFromHere(page);
    const steps: [string, unknown][] = [];
    await sendOn(page, P95, FIRST); steps.push(["sent", await threadSide(page)]);
    const mainId = (await creates(page)).slice(-1)[0].createId;
    await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId }); steps.push(["acknowledged before its frame, naming its id", await threadSide(page)]);
    await commentOn(page, U4, "response cache"); await typeFresh(page, SECOND); steps.push(["typed in a dialog on another message", await threadSide(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST_IDLE] }); steps.push(["the first comment's frame", await threadSide(page)]);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST_IDLE] }); steps.push(["its next frame", await threadSide(page)]);
    sameAsBase(steps, "parkedEchoSameSession");
    const p = await pop(page);
    kept.push([await echoOf(page), p.value, p.quote]);
  }, {}, false, { local: OLDER_CAPS });
  if (!kept.length) return;   // openChat skipped every page (no browser on this box): no page ran, so there is nothing to compare
  assert.deepEqual(kept, [["1", SECOND, "cache change"], ["1", SECOND, "response cache"]],
    "the echo-mode dialog stays as it was, its words in its box, on the other session and on the same one, where the base's adoption "
    + "closed the dialog open on the other session and swapped the one on the same session for the thread");
});

test("in chromium: main mode beside an echo-mode dialog: an acknowledgment after its frame, or before it, for a comment sent before its host's first answer carrying the key carries its latch and marks its thread seen, as the base did, with an echo-mode dialog open on its session on another message or on another passage of its own, and leaves that dialog and its words as they are", { timeout: 300000 }, async (t) => {
  const kept: unknown[] = [];                                            // each case's dialog once the frames have come
  for (const remote of [false, true]) for (const how of ["Idle", "Working", "SameMessage", "Parked"]) {
    const sid = remote ? REMOTE_SID : SID;
    await openChat(t, async (page, send) => {
      // the host restarts as a build with the echo: its connection opens again, and the comment is sent before that
      // connection's connect push, so the page still knows it as a kernel without the echo and the comment is main's;
      // that kernel parks it for transcript lag, and its lag refusal, the first answer carrying the key, makes the host
      // echo mode
      if (remote) await relayUp(page, "TESTHOST2"); else await wsup(page);
      await lookFromHere(page);
      const steps: [string, unknown][] = [];
      await sendOn(page, P95, FIRST, how === "Working" ? "cache-question" : undefined); steps.push(["sent", await threadSide(page)]);
      const mainId = (await creates(page)).slice(-1)[0].createId;
      await send({ type: "commentCreateFailed", id: sid, uuid: U2, transient: true, text: LAG, createId: mainId });
      steps.push(["its lag refusal, naming its id", await threadSide(page)]);
      // a relay's connect push, carrying the marker, before any of that host's comments frames (federation hands a
      // relay's frames on as they come, and the kernel sends its strip first; the page's own socket's queue can hand a
      // later strip on after them): nothing of echo mode's is out to post again
      if (remote) { await connectPush(page, "TESTHOST2", true); steps.push(["its connection's connect push, carrying the marker", await threadSide(page)]); }
      await pressOutside(page);
      const passage = how === "SameMessage" ? "cache change" : "response cache";
      await commentOn(page, how === "SameMessage" ? U2 : U4, passage);
      await typeFresh(page, SECOND); steps.push(["typed in a dialog on " + passage, await threadSide(page)]);
      // the kernel's pusher lands the parked comment: in the kernel's order its thread's frame and then its ack, naming
      // its id, or the ack first
      const frame = { type: "comments", id: sid, threads: [T_OLD, how === "Working" ? T_FIRST : T_FIRST_IDLE] };
      const ack = { type: "commentCreated", id: sid, tid: "t-0002", uuid: U2, createId: mainId };
      if (how === "Parked") {
        await send(ack); steps.push(["acknowledged before its frame", await threadSide(page)]);
        await send(frame); steps.push(["its frame", await threadSide(page)]);
      } else {
        await send(frame); steps.push(["its frame", await threadSide(page)]);
        await send(ack); steps.push(["its acknowledgment", await threadSide(page)]);
      }
      await send(frame); steps.push(["its next frame", await threadSide(page)]);
      const p = await pop(page);
      kept.push([how, remote, await echoOf(page), p.value, p.quote]);
      if (how === "Working") {
        await pressOutside(page);
        await page.evaluate(() => (document.querySelector('mark.cmt-hl[data-tid="t-0002"]') as HTMLElement).click());
        steps.push(["its thread opened from its mark", await threadSide(page)]);
      }
      sameAsBase(steps, "ackEcho" + how + (remote ? "Remote" : "Local"));
    }, {}, remote ? "relayed" : false, remote ? { remote: OLDER_CAPS } : { local: OLDER_CAPS });
  }
  if (!kept.length) return;   // openChat skipped every page (no browser on this box): no page ran, so there is nothing to compare
  assert.deepEqual(kept, [false, true].flatMap((remote) => ["Idle", "Working", "SameMessage", "Parked"].map((how) =>
    [how, remote, "1", SECOND, how === "SameMessage" ? "cache change" : "response cache"])),
    "the echo-mode dialog stays as it was, its words in its box, where the base's adoption swapped the dialog open on the session for "
    + "the thread");
});

test("in chromium: main mode beside an echo-mode dialog: a warn drops the working mark of the main-mode comment out on the dialog's message, as the base did, whether it is unrelated or that comment's own refusal's, and none on another message, and leaves that dialog and its words as they are", { timeout: 300000 }, async (t) => {
  const kept: unknown[] = [];                                            // each case's dialog at the end
  for (const remote of [false, true]) for (const how of ["SameMessage", "OwnRefusal", "OtherMessage"]) {
    const sid = remote ? REMOTE_SID : SID, session = remote ? REMOTE_SESSION : SESSION;
    await openChat(t, async (page, send) => {
      // the host restarts as a build with the echo: its connection opens again, and the comment is sent before that
      // connection's connect push, so it is main's; that kernel parks it for transcript lag, and its lag refusal, the
      // first answer carrying the key, makes the host echo mode; an echo-mode dialog then opens with words typed in it
      if (remote) await relayUp(page, "TESTHOST2"); else await wsup(page);
      await lookFromHere(page);
      const steps: [string, unknown][] = [];
      await sendOn(page, P95, FIRST, "cache-question"); steps.push(["sent", await markSide(page)]);
      const mainId = (await creates(page)).slice(-1)[0].createId;
      await send({ type: "commentCreateFailed", id: sid, uuid: U2, transient: true, text: LAG, createId: mainId });
      steps.push(["its lag refusal, naming its id", await markSide(page)]);
      // a relay's connect push, carrying the marker, before any of that host's session or comments frames, as in the
      // test above
      if (remote) { await connectPush(page, "TESTHOST2", true); steps.push(["its connection's connect push, carrying the marker", await markSide(page)]); }
      await pressOutside(page);
      const passage = how === "OtherMessage" ? "response cache" : "cache change";
      await commentOn(page, how === "OtherMessage" ? U4 : U2, passage);
      await typeFresh(page, SECOND);
      const name = async () => ({ ...(await markSide(page) as object), suggested: (await pop(page)).prefill });
      steps.push(["typed in a dialog on " + passage, await name()]);
      if (how === "OwnRefusal") {
        // the session frame's retry re-posts the parked comment, and that kernel, whose pusher dropped the park, refuses
        // the re-post: its warn, then its refusal naming its id
        await send(session); steps.push(["a session frame, its retry re-posting the comment", await name()]);
        await send({ type: "warn", text: REFUSAL }); steps.push(["its refusal's warn", await name()]);
        await send({ type: "commentCreateFailed", id: sid, uuid: U2, transient: false, text: REFUSAL, createId: mainId });
        steps.push(["its refusal, naming its id", await name()]);
      } else {
        await send({ type: "warn", text: "the clipboard could not be read" }); steps.push(["a warn that is not a comment's", await name()]);
        await send(session); steps.push(["a session frame, its retry re-posting the comment", await name()]);
        await send({ type: "comments", id: sid, threads: [T_OLD, T_FIRST] }); steps.push(["its frame", await markSide(page)]);
        await send({ type: "commentCreated", id: sid, tid: "t-0002", uuid: U2, createId: mainId }); steps.push(["its acknowledgment", await markSide(page)]);
      }
      sameAsBase(steps, "warnBeside" + how + (remote ? "Remote" : "Local"));
      const p = await pop(page);
      kept.push([how, remote, await echoOf(page), p.value, p.quote]);
    }, {}, remote ? "relayed" : false, remote ? { remote: OLDER_CAPS } : { local: OLDER_CAPS });
  }
  if (!kept.length) return;   // openChat skipped every page (no browser on this box): no page ran, so there is nothing to compare
  assert.deepEqual(kept, [false, true].flatMap((remote) => ["SameMessage", "OwnRefusal", "OtherMessage"].map((how) =>
    [how, remote, "1", SECOND, how === "OtherMessage" ? "response cache" : "cache change"])),
    "the echo-mode dialog stays as it was, its words in its box: the warn rebuilt it whole, as the base's warn rebuilt its main-mode dialog, "
    + "and handed nothing back, since nothing of its own was out");
});

// ── a given-up main-mode comment's own words, its typed name gone with main's prune ─────────────────────────────────────

test("in chromium: a main-mode comment the page gave up on, whose typed name main's prune deleted at a comments frame after the send, is still settled in an echo-mode box by its late acknowledgment: its own words, carried in or brought back, are cleared from that box, and nothing posts it twice", { timeout: 300000 }, async (t) => {
  for (const how of ["carried", "broughtBack"]) {
    await openChat(t, async (page, send) => {
      await sendOn(page, P95, FIRST, "cache-question");                  // a kernel without the echo: main mode, under a typed name
      const mainId = (await creates(page))[0].createId;
      await pressOutside(page);
      await send({ type: "comments", id: SID, threads: [T_OLD] });       // a comments frame: main's prune deletes main's typed-name draft
      await send(LAG_NO_ID);                                           // that kernel parks it, answering without the key: main's retry is armed
      await reconnect(page, true);                                       // it restarts as a build with the echo, the park lost with it
      if (how === "broughtBack") await commentOn(page, U2, "cache change");   // an echo-mode dialog open through the give-up
      // the kernel with the echo answers each of main's re-posts, naming main's own id
      const lag = { type: "commentCreateFailed", id: SID, uuid: U2, transient: true, text: LAG, createId: mainId };
      for (let i = 0; i < 14; i++) {                                     // every re-post answered busy, until main's retry gives up
        const before = (await creates(page)).length;
        await send(SESSION);
        if ((await creates(page)).length > before) await send(lag);
      }
      assert.ok((await toasts(page)).includes(GIVE_UP), "the precondition: main's retry gave up");
      if (how === "broughtBack") {
        assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[draftLead(null), FIRST, "enabled"]],
          "the precondition: the open dialog's note offers main's draft, the comment's own words with no typed name, which main's prune deleted");
        await page.click('#cmt-pop [data-act="cmtheldback"]');
      } else await commentOn(page, U2, P95);                             // the echo-mode dialog takes main's draft into its box
      const b = await pop(page);
      assert.deepEqual([await echoOf(page), b.value, b.name, await heldNotes(page)], ["1", FIRST, b.prefill, []],
        "the precondition: the echo-mode box holds the comment's own words, under the suggested name, main's draft holding no typed name");
      // the kernel's pusher lands it after all: its frame, then main's late ack, naming main's own id
      await send({ type: "comments", id: SID, threads: [T_OLD, T_FIRST] });
      await send({ type: "commentCreated", id: SID, tid: "t-0002", uuid: U2, createId: mainId });
      const p = await pop(page);
      assert.deepEqual([p.mode, p.tid, (await toasts(page)).includes(SAVED_AFTER_ALL)], ["thread", "t-0002", false],
        "the words are the comment's own, so they leave the box, which adopts the landed thread, with no toast, as main's late ack does");
      const before = (await creates(page)).length;
      await page.focus("#cmt-pop .cmt-input");
      await page.keyboard.press("Enter");
      assert.equal((await creates(page)).length, before, "and nothing posts the comment a second time");
    }, {}, false, { local: null });
  }
});

// ── the fail-safe: a comment caught by a downgrade is handed back ─────────────────────────────────────────────────────
// The user approved it on 2026-09-28, over matching main's handling in this case. When the page finds a connection
// without the echo (a connect push without the marker, a caps frame without the cap, or an answer without the key, on
// that host), each echo-mode comment still out on that host stops being handled: no retry, no re-post. Its dialog
// closes, and its words and typed name wait in the note, which says it may or may not have been saved because the
// kernel restarted as an older version, with Bring it back enabled at once. Each test counts every frame the page posts
// from the moment the downgrade is seen (or from earlier, where a post could slip out before it) and checks that none
// carries the comment, by its createId or its words, while it plays the events on which a page still handling the
// comment would post it: a lag refusal before the drop arming its retry, session frames after the downgrade, and
// another return of its connection.

const HANDED_BACK_P95 = "Your earlier comment on “p95 latency” may or may not have been saved, because the kernel restarted as an older version:";
const HANDED_BACK_TOAST_P95 = "Your comment on “p95 latency” may or may not have been saved, because the kernel restarted as an older version. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.";
/** How many frames the page has posted so far. */
const postCount = (page: any): Promise<number> => page.evaluate(() => (window as any).__posts.length);
/** Every frame the page has posted since `from` (their types, for the message), and those that carry the comment: a
 *  commentCreate of any id, or any frame that names its createId or holds its words. */
async function carrying(page: any, from: number, createId: string, words: string): Promise<{ all: string[]; hits: unknown[] }> {
  const frames: any[] = await page.evaluate((from: number) => (window as any).__posts.slice(from), from);
  return { all: frames.map((m) => m.type), hits: frames.filter((m) => m.type === "commentCreate" || JSON.stringify(m).includes(createId) || JSON.stringify(m).includes(words)) };
}
/** The comment's host: this kernel (the page's own socket) or the other host (its relay, on the relayed page). */
type Host = { remote: boolean; sid: string; session: unknown; name: string };
const HOSTS: Host[] = [{ remote: false, sid: SID, session: SESSION, name: "local" }, { remote: true, sid: REMOTE_SID, session: REMOTE_SESSION, name: "relayed" }];
/** The host's connection dropping and opening again, its connect push still to come. */
const reopened = (page: any, h: Host) => h.remote ? relayUp(page, "TESTHOST2") : wsup(page);
/** The host's connect push, carrying the marker or not. */
const pushOf = (page: any, h: Host, marked: boolean) => connectPush(page, h.remote ? "TESTHOST2" : "", marked);
/** The kernel's lag refusal of the comment, which parks it: echo mode's frame-keyed retry is armed. */
const lagOf = (send: (m: unknown) => Promise<void>, h: Host, createId: string) =>
  send({ type: "commentCreateFailed", id: h.sid, uuid: U2, createId, transient: true, text: LAG });
/** What the person sees once the comment `createId` (FIRST under the typed name "cache-question", on "p95 latency") was
 *  handed back, and what the page posts from `from` on: its dialog closed, its working mark gone, the toast; then two
 *  session frames of its session (a page still retrying it would post it on each) and, unless `again` is false, another
 *  return of its connection without the echo (a page re-posting it would post it there); then a dialog opened on its
 *  passage, main mode now, whose note holds the comment's words under the lead saying it may or may not have been
 *  saved, with Bring it back enabled and a dismiss; and Bring it back, which puts its words and typed name in the empty
 *  box. Nothing posted since `from` carries the comment. `other` names another comment whose own posts the caller
 *  expects in that window (a marked host's re-post and retry): a frame naming that id and holding neither this comment's
 *  id nor its words is left out. The dialog left open is that new one. */
async function handedBackAfter(page: any, send: (m: unknown) => Promise<void>, h: Host, createId: string, from: number, why: string, again = true, other?: string): Promise<void> {
  assert.deepEqual([(await pop(page)).open, await workingMarks(page), (await toasts(page)).includes(HANDED_BACK_TOAST_P95)], [false, [], true],
    why + ": its dialog is closed, its working mark gone, and a toast says it may or may not have been saved and where its words are");
  await send(h.session); await send(h.session);
  if (again) { await reopened(page, h); await pushOf(page, h, false); await send(h.session); }
  await commentOn(page, U2, P95);
  assert.deepEqual([await echoOf(page), (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])], ["", [[HANDED_BACK_P95, FIRST, "enabled", true]]],
    why + ": a dialog opened on its passage is main mode, and its note holds the comment's words under the lead saying it may or may not have "
    + "been saved because the kernel restarted as an older version, with Bring it back enabled and a dismiss");
  await page.click('#cmt-pop [data-act="cmtheldback"]');
  const q = await pop(page);
  assert.deepEqual([q.value, q.name, await heldNotes(page)], [FIRST, "cache-question", []], why + ": Bring it back puts its words and typed name, intact, in the empty box");
  const c = await carrying(page, from, createId, FIRST);
  const hits = c.hits.filter((m: any) => !(other && m.createId === other && !JSON.stringify(m).includes(createId) && !JSON.stringify(m).includes(FIRST)));
  assert.deepEqual(hits, [], why + ": the page posted nothing that carries the comment from the downgrade on (every frame posted: " + JSON.stringify(c.all) + ")");
}

/** A reopen whose romp:wsup the page did not hear: the socket's generation published and its flip frame queued, as the
 *  shim leaves them for a bundle that began listening after the shim fired romp:wsup (the bundle's fetch lets the
 *  socket's tasks run first), which a loaded page cannot be. A synthetic stand-in for that order: the page's state is the
 *  same, since the page keeps nothing from a romp:wsup it did not hear. */
const reopenUnheard = (page: any) => page.evaluate(() => { const w = window as any; w.__rompSockGen++; w.__legFlips.push(w.__rompSockGen); });
/** A reopen on a page whose shim published no generation (window.__rompSockGen absent): romp:wsup, and a socket-flip
 *  frame that carries one the page has nothing to compare with (`stamped`), or none, as the shim of a kernel from before
 *  the generation sends it (enqueue({type:"wsup"}) in the base's kernel.py). No shim publishes no generation and stamps
 *  its flip frame: that pairing is a synthetic input for the fail-safe. */
const reopenNoGen = (page: any, stamped = true) => page.evaluate((stamped: boolean) => {
  const w = window as any; delete w.__rompSockGen; w.__legWs = "open"; w.__rompLocalUp = true;
  window.dispatchEvent(new Event("romp:wsup"));
  window.dispatchEvent(new MessageEvent("message", { data: stamped ? { type: "wsup", gen: 1 } : { type: "wsup" } }));
}, stamped);
/** The oldest socket-flip frame still queued, handed on without the generation the shim stamps on it: a synthetic input
 *  for the fail-safe (this change's shim stamps every flip frame, and publishes the generation it stamps). */
const flipFrameNoGen = (page: any) => page.evaluate(() => {
  const w = window as any; w.__legFlips.shift();
  window.dispatchEvent(new MessageEvent("message", { data: { type: "wsup" } }));
});

test("in chromium: the fail-safe: a comment still out when its kernel comes back without the echo is handed back at that connection's connect push, local or relayed, sent before the push or between the open and the push, with its dialog open or closed: the dialog closes, the note says it may or may not have been saved and holds its words and typed name, Bring it back is enabled, and the page posts nothing more until the person sends it again", { timeout: 600000 }, async (t) => {
  for (const h of HOSTS) for (const when of ["before", "between"] as const) for (const dialog of ["open", "closed"] as const) {
    await openChat(t, async (page, send) => {
      const why = h.name + ", sent " + when + " the push, its dialog " + dialog;
      let first = "";
      if (when === "before") {
        first = await firstCreate(page, "cache-question");               // echo mode, sent on the connection that then drops
        await lagOf(send, h, first);                                     // that kernel parks it: its retry armed
        if (dialog === "closed") await pressOutside(page);
        await reopened(page, h);                                         // the connection comes back, on a kernel without the echo
      } else {
        await reopened(page, h);                                         // the connection comes back, on a kernel without the echo, its push still to come
        first = await firstCreate(page, "cache-question");               // sent in that moment: posted once, on that connection, as main's would be
        if (dialog === "closed") await pressOutside(page);
      }
      if (dialog === "closed")
        assert.equal((await pop(page)).open, false, "the precondition: its dialog closed while it was out");
      const from = await postCount(page);
      await pushOf(page, h, false);                                      // the connect push without the marker: the downgrade is seen
      await handedBackAfter(page, send, h, first, from, why);
      if (when === "before" && dialog === "open") {
        const n = (await creates(page)).length;
        await page.keyboard.press("Enter");                              // the person sends it again, from the main-mode dialog: main's handling
        const sent = (await creates(page)).slice(n);
        assert.deepEqual([sent.length, sent[0]?.text, sent[0]?.createId !== first], [1, FIRST, true],
          "the comment is saved only when the person sends it again: one post, a new gesture of main's handling");
      }
    }, {}, h.remote ? "relayed" : false);
  }
});

test("in chromium: the fail-safe: an answer without the key ahead of the connection's connect push hands back the comment still out, sent before the push or between the open and the push, local or relayed, with its dialog open or closed, and the page posts nothing more", { timeout: 600000 }, async (t) => {
  // The page's own socket: a reconnect's connect push can come after other frames of the new socket when the shim's
  // queue replaced a queued strip with a newer one and moved it to the end (a real order). A relay's first strip always
  // comes first (federation hands a relay's frames on in the order they arrive), so for a relay this is an input no
  // page gets, played to show the answer alone decides.
  for (const h of HOSTS) for (const when of ["before", "between"] as const) for (const dialog of ["open", "closed"] as const) {
    await openChat(t, async (page, send) => {
      const why = h.name + ", sent " + when + " the push, its dialog " + dialog;
      let first = "";
      if (when === "before") {
        first = await firstCreate(page, "cache-question");
        await lagOf(send, h, first);
        if (dialog === "closed") await pressOutside(page);
        await reopened(page, h);
      } else {
        await reopened(page, h);
        first = await firstCreate(page, "cache-question");
        if (dialog === "closed") await pressOutside(page);
      }
      const from = await postCount(page);
      if (when === "before") {
        // another page's comment on the message lands, and the kernel's pusher acknowledges it to every chat client
        // without the key: the answer that shows the page this kernel has no echo
        await send({ type: "comments", id: h.sid, threads: [T_OLD, T_OTHER_PAGE] });
        await send({ type: "commentCreated", id: h.sid, tid: "t-0009", uuid: U2 });
      } else await send({ type: "commentCreateFailed", id: h.sid, uuid: U2, transient: true, text: LAG });   // the comment's own lag refusal, without the key
      assert.deepEqual([(await pop(page)).open, await workingMarks(page)], [false, []], why + ": the answer hands it back at once, before any connect push");
      await pushOf(page, h, false);                                      // the connect push, moved behind the answer
      await handedBackAfter(page, send, h, first, from, why);
    }, {}, h.remote ? "relayed" : false);
  }
});

test("in chromium: the fail-safe: a caps frame without the cap hands back the comment still out on its host, local or relayed, with its dialog open or closed, and turns an unsent echo-mode dialog there main mode, the page posting nothing, played ahead of the connection's connect push, an order no kernel sends", { timeout: 600000 }, async (t) => {
  // A kernel sends its caps frame only in answer to a page's ready, after that connection's connect push (kernel.py
  // _send_caps), so on a kernel without the echo the connect push without the marker has already handed the comment back,
  // and turned an unsent dialog main mode, when its caps frame comes. Played here ahead of that push, a synthetic order,
  // to pin that a caps frame without the cap is evidence of no echo on its own: the local kernel's (the frame handler's
  // caps line) and a remote host's (the romp:hostCaps event federation dispatches for it, whose listener also turns an
  // unsent dialog main mode)
  const olderCaps = (page: any, send: (m: unknown) => Promise<void>, h: Host) =>
    h.remote ? hostCapsFrame(page, OLDER_CAPS) : send({ type: "caps", caps: OLDER_CAPS, viewsSeq: null });
  for (const h of HOSTS) for (const dialog of ["open", "closed"] as const) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await lagOf(send, h, first);                                       // that kernel parks it: its retry armed
      if (dialog === "closed") await pressOutside(page);
      await reopened(page, h);                                           // the connection comes back, its connect push still to come
      const from = await postCount(page);
      await olderCaps(page, send, h);                                    // the caps frame without the cap: the downgrade is seen
      await handedBackAfter(page, send, h, first, from, "a caps frame, " + h.name + ", its dialog " + dialog);
    }, {}, h.remote ? "relayed" : false);
  }
  for (const h of HOSTS) {
    await openChat(t, async (page, send) => {
      await commentOn(page, U2, P95);                                    // echo mode: the host announced the echo
      await page.fill("#cmt-pop .cmt-name", "draft-name");
      await typeFresh(page, OTHER);                                      // typed, not sent
      assert.equal(await echoOf(page), "1", "the precondition: an echo-mode dialog that has not sent");
      const from = await postCount(page);
      await olderCaps(page, send, h);
      const p = await pop(page);
      assert.deepEqual([p.open, p.mode, p.quote, await echoOf(page), p.value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])],
        [true, "create", P95, "", "", [[draftLead(P95, "draft-name"), OTHER, "enabled", true]]],
        h.name + ": a caps frame without the cap turns the unsent dialog main mode, its words and typed name waiting in its note with Bring it back");
      assert.deepEqual((await carrying(page, from, "no-create-id", OTHER)).hits, [], h.name + ": and nothing is posted");
    }, {}, h.remote ? "relayed" : false);
  }
});

test("in chromium: the fail-safe: a comment still out while the page's socket is closing is posted again neither at that socket's marked connect push nor at a session frame, and is handed back at the next socket's connect push without the echo, the page posting nothing", { timeout: 300000 }, async (t) => {
  // Socket 1 drops with the comment's answer; socket 2 opens on a kernel with the echo and starts closing (a close under
  // way, the page's netState still up) before its frames are handed on: the shim would send a post then first on the next
  // socket, whose kernel may be a build without the echo. Socket 3 then opens, without the echo (`next` false), or with it.
  for (const next of [false, true]) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await lagNack(send, first);                                        // parked: its retry armed
      await socketDown(page); await socketOpens(page);                   // socket 1 drops; socket 2 opens, its flip frame queued
      await socketClosing(page);                                         // and closes before its frames are handed on
      const from = await postCount(page);
      await flipFrame(page); await connectPush(page, "", true);          // socket 2's flip frame and its connect push, carrying the marker
      await send(SESSION);                                               // and a session frame of socket 2's
      assert.equal((await creates(page)).length, 1,
        "nothing is posted again while the page's socket is closing, at its marked push or its session frame: the shim would send it first on the next socket");
      await socketDown(page); await socketUp(page);                      // socket 2 closes; socket 3 opens
      await connectPush(page, "", next);
      if (!next) await handedBackAfter(page, send, HOSTS[0], first, from, "socket 3 without the echo");
      else {
        assert.deepEqual([(await creates(page)).map((c) => c.createId), (await pop(page)).send], [[first, first], "disabled busy"],
          "socket 3 with the echo: its connect push posts the comment again, once, and its dialog waits on it");
        const c = await carrying(page, from, first, FIRST);
        assert.equal(c.hits.length, 1, "that one post is all the page sent of it from socket 2's close on: " + JSON.stringify(c.all));
      }
    });
  }
});

test("in chromium: the fail-safe: a strip from a socket that opened and dropped before the shim handed any of its frames on, handed on once the next socket is open, is read as no connect push, whether or not the page heard that reopen, so it posts nothing and the open socket's own connect push decides", { timeout: 360000 }, async (t) => {
  // The page's own socket drops (socket 1); socket 2 opens and drops before the shim's queue has handed on its frames;
  // and socket 3 opens. The shim fires romp:wsup at each open and hands frames on in the order they came, a socket's
  // after its own socket-flip frame, so the queue then hands on socket 2's flip frame and connect push, and after them
  // socket 3's. Played on a page that heard socket 1's romp:wsup and on one that did not (reopenUnheard, a synthetic
  // stand-in for a bundle that began listening after the shim fired it: the page keeps nothing from an event it missed).
  for (const heard of [true, false]) for (const builds of ["echoThenOlder", "olderThenEcho"] as const) {
    await openChat(t, async (page, send) => {
      if (!heard) { await reopenUnheard(page); await flipFrame(page); }
      const first = await firstCreate(page, "cache-question");
      await lagNack(send, first);
      const from = await postCount(page);
      await socketDown(page); await socketOpens(page);                   // socket 1 drops; socket 2 opens, its flip frame queued
      await socketDown(page); await socketOpens(page);                   // socket 2 drops; socket 3 opens, its flip frame queued behind socket 2's frames
      await flipFrame(page); await connectPush(page, "", builds === "echoThenOlder");   // socket 2's flip frame and its strip, handed on now
      await send(SESSION);
      assert.deepEqual([(await creates(page)).length, (await pop(page)).send], [1, "disabled busy"],
        (heard ? "" : "unheard reopen: ") + "socket 2's strip, handed on once socket 3 is open, is socket 2's: it posts nothing again and hands nothing back, "
        + "whatever its marker says, since socket 3's kernel has shown nothing of its build");
      await flipFrame(page); await connectPush(page, "", builds === "olderThenEcho");   // socket 3's flip frame and its own connect push
      if (builds === "echoThenOlder") await handedBackAfter(page, send, HOSTS[0], first, from, (heard ? "" : "unheard reopen, ") + "socket 3 without the echo");
      else assert.deepEqual((await creates(page)).map((c) => c.createId), [first, first], "socket 3's own connect push, carrying the marker, posts it again, once");
    });
  }
});

test("in chromium: the fail-safe: after a socket-flip frame carrying no generation, or on a page whose shim published none, the next strip is read as one without the marker, whatever it carries, so the comments still out are handed back with nothing posted", { timeout: 300000 }, async (t) => {
  // Synthetic inputs for the fail-safe: "flipWithout", a published generation with a flip frame carrying none;
  // "nonePublished", no generation published with a stamped flip frame; neither pairing comes from a shim. "olderShim":
  // neither, as the shim of a kernel from before the generation sends them.
  for (const how of ["flipWithout", "nonePublished", "olderShim"]) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await lagNack(send, first);
      const from = await postCount(page);
      await socketDown(page);
      if (how === "flipWithout") { await socketOpens(page); await flipFrameNoGen(page); }
      else await reopenNoGen(page, how === "nonePublished");
      await connectPush(page, "", true);                                 // the next socket's strip, carrying the marker
      await handedBackAfter(page, send, HOSTS[0], first, from, how, false);
    });
  }
});

test("in chromium: the fail-safe: an echo-mode dialog that has not sent when its kernel comes back without the echo turns main mode, its words and typed name waiting in its note with Bring it back, the answer that showed it swapping nothing, and Comment then sends by main's handling", { timeout: 300000 }, async (t) => {
  for (const h of HOSTS) {
    await openChat(t, async (page, send) => {
      await commentOn(page, U2, P95);                                    // echo mode: the host announced the echo
      await page.fill("#cmt-pop .cmt-name", "draft-name");
      await typeFresh(page, OTHER);                                      // typed, not sent: its passage's own draft
      const from = await postCount(page);
      await reopened(page, h); await pushOf(page, h, false);             // the kernel restarts as a build without the echo
      let p = await pop(page);
      assert.deepEqual([p.open, p.mode, p.quote, await echoOf(page), p.value, (await heldNotes(page)).map((n) => [n.lead, n.words, n.back, n.dismiss])],
        [true, "create", P95, "", "", [[draftLead(P95, "draft-name"), OTHER, "enabled", true]]],
        h.name + ": the dialog stays open and turns main mode, rebuilt with main's box, empty, and the words and typed name typed in it wait in its "
        + "note with Bring it back and a dismiss, as in any main-mode dialog on that passage: no echo-mode comment is sent to a kernel without the echo");
      await page.click('#cmt-pop [data-act="cmtheldback"]');
      p = await pop(page);
      assert.deepEqual([p.value, p.name], [OTHER, "draft-name"], h.name + ": Bring it back puts them in main's box");
      assert.deepEqual((await carrying(page, from, "no-create-id", OTHER)).hits, [], h.name + ": and nothing was posted of them");
      await page.keyboard.press("Enter");
      p = await pop(page);
      assert.deepEqual([(await creates(page)).map((c) => [c.text, c.createId.length > 0]), p.readOnly, p.send], [[[OTHER, true]], false, "disabled busy"],
        h.name + ": Comment sends it by main's handling: main's frame, its box left editable while it is out, as main's is");
    }, {}, h.remote ? "relayed" : false);
  }
  // an answer without the key shows it: another page's comment on the same session acknowledged ahead of the new socket's
  // connect push. Main's handling of that acknowledgment runs beside the dialog while it is still echo mode, so it does
  // not swap the dialog for that thread, as it would a main-mode dialog; the dialog turns main mode after
  await openChat(t, async (page, send) => {
    await commentOn(page, U2, P95);
    await typeFresh(page, OTHER);
    await socketDown(page); await socketUp(page);
    await send({ type: "comments", id: SID, threads: [T_OLD, T_OTHER_PAGE] });
    await send({ type: "commentCreated", id: SID, tid: "t-0009", uuid: U2 });
    const p = await pop(page);
    assert.deepEqual([p.open, p.mode, p.quote, await echoOf(page), (await heldNotes(page)).map((n) => [n.lead, n.words])],
      [true, "create", P95, "", [[draftLead(P95), OTHER]]],
      "the dialog is neither swapped for the other page's thread nor closed, and turns main mode once that answer is handled, its words in its note");
    await connectPush(page, "", false);
    assert.deepEqual([(await pop(page)).open, await echoOf(page), (await creates(page)).length], [true, "", 0], "and the connect push after it changes nothing more");
  });
});

test("in chromium: the fail-safe: a later acknowledgment naming a handed-back comment takes its entry out of the note, and a refusal naming it leaves the entry as it is, neither posting anything", { timeout: 240000 }, async (t) => {
  // Only a kernel with the echo names a comment in its answers, and the page handed this one back because its kernel
  // came back without the echo, so no page gets these orders from one kernel: synthetic inputs, played to pin what the
  // page does with them
  for (const answer of ["landing", "refusal"] as const) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await pressOutside(page);
      await reconnect(page, false);                                      // handed back at the connect push without the marker
      await commentOn(page, U2, "cache change");
      assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), [[HANDED_BACK_P95, FIRST, "none"]],
        "the precondition: its entry shows on another passage of its message, with no Bring it back there");
      await pressOutside(page);
      const from = await postCount(page);
      if (answer === "landing") await ackFirst(page, send, first);
      else await refuse(send, first);
      await commentOn(page, U2, "cache change");
      assert.deepEqual((await heldNotes(page)).map((n) => [n.lead, n.words, n.back]), answer === "landing" ? [] : [[HANDED_BACK_P95, FIRST, "none"]],
        answer === "landing" ? "its landing takes its entry out of the note: its thread is on the page"
                             : "a refusal naming it leaves the entry as it was");
      assert.deepEqual((await carrying(page, from, first, FIRST)).hits, [], "and the page posts nothing that carries it");
    });
  }
});

test("in chromium: the fail-safe: a later acknowledgment naming a handed-back comment whose words were brought back into a main-mode box clears them there when unchanged, the dialog adopting its thread, keeps them with a toast when changed, and clears them from main's draft of the message when the dialog was closed", { timeout: 300000 }, async (t) => {
  // Synthetic, as above: only a kernel with the echo names a comment in its answers. After the hand-back every dialog on
  // the host is main mode, so Bring it back puts the words in main's box and main's draft of the message
  for (const how of ["unchanged", "changed", "closed"] as const) {
    await openChat(t, async (page, send) => {
      const first = await firstCreate(page, "cache-question");
      await pressOutside(page);
      await reconnect(page, false);                                      // handed back at the connect push without the marker
      await commentOn(page, U2, P95);
      await page.click('#cmt-pop [data-act="cmtheldback"]');
      let p = await pop(page);
      assert.deepEqual([await echoOf(page), p.value, p.name, await heldNotes(page)], ["", FIRST, "cache-question", []],
        "the precondition: Bring it back put the words and typed name in a main-mode box");
      if (how === "changed") await typeFresh(page, OTHER);
      if (how === "closed") await pressOutside(page);
      const from = await postCount(page);
      await ackFirst(page, send, first);                                 // its landing, naming it: its frame, then its acknowledgment
      p = await pop(page);
      if (how === "unchanged")
        assert.deepEqual([p.open, p.mode, p.tid, (await toasts(page)).includes(SAVED_AFTER_ALL)], [true, "thread", "t-0002", false],
          "the words brought back are the comment's own, unchanged: they leave the box, and the dialog adopts the comment's thread");
      else if (how === "changed")
        assert.deepEqual([p.open, p.mode, p.value, (await toasts(page)).includes(SAVED_AFTER_ALL)], [true, "create", OTHER, true],
          "changed since, the box keeps what the person typed, and a toast says the comment was saved after all");
      else assert.deepEqual([p.open, (await toasts(page)).includes(SAVED_AFTER_ALL)], [false, false], "with the dialog closed nothing shows");
      if (how !== "changed") {
        await pressOutside(page);
        await commentOn(page, U2, P95);
        p = await pop(page);
        assert.deepEqual([p.value, p.name, await heldNotes(page)], ["", p.prefill, []],
          "the words are gone from main's draft of the message: a dialog opened there again opens empty, so Comment cannot post them a second time");
      }
      assert.deepEqual((await carrying(page, from, first, FIRST)).hits, [], "and the page posts nothing that carries the comment");
    });
  }
});

test("in chromium: the fail-safe: a later acknowledgment naming a handed-back comment whose words were brought back into a main-mode box, then moved from main's draft into an echo-mode dialog on another passage of the message once the kernel shows the echo again, by the carry as it opens or by its Bring it back, clears them from that box when unchanged, the dialog adopting its thread, keeps them with a toast when changed, and clears them from that passage's draft when the dialog was closed", { timeout: 360000 }, async (t) => {
  // Synthetic, as above: only a kernel with the echo names a comment in its answers. After the hand-back Bring it back
  // puts the words in main's box and main's draft of the message; the kernel then comes back with the echo, and an
  // echo-mode dialog opened on a passage with no draft of its own takes main's draft, so the words move to that passage.
  // In the last case that passage has words of its own, so the carry takes nothing and main's draft waits in its note,
  // until the person clears the box and brings main's draft back there
  for (const how of ["unchanged", "changed", "closed", "brought"] as const) {
    await openChat(t, async (page, send) => {
      if (how === "brought") {                                           // words of its own on the other passage
        await commentOn(page, U2, "cache change");
        await typeFresh(page, OTHER);
        await pressOutside(page);
      }
      const first = await firstCreate(page, "cache-question");
      await pressOutside(page);
      await reconnect(page, false);                                      // handed back at the connect push without the marker
      await commentOn(page, U2, P95);
      await page.click('#cmt-pop [data-act="cmtheldback"]');             // into main's box and main's draft of the message
      assert.deepEqual([await echoOf(page), (await pop(page)).value], ["", FIRST], "the precondition: Bring it back put the words in a main-mode box");
      await pressOutside(page);
      await reconnect(page, true);                                       // the kernel comes back with the echo
      await commentOn(page, U2, "cache change");
      let p = await pop(page);
      if (how === "brought") {
        assert.deepEqual([await echoOf(page), p.value, (await heldNotes(page)).map((n) => [n.words, n.back])], ["1", OTHER, [[FIRST, "disabled"]]],
          "the precondition: the passage's own words are in the box, so the carry took nothing, and main's draft waits in the note");
        await page.fill("#cmt-pop .cmt-input", "");
        await page.click('#cmt-pop [data-act="cmtheldback"]');
        p = await pop(page);
      }
      assert.deepEqual([await echoOf(page), p.value, p.name, await heldNotes(page)], ["1", FIRST, "cache-question", []],
        "the precondition: an echo-mode dialog on another passage of the message took main's draft, the words and typed name brought back");
      if (how === "changed") await typeFresh(page, OTHER);
      if (how === "closed") await pressOutside(page);
      const from = await postCount(page);
      await ackFirst(page, send, first);                                 // its landing, naming it: its frame, then its acknowledgment
      p = await pop(page);
      if (how === "unchanged" || how === "brought")
        assert.deepEqual([p.open, p.mode, p.tid, (await toasts(page)).includes(SAVED_AFTER_ALL)], [true, "thread", "t-0002", false],
          "the words moved there are the comment's own, unchanged: they leave the box, and the dialog adopts the comment's thread (" + how + ")");
      else if (how === "changed")
        assert.deepEqual([p.open, p.mode, p.value, (await toasts(page)).includes(SAVED_AFTER_ALL)], [true, "create", OTHER, true],
          "changed since, the box keeps what the person typed, and a toast says the comment was saved after all");
      else assert.deepEqual([p.open, (await toasts(page)).includes(SAVED_AFTER_ALL)], [false, false], "with the dialog closed nothing shows");
      if (how !== "changed") {
        for (const on of ["cache change", P95]) {
          await commentOn(page, U2, on);
          p = await pop(page);
          assert.deepEqual([p.value, p.name, await heldNotes(page)], ["", p.prefill, []],
            "the words are gone from that passage's draft and from main's: a dialog opened on '" + on + "' opens empty, so Comment cannot post them a second time");
        }
      }
      assert.deepEqual((await carrying(page, from, first, FIRST)).hits, [], "and the page posts nothing that carries the comment");
    });
  }
});
