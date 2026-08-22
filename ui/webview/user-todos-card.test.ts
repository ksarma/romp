// The split to-do card (plans/user-todos.md, slice 1): the agent's plan (the existing checklist)
// and "Waiting on you" (open user todos — needs the agent flagged for the person it works for)
// share ONE transcript-bottom card, each section auto-hiding when empty, so today's behavior is
// unchanged when no todos exist. Per-row Reply (injects the user's answer, anchored) and Dismiss
// (clears without one). Source pins — render.ts has no jsdom harness.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the todo ChatEvent and the session payload both carry the user todos", () => {
  // the rows ride ON the event (the chatTail delta re-sends changed events only) AND on the
  // session as the merge seam the plan names
  assert.match(RENDER, /kind: "todo"; tasks: TodoTask\[\]; userTodos\?: UserTodo\[\]; error\?: string/);
  assert.match(RENDER, /interface UserTodo \{ id: string; text: string; detail\?: string; createdT\?: number \}/);
  assert.match(RENDER, /userTodos\?: UserTodo\[\];/);
});

test("the session field merges through the upsert's prev-fallback (the bg-tasks payload idiom)", () => {
  assert.match(RENDER, /userTodos: \("userTodos" in msg\) \? msg\.userTodos : \(prev \? prev\.userTodos : undefined\)/);
});

test("the kernel ships only fixed store values on the field — never a per-build value", () => {
  // _send_client dedups by the serialized payload (the firstSeen lesson): a value that ticks
  // with the clock would re-send the full chat to every client about once a second
  assert.match(KERNEL, /"userTodos": _user_todos_open/);
  const helper = (KERNEL.match(/def _open_user_todos\(sid\):[\s\S]*?\n\n/) || [""])[0];
  assert.ok(helper.length > 0, "_open_user_todos exists");
  assert.doesNotMatch(helper, /time\.time\(\)/, "no build-time clock reaches the payload");
});

test("both sections auto-hide when empty", () => {
  const body = RENDER.slice(RENDER.indexOf("function renderTodo"));
  assert.match(body, /else if \(ev\.tasks\.length\) \{/); // the agent's plan renders only with tasks
  assert.match(body, /if \(uts\.length\) \{/);            // waiting-on-you renders only with open todos
});

test("a task-store error still shows the waiting-on-you section (no early return)", () => {
  const start = RENDER.indexOf("function renderTodo");
  const body = RENDER.slice(start, RENDER.indexOf("\nfunction ", start + 10));
  const returns = body.match(/return turn;/g) || [];
  assert.equal(returns.length, 1, "one exit: the error branch no longer returns before the todo section");
  assert.ok(body.indexOf("if (ev.error)") < body.indexOf("Waiting on you"),
    "the error section precedes the waiting-on-you section");
});

test("reply and dismiss are delegated to the stable root, never per-render listeners", () => {
  // the card rebuilds on every push; a per-render listener eats a mid-press click (ui/CLAUDE.md)
  assert.match(RENDER, /reply\.dataset\.act = "utreply"/);
  assert.match(RENDER, /dis\.dataset\.act = "utdismiss"/);
  assert.match(RENDER, /utreply: \(elx\) => \{/);
  assert.match(RENDER, /utdismiss: \(elx\) => \{/);
});

test("dismiss arms then confirms in place, posts the op, and removes the row optimistically", () => {
  assert.match(RENDER, /if \(!elx\.classList\.contains\("armed"\)\) \{ elx\.classList\.add\("armed"\); elx\.textContent = "Really dismiss\?"; return; \}/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "userTodoDismiss", id: sid, todoId: tid \}\)/);
  assert.match(RENDER, /elx\.closest\("\.ut-item"\)\?\.remove\(\)/);
});

test("reply opens a modal (outside the rebuilt transcript) and posts one answer+stamp op", () => {
  // one kernel op both injects the reply AND stamps the todo answered — never sendMessage plus a
  // separate stamp; and a modal, not an inline box, because the card rebuilds every push
  assert.match(RENDER, /function showUserTodoReply\(sid: string, todoId: string, todoText: string\)/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "userTodoAnswer", id: sid, todoId, text \}\)/);
});

test("detail hides behind a keyed fold that survives re-renders (progressive disclosure)", () => {
  assert.match(RENDER, /const utDetailOpen = new Set<string>\(\)/);
  assert.match(RENDER, /uttoggle: \(elx\) => \{/);
});

test("the waiting-on-you styles reuse the todo card vocabulary", () => {
  assert.match(CSS, /\.ut-head \{/);
  assert.match(CSS, /\.ut-item \{/);
  assert.match(CSS, /\.ut-detail \{ display: none;/);
  assert.match(CSS, /\.ut-detail\.open \{ display: block; \}/);
  assert.match(CSS, /\.ut-dismiss\.armed \{ border-color: var\(--err\); color: var\(--err\); \}/);
});
