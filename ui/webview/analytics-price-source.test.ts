// The Token usage modal's PRICE-SOURCE line (the user 2026-09-20, with the price feed's off switch): the kernel's
// /analytics payload carries `priceFeed`, the state of the per-model price table behind the modal's dollar figures,
// and the modal says where the prices came from on one muted line under the footnote: the live feed with its age,
// or the baked-in defaults with the reason (the feed is off, the last fetch failed, nothing fetched yet). Three
// layers, each tested the way it can be: the WORDING is a pure function gear.js exports (raPriceNote), run here for
// real with the payload shapes; the NODE is the closure helper raPriceLine, lifted out of initGear and driven
// against the repo's DOM stand-in (present with its text, absent without, one node across re-renders); the
// render's WIRING is pinned in the source, the convention where nothing executes raRender (rail-spend.test.ts
// states it). The kernel side of the contract (the block in /analytics and /version) is pinned by its own tests.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { nodeFactory } from "../test-dom-shim";

const ROOT = path.resolve(process.cwd(), "..");
const GEAR = fs.readFileSync(path.join(ROOT, "ui", "webview", "gear.js"), "utf8");
const GEAR_CSS = fs.readFileSync(path.join(ROOT, "ui", "webview", "gear.css"), "utf8");
// gear.js loads under node with no DOM global touched at require time (checked 2026-09-20: its top level is
// declarations, requires and the export), so the formatter runs as the module ships it
const gear = require("./gear.js");
const note = (pf: unknown): string => {
  assert.equal(typeof gear.raPriceNote, "function", "gear.js exports raPriceNote beside initGear (the modal's price-source wording)");
  return gear.raPriceNote(pf);
};

test("live feed: the line names the feed and the fetch's age in plain words, minutes then hours", () => {
  assert.equal(note({ off: false, source: "feed", ageS: 240, fetchedAt: 1_700_000_000, rows: 6, lastError: null }), "prices: live feed, fetched 4 minutes ago");
  assert.equal(note({ source: "feed", ageS: 30 }), "prices: live feed, fetched just now", "under a minute");
  assert.equal(note({ source: "feed", ageS: 60 }), "prices: live feed, fetched 1 minute ago", "singular");
  assert.equal(note({ source: "feed", ageS: 3599 }), "prices: live feed, fetched 59 minutes ago", "whole minutes up to the hour");
  assert.equal(note({ source: "feed", ageS: 3600 }), "prices: live feed, fetched 1 hour ago", "singular hour");
  assert.equal(note({ source: "feed", ageS: 7_200 }), "prices: live feed, fetched 2 hours ago");
  assert.equal(note({ source: "feed", ageS: 90_000 }), "prices: live feed, fetched 25 hours ago", "hours keep counting; the feed's TTL is six, a cache kept under the switch can be older");
  assert.equal(note({ source: "feed" }), "prices: live feed", "no age in the block (an older kernel's shape): the source alone, never a made-up age");
  // a cache kept while the switch is on still prices from the feed, and the line says the feed, with its age: the
  // user stopped the traffic, not the data
  assert.equal(note({ off: true, source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago");
});

test("the feed is off: baked-in defaults, and the switch is named so the reader knows what to flip", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", fetchedAt: null, ageS: null, rows: 0, lastError: null }),
    "prices: baked-in defaults; live feed off (ROMP_PRICE_FEED=off)");
});

test("the last fetch failed: baked-in defaults with the reason the kernel recorded, never a fetched body", () => {
  assert.equal(note({ off: false, source: "defaults", reason: "failed", lastError: "HTTPError: HTTP Error 500: Internal Server Error" }),
    "prices: baked-in defaults; the last feed fetch failed (HTTPError: HTTP Error 500: Internal Server Error)");
  assert.equal(note({ source: "defaults", reason: "failed", lastError: "URLError: <urlopen error [Errno 111] Connection refused>" }),
    "prices: baked-in defaults; the last feed fetch failed (URLError: <urlopen error [Errno 111] Connection refused>)",
    "the reason is placed as text by the render (textContent), so angle brackets are no hazard");
  assert.equal(note({ source: "defaults", reason: "failed" }), "prices: baked-in defaults; the last feed fetch failed", "a failure with no recorded reason says that much and no more");
});

test("nothing fetched yet: baked-in defaults, whether the fetch has not started or is in flight", () => {
  assert.equal(note({ off: false, source: "defaults", reason: "unfetched", fetchedAt: null, rows: 0 }), "prices: baked-in defaults; nothing fetched from the feed yet");
  assert.equal(note({ source: "defaults", reason: "inflight" }), "prices: baked-in defaults; nothing fetched from the feed yet",
    "the first open of the modal: the payload is built before the fetch it started lands");
  assert.equal(note({ source: "defaults", reason: "empty", rows: 0 }), "prices: baked-in defaults; the feed matched no known model",
    "a fetch that landed and matched nothing is not 'not fetched yet'");
  assert.equal(note({ source: "defaults", reason: "someday" }), "prices: baked-in defaults", "a reason this view does not know: the source, which the block did say, and no invented why");
});

test("absent: a payload without the block (an older kernel) words nothing, so the modal renders no node", () => {
  assert.equal(note(undefined), "");
  assert.equal(note(null), "");
  assert.equal(note("feed"), "", "not an object");
  assert.equal(note({ source: "live", ageS: 5 }), "", "a source this view does not know says nothing rather than something false");
  assert.equal(note({}), "", "no source at all");
});

// The node: raPriceLine(text) inside initGear, evaluated with the two closure names it reads passed in (`document`
// for createElement, `raNote` for the footnote it follows), over the repo's DOM stand-in.
function lift() {
  const start = GEAR.indexOf("  var raPrice = null;"), end = GEAR.indexOf("  function raRender() {");
  assert.ok(start > 0 && end > start, "raPrice and raPriceLine sit together ahead of raRender inside initGear; re-anchor if the block moved");
  const make = nodeFactory();
  const panel = make("div"), footnote = make("div"), doc = { createElement: make };
  panel.appendChild(footnote);
  // the stand-in has no nextSibling; the real one answers the node after the footnote (null when it is last, as in the markup)
  Object.defineProperty(footnote, "nextSibling", { get: () => panel.children[panel.children.indexOf(footnote) + 1] || null });
  const api = new Function("document", "raNote", GEAR.slice(start, end) + "\nreturn { line: raPriceLine, node: function () { return raPrice; } };")(doc, footnote) as
    { line: (text: string) => void; node: () => any };
  return { panel, footnote, api };
}

test("executed: the line's node exists exactly while there is text, one node across re-renders, none (not even empty) without", () => {
  const { panel, footnote, api } = lift();
  api.line("");
  assert.equal(panel.children.length, 1, "no text, no node: an older kernel's modal is what it was");
  assert.equal(api.node(), null);
  api.line("prices: live feed, fetched just now");
  assert.equal(panel.children.length, 2, "text: one node");
  const el = panel.children[1];
  assert.equal(el, api.node());
  assert.equal(el.parentNode, panel);
  assert.equal(el.id, "ra-price");
  assert.equal(el.className, "ra-price", "the muted footnote size, gear.css");
  assert.equal(el.textContent, "prices: live feed, fetched just now");
  api.line("prices: baked-in defaults; live feed off (ROMP_PRICE_FEED=off)");
  assert.equal(panel.children.length, 2, "a re-render (metric or group button) updates the node, never stacks a second");
  assert.equal(panel.children[1], el, "the same node");
  assert.equal(el.textContent, "prices: baked-in defaults; live feed off (ROMP_PRICE_FEED=off)");
  api.line("");
  assert.equal(panel.children.length, 1, "the block gone from the payload (a loading repaint, a failed read): the node is removed, not emptied");
  assert.equal(api.node(), null);
  assert.equal(el.parentNode, null);
  assert.equal(footnote.parentNode, panel, "the footnote itself is untouched");
});

test("executed: the node is placed right after the footnote, ahead of anything that follows it", () => {
  const { panel, footnote, api } = lift();
  const after = nodeFactory()("div");
  panel.appendChild(after);
  api.line("prices: baked-in defaults; nothing fetched from the feed yet");
  assert.equal(panel.children.length, 3);
  assert.equal(panel.children[0], footnote);
  assert.equal(panel.children[1], api.node(), "between the footnote and its follower");
  assert.equal(panel.children[2], after);
});

test("wired: raRender places the line from the payload's block in both metrics, and every clearing road clears it", () => {
  // the render's last statement, after the footnote's text is set, so the footnote's own content stands beside it
  assert.match(GEAR, /session \$ estimated from token prices; fast mode draws more than shown'\) : ''\);\n(?:\s*\/\/[^\n]*\n)*\s*raPriceLine\(raPriceNote\(d\.priceFeed\)\); \}/,
    "the footnote's content is kept and the price line follows it, keyed on the payload's block alone (no metric guard: the block's presence decides)");
  // the loading repaint, the no-data return and a failed /analytics read leave no line behind
  assert.ok(GEAR.includes("raNote.textContent = ''; raPriceLine(''); return; }"), "loading");
  assert.ok(GEAR.includes("raChart.innerHTML = '<div class=ra-empty>no data</div>'; raPriceLine(''); return; }"), "no data");
  assert.ok(GEAR.includes("raNote.textContent = ''; raPriceLine(''); }); }"), "the fetch's catch");
  // no static node in the markup: the line's node is minted with its text and removed with it
  assert.ok(GEAR.includes("'<div id=ra-note class=ra-note></div>' +\n  '</div></div>';"), "the footnote stays the panel's last markup child");
  assert.ok(!GEAR.includes("id=ra-price class=ra-price"), "no empty #ra-price in the markup");
  assert.ok(GEAR.includes("raPrice.id = 'ra-price'; raPrice.className = 'ra-price'; raNote.parentNode.insertBefore(raPrice, raNote.nextSibling);"));
  // the four wordings and the absent case, as the source spells them
  assert.match(GEAR, /if \(pf\.source === 'feed'\) return 'prices: live feed' \+ \(typeof pf\.ageS === 'number' \? ', fetched ' \+ raAgo\(pf\.ageS\) : ''\);/);
  assert.match(GEAR, /pf\.reason === 'off' \? 'live feed off \(ROMP_PRICE_FEED=off\)'/, "the switch is named where the user looks");
  assert.match(GEAR, /pf\.reason === 'failed' \? 'the last feed fetch failed' \+ \(pf\.lastError \? ' \(' \+ pf\.lastError \+ '\)' : ''\)/);
  assert.match(GEAR, /\(pf\.reason === 'unfetched' \|\| pf\.reason === 'inflight'\) \? 'nothing fetched from the feed yet'/);
  assert.match(GEAR, /if \(!pf \|\| typeof pf !== 'object'\) return '';/, "absent: no block, no text");
  // the line wears the footnote's muted 11px (the font-size rule: reuse a size already on the surface)
  assert.match(GEAR_CSS, /\.ra-note \{ color: var\(--text-muted, #9aa0a6\); font-size: 11px;/);
  assert.match(GEAR_CSS, /\.ra-price \{ color: var\(--text-muted, #9aa0a6\); font-size: 11px; padding-top: 4px; \}/);
});
