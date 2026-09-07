// The file-comments panel's PURE half (plans/file-review.md, Slices 1 and 2): the view model the panel
// renders from a `status` reply — the comment cards, and from Slice 2 the change cards grouped by
// paragraph — the unsent count, the Send-to-session message preview, the Log rows, and the poll's state
// machine. No DOM, no anchor-map import, no fetch — every function here is a
// plain transform over the kernel's reply shapes (the contract sheet's C1/C2), so
// file-comments.test.ts can run them under node with no stand-in at all. file-comments.ts owns the
// DOM and the wire; this module owns what the DOM shows.
//
// The message builder must produce EXACTLY the text the kernel builds for the same parts (C3): the
// kernel's builder and this one are tested against the same literal, and the panel shows this text
// in the send confirm as "what goes" — a preview that differs from the sent message would be a lie.
// Two of the kernel's rules ride along as ports: the path is ONE shell word on the two command lines
// (shWord = _sh_word) and the second "To respond" bullet follows the kernel's text allowlist
// (isTextPath = _is_text_path), never the viewer's own verdict.

import { regionDesc, staleness, type Region, type Staleness } from "./region-geometry";   // pure, like this module

// ── the sidecar and reply shapes (track-changents v3 + the host script's status fields) ────────────
export type Anchor = { quote: string; prefix: string; suffix: string };
/** A region on an image or a PDF page (Slice 3; contract E1): fractions of the natural size, the page for a PDF,
 *  the sha256 of the file's bytes the HOST stamped when the region was drawn (staleness compares it with the
 *  file's current hash), and for a figure embedded in markdown `src` exactly as the embed writes it. */
export type Target = { kind: "image" | "pdf"; region: Region; page?: number; hash?: string; src?: string };
export type StoreReply = { author: string; authorId?: string; ts: number; body?: string; kind?: string; oldText?: string; newText?: string };
export type StoreComment = {
  id: string; author: string; authorId?: string; ts: number; body: string;
  replies?: StoreReply[]; resolved?: boolean; anchor?: Anchor | null; suggestionId?: string; target?: Target;
};
export type Store = {
  v: number; id?: string; path: string; suggestions: unknown[]; comments: StoreComment[];
  detached?: unknown[]; fingerprint?: string;
};
/** The engine's three change kinds (toHunks): an insertion has the new text at curFrom..curTo and no old
 *  text; a deletion is a POINT (curFrom === curTo) with its old text; a substitution has both. */
export type HunkKind = "ins" | "del" | "sub";
export type Hunk = {
  id: string; author: string; ts: number; kind: HunkKind; curFrom: number; curTo: number;
  baseFrom: number; baseTo: number; oldText: string; newText: string; anchor: Anchor | null;
};
export type Unsent = { comments: string[]; replies: Array<{ commentId: string; ts: number }>; accepted: number; rejected: number; watermark: number | null };
export type TrackedBy = { kind: "file" | "folder" | "inherited"; entry: string } | null;
export type LogEntry = { ts: string; kind: string; author: string; [k: string]: unknown };
export type Status = {
  verb: string; root: string | null; storePath: string | null; trackedBy: TrackedBy;
  agentTooling: "present" | "absent"; fileMtimeNs: string; storeMtimeNs: string | null; configMtimeNs: string | null;
  store: Store | null; hunks: Hunk[]; unsent: Unsent; log: LogEntry[]; logTruncated?: boolean;
  /** a non-text file's sha256 (E2); null when the host could not compute it (over its cap); absent from an older host */
  fileHash?: string | null;
  /** a text file: the current sha256 of every figure its region comments name, by `src` as written (E2) */
  embeddedHashes?: Record<string, string | null> | null;
};

const EMPTY_UNSENT: Unsent = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };

/** The number on the Send button: everything the comments log says has not gone yet. */
export function unsentCount(u: Unsent | null | undefined): number {
  if (!u) return 0;
  return (u.comments || []).length + (u.replies || []).length + (u.accepted || 0) + (u.rejected || 0);
}

/** The action-row label — the glance. Plain "Comments" until a sidecar exists; then the open-comment
 *  count, then the pending-change count when there are any. A tracked file with no sidecar yet says so,
 *  since whether a session's writes will come back as changes is the fact the glance is for. */
export function actionLabel(s: Status | null): string {
  if (!s) return "Comments";
  if (!s.store) return s.trackedBy ? "Comments · tracked" : "Comments";
  const open = s.store.comments.filter((c) => !c.resolved).length;
  const n = s.hunks.length;
  return "Comments · " + open + (n ? " · " + n + (n === 1 ? " change" : " changes") : "");
}

// ── the send parts (C2) ────────────────────────────────────────────────────────────────────────────

/** A decision the comments log remembers for change `id`: the accept or reject entry's texts, newest first.
 *  Accept drops the change from the sidecar, so once decided the log is the only place its old and new text
 *  survive (the plan's comments log: "a decision survives the change leaving the sidecar"). */
export function decidedChange(log: LogEntry[] | null | undefined, id: string): { decision: "accepted" | "rejected"; oldText: string; newText: string } | null {
  for (let i = (log || []).length - 1; i >= 0; i--) {
    const e = log![i];
    if (e.kind !== "accept" && e.kind !== "reject" || !Array.isArray(e.changes)) continue;
    for (const ch of e.changes as Array<Record<string, unknown>>) {
      if (ch && typeof ch === "object" && ch.id === id) {
        return { decision: e.kind === "accept" ? "accepted" : "rejected",
          oldText: typeof ch.oldText === "string" ? ch.oldText : "", newText: typeof ch.newText === "string" ? ch.newText : "" };
      }
    }
  }
  return null;
}

/** The parenthetical the kernel prints after "Comment <id>", without parentheses (C2). A comment bound to a
 *  change describes the change while it is pending, and from the log's accept or reject entry after a decision
 *  (a manual Accept before the send would otherwise describe it as "on this file"). */
export function describeComment(c: StoreComment, hunks: Hunk[], log: LogEntry[] = []): string {
  if (c.suggestionId) {
    const h = hunks.find((x) => x.id === c.suggestionId);
    if (h) return 'on your change "' + h.oldText + '" to "' + h.newText + '"';
    const d = decidedChange(log, c.suggestionId);
    if (d) return 'on your change "' + d.oldText + '" to "' + d.newText + '"';
  }
  if (c.target && c.target.region) return "on " + regionDesc(c.target.region, c.target.kind === "pdf" ? c.target.page : null);
  if (c.anchor && typeof c.anchor.quote === "string" && c.anchor.quote) return 'on "' + c.anchor.quote.slice(0, 40) + '"';
  return "on this file";
}

export type SendComment = { id: string; desc: string; body: string };
export type SendParts = { comments: SendComment[]; accepted: number; rejected: number; watermark: number | null };

/** What one Send hands over, derived from the status reply's unsent lists (never from browser state):
 *  each comment with something unsent, its unsent `you` turns joined with a blank line oldest first — the
 *  opening only when the log says it never went, else just the new replies — plus the decision counts
 *  and the watermark (the largest `ts` among what goes). */
export function sendParts(s: Status): SendParts {
  const u = s.unsent || EMPTY_UNSENT;
  const store = s.store;
  const openings = new Set(u.comments || []);
  const replyKeys = new Set((u.replies || []).map((r) => r.commentId + "\0" + r.ts));
  const out: SendComment[] = [];
  let watermark: number | null = null;
  const bump = (ts: number) => { if (typeof ts === "number" && (watermark === null || ts > watermark)) watermark = ts; };
  if (store) {
    const sorted = [...store.comments].sort((a, b) => (a.ts || 0) - (b.ts || 0));
    for (const c of sorted) {
      const turns: string[] = [];
      if (openings.has(c.id)) { turns.push(c.body); bump(c.ts); }
      for (const r of [...(c.replies || [])].sort((a, b) => (a.ts || 0) - (b.ts || 0))) {
        if (typeof r.body !== "string") continue;                 // an edit step has no words to send
        if (replyKeys.has(c.id + "\0" + r.ts)) { turns.push(r.body); bump(r.ts); }
      }
      if (turns.length) out.push({ id: c.id, desc: describeComment(c, s.hunks || [], s.log || []), body: turns.join("\n\n") });
    }
  }
  return { comments: out, accepted: u.accepted || 0, rejected: u.rejected || 0, watermark };
}

/** The counts the send carries and the preview prints (D5): what the log says is unsent plus, when the
 *  confirm's "accept the N pending changes" is checked, the N the send is about to accept — the same A and R
 *  in both places, so the preview is the sent text. */
export function sendCounts(parts: SendParts, acceptPending: boolean, pending: number): { accepted: number; rejected: number } {
  return { accepted: parts.accepted + (acceptPending && pending > 0 ? pending : 0), rejected: parts.rejected };
}

// ── marker hygiene — the kernel's _neutralize_romp_markers, ported unchanged ───────────────────────
// The kernel neutralizes the path and every comment id, desc and body before formatting the message, so
// the sent text never carries a live "<!-- romp-…" opener or a bare "romp-goal-id:" (downstream readers
// key on both: peer-mail and author attribution on the comment form, goal reopening on the bare one).
// The preview must show the same bytes, so the same two substitutions run here, in the same order, with
// the same visible escapes: "<!--" becomes "<!- -" when any whitespace then "romp-" follows, and the colon
// of "romp-goal-id:" becomes ";" (whitespace before it kept). Same patterns as kernel.py's
// _ROMP_MARKER_OPEN_RE and _ROMP_GOALID_BARE_RE; JS's \s and Python's differ only at exotic code points
// (\x1c-\x1f and \x85 are whitespace to Python, \ufeff to JS).
const ROMP_MARKER_OPEN_RE = /<!--(?=\s*romp-)/g;
const ROMP_GOALID_BARE_RE = /(romp-goal-id\s*):/g;

export function neutralizeRompMarkers(text: string): string {
  return String(text ?? "").replace(ROMP_MARKER_OPEN_RE, "<!- -").replace(ROMP_GOALID_BARE_RE, "$1;");
}

// ── one shell word — the kernel's _sh_word (shlex.quote), ported unchanged ─────────────────────────
// The session runs the message's two command lines as written, so the kernel puts the path on them as
// ONE word: an empty string is ''; a word made only of [A-Za-z0-9_@%+=:,./-] passes through unchanged, so
// an ordinary path reads as the plan's own `--file <absPath>`; anything else is wrapped in single quotes,
// each single quote inside it written as '"'"'. Single quotes keep a space from splitting the word and
// leave $, backticks and ; inert (a `Meeting notes.md` used to reach the CLI as …/Meeting plus a stray
// word, and a `;` in a name ran what followed it). The prose keeps the plain path. Same rule as
// shlex.quote with re.ASCII's \w; tests/test_kernel_file_comments_hardening.py pins the kernel's cases
// and file-comments-model-message.test.ts pins this port to the same ones.
const SH_SAFE_RE = /^[A-Za-z0-9_@%+=:,./-]+$/;

export function shWord(s: string): string {
  const t = String(s ?? "");
  if (!t) return "''";
  if (SH_SAFE_RE.test(t)) return t;
  return "'" + t.replace(/'/g, "'\"'\"'") + "'";
}

// ── text or not — the kernel's _is_text_path with its _TEXT_EXT and _TEXT_NAMES, ported unchanged ──
// The kernel decides text vs image/PDF by its own allowlist, never by a client flag (C2), and the second
// "To respond" bullet follows that verdict: track-edit (or edit-normally) on a text file, regenerate on
// anything else. The preview reads the path the same way, so a file the viewer showed as neither image
// nor PDF but the kernel does not call text (a .dat, an .ipynb) previews the bullet the session receives.
// The lists are copied word for word; the test compares them against kernel.py's literals.
export const TEXT_EXT: ReadonlySet<string> = new Set((
  "txt md markdown rst adoc org text log err out diff patch csv tsv"
  + " py pyi rb rs go java kt kts swift c h cc cpp hpp cs m mm scala clj lua pl php r jl dart"
  + " js jsx mjs cjs ts tsx json jsonc json5 yaml yml toml ini cfg conf properties"
  + " html htm xml svg css scss sass less vue svelte astro"
  + " sh bash zsh fish ps1 bat cmd nix tf hcl proto graphql gql sql prisma"
  + " lock mod sum gradle cmake mk make bazel bzl gemspec podspec bats"
).split(" ").filter(Boolean));
export const TEXT_NAMES: ReadonlySet<string> = new Set([
  "makefile", "dockerfile", "jenkinsfile", "procfile", "rakefile", "gemfile", "brewfile",
  "vagrantfile", "caddyfile", "justfile", "license", "licence", "notice", "authors",
  "changelog", "readme", "todo", "codeowners", ".gitignore", ".gitattributes",
  ".dockerignore", ".editorconfig", ".env", ".bashrc", ".zshrc", ".profile",
]);

/** os.path.splitext's extension without its dot: the text after the last dot of `base`, unless every
 *  character before that dot is itself a dot (".bashrc" and "..md" have no extension). */
function extOf(base: string): string {
  const dot = base.lastIndexOf(".");
  if (dot < 0) return "";
  for (let i = 0; i < dot; i++) if (base[i] !== ".") return base.slice(dot + 1);
  return "";
}

/** Is `fp` a path the kernel serves as TEXT? Its basename lowered, then the extension allowlist or the
 *  extensionless names that are text by convention — name-based, like the kernel's. */
export function isTextPath(fp: string): boolean {
  const p = String(fp ?? "");
  const base = p.slice(p.lastIndexOf("/") + 1).toLowerCase();
  return TEXT_EXT.has(extOf(base)) || TEXT_NAMES.has(base);
}

// ── the message (C3) — byte-identical to the kernel's builder ──────────────────────────────────────
export type MessageOpts = {
  absPath: string; comments: SendComment[]; accepted: number; rejected: number;
  tracked: boolean;   // the post-toggle verdict: picks the second bullet on a text file
  /** The viewer's image-or-PDF verdict. NOT consulted: the kernel picks the second bullet by its text
   *  allowlist, not a client flag (C2), so the builder reads the path through isTextPath the same way —
   *  the two verdicts differ on a file the viewer calls neither image nor PDF and the kernel calls not
   *  text. Optional so the panel's call compiles; the panel can stop computing it. */
  media?: boolean;
};

export function buildSendMessage(o: MessageOpts): string {
  // The same fields the kernel neutralizes, so the preview is the sent text byte for byte: the path (it
  // rides the header plain and both command lines as one shell word) and each comment's id, desc and
  // body. The counts are numbers. Text or not is the RAW path's verdict, as the kernel's _is_text_path(p).
  const ap = neutralizeRompMarkers(o.absPath);
  const word = shWord(ap);
  const n = o.comments.length;
  const lines: string[] = ["[obsidian-diff] I left " + n + " comment" + (n === 1 ? "" : "s") + " on " + ap + ".", ""];
  for (const c of o.comments) {
    lines.push("Comment " + neutralizeRompMarkers(c.id) + " (" + neutralizeRompMarkers(c.desc) + "):", neutralizeRompMarkers(c.body), "");
  }
  if (o.accepted + o.rejected > 0) lines.push("I accepted " + o.accepted + " of your changes and rejected " + o.rejected + ".", "");
  let second: string;
  if (!isTextPath(o.absPath)) second = "  • to revise it:       regenerate the file with normal writes; never run track-edit on it";
  else if (o.tracked) second = "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file " + word + ' --thread <id> --old "<exact text>" --new "<replacement>"';
  else second = "  • to revise the text: edit the file normally, then say what you changed with the reply command above";
  lines.push(
    "To respond:",
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file " + word + ' --thread <id> --note "<your reply>"',
    second,
    "",
    "When you have addressed these, ask me for another look the same way you asked for this one,",
    "naming the file.",
  );
  return lines.join("\n") + "\n";
}

// ── region comments (Slice 3) ──────────────────────────────────────────────────────────────────────
/** The `target` a `comment` or `retarget` sends: the kind, the fractions, and for an embedded figure the embed's
 *  `src` as written; with a `page` (1-based) the region is on a PDF page (F4) — kind "pdf", the page, never a src
 *  (a PDF is always a file of its own). Never a hash — the host stamps that from the bytes it reads (E1). */
export function regionTarget(region: Region, src: string | null, page: number | null = null): Target {
  if (page) return { kind: "pdf", region, page };
  const t: Target = { kind: "image", region };
  if (src) t.src = src;
  return t;
}

/** Whether a region comment's image still has the bytes it was drawn on (E2): a standalone image compares the
 *  stored hash with the status's `fileHash`; an embedded figure with `embeddedHashes[src]`. Unknown when either
 *  side is missing — an older host, a file over the hash cap, a comment written without a hash. */
export function regionState(target: Target | null | undefined, s: Pick<Status, "fileHash" | "embeddedHashes"> | null | undefined): Staleness {
  if (!target || !s) return "unknown";
  const current = target.src ? (s.embeddedHashes ? s.embeddedHashes[target.src] : undefined) : s.fileHash;
  return staleness(target.hash, current);
}

// ── the card model ─────────────────────────────────────────────────────────────────────────────────
export type CardKind = "passage" | "file" | "change" | "region";
/** One turn under a comment: words (a reply), or a revision — the session's `track-edit --thread` records
 *  its edit as a reply with no body and the old and new text instead (the VS Code host's weave), and the
 *  card shows it as a row of its own, in `ts` order among the words. */
export type CardTurn =
  | { kind: "msg"; author: string; authorId: string | null; ts: number; body: string }
  | { kind: "rev"; author: string; authorId: string | null; ts: number; oldText: string; newText: string };
export type Card = {
  id: string; author: string; authorId: string | null; ts: number; body: string; resolved: boolean;
  kind: CardKind; ref: string; anchor: Anchor | null; hunk: Hunk | null; target: Target | null;
  /** for a comment bound to a change the log has decided: which way, so the card can say so */
  decision: "accepted" | "rejected" | null;
  replies: CardTurn[];
};

const oneLine = (s: string, max: number): string => {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1) + "…" : t;
};

/** One card per comment, oldest first, from the sidecar and the engine's hunks — no card model
 *  crosses the wire. `ref` is the collapsed card's one-line reference (the quote, the change, the
 *  region, or "this file"); the message's `desc` is describeComment's job, kept separate on purpose.
 *  A comment bound to a PENDING change (`hunk` set) is shown on that change's card (changeCards), not in
 *  the comment list; once the change is decided, `hunk` is null, `decision` says which way from the log,
 *  and the card stands on its own again with the change's texts as its reference. */
export function cardModel(store: Store | null, hunks: Hunk[], log: LogEntry[] = []): Card[] {
  if (!store) return [];
  return [...store.comments].sort((a, b) => (a.ts || 0) - (b.ts || 0)).map((c) => {
    const hunk = c.suggestionId ? hunks.find((h) => h.id === c.suggestionId) || null : null;
    const decided = !hunk && c.suggestionId ? decidedChange(log, c.suggestionId) : null;
    const target = c.target && c.target.region ? c.target : null;
    const anchor = c.anchor && typeof c.anchor.quote === "string" ? c.anchor : null;
    let kind: CardKind; let ref: string;
    if (hunk) { kind = "change"; ref = oneLine(hunk.oldText, 30) + " → " + oneLine(hunk.newText, 30); }
    else if (decided) { kind = "change"; ref = oneLine(decided.oldText, 30) + " → " + oneLine(decided.newText, 30); }
    else if (target) { kind = "region"; ref = describeComment(c, hunks).replace(/^on /, ""); }
    else if (anchor && anchor.quote) { kind = "passage"; ref = oneLine(anchor.quote, 72); }
    else { kind = "file"; ref = "this file"; }
    return {
      id: c.id, author: c.author, authorId: c.authorId || null, ts: c.ts, body: c.body, resolved: !!c.resolved,
      kind, ref, anchor, hunk, target, decision: decided ? decided.decision : null,
      replies: (c.replies || []).map((r): CardTurn | null => {
        if (typeof r.body === "string") return { kind: "msg", author: r.author, authorId: r.authorId || null, ts: r.ts, body: r.body };
        if (r.kind === "edit") return { kind: "rev", author: r.author, authorId: r.authorId || null, ts: r.ts, oldText: r.oldText || "", newText: r.newText || "" };
        return null;                                   // neither words nor an edit: nothing to show
      }).filter((t): t is CardTurn => t !== null).sort((a, b) => (a.ts || 0) - (b.ts || 0)),
    };
  });
}

// ── the change cards (Slice 2) ──────────────────────────────────────────────────────────────────────
// One card per pending change (a hunk from the engine's toHunks), ordered by its place in the current text,
// with the comments bound to it (suggestionId) ON the card, and grouped by the paragraph it falls in — the
// VS Code host's buildCards idea over the kernel's `store` + `hunks` + the viewer's text, with the buttons
// that host deliberately lacks added by the panel. Nothing here touches the DOM.
export type ChangeCard = {
  /** the expand key and the card's data-id — prefixed so a change id and a comment id can never collide */
  key: string;
  id: string; kind: HunkKind; author: string; authorId: string | null; ts: number;
  curFrom: number; curTo: number; oldText: string; newText: string;
  /** the collapsed card's one line: `old → new`, `added new`, or `removed old` */
  ref: string;
  /** the comments bound to this change, oldest first, each with its turns */
  comments: Card[];
};
export type ChangeGroup = { key: string; title: string; start: number; end: number; changes: ChangeCard[] };
/** Groups beyond this many collapse behind one "… N more changes" row (D5). */
export const GROUP_LIMIT = 3;

/** The sidecar record's authorId for change `id` — toHunks drops it, and the session colour map is keyed by it. */
export function authorIdOf(store: Store | null, id: string): string | null {
  for (const s of store ? store.suggestions : []) {
    if (s && typeof s === "object" && (s as { id?: unknown }).id === id) {
      const a = (s as { authorId?: unknown }).authorId;
      return typeof a === "string" && a ? a : null;
    }
  }
  return null;
}

export function changeRef(h: { kind: HunkKind; oldText: string; newText: string }): string {
  if (h.kind === "ins") return "added " + oneLine(h.newText, 60);
  if (h.kind === "del") return "removed " + oneLine(h.oldText, 60);
  return oneLine(h.oldText, 30) + " → " + oneLine(h.newText, 30);
}

export function changeCards(store: Store | null, hunks: Hunk[], log: LogEntry[] = []): ChangeCard[] {
  const bound = cardModel(store, hunks, log).filter((c) => c.hunk !== null);
  return [...hunks].sort((a, b) => a.curFrom - b.curFrom || (a.ts || 0) - (b.ts || 0)).map((h) => ({
    key: "chg:" + h.id, id: h.id, kind: h.kind, author: h.author, authorId: authorIdOf(store, h.id), ts: h.ts,
    curFrom: h.curFrom, curTo: h.curTo, oldText: h.oldText, newText: h.newText, ref: changeRef(h),
    comments: bound.filter((c) => c.hunk!.id === h.id),
  }));
}

/** The [start, end) of the paragraph holding `pos`: the maximal run of non-blank lines around it (the display
 *  planner's own rule, so a group here is the paragraph the other hosts would merge). A blank line is its own
 *  empty paragraph. */
export function paragraphAt(text: string, pos: number): { start: number; end: number } {
  const p = Math.max(0, Math.min(pos, text.length));
  let start = text.lastIndexOf("\n", p - 1) + 1;
  const nl = text.indexOf("\n", p);
  let end = nl === -1 ? text.length : nl;
  const blank = (a: number, b: number) => /^\s*$/.test(text.slice(a, b));
  if (blank(start, end)) return { start, end };
  while (start > 0) {
    const prevEnd = start - 1;
    const prevStart = text.lastIndexOf("\n", prevEnd - 1) + 1;
    if (blank(prevStart, prevEnd)) break;
    start = prevStart;
  }
  while (end < text.length) {
    const nextStart = end + 1;
    const nn = text.indexOf("\n", nextStart);
    const nextEnd = nn === -1 ? text.length : nn;
    if (nextStart > text.length || blank(nextStart, nextEnd)) break;
    end = nextEnd;
  }
  return { start, end };
}

/** The change cards grouped by paragraph, in text order; a group is named by its paragraph's first line,
 *  trimmed to 60 characters, or by its line number when the paragraph is blank (a deletion at an empty
 *  line). With no text to read (media, or the fetch not landed) every change is one unnamed group. */
export function changeGroups(cards: ChangeCard[], text: string | null): ChangeGroup[] {
  if (!cards.length) return [];
  if (text === null) return [{ key: "all", title: "", start: 0, end: 0, changes: cards }];
  const out: ChangeGroup[] = [];
  for (const c of cards) {
    const pr = paragraphAt(text, c.curFrom);
    const last = out[out.length - 1];
    if (last && last.start === pr.start && last.end === pr.end) { last.changes.push(c); continue; }
    const first = text.slice(pr.start, pr.end).split("\n").map((l) => l.trim()).find((l) => l) || "";
    const line = (text.slice(0, pr.start).match(/\n/g) || []).length + 1;
    out.push({ key: pr.start + "-" + pr.end, title: first ? oneLine(first, 60) : "line " + line, start: pr.start, end: pr.end, changes: [c] });
  }
  return out;
}

/** Progressive disclosure over the groups: the first GROUP_LIMIT show; the rest fold behind one row unless
 *  `expanded`. `hiddenChanges` is the row's N (changes, not groups — the count the person acts on). */
export function foldGroups(groups: ChangeGroup[], expanded: boolean): { shown: ChangeGroup[]; hidden: ChangeGroup[]; hiddenChanges: number } {
  if (expanded || groups.length <= GROUP_LIMIT) return { shown: groups, hidden: [], hiddenChanges: 0 };
  const shown = groups.slice(0, GROUP_LIMIT), hidden = groups.slice(GROUP_LIMIT);
  return { shown, hidden, hiddenChanges: hidden.reduce((n, g) => n + g.changes.length, 0) };
}

/** The fold row's text: "… 4 more changes". */
export function moreChangesLabel(n: number): string {
  return "… " + plural(n, "more change", "more changes");
}

// ── the Log section ────────────────────────────────────────────────────────────────────────────────
const plural = (n: number, one: string, many: string): string => n + " " + (n === 1 ? one : many);

/** One line per comments-log entry. `nameOf` turns a sid into the session's name when the panel knows it. */
export function logRowText(e: LogEntry, nameOf: (sid: string) => string | null = () => null): string {
  const k = e.kind;
  if (k === "send") {
    const ids = Array.isArray(e.comments) ? (e.comments as unknown[]).length : 0;
    const sid = typeof e.sid === "string" ? e.sid : "";
    const who = (typeof e.sessionName === "string" && e.sessionName) || (sid && nameOf(sid)) || (sid ? sid.slice(0, 8) : "the session");
    let t = "Sent " + plural(ids, "comment", "comments") + " to " + who;
    const acc = typeof e.accepted === "number" ? e.accepted : 0;
    const rej = typeof e.rejected === "number" ? e.rejected : 0;
    if (acc || rej) t += " with " + plural(acc, "accept", "accepts") + " and " + plural(rej, "reject", "rejects");
    return e.queued ? t + " (queued until the session wakes)" : t;
  }
  if (k === "accept" || k === "reject") {
    const n = Array.isArray(e.ids) ? (e.ids as unknown[]).length : Array.isArray(e.changes) ? (e.changes as unknown[]).length : 1;
    return (k === "accept" ? "Accepted " : "Rejected ") + plural(n, "change", "changes");
  }
  if (k === "set-tracked") {
    const entry = typeof e.entry === "string" ? e.entry : "";
    if (e.on === true) return "Track changes on" + (entry ? " for " + entry : "");
    if (e.on === false) return "Track changes off" + (entry ? " for " + entry : "");
    return "Track changes changed" + (entry ? " for " + entry : "");
  }
  if (k === "edit") {
    const s = (e.summary && typeof e.summary === "object" ? e.summary : e) as Record<string, unknown>;
    const b = typeof s.bytesBefore === "number" ? s.bytesBefore : null;
    const a = typeof s.bytesAfter === "number" ? s.bytesAfter : null;
    return "Edited the file directly" + (b !== null && a !== null ? " (" + b + " → " + a + " bytes)" : "");
  }
  return String(k || "entry");
}

// ── the poll's state machine ───────────────────────────────────────────────────────────────────────
// Per target the state is one of: a mtime string, the value "absent" (a 404 — so absent→present is a
// transition like any other), or unknown with a status. Every fileCommentsResult supplies the baseline,
// so the person's own writes never fire the poll; a 413/415 stops the poll on that target.
export const ABSENT = "absent";
export type PollBaseline = { file: string; store: string; config: string };
export type HeadVerdict = { kind: "value"; value: string } | { kind: "stop"; status: number } | { kind: "unknown"; status: number };

export function pollBaseline(s: Status): PollBaseline {
  return { file: s.fileMtimeNs || "", store: s.storeMtimeNs === null || s.storeMtimeNs === undefined ? ABSENT : s.storeMtimeNs,
    config: s.configMtimeNs === null || s.configMtimeNs === undefined ? ABSENT : s.configMtimeNs };
}

export function headVerdict(status: number, mtimeNs: string | null): HeadVerdict {
  if (status === 200) return mtimeNs ? { kind: "value", value: mtimeNs } : { kind: "unknown", status };
  if (status === 404) return { kind: "value", value: ABSENT };
  if (status === 413 || status === 415) return { kind: "stop", status };
  return { kind: "unknown", status };
}

/** The three HEAD targets: the file, the sidecar the kernel named (never a client-computed sidecar path),
 *  and the project's config.json beside it; a file with no project root polls the file alone. */
export function pollTargets(s: Status, path: string): { file: string; store: string | null; config: string | null } {
  return { file: path, store: s.storePath || null, config: s.root ? s.root.replace(/\/$/, "") + "/.trackchanges/config.json" : null };
}

/** Mtimes are compared as STRINGS: ~1.7e18 ns exceeds JS's safe integers, so a number would round two
 *  distinct writes onto one value. */
export function mtimeMoved(baseline: string, seen: string): boolean {
  return baseline !== seen;
}

// ── small helpers the panel and its tests share ────────────────────────────────────────────────────
/** Why Edit refuses while changes are pending: a raw save over pending changes would move their offsets, so
 *  the person accepts or rejects them first (Slice 2 wording; the session's own track-edit still works). */
export function editBlockedReason(hunks: Hunk[]): string | null {
  const n = hunks.length;
  if (!n) return null;
  return plural(n, "change is", "changes are") + " pending in this file, so Edit is off here: a direct edit would move "
    + (n === 1 ? "it" : "them") + ". Accept or reject " + (n === 1 ? "the change" : "the " + n + " changes")
    + " first; the session's own track-edit still works.";
}

// ── editing over pending changes (Slice 5) ─────────────────────────────────────────────────────────
/** One decision taken inside the editor: the change's id and its two texts as the record held them then. */
export type EditDecision = { id: string; oldText: string; newText: string };
/** The editor's decisions since it mounted, net of undo, as its handle reports them. */
export type EditDecisions = { accepted: EditDecision[]; rejected: EditDecision[] };

/** The change records the editor carries as marks: the sidecar's own records, as the status holds them (the
 *  storage format's array; the panel never reads inside them). [] with no sidecar. */
export function pendingRecords(store: Store | null): unknown[] {
  return store && Array.isArray(store.suggestions) ? store.suggestions : [];
}

/** The session id behind an author label on the file's pending changes: the editor's marks ask for a colour by the
 *  record's `author` (the label), and the colour map is keyed by session id. null when no record carries the label. */
export function authorIdByLabel(store: Store | null, author: string): string | null {
  for (const s of pendingRecords(store)) {
    if (s && typeof s === "object" && (s as { author?: unknown }).author === author) {
      const a = (s as { authorId?: unknown }).authorId;
      return typeof a === "string" && a ? a : null;
    }
  }
  return null;
}

/** The `save` verb's arguments (plans/file-review.md, Slice 5): the whole new text, the records as the editor's field
 *  holds them after the person's typing remapped them, and the decisions taken in the editor. Built here so the
 *  panel speaks the person's words and the wire keeps the format's. */
export function saveArgs(content: string, records: unknown[], decided: EditDecisions): Record<string, unknown> {
  return { content, suggestions: records, accepted: decided.accepted, rejected: decided.rejected };
}

/** Two record lists that hold the same changes: the same records in the same order, field for field. The panel
 *  compares what rode into the editor with what the sidecar holds after a `store-moved` refusal — a reply a
 *  session wrote mid-edit moves the sidecar without touching the records, and that save may go through. */
export function sameRecords(a: unknown[], b: unknown[]): boolean {
  return a.length === b.length && JSON.stringify(a) === JSON.stringify(b);
}

/** The panel's row while the file changes on disk under an edit (the poll saw it move; the viewer's reload is a
 *  no-op in edit mode, so nothing repaints over the person's text). Named after what happens next. */
export const MOVED_UNDER_EDIT = "The file changed on disk while you were editing it. Save will refuse and offer Reload; "
  + "Cancel shows the file as it is now.";

/** The source offset where 0-based line `line` starts (for the mapping refusal's scroll-to-block offer). */
export function lineStartOffset(source: string, line: number): number {
  let at = 0;
  for (let i = 0; i < line; i++) {
    const nl = source.indexOf("\n", at);
    if (nl < 0) return source.length;
    at = nl + 1;
  }
  return at;
}

/** The folder a folder-scope toggle names in its confirm: the file's directory, with a trailing slash. */
export function folderOf(path: string): string {
  const cut = path.lastIndexOf("/");
  return cut > 0 ? path.slice(0, cut + 1) : "/";
}
