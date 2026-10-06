// A page reload keeps the chat reader's place (T265, the user 2026-09-08: the dashboard reloads itself on a kernel
// restart and on a newer served bundle, superseding their 2026-07-13 preference for a banner the reader clicks, so
// the reload must not cost the reader their scroll position or follow mode). The decisions are pure and execute
// here; render.ts has import-time DOM side effects, so its wiring — the synchronous persist hook the reload core
// calls, the pagehide belt, the load-time take, landActive's one-shot consume — is pinned to source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as ts from "typescript";
import { reloadScrollRecord, takeReloadScroll, reloadLandTarget } from "./reload-restore";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const SID = "11111111-2222-4333-8444-000000000201";

test("the record names the tab, the position, the follow mode and the anchor; no tab → nothing to keep", () => {
  assert.deepEqual(reloadScrollRecord(SID, 1234, false, { uuid: "u1", y: 40 }), { id: SID, top: 1234, stick: false, anchor: { uuid: "u1", y: 40 } });
  assert.deepEqual(reloadScrollRecord(SID, 1234, false, { uuid: "u1", y: 40, at: { block: 3, char: 17, y: -6 } }), { id: SID, top: 1234, stick: false, anchor: { uuid: "u1", y: 40, at: { block: 3, char: 17, y: -6 } } }, "the reader's line in the anchor turn rides with it");
  assert.deepEqual(reloadScrollRecord(SID, 5000, true, null), { id: SID, top: 5000, stick: true, anchor: null });
  assert.equal(reloadScrollRecord(null, 10, false, null), null);
  assert.equal(reloadScrollRecord("", 10, false, null), null);
});

test("the record applies to the tab it was saved for, once; another tab or a malformed record gets nothing", () => {
  const rec = reloadScrollRecord(SID, 1234, false, null);
  assert.equal(takeReloadScroll(rec, SID), rec);
  assert.equal(takeReloadScroll(rec, "11111111-2222-4333-8444-000000000202"), null, "a different tab lands by the ordinary rule");
  assert.equal(takeReloadScroll(rec, null), null);
  assert.equal(takeReloadScroll(null, SID), null);
  assert.equal(takeReloadScroll({ id: SID }, SID), null, "no position → no restore");
  assert.equal(takeReloadScroll("junk", SID), null);
});

test("where the restored land goes: bottom for follow mode, the anchor when honoured, else the raw top", () => {
  assert.equal(reloadLandTarget({ id: SID, top: 999, stick: true, anchor: { uuid: "u", y: 0 } }, true), "bottom");
  assert.equal(reloadLandTarget({ id: SID, top: 999, stick: false, anchor: { uuid: "u", y: 0 } }, true), "anchor");
  assert.equal(reloadLandTarget({ id: SID, top: 999, stick: false, anchor: { uuid: "u", y: 0 } }, false), 999, "the anchor turn is not in the rebuilt DOM: raw scrollTop");
  assert.equal(reloadLandTarget({ id: SID, top: 999, stick: false, anchor: null }, false), 999);
});

test("render.ts persists SYNCHRONOUSLY for the reload core and on pagehide, into THIS tab's sessionStorage", () => {
  assert.match(RENDER, /import \{ reloadScrollRecord, takeReloadScroll, type ReloadScroll \} from "\.\/reload-restore";/);
  // the core's hook writes the scroll record and then the notices on screen (reload-notices.test.ts pins that half);
  // pagehide writes the scroll record alone
  assert.match(RENDER, /^function persistForReload\(\): void \{ persistScrollForReload\(\); persistNoticesForReload\(\); \}/m);
  assert.match(RENDER, /\(window as any\)\.__rompPersistForReload = persistForReload;/);
  assert.match(RENDER, /window\.addEventListener\("pagehide", persistScrollForReload\);/);
  const m = RENDER.match(/^function persistScrollForReload\(\): void \{([\s\S]*?)\n\}/m);
  assert.ok(m, "persistScrollForReload");
  const body = m![1];
  assert.match(body, /const stick = content\.scrollHeight - content\.scrollTop - content\.clientHeight <= 2;/, "follow mode is the true bottom");
  assert.match(body, /reloadScrollRecord\(activeId, content\.scrollTop, stick, stick \? null : captureReadingAnchor\(content, v\)\)/, "the anchor turn and the reader's line in it (reading-point.ts): a turn with formulas lays out shorter on the fresh page while they wait for the math renderer, so its top alone lands the line off; tests/test_math_chunk_served.py executes the landing");
  assert.match(body, /sessionStorage\.setItem\(RELOAD_SCROLL_KEY, JSON\.stringify\(rec\)\)/, "per tab: the persisted webview state is localStorage on the served page, shared by every dashboard tab");
  assert.match(RENDER, /const RELOAD_SCROLL_KEY = "romp:reloadScroll";/);
  // nothing to keep for a hidden pane or a tab never shown
  assert.match(body, /if \(!content \|\| !v \|\| !v\.shown \|\| content\.clientHeight <= 0\) return;/);
});

test("render.ts takes the record out of sessionStorage at load (one reload, one restore)", () => {
  assert.match(RENDER, /let pendingReloadScroll: ReloadScroll \| null = \(\(\) => \{[\s\S]*?const raw = sessionStorage\.getItem\(RELOAD_SCROLL_KEY\);\s*\n\s*if \(raw\) sessionStorage\.removeItem\(RELOAD_SCROLL_KEY\);/);
});

test("landActive's landing consumes the record for the active tab first, then falls to the ordinary rule", () => {
  const m = RENDER.match(/^function landActive\(content: HTMLElement \| null, v: View, scrollerHolds: boolean = false\): void \{([\s\S]*?)\n\}/m);
  assert.ok(m, "landActive");
  const body = m![1];
  assert.match(body, /const rs = takeReloadScroll\(pendingReloadScroll, activeId\);\s*\n\s*if \(rs\) \{\s*\n\s*pendingReloadScroll = null;\s*\n\s*v\.stick = rs\.stick;\s*\n\s*if \(rs\.stick\) writeScroll\(content, content\.scrollHeight, "reload-restore", true\);\s*\n\s*else if \(!\(rs\.anchor && \(restoreReadingLine\(content, v, rs\.anchor\) \|\| restoreScrollAnchor\(content, v, rs\.anchor\)\)\)\) \{/, "the reader's line first, the turn when the fresh turn lacks the line (land-active-keep.test.ts executes both roads; tests/test_math_chunk_served.py the landing over waiting formulas)");
  // the anchor turn outside the fresh window: the raw top is the first guess and the deep-link land finishes it
  assert.match(body, /writeScroll\(content, rs\.top, "reload-restore"\);\s*\n\s*if \(rs\.anchor\) \{\s*\n\s*pendingAnchor = rs\.anchor\.uuid; pendingAnchorKeepY = rs\.anchor\.y; pendingAnchorKeepAt = rs\.anchor\.at \?\? null;/, "the raw top first, then the deep-link land is armed with the row's offset and the reader's line in it (the keep-offset landing writes by the line: scroll-to-anchor-roads.test.ts executes it, land-active-keep.test.ts the arm, tests/test_math_chunk_served.py the landing in a long transcript)");
  // …and RUN in the same pass (T374): the pass already made its own attempt before the restore armed anything, and an idle
  // session sends no frame for another; a row outside the fresh window asks its window here and stays armed for the reply
  assert.match(body, /landTrail = \[\];\s*\n\s*const landedNow = scrollToAnchor\(rs\.anchor\.uuid\);\s*\n\s*if \(landedNow \|\| !anchorPendingOlder\) \{ pendingAnchor = null; pendingAnchorKeepY = null; pendingAnchorKeepAt = null; \}/, "landed or asked at once; the arm is kept only for a window in flight");
  // the ordinary rule: the bottom, else the saved place (the row the saved place held, put back over the spacers an armed land's take
  // re-sized, PR E, the maintainer's round 2 ruling; the raw scrollTop when that restore has no row to put back, nothing armed, no row at
  // the saved place or the row gone with the attempt's window build, with the take given back first on the two roads after one, the
  // maintainer's round 3 ruling B: land-active-keep.test.ts executes the roads)
  assert.match(body, /else if \(!v\.shown \|\| v\.stick\) writeScroll\(content, content\.scrollHeight, "land-bottom", true\);\s*\n(?:\s*\/\/[^\n]*\n)*\s*else if \(!\(held && restoreScrollAnchor\(content, v, held\)\) && !\(moved && \(restoreReadingLine\(content, v, moved\) \|\| restoreScrollAnchor\(content, v, moved\)\)\)\) \{ untakeMeasure\(v, figures\); writeScroll\(content, v\.scrollTop, "land-saved"\); \}/);
});

test("every write of the keep offset writes the reader's line beside it, in the statement next to it (pendingAnchorKeepAt's declaration: set with pendingAnchorKeepY, cleared wherever it is cleared)", () => {
  // the census reads render.ts with the TypeScript compiler's parser (writer-census.ts's precedent), so every assignment operator
  // (`=`, `??=`, `||=`, `&&=`, the arithmetic ones), `++`/`--`, a destructuring target and a for-of/for-in target count as writes of
  // pendingAnchorKeepY wherever they sit, and a comment or a string spelling the line's assignment counts as nothing. Each write must
  // be a plain statement of a statement list (a block, a case, the module), not one arm of an if or a branch of an expression, and the
  // statement beside it in that list (or the same statement, through a comma) must write pendingAnchorKeepAt, so the two always run
  // together. What it guards is the declaration's rule: a line left from an earlier keep is never READ while the offset is null
  // (scrollToAnchor reads it only under a non-null offset, and every write of a non-null offset writes the line too, which this census
  // also holds), so a miss is a broken invariant, not a misplaced reader; the line's landing itself executes in
  // scroll-to-anchor-roads.test.ts and land-active-keep.test.ts
  const sf = ts.createSourceFile("render.ts", RENDER, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const bare = (e: ts.Node): ts.Node => { let x = e; while (ts.isParenthesizedExpression(x) || ts.isAsExpression(x) || ts.isNonNullExpression(x) || ts.isTypeAssertionExpression(x) || ts.isSatisfiesExpression(x)) x = x.expression; return x; };
  /** Whether an assignment target writes `name`: the name itself, or a destructuring pattern naming it anywhere (a key or a default
   *  named so counts too: the safe side). */
  const holds = (e: ts.Node, name: string): boolean => {
    const x = bare(e);
    if (ts.isIdentifier(x)) return x.text === name;
    if (!ts.isObjectLiteralExpression(x) && !ts.isArrayLiteralExpression(x)) return false;
    let hit = false;
    const walk = (n: ts.Node): void => { if (ts.isIdentifier(n) && n.text === name) hit = true; ts.forEachChild(n, walk); };
    walk(x);
    return hit;
  };
  const writes = (n: ts.Node, name: string): boolean =>
    (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && holds(n.left, name))
    || ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && holds(n.operand, name))
    || ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer) && holds(n.initializer, name));
  /** The plain statement a write runs as: up through parentheses and commas to an expression statement whose parent is a statement
   *  list; null for a write under anything else (an if's arm, a ternary, a short circuit, a call's argument, a loop head). */
  const LIST = (p: ts.Node): boolean => ts.isBlock(p) || ts.isSourceFile(p) || ts.isCaseClause(p) || ts.isDefaultClause(p) || ts.isModuleBlock(p);
  const plain = (n: ts.Node): ts.ExpressionStatement | null => {
    let x: ts.Node = n;
    while (x.parent && (ts.isParenthesizedExpression(x.parent) || (ts.isBinaryExpression(x.parent) && x.parent.operatorToken.kind === ts.SyntaxKind.CommaToken))) x = x.parent;
    return x.parent && ts.isExpressionStatement(x.parent) && LIST(x.parent.parent) ? x.parent : null;
  };
  const keepY: ts.Node[] = [];
  const keepAt: ts.Node[] = [];
  const visit = (n: ts.Node): void => { if (writes(n, "pendingAnchorKeepY")) keepY.push(n); if (writes(n, "pendingAnchorKeepAt")) keepAt.push(n); ts.forEachChild(n, visit); };
  visit(sf);
  const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const shown = (n: ts.Node): string => `render.ts:${lineOf(n)}: ${n.getText(sf).replace(/\s+/g, " ").slice(0, 160)}`;
  assert.ok(keepY.length >= 10, `the census finds the writes it is about (found ${keepY.length}): the reload restore's arm and its release, keepPlaceAcrossWindow's arm and its release, chatHead's re-arm, scrollToAnchor's consume, the pass's clear, cancelLanding's reset and chatWindow's two re-arms`);
  const lineStmts = keepAt.map(plain).filter((s): s is ts.ExpressionStatement => s !== null);
  const unpaired = keepY.filter((w) => {
    const s = plain(w);
    if (!s) return true;
    const list = (s.parent as ts.Block).statements;
    const i = list.indexOf(s);
    return !lineStmts.some((t) => t === s || (t.parent === s.parent && Math.abs(list.indexOf(t) - i) === 1));
  }).map(shown);
  assert.deepEqual(unpaired, [], "a write of pendingAnchorKeepY that is not a plain statement with a write of pendingAnchorKeepAt beside it");
});
