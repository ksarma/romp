// The .svg tab road's executed witness (the fifth review round of the price-feed-off change, extra6-2; before the sixth round's review
// widened to the row's whole list and to Firefox and WebKit): on the web dashboard a Cmd, Ctrl or middle click on a path link to an
// .svg in a viewed file reaches openFileTab (ui/webview/preview.ts), which opens the kernel's /file URL, or a remote session's
// /remote/<host>/file relay, in the browser's own tab; the tab is an svg document, sandboxed, that loads the hosts its own markup
// names. Two real servers on the loopback: the page server at http://localhost:P plays the kernel, answering /file and
// /remote/labhost/file for an .svg with the headers the kernel writes on that success, read from kernel/kernel.py's source and pinned
// by value below (Handler._send's four unconditional headers and _media_policy_headers' sandbox: a source pin, stated as such; the
// wire-level tie, the kernel's own Handler writing exactly these on both arms, is tests/test_security_price_feed.py); the media
// listener at http://127.0.0.1:Q records every request line with its Cookie, Referer, Origin, Sec-Fetch-Site and Sec-Fetch-Mode.
// localhost and 127.0.0.1 are two sites, so of the two cookies set on 127.0.0.1 the SameSite=None; Secure one rides a cross-site load
// made without CORS in Chromium and Firefox and the Lax one does not (WebKit sends neither to this plain-http host on a cross-site
// load, below). What the svg names is the census row's list, read from scripts/network-inventory.py SVG_TAB_ROW (its sent cell, with
// PAINT_LIST spliced in as --table prints it), never a literal list here. The row's list names examples ("among them") of its general
// rule, that the tab loads each resource its markup names from that resource's host; the list is not the population (a CSS background,
// a srcset, a picture source, a video's poster, an input image or a preload loads by the same rule and is not among them). The two-way
// check is between the plants here and the named examples: every example the row names has a plant in LOADS or PAINT_EL, and every
// plant is an example the row names, so an example added to the row reds this leg until it plants and observes it. The elements the
// cookie clause's two marks name are held the same way: read from the row's words (CRED_MARK_RE, ANON_MARK_RE), they must be the
// elements the plants marked that way put their loads on, read from each plant's markup (markedElements), so an element the clause adds
// with no plant, or a marked plant on an element the clause does not name, reds. The script is read as source by regex, as kernel.py
// is: SVG_TAB_ROW must stay five cells of one line each, with PAINT_LIST, a parenthesized run of literals, spliced into the sent cell
// once, the cell's literals escaping only a quote or a backslash; a read that does not match (a reformatted row, say) reds with an
// assertion naming what it looked for, never a skip or an empty list. Each load arrives and carries what the row's clauses say, each
// held by its words (SENT_CLAUSE with the marks CRED_MARK_RE and ANON_MARK_RE read, FRAME_TURN, REFERER_CAUSE_RE, RELAX_CLAUSE,
// FRAME_REFERER, SHEET_REFERER_RE, TOKEN_CLAUSE), so a reworded clause reds here until the assertions follow it. Cookies: a load made
// without CORS, or a load the markup marks crossorigin="use-credentials" on one of the five elements the clause names (an svg image, an
// img, a stylesheet link, a video and an audio, each planted), carries the cookies that browser sends cross-site; a paint reference, a
// web font outside WebKit, or a load the markup marks crossorigin="anonymous" on the same five elements (each planted, a video's poster
// aside), carries none; every CORS request carries Origin null. Referer, for a load to another site (every load here is one: the page
// on localhost, the media host on 127.0.0.1), per engine as the row's words name the engines: in Chromium none of the tab's own loads
// carries one in any scene but scene 3, the control without the sandbox, where the mask reference carries the page's origin (the other
// scenes keep the sandbox: the sandboxed tabs, the arm with the page's Referrer-Policy removed and the sandbox kept, and both
// relaxation scenes below); in Firefox and WebKit none under the /file headers except in the relaxation scenes below, where each load
// the relaxing markup reaches carries the dashboard's origin, and the dashboard's origin in the arm. Two relaxation scenes, each a
// route of its own under the /file headers opened at an address whose query carries a token parameter, run in every engine and are held
// to the page's policy: each navigation's response is read as the arm's is and must carry the /file headers, the Referrer-Policy among
// them. The meta scene serves an svg whose first load is the CSS @import sheet, which carries no Referer, and whose foreignObject then
// holds a referrer meta and, after it, an img and a frame: each load after the meta carries exactly the dashboard's origin in Firefox
// and WebKit and none in Chromium (two-sided, so the scene proves the relaxation happened, and no path or query). The attribute scene
// serves an svg with no meta and two imgs, one with referrerpolicy="unsafe-url" and one without: in Firefox and WebKit the first
// carries exactly the dashboard's origin and the second none, so the attribute is what relaxes it, and in Chromium neither carries a
// Referer. The loads a stylesheet names in turn (a nested @import and a cursor, named by the sheet the row's CSS @import plant loads)
// carry, in the engines the row names for it, null or that stylesheet's own address, and in the rest what the tab's own loads carry in
// that scene; the framed page's own loads, and in the meta scene those of a framed page that relaxes its own policy, carry null or that
// frame's origin. In the sandboxed tabs (Chromium's scenes 1 and 2, the Firefox and WebKit sandboxed tab), the arm and both relaxation
// scenes, no request to the other site carries a Referer that names the dashboard's origin with a path or query after it; the controls
// without the sandbox (Chromium's scene 3, the Firefox and WebKit control) are not read for it. Three texts are checked on one shape
// each, though their words cover more: the framed-page clause on frames the media host serves, whose own loads go to that host; the
// stylesheet clause on a stylesheet the media host serves, whose loads in turn go to that host; and the referrerpolicy attribute on an
// img. The token clause is a fact of fileUrl: each address it builds (for a file of no session, of a session on this machine and of one
// on an attached machine) takes one of the clause's forms and carries no token, the tab Chromium opens carries none though the opener
// page's address does; in Chromium's scenes 1 and 2, the tabs the opener page opens, no request to the other site carries that page's
// token; and in each relaxation scene no request to the other site carries the scene's token parameter. The `use` that names another
// host and the `filter` load in no engine: the engine's own refusal report is the event waited on where it makes one (Chromium and
// Firefox for both, WebKit for the use), and WebKit, which reports no refused filter, has its filter absence read once every other load
// has arrived; an inline script never runs. Two per-engine literals were measured at the engine builds this leg ran on:
// CROSS_SITE_COOKIE, what each engine sends this fixture's media host on a load made without CORS and on a credentialed one, and
// REFUSAL_REPORTED, which refusals its console reports; an engine update that changes a console report, or the cookie Chromium or
// Firefox sends, reds the leg with a message naming the engine, and the literal is measured again. Each CORS request is asserted a CORS
// request by its Sec-Fetch-Mode (cors), the request kind its Origin null implies; the mode says nothing of cookies, since a CORS
// request made with credentials can carry them, as the credentialed loads do in Chromium and Firefox. What keeps a paint reference, a
// web font in Chromium and Firefox, or an anonymous load cookieless is its fetch's credentials mode, which the specifications set
// (same-origin, which sends no cookie on a cross-origin request, as each of these is) and which the wire does not show, so the clause's
// no-cookie half is read against loads that carry the cookie. Those loads exist in Chromium and Firefox: in the same tab the loads made
// without CORS and the credentialed ones carry the SameSite=None cookie, and each paint reference, web font and anonymous load must
// carry none. In WebKit none can on this fixture: the fixture's cross-site cookie (SameSite=None, Secure) is sent to the plain-http
// media host on no cross-site load, so WebKit's loads carry none and its cookie assertions cannot fail here; there the no-cookie half
// rests on that credentials mode, which no run here observes. The arm serves the same svg with the sandbox kept and the page's
// Referrer-Policy removed; NO_POLICY_HEADERS is held to the /file headers less exactly that one, and so is the response each engine
// received, its headers of the names the /file headers carry compared with NO_POLICY_HEADERS: in Chromium in the order served, read
// from the raw header text the DevTools protocol gives, since Chromium's report sorts them by name; in Firefox and WebKit as the
// engine reports them, which holds the headers and the order of distinct names, not where a repeated name sits on the wire (each
// groups same-named headers its own way: Firefox moves the earlier one down, WebKit the later one up). The relaxation scenes'
// responses are read the same way and held to SVG_FILE_HEADERS, whose two Content-Security-Policy headers stand apart, so in Firefox
// and WebKit the list they are held to is grouped the way that engine groups it (REPORTED_GROUPING, measured at the builds this leg
// ran on). Chromium keeps the opener and the relay: it opens the tab with openFileTab itself, bundled from preview.ts and called from
// a real Control-click, so its URL is fileUrl's; scene 2 is the relay's URL; scene 3 is the control for the sandbox: the same svg
// without it (the Referrer-Policy kept) runs its script, its mask reference sends the page's origin as Referer, and the `use` naming
// another host still does not load. Firefox and WebKit exercise the document: each navigates a tab to the same /file URL directly,
// since the opener is the same JavaScript in every engine and what the engine decides is what the document loads (the row's list is
// claimed for every engine; the paint list is the engine's, as PAINT_LIST says). The two no-sandbox controls assert different sets.
// Chromium's scene 3 waits for every load, the script's fetch and the refusal reports, then asserts the mask request's Referer (the
// page's origin) and that the `use` naming another host does not load; it reads the script's run by its fetch alone. Firefox's and
// WebKit's control reads the script's mark (set, data-ran) once the document is parsed, waits for the same loads, fetch and refusal
// reports, and asserts that the `use` naming another host does not load; it logs its mask request and does not assert that request's
// Referer. In each scene that plants it, each engine's own refusal report names that `use`'s URL, so the plant is a reference the
// engine read and refused. Every wait is on a request event or the page's own event, never a timer alone; the bounds are the failure.
// Skips LOUDLY without a playwright browser, as the other browser legs do; in CI it skips because the vscode-extension job runs npm
// test before it installs Playwright's Chromium, and installs no Firefox or WebKit. Synthetic values only: loopback URLs, invented
// cookie names, a placeholder uuid and a TESTHOST path.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as http from "node:http";
import * as path from "node:path";
import type { AddressInfo } from "node:net";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const INVENTORY = fs.readFileSync(path.resolve(EXT, "..", "scripts", "network-inventory.py"), "utf8");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const SVG_DOC = '<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="red"/></pattern>'
  + '<filter id="f"><feGaussianBlur stdDeviation="1"/></filter><clipPath id="c"><rect width="4" height="4"/></clipPath><mask id="m"><rect width="4" height="4" fill="white"/></mask>'
  + '<marker id="k" markerWidth="4" markerHeight="4" refX="2" refY="2"><circle cx="2" cy="2" r="2"/></marker><g id="u"><rect width="4" height="4"/></g></defs></svg>';

// ── the headers, from the code that sends them ──────────────────────────────────────────────────────

/** Handler._send's unconditional two-literal send_header lines (the chat-media witness reads the same lines). */
function sendHeaders(): Record<string, string> {
  const m = /\n    def _send\(self, code, body, ctype, cache=None, headers=None\):\n([\s\S]*?)\n        for k, v in \(headers or \{\}\)\.items\(\):/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py Handler._send up to its caller-supplied headers loop");
  const out: Record<string, string> = {};
  for (const h of m![1].matchAll(/^        self\.send_header\("([^"]+)", "([^"]+)"\)/gm)) out[h[1]] = h[2];
  return out;
}
/** _media_policy_headers' return for image/svg+xml, the one pair it adds. */
function svgPolicy(): [string, string] {
  const m = /\ndef _media_policy_headers\(mime\):\n[\s\S]*?\n    return \{"([^"]+)": "([^"]+)"\} if mime == _IMG_MIME\["\.svg"\] else \{\}\n/.exec(KERNEL);
  assert.ok(m, "kernel/kernel.py _media_policy_headers' return");
  return [m![1], m![2]];
}
/** What a /file success for an .svg carries at this head, by value (tests/test_security_price_feed.py reads the same on the wire,
 *  both arms): the four every page carries, the sandbox beside the framing policy under the same name, the type and no-cache. */
export const SVG_FILE_HEADERS: [string, string][] = [
  ["Content-Type", "image/svg+xml"],
  ["X-Content-Type-Options", "nosniff"],
  ["X-Frame-Options", "SAMEORIGIN"],
  ["Content-Security-Policy", "frame-ancestors 'self'"],
  ["Referrer-Policy", "same-origin"],
  ["Content-Security-Policy", "sandbox"],
  ["Cache-Control", "no-cache"],
];
/** The arm for what withholds the tab's Referer: the same success with the page's Referrer-Policy removed and the sandbox kept. */
const NO_POLICY_HEADERS: [string, string][] = SVG_FILE_HEADERS.filter(([k]) => k !== "Referrer-Policy");
/** The source pin every test of this file runs first: the headers read from _send and _media_policy_headers are SVG_FILE_HEADERS. */
function pinnedHeaders(): { send: Record<string, string>; pol: [string, string] } {
  const send = sendHeaders(), pol = svgPolicy();
  const read: [string, string][] = [["Content-Type", "image/svg+xml"], ...Object.entries(send), pol, ["Cache-Control", "no-cache"]];
  assert.deepEqual(read, SVG_FILE_HEADERS, "the /file success for an .svg carries these, read from _send and _media_policy_headers: " + JSON.stringify(read));
  return { send, pol };
}

// ── the row's list, from the script that prints it ──────────────────────────────────────────────────

/** PAINT_LIST as scripts/network-inventory.py binds it: a parenthesized run of adjacent string literals, joined. */
function paintListText(): string {
  const m = /\nPAINT_LIST = \(((?:\s*"[^"\\\n]*")+)\)\n/.exec(INVENTORY);
  assert.ok(m, "scripts/network-inventory.py PAINT_LIST, a parenthesized run of string literals");
  return Array.from(m![1].matchAll(/"([^"\\\n]*)"/g)).map((x) => x[1]).join("");
}
/** SVG_TAB_ROW's sent cell as --table prints it: the cell's one line of literals with PAINT_LIST spliced in where it is named. */
export function rowSent(): string {
  const row = /\nSVG_TAB_ROW = \(("an \.svg opened in its own tab \(browser\)",\n[\s\S]*?)\)\n/.exec(INVENTORY);
  assert.ok(row, "scripts/network-inventory.py SVG_TAB_ROW, the .svg tab road's row");
  const cells = row![1].split("\n").map((l) => l.trim().replace(/,$/, ""));
  assert.equal(cells.length, 5, "SVG_TAB_ROW is five cells, one line each");
  const parts = cells[3].split(/"\s*\+\s*PAINT_LIST\s*\+\s*"/);
  assert.ok(parts.length === 2 && parts[0].startsWith('"') && parts[1].endsWith('"') && !parts.some((p) => /"\s*\+|\+\s*"/.test(p)),
    "SVG_TAB_ROW's sent cell is literals with PAINT_LIST spliced in once and nothing else: " + cells[3].slice(0, 160));
  // the literals' text as Python reads it: an escaped quote or backslash is the character; any other escape reds the read
  const text = (src: string) => {
    assert.ok(/^(?:[^\\"]|\\["\\])*$/.test(src), "SVG_TAB_ROW's sent cell is one literal each side of PAINT_LIST, escaping only a quote or a backslash: " + src.slice(0, 160));
    return src.replace(/\\(["\\])/g, "$1");
  };
  return text(parts[0].slice(1)) + paintListText() + text(parts[1].slice(0, -1));
}
/** A list as the row writes it, "a, b (c, d or e), f": split on the commas outside parentheses. */
function splitList(s: string): string[] {
  const out: string[] = [];
  let depth = 0, cur = "";
  for (const ch of s) {
    if (ch === "(") depth++;
    if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur.trim()); cur = ""; } else cur += ch;
  }
  out.push(cur.trim());
  return out;
}
const LIST_RE = /loads each resource its markup names from that resource's host \(whether or not the host is on the gear's Pictures from the web in files list\), among them (.+?), and paint references: /;
const PAINT_LIST_RE = /in Chromium a ((?:`[a-z-]+`, )*`[a-z-]+` or `[a-z-]+`) whose `url\(\)` names another host loads from that host/;
const PAINT_MIN_RE = /in Firefox and WebKit at least a `([a-z-]+)` does/;
const PAINT_NONE_RE = /and a `([a-z-]+)` does in no engine/;
const USE_NONE_RE = /; a `([a-z]+)` that names another host loads in no engine;/;
// the framed page's clause, held by its text as SENT_CLAUSE is: the framed page's own loads are observed below
const FRAME_TURN = "a frame the markup embeds is a page from that host, which loads what that page names in turn";
// the two marks the cookie clause names, each read from the row with the elements it names (a load marked use-credentials carries what
// the engine sends cross-site, one marked anonymous none): the credentialed clause's list is captured, and the anonymous clause names
// "one of those elements", that list, or a list of its own, captured; population() holds each list both ways to the elements the
// plants marked that way use (markedElements)
const ELEMENT_LIST = "((?:`[^`]+`, )*`[^`]+` or `[^`]+`)";
const CRED_MARK_RE = new RegExp("a load the markup marks `crossorigin=\"use-credentials\"` on an? " + ELEMENT_LIST + " element");
const ANON_MARK_RE = new RegExp("a load the markup marks `crossorigin=\"anonymous\"` on (?:one of those elements|an? " + ELEMENT_LIST + " element) "
  + "\\(a video's poster aside\\)");
// the cookie clause the per-request asserts below carry out, held by its text so a reworded clause reds here until they follow it, the
// two marks as the row words them (CRED_MARK_RE's and ANON_MARK_RE's matches) spliced in where they stand
const SENT_CLAUSE = (cred: string, anon: string) => "a load the browser makes without CORS (an image, a stylesheet, a frame, a media element, an "
  + "embedded object, or in WebKit a web font), or " + cred + ", carries whatever cookies that browser sends cross-site to that host; a paint "
  + "reference, a web font in Chromium and Firefox, or " + anon + ", carries none";
// the Referer clause, for a load to another site (every load this leg observes is one), read from the row's words in parts so the red
// for a missing part names it: the engines in which the sandbox withholds the tab's own Referer (captured first) and those in which the
// page's Referrer-Policy does, the relaxation the second may meet, a framed page's loads and the stylesheet's loads in turn (the engines
// in which a stylesheet's loads carry at most its own address, then those in which they carry what the tab's own loads carry); and the
// token clause, a fact of fileUrl's address
const ENGINE_LIST = "([A-Z][A-Za-z]*(?:(?:, | and )[A-Z][A-Za-z]*)*)";
const REFERER_CAUSE_RE = new RegExp("for a load to another site: in " + ENGINE_LIST + " none of the tab's own loads carries a Referer, the sandbox "
  + "withholding it; in " + ENGINE_LIST + " the page's `Referrer-Policy` withholds it");
const RELAX_CLAUSE = "and markup that relaxes that policy (a referrer `meta` or a `referrerpolicy` attribute) makes such a load carry at most the dashboard's origin";
const FRAME_REFERER = "a framed page's loads to another site carry at most that frame's origin";
const SHEET_REFERER_RE = new RegExp("and those a stylesheet names in turn at most that stylesheet's own address in " + ENGINE_LIST
  + " and what the tab's own loads carry in " + ENGINE_LIST);
const TOKEN_CLAUSE = "and the tab's address (`/file?path=...` or `/file?path=...&sid=...`, or its `/remote/<host>/file` form) carries no serve token";
const ENGINES = ["chromium", "firefox", "webkit"];
type RowList = { loads: string[]; chromium: string[]; min: string; none: string; useNone: string; credMark: string; anonMark: string; marked: Record<Mark, string[]>;
  bySandbox: string[]; byPolicy: string[]; sheetOwn: string[]; sheetAsTab: string[]; cause: string; sandboxHalf: string };
/** The row's loads, one item per load (a parenthesized list opens into its items, "HTML inside a `foreignObject`: a frame"), the
 *  paint list each engine loads and the elements each of the cookie clause's two marks names, from the sent cell: the named examples
 *  the scenes plant and observe (examples of the row's general rule, not the population). */
function rowList(sent: string): RowList {
  const lm = LIST_RE.exec(sent);
  assert.ok(lm, "SVG_TAB_ROW's sent cell names the general rule and its examples (\"loads each resource its markup names from that resource's host "
    + "(whether or not the host is on the gear's Pictures from the web in files list), among them ..., and paint references: \")");
  const loads: string[] = [];
  for (const item of splitList(lm![1])) {
    const sub = /^(.*?) \((.*)\)$/.exec(item);
    if (!sub) { loads.push(item); continue; }
    const inner = splitList(sub[2]);
    const last = inner.pop()!.split(" or ");
    for (const s of [...inner, ...last]) loads.push(sub[1] + ": " + s);
  }
  const cm = PAINT_LIST_RE.exec(sent), mn = PAINT_MIN_RE.exec(sent), no = PAINT_NONE_RE.exec(sent), um = USE_NONE_RE.exec(sent);
  assert.ok(cm && mn && no, "SVG_TAB_ROW's sent cell carries PAINT_LIST: the Chromium list, the Firefox/WebKit attribute and the no-engine attribute");
  assert.ok(um, "SVG_TAB_ROW's sent cell names the element that loads in no engine when it names another host (\"; a `use` that names another host loads in no engine;\")");
  assert.ok(sent.includes(FRAME_TURN), "SVG_TAB_ROW's sent cell says a framed page loads what it names in turn: " + FRAME_TURN);
  const cr = CRED_MARK_RE.exec(sent);
  assert.ok(cr && sent.includes(", or " + cr[0] + ", carries whatever cookies that browser sends cross-site to that host;"),
    "SVG_TAB_ROW's sent cell names the loads that carry the cookies the browser sends cross-site whatever their fetch, and the elements they are on "
    + "(\", or a load the markup marks `crossorigin=\"use-credentials\"` on an <elements> element, carries whatever cookies that browser sends cross-site to that host;\")");
  const an = ANON_MARK_RE.exec(sent);
  assert.ok(an && sent.includes(", or " + an[0] + ", carries none"), "SVG_TAB_ROW's sent cell names the anonymous loads that carry no cookie, and the elements "
    + "they are on (\", or a load the markup marks `crossorigin=\"anonymous\"` on one of those elements (a video's poster aside), carries none\", or on an <elements> element)");
  assert.ok(sent.includes(SENT_CLAUSE(cr![0], an![0])), "SVG_TAB_ROW's sent cell carries the cookie clause the per-request asserts carry out: " + SENT_CLAUSE(cr![0], an![0]));
  // each mark's elements as the clause names them: the backticked items of its list, the anonymous clause's "those elements" being the
  // credentialed clause's list
  const items = (s: string) => Array.from(s.matchAll(/`([^`]+)`/g)).map((x) => x[1]);
  const marked: Record<Mark, string[]> = { "use-credentials": items(cr![1]), "anonymous": an![1] === undefined ? items(cr![1]) : items(an![1]) };
  const rc = REFERER_CAUSE_RE.exec(sent);
  assert.ok(rc, "SVG_TAB_ROW's sent cell says, for a load to another site, per engine what withholds the tab's own Referer (\"for a load to another "
    + "site: in <engines> none of the tab's own loads carries a Referer, the sandbox withholding it; in <engines> the page's `Referrer-Policy` withholds it\")");
  assert.ok(sent.includes(rc![0] + ", " + RELAX_CLAUSE), "SVG_TAB_ROW's sent cell says what markup that relaxes the page's policy makes such a load carry, "
    + "in the engines where that policy withholds the Referer: " + RELAX_CLAUSE);
  assert.ok(sent.includes(RELAX_CLAUSE + "; " + FRAME_REFERER), "SVG_TAB_ROW's sent cell says what Referer a framed page's loads to another site carry: " + FRAME_REFERER);
  const sm = SHEET_REFERER_RE.exec(sent);
  assert.ok(sm && sent.includes(FRAME_REFERER + ", " + sm[0]), "SVG_TAB_ROW's sent cell says, per engine, what Referer the loads a stylesheet names in turn "
    + "carry (\"and those a stylesheet names in turn at most that stylesheet's own address in <engines> and what the tab's own loads carry in <engines>\")");
  assert.ok(sent.includes(TOKEN_CLAUSE), "SVG_TAB_ROW's sent cell says the tab's address, in each of its forms, carries no serve token: " + TOKEN_CLAUSE);
  const engines = (s: string) => s.split(/, | and /).map((x) => x.toLowerCase());
  const bySandbox = engines(rc![1]), byPolicy = engines(rc![2]), sheetOwn = engines(sm![1]), sheetAsTab = engines(sm![2]);
  assert.deepEqual([...bySandbox, ...byPolicy].sort(), ENGINES, "the row's Referer clause names each engine once, under the sandbox or under the policy: " + rc![0]);
  assert.deepEqual([...sheetOwn, ...sheetAsTab].sort(), ENGINES, "the row's stylesheet clause names each engine once: " + sm![0]);
  return { loads, chromium: Array.from(cm![1].matchAll(/`([a-z-]+)`/g)).map((x) => x[1]), min: mn![1], none: no![1], useNone: um![1], credMark: cr![0],
    anonMark: an![0], marked, bySandbox, byPolicy, sheetOwn, sheetAsTab, cause: rc![0] + ", " + RELAX_CLAUSE,
    sandboxHalf: rc![0].slice(0, rc![0].indexOf("; in ")) };
}

// ── the plants: one per load the row names ──────────────────────────────────────────────────────────

type Parts = { prolog?: string; style?: string; body?: string; fo?: string };
type Mark = "use-credentials" | "anonymous";
type Load = { files: string[]; cors: boolean | string[]; marks?: Record<string, Mark>; turn?: string[]; parts: (u: (f: string) => string) => Parts };
/** Every load of the row's list, keyed by the row's own words for it; cors says which half of the cookie clause it falls under
 *  (a list: the engines in which it is a CORS request, as the clause names them); marks names the files the markup marks with a
 *  crossorigin value, each on one of the five elements the clause names (on those elements CRED_MARK_RE's load is a CORS request that
 *  carries the cookies the engine sends cross-site, ANON_MARK_RE's one that carries none; the element is read from the markup by
 *  markedElements); turn names the loads the item's stylesheet names in turn (SHEET_REFERER_RE), served by the media host in sheetCss. */
export const LOADS: Record<string, Load> = {
  "an `image` element's `href` or `xlink:href`": { files: ["image.png", "ximage.png", "cimage.png", "aimage.png"], cors: false,
    marks: { "cimage.png": "use-credentials", "aimage.png": "anonymous" },
    parts: (u) => ({ body: `<image href="${u("image.png")}" width="10" height="10"/><image xlink:href="${u("ximage.png")}" x="12" width="10" height="10"/>`
      + `<image crossorigin="use-credentials" href="${u("cimage.png")}" y="150" width="10" height="10"/>`
      + `<image crossorigin="anonymous" href="${u("aimage.png")}" x="12" y="150" width="10" height="10"/>` }) },
  "a CSS `@import`": { files: ["import.css"], cors: false, turn: ["nested.css", "nested-cursor.png"], parts: (u) => ({ style: `@import url("${u("import.css")}");` }) },
  "an `xml-stylesheet` instruction": { files: ["pi.css"], cors: false, parts: (u) => ({ prolog: `<?xml-stylesheet type="text/css" href="${u("pi.css")}"?>` }) },
  "an `feImage`": { files: ["feimage.png"], cors: false,
    parts: (u) => ({ body: `<filter id="fi"><feImage href="${u("feimage.png")}" width="10" height="10"/></filter><rect x="260" width="10" height="10" filter="url(#fi)"/>` }) },
  "HTML inside a `foreignObject`: an `img`": { files: ["fo-img.png", "fo-cimg.png", "fo-aimg.png"], cors: false,
    marks: { "fo-cimg.png": "use-credentials", "fo-aimg.png": "anonymous" },
    parts: (u) => ({ fo: `<img src="${u("fo-img.png")}" width="10" height="10"/><img crossorigin="use-credentials" src="${u("fo-cimg.png")}" width="10" height="10"/>`
      + `<img crossorigin="anonymous" src="${u("fo-aimg.png")}" width="10" height="10"/>` }) },
  "HTML inside a `foreignObject`: a stylesheet": { files: ["fo-link.css", "fo-clink.css", "fo-alink.css"], cors: false,
    marks: { "fo-clink.css": "use-credentials", "fo-alink.css": "anonymous" },
    parts: (u) => ({ fo: `<link rel="stylesheet" href="${u("fo-link.css")}"/><link rel="stylesheet" crossorigin="use-credentials" href="${u("fo-clink.css")}"/>`
      + `<link rel="stylesheet" crossorigin="anonymous" href="${u("fo-alink.css")}"/>` }) },
  "HTML inside a `foreignObject`: a frame": { files: ["fo-frame.html"], cors: false, parts: (u) => ({ fo: `<iframe src="${u("fo-frame.html")}" width="20" height="20"></iframe>` }) },
  "HTML inside a `foreignObject`: a video": { files: ["fo-video.mp4", "fo-cvideo.mp4", "fo-avideo.mp4"], cors: false,
    marks: { "fo-cvideo.mp4": "use-credentials", "fo-avideo.mp4": "anonymous" },
    parts: (u) => ({ fo: `<video src="${u("fo-video.mp4")}" width="20" height="20"></video><video crossorigin="use-credentials" src="${u("fo-cvideo.mp4")}" width="20" height="20"></video>`
      + `<video crossorigin="anonymous" src="${u("fo-avideo.mp4")}" width="20" height="20"></video>` }) },
  "HTML inside a `foreignObject`: audio": { files: ["fo-audio.mp3", "fo-caudio.mp3", "fo-aaudio.mp3"], cors: false,
    marks: { "fo-caudio.mp3": "use-credentials", "fo-aaudio.mp3": "anonymous" },
    parts: (u) => ({ fo: `<audio src="${u("fo-audio.mp3")}" controls="controls"></audio><audio crossorigin="use-credentials" src="${u("fo-caudio.mp3")}" controls="controls"></audio>`
      + `<audio crossorigin="anonymous" src="${u("fo-aaudio.mp3")}" controls="controls"></audio>` }) },
  "HTML inside a `foreignObject`: an object": { files: ["fo-object.png"], cors: false, parts: (u) => ({ fo: `<object data="${u("fo-object.png")}" width="10" height="10"></object>` }) },
  "HTML inside a `foreignObject`: an embed": { files: ["fo-embed.png"], cors: false, parts: (u) => ({ fo: `<embed src="${u("fo-embed.png")}" width="10" height="10"/>` }) },
  "a cursor image": { files: ["cursor.png"], cors: false,
    parts: (u) => ({ style: `.cu { cursor: url("${u("cursor.png")}"), auto; }`, body: `<rect class="cu" x="272" width="10" height="10"/>` }) },
  "a web font": { files: ["font.woff2"], cors: ["chromium", "firefox"],
    parts: (u) => ({ style: `@font-face { font-family: wf; src: url("${u("font.woff2")}") format("woff2"); } .wf { font-family: wf; }`, body: `<text class="wf" x="10" y="50">font</text>` }) },
};
/** The stylesheet the CSS `@import` plant loads, as the media host serves it: a nested `@import` and a cursor, the loads it names in
 *  turn (that item's turn files), whose Referer the row's stylesheet clause names per engine. */
function sheetCss(M: string, t: string): string {
  return `@import url("${M}/${t}-nested.css"); svg { cursor: url("${M}/${t}-nested-cursor.png"), auto; }`;
}
/** The meta scene's svg, served under the /file headers at RELAX_ROUTES.meta: its first load is the CSS `@import` plant's sheet
 *  (whose loads in turn follow), started before any relaxing markup; then a referrer meta inside the foreignObject, then an img and a
 *  frame whose loads start after the meta is parsed (RELAXED: the tab's own loads the meta reaches); the frame's page relaxes its own
 *  policy by a meta and a referrerpolicy attribute (RELAX_FRAME, its own loads, served by the media host). */
const RELAXED: Record<string, string> = { "rmeta.png": "an img after the referrer meta", "rframe.html": "a frame after the referrer meta" };
const RELAX_FRAME = ["rframe-img.png", "rframe-attr.png"];
function relaxSvg(M: string, t: string): string {
  const u = (f: string) => `${M}/${t}-${f}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">\n<style>@import url("${u("import.css")}");</style>\n`
    + `<foreignObject width="200" height="100"><div xmlns="http://www.w3.org/1999/xhtml">`
    + `<meta name="referrer" content="unsafe-url"/>`
    + `<img src="${u("rmeta.png")}" width="4" height="4"/><iframe src="${u("rframe.html")}" width="20" height="20"></iframe>`
    + `</div></foreignObject></svg>`;
}
/** The attribute scene's svg, served under the /file headers at RELAX_ROUTES.attr: no referrer meta, and two imgs in the
 *  foreignObject, one without a referrerpolicy attribute (RELAX_PLAIN) and one with referrerpolicy="unsafe-url" (RELAX_ATTR), so the
 *  attribute is the only markup that can relax the page's policy for its load. */
const RELAX_PLAIN = "rplain.png", RELAX_ATTR = "rattr.png";
function relaxAttrSvg(M: string, t: string): string {
  const u = (f: string) => `${M}/${t}-${f}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">\n`
    + `<foreignObject width="200" height="100"><div xmlns="http://www.w3.org/1999/xhtml">`
    + `<img src="${u(RELAX_PLAIN)}" width="4" height="4"/><img referrerpolicy="unsafe-url" src="${u(RELAX_ATTR)}" width="4" height="4"/>`
    + `</div></foreignObject></svg>`;
}
const RELAX_ROUTES = { meta: "/relax/file", attr: "/relaxattr/file" };
// the relaxation scenes' addresses carry a token parameter, which fileUrl never adds: a Referer that carried the tab's address, or its
// query, would show it
const RELAX_TOKEN = "witness-token-0002";
/** One element per paint attribute, as the chat-media witness renders them; "fill" also as the CSS property (cssfill.svg). */
const PAINT_EL: Record<string, (u: string) => string> = {
  "fill": (u) => `<rect x="150" width="10" height="10" fill="url(${u}#p)"/>`,
  "stroke": (u) => `<rect x="162" width="10" height="10" fill="none" stroke="url(${u}#p)"/>`,
  "filter": (u) => `<rect x="236" width="10" height="10" filter="url(${u}#f)"/>`,
  "clip-path": (u) => `<rect x="174" width="10" height="10" clip-path="url(${u}#c)"/>`,
  "mask": (u) => `<rect x="186" width="10" height="10" mask="url(${u}#m)"/>`,
  "marker-start": (u) => `<path d="M200 1 L205 5 L210 1" fill="none" stroke="black" marker-start="url(${u}#k)"/>`,
  "marker-mid": (u) => `<path d="M212 1 L217 5 L222 1" fill="none" stroke="black" marker-mid="url(${u}#k)"/>`,
  "marker-end": (u) => `<path d="M224 1 L229 5 L234 1" fill="none" stroke="black" marker-end="url(${u}#k)"/>`,
};
const paintFiles = (a: string) => a === "fill" ? ["fill.svg", "cssfill.svg"] : [a + ".svg"];
type Population = { loads: [string, Load][]; paint: string[] };
/** The elements the marked plants put their loads on, by mark, each read from its plant's own markup (the one element whose attribute
 *  names the marked file) and spelled as the cookie clause spells an element: its tag, and for a `link` its rel, since a link's rel
 *  decides what it loads (`link rel="stylesheet"`). The mark is LOADS' marks entry; the markup's crossorigin value is the per-request
 *  asserts' to hold (the other value reds at the load's cookie in Chromium and Firefox and goes unseen in WebKit, which sends this
 *  fixture no cookie; no crossorigin at all reds at the load's cookie or its mode). */
function markedElements(): Record<Mark, string[]> {
  const out: Record<Mark, string[]> = { "use-credentials": [], "anonymous": [] };
  const at = (f: string) => "https://marked.test/" + f;
  for (const [name, l] of Object.entries(LOADS)) for (const [f, mark] of Object.entries(l.marks || {})) {
    assert.ok(l.files.includes(f), "the marked load " + f + " is one of the files the plant for " + name + " names: " + JSON.stringify(l.files));
    const p = l.parts(at);
    const markup = [p.prolog, p.style, p.body, p.fo].filter((s): s is string => !!s).join("\n");
    const attrsOf = (s: string) => new Map(Array.from(s.matchAll(/\s([\w:-]+)="([^"]*)"/g)).map((a) => [a[1], a[2]] as [string, string]));
    const els = Array.from(markup.matchAll(/<([a-zA-Z]+)((?:\s+[\w:-]+="[^"]*")*)\s*\/?>/g)).filter((m) => Array.from(attrsOf(m[2]).values()).includes(at(f)));
    assert.equal(els.length, 1, "one element of the plant for " + name + " names the marked load " + f + ": " + markup);
    out[mark].push(els[0][1] + (els[0][1] === "link" ? ' rel="' + (attrsOf(els[0][2]).get("rel") ?? "") + '"' : ""));
  }
  return out;
}
/** The plants the row's list asks for, checked one population with the row: a load the row names and nothing plants, or a plant
 *  for a load the row does not name, is red here by name; and the elements the cookie clause's two marks name, each held both ways to
 *  the elements the plants marked that way use (markedElements): an element the clause names with no marked plant, or a marked plant
 *  on an element the clause does not name, is red here by name. */
function population(list: RowList): Population {
  assert.deepEqual(list.loads.slice().sort(), Object.keys(LOADS).sort(), "the loads SVG_TAB_ROW names are the loads this leg plants and observes, "
    + "no more, no fewer (row: " + JSON.stringify(list.loads) + ")");
  const planted = markedElements();
  for (const mark of ["use-credentials", "anonymous"] as Mark[]) {
    const set = (xs: string[]) => Array.from(new Set(xs)).sort();
    assert.deepEqual(set(planted[mark]), set(list.marked[mark]), "the elements SVG_TAB_ROW's cookie clause names for a load marked crossorigin=\"" + mark
      + "\" are the elements this leg's plants marked that way use, no more, no fewer (row: " + JSON.stringify(list.marked[mark]) + "; plants: "
      + JSON.stringify(planted[mark]) + ")");
  }
  const paint = [...list.chromium, list.none];
  assert.deepEqual(paint.filter((a) => !PAINT_EL[a]), [], "every paint attribute PAINT_LIST names has a plant here");
  assert.ok(list.chromium.includes(list.min) && !list.chromium.includes(list.none), "PAINT_LIST's Firefox/WebKit attribute is in its Chromium list, its no-engine one is not: " + JSON.stringify(list));
  return { loads: Object.entries(LOADS), paint };
}
function svg(M: string, t: string, pop: Population, useNone: string): string {
  const u = (f: string) => `${M}/${t}-${f}`;
  const parts = pop.loads.map(([, l]) => l.parts(u));
  const style = parts.map((p) => p.style).filter((s): s is string => !!s);
  style.sort((a, b) => Number(!a.startsWith("@import")) - Number(!b.startsWith("@import")));   // an @import must lead its sheet
  return parts.map((p) => p.prolog || "").join("")
    + `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="400" height="200">\n`
    + `<style>${style.join(" ")} .c { fill: url("${u("cssfill.svg")}#p"); }</style>\n`
    + parts.map((p) => p.body || "").join("\n") + "\n"
    + `<foreignObject x="24" width="120" height="120"><div xmlns="http://www.w3.org/1999/xhtml">${parts.map((p) => p.fo || "").join("")}</div></foreignObject>\n`
    + pop.paint.map((a) => PAINT_EL[a](u(a + ".svg"))).join("\n") + `<rect class="c" x="248" width="10" height="10"/>\n`
    + `<${useNone} href="${u(useNone + ".svg")}#u" x="290"/>\n`
    + `<script>document.documentElement.setAttribute("data-ran", "1"); fetch("${u("script-ran.png")}")</script></svg>`;
}

// ── the opener, as preview.ts runs it ────────────────────────────────────────────────────────────────

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function openerBundle(): string {
  const contents = 'import { openFileTab, fileUrl } from "./preview";\n(window as any).__openFileTab = openFileTab; (window as any).__fileUrl = fileUrl;';
  return requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "svg-tab-probe.ts", loader: "ts" } }).outputFiles[0].text;
}

type Hit = { path: string; cookie: string | null; referer: string | null; origin: string | null; site: string | null; mode: string | null };
async function listen(handler: http.RequestListener, host: string): Promise<{ server: http.Server; origin: string }> {
  const server = http.createServer(handler);
  await new Promise<void>((ok, bad) => { server.once("error", bad); server.listen(0, host, () => ok()); });
  return { server, origin: `http://${host}:${(server.address() as AddressInfo).port}` };
}
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
// why the leg skips in CI: the vscode-extension job's order of steps, not an absent browser
const CI_SKIP = "in CI the vscode-extension job runs npm test before it installs Playwright's Chromium, and installs no Firefox or WebKit";

// what each engine sends this fixture's media host on a load made without CORS and on a credentialed one (what "whatever cookies
// that browser sends cross-site" comes to here): the SameSite=None one in Chromium and Firefox; none in WebKit, which sends that Secure
// cookie to the plain-http media host on no cross-site load, so WebKit's null is the fixture's and its cookie assertions cannot fail on
// it (the no-cookie half there rests on the credentials mode the specifications set for a paint reference, a web font or an anonymous
// load, which no run here observes)
const CROSS_SITE_COOKIE: Record<string, string | null> = { chromium: "cross_site=1", firefox: "cross_site=1", webkit: null };
// the engines whose console reports the refusal of a no-engine load (measured: Chromium and WebKit "Unsafe attempt to load URL",
// Firefox "may not load data from"); WebKit reports the use and never the filter, whose absence is read after every other load
const REFUSAL_REPORTED: Record<string, ("use" | "filter")[]> = { chromium: ["use", "filter"], firefox: ["use", "filter"], webkit: ["use"] };
const REFUSAL = /Unsafe attempt to load URL|may not load data from/;
// how each engine reports a response whose headers repeat a name with another between them (measured at the engine builds this leg ran
// on): Chromium's raw header text is the order served; Firefox groups the repeated name where it last stands (moving the earlier one
// down), WebKit where it first stands (moving the later one up)
const REPORTED_GROUPING: Record<string, "served" | "last" | "first"> = { chromium: "served", firefox: "last", webkit: "first" };
/** A header list as the engine reports it when served in that order: unchanged for Chromium's raw text; in Firefox and WebKit each
 *  repeated name's headers together, at its last or its first place, the rest in order (a list with no name repeated apart, as
 *  NO_POLICY_HEADERS, comes back unchanged). */
function asReported(hs: [string, string][], engine: string): [string, string][] {
  const g = REPORTED_GROUPING[engine];
  if (g === "served") return hs;
  const names = hs.map(([k]) => k.toLowerCase());
  const out: [string, string][] = [];
  names.forEach((n, i) => { if ((g === "last" ? names.lastIndexOf(n) : names.indexOf(n)) === i) out.push(...hs.filter(([k]) => k.toLowerCase() === n)); });
  return out;
}
type Expect = { file: string; name: string; cors: boolean; mark?: Mark; turn?: "frame" | "sheet"; from?: string };

/** The two servers and the per-scene assertions one engine's test uses. */
async function harness(engine: string, list: RowList, pop: Population, send: Record<string, string>, pol: [string, string]) {
  const hits: Hit[] = [];
  const waiters: { paths: Set<string>; done: () => void }[] = [];
  const heard = (u: string) => { for (const w of waiters.slice()) { w.paths.delete(u); if (!w.paths.size) { waiters.splice(waiters.indexOf(w), 1); w.done(); } } };
  let M = "";
  const media = await listen((req, res) => {
    const h = req.headers, u = req.url || "";
    hits.push({ path: u, cookie: (h.cookie as string) ?? null, referer: (h.referer as string) ?? null, origin: (h.origin as string) ?? null,
      site: (h["sec-fetch-site"] as string) ?? null, mode: (h["sec-fetch-mode"] as string) ?? null });
    heard(u);
    if (u.endsWith(".png")) { res.writeHead(200, { "Content-Type": "image/png" }); res.end(PNG); return; }
    // the CSS `@import` plant's sheet names loads in turn (sheetCss); every other sheet is inert
    if (u.endsWith("-import.css")) { res.writeHead(200, { "Content-Type": "text/css" }); res.end(sheetCss(M, u.slice(1, -"-import.css".length))); return; }
    if (u.endsWith(".css")) { res.writeHead(200, { "Content-Type": "text/css" }); res.end("rect{}"); return; }
    if (u.endsWith(".svg")) { res.writeHead(200, { "Content-Type": "image/svg+xml" }); res.end(SVG_DOC); return; }
    // the relaxation scene's framed page relaxes its own policy by a referrer meta and a referrerpolicy attribute on its images
    if (u.endsWith("-rframe.html")) { const t = u.slice(0, -"-rframe.html".length); res.writeHead(200, { "Content-Type": "text/html" });
      res.end(`<!doctype html><meta name="referrer" content="unsafe-url"><img src="${M}${t}-rframe-img.png"><img referrerpolicy="unsafe-url" src="${M}${t}-rframe-attr.png">`); return; }
    // the framed page names one image of its own: the row's "loads what that page names in turn"
    if (u.endsWith(".html")) { res.writeHead(200, { "Content-Type": "text/html" }); res.end(`<!doctype html><img src="${M}${u.replace(/-fo-frame\.html$/, "-frame-img.png")}">`); return; }
    if (u.endsWith(".mp4") || u.endsWith(".mp3")) { res.writeHead(200, { "Content-Type": u.endsWith(".mp4") ? "video/mp4" : "audio/mpeg", "Content-Length": "16" }); res.end(Buffer.alloc(16)); return; }
    if (u.endsWith(".woff2")) { res.writeHead(200, { "Content-Type": "font/woff2" }); res.end(Buffer.alloc(16)); return; }
    res.writeHead(404); res.end();
  }, "127.0.0.1");
  M = media.origin;
  let P = "";
  const page = await listen((req, res) => {
    const u = new URL(req.url || "/", "http://x");
    if (u.pathname === "/opener") { res.writeHead(200, [["Content-Type", "text/plain; charset=utf-8"], ...Object.entries(send)].flat()); res.end("the tab's opener\n"); return; }
    const bare = u.pathname === "/nosandbox/file", nopolicy = u.pathname === "/nopolicy/file";
    const relax = u.pathname === RELAX_ROUTES.meta, relaxAttr = u.pathname === RELAX_ROUTES.attr;
    if (u.pathname !== "/file" && u.pathname !== "/remote/labhost/file" && !bare && !nopolicy && !relax && !relaxAttr) { res.writeHead(404); res.end(); return; }
    const hs = bare ? SVG_FILE_HEADERS.filter(([k, v]) => !(k === pol[0] && v === pol[1])) : nopolicy ? NO_POLICY_HEADERS : SVG_FILE_HEADERS;
    const t = path.basename(u.searchParams.get("path") || "", ".svg");
    res.writeHead(200, hs.flat()); res.end(relax ? relaxSvg(M, t) : relaxAttr ? relaxAttrSvg(M, t) : svg(M, t, pop, list.useNone));
  }, "localhost");
  P = page.origin;
  const arrived = (paths: string[], ms: number) => new Promise<void>((ok, bad) => {
    const pending = new Set(paths.filter((p) => !hits.some((h) => h.path === p)));
    if (!pending.size) return ok();
    const w = { paths: pending, done: () => { clearTimeout(timer); ok(); } };
    const timer = setTimeout(() => { waiters.splice(waiters.indexOf(w), 1); bad(new Error(engine + ": no request for " + Array.from(pending).join(", ") + " within " + ms + " ms; arrived: " + hits.map((h) => h.path).join(" | "))); }, ms);
    waiters.push(w);
  });
  // what the row says loads in this engine, by request path: every load of the list, the framed page's own image, and the paint list
  // for the engine (Chromium's whole list with the CSS fill; at least the Firefox/WebKit attribute elsewhere)
  const expected = (tag: string): Expect[] => {
    const out: Expect[] = [];
    for (const [name, l] of pop.loads) {
      for (const f of l.files) {
        const mark = l.marks ? l.marks[f] : undefined;
        out.push({ file: `/${tag}-${f}`, name: mark ? name + ", the one the markup marks crossorigin=\"" + mark + "\"" : name,
          cors: !!mark || (Array.isArray(l.cors) ? l.cors.includes(engine) : l.cors), mark });
      }
      for (const f of l.turn || []) out.push({ file: `/${tag}-${f}`, name: "a load the sheet of " + name + " names in turn", cors: false, turn: "sheet", from: `${M}/${tag}-${l.files[0]}` });
    }
    out.push({ file: `/${tag}-frame-img.png`, name: "the framed page's own image", cors: false, turn: "frame" });
    for (const a of engine === "chromium" ? list.chromium : [list.min]) for (const f of paintFiles(a)) out.push({ file: `/${tag}-${f}`, name: "the " + a + " paint reference", cors: true });
    return out;
  };
  const refusals = (context: any, tag: string): Promise<unknown>[] => REFUSAL_REPORTED[engine].map((what) => {
    const url = `${M}/${tag}-${what === "use" ? list.useNone : list.none}.svg`;
    const p: Promise<unknown> = context.waitForEvent("console", { predicate: (m: any) => REFUSAL.test(m.text()) && m.text().includes(url), timeout: 10000 })
      .catch(() => { throw new Error(engine + ": no refusal report for " + url + " within 10000 ms"); });
    p.catch(() => {});                                            // a scene that reds before awaiting it leaves no unhandled rejection
    return p;
  });
  // referer: what the tab's own loads carry as their Referer in the scenes check() reads: none in the sandboxed tabs (Chromium's scenes
  // 1 and 2, the Firefox and WebKit sandboxed tab), and in the arm below the row's per-engine expectation, passed with the clause it
  // read so its message quotes the row. The relaxation scenes, under the /file headers too, are not among them; relaxScene holds their
  // loads
  const check = (tag: string, scene: string, token: string | null, referer: { want: string | null; why: string } = { want: null, why: "" }) => {
    const these = hits.filter((h) => h.path.startsWith(`/${tag}-`));
    console.log(engine + " " + scene + " request lines:"); for (const h of these) console.log("  " + JSON.stringify(h));
    for (const e of expected(tag)) {
      const reqs = these.filter((h) => h.path === e.file);
      // Chromium and Firefox fetch each once; WebKit re-requests a media element's bytes with a Range, so it is each at least once
      if (engine === "webkit") assert.ok(reqs.length >= 1, scene + ": a request for " + e.file + " (" + e.name + ")");
      else assert.equal(reqs.length, 1, scene + ": one request for " + e.file + " (" + e.name + "): " + JSON.stringify(reqs));
      for (const r of reqs) {
        // the tab's loads are cross-site; a load a stylesheet names in turn is that sheet's, on the sheet's own host (Firefox classes
        // it same-origin), so its site is not asserted
        if (e.turn !== "sheet") assert.equal(r.site, "cross-site", scene + ": " + e.file + " is cross-site");
        if (e.turn === "frame") assert.ok(r.referer === null || r.referer === M + "/", scene + ": the framed page's own load carries at most that frame's origin (" + M + "/) as its Referer, as the row says (" + FRAME_REFERER + "): " + JSON.stringify(r));
        else if (e.turn === "sheet" && list.sheetOwn.includes(engine)) assert.ok(r.referer === null || r.referer === e.from, scene + ": " + e.file + " (" + e.name
          + ") carries at most that stylesheet's own address (" + e.from + ") as its Referer, as the row says for " + engine + ": " + JSON.stringify(r));
        else if (e.turn === "sheet") assert.equal(r.referer, referer.want, scene + ": " + e.file + " (" + e.name + ") carries what the tab's own loads carry as "
          + "their Referer (" + referer.want + "), as the row says for " + engine + ": " + JSON.stringify(r));
        else assert.equal(r.referer, referer.want, scene + ": " + e.file + (referer.want === null ? " carries no Referer" : " carries the dashboard's origin ("
          + referer.want + ") as its Referer") + referer.why);
        if (e.mark === "use-credentials" || (!e.cors && !e.mark)) {
          // a load made without CORS, and the clause's CORS request made with credentials, carry what the engine sends cross-site
          assert.equal(r.cookie, CROSS_SITE_COOKIE[engine], scene + ": " + e.file + " (" + e.name + ") carries the cookies " + engine + " sends cross-site ("
            + CROSS_SITE_COOKIE[engine] + ") and not the Lax one" + (e.mark ? ", as the row says of " + list.credMark : "") + ": " + JSON.stringify(r));
          if (!e.mark) { assert.notEqual(r.mode, "cors", scene + ": " + e.file + " (" + e.name + ") is a load made without CORS"); continue; }
        } else {
          assert.equal(r.cookie, null, scene + ": " + e.file + " (" + e.name + ") carries no cookie, as the row says of "
            + (e.mark ? list.anonMark : "a paint reference or a web font in Chromium and Firefox")
            + (CROSS_SITE_COOKIE[engine] ? ", where " + engine + "'s loads made without CORS and its credentialed ones carry " + CROSS_SITE_COOKIE[engine]
              : "; in " + engine + " the loads made without CORS carry none on this fixture, so this cannot fail here and the half rests on the credentials "
                + "mode the specifications set for this fetch, which no run here observes") + ": " + JSON.stringify(r));
        }
        assert.equal(r.mode, "cors", scene + ": " + e.file + " (" + e.name + ") is a CORS request (Sec-Fetch-Mode cors), the request kind its Origin null implies: " + JSON.stringify(r));
        assert.equal(r.origin, "null", scene + ": " + e.file + " is a CORS request from the sandbox's opaque origin");
      }
    }
    for (const a of [list.none, list.useNone]) assert.equal(these.filter((h) => h.path === `/${tag}-${a}.svg`).length, 0, scene + ": the " + a + " that names another host loads in no engine");
    assert.ok(!these.some((h) => h.path.endsWith("-script-ran.png")), scene + ": the sandbox stops the svg's script");
    const pathed = these.filter((h) => h.referer !== null && h.referer.startsWith(P) && h.referer !== P + "/");
    assert.deepEqual(pathed, [], scene + ": no request to the other site carries a Referer that names the dashboard's origin with a path or query after it, "
      + "as the row's Referer clause allows none: " + list.cause);
    if (token) assert.ok(!these.some((h) => [h.path, h.referer, h.cookie].some((v) => v && v.includes(token))), scene + ": no request to the other site carries "
      + "the token the opener page's address carries (the tab's address carries none, as the row says: " + TOKEN_CLAUSE + ")");
  };
  // a tab navigated to url, and its response's headers as the engine received them: in Chromium the raw header text the DevTools
  // protocol gives for the navigation (Chromium's report sorts them by name; listened for before the navigation starts, the bound the
  // failure), in Firefox and WebKit as the engine reports them. heldTo holds the response's headers of the names the /file headers carry
  // to a list: in Chromium in the order served; in Firefox and WebKit as the engine reports them, which holds the headers and the order
  // of distinct names, not where a repeated name sits on the wire (each groups same-named headers its own way, Firefox moving the
  // earlier one down and WebKit the later one up, so each misses a reorder of the two Content-Security-Policy headers that the other
  // catches), the list grouped as that engine groups it (asReported)
  const navigate = async (context: any, url: string, what: string) => {
    const tab = await context.newPage();
    let raw: Promise<string> | null = null;
    if (engine === "chromium") {
      const cdp = await context.newCDPSession(tab);
      const urls = new Map<string, string>(), texts = new Map<string, string | null>();
      raw = new Promise<string>((ok, bad) => {
        const timer = setTimeout(() => bad(new Error("chromium: no raw header text for " + what + "'s navigation within 10000 ms")), 10000);
        const settle = (id: string) => {
          if (urls.get(id) !== url || !texts.has(id)) return;
          clearTimeout(timer);
          const t = texts.get(id);
          if (t) ok(t); else bad(new Error("chromium: " + what + "'s navigation came with no raw header text"));
        };
        cdp.on("Network.responseReceived", (e: any) => { urls.set(e.requestId, e.response.url); settle(e.requestId); });
        cdp.on("Network.responseReceivedExtraInfo", (e: any) => { texts.set(e.requestId, e.headersText ?? null); settle(e.requestId); });
      });
      raw.catch(() => {});                                        // a red before it is awaited leaves no unhandled rejection
      await cdp.send("Network.enable");
    }
    const res = await tab.goto(url, { waitUntil: "domcontentloaded" });
    assert.ok(res, engine + ": " + what + "'s navigation has a response");
    const got: { name: string; value: string }[] = await res.headersArray();
    console.log(engine + " " + what + ": the navigation's response headers: " + JSON.stringify(got));
    const served: [string, string][] = raw
      ? (await raw).split("\r\n").slice(1).filter((l) => l !== "").map((l) => [l.slice(0, l.indexOf(":")), l.slice(l.indexOf(":") + 1).trim()] as [string, string])
      : got.map((h) => [h.name, h.value] as [string, string]);
    if (raw) console.log(engine + " " + what + ": the navigation's raw response headers: " + JSON.stringify(served));
    // a header an engine reports joined with another under the same name is split at its commas or line breaks
    const valuesOf = (n: string) => got.filter((h) => h.name.toLowerCase() === n.toLowerCase()).flatMap((h) => h.value.split(/\n|,/)).map((v) => v.trim());
    const names = new Set(SVG_FILE_HEADERS.map(([k]) => k.toLowerCase()));
    const heldTo = (want: [string, string][], wantName: string) => assert.deepEqual(served.filter(([k]) => names.has(k.toLowerCase())), asReported(want, engine),
      engine + ": " + what + "'s response, its headers of the names the /file headers carry, is " + wantName + (raw ? " in the order served (Chromium's raw header text)"
        : " as " + engine + " reports them (the headers and the order of distinct names, a repeated name grouped at its " + REPORTED_GROUPING[engine] + " place)")
        + ": " + JSON.stringify(served));
    return { tab, got, valuesOf, heldTo };
  };
  // the relaxation scenes: a tab at a route of its own under the /file headers (RELAX_ROUTES), at an address whose query carries a token
  // parameter, held first to the page's policy: the navigation's response carries the /file headers, its Referrer-Policy among them.
  // The meta scene (every engine): the first load, the CSS `@import` sheet started before any relaxing markup, carries no Referer; each
  // load the referrer meta reaches carries none where the row says the sandbox withholds the tab's own Referer and exactly the
  // dashboard's origin where it says the policy does (two-sided: a scene whose relaxation did not happen reds, and so does a load that
  // carries a path or query); the relaxing framed page's own loads carry at most that frame's origin; the stylesheet's loads in turn
  // carry at most its own address, or at most the dashboard's origin where the row says they carry what the tab's own loads carry (here,
  // none before the meta and the origin after it). The attribute scene (every engine): the img without the attribute carries no
  // Referer, and the one with it none where the row says the sandbox withholds the tab's own Referer and exactly the dashboard's origin
  // where it says the policy does, so there the attribute is what relaxes it. In both, no request to the other site carries a Referer
  // with a path or query on the dashboard's origin, or the token
  const relaxScene = async (context: any, tag: string, kind: "meta" | "attr") => {
    const scene = kind === "meta" ? "relaxation scene (referrer meta)" : "relaxation scene (referrerpolicy attribute)";
    const url = P + RELAX_ROUTES[kind] + "?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/" + tag + ".svg") + "&token=" + RELAX_TOKEN;
    const inPolicy = list.byPolicy.includes(engine);
    assert.ok(inPolicy || list.bySandbox.includes(engine), "the row's Referer clause names " + engine + ": " + list.cause);
    const nav = await navigate(context, url, "the " + scene);
    const policy = SVG_FILE_HEADERS.filter(([k]) => k === "Referrer-Policy").map(([, v]) => v);
    assert.deepEqual(nav.valuesOf("Referrer-Policy"), policy, engine + " " + scene + ": the response carries the page's Referrer-Policy (" + policy.join(", ")
      + "), the policy the scene's markup relaxes: " + JSON.stringify(nav.got));
    nav.heldTo(SVG_FILE_HEADERS, "SVG_FILE_HEADERS");
    const sheet = pop.loads.find(([, l]) => l.turn)![1];
    const sheetAt = `${M}/${tag}-${sheet.files[0]}`;
    const files = kind === "meta" ? [sheet.files[0], ...sheet.turn!, ...Object.keys(RELAXED), ...RELAX_FRAME] : [RELAX_PLAIN, RELAX_ATTR];
    await arrived(files.map((f) => `/${tag}-${f}`), 10000);
    const these = hits.filter((h) => h.path.startsWith(`/${tag}-`));
    console.log(engine + " " + scene + " (" + url + ") request lines:"); for (const h of these) console.log("  " + JSON.stringify(h));
    const of = (f: string) => { const r = these.filter((h) => h.path === `/${tag}-${f}`); assert.ok(r.length >= 1, scene + ": a request for /" + tag + "-" + f); return r; };
    const relaxed = (f: string, what: string) => { for (const r of of(f)) assert.equal(r.referer, inPolicy ? P + "/" : null, scene + ": " + f + " (" + what + ") carries "
      + (inPolicy ? "exactly the dashboard's origin (" + P + "/) as its Referer, no path or query, as the row says for " + engine + " (" + RELAX_CLAUSE + ")"
        : "no Referer, as the row says for " + engine + " (" + list.cause + ")") + ": " + JSON.stringify(r)); };
    if (kind === "meta") {
      for (const r of of(sheet.files[0])) assert.equal(r.referer, null, scene + ": " + sheet.files[0] + " (the scene's first load, the CSS `@import` sheet, started "
        + "before any relaxing markup) carries no Referer, as the row says for " + engine + " (" + list.cause + "): " + JSON.stringify(r));
      for (const f of Object.keys(RELAXED)) relaxed(f, RELAXED[f]);
      for (const f of RELAX_FRAME) for (const r of of(f)) assert.ok(r.referer === null || r.referer === M + "/", scene + ": " + f + ", a load of a framed page that "
        + "relaxes its own policy, carries at most that frame's origin (" + M + "/) as its Referer, as the row says (" + FRAME_REFERER + "): " + JSON.stringify(r));
      for (const f of sheet.turn!) for (const r of of(f)) {
        if (list.sheetOwn.includes(engine)) assert.ok(r.referer === null || r.referer === sheetAt, scene + ": " + f + " carries at most that stylesheet's own address ("
          + sheetAt + ") as its Referer, as the row says for " + engine + ": " + JSON.stringify(r));
        else assert.ok(r.referer === null || (inPolicy && r.referer === P + "/"), scene + ": " + f + " carries what the tab's own loads carry, at most the dashboard's "
          + "origin, as the row says for " + engine + ": " + JSON.stringify(r));
      }
    } else {
      for (const r of of(RELAX_PLAIN)) assert.equal(r.referer, null, scene + ": " + RELAX_PLAIN + " (an img without the attribute) carries no Referer, as the row "
        + "says for " + engine + " (" + list.cause + "): " + JSON.stringify(r));
      relaxed(RELAX_ATTR, "an img with referrerpolicy=\"unsafe-url\"");
    }
    const pathed = these.filter((h) => h.referer !== null && h.referer.startsWith(P) && h.referer !== P + "/");
    assert.deepEqual(pathed, [], scene + ": no request to the other site carries a Referer that names the dashboard's origin with a path or query after it, "
      + "as the row's Referer clause allows none: " + list.cause);
    assert.ok(!these.some((h) => [h.path, h.referer, h.cookie].some((v) => v && v.includes(RELAX_TOKEN))), scene + ": no request to the other site carries the "
      + "token parameter this scene's address carries (" + (inPolicy ? "none of the tab's own requests to another site carries more than the dashboard's origin "
        + "as its Referer, as the row says for " + engine + ": " + RELAX_CLAUSE : "none of the tab's own requests to another site carries a Referer, as the row "
        + "says for " + engine + ": " + list.sandboxHalf) + ")");
    await nav.tab.close();
  };
  // the arm for what withholds the tab's Referer, every engine: the tab under the /file headers less the page's Referrer-Policy, the
  // sandbox kept, checked as written (NO_POLICY_HEADERS) and as the engine received it (navigate's heldTo: in Chromium in the order
  // served, in Firefox and WebKit as the engine reports them); every load is asserted as in the sandboxed scenes, and the tab's own
  // loads carry the Referer the row's clause names for this engine: none where it says the sandbox withholds it, the dashboard's origin
  // where it says the policy does
  const policyArm = async (context: any, tag: string) => {
    assert.ok(!NO_POLICY_HEADERS.some(([k]) => k.toLowerCase() === "referrer-policy"), "the arm's headers carry no Referrer-Policy: " + JSON.stringify(NO_POLICY_HEADERS));
    assert.equal(SVG_FILE_HEADERS.filter(([k]) => k.toLowerCase() === "referrer-policy").length, 1, "the /file headers carry one Referrer-Policy: " + JSON.stringify(SVG_FILE_HEADERS));
    assert.deepEqual(NO_POLICY_HEADERS, SVG_FILE_HEADERS.filter(([k]) => k.toLowerCase() !== "referrer-policy"),
      "the arm's headers are the /file headers less exactly the Referrer-Policy, every other one kept: " + JSON.stringify(NO_POLICY_HEADERS));
    assert.ok(NO_POLICY_HEADERS.some(([k, v]) => k === pol[0] && v === pol[1]), "the arm keeps the sandbox: " + JSON.stringify(NO_POLICY_HEADERS));
    const inPolicy = list.byPolicy.includes(engine);
    assert.ok(inPolicy || list.bySandbox.includes(engine), "the row's Referer clause names " + engine + ": " + list.cause);
    const refused = refusals(context, tag);
    const url = P + "/nopolicy/file?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/" + tag + ".svg");
    const nav = await navigate(context, url, "the arm");
    // the arm's response as the engine received it: no Referrer-Policy, and the sandboxing Content-Security-Policy present
    assert.deepEqual(nav.valuesOf("Referrer-Policy"), [], engine + ": the arm's response carries no Referrer-Policy: " + JSON.stringify(nav.got));
    assert.ok(nav.valuesOf(pol[0]).includes(pol[1]), engine + ": the arm's response carries the sandboxing " + pol[0] + " (" + pol[1] + "): " + JSON.stringify(nav.got));
    nav.heldTo(NO_POLICY_HEADERS, "NO_POLICY_HEADERS");
    await arrived(expected(tag).map((e) => e.file), 10000);
    await Promise.all(refused);
    check(tag, "sandbox kept, Referrer-Policy removed", null, { want: inPolicy ? P + "/" : null,
      why: ", as the row says for " + engine + " (" + (inPolicy ? "it names the page's Referrer-Policy as what withholds it, and this arm removes that policy"
        : "it names the sandbox as what withholds it, and this arm keeps the sandbox") + "): " + list.cause });
    await nav.tab.close();
  };
  return { hits, media, page, M, P, arrived, expected, refusals, check, policyArm, relaxScene };
}

test("the .svg tab road: openFileTab's tab of an .svg under the kernel's /file headers loads every host its markup names that the census row lists as examples, the non-CORS loads and the credentialed ones with the cross-site cookie, the paint references, the web font and the anonymous loads without, none of the tab's own loads to another site with a Referer, nor with the page's Referrer-Policy removed and the sandbox kept, nor under a referrer meta or a referrerpolicy attribute that relaxes that policy, as the row says for Chromium, the loads a stylesheet names in turn with at most its own address; the tab's address carries no serve token; the use and the filter that name another host load nowhere; the sandbox is what stops its script", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (" + CI_SKIP + ")"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (" + CI_SKIP + "): " + String((e as Error).message).split("\n")[0]); return; }
  let hx: Awaited<ReturnType<typeof harness>> | null = null;
  try {
    const { send, pol } = pinnedHeaders();
    const list = rowList(rowSent()), pop = population(list);
    hx = await harness("chromium", list, pop, send, pol);
    const { hits, M, P, arrived, expected, refusals, check, policyArm, relaxScene } = hx;
    const TOKEN = "witness-token-0001";                           // the opener page's address carries it, as the shell's first load does
    const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
    await context.addCookies([
      { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
      { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
    ]);
    const pg = await context.newPage();
    await pg.goto(P + "/opener?token=" + TOKEN);
    await pg.evaluate(openerBundle());
    await pg.evaluate(() => { const b = document.createElement("button"); b.id = "open"; b.textContent = "open"; document.body.appendChild(b);
      b.addEventListener("click", () => { const w = window as any; w.__opened = w.__openFileTab(w.__path, w.__sid); }); });
    // the token clause, from fileUrl itself: each address it builds (for a file of no session, of a session on this machine and of one
    // on an attached machine) takes one of the forms the clause names and carries no serve token
    const FORMS: [string, RegExp][] = [["`/file?path=...`", /^\/file\?path=[^&]+$/], ["`/file?path=...&sid=...`", /^\/file\?path=[^&]+&sid=[^&]+$/],
      ["`/remote/<host>/file`", /^\/remote\/labhost\/file\?path=[^&]+&sid=[^&]+$/]];
    const built: string[] = await pg.evaluate(([p, b]: [string, string]) => { const f = (window as any).__fileUrl; return [f(p, null), f(p, b), f(p, "labhost:" + b)]; },
      ["/tmp/TESTHOST/notes-api/docs/s0.svg", "11111111-2222-3333-4444-555555555555"] as [string, string]);
    FORMS.forEach(([shown, form], i) => {
      assert.ok(TOKEN_CLAUSE.includes(shown), "the token clause names the form " + shown + " fileUrl builds: " + TOKEN_CLAUSE);
      assert.ok(form.test(built[i]) && !/token/i.test(built[i]), "fileUrl's address " + built[i] + " takes the form " + shown + " and carries no serve token, as the row says (" + TOKEN_CLAUSE + ")");
    });
    const open = async (file: string, sid: string | null, tag: string) => {
      await pg.evaluate(([p, s]: [string, string | null]) => { const w = window as any; w.__path = p; w.__sid = s; }, [file, sid] as [string, string | null]);
      const popup = context.waitForEvent("page", { timeout: 10000 });
      // the page's own reports, listened for before the click so none can fire unheard: the sandbox's block of the script, and
      // the refusal of each no-engine load
      const sandboxed = context.waitForEvent("console", { predicate: (m: any) => /Blocked script execution/.test(m.text()) && m.text().includes(encodeURIComponent(file)), timeout: 10000 });
      const refused = refusals(context, tag);
      await pg.click("#open", { modifiers: ["Control"] });
      const tab = await popup;
      await tab.waitForLoadState("domcontentloaded");
      assert.equal(await pg.evaluate(() => (window as any).__opened), true, "openFileTab reports the tab opened");
      assert.equal(tab.url(), P + await pg.evaluate(([p, s]: [string, string | null]) => (window as any).__fileUrl(p, s), [file, sid] as [string, string | null]), "the tab's URL is fileUrl's");
      return { tab, sandboxed, refused };
    };

    // scene 1: the local /file URL
    const f1 = "/tmp/TESTHOST/notes-api/docs/s1.svg";
    const { tab: tab1, sandboxed: b1, refused: r1 } = await open(f1, null, "s1");
    await arrived(expected("s1").map((e) => e.file), 10000);
    await b1;                                                     // the page's own report of the sandbox's block: its script never ran
    await Promise.all(r1);                                        // and of its refusal of the use and the filter
    assert.ok(!/token/i.test(tab1.url()), "the tab's address carries no serve token, though the opener page's does, as the row says (" + TOKEN_CLAUSE + "): " + tab1.url());
    check("s1", "scene 1 (/file)", TOKEN);
    await tab1.close();

    // scene 2: a remote session's file, the relay's URL (the same headers: the Python tie reads them on the relay's wire)
    const { tab: tab2, sandboxed: b2, refused: r2 } = await open("/tmp/TESTHOST/notes-api/docs/s2.svg", "labhost:11111111-2222-3333-4444-555555555555", "s2");
    assert.ok(tab2.url().startsWith(P + "/remote/labhost/file?"), "a host-prefixed session id opens the relay's URL: " + tab2.url());
    assert.ok(!/token/i.test(tab2.url()), "the relay's tab address carries no serve token, as the row says (" + TOKEN_CLAUSE + "): " + tab2.url());
    await arrived(expected("s2").map((e) => e.file), 10000);
    await b2;
    await Promise.all(r2);
    check("s2", "scene 2 (/remote/labhost/file)", TOKEN);
    await tab2.close();

    // scene 3: the control for the sandbox: without it the script runs and the mask reference sends the page's origin; and the use
    // naming another host is still refused (the engine's refusal report names its URL: a reference the engine read and refused)
    const r3 = refusals(context, "s3");
    const tab3 = await context.newPage();
    await tab3.goto(P + "/nosandbox/file?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/s3.svg"));
    await arrived([...expected("s3").map((e) => e.file), "/s3-script-ran.png"], 10000);
    await Promise.all(r3);
    const mask = hits.find((h) => h.path === "/s3-mask.svg")!;
    console.log("scene 3 (no sandbox) mask request: " + JSON.stringify(mask));
    assert.equal(mask.referer, P + "/", "the control: in Chromium, with the sandbox removed and the Referrer-Policy kept, the mask reference sends the page's origin, so there the sandbox is what removes it");
    assert.equal(hits.filter((h) => h.path === `/s3-${list.useNone}.svg`).length, 0, "the control: the " + list.useNone + " naming another host is refused without the sandbox too");
    assert.ok(M.startsWith("http://127.0.0.1:"), "the media host is the other site");
    await tab3.close();

    // scene 4: the arm for what withholds the Referer, the sandbox kept and the page's Referrer-Policy removed
    await policyArm(context, "s4");

    // scene 5: the meta scene, a referrer meta in the svg relaxing the page's Referrer-Policy under the /file headers
    await relaxScene(context, "s5", "meta");

    // scene 6: the attribute scene, a referrerpolicy attribute on an img in a document with no meta; the sandbox withholds the
    // Referer of both imgs, the one with the attribute and the one without
    await relaxScene(context, "s6", "attr");
  } finally {
    await browser.close();
    if (hx) { hx.media.server.close(); hx.page.server.close(); }
  }
});

// Firefox and WebKit: the same svg in a tab navigated to the same /file URL. The row's list is claimed for every engine; the paint
// list is the engine's (PAINT_LIST: at least its Firefox/WebKit attribute). Skips LOUDLY per engine that cannot launch.
for (const engineName of ["firefox", "webkit"]) {
  test(`the .svg tab road on ${engineName}: the tab loads every host the census row lists as examples, with the cookies ${engineName} sends cross-site on the loads made without CORS and on the credentialed ones and none on the other CORS requests, no Referer on the tab's own loads to another site and at most the frame's origin on a framed page's, the dashboard's origin on the tab's own with the page's Referrer-Policy removed and the sandbox kept and, exactly, on those that a referrer meta or a referrerpolicy attribute relaxing that policy reaches, and on the loads a stylesheet names in turn what the row says for ${engineName}; the use and the filter that name another host load nowhere; no script runs`, { timeout: 120000 }, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (" + CI_SKIP + ")"); return; }
    let browser: any;
    try { browser = await pw[engineName].launch(); }
    catch (e) { t.skip("no " + engineName + " on this box; the leg needs one (" + CI_SKIP + "): " + String((e as Error).message).split("\n")[0]); return; }
    let hx: Awaited<ReturnType<typeof harness>> | null = null;
    try {
      const { send, pol } = pinnedHeaders();
      const list = rowList(rowSent()), pop = population(list);
      hx = await harness(engineName, list, pop, send, pol);
      const { hits, P, arrived, expected, refusals, check, policyArm, relaxScene } = hx;
      const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
      await context.addCookies([
        { name: "lax_only", value: "1", domain: "127.0.0.1", path: "/", sameSite: "Lax" },
        { name: "cross_site", value: "1", domain: "127.0.0.1", path: "/", sameSite: "None", secure: true },
      ]);
      // the sandboxed tab: the loads, the refusals, and the script's mark read from the document once it is parsed (an inline
      // script runs during the parse, so a script that ran has set it by DOMContentLoaded)
      const r1 = refusals(context, "e1");
      const tab = await context.newPage();
      await tab.goto(P + "/file?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/e1.svg"), { waitUntil: "domcontentloaded" });
      assert.equal(await tab.evaluate(() => document.documentElement.getAttribute("data-ran")), null, engineName + ": the sandbox stops the svg's script (its mark is unset once the document is parsed)");
      await arrived(expected("e1").map((e) => e.file), 10000);
      await Promise.all(r1);
      const others = hits.filter((h) => h.path.startsWith("/e1-") && !expected("e1").some((e) => e.file === h.path)).map((h) => h.path);
      console.log(engineName + " loads beyond the row's floor for this engine: " + JSON.stringify(others));
      check("e1", "sandboxed tab", null);
      await tab.close();
      // the control: without the sandbox the script runs (its mark set, its fetch arrives), and the use naming another host is still
      // refused (the engine's refusal report names its URL)
      const r2 = refusals(context, "e2");
      const tab2 = await context.newPage();
      await tab2.goto(P + "/nosandbox/file?path=" + encodeURIComponent("/tmp/TESTHOST/notes-api/docs/e2.svg"), { waitUntil: "domcontentloaded" });
      assert.equal(await tab2.evaluate(() => document.documentElement.getAttribute("data-ran")), "1", engineName + ": the control: without the sandbox the script runs and sets its mark");
      await arrived([...expected("e2").map((e) => e.file), "/e2-script-ran.png"], 10000);
      await Promise.all(r2);
      console.log(engineName + " control (no sandbox) mask request: " + JSON.stringify(hits.find((h) => h.path === `/e2-${list.min}.svg`)));
      assert.equal(hits.filter((h) => h.path === `/e2-${list.useNone}.svg`).length, 0, engineName + ": the control: the " + list.useNone + " naming another host is refused without the sandbox too");
      await tab2.close();
      // the arm for what withholds the Referer, the sandbox kept and the page's Referrer-Policy removed
      await policyArm(context, "e3");
      // the relaxation scenes under the /file headers: a referrer meta in the svg relaxing the page's Referrer-Policy, then a
      // referrerpolicy attribute on an img in a document with no meta
      await relaxScene(context, "e4", "meta");
      await relaxScene(context, "e5", "attr");
      await context.close();
    } finally {
      await browser.close();
      if (hx) { hx.media.server.close(); hx.page.server.close(); }
    }
  });
}
