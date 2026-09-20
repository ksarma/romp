// The Requests switch (plans/user-todos.md): requests from sessions are switchable, OFF by default, per
// install. Source pins, like the other webview tests (no jsdom harness):
//  - the GEAR row: a per-install kernel-side checkbox in the Sessions pane under a Requests section, honest
//    copy (what it turns on, off by default, this machine's own), stamped through the gesture clock under its
//    own store name like every kernel setting the gear emits, filled from /version, named in the stale-gesture
//    toast and re-issuable from it (STALE_TYPE), with a note about the surfaces that wait for task tracking,
//    un-hidden by dressTracking like the Automation rows' notes;
//  - PER-INSTALL: deliberately NOT in federation's KERNEL_SETTING set, so it never queues for or reaches another
//    machine's kernel (gear.test.ts's PER_INSTALL pin covers the class);
//  - the CLIENT needs no gate of its own: the kernel ships no rows while the switch is off, since the one gated
//    read is _open_user_todos, which the session field and the card's event derive from;
//  - every OFF surface refuses loudly: the kernel routes (409), the drive ops (a warn frame), the postal bus
//    (the pair leaves tools/list; a call anyway is refused).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const GEAR = read("ui", "webview", "gear.js");
const FED = read("ui", "webview", "federation.ts");
const KERNEL = read("kernel", "kernel.py");
const BUS = read("postal", "postal_service.py");

test("the gear has a Requests from sessions checkbox in the Sessions pane, gesture-stamped, filled from /version", () => {
  assert.ok(GEAR.includes("id=rs-usertodos"), "the checkbox exists in the gear markup");
  const at = GEAR.indexOf("id=rs-usertodos");
  const pane = GEAR.indexOf("data-pane=sessions"), next = GEAR.indexOf("data-pane=automation");
  assert.ok(pane > 0 && next > pane, "both panes exist (indexOf's -1 would pass the order check)");
  assert.ok(pane < at && at < next, "in the Sessions pane (a request is what a session asks of the user)");
  assert.ok(GEAR.indexOf("id=rs-backend") < GEAR.lastIndexOf("<div class='rs-sec'>Requests</div>", at)
    && GEAR.lastIndexOf("<div class='rs-sec'>Requests</div>", at) < at,
    "under its own Requests section head, after the New sessions rows");
  const row = GEAR.slice(at, at + 900);
  assert.match(row, /<b>Requests from sessions<\/b>/);
  assert.ok(/file a request with you/.test(row), "says what it turns on");
  assert.ok(/Waiting on you/.test(row) && /card at the bottom/.test(row), "and where it shows");
  assert.ok(/Off by default/.test(row), "says it is off by default");
  assert.ok(/This machine/.test(row) && /never sent to another/.test(row), "and that it is this machine's own");
  assert.ok(row.includes("id=rs-usertodos-tt hidden"), "the note about task tracking, hidden while tracking is on");
  assert.ok(/While task tracking is off/.test(row), "the note names what waits for tracking");
  assert.ok(!/todo/i.test(row.replace(/rs-usertodos(-tt)?/g, "")), "the row says request, never todo");
  assert.ok(GEAR.includes("post({ type: 'setUserTodos', enabled: utd.checked, gt: gclock.stamp('user-todos') })"),
    "the click posts the kernel's designed message, stamped through the gesture clock under its own store name");
  assert.ok(GEAR.includes("utd.checked = !!v.userTodos"),
    "the checkbox always shows the kernel's persisted answer, never a page default");
  assert.match(GEAR, /STALE_LABELS = \{[\s\S]*?'user-todos': 'Requests from sessions'/,
    "a stood-down gesture toasts under the row's own name");
  assert.match(GEAR, /STALE_TYPE = \{[\s\S]*?'user-todos': 'setUserTodos'/,
    "and the toast's Apply anyway may re-issue exactly this one setting");
  const dress = GEAR.slice(GEAR.indexOf("function dressTracking"), GEAR.indexOf("function tellShellTracking"));
  assert.match(dress, /getElementById\('rs-usertodos-tt'\)/, "dressTracking un-hides the note while tracking is off");
});

test("the switch is per-install: not a KERNEL_SETTING, so it never propagates", () => {
  const setSrc = FED.match(/const KERNEL_SETTING = new Set\(\[([\s\S]*?)\]\)/);
  assert.ok(setSrc, "federation.ts's KERNEL_SETTING set located");
  assert.ok(!setSrc![1].includes("setUserTodos"), "the set must not carry it: this kernel keeps its own copy");
  assert.ok(!FED.includes("setUserTodos"), "and no other federation path names it either");
  assert.ok(!KERNEL.includes('"userTodos", _set_user_todos'), "nor the /judge-settings propagation table on the kernel side");
  assert.ok(!/_pinned_stand_down\("user-todos"/.test(KERNEL), "a per-install store is never pinned");
  assert.ok(KERNEL.includes('msg.get("type") == "setUserTodos"'), "the kernel handles the op");
  assert.match(KERNEL, /"userTodos": _user_todos_on\(\)/, "/version carries it top-level");
  const settingsDict = KERNEL.slice(KERNEL.indexOf('"settings": {"autoNudge"'), KERNEL.indexOf('"settingsGt"'));
  assert.ok(!settingsDict.includes("userTodos"), "and not inside the mesh-compared settings dict");
});

test("the kernel ships no rows while the switch is off: the client needs no logic of its own", () => {
  const helper = KERNEL.slice(KERNEL.indexOf("def _open_user_todos(sid):"), KERNEL.indexOf("def _user_todo_session_ended"));
  assert.match(helper, /if not _user_todos_on\(\):\n        return \[\]/, "the one gated read");
  assert.match(KERNEL, /_user_todos_open = _open_user_todos\(sid\)/, "the session field and the card's event derive from it");
  assert.match(KERNEL, /USER_TODOS_SWITCH_FILE = "user-todos-enabled\.json"/);
  assert.ok(!/USER_TODOS_SWITCH_FILE = "user-todos\.json"/.test(KERNEL), "never the store's own file");
  const RENDER = read("ui", "webview", "render.ts");
  assert.ok(!/userTodos_on|_user_todos_on|userTodosEnabled|userTodosOn/.test(RENDER), "no switch logic in the renderer");
});

test("each OFF surface refuses loudly, never a silent no-op", () => {
  assert.match(KERNEL, /_USER_TODOS_OFF_ERR = "requests from sessions are turned off on this machine"/);
  // The switch's 409 for POST /usertodo and POST /usertodo/withdraw lives in the function each route hands its parsed
  // body to (_user_todo_register_route, _user_todo_withdraw_route: one answer shared with the Codex postal tools), not
  // in Handler.do_POST, so the pin follows each route block to its function by name and reads the 409 there. This is
  // a TEXT pin keyed on where the 409 lives: it guards against the handler losing the route to the function, not
  // against the 409 being right. The 409's correctness under the switch is proven by execution in
  // tests/test_user_todo_route_answers.py (the golden of the routes' HTTP answers) and tests/test_user_todos_switch.py,
  // not by this text read.
  const routeFunction = (p: string, fn: string) => {
    const at = KERNEL.indexOf(`if u.path == "${p}":`);
    assert.ok(at > 0, `Handler.do_POST has a ${p} route`);
    const rest = KERNEL.slice(at + 1), end = rest.search(/\n\s*if u\.path == "/);
    const block = end > 0 ? rest.slice(0, end) : rest;
    assert.ok(block.includes(`st, out = ${fn}(body)`) && block.includes("self._send(st, json.dumps(out)"),
      `the ${p} route hands its parsed body to ${fn} and sends whatever it answers`);
    const def = KERNEL.indexOf(`\ndef ${fn}(body):`);
    assert.ok(def > 0, `${fn} is defined`);
    return KERNEL.slice(def, KERNEL.indexOf("\ndef ", def + 1));
  };
  for (const [p, fn] of [["/usertodo", "_user_todo_register_route"], ["/usertodo/withdraw", "_user_todo_withdraw_route"]]) {
    assert.match(routeFunction(p, fn), /if not _user_todos_on\(\):\n(?:\s*#[^\n]*\n)*\s*return 409, \{"ok": False, "error": _USER_TODOS_OFF_ERR\}/,
      `the handler's ${p} route still hands its body to ${fn}, and that function still carries the switch's 409. `
      + "A text pin on where the 409 lives: it guards against the handler losing the route to the function, not against "
      + "the 409 being right. The 409's correctness under the switch is proven by execution in "
      + "tests/test_user_todo_route_answers.py (the golden of the routes' HTTP answers) and tests/test_user_todos_switch.py, "
      + "not by this text read");
  }
  assert.match(KERNEL, /elif t == "userTodoAnswer"[\s\S]*?if not _user_todos_on\(\):\n\s+client\["send"\]\(json\.dumps\(\{"type": "warn", "text": _USER_TODOS_OFF_WARN, "sid": sid\}\)\)/,
    "userTodoAnswer warns with the switch's own text, ahead of the settled-row gate");
  assert.match(KERNEL, /elif t == "userTodoDismiss"[\s\S]*?"type": "warn", "text": _USER_TODOS_OFF_WARN/, "userTodoDismiss warns");
  assert.match(BUS, /USER_TODOS_SWITCH = STATE\.parent \/ "user-todos-enabled\.json"/);
  assert.match(BUS, /"tools": _tools_offered\(\)/);
  assert.match(BUS, /USER_TODO_TOOLS = \("add_user_todo", "withdraw_user_todo"\)/);
});
