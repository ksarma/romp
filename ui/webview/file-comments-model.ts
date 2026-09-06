// The file-comments panel's PURE half (plans/file-review.md, Slice 1): the view model the panel
// renders from a `status` reply, the unsent count, the Send-to-session message preview, the Log rows,
// and the poll's state machine. No DOM, no anchor-map import, no fetch — every function here is a
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

// ── the sidecar and reply shapes (track-changents v3 + the host script's status fields) ────────────
export type Anchor = { quote: string; prefix: string; suffix: string };
export type Target = { kind: "image" | "pdf"; region: { x: number; y: number; w: number; h: number }; page?: number; hash?: string };
export type StoreReply = { author: string; authorId?: string; ts: number; body?: string; kind?: string; oldText?: string; newText?: string };
export type StoreComment = {
  id: string; author: string; authorId?: string; ts: number; body: string;
  replies?: StoreReply[]; resolved?: boolean; anchor?: Anchor | null; suggestionId?: string; target?: Target;
};
export type Store = {
  v: number; id?: string; path: string; suggestions: unknown[]; comments: StoreComment[];
  detached?: unknown[]; fingerprint?: string;
};
export type Hunk = {
  id: string; author: string; ts: number; kind: string; curFrom: number; curTo: number;
  baseFrom: number; baseTo: number; oldText: string; newText: string; anchor: Anchor | null;
};
export type Unsent = { comments: string[]; replies: Array<{ commentId: string; ts: number }>; accepted: number; rejected: number; watermark: number | null };
export type TrackedBy = { kind: "file" | "folder" | "inherited"; entry: string } | null;
export type LogEntry = { ts: string; kind: string; author: string; [k: string]: unknown };
export type Status = {
  verb: string; root: string | null; storePath: string | null; trackedBy: TrackedBy;
  agentTooling: "present" | "absent"; fileMtimeNs: string; storeMtimeNs: string | null; configMtimeNs: string | null;
  store: Store | null; hunks: Hunk[]; unsent: Unsent; log: LogEntry[]; logTruncated?: boolean;
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
const num = (v: number): string => (Number.isInteger(v) ? String(v) : v.toFixed(2));

/** The parenthetical the kernel prints after "Comment <id>", without parentheses (C2). */
export function describeComment(c: StoreComment, hunks: Hunk[]): string {
  if (c.suggestionId) {
    const h = hunks.find((x) => x.id === c.suggestionId);
    if (h) return 'on your change "' + h.oldText + '" to "' + h.newText + '"';
  }
  if (c.target && c.target.region) {
    const r = c.target.region;
    const at = "on the region at " + num(r.x) + ", " + num(r.y) + ", " + num(r.w) + ", " + num(r.h);
    return c.target.kind === "pdf" && c.target.page ? at + " of page " + c.target.page : at;
  }
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
      if (turns.length) out.push({ id: c.id, desc: describeComment(c, s.hunks || []), body: turns.join("\n\n") });
    }
  }
  return { comments: out, accepted: u.accepted || 0, rejected: u.rejected || 0, watermark };
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

// ── the card model ─────────────────────────────────────────────────────────────────────────────────
export type CardKind = "passage" | "file" | "change" | "region";
export type Card = {
  id: string; author: string; authorId: string | null; ts: number; body: string; resolved: boolean;
  kind: CardKind; ref: string; anchor: Anchor | null; hunk: Hunk | null; target: Target | null;
  replies: Array<{ author: string; authorId: string | null; ts: number; body: string }>;
};

const oneLine = (s: string, max: number): string => {
  const t = s.replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1) + "…" : t;
};

/** One card per comment, oldest first, from the sidecar and the engine's hunks — no card model
 *  crosses the wire. `ref` is the collapsed card's one-line reference (the quote, the change, the
 *  region, or "this file"); the message's `desc` is describeComment's job, kept separate on purpose. */
export function cardModel(store: Store | null, hunks: Hunk[]): Card[] {
  if (!store) return [];
  return [...store.comments].sort((a, b) => (a.ts || 0) - (b.ts || 0)).map((c) => {
    const hunk = c.suggestionId ? hunks.find((h) => h.id === c.suggestionId) || null : null;
    const target = c.target && c.target.region ? c.target : null;
    const anchor = c.anchor && typeof c.anchor.quote === "string" ? c.anchor : null;
    let kind: CardKind; let ref: string;
    if (hunk) { kind = "change"; ref = oneLine(hunk.oldText, 30) + " → " + oneLine(hunk.newText, 30); }
    else if (target) { kind = "region"; ref = describeComment(c, hunks).replace(/^on /, ""); }
    else if (anchor && anchor.quote) { kind = "passage"; ref = oneLine(anchor.quote, 72); }
    else { kind = "file"; ref = "this file"; }
    return {
      id: c.id, author: c.author, authorId: c.authorId || null, ts: c.ts, body: c.body, resolved: !!c.resolved,
      kind, ref, anchor, hunk, target,
      replies: (c.replies || []).filter((r) => typeof r.body === "string")
        .map((r) => ({ author: r.author, authorId: r.authorId || null, ts: r.ts, body: r.body as string })),
    };
  });
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
/** Why Edit refuses while changes are pending (Slice 1 wording: accept/reject come next; track-edit still works). */
export function editBlockedReason(hunks: Hunk[]): string | null {
  const n = hunks.length;
  if (!n) return null;
  return plural(n, "change is", "changes are") + " pending in this file, so Edit is off here: a direct edit would move "
    + (n === 1 ? "it" : "them") + ". Accept and reject arrive with the next update; the session's own track-edit still works.";
}

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
