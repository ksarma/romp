// The gear's File comments row (plans/file-review.md, Getting into it): the row "names the machine and the
// reason". The reason is one FILECOMMENTS_SUB sentence per /defaults verdict; the machine is the local
// kernel's name from the /tunnels read fill() already makes (`local.host`), swapped in for the literals'
// "this machine" — the gear's phrase for the local kernel, kept as the fallback when /tunnels has not
// answered or an older kernel's /tunnels carries no `local`. BEHAVIORAL where it can be: the copy table,
// fileCommentsText, the state-and-paint block and the two fetch handlers' row fragments are lifted out of
// gear.js by anchor and run against a stub document, so the race between /defaults and /tunnels is
// exercised in both orders. The wiring that cannot be lifted without the whole of fill() is pinned at
// source. Synthetic names only: TESTHOST, and the notes-api world's web/api machines.
//
// Also pinned: the one DEVIATION from the plan sentence — "offers to run the link step" — is stated in
// the row's comment and the row stays a report (no button, no invented op). No kernel op runs install.sh
// from a socket; adding one is a Security posture decision the plan has to make, not the row.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");

// slice `src` from `start` (inclusive) to the first `stop` after it (inclusive); every anchor must exist
function slice(src: string, start: string, stop: string, from = 0): string {
  const a = src.indexOf(start, from);
  assert.ok(a >= 0, "anchor not found — gear.js moved: " + start.slice(0, 50));
  const b = src.indexOf(stop, a);
  assert.ok(b > a, "end anchor not found — gear.js moved: " + stop.slice(0, 50));
  return src.slice(a, b + stop.length);
}

type Row = { textContent: string };
type Api = {
  SUB: Record<string, string>;
  text: (base: string | null, host: string, others: string[]) => string;
  onTunnels: (d: unknown) => void;
  onDefaults: (d: unknown) => void;
  onDefaultsFail: () => void;
  state: () => { base: string | null; host: string; others: string[] };
};

// The lift: the copy table and the pure text function (top level), the row's state + paint (initGear),
// and the three handler fragments (inside fill()'s /tunnels then, /defaults then, /defaults catch),
// each wrapped in a function that takes what the surrounding closure supplied (`d`, and `rows` derived
// from it exactly as fill() derives it).
function lift(el: Row | null): Api {
  const table = slice(GEAR, "var FILECOMMENTS_SUB = {", "\n};\n");
  const fn = slice(GEAR, "function fileCommentsText(base, host, others) {", "\n}\n");
  const state = slice(GEAR, "  var fcBase = null, fcHost = '', fcOthers = [];", "\n  }\n");
  const tunnels = slice(GEAR, "      fcHost = (d && d.local", "      paintFileComments();\n");
  const defaults = slice(GEAR, "        fcBase = FILECOMMENTS_SUB[typeof d.fileComments", "        paintFileComments();\n");
  const fail = slice(GEAR, "        fcBase = FILECOMMENTS_SUB.unknown;", "        paintFileComments();\n");
  const src = table + fn + state
    + "\nfunction onTunnels(d) { var rows = (d && d.tunnels) || [];\n" + tunnels + "}\n"
    + "function onDefaults(d) {\n" + defaults + "}\n"
    + "function onDefaultsFail() {\n" + fail + "}\n"
    + "return { SUB: FILECOMMENTS_SUB, text: fileCommentsText, onTunnels: onTunnels, onDefaults: onDefaults, onDefaultsFail: onDefaultsFail,"
    + " state: function () { return { base: fcBase, host: fcHost, others: fcOthers }; } };";
  const doc = { getElementById: (id: string) => (id === "rs-filecomments" ? el : null) };
  return new Function("document", src)(doc) as Api;
}
const row = (): Row => ({ textContent: "" });
const VERDICTS = ["ok", "no-node", "agent-tooling-absent", "unknown"] as const;

test("executed: the machine's name from /tunnels replaces 'this machine' in every verdict's sentence; the fallback keeps the phrase", () => {
  const { SUB, text } = lift(null);
  for (const v of [...VERDICTS, "checking"]) {
    assert.match(SUB[v], /[Tt]his machine/, v + ": the literal is written about one machine");
    const named = text(v === "checking" ? null : SUB[v], "TESTHOST", []);
    assert.doesNotMatch(named, /[Tt]his machine/, v + ": nothing left unnamed");
    assert.match(named, /TESTHOST/, v + ": names the machine");
    assert.equal(text(v === "checking" ? null : SUB[v], "", []), SUB[v], v + ": no name yet → the literal, unchanged");
  }
  // the reason survives the naming, with the machine in it
  assert.match(text(SUB["no-node"], "TESTHOST", []), /^Comments are unavailable on TESTHOST: node was not found on the kernel’s PATH, so the Comments action does not appear on its files\./);
  assert.match(text(SUB["agent-tooling-absent"], "TESTHOST", []), /but its sessions cannot reply to them: .*Run install\.sh on TESTHOST; there is no button for it\. The link step places track-reply, track-edit, track-comment, track-config, and the guard hook in ~\/\.claude\/hooks\.$/);
  assert.match(text(SUB.unknown, "TESTHOST", []), /^TESTHOST’s kernel predates file comments/, "the capitalised sentence-opener is renamed too");
  assert.match(text(SUB.ok, "TESTHOST", []), /work on TESTHOST’s files: .*and its sessions can reply to what you send\./);
  // a name is inserted as data: String.replace's $-patterns never fire (ROMP_HOST_NAME is not validated by the kernel)
  assert.equal(text(SUB.unknown, "a$&b$1", []), SUB.unknown.replace("This machine", "a$$&b$$1"));
});

test("executed: with other machines attached the row says whose files it covers and whose it does not; not while checking, not alone", () => {
  const { SUB, text } = lift(null);
  const t = text(SUB.ok, "TESTHOST", ["web-box", "api-box"]);
  assert.ok(t.startsWith(SUB.ok.replace(/[Tt]his machine/g, "TESTHOST") + " "), "the verdict sentence first, then the scope");
  assert.match(t, / This row covers TESTHOST only\. Files owned by web-box, api-box are checked by their own kernels, and those answers are not shown here\.$/);
  assert.equal(t.split("This row covers").length, 2, "appended once");
  assert.match(text(SUB["no-node"], "", ["web-box"]), / This row covers this machine only\. Files owned by web-box are checked/, "the fallback name in the scope sentence too");
  assert.equal(text(SUB.ok, "TESTHOST", []), SUB.ok.replace(/[Tt]his machine/g, "TESTHOST"), "no peers → no scope sentence");
  assert.equal(text(null, "TESTHOST", ["web-box"]), SUB.checking.replace(/[Tt]his machine/g, "TESTHOST"), "still checking → no scope sentence yet");
  // the person's words: the scope sentence names no romp-internal noun for the answer
  assert.doesNotMatch(t.slice(t.indexOf(" This row covers")), /verdict/i);
});

test("executed: /defaults and /tunnels race — either order ends on the same named row; a failed /defaults still names the machine", () => {
  const tun = { tunnels: [{ host: "web-box", status: "up" }, { host: "api-box", status: "down" }, { host: "", status: "up" }, null],
                local: { ver: "0.9.0", sha: "abcdef0", host: "TESTHOST" } };
  const want = (a: Api) => a.text(a.SUB["agent-tooling-absent"], "TESTHOST", ["web-box"]);
  // /defaults first: the row paints unnamed, then /tunnels names it
  let el = row(); let api = lift(el);
  assert.equal(el.textContent, "", "nothing painted before either read (the HTML carries the checking line)");
  api.onDefaults({ defaultDir: "~/code", nativeDialogs: false, fileComments: "agent-tooling-absent" });
  assert.equal(el.textContent, api.SUB["agent-tooling-absent"], "verdict first, the machine still unnamed");
  api.onTunnels(tun);
  assert.equal(el.textContent, want(api), "…then named, with only the UP peers (a down row and a nameless row are not files anyone can open here)");
  const a = el.textContent;
  // /tunnels first: the checking line is named, then the verdict lands already named
  el = row(); api = lift(el);
  api.onTunnels(tun);
  assert.equal(el.textContent, api.SUB.checking.replace(/[Tt]his machine/g, "TESTHOST"), "the checking line names the machine while /defaults is out");
  api.onDefaults({ fileComments: "agent-tooling-absent" });
  assert.equal(el.textContent, a, "same final text in either order");
  // an older kernel: /defaults without the key → the unknown sentence; /tunnels without `local` → unnamed
  el = row(); api = lift(el);
  api.onTunnels({ tunnels: [] });
  api.onDefaults({ defaultDir: "~/code" });
  assert.equal(el.textContent, api.SUB.unknown);
  assert.deepEqual(api.state(), { base: api.SUB.unknown, host: "", others: [] });
  // /defaults failed (rejected fetch, non-JSON): the unknown sentence, still named when /tunnels answered
  el = row(); api = lift(el);
  api.onTunnels(tun);
  api.onDefaultsFail();
  assert.equal(el.textContent, api.text(api.SUB.unknown, "TESTHOST", ["web-box"]));
  // no row in the DOM (the gear not mounted): the paint is a no-op, the state still moves
  api = lift(null);
  api.onTunnels(tun); api.onDefaults({ fileComments: "ok" });
  assert.equal(api.state().host, "TESTHOST");
});

test("source: the name rides the /tunnels read fill() already makes, the paint is event-driven, and the row stays a report", () => {
  // one /tunnels fetch per fill(), and the row's fragment sits in ITS then-handler, after the marks
  assert.equal(GEAR.split("fetch(ku('/tunnels')").length, 2, "one /tunnels read");
  assert.match(GEAR, /fillMixedMarks\(v, rows\);\n(\s*\/\/[^\n]*\n)*\s*fcHost = \(d && d\.local && typeof d\.local\.host === 'string'\) \? d\.local\.host : '';/);
  assert.match(GEAR, /fcOthers = rows\.filter\(function \(t\) \{ return t && t\.status === 'up' && t\.host; \}\)\.map\(function \(t\) \{ return t\.host; \}\);/, "up peers only, as fillAutoNudge counts them");
  // the /defaults handler keeps the verdict lookup the panel test pins, and both handlers paint through the one function
  assert.match(GEAR, /fcBase = FILECOMMENTS_SUB\[typeof d\.fileComments === 'string' \? d\.fileComments : 'unknown'\] \|\| FILECOMMENTS_SUB\.unknown;\n\s*paintFileComments\(\);/);
  assert.equal(GEAR.split("paintFileComments();").length, 4, "painted from /tunnels, /defaults, and the /defaults catch — nowhere else");
  const paint = slice(GEAR, "  function paintFileComments() {", "\n  }\n");
  assert.match(paint, /fcs\.textContent = fileCommentsText\(fcBase, fcHost, fcOthers\)/, "textContent, never HTML — a host name is data");
  assert.doesNotMatch(slice(GEAR, "  var fcBase = null", "\n  }\n") + slice(GEAR, "function fileCommentsText", "\n}\n"), /setTimeout|setInterval/, "no timers: the reads' answers are the events");
  // the row itself: text only — no button, no delegated action, no op to run the link step
  const markup = slice(GEAR, "<b>File comments</b>", "</span></div>' +");
  assert.doesNotMatch(markup, /<button|data-act|onclick|<a /, "a report, not a control");
  assert.doesNotMatch(GEAR, /linkTooling|installTooling|fileCommentsLink|runInstall/, "no WS op to run the link step is invented");
});

test("source: the deviation from the plan sentence is stated where the row is built, with its reason", () => {
  const comment = GEAR.slice(GEAR.indexOf("  // File comments (plans/file-review.md Slice 1)"), GEAR.indexOf("<b>File comments</b>"));
  assert.match(comment, /DEVIATION/, "named as one, not left implicit");
  assert.match(comment, /"offers to run\s*\/\/\s*the link step"|offers to run the link step/, "quotes the plan sentence it departs from");
  assert.match(comment, /no kernel op runs install\.sh/, "the reason: the mechanism does not exist");
  assert.match(comment, /Security posture/, "and why the row does not add it: a posture decision for the plan");
  // the copy: the person's words, no em dashes, no fleet, no home paths, no time words for a state
  const sub = slice(GEAR, "var FILECOMMENTS_SUB = {", "\n};\n");
  assert.doesNotMatch(sub, /—/, "no em dashes in UI copy");
  assert.doesNotMatch(sub, /\byet\b|\bcurrently\b|\bnow\b/, "a state, not a moment");
  assert.doesNotMatch(sub, /fleet/i);
  assert.doesNotMatch(sub, /\/home\/[a-z]/);
  assert.match(sub, /'agent-tooling-absent': '[^']*Run install\.sh on this machine; there is no button for it\./, "the step is named and the missing button admitted, in that order");
});
