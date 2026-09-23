// Every notify kind a ui/webview writer posts to the shell's error centre is one the centre registers (the maintainer's round 6
// of the wsBytesByHost review, ui-1: the apply-throw refusal's two messages posted the kindless catch-all "error", registered in
// none of the three tables and with no chip colour, so each landed in the Log unlabelled and unmutable). The tables are READ BY
// EVALUATION of the shell's JS (kernel.py's KINDS, KINDLBL and DESC, from the declaration to their first use, so a kind registered
// on a later line of that segment counts as the page counts it) and never by the array literal's spelling; the writers are DERIVED
// from the sources (every {romp: "notify"} post and every tellShell, notifyShell and __rompNotify call under ui/webview, with a
// wrapper's parameter resolved through its call sites and feed.ts's forwarded BadgeNotice kinds through badge-mirror.ts), so a new
// writer, a new kind or a kind in a form this census cannot read reds here until it is registered or classified.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const ROOT = path.resolve(EXT, "..");
const UI = path.join(ROOT, "ui", "webview");
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");

type Tables = { KINDS: string[]; KINDLBL: Record<string, string>; DESC: Record<string, string> };

/** The three tables as the page holds them: KINDS drives the filter row, KINDLBL the chip's text, DESC the tooltip. */
function tables(): Tables {
  const a = KERNEL.indexOf("var KINDS=");
  const b = KERNEL.indexOf("if(filtBar)KINDS.forEach", a);
  assert.ok(a > 0 && b > a, "the rig: the error centre's tables and their first use are in kernel.py");
  const r = vm.runInNewContext(KERNEL.slice(a, b) + ";({KINDS, KINDLBL, DESC})", {}) as Tables;
  // copied into this realm: the context's arrays and objects have another prototype, which deepStrictEqual reads as a difference
  return { KINDS: Array.from(r.KINDS), KINDLBL: { ...r.KINDLBL }, DESC: { ...r.DESC } };
}

/** The kinds with a chip colour: every `.rerr-chip.k-<kind>` selector in the served CSS. */
function chipKinds(): Set<string> {
  return new Set(Array.from(KERNEL.matchAll(/\.rerr-chip\.k-([a-z]+)(?=[,{])/g), (m) => m[1]));
}

/** Comments out, so a writer named in prose is not a writer; a block comment leaves its line breaks, so a site's line number is
 *  its number in the file. */
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, "")).replace(/(^|[^:"'`\\])\/\/[^\n]*/g, "$1");

/** The top-level arguments of the call whose `(` is at `open`: parentheses, brackets and braces balanced, strings skipped. */
function callArgs(src: string, open: number): string[] {
  const out: string[] = [];
  let depth = 0, quote = "", start = open + 1;
  for (let i = open; i < src.length; i++) {
    const c = src[i];
    if (quote) { if (c === "\\") i++; else if (c === quote) quote = ""; continue; }
    if (c === '"' || c === "'" || c === "`") { quote = c; continue; }
    if (c === "(" || c === "[" || c === "{") depth++;
    else if (c === ")" || c === "]" || c === "}") { depth--; if (depth === 0) { const last = src.slice(start, i).trim(); if (last) out.push(last); return out; } }
    else if (c === "," && depth === 1) { out.push(src.slice(start, i).trim()); start = i + 1; }
  }
  throw new Error("an unbalanced call at " + open);
}

type Site = { file: string; line: number; form: string; expr: string };

/** Every site under ui/webview (the page modules, not their tests) that posts a notify: the parent post itself, and the three
 *  wrapper names; a wrapper's DEFINITION (its first parameter is `kind: string`) is a site whose kind is its callers'. */
function writerSites(): Site[] {
  const out: Site[] = [];
  for (const f of fs.readdirSync(UI).filter((n) => n.endsWith(".ts") && !n.endsWith(".test.ts") && !n.endsWith(".d.ts")).sort()) {
    const src = code(fs.readFileSync(path.join(UI, f), "utf8"));
    const lineOf = (i: number) => src.slice(0, i).split("\n").length;
    for (const m of src.matchAll(/romp:\s*"notify",\s*kind:\s*([^,}]+)/g)) out.push({ file: f, line: lineOf(m.index!), form: "post", expr: m[1].trim() });
    for (const m of src.matchAll(/\b(tellShell|notifyShell|__rompNotify)\(/g)) {
      const expr = callArgs(src, m.index! + m[0].length - 1)[0] || "";
      out.push({ file: f, line: lineOf(m.index!), form: m[1], expr });
    }
  }
  return out;
}

/** The kinds badge-mirror.ts mints into a BadgeNotice, which feed.ts forwards as `n.kind`: every `kind:` value in the module that is
 *  a string literal or a two-literal ternary, plus the literal second argument of every `add(` call (the helper's `kind` parameter);
 *  an interface's `kind: string` is a type, not a value. Any other value form is returned unread, and the census fails on it. */
function badgeMirrorKinds(): { kinds: Set<string>; unread: string[] } {
  const src = code(fs.readFileSync(path.join(UI, "badge-mirror.ts"), "utf8"));
  const kinds = new Set<string>(), unread: string[] = [];
  for (const m of src.matchAll(/\bkind\??:\s*([^,;}\n]+)/g)) {
    const v = m[1].trim();
    if (v === "string") continue;
    const lit = /^"([a-z]+)"$/.exec(v);
    const tern = /^[\w.]+ === "[a-z]+" \? "([a-z]+)" : "([a-z]+)"$/.exec(v);
    if (lit) kinds.add(lit[1]);
    else if (tern) { kinds.add(tern[1]); kinds.add(tern[2]); }
    else unread.push(v);
  }
  for (const m of src.matchAll(/\badd\(/g)) {
    const args = callArgs(src, m.index! + m[0].length - 1);
    if (args.length < 2) continue;                                   // a Set's add(sig): not the helper
    const lit = /^"([a-z]+)"$/.exec(args[1]);
    if (lit) kinds.add(lit[1]); else unread.push("add(" + args.slice(0, 2).join(", ").slice(0, 60) + ")");
  }
  return { kinds, unread };
}

test("the shell's Log knows the `frozen` kind the apply-throw refusal posts: listed, labelled, explained, worn in the warning yellow, and read where the page renders it", () => {
  // the registration keys on the PROPERTY (the kind is in every table the page evaluates) and never on the array literal's
  // spelling: the KINDS line is upstream's, and the fork registers on lines after the tables
  const { KINDS, KINDLBL, DESC } = tables();
  assert.ok(KINDS.includes("frozen"), "KINDS lists it, so the filter row gets its toggle: " + KINDS.join(","));
  assert.equal(KINDLBL.frozen, "cards frozen", "the chip's text");
  assert.match(DESC.frozen, /frozen at their last update/, "the tooltip says what the person sees");
  assert.match(DESC.frozen, /reconnects/, "and the way out");
  assert.match(KERNEL, /\.rerr-chip\.k-frozen\{color:#ffd166;border-color:rgba\(255,209,102,0\.6\)\}/, "its chip wears the warning yellow (stale, not lost), a rule of its own");
  // the tables read here are the ones the page renders from: the filter row iterates KINDS and the chip keys on KINDLBL
  assert.ok(KERNEL.includes("if(filtBar)KINDS.forEach(function(k){"), "the filter row is built from KINDS");
  assert.ok(KERNEL.includes("if(KINDLBL[n.kind]){ch.className='rerr-chip k-'+n.kind;"), "an entry's chip is drawn only for a kind KINDLBL knows");
});

test("every notify kind a ui/webview writer posts is registered in all three tables and has a chip; the tables agree with each other; the one unregistered kind is upstream's `ended`, stated here until it is registered", (t) => {
  const { KINDS, KINDLBL, DESC } = tables();
  const chips = chipKinds();
  assert.deepEqual(Object.keys(KINDLBL).sort(), [...KINDS].sort(), "KINDLBL labels exactly the kinds KINDS lists");
  assert.deepEqual(Object.keys(DESC).sort(), [...KINDS].sort(), "DESC explains exactly the kinds KINDS lists");
  assert.deepEqual(KINDS.filter((k) => !chips.has(k)), [], "every listed kind has a chip colour rule");
  const sites = writerSites();
  assert.ok(sites.length >= 14, "the rig: the writers this census read when it was written (" + sites.length + "): " + sites.map((s) => s.file + ":" + s.line).join(" "));
  const posted = new Map<string, string[]>();
  const wrappers = new Set(sites.filter((s) => /^kind: string\b/.test(s.expr)).map((s) => s.file));
  const unclassified: string[] = [];
  const badge = badgeMirrorKinds();
  assert.deepEqual(badge.unread, [], "a kind value in badge-mirror.ts in a form this census does not read (a literal, a two-literal ternary or add()'s second argument)");
  for (const s of sites) {
    const where = s.file + ":" + s.line + " " + s.form + "(" + s.expr + ")";
    const lit = /^["']([a-z]+)["']$/.exec(s.expr);
    if (lit) posted.set(lit[1], [...(posted.get(lit[1]) || []), where]);
    else if (/^kind: string\b/.test(s.expr)) continue;                       // a wrapper's definition: its callers are sites above
    else if (s.expr === "kind" && wrappers.has(s.file)) continue;            // the wrapper's own post of its parameter
    else if (s.expr === "n.kind" && s.file === "feed.ts") for (const k of badge.kinds) posted.set(k, [...(posted.get(k) || []), where + " via badge-mirror.ts"]);
    else unclassified.push(where);
  }
  assert.deepEqual(unclassified, [], "a notify writer whose kind this census cannot read (not a literal, a wrapper's parameter or feed.ts's forwarded BadgeNotice kind): classify it here or make it a literal");
  t.diagnostic("kinds posted under ui/webview: " + [...posted.keys()].sort().join(",") + " from " + sites.length + " sites; badge-mirror mints " + [...badge.kinds].sort().join(","));
  assert.ok(posted.has("frozen"), "the apply-throw refusal's kind is among the posted kinds: " + [...posted.keys()].sort().join(","));
  assert.equal((posted.get("frozen") || []).length, 2, "posted at its two sites, the wire road's and the local road's: " + (posted.get("frozen") || []).join(" "));
  // the one pre-existing gap, upstream's and from before this branch: clearBoundaryNotices mints `ended` for a session death that
  // finalized open cards, and no table knows it (the maintainer's item, filed with this review); registering it reds this line
  // until the exception comes out, and a second unregistered kind reds it too
  const unregistered = [...posted.keys()].filter((k) => !KINDS.includes(k)).sort();
  assert.deepEqual(unregistered, ["ended"], "every kind a ui/webview writer posts is registered, but upstream's `ended` (badge-mirror.ts, from before this branch): " + unregistered.map((k) => k + " at " + (posted.get(k) || []).join(" ")).join("; "));
});
