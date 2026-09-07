// FAIL LOUDLY, don't degrade silently (the user 2026-07-03): when the kernel can't read Claude's
// authoritative task store it surfaces an ERROR on the to-do card instead of quietly rendering a lossy
// transcript-folded list that could be wrong. Source pins (the render bundle isn't jsdom-exercised here).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("the todo ChatEvent carries an optional error", () => {
  assert.match(RENDER, /kind: "todo"; tasks: TodoTask\[\]; userTodos\?: UserTodo\[\]; error\?: string/);
});

test("renderTodo shows the surfaced error instead of the task list", () => {
  assert.match(RENDER, /if \(ev\.error\) \{/);
  assert.match(RENDER, /card\.classList\.add\("todo-card-error"\)/);
  assert.match(RENDER, /el\("div", "todo-error-msg"\)/);
  // and the task loop sits in the else-branch — per-task rendering is skipped when erroring.
  // (No early return, though: the waiting-on-you section below renders from a DIFFERENT store —
  // user todos — and must survive an unreadable task store; user-todos-card.test.ts pins that.)
  const body = RENDER.slice(RENDER.indexOf("function renderTodo"));
  const errIdx = body.indexOf("if (ev.error)");
  const loopIdx = body.indexOf("else if (ev.tasks.length)");
  assert.ok(errIdx > -1 && loopIdx > -1 && errIdx < loopIdx, "the error branch supplants the task list");
  // the row builder + completed-item fold (2026-08-24) live INSIDE that else-branch, so an erroring
  // store skips all the task machinery while the user-todos section below still renders
  const rowIdx = body.indexOf("const row = (t:");
  assert.ok(rowIdx > loopIdx, "the row machinery sits in the task branch, behind the error gate");
});

test("the error card is styled in the error color, not a normal card", () => {
  assert.match(CSS, /\.todo-card-error \{ border-color: var\(--err\); \}/);
  assert.match(CSS, /\.todo-error-msg \{ color: var\(--err\)/);
});
