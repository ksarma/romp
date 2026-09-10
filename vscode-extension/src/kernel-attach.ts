// kernel-attach — the ensure-then-attach decision, factored OUT of any front end so it can be unit
// tested headlessly (extension.ts can't be imported in a node test — it pulls in `vscode`).
//
// The rule (the user's 2026-06-13 ruling): a front end NEVER spawns the kernel itself. It attaches to
// a manager-owned kernel on its configured port; if none is there, it asks the `romp up` manager to
// ENSURE one (the manager spawns + owns it), then waits for it to come up and attaches. This keeps a
// single owner (no invisible orphans, no two front ends fighting over the port) while still giving the
// "point a front end at a port and a kernel appears" UX.

import * as http from "http";

// The manager's answer to POST /ensure, as the decision below reads it (the manager's write gate,
// 2026-09-10): true, the manager took it; false, nothing answered (no manager on the port, or no answer
// inside the timeout); a refusal, the manager answered 4xx or 5xx, with its own one-line error and the
// status. 401 is a token the manager does not hold (this window's state root is not the manager's, or
// it found no token file); 503 is a manager that cannot read its own token file.
export type ManagerRefusal = { refused: string; status: number };

export interface AttachDeps {
  // resolves true once a kernel is serving /healthz on the target port
  healthz: () => Promise<boolean>;
  // POST manager /ensure?port=N: true iff the manager took it, false when nothing answered, else its refusal
  ensureViaManager: () => Promise<boolean | ManagerRefusal>;
  // await-able sleep (injected so tests run instantly)
  delay: (ms: number) => Promise<void>;
  // How long to wait for a freshly-ensured kernel to start serving. A RESTART
  // (romp refresh) also lands here — healthz is down while the manager
  // respawns, and a cold kernel boot (reconcile + bundle check) can take well
  // over 5s — so the budget must cover a restart, not just a clean spawn
  // (the user 2026-07-13: a reload during a refresh raised the failure toast
  // even though the kernel was up seconds later).
  pollTries?: number;   // default 40
  pollMs?: number;      // default 250  → ~10s total
}

export type AttachResult =
  | { ok: true }
  | { ok: false; reason: "no-manager" }        // nothing serving the port AND no manager to ask
  | { ok: false; reason: "manager-refused"; status: number; detail: string }   // a manager answered, and said no
  | { ok: false; reason: "kernel-didnt-start" }; // manager acked but the kernel never came up (port in use?)

export async function ensureThenAttach(d: AttachDeps): Promise<AttachResult> {
  // 1. Already a kernel on our port? Attach straight away — the common case.
  if (await d.healthz()) return { ok: true };
  // 2. None there — ask the manager to ensure one. If the manager isn't running, we can't proceed. A
  //    manager that answered and refused is a different failure with a different fix (review round 1,
  //    2026-09-10: a 401 or 503 used to read as "no manager", and the toast sent the user to `romp up`,
  //    which then reported a manager already running).
  const answer = await d.ensureViaManager();
  if (answer === false) return { ok: false, reason: "no-manager" };
  if (answer !== true) return { ok: false, reason: "manager-refused", status: answer.status, detail: answer.refused };
  // 3. Manager is bringing it up (or already owns it) — poll until it's serving.
  const tries = d.pollTries ?? 40;
  const ms = d.pollMs ?? 250;
  for (let i = 0; i < tries; i++) {
    await d.delay(ms);
    if (await d.healthz()) return { ok: true };
  }
  // 4. Manager answered but no kernel came up — most often the port is held by a foreign process.
  return { ok: false, reason: "kernel-didnt-start" };
}

// The liveness probe's answer. The Python kernel serves /healthz as plain-text
// "ok" (auth-exempt); the superseded TS kernel answered {"ok":true,"version":…}.
// The old JSON-only parse read the plain form as UNHEALTHY, so the extension
// could never attach to the real kernel and always escalated to the manager —
// the "couldn't bring up a kernel" toast with a healthy kernel on the port
// (the user 2026-07-13, broken since the serve-layer security change
// de58481 on 2026-06-15). Accept both forms — a remote/federated kernel may
// run either generation.
export function parseHealthz(status: number | undefined, body: string): { ok: boolean; version?: string } {
  if ((status ?? 0) !== 200) return { ok: false };
  const t = String(body || "").trim();
  if (t === "ok") return { ok: true };
  try {
    const j = JSON.parse(t);
    return { ok: !!j.ok, version: j.version ? String(j.version) : undefined };
  } catch {
    return { ok: false };
  }
}

// Should this many CONSECUTIVE failed attach rounds interrupt the user? One
// round can fail transiently (attaching in the middle of a kernel restart);
// the caller's retry loop runs another round seconds later, and only a
// PERSISTENT failure is the user's problem — a false interrupt is a broken
// flow state.
export function warnAfter(consecutiveFailures: number): boolean {
  return consecutiveFailures >= 2;
}

// POST the manager's /ensure?port=N with the serve token, and read the answer the way ensureThenAttach
// wants it. vscode-free, so the header and the three outcomes run against a real loopback server in
// kernel-attach.test.ts (extension.ts cannot be imported by node --test: it pulls in `vscode`). /ensure
// is a state-changing door, so it carries the token the way every kernel request does (the manager gates
// its writes on X-Romp-Token, bin/romp-manager writeGate). A 4xx or 5xx body is the manager's one-line
// JSON {error}; it names the header and the manager's token file, never a token.
export function askManagerEnsure(o: { host: string; managerPort: number; port: number; token: string; timeoutMs?: number }):
  Promise<boolean | ManagerRefusal> {
  return new Promise((resolve) => {
    const req = http.request(
      { host: o.host, port: o.managerPort, path: `/ensure?port=${o.port}`, method: "POST",
        timeout: o.timeoutMs ?? 4000, headers: { "X-Romp-Token": o.token } },
      (res) => {
        const status = res.statusCode ?? 500;
        if (status < 400) { res.resume(); resolve(true); return; }
        let body = "";
        res.on("data", (d) => (body += d));
        res.on("end", () => resolve({ status, refused: refusalText(body, status) }));
      });
    req.on("timeout", () => { req.destroy(); resolve(false); });
    req.on("error", () => resolve(false));
    req.end();
  });
}

function refusalText(body: string, status: number): string {
  try {
    const e = (JSON.parse(body) as { error?: unknown }).error;
    if (typeof e === "string" && e.trim()) return e.trim();
  } catch { /* not JSON: the status is all there is */ }
  return `HTTP ${status}`;
}

// The toast for a failed attach round, in the user's terms: what did not happen, why, and the way out.
// One function for every reason, so the text a round produces is pinned beside the decision that
// produced it. `tokenFile` is the serve-token file this window reads (the extension's serveToken);
// `tokenFromEnv` says ROMP_SERVE_TOKEN outranked it; `hadToken` says the read found one.
export function attachFailureToast(res: Exclude<AttachResult, { ok: true }>,
                                   ctx: { port: number; managerPort: number; tokenFile: string; tokenFromEnv: boolean; hadToken: boolean }): string {
  const mp = `:${ctx.managerPort}`;
  if (res.reason === "no-manager") {
    return `romp: no kernel on port ${ctx.port} and no manager on ${mp}; start it with \`romp up\` in a terminal.`;
  }
  if (res.reason === "kernel-didnt-start") {
    return `romp: the manager couldn't bring up a kernel on port ${ctx.port}; is that port already in use? Check \`romp status\`.`;
  }
  const src = ctx.tokenFromEnv ? "ROMP_SERVE_TOKEN" : ctx.tokenFile;
  if (res.status === 401 && !ctx.hadToken) {
    return `romp: the manager on ${mp} needs the serve token, and this window found none at ${src}. `
      + `Point this window at the manager's state root (ROMP_STATE_DIR) or check \`romp status\` in a terminal. Manager: ${res.detail}`;
  }
  if (res.status === 401 && ctx.tokenFromEnv) {
    // the env spelling outranks the file (review round 2, 2026-09-10): a stale ROMP_SERVE_TOKEN in the window's
    // environment is the likelier cause, and the state root changes nothing while it is set
    return `romp: the manager on ${mp} does not hold the serve token this window read from ROMP_SERVE_TOKEN. `
      + `Unset it and relaunch this window (or start VS Code from a shell without it), or check \`romp status\` in a terminal. Manager: ${res.detail}`;
  }
  if (res.status === 401) {
    return `romp: the manager on ${mp} does not hold the serve token this window read from ${src}, so it runs under another state root. `
      + `Point this window at that root (ROMP_STATE_DIR) or check \`romp status\` in a terminal. Manager: ${res.detail}`;
  }
  if (res.status === 503) {
    return `romp: the manager on ${mp} cannot read its serve-token file, so it refuses every request. `
      + `Make that file a regular 0600 file that you own, under the manager's state root; the manager log names it. Manager: ${res.detail}`;
  }
  return `romp: the manager on ${mp} refused to bring up a kernel on port ${ctx.port} (HTTP ${res.status}: ${res.detail}). Check \`romp status\` and the manager log.`;
}
