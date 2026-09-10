// ensureThenAttach (kernel-attach.ts): a front end attaches to a manager-owned kernel; if none is on
// its port it asks the manager to ensure one, waits, then attaches. It must NEVER conclude success
// without /healthz passing, and must distinguish "no manager running" from "manager acked but the
// kernel never came up" so the UI can show the right fix. Tests inject deps so they run instantly.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { ensureThenAttach, parseHealthz, warnAfter, AttachDeps } from "./kernel-attach";

const noDelay = () => Promise.resolve();

// A scripted healthz that returns the i-th value per call, sticking on the last.
function healthSeq(seq: boolean[]) {
  let i = 0;
  return () => Promise.resolve(seq[Math.min(i++, seq.length - 1)]);
}

test("attaches immediately when a kernel already serves the port (never asks the manager)", async () => {
  let asked = 0;
  const res = await ensureThenAttach({
    healthz: () => Promise.resolve(true),
    ensureViaManager: () => { asked++; return Promise.resolve(true); },
    delay: noDelay,
  });
  assert.deepEqual(res, { ok: true });
  assert.equal(asked, 0, "should not contact the manager when a kernel is already up");
});

test("no kernel + no manager → reason no-manager (does not poll)", async () => {
  let polls = 0;
  const deps: AttachDeps = {
    healthz: () => { polls++; return Promise.resolve(false); },
    ensureViaManager: () => Promise.resolve(false),
    delay: noDelay,
    pollTries: 10,
  };
  const res = await ensureThenAttach(deps);
  assert.deepEqual(res, { ok: false, reason: "no-manager" });
  assert.equal(polls, 1, "only the initial probe; no post-ensure polling when the manager is absent");
});

test("manager ensures and the kernel comes up on a later poll → ok", async () => {
  // down on the initial probe + first poll, then up
  const res = await ensureThenAttach({
    healthz: healthSeq([false, false, true]),
    ensureViaManager: () => Promise.resolve(true),
    delay: noDelay,
    pollTries: 5,
  });
  assert.deepEqual(res, { ok: true });
});

test("manager acked but the kernel never serves → reason kernel-didnt-start (bounded by pollTries)", async () => {
  let polls = 0;
  const res = await ensureThenAttach({
    healthz: () => { polls++; return Promise.resolve(false); },
    ensureViaManager: () => Promise.resolve(true),
    delay: noDelay,
    pollTries: 4,
  });
  assert.deepEqual(res, { ok: false, reason: "kernel-didnt-start" });
  assert.equal(polls, 5, "1 initial probe + 4 post-ensure polls, then give up");
});

test("default poll budget covers a kernel RESTART, not just a clean spawn (>= 10s)", async () => {
  // A `romp refresh` respawn + cold boot can exceed the old ~5s budget; attaching mid-restart
  // then toasted "couldn't bring up a kernel" while it came up seconds later (2026-07-13).
  let waited = 0;
  const res = await ensureThenAttach({
    healthz: () => Promise.resolve(false),
    ensureViaManager: () => Promise.resolve(true),
    delay: (ms) => { waited += ms; return Promise.resolve(); },
  });
  assert.deepEqual(res, { ok: false, reason: "kernel-didnt-start" });
  assert.ok(waited >= 10000, `default budget must be >= 10s of polling, got ${waited}ms`);
});

test("warnAfter: one failed round is a transient (quiet); a persistent failure warns", () => {
  assert.equal(warnAfter(0), false);
  assert.equal(warnAfter(1), false, "a single failure (e.g. attaching mid-restart) must not interrupt");
  assert.equal(warnAfter(2), true);
  assert.equal(warnAfter(5), true);
});

test("parseHealthz accepts BOTH kernel generations: plain 'ok' and {ok:true} JSON", () => {
  // The Python kernel's plain-text form read as unhealthy under the old JSON-only
  // parse — VS Code could never attach to a healthy kernel (2026-07-13).
  assert.deepEqual(parseHealthz(200, "ok"), { ok: true });
  assert.deepEqual(parseHealthz(200, " ok\n"), { ok: true });
  assert.deepEqual(parseHealthz(200, '{"ok": true, "version": "1.2"}'), { ok: true, version: "1.2" });
  assert.equal(parseHealthz(200, '{"ok": false}').ok, false);
});

test("parseHealthz rejects non-200s and junk bodies", () => {
  assert.equal(parseHealthz(403, "ok").ok, false, "a forbidden 'ok' body is not health");
  assert.equal(parseHealthz(undefined, "ok").ok, false);
  assert.equal(parseHealthz(200, "<html>proxy error</html>").ok, false);
  assert.equal(parseHealthz(200, "").ok, false);
});

// ---- the manager's /ensure request and the toast per reason (the manager's write gate, 2026-09-10) ----
// askManagerEnsure runs against a real loopback server: the header it sends, and the three answers the
// decision must tell apart (took it; nothing there; answered and refused, 401 or 503). Before this the
// extension read every status >= 400 as "no manager" and the toast sent the user to `romp up`, which
// then reported a manager already running.
import * as http from "http";
import * as net from "net";
import { askManagerEnsure, attachFailureToast, ManagerRefusal } from "./kernel-attach";

type Seen = { method?: string; url?: string; token?: string };
function fakeManager(status: number, body: string): Promise<{ port: number; seen: Seen[]; close: () => void }> {
  const seen: Seen[] = [];
  const srv = http.createServer((req, res) => {
    seen.push({ method: req.method, url: req.url, token: String(req.headers["x-romp-token"] ?? "") });
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(body);
  });
  return new Promise((resolve) => srv.listen(0, "127.0.0.1", () => {
    const port = (srv.address() as net.AddressInfo).port;
    resolve({ port, seen, close: () => srv.close() });
  }));
}
function closedPort(): Promise<number> {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.listen(0, "127.0.0.1", () => { const p = (s.address() as net.AddressInfo).port; s.close(() => resolve(p)); });
  });
}

test("askManagerEnsure POSTs /ensure?port=N with the serve token in X-Romp-Token, and a 200 is true", async () => {
  const m = await fakeManager(200, '{"ok":true,"spawned":true}');
  try {
    const r = await askManagerEnsure({ host: "127.0.0.1", managerPort: m.port, port: 29999, token: "zq9-window-token-zq9" });
    assert.equal(r, true);
    assert.deepEqual(m.seen, [{ method: "POST", url: "/ensure?port=29999", token: "zq9-window-token-zq9" }]);
  } finally { m.close(); }
});

test("a 401 and a 503 come back as the manager's refusal, with its words and the status; the decision files manager-refused without polling", async () => {
  for (const [status, words] of [[401, "serve token required: send it in X-Romp-Token (the serve-token file under the kernel's state root: /x/state/serve-token for the primary kernel)"],
                                 [503, "the manager cannot read the serve token (/x/state/serve-token: EACCES); state-changing requests are refused until it can"]] as [number, string][]) {
    const m = await fakeManager(status, JSON.stringify({ ok: false, error: words }));
    try {
      const r = await askManagerEnsure({ host: "127.0.0.1", managerPort: m.port, port: 29999, token: "zq9-window-token-zq9" });
      assert.deepEqual(r, { status, refused: words } as ManagerRefusal);
      let polls = 0;
      const res = await ensureThenAttach({
        healthz: () => { polls++; return Promise.resolve(false); },
        ensureViaManager: () => Promise.resolve(r),
        delay: noDelay,
        pollTries: 10,
      });
      assert.deepEqual(res, { ok: false, reason: "manager-refused", status, detail: words });
      assert.equal(polls, 1, "a refusal is an answer: nothing to wait for");
    } finally { m.close(); }
  }
});

test("a refusal whose body is not the manager's JSON still carries the status", async () => {
  const m = await fakeManager(500, "boom");
  try {
    assert.deepEqual(await askManagerEnsure({ host: "127.0.0.1", managerPort: m.port, port: 1, token: "t" }), { status: 500, refused: "HTTP 500" });
  } finally { m.close(); }
});

test("nothing on the port is false, as before: no-manager", async () => {
  const port = await closedPort();
  const r = await askManagerEnsure({ host: "127.0.0.1", managerPort: port, port: 29999, token: "t", timeoutMs: 2000 });
  assert.equal(r, false);
  const res = await ensureThenAttach({ healthz: () => Promise.resolve(false), ensureViaManager: () => Promise.resolve(r), delay: noDelay, pollTries: 2 });
  assert.deepEqual(res, { ok: false, reason: "no-manager" });
});

test("attachFailureToast: each reason names its own fix; a refusal never sends the user to `romp up`", () => {
  const ctx = { port: 29855, managerPort: 7432, tokenFile: "/x/state/serve-token", tokenFromEnv: false, hadToken: true };
  const none = attachFailureToast({ ok: false, reason: "no-manager" }, ctx);
  assert.match(none, /no manager on :7432/);
  assert.match(none, /romp up/);
  const dead = attachFailureToast({ ok: false, reason: "kernel-didnt-start" }, ctx);
  assert.match(dead, /port 29855/);
  assert.match(dead, /romp status/);
  const words = "serve token required: send it in X-Romp-Token (the serve-token file under the kernel's state root: /m/state/serve-token for the primary kernel)";
  const wrong = attachFailureToast({ ok: false, reason: "manager-refused", status: 401, detail: words }, ctx);
  assert.match(wrong, /does not hold the serve token this window read from \/x\/state\/serve-token/, "which root this window read");
  assert.match(wrong, /another state root/);
  assert.match(wrong, /ROMP_STATE_DIR/);
  assert.match(wrong, /romp status/);
  assert.ok(wrong.endsWith(`Manager: ${words}`), "the manager's own words, which name its file");
  assert.doesNotMatch(wrong, /romp up/, "a manager IS running: `romp up` would only say so");
  const missing = attachFailureToast({ ok: false, reason: "manager-refused", status: 401, detail: words }, { ...ctx, hadToken: false });
  assert.match(missing, /found none at \/x\/state\/serve-token/);
  assert.match(missing, /ROMP_STATE_DIR/);
  const env = attachFailureToast({ ok: false, reason: "manager-refused", status: 401, detail: words }, { ...ctx, tokenFromEnv: true });
  assert.match(env, /read from ROMP_SERVE_TOKEN/, "the env spelling outranks the file, so the toast names it");
  const notoken = attachFailureToast({ ok: false, reason: "manager-refused", status: 503, detail: "the manager cannot read the serve token (/m/state/serve-token: EACCES); state-changing requests are refused until it can" }, ctx);
  assert.match(notoken, /cannot read its serve-token file/);
  assert.match(notoken, /0600 file/);
  assert.doesNotMatch(notoken, /romp up/);
  const other = attachFailureToast({ ok: false, reason: "manager-refused", status: 500, detail: "HTTP 500" }, ctx);
  assert.match(other, /HTTP 500/);
  assert.match(other, /romp status/);
  for (const t of [none, dead, wrong, missing, env, notoken, other]) assert.doesNotMatch(t, /\u2014/, "no em dashes in a toast");
});
