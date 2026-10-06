// The settings card's usage pull and its bound (PR 976, iOS item 4g; romp-manager's decisions on its round 1 builds). Each
// opening of the card asks the shell for a fresh read of the usage readings (kernel/kernel.py _LANDING_USAGE_JS,
// window.__rompUsagePull; ui/webview/gear.js usagePull) and shows the romp loader on Usage until the pull ends. The pull carries
// a bounded abort, so the loader ends on an event even when the kernel never answers, and Usage then says Couldn't load.
// tests/test_mtabs_fit_served.py runs that end in three engines under a 1.5 s override (window.__rompUsagePullMs) and expects
// it within 5 s of the click, so an override the pull does not apply reads as hung there; the default itself, 10 s, is out of
// that test's reach. This file holds it: the value and the reason the kernel's comment gives for it (a source pin, so the value
// cannot change without the reason being rewritten beside it), and the pull's own code, lifted from kernel.py and run here, set
// at the default with no override and at the override where one is set. And an engine without AbortSignal.timeout (Safari
// before 16; romp-manager's fourth decision on those builds): the same code run with AbortSignal.timeout deleted and the timers
// mocked, where an AbortController with a timer of the same bound aborts the fetch at the bound, the read is marked failed and
// the card told, and the card's own code (gear.js usageAct, run over that shell) lands in Couldn't load; the timer takes the
// override too, and a pull that ends first clears it.
// Then PR 976's round 2. Every read of the readings goes through the script's one bounded helper (boundedPull): a census of
// the script's code finds the read's name in its declaration and in the helper alone, so no caller reaches the read unbounded,
// and the card's name and the panel's opener reach the helper.
import { test, mock } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const KERNEL = read("kernel", "kernel.py");
const OPEN = '_LANDING_USAGE_JS = """';
const START = KERNEL.indexOf(OPEN) + OPEN.length;
const USAGE = KERNEL.slice(START, KERNEL.indexOf('"""', START));
assert.ok(START > OPEN.length && USAGE.length > 1000, "the shell's usage script");
function between(src: string, a: string, b: string): string {
  const i = src.indexOf(a), j = src.indexOf(b, i + a.length);
  assert.ok(i >= 0 && j > i, "found: " + a.slice(0, 60));
  assert.equal(src.indexOf(a, i + 1), -1, "once: " + a.slice(0, 60));
  return src.slice(i, j);
}
// the script's read of the readings, found by its opening statement (it numbers its reads), and the code the cases lift: the
// read, __rompUsageFailed and __rompUsageReading as kernel.py has them
const READ_NAME = (USAGE.match(/function (\w+)\(sig\)\{var ok=false,n=\+\+PULLS;/) || [])[1];
assert.ok(READ_NAME, "the read of the readings, numbering its pulls");
const READ = between(USAGE, "function " + READ_NAME + "(sig){", "function pull(ack){");
const FAILED = between(USAGE, "window.__rompUsageFailed=function(){", "\n");
const READING = between(USAGE, "window.__rompUsageReading=function(){", "\n");
// ...and, read when a case needs it, the one bounded helper with the card's name for it, from the helper down to the next
// section's comment, and the comment over it as prose: its lines from the one that opens it down to the helper, each line's
// // taken off. A case that needs neither runs where they are missing
const pullCode = () => between(USAGE, "function boundedPull(){", "// the API-health dot sits inside this cell");
const note = () => between(USAGE, "// ...and the source behind those answers", "function boundedPull(){")
  .split("\n").map((l) => l.replace(/^\/\/ ?/, "").trim()).filter(Boolean).join(" ");

type Answer = { ok: boolean; rows: unknown[] } | "fail";
type Pending = { url: string; signal: AbortSignal | null; end: (a: Answer) => void };
type World = { pull: () => Promise<unknown>; failed: () => boolean; reading: () => boolean; read: () => Promise<unknown>;
  win: Record<string, unknown>; fetches: Pending[]; tells: number; renders: number; last: unknown[] };
// the pull's code in a world of its own: the read, __rompUsageFailed and __rompUsageReading as kernel.py has them, with the
// bounded helper where a case asks for it, over a fetch that
// answers ok with no rows ("ok"), never answers and rejects when its signal aborts, as a real fetch does ("hang"), or waits
// for the case to end it ("held": an ok answer with rows, an error status, or a failure in transit). renderRows stands for the
// script's own: it keeps each row that has a usage as the readings (tipHTML then says there is a reading) and tells the card;
// the card's tell is counted, and a case can hook it
function world(answer: "ok" | "hang" | "held", parts: { helper?: boolean } = { helper: true }, onTell?: () => void): World {
  const w: World = { pull: () => Promise.resolve(), failed: () => false, reading: () => false, read: () => Promise.resolve(),
    win: {}, fetches: [], tells: 0, renders: 0, last: [] };
  const tell = () => { w.tells++; if (onTell) onTell(); };
  const renderRows = (rows: unknown[]) => { w.renders++; w.last = (rows || []).filter((r) => !!(r && (r as { usage?: unknown }).usage)); tell(); };
  const fetchStub = (url: string, opts?: { signal?: AbortSignal }) => {
    const signal = (opts && opts.signal) || null;
    return new Promise((resolve, reject) => {
      const end = (a: Answer) => {
        if (a === "fail") reject(new TypeError("synthetic failure in transit"));
        else resolve({ ok: a.ok, json: () => Promise.resolve({ rows: a.rows, host: "" }) });
      };
      w.fetches.push({ url, signal, end });
      if (answer === "ok") end({ ok: true, rows: [] });
      if (signal) signal.addEventListener("abort", () => reject(signal.reason), { once: true });
    });
  };
  const made = new Function("window", "fetch", "renderRows", "notices", "cardTell", "tipHTML",
    "var READ_FAILED=false,PULLS=0,PULL_ENDED=0,SELF='';\n" + READ + "\n" + FAILED + "\n" + READING + "\n" +
    (parts.helper ? pullCode() + "\n" : "") +
    "return { pull: window.__rompUsagePull, failed: window.__rompUsageFailed, reading: window.__rompUsageReading," +
    " read: " + READ_NAME + " };")(
    w.win, fetchStub, renderRows, () => undefined, tell, () => (w.last.length ? "a reading" : ""));
  w.pull = made.pull;
  w.failed = made.failed;
  w.reading = made.reading;
  w.read = made.read;
  return w;
}

test("the bound's default is 10 s, the figure the kernel's comment states, and the comment gives the reason for it", () => {
  const code = pullCode().match(/\(window\.__rompUsagePullMs\|0\)\|\|(\d+)/);
  assert.ok(code, "the pull's default, read after the override");
  const said = note().match(/(\d+) s: the kernel answers \/usage\/\w+ from usage\.json/);
  assert.ok(said, "the comment states the bound in seconds where it gives the reason");
  assert.equal(Number(code![1]), 10000, "the default is 10 s");
  assert.equal(Number(said![1]) * 1000, Number(code![1]), "the comment's figure is the code's");
  // the reason, in the comment's words: an answer is cheap and fast, and the person at the card learns that the read failed
  // within seconds, sooner than the spend panel's heavier read allows
  for (const why of [
    "from usage.json and the tunnel supervisor's cached readings, dialing nothing, so an answer takes well under a second even over a phone's network",
    "within seconds rather than after the 20 s the spend panel allows its heavier read",
  ]) assert.ok(note().includes(why), "the reason: " + why);
});

test("the pull's abort is set at 10 s with no override, and at window.__rompUsagePullMs where that is set", async () => {
  const saved = Object.getOwnPropertyDescriptor(AbortSignal, "timeout");
  assert.ok(saved, "this node has AbortSignal.timeout to stand in for");
  const asked: number[] = [];
  Object.defineProperty(AbortSignal, "timeout", { configurable: true, writable: true,
    value: (ms: number) => { asked.push(ms); return new AbortController().signal; } });
  try {
    const plain = world("ok");
    await plain.pull();
    const short = world("ok");
    short.win.__rompUsagePullMs = 1500;
    await short.pull();
    assert.deepEqual(asked, [10000, 1500]);
    assert.ok(plain.fetches[0].signal && short.fetches[0].signal, "each fetch carries the signal");
    assert.match(plain.fetches[0].url, /^\/usage\//, "the usage read");
  } finally {
    Object.defineProperty(AbortSignal, "timeout", saved!);
  }
});

// the card's own code for Usage's state (gear.js usageAct), run over a shell that answers with the given reading and read
// failure: the button's disabled state and which of its two lines shows
const GEAR = read("ui", "webview", "gear.js");
const USAGE_ACT = between(GEAR, "  function usageAct() {", "  // the opening's ask:");
class El {
  hidden = true;
  disabled = false;
  attrs: Record<string, string> = {};
  setAttribute(k: string, v: string) { this.attrs[k] = v; }
  removeAttribute(k: string) { delete this.attrs[k]; }
}
function usageCard(shell: { reading: () => boolean; failed: () => boolean }): { disabled: boolean; none: boolean; err: boolean } {
  const els: Record<string, El> = { "rs-pact-usage": new El(), "rs-pact-usage-none": new El(), "rs-pact-usage-err": new El(), "rs-pact-usage-wait": new El() };
  const win = { parent: { __rompUsageReading: shell.reading, __rompUsageFailed: shell.failed } };
  const act = new Function("document", "window", "var usageWait = 0;\n" + USAGE_ACT + "\nreturn usageAct;")(
    { getElementById: (id: string) => els[id] || null }, win);
  act();
  return { disabled: els["rs-pact-usage"].disabled, none: !els["rs-pact-usage-none"].hidden, err: !els["rs-pact-usage-err"].hidden };
}
function track(p: Promise<unknown>): { done: boolean; ok: boolean; err: unknown } {
  const s = { done: false, ok: false, err: null as unknown };
  p.then(() => { s.done = true; s.ok = true; }, (e) => { s.done = true; s.err = e; });
  return s;
}
const flush = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };
// an engine without AbortSignal.timeout: the static method deleted for the test's length, setTimeout mocked, both put back
async function withoutTimeout(fn: () => Promise<void>): Promise<void> {
  const saved = Object.getOwnPropertyDescriptor(AbortSignal, "timeout");
  assert.ok(saved, "this node has AbortSignal.timeout to delete");
  delete (AbortSignal as unknown as { timeout?: unknown }).timeout;
  mock.timers.enable({ apis: ["setTimeout"] });
  try {
    assert.equal(typeof (AbortSignal as unknown as { timeout?: unknown }).timeout, "undefined", "the premise: no AbortSignal.timeout");
    await fn();
  } finally {
    mock.timers.reset();
    Object.defineProperty(AbortSignal, "timeout", saved!);
  }
}

test("where AbortSignal.timeout is absent, an AbortController with a timer of the same bound aborts the pull at 10 s, and the card lands in Couldn't load", async () => {
  await withoutTimeout(async () => {
    const w = world("hang");
    const s = track(w.pull());
    await flush();
    const sig = w.fetches.length === 1 ? w.fetches[0].signal : null;
    assert.ok(sig, "the fetch carries an abort signal");
    mock.timers.tick(9999);
    await flush();
    assert.equal(s.done, false, "the pull is still out 1 ms before the bound");
    assert.equal(sig!.aborted, false);
    assert.equal(w.failed(), false);
    mock.timers.tick(1);
    await flush();
    assert.equal(sig!.aborted, true, "aborted at the bound");
    assert.ok(s.done && !s.ok, "the pull rejects");
    assert.equal((s.err as Error).name, "AbortError");
    assert.equal(w.failed(), true, "the read is marked failed (__rompUsageFailed)");
    assert.equal(w.tells, 1, "and the card is told");
    assert.equal(w.renders, 0, "the readings are left as they were");
    // the card over that shell: with no reading, Usage disabled with Couldn't load and not No reading yet; with a reading the
    // shell still holds, Usage enabled beside the same line
    assert.deepEqual(usageCard({ reading: () => false, failed: w.failed }), { disabled: true, none: false, err: true });
    assert.deepEqual(usageCard({ reading: () => true, failed: w.failed }), { disabled: false, none: false, err: true });
  });
});

test("without AbortSignal.timeout, the fallback's timer takes window.__rompUsagePullMs, and a pull that ends first clears it", async () => {
  await withoutTimeout(async () => {
    const w = world("hang");
    w.win.__rompUsagePullMs = 1500;
    const s = track(w.pull());
    await flush();
    const sig = w.fetches.length === 1 ? w.fetches[0].signal : null;
    assert.ok(sig, "the fetch carries an abort signal");
    mock.timers.tick(1499);
    await flush();
    assert.equal(sig!.aborted, false, "still out 1 ms before the override");
    mock.timers.tick(1);
    await flush();
    assert.ok(sig!.aborted && s.done && !s.ok && w.failed(), "aborted at the override, the read marked failed");
    const ok = world("ok");
    await ok.pull();
    const done = ok.fetches.length === 1 ? ok.fetches[0].signal : null;
    assert.ok(done, "the answered fetch carried an abort signal too");
    mock.timers.tick(10000);
    await flush();
    assert.equal(done!.aborted, false, "the timer was cleared when the pull ended first: nothing aborts it at the bound");
    assert.equal(ok.failed(), false);
  });
});

// The census (PR 976's round 2, romp-manager's first rule): the script's code with each whole-line comment dropped and each
// trailing one cut (the kernel's two spellings of one: three spaces then //, and // right after a statement's ;), so a name in
// a comment counts for nothing
function codeOf(src: string): string {
  return src.split("\n").map((ln) => {
    if (ln.trimStart().startsWith("//")) return "";
    for (const mark of ["   //", ";//"]) { const i = ln.indexOf(mark); if (i >= 0) ln = ln.slice(0, i) + (mark === ";//" ? ";" : ""); }
    return ln;
  }).join("\n");
}
// the end of the braced body that opens at `open` (the index of its {), by depth
function bodyEnd(code: string, open: number): number {
  assert.equal(code[open], "{", "a body opens here");
  let depth = 0;
  for (let i = open; i < code.length; i++) {
    if (code[i] === "{") depth++;
    else if (code[i] === "}" && --depth === 0) return i;
  }
  return assert.fail("the body never closes");
}

test("every read of the readings goes through the one bounded helper: no caller reaches the read unbounded, and the card's name, the panel's opener and pull() reach the helper", () => {
  const code = codeOf(USAGE);
  const head = "function boundedPull(){";
  const at = code.indexOf(head);
  assert.ok(at >= 0, "the script's one bounded helper, boundedPull");
  assert.equal(code.indexOf(head, at + 1), -1, "declared once");
  const end = bodyEnd(code, at + head.length - 1);
  // every use of the read's name in the code: its declaration, and inside the helper's body alone. A call anywhere else (a
  // caller reaching the read with no bound) or the name handed on as a value is listed with the code around it
  const decl = code.indexOf("function " + READ_NAME + "(sig){") + "function ".length;
  const uses = Array.from(code.matchAll(new RegExp("\\b" + READ_NAME + "\\b", "g")), (m) => m.index as number);
  const stray = uses.filter((i) => i !== decl && !(i > at && i < end)).map((i) => code.slice(Math.max(0, i - 50), i + 30).replace(/\s+/g, " "));
  assert.deepEqual(stray, [], "the read reached outside the bounded helper");
  assert.equal(uses.length, 2, "the read's name: its declaration and the helper's one call");
  assert.ok(code.slice(at, end).includes(READ_NAME + "(sig)"), "the helper hands the read the abort signal it sets");
  // the card's name for the pull is the helper itself, and the panel's opener and pull() call the helper by its own name, so
  // a page that wraps or deletes the window name (as the served test's race does) leaves the opener's bound in place
  assert.ok(/window\.__rompUsagePull=boundedPull;/.test(code), "window.__rompUsagePull is bound to the helper");
  const panel = between(code, "window.__rompUsagePanel=function(){", "window.__rompUsageReading=function(){");
  assert.ok(/boundedPull\(\)\.then\(openIt,openIt\)/.test(panel), "the panel's opener pulls through the helper");
  assert.ok(!/__rompUsagePull\b/.test(panel), "the panel's opener does not read the window name");
  const pullAt = code.indexOf("function pull(ack){");
  assert.ok(pullAt >= 0, "pull(), the readout's click and the 60 s refresh");
  const pullFn = code.slice(pullAt, bodyEnd(code, pullAt + "function pull(ack)".length));
  assert.ok(/boundedPull\(\)\.then\(done,/.test(pullFn), "pull() pulls through the helper");
});
