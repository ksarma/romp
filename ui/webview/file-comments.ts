// File comments and tracked changes — the viewer's Comments panel (plans/file-review.md, Slice 1).
//
// The person who directs the sessions reads their output as files, and until now a comment on a file
// left romp: GitHub, a chat quote that scrolled away, or a note typed into the file itself. This panel
// keeps a comment WITH the file, in the track-changents sidecar the agent's own CLIs read and write
// (`.trackchanges/` beside the project's root; docs/adr/0002), and hands everything unsent to the
// session in ONE message — so a morning's reading costs one interruption, not one per remark.
//
// Shape (the plan's Shape of the feature):
//   • The action-row entry is the glance ("Comments · 2 · 5 changes"); the panel is one click; a card
//     expands on click, keyed by comment id in a set that survives every re-render.
//   • The kernel does the disk work on the OWNING kernel (the `fileComments` op runs a node host
//     script over the vendored track-changents store); this module renders JSON and never holds a
//     sidecar it writes back. Both ops carry `sid`, so federation routes a remote session's file to
//     the kernel that owns the disk with no new relay code.
//   • Change awareness by POLLING (2.5 s while the panel is open and the tab visible): HEAD /file on
//     the file, the sidecar the kernel named, and the project's config.json, comparing X-Romp-Mtime-Ns
//     as STRINGS. The Files pane has no filesystem watcher; the poll stands in for that event, and the
//     person's own writes never fire it because every verb reply re-baselines it.
//   • What is unsent is derived from the comments log on the owning kernel, never from browser state
//     (decision 10): the `status` reply carries it, the button's count is that number.
//   • Every write sits behind the one file-editing consent, shared with Save (decision 5).
// The pure half (view model, message preview, poll verdicts) is file-comments-model.ts; the
// selection→anchor mapping and the highlight painters are anchor-map.ts (contract C4).
//
// This module imports only TYPES from file-view.ts and is registered there (registerFileViewAction
// in file-view.ts), so the two never form a runtime import cycle.
import type { FileViewAction, FileViewActionCtx, FileViewIdentity } from "./file-view";
import { delegate, flash } from "./actions";
import { fileUrl } from "./preview";
import { kernelUrl } from "./media";
import { hostOf, bareId } from "./host-prefix";
import { mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered, rawOffsetToLine } from "./anchor-map";
import type { MapRefusal, SourceRange, Located } from "./anchor-map";
import {
  type Status, type Card, type SendParts, actionLabel, cardModel, sendParts, buildSendMessage, unsentCount,
  logRowText, pollBaseline, pollTargets, headVerdict, mtimeMoved, editBlockedReason, lineStartOffset, folderOf,
  type PollBaseline,
} from "./file-comments-model";

const POLL_MS = 2500;
const MOVED = new Set(["store-moved", "file-moved", "config-moved"]);

function el(tag: string, cls?: string, text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function btn(label: string, act: string, cls = "fileview-btn"): HTMLButtonElement {
  const b = el("button", cls, label) as HTMLButtonElement;
  b.type = "button";
  b.dataset.act = act;
  return b;
}
const clock = (t: number | string): string => {
  const d = new Date(t);
  if (isNaN(d.getTime())) return "";
  const today = new Date();
  const sameDay = d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate();
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return sameDay ? hm : d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + hm;
};
// a pane the shell has hidden gives its iframe a ZERO viewport (document.hidden stays false there) — the
// Sessions pane's gate, reused: skip the tick while hidden, catch up once on the first visible moment
const paneHidden = (): boolean => document.hidden || window.innerWidth === 0 || window.innerHeight === 0;

type Pending = { verb: string; ok: (m: Record<string, unknown>) => void; fail: (e: { code: string; error: string }) => void };
type Composer =
  | { kind: "comment"; range: SourceRange | null; quote: string | null; refusal: (MapRefusal & { selText: string }) | null }
  | { kind: "reply"; commentId: string; ref: string };
type Err = { text: string; reload: boolean; warn?: boolean };

// ── the wire: ONE window listener for the module, dispatching to the live panel by reqId ───────────
// A reply is matched by reqId only — a REMOTE kernel's reply comes back with its sid host-prefixed
// (federation's prefixInbound), so sid equality would fail there. A federation `warn` carries no reqId
// and means the owning host is unreachable: while a request is outstanding it is that request's
// failure (the viewer does the same for saveFile). The shim's own drop event (romp:wsdown) likewise.
let live: Panel | null = null;
let listening = false;
function ensureListener(): void {
  if (listening) return;
  listening = true;
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m || !live) return;
    if (m.type === "fileCommentsResult" || m.type === "fileCommentsSent") live.settle(m, true);
    else if (m.type === "fileCommentsFailed" || m.type === "fileCommentsSendFailed") live.settle(m, false);
    else if (m.type === "warn") live.failAll(String(m.text || "the session's host is not answering"));
  });
  window.addEventListener("romp:wsdown", () => { if (live) live.failAll("the connection dropped; try again once it returns"); });
}

let reqSeq = 0;

class Panel {
  status: Status | null = null;
  root: HTMLElement | null = null;          // the aside, built on first open
  open = false;
  pending = new Map<number, Pending>();
  openCards = new Set<string>();            // keyed expand state: survives every re-render (ui/CLAUDE.md)
  logOpen = false;
  resolvedOpen = false;
  trackChoice = false;                      // the on-toggle's scope row (file / folder) is showing
  trackStop = false;                        // the folder-off confirm is showing
  composer: Composer | null = null;
  errors = new Map<string, Err>();          // per slot: the row sits under the control that asked
  busy = new Set<string>();
  sendConfirm = false;
  sending = false;
  sendOpts = { todo: true, track: true };   // both checked by default (decision 8)
  sentNote: string | null = null;
  todoAnswered = false;                     // one send answers the todo; later sends show no checkbox
  previewOpen = false;
  colors: Map<string, FileViewIdentity> | null = null;
  located = new Map<string, Located & { painted: boolean }>();
  base: PollBaseline | null = null;
  stopped = new Set<string>();              // poll targets a 413/415 retired
  timer: ReturnType<typeof setInterval> | null = null;
  polling = false;
  tickSkipped = false;
  // persistent section wrappers: render() swaps each section's CHILDREN, never the aside's own children —
  // replaceChildren on the aside would remove and re-insert the composer box, and a removed element
  // loses focus, so a poll-triggered re-render would drop the input's focus mid-word
  sections = { head: el("div", "fc-sec-head"), cards: el("div", "fc-sec-cards"), send: el("div", "fc-sec-send"), log: el("div", "fc-sec-log") };
  // persistent composer parts, for the same reason
  composerBox = el("div", "fc-composer");
  composerRef = el("div", "fc-composer-ref");
  input = el("input", "fc-input") as HTMLInputElement;
  composerActs = el("div", "fc-actions");
  composerErr = el("div");
  float = el("button", "fileview-btn fc-float", "Comment") as HTMLButtonElement;
  catchUp = () => { if (this.tickSkipped) void this.tick(); };
  hideFloatOnDown = (ev: Event) => { if (ev.target !== this.float) this.float.hidden = true; };

  constructor(readonly ctx: FileViewActionCtx, readonly button: HTMLButtonElement, readonly unit: HTMLElement) {
    ensureListener();
    live = this;
    this.input.type = "text";
    this.input.placeholder = "Your note (Enter saves, Esc cancels)";
    this.input.setAttribute("aria-label", "Comment text");
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); void this.saveComposer(); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); this.closeComposer(); }   // never the viewer's Escape
    });
    (this.float as HTMLButtonElement).type = "button";
    this.float.hidden = true;
    this.float.title = "Comment on the selected passage";
    // keep the selection alive across the click: a mousedown elsewhere would collapse it before the click lands
    for (const ev of ["mousedown", "touchstart"]) this.float.addEventListener(ev, (e) => e.preventDefault());
    this.float.addEventListener("click", () => {
      flash(this.float);
      const sel = window.getSelection();
      this.float.hidden = true;
      if (sel && !sel.isCollapsed) this.startComment(sel);
    });
    document.body.appendChild(this.float);
    document.addEventListener("mousedown", this.hideFloatOnDown, true);
    ctx.onSelection((sel) => this.onSelection(sel));
    ctx.onRendered(() => { this.float.hidden = true; this.paintAll(); });
    ctx.onSaved((info) => {
      if (this.base) this.base.file = info.mtimeNs;   // the poll must not re-fetch the person's own save
      if (this.status) void this.refresh();            // the Log gained the edit entry before the reply
    });
    ctx.onClose(() => this.dispose());
    // every control the panel ever renders hangs off ONE stable root (ui/CLAUDE.md, click-safe): the
    // viewer's body row, which also holds the painted highlights — so a highlight click routes here too
    const row = ctx.body().parentElement || ctx.body();
    delegate(row, {
      fctrack: () => this.onTrackClick(),
      fctrackfile: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "file" }, "track"); },
      fctrackfolder: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "folder" }, "track"); },
      fctrackcancel: () => { this.trackChoice = false; this.trackStop = false; this.render(); },
      fctrackstop: () => { this.trackStop = false; void this.mutate("set-tracked", { on: false, scope: "folder" }, "track"); },
      fcfile: () => this.startFileComment(),
      fcsave: () => { void this.saveComposer(); },
      fccancel: () => this.closeComposer(),
      fcraw: () => this.switchToRaw(),
      fccard: (x) => { const id = x.dataset.id!; if (this.openCards.has(id)) this.openCards.delete(id); else this.openCards.add(id); this.render(); },
      fcgoto: (x, ev) => { ev.stopPropagation(); this.goTo(x.dataset.id!); },
      fcreveal: (x, ev) => { ev.stopPropagation(); this.reveal(x.dataset.id!); },
      fcreply: (x, ev) => { ev.stopPropagation(); this.startReply(x.dataset.id!); },
      fcresolve: (x, ev) => { ev.stopPropagation(); void this.mutate("resolve", { commentId: x.dataset.id!, on: x.dataset.on === "1" }, "card:" + x.dataset.id!); },
      fcresolved: () => { this.resolvedOpen = !this.resolvedOpen; this.render(); },
      fcsend: () => { this.sendConfirm = true; this.sentNote = null; this.render(); },
      fcsendcancel: () => { this.sendConfirm = false; this.previewOpen = false; this.render(); },
      fcsendgo: () => { void this.doSend(); },
      fcpreview: () => { this.previewOpen = !this.previewOpen; this.render(); },
      fclog: () => { this.logOpen = !this.logOpen; this.render(); },
      fcreload: (x) => { this.errors.delete(x.dataset.slot || ""); this.stopped.clear(); void this.refresh(); this.ctx.reload(); },
      fcerrx: (x) => { this.errors.delete(x.dataset.slot || ""); this.render(); },
      fcopen: (x) => { this.openPanel(); const id = x.dataset.id!; this.openCards.add(id); this.render(); this.scrollCard(id); },
    });
    row.addEventListener("change", (ev) => {
      const t = ev.target as HTMLInputElement | null;
      if (!t || t.dataset.opt !== "todo" && t.dataset.opt !== "track") return;
      this.sendOpts[t.dataset.opt as "todo" | "track"] = t.checked;
    });
    this.button.addEventListener("click", () => { flash(this.button); if (this.open) this.closePanel(); else this.openPanel(); });
  }

  // ── the wire ───────────────────────────────────────────────────────────────────────────────────
  request(verb: string, args?: Record<string, unknown>, fence?: Record<string, string>): Promise<Status> {
    const reqId = ++reqSeq;
    const { ctx } = this;
    const msg: Record<string, unknown> = { type: "fileComments", reqId, sid: ctx.sid || undefined, path: ctx.path, verb };
    if (args) msg.args = args;
    if (fence) msg.fence = fence;
    return new Promise<Status>((ok, fail) => {
      this.pending.set(reqId, { verb, ok: (m) => ok(m as unknown as Status), fail });
      ctx.post(msg);
    });
  }
  requestSend(msg: Record<string, unknown>): Promise<{ queued: boolean; warning?: string }> {
    const reqId = ++reqSeq;
    return new Promise((ok, fail) => {
      this.pending.set(reqId, { verb: "send", ok: (m) => ok({ queued: m.queued === true, warning: typeof m.warning === "string" ? m.warning : undefined }), fail });
      this.ctx.post({ ...msg, type: "fileCommentsSend", reqId });
    });
  }
  settle(m: Record<string, unknown>, ok: boolean): void {
    const p = this.pending.get(Number(m.reqId));
    if (!p) return;                                    // an older open's reply, or a stale one — lands nowhere
    this.pending.delete(Number(m.reqId));
    if (ok) p.ok(m);
    else p.fail({ code: String(m.code || "failed"), error: String(m.error || "the request failed") });
  }
  failAll(text: string): void {
    if (!this.pending.size) return;
    const ps = [...this.pending.values()]; this.pending.clear();
    for (const p of ps) p.fail({ code: "unreachable", error: text });
  }

  // ── status ─────────────────────────────────────────────────────────────────────────────────────
  /** The first ask, at mount: mounted hidden, revealed when the kernel answers (the GitHub link's
   *  idiom). A `no-node` refusal keeps the action away for good — the gear's row says why. */
  probe(): void {
    this.request("status").then((s) => this.applyStatus(s), (e: { code: string; error: string }) => {
      if (e.code === "no-node") return;
      this.unit.hidden = false;
      this.button.title = "Comments: " + e.error;
      this.errors.set("head", { text: e.error, reload: false });
    });
  }
  applyStatus(s: Status): void {
    this.status = s;
    this.base = pollBaseline(s);
    this.unit.hidden = false;
    this.button.textContent = actionLabel(s);
    this.button.title = s.store ? "Comments and changes kept beside this file" : "Comment on this file, or track a session's changes to it";
    this.ctx.setEditBlocked(editBlockedReason(s.hunks || []));
    this.paintAll();                                   // repaints the highlights and renders the panel
  }
  async refresh(): Promise<void> {
    try { this.applyStatus(await this.request("status")); }
    catch (e) { this.errors.set("head", { text: (e as { error: string }).error, reload: false }); this.render(); }
  }

  // ── open / close ───────────────────────────────────────────────────────────────────────────────
  openPanel(): void {
    if (this.open) return;
    this.open = true;
    if (!this.root) this.root = el("div", "fc-panel");
    this.ctx.aside(this.root);
    this.button.classList.add("on"); this.button.setAttribute("aria-pressed", "true");
    if (!this.colors) void this.loadColors();
    this.render();
    void this.refresh();
    this.startPoll();
  }
  closePanel(): void {
    if (!this.open) return;
    this.open = false;
    this.ctx.aside(null);
    this.button.classList.remove("on"); this.button.setAttribute("aria-pressed", "false");
    this.float.hidden = true;
    this.stopPoll();
  }
  dispose(): void {
    this.stopPoll();
    this.float.remove();
    document.removeEventListener("mousedown", this.hideFloatOnDown, true);
    this.failAll("the file viewer closed");
    if (live === this) live = null;
  }

  // ── the session color map: one GET /sessions per panel open, authorId → name + colour ──────────
  // /sessions lists the LOCAL kernel's sessions; a remote session's authors get the neutral chip (there
  // is no /remote/<host>/sessions route today).
  async loadColors(): Promise<void> {
    this.colors = new Map();
    if (this.ctx.sid && hostOf(this.ctx.sid)) return;
    try {
      const rows = await (await fetch(kernelUrl("/sessions"), { cache: "no-store" })).json();
      if (Array.isArray(rows)) {
        for (const r of rows) {
          if (r && typeof r.id === "string" && typeof r.name === "string") {
            this.colors.set(r.id, { name: r.name, color: typeof r.bg === "string" && typeof r.fg === "string" ? { bg: r.bg, fg: r.fg } : null });
          }
        }
      }
    } catch { /* the chips fall back to their labels */ }
    this.render();
  }
  sessionName(): string {
    const id = this.ctx.identity();
    if (id && id.name) return id.name;
    const c = this.ctx.sid && this.colors ? this.colors.get(bareId(this.ctx.sid)) : null;
    return c ? c.name : "the session";
  }

  // ── the poll ───────────────────────────────────────────────────────────────────────────────────
  startPoll(): void {
    if (this.timer) return;
    this.timer = setInterval(() => { void this.tick(); }, POLL_MS);
    document.addEventListener("visibilitychange", this.catchUp);
    window.addEventListener("resize", this.catchUp);
  }
  stopPoll(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    document.removeEventListener("visibilitychange", this.catchUp);
    window.removeEventListener("resize", this.catchUp);
  }
  async tick(): Promise<void> {
    if (!this.open || !this.status || !this.base || this.polling) return;
    if (paneHidden()) { this.tickSkipped = true; return; }
    this.tickSkipped = false;
    this.polling = true;
    try {
      const t = pollTargets(this.status, this.ctx.path);
      const base = this.base;
      const checks: Array<[keyof PollBaseline, string]> = [["file", t.file]];
      if (t.store) checks.push(["store", t.store]);
      if (t.config) checks.push(["config", t.config]);
      let fileMoved = false, moved = false;
      for (const [key, target] of checks) {
        if (this.stopped.has(target)) continue;
        let r: Response;
        try { r = await fetch(fileUrl(target, this.ctx.sid), { method: "HEAD", cache: "no-store" }); }
        catch { continue; }                          // a network blip: the next tick tries again
        const v = headVerdict(r.status, r.headers.get("X-Romp-Mtime-Ns"));
        if (v.kind === "stop") {
          this.stopped.add(target);
          this.errors.set("poll", { text: "Stopped watching " + target + ": the kernel answered " + v.status
            + (v.status === 413 ? " (too large to serve)" : " (not a type it serves)") + ". Reload to try again.", reload: true });
          this.render();
          continue;
        }
        if (v.kind !== "value") continue;
        if (mtimeMoved(base[key], v.value)) { moved = true; if (key === "file") fileMoved = true; }
      }
      if (moved) {
        if (fileMoved) this.ctx.reload();            // the bytes changed under the view — repaint them
        await this.refresh();                        // fresh sidecar, log, and a new baseline
      }
    } finally { this.polling = false; }
  }

  // ── verbs ──────────────────────────────────────────────────────────────────────────────────────
  /** A mutating verb: consent first (decision 5), then the request with the fence from the current
   *  status; an `editing-off` refusal re-offers the consent and retries once; a moved fence re-issues
   *  status and retries once by the same args; a second refusal shows verbatim, with Reload when the
   *  store, file, or config moved. Resolves the fresh status, or null when nothing was written. */
  async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {
    if (!(await this.ctx.ensureEditingAllowed())) { this.errors.set(slot, { text: "Nothing written: comments need file editing on.", reload: false }); this.render(); return null; }
    this.busy.add(slot); this.errors.delete(slot); this.render();
    try { return await this.mutateOnce(verb, args, slot, false); }
    finally { this.busy.delete(slot); this.render(); }
  }
  private async mutateOnce(verb: string, args: Record<string, unknown>, slot: string, retried: boolean): Promise<Status | null> {
    const s = this.status;
    const fence = { storeMtimeNs: s && s.storeMtimeNs !== null ? s.storeMtimeNs : "", configMtimeNs: s && s.configMtimeNs !== null ? s.configMtimeNs : "" };
    try {
      const r = await this.request(verb, args, fence);
      this.applyStatus(r);
      return r;
    } catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off") {
        if (await this.ctx.ensureEditingAllowed(e.error)) return this.mutateOnce(verb, args, slot, true);
      } else if (!retried && MOVED.has(e.code)) {
        await this.refresh();
        return this.mutateOnce(verb, args, slot, true);
      }
      this.errors.set(slot, { text: e.error, reload: MOVED.has(e.code) });
      return null;
    }
  }

  // ── Track changes ──────────────────────────────────────────────────────────────────────────────
  onTrackClick(): void {
    const s = this.status;
    if (!s) return;
    if (!s.trackedBy) { this.trackChoice = !this.trackChoice; this.trackStop = false; this.render(); return; }
    if (s.trackedBy.kind === "folder") { this.trackStop = !this.trackStop; this.trackChoice = false; this.render(); return; }
    // a file entry turns off directly; an inherited one is refused by the kernel naming the parent — the row shows it
    void this.mutate("set-tracked", { on: false, scope: "file" }, "track");
  }

  // ── commenting ─────────────────────────────────────────────────────────────────────────────────
  onSelection(sel: Selection): void {
    if (!this.open || this.ctx.mode() === "media" || !sel.rangeCount) return;
    const rect = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    const x = Math.min(Math.max(8, rect.right + 6), window.innerWidth - 90);
    const y = Math.min(Math.max(8, rect.top - 30), window.innerHeight - 34);
    this.float.style.left = x + "px"; this.float.style.top = y + "px";
    this.float.hidden = false;
  }
  private contentRoot(): Element | null {
    const mode = this.ctx.mode();
    if (mode === "media") return null;
    return this.ctx.body().querySelector(mode === "rendered" ? ".fileview-md" : "code.hljs");
  }
  startComment(sel: Selection): void {
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) return;
    const selText = sel.toString();
    const res = this.ctx.mode() === "rendered" ? mapRenderedSelection(sel, root, src) : mapRawSelection(sel, root, src);
    this.openPanel();
    if (res.ok) this.composer = { kind: "comment", range: res.range, quote: res.quote, refusal: null };
    else this.composer = { kind: "comment", range: null, quote: null, refusal: { ...res, selText } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  startFileComment(): void {
    this.composer = { kind: "comment", range: null, quote: null, refusal: null };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  startReply(id: string): void {
    const card = this.cards().find((c) => c.id === id);
    if (!card) return;
    this.openCards.add(id);
    this.composer = { kind: "reply", commentId: id, ref: card.ref };
    this.errors.delete("composer");
    this.repaintPresel();
    this.render();
    this.input.focus();
  }
  closeComposer(): void {
    this.composer = null;
    this.input.value = "";
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
  }
  /** The mapping refused in Rendered: switch to Raw, and when the selected text occurs in the source,
   *  target that passage (the presel mark shows it); otherwise scroll to the block's first line and
   *  leave the note waiting for a Raw selection. */
  switchToRaw(): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.refusal) return;
    this.ctx.setMode("raw");
    const src = this.ctx.text();
    if (src === null) return;
    const r = c.refusal;
    if (r.rawHasQuote && r.selText) {
      const i = src.indexOf(r.selText);
      if (i >= 0) {
        c.range = { start: i, end: i + r.selText.length }; c.quote = r.selText; c.refusal = null;
        this.ctx.scrollToOffset(i);
        this.repaintPresel();
        this.renderComposer();
        this.input.focus();
        return;
      }
    }
    if (typeof r.blockStartLine === "number") this.ctx.scrollToOffset(lineStartOffset(src, r.blockStartLine));
    this.renderComposer();
  }
  async saveComposer(): Promise<void> {
    const c = this.composer;
    const note = this.input.value.trim();
    if (!c || !note) return;
    let r: Status | null;
    if (c.kind === "reply") r = await this.mutate("reply", { commentId: c.commentId, note }, "composer");
    else {
      const args: Record<string, unknown> = { note };
      const src = this.ctx.text();
      if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }
      r = await this.mutate("comment", args, "composer");
    }
    if (r) this.closeComposer();                       // a refusal keeps the note where it was typed
  }

  // ── highlights ─────────────────────────────────────────────────────────────────────────────────
  cards(): Card[] { return this.status ? cardModel(this.status.store, this.status.hunks || []) : []; }
  /** Paint every open comment's anchor over the current view: located → the ring; quote gone but its
   *  context found → the text-changed ring; neither → card only, marked detached. Detached is a
   *  rendering state, never a stored flag. The composer's pending target is painted last. */
  paintAll(): void {
    this.located = new Map();
    this.unpaint(".fc-hl, .fc-presel");                // a status refresh repaints the SAME body: never wrap twice
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) { this.render(); return; }
    const rendered = this.ctx.mode() === "rendered";
    for (const card of this.cards()) {
      if (card.resolved || !card.anchor) continue;
      const loc = locateComment(src, card.anchor);
      let painted = false;
      if (loc.state !== "detached" && loc.range) {
        const cls = "fc-hl" + (loc.state === "context" ? " fc-hl-context" : "");
        const out = rendered ? paintRendered(root, src, loc.range, cls, { act: "fcopen", id: card.id })
          : paintRaw(root, src, loc.range, cls, { act: "fcopen", id: card.id });
        painted = !!out && out.length > 0;
      }
      this.located.set(card.id, { ...loc, painted });
    }
    this.paintPresel(root, src, rendered);
    this.render();
  }
  private paintPresel(root: Element, src: string, rendered: boolean): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.range) return;
    if (rendered) paintRendered(root, src, c.range, "fc-presel"); else paintRaw(root, src, c.range, "fc-presel");
  }
  /** Unwrap painted marks: the text nodes go back in place and the parent is normalized. */
  private unpaint(selector: string): void {
    for (const n of Array.from(this.ctx.body().querySelectorAll(selector))) {
      const p = n.parentNode; if (!p) continue;
      while (n.firstChild) p.insertBefore(n.firstChild, n);
      p.removeChild(n); p.normalize();
    }
  }
  private repaintPresel(): void {
    this.unpaint(".fc-presel");
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src !== null && root) this.paintPresel(root, src, this.ctx.mode() === "rendered");
  }
  goTo(id: string): void {
    const mark = this.ctx.body().querySelector('.fc-hl[data-id="' + id + '"]');
    if (mark) { mark.scrollIntoView({ block: "center" }); return; }
    this.reveal(id);
  }
  /** Reveal: switch to Raw and scroll to the comment's located range — for a comment the Rendered
   *  view could not paint, so the compact card never dead-ends. */
  reveal(id: string): void {
    const loc = this.located.get(id);
    if (!loc || !loc.range) return;
    this.ctx.setMode("raw");
    this.ctx.scrollToOffset(loc.range.start);
  }
  scrollCard(id: string): void {
    this.root?.querySelector('.fc-card[data-id="' + id + '"]')?.scrollIntoView({ block: "nearest" });
  }

  // ── Send to session ────────────────────────────────────────────────────────────────────────────
  /** Fixed sequence (the plan's UX): the message is built from the CURRENT status, then set-tracked
   *  when asked, then fileCommentsSend with `tracked` set to the post-toggle verdict; a refusal at any
   *  step aborts before the send. The comments are already on disk, so a refusal loses nothing. */
  async doSend(): Promise<void> {
    const s = this.status;
    if (!s || this.sending || !this.ctx.sid) return;
    const parts: SendParts = sendParts(s);
    let tracked = !!s.trackedBy;
    this.sending = true; this.errors.delete("send"); this.render();
    try {
      if (this.sendOpts.track && !s.trackedBy) {
        const r = await this.mutate("set-tracked", { on: true, scope: "file" }, "send");
        if (!r) return;
        tracked = !!r.trackedBy;
      }
      const answerTodo = !!this.ctx.todoId && this.sendOpts.todo && !this.todoAnswered;
      const msg: Record<string, unknown> = {
        sid: this.ctx.sid, path: this.ctx.path, tracked, comments: parts.comments,
        accepted: parts.accepted, rejected: parts.rejected, watermark: parts.watermark,
      };
      if (answerTodo) msg.todoId = this.ctx.todoId;
      const reply = await this.requestSend(msg);
      if (answerTodo) this.todoAnswered = true;
      const who = this.sessionName();
      this.sentNote = reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now());
      if (reply.warning) this.errors.set("send", { text: reply.warning, reload: false, warn: true });
      this.sendConfirm = false; this.previewOpen = false;
      await this.refresh();
    } catch (err) {
      this.errors.set("send", { text: (err as { error: string }).error, reload: false });
    } finally { this.sending = false; this.render(); }
  }

  // ── render ─────────────────────────────────────────────────────────────────────────────────────
  render(): void {
    if (!this.root || !this.open) return;
    const s = this.status;
    const { head, cards, send, log } = this.sections;
    if (!this.root.contains(head)) this.root.replaceChildren(head, this.composerBox, cards, send, log);   // built once per open
    head.replaceChildren(this.renderHead(s));
    this.renderComposer();
    cards.replaceChildren(this.renderCards(s));
    send.replaceChildren(this.renderSend(s));
    log.replaceChildren(this.renderLog(s));
  }
  private errRow(slot: string): HTMLElement | null {
    const e = this.errors.get(slot);
    if (!e) return null;
    const row = el("div", "fileview-err fc-err" + (e.warn ? " fc-err-warn" : ""));
    row.dataset.slot = slot;
    row.appendChild(el("span", undefined, e.text));
    if (e.reload) { const b = btn("Reload", "fcreload"); b.dataset.slot = slot; b.title = "Read the file and its comments again"; row.appendChild(b); }
    const x = btn("✕", "fcerrx", "fileview-btn fc-x"); x.dataset.slot = slot; x.setAttribute("aria-label", "Dismiss"); row.appendChild(x);
    return row;
  }
  private loader(slot: string): HTMLElement | null {
    if (!this.busy.has(slot)) return null;
    const w = el("div", "fileview-load fc-load");
    w.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    return w;
  }
  private chip(author: string, authorId: string | null): HTMLElement {
    if (author === "you") return el("span", "fc-chip fc-chip-you", "you");
    const c = authorId && this.colors ? this.colors.get(authorId) : null;
    const chip = el("span", "fc-chip", c ? c.name : author || "unknown");
    if (c && c.color) { chip.style.background = c.color.bg; chip.style.color = c.color.fg; }
    return chip;
  }
  private renderHead(s: Status | null): HTMLElement {
    const head = el("div", "fc-head");
    const row = el("div", "fc-row");
    const t = btn("Track changes", "fctrack", "fileview-btn fc-toggle");
    const tb = s?.trackedBy || null;
    t.dataset.on = tb ? "1" : "0";
    t.setAttribute("aria-pressed", tb ? "true" : "false");
    t.textContent = "Track changes" + (tb ? (tb.kind === "folder" ? " · folder" : tb.kind === "inherited" ? " · inherited" : " · on") : "");
    t.title = tb ? (tb.kind === "inherited" ? "Tracked through " + tb.entry + "; turn it off there" : "Tracked by the entry " + tb.entry + "; click to stop")
      : "Record this session's edits to the file as changes you accept or reject";
    row.appendChild(t);
    row.appendChild(btn("Comment on this file", "fcfile"));
    head.appendChild(row);
    if (this.trackChoice && s) {
      const pick = el("div", "fc-row fc-choice");
      pick.appendChild(el("span", "fc-note", "Track:"));
      pick.appendChild(btn("This file", "fctrackfile"));
      const f = btn("Its folder " + folderOf(this.ctx.path), "fctrackfolder");
      f.title = "Everything under the folder, files not written yet included";
      pick.appendChild(f);
      pick.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(pick);
    }
    if (this.trackStop && s?.trackedBy) {
      const stop = el("div", "fc-row fc-choice");
      stop.appendChild(el("span", "fc-note", "Stop tracking everything under " + s.trackedBy.entry + "?"));
      stop.appendChild(btn("Stop", "fctrackstop"));
      stop.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(stop);
    }
    for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll")]) if (n) head.appendChild(n);
    if (s && s.agentTooling === "absent") {
      head.appendChild(el("div", "fc-warn", "The session cannot reply to comments yet: the track-changents tooling is not linked into ~/.claude on the file's machine. Run romp's install.sh there."));
    }
    return head;
  }
  private renderComposer(): void {
    const c = this.composer;
    const box = this.composerBox;
    box.hidden = !c;
    if (!c) return;
    const ref = this.composerRef;
    ref.replaceChildren();
    if (c.kind === "reply") ref.appendChild(el("span", "fc-note", "Reply on " + c.ref));
    else if (c.refusal) {
      ref.appendChild(el("span", "fc-note fc-refused", c.refusal.reason));
      const sw = btn("Switch to Raw", "fcraw");
      sw.title = c.refusal.rawHasQuote ? "Raw view, with this passage selected" : "Raw view, scrolled to the block; select the passage there";
      ref.appendChild(sw);
    } else if (c.quote) {
      const q = el("span", "fc-quote", c.quote.replace(/\s+/g, " ").trim());
      q.title = c.quote;
      ref.appendChild(el("span", "fc-note", "On "));
      ref.appendChild(q);
    } else ref.appendChild(el("span", "fc-note", "On this file"));
    const acts = this.composerActs;
    acts.replaceChildren(btn("Save", "fcsave"), btn("Cancel", "fccancel"));
    const err = this.composerErr;
    err.replaceChildren(...[this.loader("composer"), this.errRow("composer")].filter((n): n is HTMLElement => !!n));
    if (!box.contains(this.input)) box.replaceChildren(ref, this.input, acts, err);   // built once; the input keeps its focus across renders
  }
  private renderCards(s: Status | null): HTMLElement {
    const list = el("div", "fc-cards");
    const cards = this.cards();
    if (!s) { list.appendChild(el("div", "fc-empty", "Reading the file's comments…")); return list; }
    if (!cards.length) {
      list.appendChild(el("div", "fc-empty", this.ctx.mode() === "media"
        ? "No comments yet. Comment on this file to leave one."
        : "No comments yet. Select a passage and press Comment, or comment on this file."));
      return list;
    }
    const open = cards.filter((c) => !c.resolved), done = cards.filter((c) => c.resolved);
    for (const c of open) list.appendChild(this.renderCard(c));
    if (done.length) {
      const fold = btn((this.resolvedOpen ? "▾ " : "▸ ") + "Resolved (" + done.length + ")", "fcresolved", "fc-sec");
      list.appendChild(fold);
      if (this.resolvedOpen) for (const c of done) list.appendChild(this.renderCard(c));
    }
    return list;
  }
  private renderCard(c: Card): HTMLElement {
    const isOpen = this.openCards.has(c.id);
    const loc = this.located.get(c.id);
    const card = el("div", "fc-card" + (isOpen ? " open" : "") + (loc && loc.state === "detached" ? " fc-card-detached" : ""));
    card.dataset.id = c.id; card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.kind === "passage" ? "“" + c.ref + "”" : c.ref);
    ref.title = c.kind === "passage" ? c.anchor?.quote || c.ref : c.ref;
    if (c.anchor && loc && loc.painted) { ref.dataset.act = "fcgoto"; ref.dataset.id = c.id; ref.classList.add("fc-link"); ref.title = "Scroll to the passage"; }
    head.appendChild(ref);
    if (loc && loc.state === "context") head.appendChild(el("span", "fc-tag", "text changed"));
    if (loc && loc.state === "detached") head.appendChild(el("span", "fc-tag", "detached"));
    if (c.resolved) head.appendChild(el("span", "fc-tag", "resolved"));
    if (c.replies.length && !isOpen) head.appendChild(el("span", "fc-tag fc-count", String(c.replies.length)));
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (!isOpen) { card.appendChild(el("div", "fc-preview", c.body.replace(/\s+/g, " ").trim())); return card; }
    card.appendChild(el("div", "fc-body", c.body));
    if (c.replies.length) {
      const rs = el("div", "fc-replies");
      for (const r of c.replies) {
        const row = el("div", "fc-reply" + (r.author === "you" ? " fc-reply-you" : ""));
        const meta = el("div", "fc-meta");
        meta.appendChild(this.chip(r.author, r.authorId));
        meta.appendChild(el("span", "fc-time", clock(r.ts)));
        row.appendChild(meta);
        row.appendChild(el("div", "fc-body", r.body));
        rs.appendChild(row);
      }
      card.appendChild(rs);
    }
    const acts = el("div", "fc-actions");
    const reply = btn("Reply", "fcreply"); reply.dataset.id = c.id; acts.appendChild(reply);
    const res = btn(c.resolved ? "Reopen" : "Resolve", "fcresolve"); res.dataset.id = c.id; res.dataset.on = c.resolved ? "0" : "1"; acts.appendChild(res);
    const src = this.ctx.text();
    if (c.anchor && loc && loc.range && !loc.painted) {
      const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.id;
      rv.title = "Show the passage in the Raw view" + (src !== null ? " (line " + (rawOffsetToLine(src, loc.range.start) + 1) + ")" : "");
      acts.appendChild(rv);
    }
    card.appendChild(acts);
    for (const n of [this.loader("card:" + c.id), this.errRow("card:" + c.id)]) if (n) card.appendChild(n);
    return card;
  }
  private renderSend(s: Status | null): HTMLElement {
    const box = el("div", "fc-send");
    const n = s ? unsentCount(s.unsent) : 0;
    const b = btn(this.sending ? "Sending…" : "Send to session" + (n ? " (" + n + ")" : ""), "fcsend");
    b.disabled = !s || !n || this.sending || !this.ctx.sid;
    b.title = !this.ctx.sid ? "No session owns this file; open it from a session's link or todo to send"
      : !n ? "Nothing unsent: every comment, reply, and decision has gone" : "Hand everything unsent to the session as one message";
    box.appendChild(b);
    if (this.sendConfirm && s && n && !this.sending) {
      const parts = sendParts(s);
      const cf = el("div", "fc-confirm");
      cf.appendChild(el("div", "fc-note", "This goes to " + this.sessionName() + ":"));
      const ul = el("ul", "fc-list");
      for (const c of parts.comments) {
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", c.desc + ": "));
        li.appendChild(el("span", undefined, c.body.replace(/\s+/g, " ").trim()));
        ul.appendChild(li);
      }
      if (parts.accepted || parts.rejected) ul.appendChild(el("li", undefined, parts.accepted + " accepted, " + parts.rejected + " rejected"));
      cf.appendChild(ul);
      const opts = el("div", "fc-opts");
      if (this.ctx.todoId && !this.todoAnswered) opts.appendChild(this.opt("todo", "answer the todo this file was opened from"));
      if (!s.trackedBy) opts.appendChild(this.opt("track", "turn on tracking so the session's edits come back as changes"));
      if (opts.childNodes.length) cf.appendChild(opts);
      const pv = btn((this.previewOpen ? "▾ " : "▸ ") + "The message", "fcpreview", "fc-sec");
      cf.appendChild(pv);
      if (this.previewOpen) {
        const media = this.ctx.media() === "image" || this.ctx.media() === "pdf";
        const tracked = !!s.trackedBy || this.sendOpts.track;   // the post-toggle verdict the send will carry
        cf.appendChild(el("pre", "fc-msg", buildSendMessage({ absPath: this.ctx.path, comments: parts.comments, accepted: parts.accepted, rejected: parts.rejected, tracked, media })));
      }
      const acts = el("div", "fc-actions");
      acts.appendChild(btn("Send", "fcsendgo", "fileview-btn fc-primary"));
      acts.appendChild(btn("Cancel", "fcsendcancel"));
      cf.appendChild(acts);
      box.appendChild(cf);
    }
    if (this.sentNote) box.appendChild(el("div", "fc-note fc-sent", this.sentNote));
    for (const x of [this.loader("send"), this.errRow("send")]) if (x) box.appendChild(x);
    return box;
  }
  private opt(key: "todo" | "track", label: string): HTMLElement {
    const l = el("label", "fc-opt");
    const cb = el("input") as HTMLInputElement;
    cb.type = "checkbox"; cb.checked = this.sendOpts[key]; cb.dataset.opt = key;
    l.appendChild(cb); l.appendChild(el("span", undefined, label));
    return l;
  }
  private renderLog(s: Status | null): HTMLElement {
    const box = el("div", "fc-log");
    const rows = s?.log || [];
    box.appendChild(btn((this.logOpen ? "▾ " : "▸ ") + "Log" + (rows.length ? " (" + rows.length + (s?.logTruncated ? "+" : "") + ")" : ""), "fclog", "fc-sec"));
    if (!this.logOpen) return box;
    if (!rows.length) { box.appendChild(el("div", "fc-empty", "Nothing yet: sends, decisions, tracking changes, and direct edits land here.")); return box; }
    const nameOf = (sid: string): string | null => {
      if (this.ctx.sid && bareId(this.ctx.sid) === sid) return this.sessionName();
      const c = this.colors ? this.colors.get(sid) : null;
      return c ? c.name : null;
    };
    for (const e of [...rows].reverse()) {
      const row = el("div", "fc-log-row");
      row.appendChild(el("span", "fc-time", clock(e.ts)));
      row.appendChild(el("span", undefined, logRowText(e, nameOf)));
      box.appendChild(row);
    }
    if (s?.logTruncated) box.appendChild(el("div", "fc-note", "Showing the last " + rows.length + " entries."));
    return box;
  }
}

// ── the registry entry ─────────────────────────────────────────────────────────────────────────────
// Mounted hidden; the first `status` answer reveals it with the glance label (a `no-node` refusal never
// does — the gear's File comments row names the machine and the reason). Registered by file-view.ts.
export const fileCommentsAction: FileViewAction = {
  id: "file-comments",
  mount(ctx) {
    const unit = el("span", "fileview-fc");
    unit.hidden = true;
    const b = el("button", "fileview-btn", "Comments") as HTMLButtonElement;
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    unit.appendChild(b);
    new Panel(ctx, b, unit).probe();
    return unit;
  },
};
