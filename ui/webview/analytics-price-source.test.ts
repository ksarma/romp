// The Token usage modal's PRICE-SOURCE line (the user 2026-09-20, with the price feed's off switch): the kernel's
// /analytics payload carries `priceFeed`, the state of the per-model price table behind the modal's dollar figures,
// and the modal says where the prices came from on one muted line under the footnote: the live feed with its age,
// or the built-in defaults with the reason (the feed is off, the last fetch failed, nothing fetched yet). Three
// layers, each tested the way it can be: the WORDING is a pure function gear.js exports (raPriceNote), run here for
// real with the payload shapes; the NODE is the closure helper raPriceLine, lifted out of initGear and driven
// against the repo's DOM stand-in (present with its text, absent without, one node across re-renders); the
// render's WIRING is pinned in the source, the convention where nothing executes raRender (rail-spend.test.ts
// states it). This file, not rail-spend.test.ts, holds the price line's pins: that file's footnote pin covers the
// footnote that predates the line and is unchanged, and a source pin beside it would hold the wordings as regexes
// with the formatter never run; here a wording change fails at the text raPriceNote produces. The kernel side of
// the contract (the block in /analytics and /version) is pinned by its own tests.
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

test("live feed: the line names the feed and the fetch's age in the shell's age words (now, then minutes, hours, days)", () => {
  // the words are api-health-merge.ts agoWords', the helper the API-health popup's as-of uses, bound in gear.js as raAgo
  // (the second round of the review of PR 878: a copy of the helper here said 720 hours ago where the popup says 30 days
  // ago); analytics-price-source-states.test.ts runs the line against the helper at every boundary
  assert.equal(note({ off: false, source: "feed", ageS: 240, fetchedAt: 1_700_000_000, rows: 6, lastError: null }), "prices: live feed, fetched 4 minutes ago");
  assert.equal(note({ source: "feed", ageS: 30 }), "prices: live feed, fetched now", "under 45 s: the popup's word");
  assert.equal(note({ source: "feed", ageS: 0 }), "prices: live feed, fetched now",
    "zero, what a read in the second the fetch landed carries (the kernel's ageS is now minus fetchedAt on one clock): the age is said whenever the block has a number, and 0 is a number, not an absence");
  assert.equal(note({ source: "feed", ageS: 60 }), "prices: live feed, fetched 1 minute ago", "singular");
  assert.equal(note({ source: "feed", ageS: 3_569 }), "prices: live feed, fetched 59 minutes ago", "rounded minutes up to the hour");
  assert.equal(note({ source: "feed", ageS: 3600 }), "prices: live feed, fetched 1 hour ago", "singular hour");
  assert.equal(note({ source: "feed", ageS: 7_200 }), "prices: live feed, fetched 2 hours ago");
  assert.equal(note({ source: "feed", ageS: 90_000 }), "prices: live feed, fetched 1 day ago", "a day past 24 h, as the popup would say it; the feed's TTL is six hours, a cache kept under the switch can be older");
  assert.equal(note({ source: "feed" }), "prices: live feed", "no age in the block (an older kernel's shape): the source alone, never a made-up age");
  // a cache kept while the switch is on still prices from the feed, and the line says the feed, with its age, and
  // why no refresh will come: the user stopped the traffic, not the data (analytics-price-source-states.test.ts
  // drives the feed line's other tails: a failed refresh, the share a partial feed priced)
  assert.equal(note({ off: true, source: "feed", ageS: 600 }), "prices: live feed, fetched 10 minutes ago; refresh off (ROMP_PRICE_FEED=off)");
});

test("the feed is off: built-in defaults, and the switch is named so the reader knows what to flip", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", fetchedAt: null, ageS: null, rows: 0, lastError: null }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)");
});

test("the last fetch failed: built-in defaults with the reason the kernel recorded, never a fetched body", () => {
  // The two reasons are the kernel's own outputs: _price_feed_error_class (kernel.py) run over the exceptions its test
  // builds, an HTTPError 500 and a URLError wrapping ConnectionRefusedError 111. That function joins the exception
  // type, the HTTP status and the wrapped socket error's type and errno, and never str(e), the response body or the
  // URL, so a lastError is short and carries no status text; these literals are what the kernel sends and the only
  // shape a reader should take from here (tests/test_price_feed_off.py pins them on the kernel's side, the socket one by
  // its prefix, since the errno's text after it is the platform's; a literal fed to a pure function needs no such care).
  assert.equal(note({ off: false, source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500" }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500)");
  assert.equal(note({ source: "defaults", reason: "failed", lastError: "URLError: ConnectionRefusedError: errno 111 (Connection refused)" }),
    "prices: built-in defaults; the feed could not be fetched (URLError: ConnectionRefusedError: errno 111 (Connection refused))");
  // NOT a shape the kernel emits (its reason class has no angle brackets): this one pins that the formatter relays
  // the string as given and interprets none of it; the render places the line as text (textContent, the executed
  // node case below), so a bracket in a reason would be no hazard
  assert.equal(note({ source: "defaults", reason: "failed", lastError: "<a shape the kernel never sends>" }),
    "prices: built-in defaults; the feed could not be fetched (<a shape the kernel never sends>)",
    "a deliberately foreign reason: relayed verbatim");
  assert.equal(note({ source: "defaults", reason: "failed" }), "prices: built-in defaults; the feed could not be fetched", "a failure with no recorded reason says that much and no more");
});

test("nothing landed yet: built-in defaults, a fetch in flight worded apart from none attempted, and a landed-empty feed by what it left", () => {
  assert.equal(note({ off: false, source: "defaults", reason: "unfetched", fetchedAt: null, rows: 0 }), "prices: built-in defaults; nothing fetched from the feed yet");
  assert.equal(note({ source: "defaults", reason: "inflight" }), "prices: built-in defaults; fetching the feed now",
    "the first open of the modal: the payload is built before the fetch it started lands, and the next open shows the feed (review round 1: one wording for both states read 'nothing fetched yet' during a re-attempt after a landed or failed fetch)");
  assert.equal(note({ source: "defaults", reason: "empty", rows: 0, matched: 0 }), "prices: built-in defaults; the feed matched no known model",
    "a fetch that landed and named no known model is not 'not fetched yet'");
  assert.equal(note({ source: "defaults", reason: "empty", rows: 0, matched: 2 }), "prices: built-in defaults; the feed's rows for 2 known models could not be read",
    "the kernel's `matched` above 0 with no row in the cache: the feed named known models and their rows did not parse (a schema change at the feed), which is not a feed that renamed its ids");
  assert.equal(note({ source: "defaults", reason: "empty", rows: 0, matched: 1 }), "prices: built-in defaults; the feed's rows for 1 known model could not be read", "singular");
  assert.equal(note({ source: "defaults", reason: "empty", rows: 0 }), "prices: built-in defaults; the feed matched no known model",
    "no `matched` in the block (an older kernel): the one wording that kernel could stand behind");
  assert.equal(note({ source: "defaults", reason: "someday" }), "prices: built-in defaults", "a reason this view does not know: the source, which the block did say, and no invented why");
});

test("rows from model-prices.json: the count is said on either source, since those rows price their models whichever table the line names", () => {
  assert.equal(note({ off: true, source: "defaults", reason: "off", overrides: 1 }),
    "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off); 1 row overridden by model-prices.json",
    "the reference tells a person with the feed off to keep a rate current in the file: the line says the row took");
  assert.equal(note({ source: "defaults", reason: "failed", lastError: "HTTPError: HTTP 500", overrides: 2 }),
    "prices: built-in defaults; the feed could not be fetched (HTTPError: HTTP 500); 2 rows overridden by model-prices.json", "plural, after the reason");
  assert.equal(note({ source: "feed", ageS: 240, overrides: 1 }), "prices: live feed, fetched 4 minutes ago; 1 row overridden by model-prices.json",
    "the feed's table too: a row in the file wins over the feed's row for that model");
  assert.equal(note({ source: "feed", ageS: 7_200, lastError: "HTTPError: HTTP 500", overrides: 1 }),
    "prices: live feed, fetched 2 hours ago; the last refresh failed (HTTPError: HTTP 500); 1 row overridden by model-prices.json", "last, after the refresh's state");
  assert.equal(note({ source: "defaults", reason: "off", overrides: 0 }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "no row in effect: nothing said about the file");
  assert.equal(note({ source: "defaults", reason: "off" }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "no `overrides` in the block (an older kernel): nothing claimed");
  assert.equal(note({ source: "defaults", reason: "off", overrides: "1" }), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "the kernel's count is a number; a string is not read as one");
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
  api.line("prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)");
  assert.equal(panel.children.length, 2, "a re-render (metric or group button) updates the node, never stacks a second");
  assert.equal(panel.children[1], el, "the same node");
  assert.equal(el.textContent, "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)");
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
  api.line("prices: built-in defaults; nothing fetched from the feed yet");
  assert.equal(panel.children.length, 3);
  assert.equal(panel.children[0], footnote);
  assert.equal(panel.children[1], api.node(), "between the footnote and its follower");
  assert.equal(panel.children[2], after);
});

test("wired: raRender places the line from the payload's block in both metrics, and every clearing road clears it", () => {
  // EXECUTED over the repo's DOM stand-in: the render block (raPrice, raPriceLine and raRender, lifted from initGear with the
  // closure names it reads passed in as stubs) is driven with a synthetic payload, so the wiring is proved by the node it
  // leaves rather than by a regex over the footnote's copy (the second round of the review of PR 878: the one pin on this
  // wiring embedded the footnote's estimate sentence, so an edit to that sentence, nothing to do with the price line, went
  // red here). The kernel-side facts behind the block are pinned by tests/test_price_feed_off.py; raPriceNote is the real export.
  const start = GEAR.indexOf("  var raPrice = null;"), end = GEAR.indexOf("  function raFetch() {");
  assert.ok(start > 0 && end > start, "raPrice, raPriceLine and raRender sit together ahead of raFetch inside initGear; re-anchor if the block moved");
  const make = nodeFactory();
  const panel = make("div"), footnote = make("div");
  panel.appendChild(footnote);
  Object.defineProperty(footnote, "nextSibling", { get: () => panel.children[panel.children.indexOf(footnote) + 1] || null });
  const raState: any = { loading: false, data: null, group: "judge", periodLabel: "24 hours", window: 86400 };
  let cost = false;
  const stubs: Record<string, unknown> = {
    document: { createElement: make }, raState, raChart: make("div"), raLegend: make("div"), raNote: footnote,
    raCost: () => cost, raVal: (s: any) => (s.in || 0) + (s.out || 0), raSegments: () => [], raDate: () => "", raWhen: () => "",
    raEsc: (s: string) => s, fmtTok: () => "", fmtUsd: () => "", raFmt: () => "", raPriceNote: gear.raPriceNote,
  };
  const api = new Function(...Object.keys(stubs), GEAR.slice(start, end) + "\nreturn { render: raRender, node: function () { return raPrice; } };")(...Object.values(stubs)) as
    { render: () => void; node: () => any };
  const line = () => { const n = api.node(); return n ? n.textContent : null; };
  raState.data = { sessions: { in: 10, out: 5, cost: 0.5 }, priceFeed: { off: true, source: "defaults", reason: "off", fetchedAt: null, ageS: null, rows: 0, lastError: null } };
  api.render();
  assert.equal(line(), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "a payload with the block: the line is its wording, from the payload's block alone (no metric guard)");
  assert.equal(panel.children[1], api.node(), "placed right after the footnote");
  assert.ok(footnote.textContent.length > 0, "the footnote's own content stands beside it");
  cost = true; api.render();
  assert.equal(line(), "prices: built-in defaults; live feed off (ROMP_PRICE_FEED=off)", "the cost metric too: the block's presence decides");
  raState.data = { sessions: { in: 10, out: 5 }, priceFeed: { source: "feed", ageS: 240 } };
  api.render();
  assert.equal(line(), "prices: live feed, fetched 4 minutes ago", "a re-render with a new block updates the one node");
  assert.equal(panel.children.length, 2, "one node across re-renders");
  raState.loading = true; api.render();
  assert.equal(api.node(), null, "the loading repaint clears the line");
  raState.loading = false; raState.data = null; api.render();
  assert.equal(api.node(), null, "the no-data return clears the line");
  raState.data = { sessions: { in: 1, out: 1 } }; api.render();
  assert.equal(api.node(), null, "a payload without the block (an older kernel) leaves no node");
  // the failed /analytics read's catch lives in raFetch, outside the lifted block: pinned as source text (the two roads above are executed)
  assert.ok(GEAR.includes("raNote.textContent = ''; raPriceLine(''); }); }"), "the fetch's catch clears the line too");
  // WHERE the call lives, anchored on the call alone and never on the footnote's copy: the render's last statement, after the
  // footnote's text is set. This guards only the call's place; the executed assertions above prove what raPriceLine produces.
  const render = GEAR.slice(start, end);
  const call = render.indexOf("raPriceLine(raPriceNote(d.priceFeed)); }"), note = render.indexOf("raNote.textContent = (fromTxt ?");
  assert.ok(call > 0 && note > 0 && call > note,
    "raRender calls raPriceLine(raPriceNote(d.priceFeed)) as its last statement, after the raNote.textContent assignment (a pin on where the call lives; the executed cases above prove what it produces)");
  // no static node in the markup: the line's node is minted with its text and removed with it
  assert.ok(GEAR.includes("'<div id=ra-note class=ra-note></div>' +\n  '</div></div>';"), "the footnote stays the panel's last markup child");
  assert.ok(!GEAR.includes("id=ra-price class=ra-price"), "no empty #ra-price in the markup");
  assert.ok(GEAR.includes("raPrice.id = 'ra-price'; raPrice.className = 'ra-price'; raNote.parentNode.insertBefore(raPrice, raNote.nextSibling);"));
  // the wordings and the absent case, as the source spells them (the executed cases above pin what they produce)
  assert.match(GEAR, /if \(pf\.source === 'feed'\) \{\n(?:[^\n]*\n){2}\s*var partial = typeof pf\.rows === 'number' && typeof pf\.known === 'number' && pf\.rows < pf\.known;\n\s*var line = 'prices: live feed' \+ \(partial \? ' for ' \+ pf\.rows \+ ' of ' \+ pf\.known \+ ' models' : ''\)\n\s*\+ \(typeof pf\.ageS === 'number' \? ', fetched ' \+ raAgo\(pf\.ageS\) : ''\);/,
    "the feed branch: the head, the share when the block carries both counts, the age when the block has a number");
  assert.match(GEAR, /pf\.reason === 'off' \? 'live feed off \(ROMP_PRICE_FEED=off\)'/, "the switch is named where the user looks");
  assert.match(GEAR, /pf\.reason === 'failed' \? 'the feed could not be fetched' \+ \(pf\.lastError \? ' \(' \+ pf\.lastError \+ '\)' : ''\)/);
  assert.match(GEAR, /pf\.reason === 'inflight' \? 'fetching the feed now'/, "a fetch in flight, worded apart from none attempted");
  assert.match(GEAR, /pf\.reason === 'unfetched' \? 'nothing fetched from the feed yet'/);
  assert.match(GEAR, /if \(!pf \|\| typeof pf !== 'object'\) return '';/, "absent: no block, no text");
  // the line wears the footnote's muted 11px (the font-size rule: reuse a size already on the surface)
  assert.match(GEAR_CSS, /\.ra-note \{ color: var\(--text-muted, #9aa0a6\); font-size: 11px;/);
  assert.match(GEAR_CSS, /\.ra-price \{ color: var\(--text-muted, #9aa0a6\); font-size: 11px; padding-top: 4px; \}/);
});
