// The math renderer's load attempts (math.ts attempt, attemptFailed and engineSettled: KaTeX is an on-demand chunk since iOS item 6,
// 2026-10-02), executed in node over math.ts's own source. Each case bundles math.ts from the tree under test and runs it in a fresh
// vm context over a stand-in document, so the module's load state starts idle every time: the page's bundle tag the chunk's URL is
// derived from, a head the script tags are appended to (each tag's onload and onerror fired by hand), a window that records its
// listeners, a timer table the backstop is armed in (fired by hand), and a console whose lines are kept. The fill runs over small
// stand-in turns holding one placeholder each. What it holds:
//   - an attempt that fails after another attempt has succeeded says nothing (attemptFailed's stale-failure guard; the review of
//     iOS item 6, round 2, tests-1): the first attempt stalls past its backstop (one console line, the retry armed), the next formula
//     uses the retry (a second tag), the first tag then loads (a late success, the arrival), and the second tag's error comes after
//     it. No browser in CI reaches that order (Chromium serves the retry's tag from the stalled fetch), so this case is the guard's pin.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import * as vm from "node:vm";
import { createRequire } from "node:module";
import { hideEdges } from "../test-dom-shim";

const EXT = process.cwd();                                               // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const requireCjs = createRequire(path.join(EXT, "package.json"));

let built: string | null = null;
/** math.ts from the tree under test, bundled as one script that leaves its exports on `M`. */
function mathSource(): string {
  if (built) return built;
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: 'export * from "./math";', resolveDir: UI, loader: "ts", sourcefile: "math-attempt-probe.ts" },
    bundle: true, write: false, format: "iife", globalName: "M", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  built = r.outputFiles[0].text as string;
  return built;
}

/** A stand-in element: a tag, classes, attributes, children and a parent, and the few calls the fill and the attempt make on one. A
 *  script tag also carries src, nonce, onload and onerror. The edges hide (ui/test-dom-shim.ts), so a failing assertion dumps the
 *  element's own primitives, never the tree. */
type Fake = {
  tagName: string; className: string; text: string; src: string; nonce: string; parentNode: Fake | null; kids: Fake[];
  attrs: Map<string, string>; ownerDocument: unknown; onload: (() => void) | null; onerror: (() => void) | null;
  classList: { contains(c: string): boolean };
  textContent: string; readonly childNodes: Fake[];
  getAttribute(n: string): string | null; setAttribute(n: string, v: string): void; hasAttribute(n: string): boolean;
  appendChild(c: Fake): Fake; replaceWith(...nodes: Fake[]): void;
  querySelectorAll(sel: string): Fake[]; querySelector(sel: string): Fake | null; closest(sel: string): Fake | null;
};
function matches(n: Fake, sel: string): boolean {
  return sel.split(",").some((one) => {
    const m = /^\s*([a-z]*)(?:\.([\w-]+))?(?:\[([\w-]+)\])?\s*$/i.exec(one);
    if (!m) throw new Error("the stand-in reads no selector " + JSON.stringify(one));
    return (!m[1] || n.tagName === m[1].toUpperCase()) && (!m[2] || n.classList.contains(m[2])) && (!m[3] || n.hasAttribute(m[3]));
  });
}
function fake(doc: unknown, tag: string): Fake {
  const n: Fake = {
    tagName: tag.toUpperCase(), className: "", text: "", src: "", nonce: "", parentNode: null, kids: [] as Fake[], attrs: new Map(),
    ownerDocument: doc, onload: null, onerror: null,
    classList: { contains: (c: string) => n.className.split(/\s+/).includes(c) },
    get textContent(): string { return n.kids.length ? n.kids.map((k) => k.textContent).join("") : n.text; },
    set textContent(v: string) { n.kids = []; n.text = v; },
    get childNodes(): Fake[] { return n.kids.slice(); },
    getAttribute: (a) => (n.attrs.has(a) ? n.attrs.get(a)! : null),
    setAttribute: (a, v) => { n.attrs.set(a, String(v)); },
    hasAttribute: (a) => n.attrs.has(a),
    appendChild: (c) => { c.parentNode = n; n.kids.push(c); return c; },
    replaceWith: (...nodes) => {
      const p = n.parentNode;
      if (!p) return;
      const i = p.kids.indexOf(n);
      for (const x of nodes) x.parentNode = p;
      p.kids.splice(i, 1, ...nodes);
      n.parentNode = null;
    },
    querySelectorAll: (sel) => { const out: Fake[] = []; const walk = (x: Fake) => { for (const k of x.kids) { if (matches(k, sel)) out.push(k); walk(k); } }; walk(n); return out; },
    querySelector: (sel) => n.querySelectorAll(sel)[0] || null,
    closest: (sel) => { for (let x: Fake | null = n; x; x = x.parentNode) if (matches(x, sel)) return x; return null; },
  };
  return hideEdges(n);
}

type Harness = {
  M: any; doc: any; win: { listeners: Map<string, Array<(e: unknown) => void>>; dispatch(type: string): void };
  head: Fake; body: Fake; lines: string[]; timers: Map<number, () => void>;
  tags(): Fake[]; turn(tex: string, display?: boolean): Fake; engineIn(): void; flush(): Promise<void>;
};
/** A fresh page: math.ts loaded in its own context, nothing requested yet. */
function page(): Harness {
  const doc: any = { readyState: "complete", currentScript: null };
  const root = fake(doc, "html"), head = fake(doc, "head"), body = fake(doc, "body");
  root.appendChild(head); root.appendChild(body);
  const bundle = fake(doc, "script");
  bundle.src = "http://romp.test/dist/render.js?v=7";             // the page's bundle tag, as the kernel's chat page carries it
  bundle.setAttribute("src", bundle.src);
  head.appendChild(bundle);
  Object.assign(doc, { head, body, documentElement: root, createElement: (tag: string) => fake(doc, tag),
    querySelectorAll: (sel: string) => root.querySelectorAll(sel), querySelector: (sel: string) => root.querySelector(sel) });
  const listeners = new Map<string, Array<(e: unknown) => void>>();
  const win = {
    listeners,
    addEventListener: (type: string, fn: (e: unknown) => void) => { listeners.set(type, (listeners.get(type) || []).concat(fn)); },
    removeEventListener: (type: string, fn: (e: unknown) => void) => { listeners.set(type, (listeners.get(type) || []).filter((f) => f !== fn)); },
    dispatch: (type: string) => { for (const f of listeners.get(type) || []) f({ type }); },
  };
  const lines: string[] = [];
  const timers = new Map<number, () => void>();
  let tid = 0;
  const say = (...a: unknown[]) => { lines.push(a.map((x) => String(x)).join(" ")); };
  const sandbox: any = {
    document: doc, window: win, queueMicrotask, console: { error: say, warn: say, log: say, info: say },
    setTimeout: (fn: () => void) => { const id = ++tid; timers.set(id, fn); return id; },
    clearTimeout: (id: number) => { timers.delete(id); },
  };
  vm.createContext(sandbox);
  vm.runInContext(mathSource(), sandbox);
  const M = sandbox.M;
  assert.ok(M && typeof M.renderMathPlaceholders === "function", "math.ts's exports reached the context");
  return {
    M, doc, win, head, body, lines, timers,
    tags: () => head.kids.filter((k) => k.tagName === "SCRIPT" && k !== bundle),
    turn: (tex: string, display = false) => {
      const t = fake(doc, "div");
      const ph = fake(doc, display ? "div" : "span");
      ph.className = display ? M.MATH_DISPLAY_CLASS : M.MATH_INLINE_CLASS;
      ph.textContent = tex;
      t.appendChild(ph);
      body.appendChild(t);
      M.renderMathPlaceholders(t);
      return t;
    },
    // the chunk has run: KaTeX registered under the global math.ts reads (its render writes a stand-in layout into the placeholder)
    engineIn: () => { sandbox.__rompKatex = { render: (tex: string, el: Fake) => { const k = fake(doc, "span"); k.className = "katex"; k.textContent = tex; el.appendChild(k); }, ParseError: class extends Error {} }; },
    flush: async () => { for (let i = 0; i < 5; i++) await new Promise<void>((r) => setImmediate(r)); },
  };
}
/** Fire the one backstop armed now (the attempt's), as its 60 s running out. */
function backstopRunsOut(h: Harness): void {
  assert.equal(h.timers.size, 1, "one timer armed: the attempt's backstop");
  const [[id, fn]] = Array.from(h.timers.entries());
  h.timers.delete(id);
  fn();
}

test("executed: an attempt that fails after another attempt has succeeded says nothing: the first tag loads after its backstop, the retry's tag errors after that, and the console keeps the backstop's one line (attemptFailed's stale-failure guard)", async () => {
  const h = page();
  const t1 = h.turn("x^2");
  assert.equal(h.tags().length, 1, "the first formula asked for the chunk: one script tag");
  assert.equal(h.tags()[0].src, "http://romp.test/dist/math-chunk.js?v=7", "beside the bundle, with its token");
  assert.equal(t1.querySelectorAll("." + h.M.MATH_INLINE_CLASS).length, 1, "the formula waits");
  backstopRunsOut(h);
  assert.equal(h.lines.length, 1, "the backstop failed the first attempt: one console line");
  assert.match(h.lines[0], /^math: the math renderer did not load within 60 seconds; formulas are shown as their TeX source; the next formula asks for the renderer again$/);
  assert.equal(t1.querySelectorAll("[" + h.M.MATH_FAILED_ATTR + "]").length, 1, "the waiting formula became its marked source");
  const t2 = h.turn("y^2");
  assert.equal(h.tags().length, 2, "the next formula used the retry the failure armed: a second tag");
  assert.equal(t2.querySelectorAll("[" + h.M.MATH_FAILED_ATTR + "]").length, 1, "nothing waits on the retry: the formula is its marked source at once");
  const [first, second] = h.tags();
  h.engineIn();
  first.onload!();                                                       // the stalled first chunk lands after its backstop: a success
  await h.flush();
  assert.equal(t1.querySelectorAll(".katex").length + t2.querySelectorAll(".katex").length, 2, "the late success laid out both formulas, the failure's fallbacks included");
  second.onerror!();                                                     // and the retry's own tag errors after that success
  await h.flush();
  assert.deepEqual(h.lines.slice(1), [], "the retry's failure, after a success, says nothing: no second console line");
  assert.equal(t1.querySelectorAll(".katex").length + t2.querySelectorAll(".katex").length, 2, "and it unlays nothing");
});
