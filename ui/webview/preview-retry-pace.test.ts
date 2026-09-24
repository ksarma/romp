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
class FakeEl {
  tag: string; attrs: Record<string, string> = {};
  children!: FakeEl[]; parent!: FakeEl | null;   // both edges are defined in the constructor, non-enumerable (ui/test-dom-shim.ts hideEdges):
                                              // a node inspects as its primitives, never as the tree it hangs in
  style: Record<string, string> = {}; _cls = new Set<string>(); _text = ""; isConnected = true;
  onclick: any = null; onerror: any = null; onmousedown: any = null; onauxclick: any = null; title = ""; src = ""; alt = ""; loading = ""; decoding = "";
  listeners: Record<string, Function[]> = {};
  constructor(tag: string) {
    this.tag = tag;
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "parent", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);   // attrs, style, _cls, listeners and the onclick-style nulls hide too; a later `img.onerror = fn` keeps the attribute
  }
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
/** A fresh box for the same mention, as a re-render of the turn builds it (the earlier boxes leave the document). */
async function rerendered(file: string): Promise<FakeEl> {
  const P = await import("./preview");
  for (const b of minted) b.isConnected = false;
  const box = P.previewFull(file, SID, true) as unknown as FakeEl;
  minted.push(box);
  return box;
}

test("an svg after a retry: the resumed fetch keeps its error words and its progress, then the picture shows from the /file address the first attempt used; a re-render shows the same address with no fetch", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/diagram.svg";
  const { P, box } = await armedBox(file);
  // a link failure first: classified and worded as for any image
  fetchAnswer = failWith(502, "tunnel to TESTHOST is not answering; re-dialing");
  P.retryFailedPreviews(); await sleep(20); await sleep(450);
  assert.match(box.shape(), /tunnel to TESTHOST is not answering; re-dialing \u2014 retries when the link is back · tap to retry now/, "the server's words and the link's plan");
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
  assert.ok(img, "the picture replaced the wait box");
  assert.ok(!img!.src.startsWith("blob:"), "the svg's picture is its /file address, not an object URL; got " + img!.src);
  assert.equal(img!.src, addressOf(file), "the /file address the first attempt used");
  const again = await rerendered(file);
  assert.equal(shownImg(again)?.src, addressOf(file), "the re-render's picture: the same address");
  assert.equal(fetchCalls, 2, "and no fetch for it");
});

test("a png after a retry shows from the object URL of its fetched bytes, and so does its re-render (the control for the svg case above)", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/p99-latency.png";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const src = shownImg(box)?.src || "";
  assert.match(src, /^blob:fake-\d+$/, "a png shows from its bytes; got " + src);
  const again = await rerendered(file);
  assert.equal(shownImg(again)?.src, src, "the re-render reads the same object URL");
  assert.equal(fetchCalls, 1, "one managed fetch in all");
});

test("an svg picture whose load fails after the resumed fetch takes the first attempt's failure path: no broken picture stays, the wait box says what the first attempt's does, and the heal shows a fresh <img> at the same address with no second fetch", async () => {
  stubBlobs();
  fetchCalls = 0;
  const file = "/home/user/notes-api/plots/error-budget.svg";
  const { P, box } = await armedBox(file);
  fetchAnswer = streams([3]);
  P.retryFailedPreviews();
  await sleep(40);
  const img = shownImg(box)!;
  assert.equal(img?.src, addressOf(file), "the picture shows from its /file address; got " + img?.src);
  assert.ok(img.onerror, "and carries an onerror, as the first attempt's <img> does");
  img.onerror();
  await sleep(10);
  assert.notEqual(box.style.display, "none", "the verified box stays shown when its picture fails to load after the resumed fetch; only an unverified box hides");
  assert.equal(shownImg(box), undefined, "no broken picture stays in the box");
  assert.match(box.shape(), /span\.path-load-note\[\]\{"connection dropped \u2014 retrying · tap to retry now"\}/, "the first attempt's words (no byte count: the bytes were not kept)");
  const calls = fetchCalls;
  P.retryFailedPreviews();
  await sleep(20);
  const retried = shownImg(box);
  assert.ok(retried && retried !== img, "the heal built a fresh picture");
  assert.notEqual(box.style.display, "none", "and the verified box shows it");
  assert.equal(retried!.src, addressOf(file), "at the same address");
  assert.equal(typeof retried!.onerror, "function", "the healed picture carries its failure handler, as the first one does");
  assert.equal(fetchCalls, calls, "with no second managed fetch");
  // the budget still bounds it: every further failure spends an attempt, and the spent budget settles on the chip
  for (let i = 0; i < 6; i++) { const cur = shownImg(box); if (!cur) break; cur.onerror(); await sleep(10); P.retryFailedPreviews(); await sleep(10); }
  assert.match(box.shape(), /span\.path-full-retry\[\]\{"⚠ still unavailable \u2014 tap to retry"\}/, "the chip, once the attempts are spent");
  const settled = box.shape();
  for (let i = 0; i < 30; i++) P.retryFailedPreviews();
  await sleep(20);
  assert.equal(box.shape(), settled, "the same failure again is no new evidence: the chip stays");
  assert.equal(fetchCalls, calls, "no managed fetch at any point after the bytes arrived");
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

test("an unverified svg preview whose picture fails to load after the resumed fetch hides its box, as it does when the first attempt's picture fails, and then takes the same failure path: registered for the heal, which builds a fresh picture from the memo", async () => {
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
  assert.match(box.shape(), /span\.path-load-note\[\]\{"connection dropped \u2014 retrying · tap to retry now"\}/, "then the first attempt's failure path: the wait box and its words");
  const calls = fetchCalls;
  P.retryFailedPreviews();
  await sleep(20);
  const again = shownImg(box);
  assert.ok(again && again !== img, "registered for the heal, which built a fresh picture");
  assert.equal(again!.src, addressOf(file), "at the same address, from the memo");
  assert.equal(fetchCalls, calls, "with no second managed fetch");
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
