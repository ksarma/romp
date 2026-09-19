// The request flag on a chat tab (plans/user-todos.md, the ambient surfaces): a session with an open request for you
// wears a small flag after its name. It is a WIDGET of tab-widgets.ts (registered, switched, demoed and ordered with the
// dot, the context bar and the hot key), reading the status row's `openRequests` (build_session's and _light_status's,
// so a skeleton tab, which gets only status frames, wears it too), and the strip's signature reads that count on a loaded
// tab and on a skeleton alike, so a request registered or closed repaints the strip. Source pins on render.ts and
// styles.css (the strip has no DOM harness), the widget executed on the tiny DOM tab-widgets.test.ts uses. The phone's
// mirror of the flag is the kernel's inline script and is tested in the Python lane (tests/test_kernel_mobile.py).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { WidgetStatus } from "./tab-widgets";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(WEBVIEW, "render.ts"), "utf8");
const CSS = fs.readFileSync(path.join(WEBVIEW, "styles.css"), "utf8");
const TW = fs.readFileSync(path.join(WEBVIEW, "tab-widgets.ts"), "utf8");

type El = { tag: string; className: string; textContent: string; title: string; attrs: Record<string, string>; children: El[];
            appendChild: (c: El) => El; setAttribute: (k: string, v: string) => void };
function mkEl(tag: string): El {
  const e: El = { tag, className: "", textContent: "", title: "", attrs: {}, children: [],
    appendChild: (c) => { e.children.push(c); return c; }, setAttribute: (k, v) => { e.attrs[k] = v; } };
  return e;
}
(globalThis as any).document = { createElement: mkEl };
(globalThis as any).localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
(globalThis as any).navigator = { platform: "Linux x86_64" };
// eslint-disable-next-line @typescript-eslint/no-var-requires
const W = require("./tab-widgets") as typeof import("./tab-widgets");
const classes = (e: El) => e.className.split(/\s+/).filter(Boolean);
const after = (status: WidgetStatus) => { const tab = mkEl("div"); W.composeTabWidgets(tab as unknown as HTMLElement, "after", "s", status, { on: {}, order: [], opts: {} }); return tab.children; };

test("the widget is the ONLY renderer of the flag: render.ts mints no .tab-usertodo of its own and reads no rows for it", () => {
  assert.ok(TW.includes('el("span", "tab-usertodo")'), "the widget mints the element");
  assert.ok(!RENDER.includes('"tab-usertodo"'), "render.ts has no inline element: the flag is a widget in the registry, switched and ordered like the rest");
  assert.ok(!/s\.userTodos\?\.length|s\.userTodos && s\.userTodos\.length/.test(RENDER), "the strip reads the status's count, not the session payload's rows");
});

test("the status row carries the count, and the strip's signature reads it on a loaded tab and on a skeleton", () => {
  const status = RENDER.slice(RENDER.indexOf("interface Status {"), RENDER.indexOf("\n", RENDER.indexOf("interface Status {")));
  assert.match(status, /openRequests\?: number \| null;/, "beside needsYou: the open request count off the status row");
  assert.match(TW, /export interface WidgetStatus extends TabStateLike \{[^}]*openRequests\?: number \| null[^}]*\}/, "the widget's status shape names it");
  const fn = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
  const sig = fn.slice(fn.indexOf("const stripSig = JSON.stringify(["), fn.indexOf("const mslotEl = "));
  assert.ok(sig.includes("st.openRequests || 0"), "a loaded tab's count is a signature input");
  assert.ok(sig.includes("kst?.openRequests || 0"), "a skeleton's status frame's count too: a request registered or closed repaints either");
});

test("the flag is themed through --dim like the tab's close glyph, never a hardcoded white, and is never a dot variant", () => {
  const rule = /^\.tab-usertodo \{([^}]*)\}/m.exec(CSS);
  assert.ok(rule, "one .tab-usertodo rule in the strip's sheet");
  assert.match(rule![1], /color: var\(--dim\)/);
  assert.doesNotMatch(rule![1], /rgba\(255, 255, 255/, "a white alpha vanishes under body.theme-light (classic tabs have no chip fill)");
  assert.ok(!CSS.includes(".tab-dot.usertodo"), "pips encode turn state; the phone's picker scrapes them by class");
  assert.ok(CSS.indexOf(".tab-usertodo {") > CSS.indexOf(".tab-dot.opening {") && CSS.indexOf(".tab-usertodo {") < CSS.indexOf(".tab-key {"), "beside the other title marks");
});

test("executed: one open request paints the flag with the request vocabulary; none paints nothing; a closed tab paints nothing", () => {
  const one = after({ state: "working", openRequests: 1 }).filter((c) => classes(c).includes("tab-usertodo"));
  assert.equal(one.length, 1);
  assert.equal(one[0].textContent, "⚑");
  assert.match(one[0].title, /request/);
  assert.doesNotMatch(one[0].title, /todo|waiting on you|\u2014/i);
  assert.equal(one[0].attrs["aria-label"], one[0].title, "the title doubles as the accessible name");
  assert.equal(after({ state: "working", openRequests: 0 }).filter((c) => classes(c).includes("tab-usertodo")).length, 0);
  assert.equal(after({ state: "closed", openRequests: 2 }).filter((c) => classes(c).includes("tab-usertodo")).length, 0);
  assert.equal(after({ state: "ready", openRequests: 4 })[0].textContent, "⚑", "no count on a tab");
});
