// A markdown-inline image whose fetch fails is PARKED, never re-set per message (T291c, the user 2026-09-09: three
// captions in a remote session's transcript flipped on and off at the push rate; the 2026-08-24 heal re-set each failed
// img's src on every kernel message, hiding the alt text while the reload ran and showing it again on the 404). The
// heal is EXECUTED here over a minimal fake DOM: the capture-phase listener parks the img (no src, the alt text as a
// stable caption); sixty pushes write the src zero times; the reconnect-class heal probes each parked URL once OFF the
// DOM, a failed probe changes nothing, a successful one lands the picture on every parked img with that URL on the
// page at that moment (a re-render during the probe included); a URL the kernel serves gets a bounded off-DOM probe on
// the per-message path, and that budget rides the URL, so a turn re-rendered on every push while it streams still gets
// its three probes, a second img with the URL failing midway starts nothing over, a load clears the budget with the
// memory (the URL failing again later starts afresh), and a heal that lands while a probe is pending is not undone by
// that probe's failure, nor does that probe's failure, arriving after the URL has failed AGAIN, shorten or delete
// the fresh budget or clear a newer probe's in-flight mark (a failure counts only for the probe whose token
// is current); the reconnect-class heal probes every remembered URL, on the page or not (a turn evicted from
// the rendered window, a closed tab); the chat's post-pass parks a re-rendered img with a remembered URL before the
// browser fetches it; and the file viewer's own picture, in its picture box, is not the heal's (the viewer asks an svg
// picture's address again itself; a raster picture's src is bytes in hand), while a figure of a markdown file the viewer
// renders parks and heals as any other. A figure an author wraps
// in markup carrying the class of either box (the viewer's picture box, the chat's preview box) parks and heals too, since the
// heal knows each box by its data mark, and the preview box's own imgs stay the preview's. The module remembers failed URLs for the page life, so fresh() heals every remembered URL off
// the DOM through the public reconnect path before each test: every test starts with an empty memory.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges } from "../test-dom-shim";   // the fake hides its edges at creation (the shim ratchet, ui/test-dom-shim.test.ts)

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

class FakeEl {
  tagName: string; attrs: Record<string, string> = {}; _cls = new Set<string>(); dataset: Record<string, string> = {};
  isConnected = true; onerror: any = null; children: FakeEl[] = []; srcWrites = 0;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }   // children and every object-valued field hide (ui/test-dom-shim.ts): a failing assertion dumps no tree; the Image subclass below calls super, so it is covered
  get src(): string { return this.attrs.src || ""; }
  set src(v: string) { this.srcWrites++; this.attrs.src = v; }   // a src write is a fetch, and hides the alt text until the response
  get alt(): string { return this.attrs.alt || ""; }
  set alt(v: string) { this.attrs.alt = v; }
  hasAttribute(k: string) { return k in this.attrs; }
  getAttribute(k: string) { return this.attrs[k] ?? null; }
  setAttribute(k: string, v: string) { if (k === "src") this.srcWrites++; this.attrs[k] = v; }
  removeAttribute(k: string) { if (k === "src") this.srcWrites++; delete this.attrs[k]; }
  get classList() { const s = this._cls; return { add: (...c: string[]) => c.forEach((x) => s.add(x)), remove: (...c: string[]) => c.forEach((x) => s.delete(x)), contains: (c: string) => s.has(c) }; }
  closest() { return null; }
  querySelectorAll(sel: string): FakeEl[] { return sel === "img" ? this.children.filter((c) => c.tagName === "IMG") : []; }
  shape(): string { return `${this.tagName}[${Object.entries(this.attrs).sort().map(([k, v]) => k + "=" + v).join(" ")}].${[...this._cls].sort().join(".")}{${JSON.stringify(this.dataset)}}`; }
}
const live: FakeEl[] = [];                            // what document.querySelectorAll sees
let errorListener: ((e: any) => void) | null = null;
(globalThis as any).document = {
  addEventListener: (type: string, fn: any, capture?: boolean) => { if (type === "error") { assert.equal(capture, true, "capture phase"); errorListener = fn; } },
  querySelectorAll: (sel: string) => (sel === "img.md-img-failed[data-md-src]" ? live.filter((e) => e.isConnected && e.tagName === "IMG" && e._cls.has("md-img-failed") && e.dataset.mdSrc) : []),
  createElement: (t: string) => new FakeEl(t),
};
(globalThis as any).location = { protocol: "http:", origin: "http://127.0.0.1:1", href: "http://127.0.0.1:1/chat" };
(globalThis as any).window = (globalThis as any).window || {};
const probes: FakeEl[] = [];
(globalThis as any).Image = class extends FakeEl { onload: any = null; constructor() { super("img"); probes.push(this); } };
let fetchCalls = 0;
(globalThis as any).fetch = () => { fetchCalls++; return Promise.reject(new Error("no fetch expected")); };

const ORIGIN_URL = (n: string) => "http://127.0.0.1:1/home/user/notes-api/plots/" + n;   // a path the browser resolved against the page: no route serves it
const servedUrl = (n: string) => "http://127.0.0.1:1/file?path=%2Fhome%2Fuser%2Fnotes-api%2Fplots%2F" + n + "&sid=11111111-2222-4333-8444-000000000001";   // a URL the kernel answers
const SERVED_URL = servedUrl("latency.png");
function mdImg(url: string, alt: string): FakeEl { const img = new FakeEl("img"); img.src = url; img.alt = alt; img.srcWrites = 0; live.push(img); return img; }
const fail = (img: FakeEl) => errorListener!({ target: img });
async function fresh() {
  const P = await import("./preview"); P.installMdImgHeal(); assert.ok(errorListener);
  live.length = 0; probes.length = 0;
  // the module remembers every failed URL for the page life; the reconnect heal probes each remembered URL off the DOM,
  // and a load forgets it, so one heal with every probe answered clears the memory an earlier test left behind
  P.refreshSettledPreviews(); for (const p of probes) (p as any).onload(); probes.length = 0;
  return P;
}

test("a failed markdown image is parked: no src, the alt text stays, and sixty pushes write the src zero times", async () => {
  const P = await fresh();
  const a = mdImg(ORIGIN_URL("schematic.png"), "Schematic"), b = mdImg(ORIGIN_URL("queue.png"), "Queued bubble with pencil and cross, composer under the editing pill");
  fail(a); fail(b);
  assert.equal(a.hasAttribute("src"), false, "the src is gone: the browser fetches nothing and shows the alt text");
  assert.equal(a.dataset.mdSrc, ORIGIN_URL("schematic.png"), "…the URL kept for the heal");
  assert.ok(a._cls.has("md-img-failed"));
  assert.equal(a.alt, "Schematic", "the caption is the alt text, untouched");
  const sa = a.shape(), sb = b.shape();
  a.srcWrites = 0; b.srcWrites = 0;
  for (let i = 0; i < 60; i++) P.retryFailedPreviews();   // what render.ts runs on every kernel message
  assert.equal(a.shape(), sa); assert.equal(b.shape(), sb);
  assert.equal(a.srcWrites + b.srcWrites, 0, "no src write on a push: a write is a fetch and hides the alt text until the response");
  assert.equal(probes.length, 0, "an origin-resolved path no route serves gets no probe either");
  assert.equal(fetchCalls, 0);
});

test("the reconnect-class heal probes each parked URL once off the DOM; a failure changes nothing, a success lands the picture on every parked img on the page then", async () => {
  const P = await fresh();
  const a = mdImg(ORIGIN_URL("schematic.png"), "Schematic"), b = mdImg(ORIGIN_URL("queue.png"), "Queued bubble");
  fail(a); fail(b);
  const sa = a.shape();
  P.refreshSettledPreviews();                        // romp:wsup / hostUp / romp:hostRelayUp all run this
  assert.equal(probes.length, 2, "one detached probe per parked URL");
  assert.deepEqual(probes.map((p) => p.src).sort(), [ORIGIN_URL("queue.png"), ORIGIN_URL("schematic.png")]);
  probes.forEach((p) => p.onerror());
  assert.equal(a.shape(), sa, "a failed probe leaves the parked caption exactly as it was");
  probes.length = 0;
  P.refreshSettledPreviews();
  assert.equal(probes.length, 2, "the next reconnect probes again, once per URL");
  // a re-render during the probe: the turn's fresh img is parked by the post-pass while the URL is still remembered
  a.isConnected = false;
  const root = new FakeEl("body"); const a2 = new FakeEl("img"); a2.src = ORIGIN_URL("schematic.png"); a2.alt = "Schematic"; root.children.push(a2);
  P.mdImgPostPass(root as unknown as ParentNode);
  assert.equal(a2.hasAttribute("src"), false, "the re-rendered img is parked before it fetches");
  live.push(a2);
  const pa = probes.find((p) => p.src === ORIGIN_URL("schematic.png"))!;
  (pa as any).onload();
  assert.equal(a2.src, ORIGIN_URL("schematic.png"), "the picture lands on the img that is on the page now, not on the snapshot's");
  assert.equal(a2._cls.has("md-img-failed"), false);
  assert.equal("mdSrc" in a2.dataset, false);
  assert.equal(b.hasAttribute("src"), false, "the other URL, still down, stays parked");
  // …and a URL that healed renders normally on the next re-render
  const root2 = new FakeEl("body"); const fine = new FakeEl("img"); fine.src = ORIGIN_URL("schematic.png"); root2.children.push(fine);
  P.mdImgPostPass(root2 as unknown as ParentNode);
  assert.equal(fine.src, ORIGIN_URL("schematic.png"), "a healed URL is no longer parked at render");
});

test("a URL the kernel serves gets a BOUNDED off-DOM probe on the per-message path, then the reconnect heal alone", async () => {
  const P = await fresh();
  const s = mdImg(SERVED_URL, "Latency");
  fail(s);
  const parked = s.shape();
  assert.equal(s.hasAttribute("src"), false, "parked like any other: the caption stands");
  s.srcWrites = 0;
  for (let round = 1; round <= 3; round++) {
    P.retryFailedPreviews();
    assert.equal(probes.length, round, "push " + round + ": one detached probe, the element untouched");
    assert.equal(s.shape(), parked);
    probes[probes.length - 1].onerror();
  }
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 3, "the budget is spent: no more per-message probes");
  assert.equal(s.srcWrites, 0, "the element's src was never written by an attempt");
  P.refreshSettledPreviews();
  assert.equal(probes.length, 4, "the reconnect-class heal still probes it");
  (probes[3] as any).onload();
  assert.equal(s.src, SERVED_URL, "…and the picture lands when the file is there");
});

test("a served URL's budget follows the URL: a turn rebuilt on every push while it streams still gets three probes, one per push", async () => {
  // a streaming assistant turn is re-rendered on every push (the tail path removes the turn's nodes and rebuilds them),
  // so the img that failed is detached by the time the next push arrives and the post-pass parks a fresh one; the
  // budget must not die with the element
  const P = await fresh();
  const url = servedUrl("throughput.png");
  let cur = mdImg(url, "Throughput");
  let twin: FakeEl | null = null;
  fail(cur);
  for (let round = 1; round <= 3; round++) {
    P.retryFailedPreviews();
    assert.equal(probes.length, round, "push " + round + ": one detached probe");
    P.retryFailedPreviews();
    assert.equal(probes.length, round, "a push while that probe is pending fires no second one for the URL");
    // the streaming re-render: the old img leaves the page, the post-pass parks the fresh one before any fetch
    cur.isConnected = false;
    const root = new FakeEl("body"); const next = new FakeEl("img"); next.src = url; next.alt = "Throughput"; root.children.push(next);
    P.mdImgPostPass(root as unknown as ParentNode);
    assert.equal(next.hasAttribute("src"), false, "the fresh img is parked at render");
    next.srcWrites = 0; live.push(next); cur = next;
    probes[probes.length - 1].onerror();
    assert.equal(cur.srcWrites, 0, "a failed probe never touches the img on the page");
    if (round === 2) {
      // a second img with the URL, rendered before the first failure (the same figure in another view), fails now: the
      // URL keeps the one attempt it has left rather than starting over at three
      twin = mdImg(url, "Throughput"); fail(twin);
      assert.equal(twin.hasAttribute("src"), false, "parked like the first");
    }
  }
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 3, "the budget is spent: no more per-message probes");
  P.refreshSettledPreviews();
  assert.equal(probes.length, 4, "the reconnect-class heal still probes it");
  (probes[3] as any).onload();
  assert.equal(cur.src, url, "the picture lands on the img that is on the page now");
  assert.equal(cur.srcWrites, 1);
  assert.equal(twin!.src, url, "…and on every other parked img with the URL");
});

test("a per-message probe that loads lands the picture on the img on the page now and clears the URL's budget with its memory; the URL failing again later starts afresh", async () => {
  const P = await fresh();
  const url = servedUrl("progress.png");
  let cur = mdImg(url, "Progress");
  fail(cur);
  P.retryFailedPreviews();
  assert.equal(probes.length, 1, "push 1: one detached probe");
  // the streaming re-render while the probe is in flight: the old img leaves the page, the fresh one is parked at render
  cur.isConnected = false;
  const root = new FakeEl("body"); const next = new FakeEl("img"); next.src = url; next.alt = "Progress"; root.children.push(next);
  P.mdImgPostPass(root as unknown as ParentNode);
  assert.equal(next.hasAttribute("src"), false, "the fresh img is parked at render");
  next.srcWrites = 0; live.push(next); cur = next;
  (probes[0] as any).onload();                       // the file is there now
  assert.equal(cur.src, url, "the picture lands on the img that is on the page now");
  assert.equal(cur.srcWrites, 1);
  assert.equal(cur._cls.has("md-img-failed"), false);
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 1, "a healed URL has no pending budget: the next pushes probe nothing");
  P.refreshSettledPreviews();
  assert.equal(probes.length, 1, "…and the reconnect heal has forgotten it");
  // the same URL fails again later (a relay blip, a file moved away): the listener arms three attempts afresh and the
  // first fires on the next push, nothing of the healed round lingering
  const again = mdImg(url, "Progress");
  fail(again);
  assert.equal(again.hasAttribute("src"), false, "parked again");
  P.retryFailedPreviews();
  assert.equal(probes.length, 2, "the URL failing again later gets its per-message probe afresh");
  assert.equal(probes[1].src, url);
});

test("a reconnect heal that lands while a per-message probe is pending stands: the stale failure re-arms nothing for the healed URL", async () => {
  const P = await fresh();
  const url = servedUrl("burndown.png");
  const s = mdImg(url, "Burndown");
  fail(s);
  s.srcWrites = 0;
  P.retryFailedPreviews();
  assert.equal(probes.length, 1, "push 1: the per-message probe is in flight");
  P.refreshSettledPreviews();                        // the socket came back meanwhile
  assert.equal(probes.length, 2, "the reconnect heal probes the URL too");
  (probes[1] as any).onload();                       // the reconnect probe answers first: healed
  assert.equal(s.src, url, "the picture lands");
  probes[0].onerror();                               // the older per-message probe's failure arrives afterwards
  assert.equal(s.src, url, "a stale failure changes nothing on the page");
  assert.equal(s.srcWrites, 1);
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 2, "the stale failure re-armed no attempt for a healed URL: the next pushes probe nothing");
  P.refreshSettledPreviews();
  assert.equal(probes.length, 2, "…and the reconnect heal has forgotten it");
});

// The stale-failure race (the review's find on the budget change): a reconnect heal loads the URL while a per-message
// probe is pending, the URL fails AGAIN before that probe's error arrives (the file moved away, a relay blipped), and
// the listener arms three attempts afresh. The stale error then belongs to a probe a load already retired: it must spend
// none of the fresh attempts and clear no newer probe's in-flight mark. Its `left` is the OLD budget's, so applying it
// deleted the fresh budget outright (one attempt left at fire time) or cut it to two (three left), and its delete of the
// in-flight mark let the next push fire a second probe for a URL whose newer probe was still pending.

test("a stale failure from a probe fired with the last attempt does not delete the budget the URL's re-fail armed afresh", async () => {
  const P = await fresh();
  const url = servedUrl("heatmap.png");
  const s = mdImg(url, "Heatmap");
  fail(s);
  P.retryFailedPreviews(); probes[0].onerror();      // attempt one spent
  P.retryFailedPreviews(); probes[1].onerror();      // attempt two spent
  P.retryFailedPreviews();                           // the last attempt's probe is in flight
  assert.equal(probes.length, 3);
  P.refreshSettledPreviews();                        // the socket came back meanwhile
  assert.equal(probes.length, 4, "the reconnect heal probes the URL too");
  (probes[3] as any).onload();                       // the reconnect probe answers first: healed, the picture lands
  assert.equal(s.src, url);
  fail(s);                                           // the URL fails again: three attempts afresh
  assert.equal(s.hasAttribute("src"), false, "parked again");
  probes[2].onerror();                               // the older per-message probe's failure arrives only now
  P.retryFailedPreviews();
  assert.equal(probes.length, 5, "the fresh budget survives the stale failure: the next push probes");
  probes[4].onerror();
  P.retryFailedPreviews(); probes[5].onerror();
  P.retryFailedPreviews(); probes[6].onerror();
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 7, "the fresh budget was a full three: the stale failure spent none of them");
});

test("a stale failure from a probe fired with three attempts does not shorten the budget the URL's re-fail armed afresh", async () => {
  const P = await fresh();
  const url = servedUrl("flamegraph.png");
  const s = mdImg(url, "Flame graph");
  fail(s);
  P.retryFailedPreviews();                           // the first probe is in flight with all three attempts
  assert.equal(probes.length, 1);
  P.refreshSettledPreviews();
  (probes[1] as any).onload();                       // the reconnect probe answers first: healed
  assert.equal(s.src, url);
  fail(s);                                           // the URL fails again: three attempts afresh
  probes[0].onerror();                               // the older per-message probe's failure arrives only now
  for (let attempt = 1; attempt <= 3; attempt++) {
    P.retryFailedPreviews();
    assert.equal(probes.length, 2 + attempt, "push " + attempt + " after the re-fail: one probe, the fresh budget intact");
    probes[probes.length - 1].onerror();
  }
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 5, "three attempts after the re-fail, then spent");
});

test("a stale failure does not clear a newer probe's in-flight mark: no two probes for one URL overlap", async () => {
  const P = await fresh();
  const url = servedUrl("waterfall.png");
  const s = mdImg(url, "Waterfall");
  fail(s);
  P.retryFailedPreviews();                           // the first probe is in flight
  P.refreshSettledPreviews();
  (probes[1] as any).onload();                       // the reconnect probe answers first: healed
  assert.equal(s.src, url);
  fail(s);                                           // the URL fails again: three attempts afresh
  P.retryFailedPreviews();                           // the fresh budget's first probe is in flight
  assert.equal(probes.length, 3);
  probes[0].onerror();                               // the older probe's failure arrives while the newer one is pending
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 3, "a push while the newer probe is pending fires no second probe for the URL");
  probes[2].onerror();                               // the newer probe fails: one fresh attempt spent
  P.retryFailedPreviews(); probes[3].onerror();
  P.retryFailedPreviews(); probes[4].onerror();
  P.retryFailedPreviews(); P.retryFailedPreviews();
  assert.equal(probes.length, 5, "the fresh budget ran its three attempts, one probe at a time");
});

test("the reconnect-class heal probes a remembered URL whose turn is outside the rendered window", async () => {
  // the turn left the rendered window (or its tab was closed), so no parked img with the URL is on the page; the
  // URL is still remembered, and until it heals a scroll-back parks the re-rendered img again for the page life
  const P = await fresh();
  const a = mdImg(ORIGIN_URL("evicted.png"), "Evicted");
  fail(a);
  a.isConnected = false;
  P.refreshSettledPreviews();
  assert.equal(probes.length, 1, "the URL is remembered even with no parked img on the page");
  assert.equal(probes[0].src, ORIGIN_URL("evicted.png"));
  probes[0].onerror();
  probes.length = 0;
  P.refreshSettledPreviews();
  assert.equal(probes.length, 1, "still down: the next reconnect probes it again");
  (probes[0] as any).onload();
  const root = new FakeEl("body"); const back = new FakeEl("img"); back.src = ORIGIN_URL("evicted.png"); root.children.push(back);
  P.mdImgPostPass(root as unknown as ParentNode);
  assert.equal(back.src, ORIGIN_URL("evicted.png"), "on scroll-back the healed URL renders normally");
  probes.length = 0;
  P.refreshSettledPreviews();
  assert.equal(probes.length, 0, "a healed URL is forgotten: the next reconnect has nothing to probe");
});

/** An element's classes and attribute names, for inside() below. */
type Up = { cls?: string[]; attrs?: string[] };
/** The img inside the ancestors given (nearest first), with closest() answering as the DOM's does for the two selector shapes the
 *  heal asks (a class, `.x`, or an attribute, `[x]`): the img itself first, then each ancestor. Any other shape throws, so a new
 *  selector in the heal fails here loudly instead of reading as "not inside". */
function inside(img: FakeEl, ...ups: Up[]): FakeEl {
  (img as any).closest = (sel: string) => {
    const c = /^\.([\w-]+)$/.exec(sel), a = /^\[([\w-]+)\]$/.exec(sel);
    if (!c && !a) throw new Error("the stand-in's closest() reads a class or an attribute selector alone, not: " + sel);
    const self: Up = { cls: [...img._cls], attrs: Object.keys(img.attrs) };
    return [self, ...ups].some((u) => (c && (u.cls || []).includes(c[1])) || (a && (u.attrs || []).includes(a[1]))) ? {} : null;
  };
  return img;
}

test("the file viewer's own picture, in its picture box, is not the heal's: its failure parks nothing, and its served URL gets no per-message probe and no reconnect probe, while a figure of a markdown file the viewer renders, in its Rendered body, parks and heals as any markdown image does", async () => {
  const P = await fresh();
  const PICTURE_URL = servedUrl("topology.svg") + "&v=1757145600000000001";
  const picture = inside(mdImg(PICTURE_URL, "/home/user/notes-api/plots/topology.svg"), { cls: ["fileview-imgbox"], attrs: [P.VIEWER_PICTURE_MARK] }, { cls: ["fileview-body"] }, { cls: ["fileview"] });   // imgBlock's box: its class and its data mark
  const figure = inside(mdImg(servedUrl("latency-hist.png"), "Latency histogram"), { cls: ["fileview-md"] }, { cls: ["fileview-body"] }, { cls: ["fileview"] });
  fail(picture); fail(figure);
  assert.equal(picture.getAttribute("src"), PICTURE_URL, "the viewer's picture keeps its src: the heal parks nothing of it");
  assert.equal(picture._cls.has("md-img-failed"), false, "and marks nothing");
  assert.equal(figure.hasAttribute("src"), false, "the rendered figure is parked: no src");
  assert.ok(figure._cls.has("md-img-failed"), "and marked");
  for (let i = 0; i < 3; i++) P.retryFailedPreviews();   // three kernel messages
  assert.deepEqual(probes.map((x) => x.src), [servedUrl("latency-hist.png")], "one per-message probe, the figure's, and none of the viewer's picture");
  (probes[0] as any).onload();
  assert.equal(figure.src, servedUrl("latency-hist.png"), "the figure's probe loaded: the picture lands on it");
  assert.equal(figure._cls.has("md-img-failed"), false, "unparked");
  P.refreshSettledPreviews();                            // a reconnect-class event
  assert.deepEqual(probes.slice(1).map((x) => x.src), [], "the reconnect-class heal probes nothing: the figure healed, and the viewer's picture was never the heal's");
});

test("a figure whose author's markup carries the picture box's class (fileview-imgbox), on a wrapper or on the img itself, in a markdown file the viewer renders and in a chat message, parks and heals as any markdown image does: the heal knows the viewer's picture by its data mark, which the sanitizer strips from an author's markup (md-img-park-browser.test.ts runs the real sanitizer and the real page)", async () => {
  const P = await fresh();
  const noteFig = inside(mdImg(servedUrl("wrapped-note.png"), "wrapped in a note"), { cls: ["fileview-imgbox"] }, { cls: ["fileview-md"] }, { cls: ["fileview-body"] }, { cls: ["fileview"] });
  const chatFig = inside(mdImg(servedUrl("wrapped-chat.png"), "wrapped in a message"), { cls: ["fileview-imgbox"] }, { cls: ["md"] });
  const own = mdImg(servedUrl("classed.png"), "the img wears the class");
  own._cls.add("fileview-imgbox");
  inside(own, { cls: ["md"] });
  const figs = [noteFig, chatFig, own];
  for (const f of figs) fail(f);
  assert.deepEqual(figs.map((f) => f.hasAttribute("src")), [false, false, false], "each is parked: no src, so the browser shows its alt text and fetches nothing");
  assert.deepEqual(figs.map((f) => f._cls.has("md-img-failed")), [true, true, true], "and marked");
  assert.deepEqual(figs.map((f) => f.dataset.mdSrc), [servedUrl("wrapped-note.png"), servedUrl("wrapped-chat.png"), servedUrl("classed.png")], "each URL kept for the heal");
  P.retryFailedPreviews();                               // a kernel message
  assert.deepEqual(probes.map((x) => x.src), [servedUrl("wrapped-note.png"), servedUrl("wrapped-chat.png"), servedUrl("classed.png")], "one per-message probe for each, off the page");
  for (const p of probes) (p as any).onload();
  assert.deepEqual(figs.map((f) => f.src), [servedUrl("wrapped-note.png"), servedUrl("wrapped-chat.png"), servedUrl("classed.png")], "each probe loaded: the picture lands on its img");
  assert.deepEqual(figs.map((f) => f._cls.has("md-img-failed")), [false, false, false], "unparked");
  assert.equal(P.VIEWER_PICTURE_MARK, "data-fv-picture", "the mark the heal skips by is a data-* attribute, which the sanitizer strips from an author's markup");
});

test("a figure whose author's markup carries the chat preview box's class (path-full), on a wrapper or on the img itself, in a markdown file the viewer renders and in a chat message, parks and heals as any markdown image does, while the preview's own imgs inside the box's data mark stay the preview's: its swirl and a picture it shows from fetched bytes, which listen to nothing, neither park nor get a probe (md-img-park-browser.test.ts runs the real sanitizer, the real preview box and the real page)", async () => {
  const P = await fresh();
  const noteFig = inside(mdImg(servedUrl("pf-note.png"), "wrapped in a note"), { cls: ["path-full"] }, { cls: ["fileview-md"] }, { cls: ["fileview-body"] }, { cls: ["fileview"] });
  const chatFig = inside(mdImg(servedUrl("pf-chat.png"), "wrapped in a message"), { cls: ["path-full"] }, { cls: ["md"] });
  const own = mdImg(servedUrl("pf-classed.png"), "the img wears the class");
  own._cls.add("path-full");
  inside(own, { cls: ["md"] });
  const box: Up = { cls: ["path-full"], attrs: [P.PREVIEW_BOX_MARK] };   // previewFull's box: its class and its data mark
  const SWIRL = "http://127.0.0.1:1/media/romp-swirl-glyph.svg";           // an address the kernel serves: parked, it would get a probe
  const HELD = "blob:http://127.0.0.1:1/11111111-2222-4333-8444-000000000009";
  const swirl = inside(mdImg(SWIRL, "loading preview"), { cls: ["path-full-wait"] }, box, { cls: ["path-thumbs"] }, { cls: ["md"] });
  const held = inside(mdImg(HELD, "held.png"), box, { cls: ["path-thumbs"] }, { cls: ["md"] });
  const figs = [noteFig, chatFig, own];
  for (const f of [...figs, swirl, held]) fail(f);
  assert.deepEqual(figs.map((f) => f.hasAttribute("src")), [false, false, false], "each figure wearing the class is parked: no src, so the browser shows its alt text and fetches nothing");
  assert.deepEqual(figs.map((f) => f._cls.has("md-img-failed")), [true, true, true], "and marked");
  assert.deepEqual([swirl.getAttribute("src"), held.getAttribute("src")], [SWIRL, HELD], "the preview's own swirl and its picture of fetched bytes keep their src: the heal parks nothing of the box");
  assert.deepEqual([swirl._cls.has("md-img-failed"), held._cls.has("md-img-failed")], [false, false], "and marks nothing");
  P.retryFailedPreviews();                               // a kernel message
  assert.deepEqual(probes.map((x) => x.src), [servedUrl("pf-note.png"), servedUrl("pf-chat.png"), servedUrl("pf-classed.png")], "one per-message probe for each figure, and none for the swirl");
  for (const p of probes) (p as any).onload();
  assert.deepEqual(figs.map((f) => f.src), [servedUrl("pf-note.png"), servedUrl("pf-chat.png"), servedUrl("pf-classed.png")], "each probe loaded: the picture lands on its img");
  assert.deepEqual(figs.map((f) => f._cls.has("md-img-failed")), [false, false, false], "unparked");
  assert.equal(P.PREVIEW_BOX_MARK, "data-preview-full", "the mark the heal knows the preview box by is a data-* attribute, which the sanitizer strips from an author's markup");
});

test("render.ts installs the listener once, parks known-failed URLs on its OWN markdown output only, and files the page's bundle build once per load", () => {
  assert.match(RENDER, /installMdImgHeal\(\);/);
  assert.doesNotMatch(RENDER, /registerMdPostPass\(mdImgPostPass\)/, "never through the shared sanitizer: the file viewer rewrites its images' paths after the sanitize (the review's find)");
  assert.equal((RENDER.match(/mdImgPostPass\(clean\);/g) || []).length, 2, "md() and userMd() park a known-failed image before the browser fetches it");
  assert.match(RENDER, /linkifyPrRefs\(clean, repo\);\s*\n\s*mdImgPostPass\(clean\);[^\n]*\n\s*return clean\.innerHTML;/, "after the sanitize and the PR links, before the string leaves");
  // the page-load row: the ?v= of the render.js script this page loaded, one row per load
  assert.match(RENDER, /\.find\(\(u\) => \/\\\/dist\\\/render\\\.js\(\\\?\|\$\)\/\.test\(u\)\)/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "clientDiag", surface: "chat", what: "pageload", data: \{ distVer: m \? Number\(m\[1\]\) : 0, path: location\.pathname \} \}\);/);
  assert.match(CSS, /\.md-img-failed \{ display: inline; font-size: 0\.86em; font-style: italic; color: var\(--dim\); \}/, "the parked caption is styled like the load note");
});
