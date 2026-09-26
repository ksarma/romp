// A figure preview whose LINK is down never moves the transcript (T291, the user 2026-09-09). Two figures in a
// remote session's transcript re-attempted on every kernel push while the laptop's relay to their host was
// failing, and every attempt swapped the box between the one-line "fetching…" and the five-line failure note:
// the transcript above the reader moved by four lines, ten times a second, for the length of the streaming
// turn. previewFull is EXECUTED here over a minimal fake DOM and a stubbed fetch, driven through the same entry
// points render.ts calls: retryFailedPreviews on every kernel message, refreshSettledPreviews on a reconnect.
// Two rules under test: a link failure heals on the reconnect-class event only, never on a push; and an attempt
// never changes the box's child structure (only the note's words may change, and only when they do).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const PREVIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "preview.ts"), "utf8");
const SID = "TESTHOST:11111111-2222-4333-8444-000000000291";
const PATH = "/home/user/notes-api/plots/latency.png";

// ── a minimal DOM: what previewFull touches, nothing more ──────────────────────────────────────────────────
/** The pictures the page still holds, by address: a picture at one of them is complete once its src is set, as the browser
 *  has a picture it holds (loads() adds one; a case drops one, as a garbage collection may let the page's picture go). */
const held = new Set<string>();
class FakeEl {
  tag: string; attrs: Record<string, string> = {};
  children!: FakeEl[]; parent!: FakeEl | null;   // both edges are defined in the constructor, non-enumerable (ui/test-dom-shim.ts hideEdges):
                                              // a node inspects as its primitives, never as the tree it hangs in
  style: Record<string, string> = {}; _cls = new Set<string>(); _text = ""; isConnected = true;
  onclick: any = null; onerror: any = null; onload: any = null; onmousedown: any = null; onauxclick: any = null; title = ""; src = ""; alt = ""; loading = ""; decoding = "";
  listeners: Record<string, Function[]> = {};
  constructor(tag: string) {
    this.tag = tag;
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "parent", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);   // attrs, style, _cls, listeners and the onclick-style nulls hide too; a later `img.onerror = fn` keeps the attribute
  }
  get complete(): boolean { return this.tag === "img" && held.has(this.src); }
  get className(): string { return [...this._cls].join(" "); }
  set className(v: string) { this._cls = new Set(v.split(/\s+/).filter(Boolean)); }
  get classList() { const s = this._cls; return { add: (...c: string[]) => c.forEach((x) => s.add(x)), remove: (...c: string[]) => c.forEach((x) => s.delete(x)), contains: (c: string) => s.has(c), toggle: (c: string, on?: boolean) => { if (on === undefined) on = !s.has(c); on ? s.add(c) : s.delete(c); return on; } }; }
  get textContent(): string { return this.children.length ? this.children.map((c) => c.textContent).join("") : this._text; }
  set textContent(v: string) { this.children.forEach((c) => (c.parent = null)); this.children.length = 0; this._text = v; }
  appendChild(c: FakeEl): FakeEl { if (c.parent) c.parent.children = c.parent.children.filter((x) => x !== c); c.parent = this; this.children.push(c); return c; }
  append(...cs: FakeEl[]) { cs.forEach((c) => this.appendChild(c)); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((x) => x !== this); this.parent = null; }
  get firstElementChild(): FakeEl | null { return this.children[0] || null; }
  querySelector(sel: string): FakeEl | null { const cls = sel.replace(/^\./, ""); const walk = (n: FakeEl): FakeEl | null => { for (const c of n.children) { if (c._cls.has(cls)) return c; const d = walk(c); if (d) return d; } return null; }; return walk(this); }
  closest() { return null; }
  addEventListener(t: string, fn: Function) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  setAttribute(k: string, v: string) { this.attrs[k] = v; }
  /** the structure a height depends on: tags, classes, text, display — one string to compare across attempts */
  /** the classes that shape the box; path-retry-flash is a one-shot pulse animation (no size), left out */
  cls(): string { return [...this._cls].filter((c) => c !== "path-retry-flash").sort().join("."); }
  shape(): string { return `${this.tag}.${this.cls()}[${this.style.display || ""}]{${this.children.length ? this.children.map((c) => c.shape()).join(",") : JSON.stringify(this._text)}}`; }
  /** the structure without the words: only the elements that are there */
  bones(): string { return `${this.tag}.${this.cls()}(${this.children.map((c) => c.bones()).join(",")})`; }
}
(globalThis as any).document = { createElement: (t: string) => new FakeEl(t), addEventListener: () => {}, querySelectorAll: () => [] };   // no parked markdown images here (md-img-park.test.ts drives those)
(globalThis as any).location = { protocol: "http:", origin: "http://127.0.0.1:1" };   // canPreview: the web dashboard
(globalThis as any).window = (globalThis as any).window || {};

let fetchCalls = 0;
let fetchAnswer: () => Promise<any> = () => Promise.reject(new Error("no answer set"));
(globalThis as any).fetch = (_url: string, _init?: any) => { fetchCalls++; return fetchAnswer(); };
const failWith = (status: number, body: string) => () => Promise.resolve({ status, ok: false, headers: { get: () => null }, text: async () => body });
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const minted: FakeEl[] = [];
async function armedBox(file = PATH) {   // a path per test: a resolved picture is memoized by URL for the page life
  const P = await import("./preview");
  for (const b of minted) b.isConnected = false;   // an earlier test's box is a re-rendered turn's: the drains drop it without a fetch
  const box = P.previewFull(file, SID, true) as unknown as FakeEl;
  minted.push(box);
  assert.ok(box, "an image preview builds (verified: the kernel said the file exists)");
  // the happy path's <img> failed to load: the first failure, no message from the server
  const img = box.children.find((c) => c.tag === "img" && c._cls.has("path-full-img"))!;
  assert.ok(img && img.onerror, "the plain <img> carries the onerror that hands the box to the retry machinery");
  img.onerror();
  await sleep(10);   // failAfterBeat(0): no beat on the first attempt
  assert.notEqual(box.style.display, "none", "a verified box stays shown when its first attempt's picture fails to load; only an unverified box hides");
  return { P, box };
}

test("a LINK failure heals on the reconnect-class event only: pushes make no attempt, and the box's structure never moves", async () => {
  fetchCalls = 0;
  const { P, box } = await armedBox();
  const s0 = box.shape();
  assert.match(s0, /path-full-wait/, "the wait persona is up after the first failure");
  assert.match(s0, /connection dropped — retrying · tap to retry now/, "the first failure has no server text");
  // the per-message heal makes ONE attempt (the budget's, this is not yet known to be a link failure)…
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  P.retryFailedPreviews();
  await sleep(20);
  assert.equal(fetchCalls, 1, "the attempt fetched once");
  const boneAfterStart = box.bones();
  await sleep(450);   // the retry beat (MIN_RETRY_SPIN_MS) before the failure is shown
  const s1 = box.shape();
  assert.equal(box.bones(), boneAfterStart, "the failed attempt kept every element: one wait, one swirl, one note");
  assert.match(s1, /tunnel to TESTHOST is not answering; re-dialing — retries when the link is back · tap to retry now/, "the note carries the link's reason and says what will happen");
  // …and now it IS a link failure: a streaming session pushing many messages makes NO further attempt and
  // leaves the box byte-identical (no height change is possible without a DOM change → zero unitchange rows)
  const before = fetchCalls;
  for (let i = 0; i < 60; i++) { P.retryFailedPreviews(); if (i % 10 === 0) await sleep(5); }
  await sleep(450);
  assert.equal(fetchCalls, before, "sixty kernel messages, no attempt: the link's heal is the reconnect event");
  assert.equal(box.shape(), s1, "the box did not change at all under the pushes");
  // the reconnect-class event (romp:wsup / hostUp → refreshSettledPreviews) makes exactly one attempt…
  P.refreshSettledPreviews();
  await sleep(20);
  assert.equal(fetchCalls, before + 1, "one attempt per reconnect");
  assert.equal(box.bones(), boneAfterStart, "the running attempt kept the wait box and its note (no one-line 'fetching…' swap)");
  assert.equal(box.shape(), s1, "the note's words stayed while the attempt ran");
  await sleep(450);
  assert.equal(box.shape(), s1, "the same failure again: nothing changed, not even the words");
  // …and another reconnect after which the link works: the picture lands (the one legitimate layout change)
  fetchAnswer = () => Promise.resolve({ status: 200, ok: true, headers: { get: (h: string) => (h === "Content-Length" ? "3" : null) },
    body: { getReader: () => { let done = false; return { read: async () => done ? { done: true, value: undefined } : (done = true, { done: false, value: new Uint8Array([1, 2, 3]) }) }; } } });
  (globalThis as any).URL = (globalThis as any).URL || {};
  (globalThis as any).URL.createObjectURL = () => "blob:fake";
  (globalThis as any).URL.revokeObjectURL = () => {};
  (globalThis as any).Blob = class { constructor(public parts: any[], public opts: any) {} };
  P.refreshSettledPreviews();
  await sleep(30);
  assert.match(box.shape(), /img\.path-full-img/, "the image replaced the wait box once the bytes arrived");
});

test("a NON-link failure keeps the bounded per-message budget, and even those attempts never change the structure", async () => {
  fetchCalls = 0;
  const { P, box } = await armedBox("/home/user/notes-api/plots/throughput.png");
  fetchAnswer = failWith(404, "not found: the file is gone");
  for (let round = 0; round < 3; round++) {
    const calls = fetchCalls;
    const before = box.shape();
    P.retryFailedPreviews();
    await sleep(20);
    if (fetchCalls === calls) break;                  // the budget is spent: the settled chip took over
    assert.equal(box.shape(), before, "attempt " + round + ": the wait box kept its elements AND its words while fetching (no one-line 'fetching…' swap)");
    await sleep(450);
  }
  assert.match(box.shape(), /span\.path-full-retry\[\]\{"⚠ not found: the file is gone — tap to retry"\}/, "the budget spent on real verdicts settles on the tap chip");
  // the settled chip's ONE new-evidence heal (the 2026-08-18 rule): pushes inside one beat make one attempt, and
  // the chip keeps its shape while that attempt runs (the chip carries the words)
  const settledBones = box.bones();
  const calls = fetchCalls;
  for (let i = 0; i < 30; i++) { P.retryFailedPreviews(); if (i % 10 === 0) await sleep(5); }
  assert.equal(fetchCalls, calls + 1, "thirty pushes inside one beat: the one new-evidence heal, never one per push");
  assert.equal(box.bones(), settledBones, "the chip kept its elements while the heal ran");
  await sleep(450);
  // that heal's failure is the last budgeted attempt: the chip carries the retrying words for one more cycle…
  assert.match(box.shape(), /path-full-retry\[\]\{"not found: the file is gone — retrying · tap to retry now"\}/, "the chip carries the words: no new element, no swap");
  P.retryFailedPreviews();
  await sleep(470);
  assert.equal(fetchCalls, calls + 2, "…which the next push spends");
  assert.match(box.shape(), /span\.path-full-retry\[\]\{"⚠ not found: the file is gone — tap to retry"\}/, "the same verdict settles the chip again");
  const settled = box.shape();
  for (let i = 0; i < 30; i++) P.retryFailedPreviews();
  await sleep(450);
  assert.equal(fetchCalls, calls + 2, "the same verdict again is no new evidence: no further attempt");
  assert.equal(box.shape(), settled, "and the chip does not move");
  // a TAP re-arms the budget and brings the loading persona back at once: swirl + note, inside the same wait
  const chip = box.querySelector("path-full-retry")!;
  fetchAnswer = () => new Promise(() => {});          // an attempt that stays in flight
  chip.onclick({ stopPropagation() {}, currentTarget: chip });
  await sleep(20);
  assert.match(box.shape(), /span\.path-full-wait\[\]\{img\.path-load-spin\[\]\{""\},span\.path-load-note\[\]\{"fetching…"\}\}/, "a tap shows the swirl and the note: the chip is the give-up state only");
});

test("a link failure while the tunnel row never left up heals once on the recovery counter's hostUp (T291b)", async () => {
  // the kernel bumps the row's upSeq when a row that had misses answers again; federation's poll turns the bump into
  // hostUp; render.ts drains the settled previews on hostUp — so the parked box makes exactly one attempt
  fetchCalls = 0;
  const { P, box } = await armedBox("/home/user/notes-api/plots/queue-depth.png");
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  P.retryFailedPreviews(); await sleep(20); await sleep(450);   // the budget's one attempt names the link
  const parked = box.shape();
  assert.match(parked, /retries when the link is back/);
  const before = fetchCalls;
  for (let i = 0; i < 30; i++) P.retryFailedPreviews();
  await sleep(450);
  assert.equal(fetchCalls, before, "the status stayed up and pushes kept coming: no attempt");
  P.refreshSettledPreviews();                                    // what the bump's hostUp runs (render.ts)
  await sleep(20);
  assert.equal(fetchCalls, before + 1, "the counter's hostUp: exactly one attempt");
  assert.equal(box.shape(), parked, "the box did not move for it");
  const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");
  assert.match(FED, /if \(prev !== undefined && seq !== prev && !down\.has\(host\) && !recovered\.includes\(host\)\) recovered\.push\(host\);/, "a bump while up is a recovery");
  const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
  assert.match(RENDER, /if \(m\.type === "hostUp"\) \{ refreshSettledPreviews\(\); healPathImgs\(\); \}/, "hostUp drains the settled previews");
});

// ── an svg shown after the resumed fetch loads from its /file address, the one the first attempt used; any other image shows
// from its fetched bytes. The fetch itself (its progress, its errors, its retry rules) is the same for both ──
let blobs = 0;
function stubBlobs(): void {
  (globalThis as any).URL.createObjectURL = () => "blob:fake-" + blobs++;
  (globalThis as any).URL.revokeObjectURL = () => {};
  (globalThis as any).Blob = class { constructor(public parts: any[], public opts: any) {} };
}
/** A 200 whose body streams chunks of these sizes (Content-Length their sum); `hold`, when given, keeps the second chunk back until it resolves. */
const streams = (sizes: number[], hold?: Promise<void>) => () => Promise.resolve({ status: 200, ok: true,
  headers: { get: (h: string) => (h === "Content-Length" ? String(sizes.reduce((a, b) => a + b, 0)) : null) },
  body: { getReader: () => { let i = 0; return { read: async () => {
    if (i === 1 && hold) await hold;
    return i < sizes.length ? { done: false, value: new Uint8Array(sizes[i++]) } : { done: true, value: undefined };
  } }; } } });
const shownImg = (box: FakeEl) => box.children.find((c) => c.tag === "img" && c._cls.has("path-full-img"));
/** The preview's /file address: SID's host relays it, with the bare sid. */
const addressOf = (file: string) => "/remote/TESTHOST/file?path=" + encodeURIComponent(file) + "&sid=11111111-2222-4333-8444-000000000291";
/** A box whose picture at its own address is loading: the wait element with its one swirl and its note, and the picture hidden beside it. */
const WAITING = "span.path-full(span.path-full-wait(img.path-load-spin(),span.path-load-note()),img.path-full-img.path-img-loading())";
/** The swirls under a node. */
const spins = (n: FakeEl): number => n.children.reduce((k, c) => k + (c._cls.has("path-load-spin") ? 1 : 0) + spins(c), 0);
/** The pictures in a box. */
const pictures = (box: FakeEl): number => box.children.filter((c) => c._cls.has("path-full-img")).length;
/** A picture's load: the page holds it from here on, so a later picture at its address is complete once its src is set. */
const loads = (img: FakeEl): void => { held.add(img.src); img.onload(); };
/** A picture's failure to load: the page does not hold its address (it asked the network, and the request failed). */
const fails = (img: FakeEl): void => { held.delete(img.src); img.onerror(); };
/** The attempts a box has left, read as the fetches its per-message heals make until the chip when each answers a real verdict
 *  (a 404, which spends one attempt and refills nothing): the attempts left, plus the one that settles the chip. */
async function untilChip(P: any, box: FakeEl): Promise<number> {
  fetchAnswer = failWith(404, "not found: the file is gone");
  const c0 = fetchCalls;
  for (let i = 0; i < 8 && !box.querySelector("path-full-retry"); i++) { P.retryFailedPreviews(); await sleep(460); }
  assert.ok(box.querySelector("path-full-retry"), "the chip, the attempts spent on real verdicts");
  return fetchCalls - c0;
}
/** A fresh box for the same mention, as a re-render of the turn builds it (the earlier boxes leave the document). */
async function rerendered(file: string): Promise<FakeEl> {
  const P = await import("./preview");
  for (const b of minted) b.isConnected = false;
  const box = P.previewFull(file, SID, true) as unknown as FakeEl;
  minted.push(box);
  return box;
}

test("an svg after a retry: the resumed fetch keeps its error words and its progress, then the picture loads from the /file address the first attempt used, beside the swirl and with no progress in the note until its load; a re-render shows the same address with no fetch, and with no cue once the picture has loaded and the page holds it", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/diagram.svg";
  const minted0 = blobs;
  const { P, box } = await armedBox(file);
  // a link failure first: classified and worded as for any image
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  P.retryFailedPreviews(); await sleep(20); await sleep(450);
  assert.match(box.shape(), /tunnel to TESTHOST is not answering; re-dialing . retries when the link is back · tap to retry now/, "the server's words and the link's plan");
  // the link is back: the fetch narrates its progress while the second chunk is held
  let release!: () => void;
  fetchAnswer = streams([1200000, 1800000], new Promise<void>((r) => { release = r; }));
  P.refreshSettledPreviews();
  await sleep(20);
  assert.equal(box.querySelector("path-load-note")?.textContent, "fetching… 1.2 MB of 3.0 MB", "the progress, as for any image");
  release();
  await sleep(30);
  assert.equal(fetchCalls, 2, "the two managed attempts, nothing more");
  const img = shownImg(box);
  assert.ok(img, "the picture is in the box");
  assert.ok(!img!.src.startsWith("blob:"), "the svg's picture is its /file address, not an object URL; got " + img!.src);
  assert.equal(img!.src, addressOf(file), "the /file address the first attempt used");
  // the picture's own load is a wait of its own: the wait element and its one swirl stay, the picture beside them until it loads
  assert.equal(box.bones(), WAITING, "the swirl holds the spot beside the picture, which waits hidden (path-img-loading)");
  assert.equal(box.querySelector("path-load-note")!.textContent, "", "the note carries no transfer progress while the picture loads");
  assert.equal(spins(box), 1, "one swirl in the box");
  const early = await rerendered(file);
  assert.equal(early.bones(), WAITING, "a re-render before the picture has loaded waits the same way");
  assert.equal(shownImg(early)?.src, addressOf(file), "at the same address");
  loads(shownImg(early)!);
  assert.equal(early.bones(), "span.path-full(img.path-full-img())", "the picture's load: the wait element goes and the picture shows alone");
  const again = await rerendered(file);
  assert.equal(again.bones(), "span.path-full(img.path-full-img())", "a re-render of a picture that has loaded puts it in the box with no cue (the page still holds it: complete once its src is set)");
  assert.equal(shownImg(again)?.src, addressOf(file), "the re-render's picture: the same address");
  assert.equal(fetchCalls, 2, "and no fetch for either re-render");
  assert.equal(blobs, minted0, "no object URL was made for the svg on any of these roads");
});

test("a re-render keys its cue on the picture itself: while the page holds the loaded picture, the re-render's is complete once its src is set and goes in with no cue; once the page has let it go (as a garbage collection may), the re-render's picture is not complete and waits beside the one swirl until its load, which leaves it alone in the box; no re-render makes a managed fetch", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/queue-depth.svg";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  loads(shownImg(box)!);                                  // the picture loaded: the page holds it
  const kept = await rerendered(file);
  assert.equal(kept.bones(), "span.path-full(img.path-full-img())", "while the page holds the picture, the re-render's is complete once its src is set: no cue");
  held.delete(addressOf(file));                           // the page let the picture go
  const later = await rerendered(file);
  assert.equal(later.bones(), WAITING, "once the page has let the picture go, the re-render's picture is not complete once its src is set: it waits beside the swirl");
  assert.equal(spins(later), 1, "one swirl");
  assert.equal(later.querySelector("path-load-note")!.textContent, "", "the note carries nothing while the picture loads");
  assert.equal(shownImg(later)?.src, addressOf(file), "at its /file address");
  loads(shownImg(later)!);
  assert.equal(later.bones(), "span.path-full(img.path-full-img())", "its load leaves the picture alone in the box");
  assert.equal(fetchCalls, 1, "the one managed fetch: the re-renders load from the memo's address");
});

test("a png after a retry shows from the object URL of its fetched bytes, and so does its re-render, each the plain <img> (the control for the svg case above)", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/p99-latency.png";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const shown = shownImg(box)!;
  const src = shown?.src || "";
  assert.match(src, /^blob:fake-\d+$/, "a png shows from its bytes; got " + src);
  assert.equal(shown.onerror, null, "a picture shown from its fetched bytes carries no failure handler");
  assert.equal(shown.onload, null, "and no load handler");
  assert.equal(box.bones(), "span.path-full(img.path-full-img())", "the plain <img> alone: no swirl, no path-img-loading");
  const again = await rerendered(file);
  assert.equal(shownImg(again)?.src, src, "the re-render reads the same object URL");
  assert.equal(shownImg(again)!.onerror, null, "the re-render's picture carries no failure handler either");
  assert.equal(shownImg(again)!.onload, null, "and no load handler");
  assert.equal(again.bones(), "span.path-full(img.path-full-img())", "the plain <img> alone");
  assert.equal(fetchCalls, 1, "one managed fetch in all");
});

test("an svg picture whose load fails after the resumed fetch: no broken picture stays, the wait box says what the first attempt's does, and the next attempt runs the managed fetch again; when every fetch succeeds and every picture fails, the fetches number the bound the budget gives and the box settles on the chip", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/error-budget.svg";
  const minted0 = blobs;
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const img = shownImg(box)!;
  assert.equal(img?.src, addressOf(file), "the picture shows from its /file address; got " + img?.src);
  assert.equal(typeof img.onerror, "function", "and carries a failure handler, as the first attempt's <img> does");
  const waits: string[] = [];                             // the box while each picture loads: its bones and its swirls
  const waitOf = (): string => box.bones() + ", swirls " + spins(box);
  waits.push(waitOf());
  img.onerror();
  await sleep(10);
  assert.notEqual(box.style.display, "none", "the verified box stays shown when its picture fails to load after the resumed fetch; only an unverified box hides");
  assert.equal(shownImg(box), undefined, "no broken picture stays in the box");
  assert.match(box.shape(), /span\.path-load-note\[\]\{"connection dropped . retrying · tap to retry now"\}/, "the first attempt's words (no byte count: the bytes were not kept)");
  P.retryFailedPreviews();
  await sleep(40);
  assert.equal(fetchCalls, 2, "the next attempt runs the managed fetch again: the memo entry went with the picture's failure");
  const retried = shownImg(box);
  assert.ok(retried && retried !== img, "and its landing built a fresh picture");
  assert.notEqual(box.style.display, "none", "the heal leaves a verified box shown");
  assert.equal(retried!.src, addressOf(file), "at the same address");
  assert.equal(typeof retried!.onerror, "function", "the new picture carries its failure handler, as the first one does");
  waits.push(waitOf());
  // every fetch succeeds and every picture fails, over the twenty kernel messages of this loop (22 in all, with the two above): a
  // fetch that ends in a picture's failure does not refill the budget, so the attempts run out, the settled chip's heal makes its one
  // attempt, and the box settles
  retried!.onerror();
  await sleep(10);
  const roads: string[] = [];
  for (let i = 0; i < 20; i++) {
    P.retryFailedPreviews();
    await sleep(40);
    const cur = shownImg(box);
    if (cur) { roads.push(cur.src); waits.push(waitOf()); cur.onerror(); await sleep(10); }
  }
  assert.ok(roads.length > 0 && roads.every((u) => u === addressOf(file)), "every picture the heals built is the /file address: " + roads.join(" | "));
  assert.deepEqual(waits, Array(6).fill(WAITING + ", swirls 1"), "each of the six pictures loads beside the one swirl, the settled chip's heal included, whose chip gives way to the swirl while its picture loads: " + waits.join(" | "));
  assert.equal(blobs, minted0, "and no object URL was made for the svg");
  assert.equal(fetchCalls, 6, "six managed fetches over 22 kernel messages, one on each of the first six, the bound the budget of three gives: the first, whose progress refilled the budget before any picture had failed; three budgeted attempts; and the settled chip's one new-evidence heal with the attempt it leaves");
  assert.match(box.shape(), /span\.path-full-retry\[\]\{"⚠ still unavailable . tap to retry"\}/, "the chip, once the attempts are spent");
  const settled = box.shape();
  for (let i = 0; i < 30; i++) P.retryFailedPreviews();
  await sleep(40);
  assert.equal(box.shape(), settled, "the same failure again is no new evidence: the chip stays");
  assert.equal(fetchCalls, 6, "and no further fetch");
});

test("a picture shown at once by a re-render (the page still held it), then failing to load (the page had let it go and its request failed): its failure drops the memo entry and takes the address out of loadedOnce, so a re-render's first attempt at the address shows its cue again, and the next attempt runs the managed fetch, whose picture, which the page no longer holds, waits beside the one swirl", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/ingest-rate.svg";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  assert.equal(typeof shownImg(box)?.onload, "function", "the picture at the preview's own address carries its load handler");
  loads(shownImg(box)!);                                  // the picture loaded: the page holds it, and its address joined loadedOnce
  const again = await rerendered(file);
  assert.equal(again.bones(), "span.path-full(img.path-full-img())", "a re-render puts the loaded picture in the box with no cue (the page still holds it: complete once its src is set)");
  const calls = fetchCalls;
  fails(shownImg(again)!);                                // the page let the picture go, and the re-render's picture fails to load
  await sleep(10);
  // a re-render's first attempt at the address (the memo entry is gone, so it is the plain <img> road): the first attempt's cue
  const first = P.previewFull(file, SID, true) as unknown as FakeEl;
  minted.push(first);
  assert.equal(spins(first), 1, "a re-render's first attempt shows the cue again: the failure took the address out of loadedOnce");
  assert.equal(fetchCalls, calls, "the first attempt's plain <img> makes no managed fetch");
  first.isConnected = false;                              // that turn is re-rendered again: its box leaves the document
  P.retryFailedPreviews();
  await sleep(40);
  assert.equal(fetchCalls, calls + 1, "the next attempt runs the managed fetch: the memo entry went with the picture's failure");
  assert.equal(again.bones(), WAITING, "and its picture waits beside the swirl: the page no longer holds it, so it is not complete once its src is set");
  assert.equal(spins(again), 1, "one swirl");
  assert.equal(shownImg(again)?.src, addressOf(file), "at its /file address");
});

test("the memo's eviction releases object URLs only: an evicted svg entry, which holds its /file address, releases nothing; an evicted png entry releases its object URL", async () => {
  stubBlobs();
  const revoked: string[] = [];
  (globalThis as any).URL.revokeObjectURL = (u: string) => { revoked.push(u); };
  const resolve = async (file: string): Promise<string> => {
    const { P, box } = await armedBox(file);
    fetchAnswer = streams([3]);
    P.retryFailedPreviews();
    await sleep(20);
    const src = shownImg(box)?.src || "";
    assert.ok(src, file + ": the picture shows");
    return src;
  };
  // the memo keeps 24 entries: after the svg and twenty-five pngs, the svg's entry and the first png's are gone, whatever came before
  const svgSrc = await resolve("/home/user/notes-api/plots/cache-hits.svg");
  const pngSrcs: string[] = [];
  for (let i = 0; i < 25; i++) pngSrcs.push(await resolve("/home/user/notes-api/plots/shard-" + i + ".png"));
  assert.ok(!revoked.includes(svgSrc), "the svg's entry released nothing: " + svgSrc + " in " + revoked.join(" | "));
  assert.ok(revoked.includes(pngSrcs[0]), "the first png's entry released its object URL: " + pngSrcs[0] + " in " + revoked.join(" | "));
  assert.ok(revoked.every((u) => u.startsWith("blob:")), "only object URLs are released: " + revoked.join(" | "));
});

test("an unverified svg preview whose picture fails to load after the resumed fetch hides its box, as it does when the first attempt's picture fails, and then takes the same failure path: registered for the heal, whose managed fetch lands a fresh picture and shows the box again", async () => {
  stubBlobs();
  fetchCalls = 0;
  const P = await import("./preview");
  for (const b of minted) b.isConnected = false;
  const file = "/home/user/notes-api/plots/slo-burn.svg";
  const box = P.previewFull(file, SID, false) as unknown as FakeEl;   // unverified: no word from the kernel that the file exists
  minted.push(box);
  shownImg(box)!.onerror();                                           // the first attempt's picture failed to load
  await sleep(10);
  assert.equal(box.style.display, "none", "the first attempt's failure hides the unverified box");
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const img = shownImg(box)!;
  assert.equal(img?.src, addressOf(file), "the picture shows from its /file address; got " + img?.src);
  assert.equal(box.style.display, "", "the box shows with its picture");
  img.onerror();
  assert.equal(box.style.display, "none", "the unverified box hides when its picture fails to load after the resumed fetch, as when the first attempt's does");
  await sleep(10);
  assert.equal(shownImg(box), undefined, "no broken picture stays in the box");
  assert.match(box.shape(), /span\.path-load-note\[\]\{"connection dropped . retrying · tap to retry now"\}/, "then the first attempt's failure path: the wait box and its words");
  const calls = fetchCalls;
  P.retryFailedPreviews();
  await sleep(40);
  assert.equal(fetchCalls, calls + 1, "the heal runs the managed fetch again, within the budget (the memo entry went with the picture's failure)");
  const again = shownImg(box);
  assert.ok(again && again !== img, "registered for the heal, whose landing built a fresh picture");
  assert.equal(again!.src, addressOf(file), "at the same address");
  assert.equal(box.style.display, "", "and the box shows again, the swirl beside the loading picture (the fetch landing's unhide)");
});

test("an upper-case .SVG path is an svg too: after the resumed fetch its picture is its /file address", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/TOPOLOGY.SVG";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const src = shownImg(box)?.src || "";
  assert.equal(src, addressOf(file), "the svg's picture is its /file address, not an object URL; got " + src);
  assert.equal(fetchCalls, 1, "after the one managed fetch");
});

test("a pinned mention's svg picture after the resumed fetch is the first attempt's address, its pin included, with the failure handler of a picture at that address", async () => {
  stubBlobs();
  fetchCalls = 0;
  const P = await import("./preview");
  for (const b of minted) b.isConnected = false;
  const file = "/home/user/notes-api/plots/queue-lag.svg";
  const box = P.previewFull(file, SID, true, "a1b2c3d4e5f60718") as unknown as FakeEl;   // the message's mention pin (synthetic)
  minted.push(box);
  const first = shownImg(box)!;
  assert.equal(first.src, addressOf(file) + "&pin=a1b2c3d4e5f60718", "the first attempt's address carries the pin");
  first.onerror();
  await sleep(10);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const img = shownImg(box)!;
  assert.equal(img?.src, first.src, "the picture after the resumed fetch is the first attempt's address, its pin included; got " + img?.src);
  assert.equal(typeof img.onerror, "function", "and carries the failure handler of a picture at the preview's own address");
});

test("after a memo'd success, a picture that fails to load runs the managed fetch again: a relay's 502 then carries the relay's words and waits for the reconnect-class heal, spending none of the budget, while the picture's own failure spends one, as a first attempt's does", async () => {
  stubBlobs();
  // a picture failure after the resumed fetch, then a relay's 502 on the fetch the next message runs
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/tail-latency.svg";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  shownImg(box)!.onerror();
  await sleep(10);
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  P.retryFailedPreviews();
  await sleep(20);
  assert.equal(fetchCalls, 2, "the picture's failure runs the managed fetch again on the next message (the memo entry went with it)");
  await sleep(450);
  assert.match(box.shape(), /span\.path-load-note\[\]\{"tunnel to TESTHOST is not answering; re-dialing . retries when the link is back · tap to retry now"\}/, "the note carries the relay's words and says what will happen");
  for (let i = 0; i < 60; i++) { P.retryFailedPreviews(); if (i % 10 === 0) await sleep(5); }
  await sleep(450);
  assert.equal(fetchCalls, 2, "sixty kernel messages, no fetch: the link's heal is the reconnect event");
  fetchAnswer = failWith(404, "not found: the file is gone");
  P.refreshSettledPreviews();
  await sleep(460);
  assert.equal(fetchCalls, 3, "one fetch on the reconnect");
  const after502 = 1 + await untilChip(P, box);
  // the controls: the attempts left after the picture's failure alone, and after a first attempt's failure alone
  const { box: picOnly } = await armedBox("/home/user/notes-api/plots/heap-growth.svg");
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  shownImg(picOnly)!.onerror();
  await sleep(10);
  const afterPicture = await untilChip(P, picOnly);
  const { box: firstOnly } = await armedBox("/home/user/notes-api/plots/gc-pauses.svg");
  const afterFirst = await untilChip(P, firstOnly);
  assert.equal(after502, afterPicture, "the 502 attempt spent none of the budget: the attempts left after it (the reconnect's fetch counted) equal those left after the picture's failure: " + after502 + " against " + afterPicture);
  assert.equal(afterPicture, afterFirst, "the picture's own failure spends one attempt, as a first attempt's does: " + afterPicture + " fetches to the chip against " + afterFirst);
});

test("after two builds within one load's life, the replaced picture's failure changes nothing, and one failed request both pictures share spends one attempt: the failed loads the budget absorbs equal a single build's", async () => {
  stubBlobs();
  // a chip settled on real verdicts, its new-evidence heal landing a picture (img1), and with `two` a reconnect heal during
  // img1's load building a second from the memo (img2); then the pictures fail until the chip, the first failure fired on
  // every picture sharing the request (`both`) or on the current one alone; the count is the failed loads before the chip
  const twoPictures = async (file: string) => {
    const { P, box } = await armedBox(file);
    await untilChip(P, box);
    fetchAnswer = streams([3]);
    P.retryFailedPreviews();
    await sleep(40);
    const img1 = shownImg(box)!;
    const wait = box.firstElementChild!;
    P.refreshSettledPreviews();
    await sleep(10);
    const img2 = shownImg(box)!;
    assert.equal(img1.src, addressOf(file), file + ": the chip's heal lands the picture at its /file address");
    assert.equal(img2?.src, addressOf(file), file + ": and the reconnect heal's picture, from the memo, is the same address");
    assert.equal(box.firstElementChild, wait, file + ": the box keeps its wait element across the build from the memo");
    assert.equal(spins(box), 1, file + ": one swirl");
    assert.equal(wait.onclick, null, file + ": and while the picture loads the wait element carries no tap handler");
    return { P, box, img1, img2 };
  };
  const absorbed = async (file: string, two: boolean, both: boolean): Promise<number> => {
    let P: any, box: FakeEl, shared: FakeEl[];
    if (two) {
      const s = await twoPictures(file);
      ({ P, box } = s);
      assert.ok(s.img2 && s.img2 !== s.img1, file + ": the reconnect heal built a second picture");
      assert.equal(pictures(box), 1, file + ": one picture in the box, the first gone from it");
      shared = both ? [s.img1, s.img2] : [s.img2];
    } else {
      ({ P, box } = await armedBox(file));
      await untilChip(P, box);
      fetchAnswer = streams([3]);
      P.retryFailedPreviews();
      await sleep(40);
      shared = [shownImg(box)!];
    }
    let failures = 0;
    for (let i = 0; i < 20; i++) {
      for (const p of shared) p.onerror();
      failures++;
      await sleep(10);
      if (box.querySelector("path-full-retry")) break;
      P.retryFailedPreviews();
      await sleep(40);
      const cur = shownImg(box);
      shared = cur ? [cur] : [];
      if (!cur) break;
    }
    assert.ok(box.querySelector("path-full-retry"), file + ": the chip in the end");
    return failures - 1;
  };
  const single = await absorbed("/home/user/notes-api/plots/fanout.svg", false, false);
  const twoBuilds = await absorbed("/home/user/notes-api/plots/fanin.svg", true, false);
  const shared = await absorbed("/home/user/notes-api/plots/backlog.svg", true, true);
  assert.equal(shared, single, "two builds sharing one failed request: one attempt spent for it, so the failed loads before the chip equal a single build's (" + shared + " against " + single + ")");
  assert.equal(twoBuilds, single, "two builds, the current picture failing: the count equals a single build's (" + twoBuilds + " against " + single + ")");
  // the replaced picture's failure alone changes nothing
  const { box, img1, img2 } = await twoPictures("/home/user/notes-api/plots/drain.svg");
  const before = box.shape();
  img1.onerror();
  await sleep(10);
  assert.equal(shownImg(box), img2, "the replaced picture's failure leaves the current picture in the box");
  assert.equal(box.shape(), before, "and changes nothing else (no failure counted, no attempt spent)");
  // the replaced picture's load changes nothing either: while the current picture still loads, the wait element and its one swirl
  // stay beside it; and after the current picture failed, the box keeps the failure's wait element and its words
  const loading = await twoPictures("/home/user/notes-api/plots/drain-rate.svg");
  const whileLoading = loading.box.shape();
  loading.img1.onload();
  assert.equal(loading.box.shape(), whileLoading, "the replaced picture's load while the current picture loads: the wait element and the swirl stay, the current picture still hidden (path-img-loading)");
  assert.equal(spins(loading.box), 1, "one swirl beside the loading picture");
  const failed = await twoPictures("/home/user/notes-api/plots/drain-lag.svg");
  failed.img2.onerror();
  await sleep(10);
  const afterFailure = failed.box.shape();
  assert.match(afterFailure, /span\.path-load-note\[\]\{"[^"]+"\}/, "the premise: the current picture failed, and the wait element carries the failure's words");
  failed.img1.onload();
  assert.equal(failed.box.shape(), afterFailure, "the replaced picture's load after the current picture failed: the box keeps its wait element and its words (nothing a stale load may take away)");
  assert.equal(typeof failed.box.firstElementChild?.onclick, "function", "and the wait element's tap");
});

test("while the picture loads beside the swirl after its fetch, the wait element is out of the failure state: no retry title, no pointer cursor and no tap handler, so nothing offers a tap that would start nothing new; the picture's failure puts the retrying persona back, its title, pointer and tap", async () => {
  stubBlobs();
  const file = "/home/user/notes-api/plots/retries.svg";
  const { P, box } = await armedBox(file);
  const wait = box.firstElementChild!;
  assert.ok(wait._cls.has("path-full-wait") && /tap to retry now/.test(wait.title) && wait.style.cursor === "pointer" && typeof wait.onclick === "function", "the premise: after the first attempt's failure the wait element is the retrying swirl, titled, pointer and tap");
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  assert.equal(box.bones(), WAITING, "the picture loads beside the one swirl");
  assert.equal(box.firstElementChild, wait, "in the same wait element");
  assert.doesNotMatch(wait.title, /retry/, "no retry wording in its title while the picture loads; got " + JSON.stringify(wait.title));
  assert.equal(wait.title, "loading preview…", "its title says the picture is loading, as the first attempt's cue does");
  assert.equal(wait.style.cursor || "", "", "no pointer cursor");
  assert.equal(wait.onclick, null, "and no tap handler");
  shownImg(box)!.onerror();
  await sleep(10);
  const back = box.firstElementChild!;
  assert.ok(back._cls.has("path-full-wait") && /tap to retry now/.test(back.title) && back.style.cursor === "pointer" && typeof back.onclick === "function", "the picture failed: the retrying swirl again, titled, pointer and tap");
});

test("a tap on the chip a failing svg picture settled on shows the swirl: the tap runs the managed fetch, in the loading persona", async () => {
  stubBlobs();
  fetchCalls = 0;
  const { P, box } = await armedBox("/home/user/notes-api/plots/saturation.svg");
  fetchAnswer = streams([3]);
  for (let i = 0; i < 20; i++) {
    P.retryFailedPreviews();
    await sleep(40);
    const cur = shownImg(box);
    if (cur) { cur.onerror(); await sleep(10); }
  }
  const chip = box.querySelector("path-full-retry")!;
  assert.ok(chip, "the chip, the budget spent");
  const before = fetchCalls;
  fetchAnswer = () => new Promise(() => {});          // an attempt that stays in flight
  chip.onclick({ stopPropagation() {}, currentTarget: chip });
  await sleep(20);
  assert.match(box.shape(), /span\.path-full-wait\[\]\{img\.path-load-spin\[\]\{""\},span\.path-load-note\[\]\{"fetching…"\}\}/, "the tap shows the swirl and the note");
  assert.equal(fetchCalls, before + 1, "the tap ran the managed fetch");
});

test("a tap, and every reconnect-class event, clear the budget flag a picture's failure set: after a tap, after the heal of a settled box, and after romp:wsup, hostUp or romp:hostRelayUp over a box still retrying after its picture failed, each driven as render.ts drives it, fetches that make progress refill the budget again, as before the picture failed; with neither, the flag holds the refill and the box settles on the chip", async () => {
  stubBlobs();
  // a link that cuts every transfer: the first answer brings 1000 of 6000 bytes, each resumed one 500 more, then the stream ends
  const flaky = () => { let first = true; return () => { const size = first ? 1000 : 500; const answer = first
    ? { status: 200, ok: true, headers: { get: (h: string) => (h === "Content-Length" ? "6000" : null) } }
    : { status: 206, ok: true, headers: { get: (h: string) => (h === "Content-Range" ? "bytes 1000-5999/6000" : null) } };
    first = false;
    return Promise.resolve({ ...answer, body: { getReader: () => { let sent = false; return { read: async () => sent ? { done: true, value: undefined } : (sent = true, { done: false, value: new Uint8Array(size) }) }; } } }); }; };
  // the picture at its address fails after its fetch: the flag is set
  const failedPicture = async (file: string) => {
    const { P, box } = await armedBox(file);
    fetchAnswer = streams([3]);
    P.retryFailedPreviews();
    await sleep(40);
    shownImg(box)!.onerror();
    await sleep(10);
    return { P, box };
  };
  // six kernel messages over the flaky link: whether the chip settles
  const settles = async (P: any, box: FakeEl): Promise<boolean> => {
    for (let i = 0; i < 6 && !box.querySelector("path-full-retry"); i++) { P.retryFailedPreviews(); await sleep(460); }
    return !!box.querySelector("path-full-retry");
  };
  const held = await failedPicture("/home/user/notes-api/plots/wal-flush.svg");
  fetchAnswer = flaky();
  assert.equal(await settles(held.P, held.box), true, "with neither: the flag holds the refill, so the cut attempts spend the budget and the box settles on the chip");
  const tapped = await failedPicture("/home/user/notes-api/plots/wal-sync.svg");
  fetchAnswer = flaky();
  const wait = tapped.box.firstElementChild!;
  wait.onclick({ stopPropagation() {}, currentTarget: wait });
  await sleep(460);
  assert.equal(await settles(tapped.P, tapped.box), false, "after a tap: each cut attempt made progress and refilled the budget, so no chip");
  const healed = await failedPicture("/home/user/notes-api/plots/wal-replay.svg");
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  healed.P.retryFailedPreviews();
  await sleep(460);                                       // a link failure: registered for the reconnect-class heal
  fetchAnswer = flaky();
  healed.P.refreshSettledPreviews();
  await sleep(460);
  assert.equal(await settles(healed.P, healed.box), false, "after a reconnect-class heal: each cut attempt made progress and refilled the budget, so no chip");
  // a box still in the retrying persona after its picture failed (registered for the per-message heal, not settled): each
  // reconnect-class event as render.ts drives it; romp:wsup and hostUp rebuild the box through the per-message retry first
  const events: Array<[string, (P: any) => void]> = [
    ["romp:wsup", (P) => { P.retryFailedPreviews(); P.refreshSettledPreviews(); }],   // render.ts's romp:wsup line
    ["hostUp", (P) => { P.retryFailedPreviews(); P.refreshSettledPreviews(); }],      // render.ts's message handler: the retry on every message, then hostUp's settled drain
    ["romp:hostRelayUp", (P) => { P.refreshSettledPreviews(); }],                    // render.ts's romp:hostRelayUp listener: the settled drain alone
  ];
  for (const [name, drive] of events) {
    const retrying = await failedPicture("/home/user/notes-api/plots/wal-" + name.replace(/\W/g, "") + ".svg");
    assert.ok(!retrying.box.querySelector("path-full-retry") && /tap to retry now/.test(retrying.box.firstElementChild!.title), name + ": the premise: the box retries (the swirl, not the chip) after its picture failed");
    fetchAnswer = flaky();
    drive(retrying.P);
    await sleep(460);
    assert.equal(await settles(retrying.P, retrying.box), false, name + " over a box still retrying after its picture failed: the event cleared the flag, so each cut attempt made progress and refilled the budget, and no chip");
  }
});

test("the source keeps the two rules where the behaviour lives", () => {
  assert.match(PREVIEW, /if \(transient\) settledPreviews\.set\(box, \(\) => build\(true\)\);\s*\n\s*else \{ autoRetries--; failedPreviews\.set\(box, \(\) => build\(true\)\); \}/,
    "a link failure registers for the reconnect-class heal only; a real verdict spends the budget on the per-message heal");
  assert.match(PREVIEW, /const waitBox = \(\): \{ wait: HTMLElement; note: HTMLElement \} => \{/, "one wait box reused across attempts");
  assert.match(PREVIEW, /if \(autoRetries <= 1\) return \{ wait, note: chip \};\s*\n\s*chip\.remove\(\);/, "the chip carries the words for the one new-evidence heal; a re-armed budget gets the loading persona back");
  // the PDF probe's 502 and a relay-URL markdown image wait for the reconnect-class heal too
  assert.match(PREVIEW, /\(r\.status === 502 \? settledPreviews : failedPreviews\)\.set\(box, probe\);/);
  assert.match(PREVIEW, /parkMdImg\(img, src\);/, "a markdown image that failed is parked, not registered for any per-message heal (T291c)");
  // a remote kernel's restart reopens the relay socket and fires neither romp:wsup nor hostUp: that event heals too
  const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
  assert.match(RENDER, /window\.addEventListener\("romp:hostRelayUp", \(e\) => \{[\s\S]{0,600}?refreshSettledPreviews\(\);/);
  assert.match(PREVIEW, /const \{ note \} = waitBox\(\);\s*\n\s*if \(!note\.textContent\) setNote\(note, got > 0 \? "resuming… "/, "an attempt keeps the note that is up");
  assert.match(PREVIEW, /const setNote = \(note: HTMLElement, text: string\) => \{ if \(note\.textContent !== text\) note\.textContent = text; \};/, "the words change only when they do");
});

// ── the stand-in's nodes are projections (ui/test-dom-shim.ts): a failing assertion dumps a node's primitives, never the tree ──
test("a node of the preview's DOM stand-in enumerates its primitives alone, and a dump of it names neither parent nor children", () => {
  const root = new FakeEl("span"); const kid = new FakeEl("img"); root.appendChild(kid); kid.textContent = "text"; kid.setAttribute("src", "blob:fake"); kid.style.display = "none";
  for (const n of [root, kid]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), n.tag + " keeps an enumerable edge: " + Object.keys(n).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    for (const edge of ["parent", "children", "listeners", "attrs", "style"]) assert.ok(!dump.includes(edge), n.tag + " dumps " + edge + ":\n" + dump);
  }
  assert.ok(kid.parent === root && root.children[0] === kid && kid.textContent === "text" && kid.attrs.src === "blob:fake" && kid.style.display === "none", "the edges are still reachable");
});
