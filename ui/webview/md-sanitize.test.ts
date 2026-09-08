// The shared markdown sanitizer's pure parts, in node (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does).
// DOMPurify itself needs a window, so the sanitize call and the DOM post-passes are proven over the real files
// bundle in headless Chromium by md-sanitize-browser.test.ts. Here: the colour grammar behind decision 6 (the user
// 2026-09-07: colour and background-colour survive, nothing else does), the profile's forbidden tags, the hook body,
// the hook guard, and the source pins that make md-sanitize.ts the ONE sanitizer the dashboard has.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { MD_FORBID_TAGS, MD_FORBID_ATTR, MD_PURIFY, colourOnlyStyle, isLiteralColour, styleAttributeHook, installMdSanitizeHooks } from "./md-sanitize";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");

// ── the colour grammar ──────────────────────────────────────────────────────────────────────────────

test("a literal colour: a keyword, #hex of 3 to 8 digits, or rgb/rgba/hsl/hsla over plain numeric arguments", () => {
  for (const v of ["red", "Red", "transparent", "currentcolor", "inherit", "#abc", "#abcd", "#aabbcc", "#AABBCCDD",
                   "rgb(200, 0, 0)", "rgb(200 0 0)", "rgb(200 0 0 / 50%)", "rgba(1,2,3,.5)", "rgba(1, 2, 3, 0.5)",
                   "hsl(120, 50%, 50%)", "hsl(120deg 50% 50%)", "hsla(120 50% 50% / 0.4)", "hsl(none 50% 50%)", "rgb(+10 -0 0.5)"]) {
    assert.ok(isLiteralColour(v), "accepted: " + v);
  }
});

test("not a literal colour: functions other than the four, nested parentheses, escapes, quotes, !important, wrong arity", () => {
  for (const v of ["url(x)", "url(javascript:alert(1))", "var(--x)", "expression(alert(1))", "calc(1px)", "rgb(var(--x))",
                   "rgb(1,2)", "rgb(1,2,3,4,5)", "rgb()", "red !important", "red\"", "'red'", "#ab", "#abcdefabc", "#ggg",
                   "rgb(1,2,3)) ;", "red;color:blue", "rgb(1,2,3/**/)", "r\\65d", "rgb(1 2 3) x", "rgb(1px 2 3)", "red blue", "", " "]) {
    assert.ok(!isLiteralColour(v), "rejected: " + JSON.stringify(v));
  }
});

test("colourOnlyStyle keeps color and background-color with literal values, in order, and nothing else", () => {
  assert.equal(colourOnlyStyle("color: rgb(200, 0, 0); font-size: 80px"), "color: rgb(200, 0, 0)");
  assert.equal(colourOnlyStyle("position:fixed;inset:0;background:red"), "", "`background` is not `background-color`: the shorthand takes images and positions");
  assert.equal(colourOnlyStyle("COLOR: Red; Background-Color: #abc"), "color: Red; background-color: #abc", "property names case-folded, values as written");
  assert.equal(colourOnlyStyle("color: red !important"), "");
  assert.equal(colourOnlyStyle("color: url(javascript:alert(1))"), "");
  assert.equal(colourOnlyStyle("color: red; color: blue"), "color: red; color: blue", "a repeated property is two valid declarations");
  assert.equal(colourOnlyStyle("color"), "");
  assert.equal(colourOnlyStyle("color:"), "");
  assert.equal(colourOnlyStyle(""), "");
  assert.equal(colourOnlyStyle("background-color: rgb(0 0 0 / 50%)"), "background-color: rgb(0 0 0 / 50%)");
  assert.equal(colourOnlyStyle("color: red; background: url(x); background-color: var(--y); display: none"), "color: red");
  assert.equal(colourOnlyStyle("color: red; }; .fileview { display: none"), "color: red", "a declaration that tries to close the block is just an invalid declaration");
  assert.equal(colourOnlyStyle("color: rgb(1,2,3); font-family: x; color: hsl(1 2% 3%)"), "color: rgb(1,2,3); color: hsl(1 2% 3%)");
});

// ── the hook ────────────────────────────────────────────────────────────────────────────────────────

test("the style hook rewrites a style attribute to its colours, drops it when none remain, and leaves other attributes to DOMPurify", () => {
  const kept = { attrName: "style", attrValue: "color: red; position: fixed; inset: 0", keepAttr: true };
  styleAttributeHook(kept);
  assert.deepEqual(kept, { attrName: "style", attrValue: "color: red", keepAttr: true });
  const dropped = { attrName: "style", attrValue: "position:fixed;inset:0;background:red", keepAttr: true };
  styleAttributeHook(dropped);
  assert.equal(dropped.keepAttr, false, "nothing survived: the attribute goes");
  const other = { attrName: "href", attrValue: "position:fixed", keepAttr: true };
  styleAttributeHook(other);
  assert.deepEqual(other, { attrName: "href", attrValue: "position:fixed", keepAttr: true }, "not a style attribute: untouched (DOMPurify's own URI rules apply)");
  const upper = { attrName: "style", attrValue: "COLOR: #fff", keepAttr: true };
  styleAttributeHook(upper);
  assert.equal(upper.attrValue, "color: #fff");
});

test("installMdSanitizeHooks registers ONE uponSanitizeAttribute hook however often it is called, and that hook is the style rewrite", () => {
  const calls: { name: string; fn: Function }[] = [];
  const fake = { addHook: (name: string, fn: Function) => { calls.push({ name, fn }); } } as unknown as Parameters<typeof installMdSanitizeHooks>[0];
  installMdSanitizeHooks(fake);
  installMdSanitizeHooks(fake);
  installMdSanitizeHooks(fake);
  assert.equal(calls.length, 1, "idempotent: a second registration would run the rewrite twice per attribute");
  assert.equal(calls[0].name, "uponSanitizeAttribute");
  const ev = { attrName: "style", attrValue: "font-size: 80px; color: rgb(200, 0, 0)", keepAttr: true, allowedAttributes: {}, forceKeepAttr: undefined };
  calls[0].fn.call(fake, {} as Element, ev, {});
  assert.equal(ev.attrValue, "color: rgb(200, 0, 0)");
  assert.equal(ev.keepAttr, true);
});

// ── the profile ─────────────────────────────────────────────────────────────────────────────────────

test("the profile: html + svg, data: on img, no data-*, GitHub's forbidden tags, prefixed ids and names; input stays for the task checkbox", () => {
  assert.deepEqual(MD_PURIFY.USE_PROFILES, { html: true, svg: true });
  assert.deepEqual(MD_PURIFY.ADD_DATA_URI_TAGS, ["img"]);
  assert.equal(MD_PURIFY.ALLOW_DATA_ATTR, false);
  assert.equal(MD_PURIFY.SANITIZE_NAMED_PROPS, true, "GitHub's rule: an author's id and name are prefixed user-content-, never FORBID_ATTR (departure 2 in the plan's Slice 1 build note)");
  assert.deepEqual(MD_PURIFY.FORBID_TAGS, [...MD_FORBID_TAGS]);
  for (const tag of ["style", "dialog", "form", "button", "select", "option", "optgroup", "textarea", "fieldset", "legend", "label", "datalist", "output", "meter", "progress"]) {
    assert.ok(MD_FORBID_TAGS.includes(tag), tag + " is forbidden");
  }
  assert.ok(!MD_FORBID_TAGS.includes("input"), "input is allowed by the profile; sanitizeMd's post-pass keeps only a disabled checkbox");
  assert.ok(!MD_FORBID_TAGS.includes("details") && !MD_FORBID_TAGS.includes("summary"), "details/summary are prose structure GitHub keeps");
  assert.deepEqual(MD_PURIFY.FORBID_ATTR, [...MD_FORBID_ATTR]);
  assert.deepEqual([...MD_FORBID_ATTR], ["background"], "the one forbidden attribute: a background image fetches on render with no click and no gate; id/name are prefixed, style is filtered by the hook");
});

// ── source pins: one sanitizer ──────────────────────────────────────────────────────────────────────

test("md-sanitize.ts holds the dashboard's ONLY DOMPurify.sanitize call; render.ts and file-view.ts import sanitizeMd and no dompurify of their own", () => {
  const sources = fs.readdirSync(UI).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts") && !f.endsWith(".d.ts"));
  const callers = sources.filter((f) => /DOMPurify\.sanitize\(/.test(read(f)));
  assert.deepEqual(callers, ["md-sanitize.ts"], "every other module goes through sanitizeMd");
  const SAN = read("md-sanitize.ts");
  assert.equal((SAN.match(/DOMPurify\.sanitize\(/g) || []).length, 1);
  assert.match(SAN, /export function sanitizeMd\(dirty: string\): HTMLElement \{\n\s*installMdSanitizeHooks\(\);\n\s*const clean = DOMPurify\.sanitize\(dirty, \{ \.\.\.MD_PURIFY, RETURN_DOM: true \}\) as HTMLElement;/,
    "the hook is installed before the first sanitize, and the profile is spread with RETURN_DOM");
  assert.match(SAN, /keepOnlyInertCheckboxes\(clean\);\n\s*return clean;/, "the input post-pass runs on the sanitized DOM before it is handed back");
  const importers = sources.filter((f) => /from "dompurify"/.test(read(f)));
  assert.deepEqual(importers, ["md-sanitize.ts"]);
  assert.match(read("render.ts"), /import \{ sanitizeMd \} from "\.\/md-sanitize";/);
  assert.match(read("file-view.ts"), /import \{ sanitizeMd \} from "\.\/md-sanitize";/);
  assert.equal((read("render.ts").match(/sanitizeMd\(/g) || []).length, 2, "md() and userMd()");
  assert.equal((read("file-view.ts").match(/sanitizeMd\(/g) || []).length, 1, "mdBlock");
});

test("the submit backstop: one preventDefault listener on the viewer body in openFileView AND openUrlView, beside the click delegate", () => {
  const VIEW = read("file-view.ts");
  const local = VIEW.split("export function openFileView(")[1].split("\nexport function ")[0];
  const url = VIEW.split("export function openUrlView(")[1].split("\nexport function ")[0];
  for (const [name, fn] of [["openFileView", local], ["openUrlView", url]] as const) {
    assert.equal((fn.match(/body\.addEventListener\("submit", \(ev\) => \{ ev\.preventDefault\(\); \}\);/g) || []).length, 1, name + " installs the backstop once per open");
    assert.ok(fn.indexOf("delegate(body, {") < fn.indexOf('body.addEventListener("submit"'), name + ": beside the click delegate, on the same stable body");
    assert.ok(fn.indexOf('body.addEventListener("submit"') < fn.indexOf("body.replaceChildren("), name + ": installed before any render swaps the body's children");
  }
});

test("contain: layout on .fileview-md in BOTH sheets, byte-equal, and the md rule is in the parity list", () => {
  const rule = (css: string) => { const at = css.indexOf(".fileview-md {"); assert.ok(at >= 0); return css.slice(at, css.indexOf("}", at) + 1); };
  const chat = rule(read("styles.css")), feed = rule(read("feed.css"));
  assert.equal(chat, feed);
  assert.match(chat, /contain: layout;/);
  assert.doesNotMatch(chat, /contain: (paint|strict|content|size)/, "layout only: paint containment would clip the body's scroll and a table's own horizontal scroll");
  assert.match(read("fileview-parity.test.ts"), /"\.fileview-md \{"/);
});

test("the guide says what a note's own HTML may do, and SECURITY.md still names the sanitizer", () => {
  const guide = fs.readFileSync(path.resolve(UI, "..", "..", "docs", "guide.md"), "utf8");
  const files = guide.split("\n### Files\n")[1].split("\n## ")[0];
  assert.match(files, /\*\*A file's own HTML\.\*\*/);
  assert.match(files, /`<style>`/);
  assert.match(files, /user-content-/);
  assert.match(files, /`color` and `background-color`/);
  const security = fs.readFileSync(path.resolve(UI, "..", "..", "SECURITY.md"), "utf8");
  assert.match(security, /markdown through marked and\s+DOMPurify/);
});
