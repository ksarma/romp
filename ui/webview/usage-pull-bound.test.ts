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
const PULL = between(USAGE, "window.__rompUsagePull=function(){", "// the API-health dot sits inside this cell");
// the script's read of the readings, the function __rompUsagePull hands its signal to, found by its opening statement
const READ_NAME = (USAGE.match(/function (\w+)\(sig\)\{var ok=false,n=\+\+PULLS;/) || [])[1];
assert.ok(READ_NAME, "the read of the readings, numbering its pulls");
const READ = between(USAGE, "function " + READ_NAME + "(sig){", "function pull(ack){");
const FAILED = between(USAGE, "window.__rompUsageFailed=function(){", "\n");
// the comment over the pull, as prose: its lines from the one that opens it down to the pull, each line's // taken off
const NOTE = between(USAGE, "// ...and the source behind those answers", "window.__rompUsagePull=function(){")
  .split("\n").map((l) => l.replace(/^\/\/ ?/, "").trim()).filter(Boolean).join(" ");

type Pulled = { url: string; signal: AbortSignal | null };
type World = { pull: () => Promise<unknown>; failed: () => boolean; win: Record<string, unknown>; fetches: Pulled[]; tells: number; renders: number };
// the pull's code in a world of its own: that read, __rompUsageFailed and __rompUsagePull as kernel.py has them, over a fetch
// that answers ok with no rows, or never answers and rejects when its signal aborts (as a real fetch does); renderRows and the
// card's tell counted
function world(answer: "ok" | "hang"): World {
  const w: World = { pull: () => Promise.resolve(), failed: () => false, win: {}, fetches: [], tells: 0, renders: 0 };
  const fetchStub = (url: string, opts?: { signal?: AbortSignal }) => {
    const signal = (opts && opts.signal) || null;
    w.fetches.push({ url, signal });
    if (answer === "ok") return Promise.resolve({ ok: true, json: () => Promise.resolve({ rows: [], host: "" }) });
    return new Promise((_resolve, reject) => { if (signal) signal.addEventListener("abort", () => reject(signal.reason), { once: true }); });
  };
  const made = new Function("window", "fetch", "renderRows", "notices", "cardTell",
    "var READ_FAILED=false,PULLS=0,PULL_ENDED=0,SELF='';\n" + READ + "\n" + FAILED + "\n" + PULL +
    "\nreturn { pull: window.__rompUsagePull, failed: window.__rompUsageFailed };")(
    w.win, fetchStub, () => { w.renders++; }, () => undefined, () => { w.tells++; });
  w.pull = made.pull;
  w.failed = made.failed;
  return w;
}

test("the bound's default is 10 s, the figure the kernel's comment states, and the comment gives the reason for it", () => {
  const code = PULL.match(/\(window\.__rompUsagePullMs\|0\)\|\|(\d+)/);
  assert.ok(code, "the pull's default, read after the override");
  const said = NOTE.match(/(\d+) s: the kernel answers \/usage\/\w+ from usage\.json/);
  assert.ok(said, "the comment states the bound in seconds where it gives the reason");
  assert.equal(Number(code![1]), 10000, "the default is 10 s");
  assert.equal(Number(said![1]) * 1000, Number(code![1]), "the comment's figure is the code's");
  // the reason, in the comment's words: an answer is cheap and fast, and the person at the card learns that the read failed
  // within seconds, sooner than the spend panel's heavier read allows
  for (const why of [
    "from usage.json and the tunnel supervisor's cached readings, dialing nothing, so an answer takes well under a second even over a phone's network",
    "within seconds rather than after the 20 s the spend panel allows its heavier read",
  ]) assert.ok(NOTE.includes(why), "the reason: " + why);
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
