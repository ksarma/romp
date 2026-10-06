// The settings card's usage pull and its bound (PR 976, iOS item 4g; romp-manager's decisions on its round 1 builds). Each
// opening of the card asks the shell for a fresh read of the usage readings (kernel/kernel.py _LANDING_USAGE_JS,
// window.__rompUsagePull; ui/webview/gear.js usagePull) and shows the romp loader on Usage until the pull ends. The pull carries
// a bounded abort, so the loader ends on an event even when the kernel never answers, and Usage then says Couldn't load.
// tests/test_mtabs_fit_served.py runs that end in three engines under a 1.5 s override (window.__rompUsagePullMs) and expects
// it within 5 s of the click, so an override the pull does not apply reads as hung there; the default itself, 10 s, is out of
// that test's reach. This file holds it: the value and the reason the kernel's comment gives for it (a source pin, so the value
// cannot change without the reason being rewritten beside it), and the pull's own code, lifted from kernel.py and run here, set
// at the default with no override and at the override where one is set.
import { test } from "node:test";
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
