// File comments and tracked changes — the viewer's Comments panel (plans/file-review.md, Slices 1 and 2).
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
//   • A session's pending changes (Slice 2) are cards too: one per change, grouped by the paragraph it
//     falls in, with Accept, Reject, Reply (a comment bound to the change, so the session's answering
//     track-edit revisions fold into it) and Reveal; the comments bound to a change sit ON its card. Past
//     three groups the rest fold behind one row. The changes are also marked inline — insertions tinted,
//     deletions struck at their point in Raw — through anchor-map's change painters (contract D4), and a
//     click on a mark opens its card. Accept and Reject fence on the sidecar's mtime; Reject, which rewrites
//     the file, also fences on the file's mtime and then reloads the view, since the bytes changed under it.
//   • A region on an image (Slice 3) is a comment too: the overlays file-comments-regions.ts puts over the media
//     body's picture and over every figure in rendered markdown take a drag and paint each region comment as a
//     rectangle placed by percentages, dashed once the image's bytes changed under it (the host's hash against
//     the stored one). The card shows the region cut from the picture and offers Re-place, which retargets the
//     comment to the next region drawn. Desktop only; a coarse pointer reads and comments on the whole file. A figure
//     in rendered markdown is wrapped by its overlay only while the panel is open or the figure has a rectangle to show
//     (paintRegions): closed, with nothing to show, the author's own layout of the page stands.
//   • The kernel does the disk work on the OWNING kernel (the `fileComments` op runs a node host
//     script over the vendored track-changents store); this module renders JSON and never holds a
//     sidecar it writes back. Both ops carry `sid`, so federation routes a remote session's file to
//     the kernel that owns the disk with no new relay code.
//   • Change awareness by POLLING (2.5 s while the panel is open and the tab visible): HEAD /file on
//     the file, the sidecar the kernel named, and the project's config.json, comparing X-Romp-Mtime-Ns
//     as STRINGS — and on every figure a text file's region comments name, against the poll's own last
//     reading (a regenerated figure moves none of the three; tick). The Files pane has no filesystem
//     watcher; the poll stands in for that event, and the person's own writes never fire it because every
//     verb reply re-baselines it. Replies land in the
//     order their asks were issued (applyStatus): the kernel runs each ask concurrently and answers when
//     it finishes, and a status that read the disk before a write — asked before it, or asked while it was
//     in flight — must not put the panel back a step once the write's reply is showing.
//   • The panel's controls hang off the viewer's body row, which also holds the FILE's rendered markup; an
//     activation is routed only when the panel made the element (own / owns), never for a data-act the
//     file's author wrote.
//   • What is unsent is derived from the comments log on the owning kernel, never from browser state
//     (decision 10): the `status` reply carries it, the button's count is that number.
//   • Every write sits behind the one file-editing consent, shared with Save (decision 5).
// The pure half (view model, message preview, poll verdicts) is file-comments-model.ts; the
// selection→anchor mapping and the highlight painters are anchor-map.ts (contract C4).
//
// This module imports only TYPES from file-view.ts and is registered there (registerFileViewAction
// in file-view.ts), so the two never form a runtime import cycle.
import type { FileViewAction, FileViewActionCtx, FileViewIdentity } from "./file-view";
import { delegate, flash, type ActionHandler } from "./actions";
import { fileUrl } from "./preview";
import { kernelUrl } from "./media";
import { hostOf, bareId } from "./host-prefix";
import { mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered, rawOffsetToLine } from "./anchor-map";
import { paintChangesRaw, paintChangesRendered, unpaintChanges } from "./anchor-map";   // the change painters (contract D4)
import type { MapRefusal, SourceRange, Located, ChangePaint } from "./anchor-map";
import {
  type Status, type Card, type CardTurn, type ChangeCard, type ChangeGroup, type SendParts, type Target, actionLabel, cardModel, changeCards, changeGroups,
  foldGroups, moreChangesLabel, authorIdOf, GROUP_LIMIT, sendParts, sendCounts, buildSendMessage, unsentCount,
  logRowText, pollBaseline, pollTargets, headVerdict, mtimeMoved, editBlockedReason, lineStartOffset, folderOf,
  regionTarget, regionState, figureTargets, figuresMoved, type PollBaseline, type FigureBaseline, type HeadVerdict,
} from "./file-comments-model";
import { RegionLayer, cropThumb, isCoarsePointer, type RegionMark } from "./file-comments-regions";   // the overlays (Slice 3, contract E5)
import { regionDesc, type Region } from "./region-geometry";

const POLL_MS = 2500;
const MOVED = new Set(["store-moved", "file-moved", "config-moved"]);
// The verbs that rewrite the FILE, not only the sidecar (reject applies the engine's reverse edits): they
// fence on the file's mtime as the panel last saw it, so a `track-edit` landing mid-round refuses `file-moved`
// instead of reverting over it, and after one succeeds the panel reloads the view — the bytes changed under
// it, and the poll will never notice, since every reply re-baselines it (the plan's own rule).
const FILE_VERBS = new Set(["reject", "reject-all"]);
// How long a `status` ask may stay unanswered before the panel says so. A kernel that has the op answers
// within its own bound: the host script is cut off at 10 s (contract C2, _FILE_COMMENTS_TIMEOUT) and the
// refusal is sent then, so an ask still open past that plus the relay was never received by a kernel with
// the handler — a kernel from before this feature matches no `type` and sends nothing, not even a warn, and
// federation's drop notice covers only an UNREACHABLE host, not a reachable one that has no answer. There is
// no event to key on because the older kernel emits none; the timer speaks only when the answer never comes
// (feed.ts's redistill watch is the same shape, and ui/CLAUDE.md wants every wait to have a backstop).
// `status` only: a mutating verb that is failed here could have landed on disk, and the kept note would
// invite a duplicate — those keep waiting for the kernel's own answer.
const STATUS_DEADLINE_MS = 15000;
// One send answers a todo (decision 28): a todo naming several files is answered by the FIRST send, and
// later sends for its other files show no checkbox. A viewer is built per open, so the memory of which
// todos THIS page has sent for lives at module level — a second file opened from the same todo, a Reload
// (which re-opens with the same todoId), or the Reply modal's other link all find it. Another device or
// document has no view of this set; the kernel's own settled check (plan: the reply warns, nothing is
// stamped) stays the backstop there.
const answeredTodos = new Set<string>();

// ── image embeds: the source text behind a rendered <img> ─────────────────────────────────────────
// A figure in a markdown file is commented on through its embed line (the plan's Images and PDFs): in
// Rendered view a click on the picture offers Comment, and the anchor is the embed's source text. The
// mapping walk records no positions for an image (it renders no text), so the embed is found here from
// the picture's own destination (pictureDest: the authored spelling the viewer kept beside a src it
// rewrote through /file, else `src` itself): every embed form the source can hold, in order, fenced code
// skipped, matched against the attribute marked emitted (which percent-encodes the destination).
export type ImageEmbed = { start: number; end: number; dest: string };
const LABEL = "(?:\\\\.|[^\\[\\]\\\\])*";
const IMG_INLINE = new RegExp("!\\[(" + LABEL + ")\\]\\([ \\t]*(?:<([^<>\\n]*)>|([^\\s()]*(?:\\([^\\s()]*\\)[^\\s()]*)*))(?:[ \\t]+(?:\"[^\"]*\"|'[^']*'|\\([^()]*\\)))?[ \\t]*\\)", "g");
const IMG_FULL_REF = new RegExp("!\\[(" + LABEL + ")\\]\\[(" + LABEL + ")\\]", "g");
const IMG_SHORT_REF = new RegExp("!\\[(" + LABEL + ")\\](?![\\[(])", "g");
const IMG_HTML = /<img\b[^>]*?\bsrc[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>/gi;
const REF_DEF = /^ {0,3}\[((?:\\.|[^\[\]\\])+)\]:[ \t]*<?([^\s>]+)>?/gm;
const normLabel = (s: string): string => s.trim().replace(/\s+/g, " ").toLowerCase();
/** Offsets of the source's fenced code blocks, [start, end): an embed written inside one renders as text. */
function fencedRanges(src: string): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let open: { ch: string; n: number; at: number } | null = null;
  let at = 0;
  for (const line of src.split("\n")) {
    const m = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (m) {
      if (!open) open = { ch: m[1][0], n: m[1].length, at };
      else if (m[1][0] === open.ch && m[1].length >= open.n && /^\s*$/.test(line.slice(m[0].length))) { out.push([open.at, at + line.length]); open = null; }
    }
    at += line.length + 1;
  }
  if (open) out.push([open.at, src.length]);
  return out;
}
/** Every image embed in the source, in order: `![alt](dest "title")`, `![alt][ref]` and `![ref]` resolved
 *  through `[ref]: dest` definitions, and a raw `<img src>` tag. Fenced code is skipped. */
export function imageEmbeds(src: string): ImageEmbed[] {
  const fences = fencedRanges(src);
  const inFence = (i: number): boolean => fences.some(([a, b]) => i >= a && i < b);
  const defs = new Map<string, string>();
  let m: RegExpExecArray | null;
  REF_DEF.lastIndex = 0;
  while ((m = REF_DEF.exec(src))) if (!inFence(m.index)) defs.set(normLabel(m[1]), m[2]);
  const out: ImageEmbed[] = [];
  const push = (start: number, len: number, dest: string | undefined): void => {
    if (dest !== undefined && !inFence(start)) out.push({ start, end: start + len, dest });
  };
  for (const re of [IMG_INLINE, IMG_FULL_REF, IMG_SHORT_REF, IMG_HTML]) re.lastIndex = 0;
  while ((m = IMG_INLINE.exec(src))) push(m.index, m[0].length, m[2] ?? m[3] ?? "");
  while ((m = IMG_FULL_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[2] || m[1])));
  while ((m = IMG_SHORT_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[1])));
  while ((m = IMG_HTML.exec(src))) push(m.index, m[0].length, m[1] ?? m[2] ?? m[3] ?? "");
  out.sort((a, b) => a.start - b.start);
  return out.filter((e, i) => !i || e.start >= out[i - 1].end);   // a shortcut form inside a longer one: the longer wins
}
/** Whether a source destination is the `src` marked emitted for it (marked percent-encodes; either side may be encoded). */
export function sameDest(dest: string, src: string): boolean {
  if (dest === src) return true;
  try { if (encodeURI(dest).replace(/%25/g, "%") === src) return true; } catch { /* a lone surrogate */ }
  try { return decodeURI(dest) === decodeURI(src); } catch { return false; }
}
/** A path with `.` and `..` folded, a leading slash kept, repeated slashes collapsed — for comparing two spellings, never for reading. */
export function normPath(p: string): string {
  const abs = p.startsWith("/");
  const out: string[] = [];
  for (const seg of p.split("/")) {
    if (!seg || seg === ".") continue;
    if (seg === "..") { if (out.length && out[out.length - 1] !== "..") out.pop(); else if (!abs) out.push(".."); continue; }
    out.push(seg);
  }
  return (abs ? "/" : "") + out.join("/");
}
const decoded = (s: string): string => { try { return decodeURIComponent(s); } catch { return s; } };
// An embed's dest is decoded with decodeURI, as the viewer decodes it before it loads the picture (file-view.ts
// rewriteFigureSrcs), the poll before it HEADs the figure (file-comments-model.ts figurePath) and the host before it
// hashes it: the three readers of a destination must name one file. decodeURIComponent, which stood here first, also
// decodes the escapes of RESERVED characters, so `a%26b.png` became `a&b.png` on this side and stayed `a%26b.png` on
// the viewer's — and a figure written with such an escape never matched its embed once rewritten through /file (the
// drag refused, the embed-line frame unpainted, the picture click's offer a whole-file comment). fileUrlPath keeps
// decodeURIComponent: fileUrl built its `path` with encodeURIComponent, and that is the exact inverse there.
const decodedDest = (s: string): string => { try { return decodeURI(s); } catch { return s; } };
/** Where an embed's `dest`, as written, points relative to the markdown file at `filePath` (absolute dest: itself). */
export function embedPath(filePath: string, dest: string): string {
  const d = decodedDest(dest);
  if (d.startsWith("/")) return normPath(d);
  return normPath(filePath.slice(0, filePath.lastIndexOf("/") + 1) + d);
}
/** The `path` a /file (or /remote/<host>/file) URL names, decoded; null for any other URL. */
export function fileUrlPath(src: string): string | null {
  const q = src.indexOf("?");
  if (q < 0 || !/(^|\/)file$/.test(src.slice(0, q))) return null;
  for (const kv of src.slice(q + 1).split("&")) if (kv.startsWith("path=")) return decoded(kv.slice(5));
  return null;
}
/** Whether a rendered picture's `src` is the embed's `dest`: as marked emitted it (either side percent-encoded),
 *  or as the viewer rewrote it through /file against the file's directory so the figure loads from the kernel
 *  (contract E4) — the two spellings name one path. */
export function srcIsEmbed(src: string, dest: string, filePath: string | null | undefined): boolean {
  if (sameDest(dest, src)) return true;
  const p = fileUrlPath(src);
  return p !== null && typeof filePath === "string" && normPath(p) === embedPath(filePath, dest);
}
const imgsIn = (root: Element): HTMLElement[] => Array.from(root.querySelectorAll("img")) as HTMLElement[];
/** The destination a rendered picture was written with: the authored attribute the viewer keeps as `data-fv-src` when it
 *  rewrites `src` through /file (file-view.ts rewriteFigureSrcs), else `src` itself — a picture the viewer left as written.
 *  Null for a picture with neither. */
export function pictureDest(img: Element): string | null {
  const kept = img.getAttribute("data-fv-src");
  return kept !== null ? kept : img.getAttribute("src");
}
/** Whether a rendered picture came from an embed written as `dest`: srcIsEmbed over the picture's own spelling. With the
 *  authored spelling in hand this is sameDest, so `./fig.png` and `fig.png` — two embeds of ONE file — stay two
 *  destinations, each with its own picture; the /file-path comparison serves only a rewritten picture that carries no
 *  authored spelling. The ONE test every reader of the picture↔embed pairing uses (embedFor, imgForRange, the region
 *  painter's fallbacks), so they cannot disagree about which picture an embed made. */
export function pictureIsEmbed(img: Element, dest: string, filePath?: string | null): boolean {
  const s = pictureDest(img);
  return s !== null && srcIsEmbed(s, dest, filePath);
}
/** The embed the picture at `img` came from, given every embed and every picture: the embeds written as the picture's
 *  destination, and among them, by order — the k-th picture of that destination is its k-th embed. */
function embedOf(img: HTMLElement, imgs: HTMLElement[], all: ImageEmbed[], filePath?: string | null): ImageEmbed | null {
  if (pictureDest(img) === null) return null;
  const hits = all.filter((e) => pictureIsEmbed(img, e.dest, filePath));
  if (hits.length === 1) return hits[0];
  if (!hits.length) return null;
  const k = imgs.filter((i) => pictureIsEmbed(i, hits[0].dest, filePath)).indexOf(img);
  return k >= 0 && k < hits.length ? hits[k] : null;
}
/** The embed a rendered picture came from: by destination, and among twins by order. Null when the source holds none.
 *  `filePath` lets a src the viewer rewrote through /file match its embed (srcIsEmbed) when the picture carries no
 *  authored spelling (pictureDest). Before the rewrite, the hits were found by path (two spellings of one file matched
 *  either picture) while the twins were counted by the rewritten `src` (which the two spellings made different): a
 *  region drawn on the second figure was anchored to the first's embed line, and imgForRange, counting the other way
 *  round, painted the second embed's rectangle on the first figure (the 2026-09-06 review). Both now pair through
 *  embedOf, and imgForRange is embedFor's inverse by construction. */
export function embedFor(img: Element, root: Element, src: string, filePath?: string | null): ImageEmbed | null {
  return embedOf(img as HTMLElement, imgsIn(root), imageEmbeds(src), filePath);
}
/** The rendered picture for an embed's exact source range — the inverse, for painting: the picture whose embedFor is
 *  that embed. Null when no picture came from it (the range is not an embed's, or the source holds more embeds of the
 *  destination than the view holds pictures). */
export function imgForRange(root: Element, src: string, range: SourceRange, filePath?: string | null): HTMLElement | null {
  const all = imageEmbeds(src);
  const e = all.find((x) => x.start === range.start && x.end === range.end);
  if (!e) return null;
  const imgs = imgsIn(root);
  return imgs.find((i) => embedOf(i, imgs, all, filePath) === e) || null;
}
// A framed picture wears the mark classes itself — an <img> has no text to wrap — plus an inline outline,
// because the sheets' ring is an inset shadow the picture covers. `fc-img` tells unpaint to strip, not unwrap.
function styleFrame(img: HTMLElement): void {
  const presel = img.classList.contains("fc-presel");
  const dashed = !presel && img.classList.contains("fc-hl-context");
  img.style.outline = "2px " + (dashed ? "dashed" : "solid") + " " + (presel ? "var(--accent)" : "var(--warn)");
  img.style.outlineOffset = "2px";
}
function frameImage(img: HTMLElement, cls: string, data?: Record<string, string>): void {
  img.classList.add("fc-img", ...cls.split(" ").filter(Boolean));
  if (data) for (const k of Object.keys(data)) img.dataset[k] = data[k];
  styleFrame(img);
}
function unframeImage(img: HTMLElement, marks: string[]): void {
  img.classList.remove(...marks);
  if (img.classList.contains("fc-hl") || img.classList.contains("fc-presel")) { styleFrame(img); return; }
  img.classList.remove("fc-img", "fc-hl-context");
  img.style.outline = ""; img.style.outlineOffset = "";
  delete img.dataset.act; delete img.dataset.id;
}

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

// `overlapped`: a status ask still unanswered when a write's reply landed (markOverlapped) — its host run may
// have read the disk before that write, whatever its place in line
type Pending = { verb: string; ok: (m: Record<string, unknown>) => void; fail: (e: { code: string; error: string }) => void; deadline?: ReturnType<typeof setTimeout>; overlapped?: boolean };
/** A status reply as the panel applies it: the kernel's fields plus the reqId of the ask it answers, and
 *  whether that ask overlapped a write (see Pending). */
type Reply = Status & { reqId: number; overlapped?: boolean };

// ── which of two status replies read the disk later ────────────────────────────────────────────────
// Mtimes are decimal nanosecond strings (~1.7e18 exceeds JS's safe integers, so they never become numbers):
// digit strings order by length, then by text. A value beats null (a sidecar or config that now exists is a
// later reading than one that says it does not); anything that is not digits is no clock and claims nothing.
function laterNs(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a) return false;
  if (!b) return true;
  if (!/^\d+$/.test(a) || !/^\d+$/.test(b)) return false;
  return a.length !== b.length ? a.length > b.length : a > b;
}
/** Did `a` read a LATER disk than `b`? True when any of the file, the sidecar or the config moved forward. */
export function newerStatus(a: Status, b: Status): boolean {
  return laterNs(a.fileMtimeNs, b.fileMtimeNs) || laterNs(a.storeMtimeNs, b.storeMtimeNs) || laterNs(a.configMtimeNs, b.configMtimeNs);
}

// ── a path the panel prints inline ─────────────────────────────────────────────────────────────────
// Chromium breaks a line at neither a slash nor anywhere inside an unbroken token, and a flex item's automatic
// minimum size is that token, so a path wider than the aside's 340px (about 55 characters) pushed .fc-panel
// into a horizontal scrollbar: the folder button of the tracking choice, the folder-off confirm, and any error
// row naming a path. The path is appended as text with a <wbr> after every `/` — a break where a reader would
// put one, and no change to textContent — with `overflow-wrap: anywhere` behind it for a single component
// wider than the aside (it also lets the item's minimum size shrink below the token).
/** The path split after every `/`: "/a/b/c.md" → ["/", "a/", "b/", "c.md"]. */
export function pathSegments(path: string): string[] {
  return path.match(/[^/]*\/|[^/]+$/g) || [];
}
function appendPath(node: HTMLElement, path: string): void {
  pathSegments(path).forEach((seg, i) => {
    if (i) node.appendChild(document.createElement("wbr"));
    node.appendChild(document.createTextNode(seg));
  });
  node.style.overflowWrap = "anywhere";
}
/** A .fileview-btn is `flex: 0 0 auto`, one line, right for "Reload" and wrong for a label carrying a path:
 *  this one may shrink to its row and wrap inside, its lines starting at the left like the text around it. */
function shrinkable(b: HTMLElement): void {
  b.style.flex = "0 1 auto"; b.style.minWidth = "0"; b.style.textAlign = "left";
}
// A passage comment's `range` indexes `text` — the source the selection was made over, or the reload the
// passage was re-found in (retargetComposer) — so the anchor is always built over the text the offsets
// belong to, never over whatever sits at those offsets now. `text` travels with every non-null range.
type Composer =
  | { kind: "comment"; range: SourceRange | null; quote: string | null; text?: string; refusal: (MapRefusal & { selText: string }) | null }
  | { kind: "reply"; commentId: string; ref: string }
  | { kind: "change"; changeId: string; ref: string }   // a comment bound to a change (comment {suggestionId, note})
  // a region drawn on a picture (Slice 3): `img` is the picture (re-found after a repaint), `src` and `range` the
  // embed's dest and source range for a figure in rendered markdown (null for a standalone image), `text` the
  // source the range indexes; `refusal` when the figure's embed line could not be found (nothing to anchor to)
  | { kind: "region"; img: HTMLImageElement; region: Region; src: string | null; range: SourceRange | null; text?: string; refusal: string | null }
  // Re-place: the next region drawn on the comment's picture becomes its target (retarget, E3); no words
  | { kind: "replace"; commentId: string; ref: string; src: string | null };
/** Why a region on a figure cannot be saved: the anchor is the embed line, and the source holds none for this picture. */
const EMBED_NOT_FOUND = "the line that embeds this image was not found in the source, so a region on it cannot be saved";
/** The passage composer's refusal for the same figure — the picture click's Comment offer builds it (startImageComment), and
 *  Switch to Raw on a refused region turns the region composer into it: a Raw selection of the embed line places the note. */
const EMBED_NOT_FOUND_SELECT = "The line that embeds this image was not found in the source; select it in the Raw view.";
type Err = { text: string; reload: boolean; warn?: boolean };

// ── why a region's staleness is unknown ─────────────────────────────────────────────────────────────
// The host puts a reason beside every hash it could not take (fileHashFor / embeddedHashesFor in the host script:
// `fileHashReason` for a media file, `embeddedHashReasons[src]` for a figure a text file's comments name), because the
// kernel keeps the host's stderr only when a call fails — the reason reaches the panel in the reply or not at all. The
// Status type (file-comments-model.ts) names the hashes; the reasons are read off the same reply here, where the card
// is the one thing that shows them: the tag's title collapsed, a sentence in the open card (a title never reaches touch,
// the caption idiom of renderSend). Unknown also has causes the host cannot explain, each named in its own words: a
// comment saved without a hash, a host from before region comments (no hash field at all). Never a bare "unknown": a
// deleted figure, one moved outside the project and one past the hash cap are three different things for the person to
// do (CLAUDE.md: surface the error, never degrade silently).
type HashReasons = { fileHashReason?: string | null; embeddedHashReasons?: Record<string, string | null> | null };
const UNKNOWN_GENERIC = "Whether the image changed since this region was drawn could not be checked.";
/** The host's reason as the card shows it: capitalized, ending in a period (the host writes lowercase fragments). */
const asSentence = (s: string): string => { const t = s.trim(); return t.charAt(0).toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? "" : "."); };
/** Why a region comment's staleness cannot be told (regionState "unknown"): the host's own reason when it sent one,
 *  else the panel-side cause it can see, else the generic sentence. */
export function unknownReason(target: Target, s: Status | null): string {
  if (typeof target.hash !== "string" || !target.hash) return "This region was saved without the image's hash, so a later change to the image cannot be detected.";
  if (!s) return UNKNOWN_GENERIC;
  const r = s as Status & HashReasons;
  const src = typeof target.src === "string" && target.src ? target.src : null;
  const reason = src ? (r.embeddedHashReasons && typeof r.embeddedHashReasons === "object" ? r.embeddedHashReasons[src] : undefined) : r.fileHashReason;
  if (typeof reason === "string" && reason.trim()) return asSentence(reason);
  const current = src ? (r.embeddedHashes && typeof r.embeddedHashes === "object" ? r.embeddedHashes[src] : undefined) : r.fileHash;
  if (current === undefined) return "The file's machine sent no hash for this image, so whether it changed since this region was drawn could not be checked. Its kernel may predate region comments: update and restart it.";
  return UNKNOWN_GENERIC;
}

// ── the wire: ONE window listener for the module, dispatching to the live panel by reqId ───────────
// A reply is matched by reqId only — a REMOTE kernel's reply comes back with its sid host-prefixed
// (federation's prefixInbound), so sid equality would fail there. The one `warn` that means an
// outstanding request will never be answered is federation's drop notice (dropWarn: "<host> is
// unreachable (its kernel isn't answering) — “<type>” was not delivered"), and only when it names one
// of THIS module's ops: the kernel sends `warn` on the same socket for unrelated refusals — a rejected
// rename, a todo notice — with no reqId, and failing a request on those reported a comment that had
// succeeded on disk as failed, with the kept note inviting a duplicate. The shim's own drop event
// (romp:wsdown) fails everything outstanding, as before.
let live: Panel | null = null;
let listening = false;
const DROPPED_OPS = ["fileComments", "fileCommentsSend"];
/** The warn's text when it is federation's drop of one of this module's requests, else null. */
export function droppedRequestText(text: unknown): string | null {
  const t = typeof text === "string" ? text : "";
  return DROPPED_OPS.some((op) => t.includes("“" + op + "” was not delivered")) ? t : null;
}
function ensureListener(): void {
  if (listening) return;
  listening = true;
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m || !live) return;
    if (m.type === "fileCommentsResult" || m.type === "fileCommentsSent") live.settle(m, true);
    else if (m.type === "fileCommentsFailed" || m.type === "fileCommentsSendFailed") live.settle(m, false);
    else if (m.type === "warn") live.failAll(droppedRequestText(m.text));
  });
  window.addEventListener("romp:wsdown", () => { if (live) live.failAll("the connection dropped; try again once it returns"); });
}

// The controls that are not <button>s — a card's head, its passage link, a Log row, a painted highlight —
// and so take Enter and Space here, through the same root the clicks use: a collapsed card is otherwise a
// dead end for the keyboard (ui/CLAUDE.md, never dead-end a compact view).
const KEY_ACTS = new Set(["fccard", "fcgoto", "fcopen", "fcchange", "fclogrow"]);

/** Where a Rendered-view refusal's passage sits in the source, for the switch to Raw. The selection
 *  came from the REFUSED block, so the search starts at that block: a copy of the same words earlier in
 *  the file (prose saying "p95" above a table cell "p95") must not win. The text searched for is the
 *  mapper's own source slice when it has one (`rawRange`, found over the normalized text, so it carries
 *  the source's tabs and CRLFs where the DOM's selection string has spaces and LFs), else the trimmed
 *  selection; the mapper's slice stands when neither search hits. Null when the mapper saw no
 *  occurrence at all (the button then only scrolls to the block). */
export function rawTarget(src: string, r: MapRefusal & { selText: string }): SourceRange | null {
  if (!r.rawHasQuote) return null;
  const rr = r.rawRange && r.rawRange.start >= 0 && r.rawRange.end > r.rawRange.start && r.rawRange.end <= src.length ? r.rawRange : null;
  const q = rr ? src.slice(rr.start, rr.end) : r.selText.trim();
  if (!q) return rr;
  const from = typeof r.blockStartOffset === "number" ? Math.max(0, r.blockStartOffset) : 0;
  let i = src.indexOf(q, from);
  if (i < 0) i = src.indexOf(q);
  return i >= 0 ? { start: i, end: i + q.length } : rr;
}

let reqSeq = 0;

class Panel {
  status: Status | null = null;
  statusRefusal: { code: string; error: string } | null = null;   // why there is no status, when the kernel refused one
  root: HTMLElement | null = null;          // the aside, built on first open
  marks = new WeakSet<Element>();           // the highlights and picture frames THIS panel painted into the body (owns)
  open = false;
  pending = new Map<number, Pending>();
  appliedReq = 0;                           // the reqId of the newest ask whose reply is showing (applyStatus)
  openCards = new Set<string>();            // keyed expand state: survives every re-render (ui/CLAUDE.md); a change card's key is "chg:" + its id
  openLog = new Set<string>();              // expanded Log rows, keyed by entry (ts|kind) — the same rule
  logOpen = false;
  moreChangesOpen = false;                  // the "… N more changes" fold past GROUP_LIMIT groups — the same rule
  rejectAllConfirm = false;                 // the Reject all confirm row is showing (pane-local, like the folder-off confirm)
  paintedChanges = new Set<string>();       // the change ids whose marks the current view shows; the rest get Reveal
  busyVerb = new Map<string, string>();     // slot → the verb in flight, so a card's Accept/Reject relabels itself (ui/CLAUDE.md)
  imageTarget: { range: SourceRange | null } | null = null;   // the picture the float's Comment is about, when it is one
  regionLayers = new Map<HTMLImageElement, RegionLayer>();   // the overlays, one per picture in view (Slice 3; paintRegions)
  // what each overlay last painted (its marks, the pending region, the re-place cue), so a pass that brings it nothing
  // new leaves its rectangles standing: a rebuild detaches the node a click just flashed, and the keyboard's focus with
  // it — openPanel's own paint did that to the rectangle whose Enter opened it (CLAUDE.md: a move on no new information)
  paintedKey = new WeakMap<RegionLayer, string>();
  cropWait = new WeakSet<HTMLImageElement>();                 // pictures whose load will re-render the cards for their thumbnails
  figureBase: FigureBaseline = {};                            // the poll's last reading of each figure a region comment names (tick)
  resolvedOpen = false;
  trackChoice = false;                      // the on-toggle's scope row (file / folder) is showing
  trackStop = false;                        // the folder-off confirm is showing
  composer: Composer | null = null;
  errors = new Map<string, Err>();          // per slot: the row sits under the control that asked
  busy = new Set<string>();
  sendConfirm = false;
  sending = false;
  sendOpts = { todo: true, track: true, accept: true };   // all checked by default (decision 8); `accept` is the Slice 2 checkbox
  sentNote: string | null = null;
  todoAnswered = false;                     // one send answers the todo; later sends show no checkbox (seeded from answeredTodos)
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
  hideFloatOnDown = (ev: Event) => { if (ev.target !== this.float) { this.float.hidden = true; this.imageTarget = null; } };
  // Esc cancels a Re-place. Every other composer kind focuses the input, whose own keydown catches Esc; a re-place hides
  // the input (it takes a drag, not words), so nothing in the box holds focus and the key fell through to the viewer's
  // document-level Escape, which closed the WHOLE viewer — the panel, the open card and the pending re-place with it, when
  // the person meant only to think again. Caught at the document in the capture phase, ahead of the viewer's handler,
  // wherever the focus sits (the re-rendered Re-place button, or the body); only while a re-place is pending.
  escapeReplace = (ev: KeyboardEvent) => {
    if (ev.key !== "Escape" || !this.composer || this.composer.kind !== "replace") return;
    ev.preventDefault(); ev.stopPropagation();
    this.closeComposer();
  };

  constructor(readonly ctx: FileViewActionCtx, readonly button: HTMLButtonElement, readonly unit: HTMLElement) {
    ensureListener();
    live = this;
    this.todoAnswered = !!ctx.todoId && answeredTodos.has(ctx.todoId);
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
    const act = () => {
      flash(this.float);
      const picture = this.imageTarget; this.imageTarget = null;
      const sel = window.getSelection();
      this.float.hidden = true;
      if (picture) this.startImageComment(picture.range);
      else if (sel && !sel.isCollapsed) this.startComment(sel);
    };
    this.float.addEventListener("click", act);
    // a tap: the touchstart above is cancelled, and a cancelled touch synthesizes no mouse events and no
    // click (Touch Events, "mouse events"), so on a phone the button acted on nothing. The tap acts here, on
    // the lift, while the selection is still live; cancelling the touchend too stops any click a browser
    // would still synthesize from acting a second time.
    this.float.addEventListener("touchend", (e) => { e.preventDefault(); act(); });
    document.body.appendChild(this.float);
    for (const ev of ["mousedown", "touchstart"]) document.addEventListener(ev, this.hideFloatOnDown, true);   // a press anywhere else hides it, mouse or finger
    document.addEventListener("keydown", this.escapeReplace, true);   // Esc during a re-place: see escapeReplace
    ctx.onSelection((sel) => this.onSelection(sel));
    ctx.onRendered(() => { this.float.hidden = true; this.retargetComposer(); this.paintAll(); });
    ctx.onSaved((info) => {
      if (this.base) this.base.file = info.mtimeNs;   // the poll must not re-fetch the person's own save
      if (this.status) void this.refresh();            // the Log gained the edit entry before the reply
    });
    ctx.onClose(() => this.dispose());
    // every control the panel ever renders hangs off ONE stable root (ui/CLAUDE.md, click-safe): the
    // viewer's body row, which also holds the painted highlights — so a highlight click routes here too.
    // The same row holds the FILE's rendered markdown, and the sanitizer keeps data-* attributes (DOMPurify's
    // ALLOW_DATA_ATTR default), so a file's author can write `<span data-act="fcsendgo">` or a
    // `data-act="fctrackstop"` into prose the session produced: a click there must not send the comments
    // or turn the guard off for a folder. `own` routes an activation only when the panel MADE the element —
    // a control in its aside, or a highlight it painted (owns) — never the file's own markup.
    const row = ctx.body().parentElement || ctx.body();
    delegate(row, {
      ...this.own({
        fctrack: () => { void this.onTrackClick(); },
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
        // the changes (Slice 2): a decision per card, both at once in the footer, a reply bound to the change, the fold
        fcaccept: (x, ev) => { ev.stopPropagation(); void this.mutate("accept", { ids: [x.dataset.id!] }, "change:" + x.dataset.id!); },
        fcreject: (x, ev) => { ev.stopPropagation(); void this.mutate("reject", { ids: [x.dataset.id!] }, "change:" + x.dataset.id!); },
        fcacceptall: () => { this.rejectAllConfirm = false; void this.mutate("accept-all", {}, "changes"); },
        fcrejectall: () => { this.rejectAllConfirm = !this.rejectAllConfirm; this.render(); },   // Reject all rewrites the file: one pane-local confirm
        fcrejectallgo: () => { this.rejectAllConfirm = false; void this.mutate("reject-all", {}, "changes"); },
        fcrejectallcancel: () => { this.rejectAllConfirm = false; this.render(); },
        fcchangereply: (x, ev) => { ev.stopPropagation(); this.startChangeReply(x.dataset.id!); },
        fcmore: () => { this.moreChangesOpen = !this.moreChangesOpen; this.render(); },
        fcchange: (x) => { this.openPanel(); this.showCard("chg:" + x.dataset.id!); },   // an inline change mark opens its card
        fcsend: () => { if (this.statusRefusal) return; this.sendConfirm = true; this.sentNote = null; this.render(); },   // renderSend disables the button and says why; the guard holds if a click lands anyway
        fcsendcancel: () => { this.sendConfirm = false; this.previewOpen = false; this.render(); },
        fcsendgo: () => { void this.doSend(); },
        fcpreview: () => { this.previewOpen = !this.previewOpen; this.render(); },
        fclog: () => { this.logOpen = !this.logOpen; this.render(); },
        fclogrow: (x) => { const k = x.dataset.key!; if (this.openLog.has(k)) this.openLog.delete(k); else this.openLog.add(k); this.render(); },
        // Reload re-reads under the row that offered it: the slot wears the loader for the wait (refresh)
        fcreload: (x) => { const slot = x.dataset.slot || "head"; this.errors.delete(slot); this.stopped.clear(); void this.refresh(slot); this.ctx.reload(); },
        fcerrx: (x) => { this.errors.delete(x.dataset.slot || ""); this.render(); },
        // a mark in the file's own markup — a rectangle on a figure, a framed picture — is the panel's control, and its
        // click is the card's opening, not the activation of whatever the author wrapped the figure in: a linked figure
        // (`[![p95](figs/p95.png)](url)`, which mdBlock gives target=_blank) opened a new tab on every click, Enter and
        // handed-on press on a rectangle inside it, since the overlay and its rectangles stand inside the <a>
        // (the 2026-09-06 review). Cancelling the click ends the anchor's activation; the card opens as before.
        fcopen: (x, ev) => { ev.preventDefault(); this.openPanel(); this.showCard(this.cardKey(x.dataset.id!)); },
        fcreplace: (x, ev) => { ev.stopPropagation(); this.startReplace(x.dataset.id!); },   // a region comment's Re-place (Slice 3)
      }),
    });
    row.addEventListener("change", (ev) => {
      const t = ev.target as HTMLInputElement | null;
      const k = t ? t.dataset.opt : undefined;
      if (!t || k !== "todo" && k !== "track" && k !== "accept" || !this.owns(t)) return;   // a checkbox the file's markup carries flips nothing
      this.sendOpts[k] = t.checked;
      this.render();                                   // the list's counts and the preview follow the boxes (refocus keeps the box focused)
    });
    // a click on a rendered picture offers Comment on its embed line (the plan's Images and PDFs) — the same
    // stable root, a plain tag check rather than a data-act: the markdown's own <img> carries none
    row.addEventListener("click", (ev) => {
      const t = ev.target as HTMLElement | null;
      if (t && typeof t.tagName === "string" && t.tagName.toUpperCase() === "IMG") this.onImageClick(t);
    });
    // Enter or Space on a focused non-button control (KEY_ACTS) is its click, so it lands on the same root —
    // for the panel's own elements only, as with the clicks
    row.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      const t = ev.target as HTMLElement | null;
      if (!t || typeof t.tagName !== "string" || t.tagName.toUpperCase() === "BUTTON" || t.tagName.toUpperCase() === "INPUT" || typeof t.closest !== "function") return;
      const x = t.closest("[data-act]") as HTMLElement | null;
      if (!x || !KEY_ACTS.has(x.dataset.act || "") || !this.owns(x)) return;
      ev.preventDefault();
      x.click();
    });
    this.button.addEventListener("click", () => { flash(this.button); if (this.open) this.closePanel(); else this.openPanel(); });
  }

  // ── provenance: which activations are the panel's ──────────────────────────────────────────────
  /** Whether the panel made `x`: a control inside its aside (none before the first open), or a highlight or
   *  picture frame it painted into the body (marks). Anything else under the delegate root is the file's own
   *  markup, whatever data-act it carries — the sanitizer keeps data-* attributes, and a class name proves
   *  nothing either. */
  owns(x: Element): boolean {
    return (this.root !== null && this.root.contains(x)) || this.marks.has(x);
  }
  /** The handlers, each routed only for an element the panel owns. The delegate helper has already flashed
   *  the element by then (a cosmetic pulse); nothing else happens for the file's markup. */
  private own(acts: Record<string, ActionHandler>): Record<string, ActionHandler> {
    const out: Record<string, ActionHandler> = {};
    for (const k of Object.keys(acts)) out[k] = (x, ev) => { if (this.owns(x)) acts[k](x, ev); };
    return out;
  }

  // ── the wire ───────────────────────────────────────────────────────────────────────────────────
  request(verb: string, args?: Record<string, unknown>, fence?: Record<string, string>): Promise<Reply> {
    const reqId = ++reqSeq;
    const { ctx } = this;
    const msg: Record<string, unknown> = { type: "fileComments", reqId, sid: ctx.sid || undefined, path: ctx.path, verb };
    if (args) msg.args = args;
    if (fence) msg.fence = fence;
    return new Promise<Reply>((ok, fail) => {
      // the reply carries the ask's own reqId (the client's, not the echo) so applyStatus can order it, and
      // whether the ask overlapped a write (set on the pending record by markOverlapped, read when it settles)
      const p: Pending = { verb, ok: (m) => ok({ ...m, reqId, overlapped: p.overlapped === true } as unknown as Reply), fail };
      if (verb === "status") p.deadline = setTimeout(() => this.expire(reqId), STATUS_DEADLINE_MS);   // STATUS_DEADLINE_MS: why, and why status only
      this.pending.set(reqId, p);
      ctx.post(msg);
    });
  }
  /** A status ask past its deadline: failed under `no-answer`, naming the machine whose kernel it went to. */
  private expire(reqId: number): void {
    const p = this.pending.get(reqId);
    if (!p) return;
    this.pending.delete(reqId);
    const machine = hostOf(this.ctx.sid || "") || "this machine";
    p.fail({ code: "no-answer", error: "No answer from the kernel on " + machine + " after " + STATUS_DEADLINE_MS / 1000
      + " s. It may predate file comments: update and restart it, then Reload to ask again." });
  }
  /** The kernel's reply carries two optional texts on a SENT message: `warning` (nothing stamped:
   *  the todo switch is off, or the todo was already settled) and `logWarning` (the comments log
   *  append failed, so the Log and the unsent count will not reflect this send). Both are shown; a
   *  send whose record is missing must never look fully done (CLAUDE.md, fail loudly). */
  requestSend(msg: Record<string, unknown>): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    const reqId = ++reqSeq;
    const str = (v: unknown) => (typeof v === "string" && v ? v : undefined);
    return new Promise((ok, fail) => {
      // a SENT reply's `warning` is exclusively the nothing-stamped text (contract C2), so its absence is the stamp
      this.pending.set(reqId, { verb: "send", ok: (m) => ok({ queued: m.queued === true, warning: [str(m.warning), str(m.logWarning)].filter(Boolean).join(" ") || undefined,
        todoStamped: !str(m.warning) }), fail });
      this.ctx.post({ ...msg, type: "fileCommentsSend", reqId });
    });
  }
  settle(m: Record<string, unknown>, ok: boolean): void {
    const p = this.pending.get(Number(m.reqId));
    if (!p) return;                                    // an older open's reply, or a stale one — lands nowhere
    this.pending.delete(Number(m.reqId));
    if (p.deadline) clearTimeout(p.deadline);
    if (ok) p.ok(m);
    else p.fail({ code: String(m.code || "failed"), error: String(m.error || "the request failed") });
  }
  /** Fail everything outstanding with `text`; null (a warn that was not a drop of ours) leaves it all in flight. */
  failAll(text: string | null): void {
    if (text === null || !this.pending.size) return;
    const ps = [...this.pending.values()]; this.pending.clear();
    for (const p of ps) { if (p.deadline) clearTimeout(p.deadline); p.fail({ code: "unreachable", error: text }); }
  }

  // ── status ─────────────────────────────────────────────────────────────────────────────────────
  /** The first ask, at mount: mounted hidden, revealed when the kernel answers (the GitHub link's
   *  idiom). A `no-node` refusal keeps the action away for good — the gear's row says why. A kernel that
   *  never answers (one from before this feature, reached through federation for a remote session's file,
   *  or the VS Code extension's local one) is named after STATUS_DEADLINE_MS, the way any other refusal
   *  is: the action appears with the reason as its title and in the panel's head row. */
  probe(): void {
    this.request("status").then((s) => this.applyStatus(s), (e: { code: string; error: string }) => {
      if (e.code === "no-node") return;
      this.statusRefusal = e;
      this.unit.hidden = false;
      this.button.title = "Comments: " + e.error;
      this.errors.set("head", { text: e.error, reload: false });
    });
  }
  /** Replies land in the order their asks were ISSUED, not the order they arrive. The kernel runs each ask
   *  concurrently and answers as each finishes, so a `status` the poll asked (or onSaved, or Reload, or a
   *  send's refresh) can be answered after a later comment or toggle whose reply already carried the
   *  post-write state — and applying it as it came put the panel back a step (the new card gone, Send's count
   *  down) until the next tick saw the store moved against that regressed baseline and re-read it: a card
   *  move on no new information (CLAUDE.md). Two asks are suspect: one OLDER than the applied reply, and one
   *  issued after a write's ask but still unanswered when that write's reply landed (`overlapped`,
   *  markOverlapped) — the kernel runs the two concurrently and the host reads the sidecar without a lock,
   *  so the later ask's run can read the disk before the write and answer after it, and its reqId
   *  alone would have let it land. Either is dropped, unless its own clocks say it read a NEWER disk than what
   *  is showing (its run started late and saw a write the applied reply predates): then it IS new information
   *  and lands. Clocks alone cannot decide the overlapped case: a sidecar gone is a later reading that reads
   *  as older (laterNs), and the vendored CLIs do delete sidecars. Returns whether it was applied. */
  applyStatus(s: Reply): boolean {
    const suspect = s.reqId < this.appliedReq || s.overlapped === true;
    if (this.status && suspect && !newerStatus(s, this.status)) return false;
    this.appliedReq = Math.max(this.appliedReq, s.reqId);
    this.status = s;
    this.statusRefusal = null;
    this.errors.delete("head");                        // a status refusal's row (probe, refresh) is answered by a status
    this.base = pollBaseline(s);
    this.unit.hidden = false;
    this.button.textContent = actionLabel(s);
    this.button.title = s.store ? "Comments and changes kept beside this file" : "Comment on this file, or track a session's changes to it";
    this.ctx.setEditBlocked(editBlockedReason(s.hunks || []));
    this.paintAll();                                   // repaints the highlights and renders the panel
    return true;
  }
  /** Re-ask status. While the ask is out and no status has ever landed, the cards section shows the romp
   *  loader (ui/CLAUDE.md: a wait wears the loader, never a line claiming a read); a refusal leaves the
   *  head's row with Reload, the one way back in — nothing re-asks on its own while status is null.
   *  `slot`: the row whose Reload asked. Over a showing status the cards stay up, so that wait would show
   *  nowhere (the row is gone, the click's pulse goes with its rebuilt button, and the ask may run to
   *  STATUS_DEADLINE_MS) — the slot wears the loader instead, where the row was. The poll's and onSaved's own
   *  re-reads pass no slot: nobody is waiting on those, and a swirl in the head per change the session
   *  makes would only pull the eye. */
  async refresh(slot?: string): Promise<void> {
    const mark = slot && this.status ? slot : null;   // with no status the cards' own loader is the wait
    this.busy.add("status"); if (mark) this.busy.add(mark); this.render();
    try { this.applyStatus(await this.request("status")); }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set("head", { text: e.error, reload: true });
    } finally { this.busy.delete("status"); if (mark) this.busy.delete(mark); this.render(); }
  }
  /** A write's reply just landed: every status ask still out was issued before it and may have read the disk
   *  before the write (applyStatus). The flag rides the pending record, so a failed or expired ask needs no
   *  cleanup. */
  private markOverlapped(): void {
    for (const p of this.pending.values()) if (p.verb === "status") p.overlapped = true;
  }
  /** A mutating verb needs a status behind it: the fence comes from there, and `""` for an unknown sidecar
   *  would claim it must not exist, so the host would refuse `store-moved` — a reason that is not the reason
   *  (a corrupt sidecar, say). Re-ask first, since the person may have fixed the file since the last answer;
   *  when the answer is still a refusal, refuse here, under the control that asked, with the host's own text.
   *  The caller (mutate) holds the slot busy for the whole call, loader included. */
  private async requireStatus(slot: string): Promise<boolean> {
    if (this.status) return true;
    try { this.applyStatus(await this.request("status")); return true; }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set(slot, { text: "Nothing written: " + e.error, reload: false });
      return false;
    }
  }

  // ── open / close ───────────────────────────────────────────────────────────────────────────────
  openPanel(): void {
    if (this.open) return;
    this.open = true;
    if (!this.root) this.root = el("div", "fc-panel");
    this.ctx.aside(this.root);
    this.button.classList.add("on"); this.button.setAttribute("aria-pressed", "true");
    if (!this.colors) void this.loadColors();
    this.paintRegions();                               // arm the overlays' drag (they paint while closed, but draw only open)
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
    this.paintRegions();                               // disarm: a closed panel leaves the pictures to the browser
    this.stopPoll();
  }
  dispose(): void {
    this.stopPoll();
    for (const l of this.regionLayers.values()) l.dispose();
    this.regionLayers.clear();
    this.float.remove();
    for (const ev of ["mousedown", "touchstart"]) document.removeEventListener(ev, this.hideFloatOnDown, true);
    document.removeEventListener("keydown", this.escapeReplace, true);
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
    // the change marks and the region rectangles carry the author's colour too (paintChanges, paintRegions): repaint
    // when any are up — a rectangle painted before this answer wears the sheet's fallback until then — else just the chips
    const s = this.status;
    if (s && ((s.hunks || []).length || this.cards().some((c) => c.target))) this.paintAll(); else this.render();
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
      // `fileMoved`: the bytes the VIEW shows moved — the file's own, or (below) an embedded figure's, drawn in it
      let fileMoved = false, moved = false;
      for (const [key, target] of checks) {
        const v = await this.head(target);
        if (!v) continue;
        if (mtimeMoved(base[key], v.value)) { moved = true; if (key === "file") fileMoved = true; }
      }
      // the figures (Slice 3): a region comment on a figure embedded in a text file goes stale when the FIGURE's bytes
      // change, and a session that regenerates one touches none of the three targets above — so they are HEADed too.
      // The status carries their hashes, not their mtimes, so the reply gives them no baseline: each is compared with the
      // poll's own last reading of it (figuresMoved; a first reading is an observation, never a move). A move re-asks
      // status, whose embeddedHashes flip the comment to stale by hash, and reloads the view so the new picture shows:
      // the kernel serves /file with Cache-Control: no-cache, so the re-rendered <img> revalidates instead of reusing
      // the old bytes. Nothing here re-baselines on a reply: no verb of the panel's writes a figure.
      const figs = figureTargets(this.status, this.ctx.path);
      const seen: FigureBaseline = {};
      for (const target of figs) {
        const v = await this.head(target);
        if (v) seen[target] = v.value;
      }
      const fm = figuresMoved(this.figureBase, figs, seen);
      this.figureBase = fm.next;
      if (fm.moved.length) { moved = true; fileMoved = true; }
      if (moved) {
        if (fileMoved) this.ctx.reload();            // the bytes changed under the view — repaint them
        await this.refresh();                        // fresh sidecar, log, and a new baseline
      }
    } finally { this.polling = false; }
  }
  /** One HEAD of the poll: the target's mtime verdict, or null when it says nothing this tick — a network blip (the next
   *  tick tries again), an unknown answer, or a 413/415, which retires the target (`stopped`) under the poll's row. */
  private async head(target: string): Promise<{ kind: "value"; value: string } | null> {
    if (this.stopped.has(target)) return null;
    let r: Response;
    try { r = await fetch(fileUrl(target, this.ctx.sid), { method: "HEAD", cache: "no-store" }); }
    catch { return null; }                           // a network blip: the next tick tries again
    const v: HeadVerdict = headVerdict(r.status, r.headers.get("X-Romp-Mtime-Ns"));
    if (v.kind === "stop") {
      this.stopped.add(target);
      // "checking … for changes", the guide's own words for this loop — never "watching": the row sits under
      // the Track changes toggle, and a tracked file whose refresh stopped is still tracked
      this.errors.set("poll", { text: "Stopped checking " + target + " for changes: the kernel answered " + v.status
        + (v.status === 413 ? " (too large to serve)" : " (not a type it serves)") + ". Reload to try again.", reload: true });
      this.render();
      return null;
    }
    return v.kind === "value" ? v : null;
  }

  // ── verbs ──────────────────────────────────────────────────────────────────────────────────────
  /** A mutating verb: consent first (decision 5), then the request with the fence from the current
   *  status; an `editing-off` refusal re-offers the consent and retries once; a moved fence re-issues
   *  status and retries once by the same args; a second refusal shows verbatim, with Reload when the
   *  store, file, or config moved. Resolves the fresh status, or null when nothing was written. */
  async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {
    // one write in flight per control: a second Enter or click during the round trip is not a second
    // write (the host mints a fresh id per `comment`, so a repeat would land twice); Save disables and
    // relabels itself meanwhile (renderComposer), the slot's loader shows for every other control
    if (this.busy.has(slot)) return null;
    this.busy.add(slot); this.busyVerb.set(slot, verb); this.errors.delete(slot); this.render();
    try {
      if (!(await this.requireStatus(slot))) return null;
      if (!(await this.ctx.ensureEditingAllowed())) { this.errors.set(slot, { text: "Nothing written: comments need file editing on.", reload: false }); return null; }
      return await this.mutateOnce(verb, args, slot, false);
    } finally { this.busy.delete(slot); this.busyVerb.delete(slot); this.render(); }
  }
  private async mutateOnce(verb: string, args: Record<string, unknown>, slot: string, retried: boolean): Promise<Status | null> {
    const s = this.status;
    const fence: Record<string, string> = { storeMtimeNs: s && s.storeMtimeNs !== null ? s.storeMtimeNs : "", configMtimeNs: s && s.configMtimeNs !== null ? s.configMtimeNs : "" };
    if (FILE_VERBS.has(verb)) fence.fileMtimeNs = s ? s.fileMtimeNs : "";   // reject rewrites the file: the file's mtime as last seen (FILE_VERBS)
    try {
      const r = await this.request(verb, args, fence);
      this.markOverlapped();                           // the status asks still out may have read the disk before this write
      this.applyStatus(r);
      // the file's bytes changed under the view: re-fetch them (the hunks and anchors in this reply index the NEW
      // text, and the poll will not do it — the reply just re-baselined it). The repaint arrives through onRendered.
      if (FILE_VERBS.has(verb) && r.fileMtimeNs && this.ctx.mtimeNs() && mtimeMoved(this.ctx.mtimeNs(), r.fileMtimeNs)) this.ctx.reload();
      return r;
    } catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off") {
        if (await this.ctx.ensureEditingAllowed(e.error)) return this.mutateOnce(verb, args, slot, true);
      } else if (!retried && MOVED.has(e.code)) {
        await this.refresh();
        if (e.code === "file-moved") this.ctx.reload();   // the file itself moved under the view: repaint its bytes (the poll's own moved branch)
        return this.mutateOnce(verb, args, slot, true);
      }
      this.errors.set(slot, { text: e.error, reload: MOVED.has(e.code) });
      return null;
    }
  }

  // ── Track changes ──────────────────────────────────────────────────────────────────────────────
  /** With no status behind it (refused, or never answered) the toggle showed "off" on nothing: re-ask under
   *  this control the way every other mutating control does (requireStatus: a second refusal is the row under
   *  the toggle, "Nothing written: …"), with the slot's loader for the wait. On an answer, act on what the
   *  click meant — turning tracking ON, since off is what showed: an untracked file gets the scope row; one
   *  that turns out tracked now reads so, which was the ask, and a second click stops it as usual. Never a
   *  click that only pulses (ui/CLAUDE.md: the result follows the acknowledgement). */
  async onTrackClick(): Promise<void> {
    let s = this.status;
    if (!s) {
      if (this.busy.has("track")) return;
      this.busy.add("track"); this.errors.delete("track"); this.render();
      try { if (!(await this.requireStatus("track"))) return; }
      finally { this.busy.delete("track"); this.render(); }
      s = this.status;
      if (!s) return;
      if (!s.trackedBy) { this.trackChoice = true; this.trackStop = false; this.render(); }
      return;
    }
    if (!s.trackedBy) { this.trackChoice = !this.trackChoice; this.trackStop = false; this.render(); return; }
    if (s.trackedBy.kind === "folder") { this.trackStop = !this.trackStop; this.trackChoice = false; this.render(); return; }
    // a file entry turns off directly; an inherited one is refused by the kernel naming the parent — the row shows it
    void this.mutate("set-tracked", { on: false, scope: "file" }, "track");
  }

  // ── commenting ─────────────────────────────────────────────────────────────────────────────────
  onSelection(sel: Selection): void {
    if (!this.open || this.ctx.mode() === "media" || !sel.rangeCount) return;
    // the seam fires for any selection inside the viewer's box, the aside included: a passage is text of the
    // FILE, so a selection in a card, the Log or the message preview offers nothing (it would only be refused)
    const body = this.ctx.body();
    if (!body.contains(sel.anchorNode) || !body.contains(sel.focusNode)) return;
    const rect = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    this.imageTarget = null;                           // a text selection replaces a picture as the float's subject
    this.showFloat(rect);
  }
  private showFloat(rect: { right: number; top: number }): void {
    const x = Math.min(Math.max(8, rect.right + 6), window.innerWidth - 90);
    const y = Math.min(Math.max(8, rect.top - 30), window.innerHeight - 34);
    this.float.style.left = x + "px"; this.float.style.top = y + "px";
    this.float.hidden = false;
  }
  /** A click on a rendered picture (the plan's Images and PDFs): with the panel open, the float offers
   *  Comment beside it; the anchor will be the embed's source text. A picture the source holds no embed
   *  for (an `src` the sanitizer rewrote, say) still gets the offer, and the composer then says why it
   *  cannot be placed — the offer must not silently do nothing. */
  onImageClick(img: HTMLElement): void {
    if (!this.open || this.ctx.mode() !== "rendered") return;
    const root = this.contentRoot(); const src = this.ctx.text();
    if (!root || src === null || !root.contains(img)) return;
    const e = embedFor(img, root, src, this.ctx.path);
    this.imageTarget = { range: e ? { start: e.start, end: e.end } : null };
    this.showFloat(img.getBoundingClientRect());
  }
  startImageComment(range: SourceRange | null): void {
    const src = this.ctx.text();
    if (src === null) return;
    this.openPanel();
    this.composer = range
      ? { kind: "comment", range, quote: src.slice(range.start, range.end), text: src, refusal: null }
      : { kind: "comment", range: null, quote: null, refusal: { ok: false, rawHasQuote: false, selText: "", reason: EMBED_NOT_FOUND_SELECT } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
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
    if (res.ok) this.composer = { kind: "comment", range: res.range, quote: res.quote, text: src, refusal: null };
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
    this.openCards.add(this.cardKey(id));
    this.composer = { kind: "reply", commentId: id, ref: card.ref };
    this.errors.delete("composer");
    this.repaintPresel();
    this.render();
    this.input.focus();
  }
  /** Reply on a change card: a comment bound to the change (comment {suggestionId, note}), so the session's
   *  answering track-edit folds into it and the message names the change ("on your change …"). */
  startChangeReply(id: string): void {
    const c = this.changeView().cards.find((x) => x.id === id);
    if (!c) return;
    this.openCards.add(c.key);
    this.composer = { kind: "change", changeId: id, ref: c.ref };
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
   *  target that passage — the one in the refused block, not an earlier copy of the same words
   *  (rawTarget) — so the presel mark shows it; otherwise scroll to the block's first line and leave the
   *  note waiting for a Raw selection. */
  switchToRaw(): void {
    let c = this.composer;
    if (c && c.kind === "region" && c.refusal) {
      // a region on a figure the source holds no embed for: nothing to anchor a region to, but a passage on the embed's
      // line can still carry the note. The composer becomes the one the picture click's offer builds for the same
      // figure (startImageComment), awaiting a Raw selection; the typed note stays in the input, the pending rectangle
      // leaves the overlay. The refusal's own sentence used to send the person to Cancel — the one exit that drops the note.
      c = this.composer = { kind: "comment", range: null, quote: null, refusal: { ok: false, rawHasQuote: false, selText: "", reason: EMBED_NOT_FOUND_SELECT } };
      this.errors.delete("composer");
      this.repaintPresel();
    }
    if (!c || c.kind !== "comment" || !c.refusal) return;
    this.ctx.setMode("raw");
    const src = this.ctx.text();
    if (src === null) return;
    const r = c.refusal;
    const range = rawTarget(src, r);
    if (range) {
      c.range = range; c.quote = src.slice(range.start, range.end); c.text = src; c.refusal = null;
      this.errors.delete("composer");                  // an Enter pressed under the refusal is answered now
      this.ctx.scrollToOffset(range.start);
      this.repaintPresel();
      this.renderComposer();
      this.input.focus();
      return;
    }
    if (typeof r.blockStartLine === "number") this.ctx.scrollToOffset(lineStartOffset(src, r.blockStartLine));
    this.renderComposer();
  }
  async saveComposer(): Promise<void> {
    const c = this.composer;
    const note = this.input.value.trim();
    if (!c || c.kind === "replace" || !note) return;   // a re-place takes a drag, not words
    if (c.kind === "region" && c.refusal) {
      this.errors.set("composer", { text: "Nothing saved: " + c.refusal + ".", reload: false });
      this.renderComposer();
      return;
    }
    if (c.kind === "comment" && c.refusal) {
      // nothing to save TO: the selection could not be placed, and a save here would silently become a
      // whole-file comment — the passage the person selected lost, and the session told "on this file"
      this.errors.set("composer", { text: "Nothing saved: select the passage in the Raw view first (Switch to Raw), or Cancel and use Comment on this file for a note on the whole file.", reload: false });
      this.renderComposer();
      return;
    }
    let r: Status | null;
    if (c.kind === "reply") r = await this.mutate("reply", { commentId: c.commentId, note }, "composer");
    else if (c.kind === "change") r = await this.mutate("comment", { suggestionId: c.changeId, note }, "composer");
    else if (c.kind === "region") {
      // the target in fractions of the natural size (E1), the host stamping the hash; a figure in rendered markdown
      // also carries the embed line's anchor, built over the text its range indexes as for a passage comment
      const args: Record<string, unknown> = { note, target: regionTarget(c.region, c.src) };
      if (c.range && c.text !== undefined) { args.anchor = makeAnchor(c.text, c.range); args.hintOffset = c.range.start; }
      r = await this.mutate("comment", args, "composer");
    } else {
      const args: Record<string, unknown> = { note };
      // the anchor is built over the text the range indexes (the selection's own, or the reload the passage
      // was re-found in), never over whatever sits at those offsets now; the host re-reads the file and
      // relocates by this anchor and hint, or refuses — a note aimed at one passage never lands on another
      const src = c.text === undefined ? null : c.text;
      if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }
      r = await this.mutate("comment", args, "composer");
    }
    if (r) this.closeComposer();                       // a refusal keeps the note where it was typed
  }

  // ── highlights ─────────────────────────────────────────────────────────────────────────────────
  cards(): Card[] { return this.status ? cardModel(this.status.store, this.status.hunks || [], this.status.log || []) : []; }
  /** The change cards, their paragraph groups over the current text, and the fold (GROUP_LIMIT). */
  changeView(): { cards: ChangeCard[]; groups: ChangeGroup[]; shown: ChangeGroup[]; hidden: ChangeGroup[]; hiddenChanges: number } {
    const s = this.status;
    const cards = s ? changeCards(s.store, s.hunks || [], s.log || []) : [];
    const groups = changeGroups(cards, this.ctx.mode() === "media" ? null : this.ctx.text());
    return { cards, groups, ...foldGroups(groups, this.moreChangesOpen) };
  }
  /** The card a comment id opens: the change card hosting it while its change is pending, else its own. */
  cardKey(commentId: string): string {
    const c = this.cards().find((x) => x.id === commentId);
    return c && c.hunk ? "chg:" + c.hunk.id : commentId;
  }
  /** Expand and scroll to a card by key — a change card inside the fold unfolds it first. */
  showCard(key: string): void {
    if (key.startsWith("chg:")) {
      const v = this.changeView();
      if (v.hidden.some((g) => g.changes.some((c) => c.key === key))) this.moreChangesOpen = true;
    }
    this.openCards.add(key);
    this.render();
    this.scrollCard(key);
  }
  /** Whether the view's text is the text the status's offsets index: the hunks are offsets into the file the
   *  host read, and after a reject (or a session write the poll has seen but the status has not) the two
   *  differ until the reload lands — painting changes over the other text would mark the wrong passages.
   *  An empty viewer mtime (the fetch not landed) claims nothing. */
  private textCurrent(s: Status): boolean {
    const vm = this.ctx.mtimeNs();
    return !vm || !s.fileMtimeNs || vm === s.fileMtimeNs;
  }
  /** Paint every open comment's anchor over the current view: located → the ring; quote gone but its
   *  context found → the text-changed ring; neither → card only, marked detached. Detached is a
   *  rendering state, never a stored flag. Then the changes (D4/D5): insertions and substitutions tinted
   *  over the new text, deletions struck at their point in Raw and card-only in Rendered, each mark
   *  carrying the change's id and the author's session colour. The composer's pending target is painted last. */
  paintAll(): void {
    const keep = this.bodyFocusKey();                  // a highlight or rectangle holding the keyboard: re-found after the pass
    this.located = new Map();
    this.paintedChanges = new Set();
    unpaintChanges(this.ctx.body());                   // before each repaint (D5): the marks are unwrapped, never stacked
    this.unpaint(".fc-hl, .fc-presel");                // a status refresh repaints the SAME body: never wrap twice
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) { this.paintRegions(); this.render(); return; }   // a media body: the overlay is its only paint (paintRegions keeps its own focus)
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
        // a highlight is a control (it opens the card): reachable by Tab, activated by Enter (KEY_ACTS), and
        // remembered as the panel's own (owns) — the one kind of control it puts among the file's markup
        for (const m of out || []) { (m as HTMLElement).tabIndex = 0; m.setAttribute("role", "button"); (m as HTMLElement).title = "Open the comment on this passage"; this.marks.add(m); }
        if (!painted && rendered && !card.target) {    // an embed line renders no text: the frame goes on its picture — unless the comment is a region, whose rectangle (paintRegions) is the mark
          const img = imgForRange(root, src, loc.range, this.ctx.path);
          if (img) { frameImage(img, cls, { act: "fcopen", id: card.id }); this.marks.add(img); painted = true; }
        }
      }
      this.located.set(card.id, { ...loc, painted });
    }
    this.paintChanges(root, src, rendered);
    this.refocusBody(keep);                            // the highlights and change marks are rebuilt; the rectangles keep their own (paintRegions)
    this.paintPresel(root, src, rendered);
    this.paintRegions();
    this.render();
  }
  // The marks in the BODY are controls too (KEY_ACTS: a highlight, a change mark, a rectangle), and every paint pass
  // rebuilds them — so a status landing while the keyboard was on one left it on the body, the way Enter on a card's
  // head once did in the aside (render's refocus mends the aside alone). The focused mark is re-found by what it IS,
  // the action plus the id of its subject, never by its node; the first match, since a highlight may span several.
  private bodyFocusKey(): { act: string; id: string } | null {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !this.marks.has(a) || !a.dataset || !a.dataset.act || !a.dataset.id) return null;
    return { act: a.dataset.act, id: a.dataset.id };
  }
  private refocusBody(k: { act: string; id: string } | null): void {
    if (!k) return;
    const a = document.activeElement;
    if (a && this.ctx.body().contains(a)) return;     // the mark survived the pass (paintedKey), or the focus moved on its own
    const n = this.ctx.body().querySelector('[data-act="' + k.act + '"][data-id="' + k.id + '"]') as HTMLElement | null;
    if (n && this.owns(n)) n.focus({ preventScroll: true });
  }
  /** The change marks, after the comment highlights (D5): stylesFor hands each mark the author's session colour
   *  from the Slice 1 colour map as `--fc-author` (nothing when unknown: the sheet's neutral). Every painted
   *  element is a control (it opens the card) and the panel's own (owns), like a comment highlight. */
  private paintChanges(root: Element, src: string, rendered: boolean): void {
    const s = this.status;
    if (!s || !(s.hunks || []).length || !this.textCurrent(s)) return;
    const store = s.store;
    const changes: ChangePaint[] = (s.hunks || []).map((h) => ({ id: h.id, kind: h.kind, curFrom: h.curFrom, curTo: h.curTo, oldText: h.oldText, author: h.author }));
    const stylesFor = (c: ChangePaint): Record<string, string> => {
      const aid = authorIdOf(store, c.id);
      const col = aid && this.colors ? this.colors.get(aid) : null;
      return col && col.color ? { "--fc-author": col.color.bg } : {};
    };
    let marks: Element[];
    if (rendered) {
      const r = paintChangesRendered(root, src, changes, stylesFor);
      for (const id of r.painted) this.paintedChanges.add(id);
      marks = Array.from(root.querySelectorAll('[data-act="fcchange"]'));
    } else {
      marks = paintChangesRaw(root, src, changes, stylesFor);
      for (const m of marks) { const id = (m as HTMLElement).dataset.id; if (id) this.paintedChanges.add(id); }
    }
    for (const m of marks) { (m as HTMLElement).tabIndex = 0; m.setAttribute("role", "button"); (m as HTMLElement).title = "Open this change"; this.marks.add(m); }
  }
  private paintPresel(root: Element, src: string, rendered: boolean): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.range || c.text !== src) return;   // the range indexes c.text; over other bytes it would paint the wrong span
    if (!rendered) { paintRaw(root, src, c.range, "fc-presel"); return; }
    const out = paintRendered(root, src, c.range, "fc-presel");
    if (!out || !out.length) { const img = imgForRange(root, src, c.range, this.ctx.path); if (img) frameImage(img, "fc-presel"); }
  }
  /** Unwrap painted marks: the text nodes go back in place and the parent is normalized. A framed
   *  picture is stripped of its marks instead — unwrapping an <img> would remove the picture. */
  private unpaint(selector: string): void {
    const marks = selector.split(",").map((s) => s.trim().replace(/^\./, ""));
    for (const n of Array.from(this.ctx.body().querySelectorAll(selector))) {
      if (n.classList.contains("fc-img")) { unframeImage(n as HTMLElement, marks); continue; }
      const p = n.parentNode; if (!p) continue;
      while (n.firstChild) p.insertBefore(n.firstChild, n);
      p.removeChild(n); p.normalize();
    }
  }
  private repaintPresel(): void {
    this.unpaint(".fc-presel");
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src !== null && root) this.paintPresel(root, src, this.ctx.mode() === "rendered");
    this.paintRegions();                               // the composer's pending region and the re-place cue live on the overlays
  }
  /** The body was repainted, possibly over NEW text (the poll saw the file move and reloaded it; Reload;
   *  a refresh): a pending passage is re-found through the anchor of its own text, so the presel, the
   *  chip and the hint follow the passage rather than its old offsets — a note typed while the session
   *  inserts a paragraph above still lands where it was aimed. Not re-found (the passage changed or went):
   *  the selection-time pair is kept, the chip says so, nothing is painted, and Save hands the host that
   *  anchor to rule on — it relocates, or refuses and the note stays. */
  private retargetComposer(): void {
    const c = this.composer; const src = this.ctx.text();
    if (!c || (c.kind !== "comment" && c.kind !== "region") || !c.range || c.text === undefined || src === null || src === c.text) return;
    const loc = locateComment(src, makeAnchor(c.text, c.range), c.range.start);
    if (loc.state === "located" && loc.range) { c.range = loc.range; c.text = src; }
  }
  // ── region comments (Slice 3): the overlays ─────────────────────────────────────────────────────
  /** The pictures that take an overlay in the current view: the media body's <img> (a PDF's frame takes none
   *  until Slice 4), or every figure in rendered markdown; none in Raw, where the embed line is the mark. */
  private regionImages(): HTMLImageElement[] {
    const mode = this.ctx.mode();
    if (mode === "media") {
      const m = this.ctx.mediaElement();
      return m && typeof m.tagName === "string" && m.tagName.toUpperCase() === "IMG" ? [m as HTMLImageElement] : [];
    }
    if (mode === "rendered") { const root = this.contentRoot(); return root ? (imgsIn(root) as HTMLImageElement[]) : []; }
    return [];
  }
  /** The picture a region comment is on, in the current view: the media body's for a standalone image; for an
   *  embedded figure the picture its anchor's embed line renders (exact), else the one whose src is the target's
   *  (the anchor detached, the figure still there). Null when the view shows none. */
  private regionImageFor(c: Card): HTMLImageElement | null {
    if (!c.target) return null;
    const imgs = this.regionImages();
    if (!imgs.length) return null;
    if (this.ctx.mode() === "media") return imgs[0];
    const root = this.contentRoot(); const src = this.ctx.text();
    const loc = this.located.get(c.id);
    if (root && src !== null && loc && loc.range) {
      const img = imgForRange(root, src, loc.range, this.ctx.path);
      if (img) return img as HTMLImageElement;
    }
    const dest = c.target.src;
    if (dest) {
      const hit = imgs.find((i) => pictureIsEmbed(i, dest, this.ctx.path));
      if (hit) return hit;
    }
    return null;
  }
  /** The author chip a rectangle wears: the label, and the session's colours as `--fc-author` / `--fc-author-fg`
   *  when the colour map knows the author (the sheet's fallback otherwise, and for `you`). */
  private chipFor(author: string, authorId: string | null): { label: string; style?: Record<string, string> } {
    if (author === "you") return { label: "you" };
    const c = authorId && this.colors ? this.colors.get(authorId) : null;
    if (!c) return { label: author || "unknown" };
    return c.color ? { label: c.name, style: { "--fc-author": c.color.bg, "--fc-author-fg": c.color.fg } } : { label: c.name };
  }
  /** The overlays: one layer per picture in view (built once per picture, dropped when the picture leaves), each
   *  repainted with the rectangles of the open region comments on it — placed by percentages, dashed when the
   *  image's bytes changed under them and marked unknown when that cannot be told (regionState), the author's chip
   *  and colour — plus the composer's pending region and the re-place cue. The drag is armed only while the panel
   *  is open and the pointer is fine (E5: a coarse pointer reads, and the whole-file comment stands in); the
   *  rectangles show whenever the highlights do. A painted rectangle is the comment's mark (located, painted): the
   *  card's reference links to it and offers no Reveal. A pending region whose picture was repainted is re-found
   *  (the media body's one picture; a figure by its embed's src). A layer is rebuilt only when what it would show
   *  changed (paintedKey): opening the panel, a status that moved nothing, a presel repaint elsewhere leave every
   *  rectangle — and the click pulse and keyboard focus on one — standing. */
  private paintRegions(): void {
    const keep = this.bodyFocusKey();
    const imgs = this.regionImages();
    for (const [img, layer] of this.regionLayers) if (!imgs.includes(img)) { layer.dispose(); this.regionLayers.delete(img); }
    if (!imgs.length) return;
    const s = this.status;
    const c = this.composer;
    if (c && c.kind === "region" && !imgs.includes(c.img)) {
      const again = this.ctx.mode() === "media" ? imgs[0]
        : c.src ? imgs.find((i) => pictureIsEmbed(i, c.src!, this.ctx.path)) : undefined;
      if (again) c.img = again;
    }
    const per = new Map<HTMLImageElement, RegionMark[]>();
    for (const card of this.cards()) {
      if (card.resolved || !card.target || card.target.kind !== "image") continue;
      const img = this.regionImageFor(card);
      if (!img) continue;
      const chip = this.chipFor(card.author, card.authorId);
      (per.get(img) || per.set(img, []).get(img)!).push({ id: card.id, region: card.target.region, label: chip.label, state: regionState(card.target, s), style: chip.style });
      const loc = this.located.get(card.id);
      this.located.set(card.id, loc ? { ...loc, painted: true } : { state: "located", painted: true });
    }
    const active = this.open && !isCoarsePointer();
    const rendered = this.ctx.mode() === "rendered";
    for (const img of imgs) {
      const marks = per.get(img) || [];
      const pending = c && c.kind === "region" && c.img === img && !c.refusal ? c.region : null;
      const replacing = !!c && c.kind === "replace" && this.replaceTarget(c.commentId) === img;
      // A figure in rendered markdown takes a layer only while the panel is open, or when there is something to put on it —
      // its rectangles, the pending region, the re-place cue. The wrapper is a layout of its own (the sheet's inline-block
      // around a block picture) standing in the AUTHOR's flow: wrapped on every paint, a right-floated README logo stopped
      // floating and a width="100%" plot shrank to its natural width, with the panel closed and no comment anywhere near
      // them (the 2026-09-06 review). Closed, a figure with nothing to show stays as the browser laid it out, and a layer
      // with nothing left to show comes down (closePanel's pass puts the picture back). The media body's one picture keeps
      // its layer as before: it is the file, in a box built for it, and its rectangles show whenever a text file's
      // highlights would (the probe's status paints both).
      const wanted = !rendered || this.open || marks.length > 0 || pending !== null || replacing;
      let layer = this.regionLayers.get(img);
      if (!wanted) { if (layer) { layer.dispose(); this.regionLayers.delete(img); } continue; }
      if (!layer) {
        // onClick is a PLAIN picture's click; a framed picture's (an embed-line comment's highlight, data-act="fcopen")
        // the layer hands to the picture itself (handOn), so the delegate's fcopen and the row's IMG listener hear it as
        // they did before the overlay stood over it
        layer = new RegionLayer(img, {
          onDraw: (i, r) => this.onRegionDrawn(i, r), onClick: (i) => this.onImageClick(i),
          onPress: () => { this.float.hidden = true; this.imageTarget = null; },   // what hideFloatOnDown does for a mousedown the overlay cancels
        });
        this.regionLayers.set(img, layer);
      }
      layer.setActive(active);
      const key = JSON.stringify([marks, pending, replacing]);
      if (this.paintedKey.get(layer) === key) continue;   // nothing new for this picture: its rectangles stand (paintedKey)
      this.paintedKey.set(layer, key);
      for (const r of layer.paint(per.get(img) || [], pending, replacing)) this.marks.add(r);
    }
    this.refocusBody(keep);
  }
  /** Whether any overlay in view takes a drag (the panel open, a fine pointer): the empty state names the gesture
   *  and the cards offer Re-place only then. */
  private drawsRegions(): boolean {
    for (const l of this.regionLayers.values()) if (l.active) return true;
    return false;
  }
  /** A region drawn on a picture (the overlay's onDraw). In re-place mode it is the comment's new place: `retarget`
   *  when drawn on the comment's own picture, refused under the card otherwise (the anchor stays on that figure's
   *  embed line, so another figure would make the two disagree). Otherwise the composer opens on the region; a
   *  figure in rendered markdown also needs the embed line's anchor (E1), found from the picture the way the picture
   *  click finds it, and a figure the source holds no embed for is refused with the reason, the note kept. */
  onRegionDrawn(img: HTMLImageElement, region: Region): void {
    const c = this.composer;
    if (c && c.kind === "replace") {
      const own = this.replaceTarget(c.commentId);
      if (own !== img) {
        this.errors.set("card:" + c.commentId, { text: own ? "Draw the new place on the figure this comment is on, not on another one." : "The figure this comment is on is not shown here.", reload: false });
        this.render();
        return;
      }
      this.composer = null;
      void this.mutate("retarget", { commentId: c.commentId, target: regionTarget(region, c.src) }, "card:" + c.commentId);
      this.repaintPresel();
      this.renderComposer();
      return;
    }
    this.openPanel();
    let src: string | null = null, range: SourceRange | null = null, text: string | undefined, refusal: string | null = null;
    if (this.ctx.mode() === "rendered") {
      const root = this.contentRoot(); const t = this.ctx.text();
      const e = root && t !== null ? embedFor(img, root, t, this.ctx.path) : null;
      if (e) { src = e.dest; range = { start: e.start, end: e.end }; text = t as string; }
      else refusal = EMBED_NOT_FOUND;
    }
    this.composer = { kind: "region", img, region, src, range, text, refusal };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  /** Re-place (a region card's button): the next region drawn on the comment's picture replaces its target (E3);
   *  the composer box carries the instruction, and Cancel keeps the region where it is. */
  startReplace(id: string): void {
    const card = this.cards().find((c) => c.id === id);
    if (!card || !card.target) return;
    this.openCards.add(this.cardKey(id));
    this.composer = { kind: "replace", commentId: id, ref: card.ref, src: card.target.src || null };
    this.errors.delete("composer"); this.errors.delete("card:" + id);
    this.repaintPresel();
    this.render();
  }
  /** The picture a re-place must be drawn on: the comment's own, when the view shows it. */
  private replaceTarget(commentId: string): HTMLImageElement | null {
    const card = this.cards().find((c) => c.id === commentId);
    return card ? this.regionImageFor(card) : null;
  }
  /** The card's thumbnail from the picture in view; a picture still loading re-renders the cards once, on its load. */
  private cropFor(img: HTMLImageElement, c: Card): HTMLCanvasElement | null {
    if (!c.target) return null;
    const crop = cropThumb(img, c.target.region);
    if (!crop && img.complete === false && !this.cropWait.has(img)) {
      this.cropWait.add(img);
      img.addEventListener("load", () => { this.cropWait.delete(img); this.render(); }, { once: true });
    }
    return crop;
  }
  goTo(key: string): void {
    const mark = key.startsWith("chg:")
      ? this.ctx.body().querySelector('[data-act="fcchange"][data-id="' + key.slice(4) + '"]')
      : this.ctx.body().querySelector('.fc-hl[data-id="' + key + '"], .fc-region[data-id="' + key + '"]');
    if (mark) { mark.scrollIntoView({ block: "center" }); return; }
    this.reveal(key);
  }
  /** Reveal: switch to Raw and scroll to the passage — a comment's located range, or a change's start — for
   *  a comment or change the Rendered view could not paint (a deletion never is), so the compact card never
   *  dead-ends. */
  reveal(key: string): void {
    if (key.startsWith("chg:")) {
      const c = this.changeView().cards.find((x) => x.key === key);
      if (!c) return;
      this.ctx.setMode("raw");
      this.ctx.scrollToOffset(c.curFrom);
      return;
    }
    const card = this.cards().find((c) => c.id === key);
    if (card && card.target) {                         // a region: the picture it is on, when the view shows it
      const img = this.regionImageFor(card);
      if (img) { img.scrollIntoView({ block: "center" }); return; }
    }
    const loc = this.located.get(key);
    if (!loc || !loc.range) return;
    this.ctx.setMode("raw");
    this.ctx.scrollToOffset(loc.range.start);
  }
  scrollCard(id: string): void {
    this.root?.querySelector('.fc-card[data-id="' + id + '"]')?.scrollIntoView({ block: "nearest" });
  }
  /** The absolute path the kernel acts on, as far as the panel can know it. The kernel resolves the viewer's
   *  path (`~`, a relative chat or todo token against the session's cwd, then realpath) and builds the sent
   *  message from THAT, so the preview and the folder label must name it too (contract C3: identical text).
   *  No reply carries the resolved path itself; the store's own `path` is the file relative to the project
   *  root, written by the host from the resolved path (store-io's relPathFor, corrected on every load), so
   *  root + path IS it whenever a sidecar exists — and a preview needs unsent comments, so one does. With no
   *  sidecar, an absolute viewer path is the kernel's up to a symlink; a relative one names nothing, and the
   *  caller then says less rather than something wrong. */
  filePath(): string | null {
    const s = this.status;
    const rel = s && s.store ? s.store.path : null;
    if (s && s.root && typeof rel === "string" && rel && !rel.startsWith("/")) return s.root.replace(/\/$/, "") + "/" + rel;
    return this.ctx.path.startsWith("/") ? this.ctx.path : null;
  }

  // ── Send to session ────────────────────────────────────────────────────────────────────────────
  /** Fixed sequence (the plan's UX, D5): the message is built from the CURRENT status FIRST (a bound
   *  comment's desc needs the change's old and new text, which accept-all removes), then set-tracked when
   *  asked, then accept-all when asked, then fileCommentsSend with `tracked` set to the post-toggle verdict
   *  and `accepted` = what the log says is unsent plus the N the accept-all just decided; a refusal at any
   *  step aborts before the send. The comments are already on disk, so a refusal loses nothing. */
  async doSend(): Promise<void> {
    const s = this.status;
    if (!s || this.statusRefusal || this.sending || !this.ctx.sid) return;   // statusRefusal: renderSend says why
    const parts: SendParts = sendParts(s);
    const pending = (s.hunks || []).length;
    const acceptAll = this.sendOpts.accept && pending > 0;
    let tracked = !!s.trackedBy;
    this.sending = true; this.errors.delete("send"); this.render();
    try {
      if (this.sendOpts.track && !s.trackedBy) {
        const r = await this.mutate("set-tracked", { on: true, scope: "file" }, "send");
        if (!r) return;
        tracked = !!r.trackedBy;
      }
      if (acceptAll) {
        const a = await this.mutate("accept-all", {}, "send");
        if (!a) return;                                // a refused accept-all sends nothing: the message would claim decisions never made
      }
      const counts = sendCounts(parts, acceptAll, pending);
      const answerTodo = !!this.ctx.todoId && this.sendOpts.todo && !this.todoAnswered;
      const msg: Record<string, unknown> = {
        sid: this.ctx.sid, path: this.ctx.path, tracked, comments: parts.comments,
        accepted: counts.accepted, rejected: counts.rejected, watermark: parts.watermark,
      };
      if (answerTodo) msg.todoId = this.ctx.todoId;
      const reply = await this.sendOnce(msg, false);
      this.markOverlapped();                           // the send appended to the comments log: a status out meanwhile may predate it
      // the latch is the STAMP, not the attempt: a send the kernel warned it could not mark (user todos off,
      // the todo already settled) leaves the checkbox, so the todo is answerable from here once the switch
      // is back on; the settled case re-warns on a later send, honestly, until the kernel says which it was
      if (answerTodo && reply.todoStamped) { this.todoAnswered = true; answeredTodos.add(this.ctx.todoId!); }
      const who = this.sessionName();
      this.sentNote = reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now());
      if (reply.warning) this.errors.set("send", { text: reply.warning, reload: false, warn: true });
      this.sendConfirm = false; this.previewOpen = false;
      await this.refresh();
    } catch (err) {
      this.errors.set("send", { text: (err as { error: string }).error, reload: false });
    } finally { this.sending = false; this.render(); }
  }

  /** The send itself, with the one retry every editing-off refusal gets (mutateOnce's branch): the kernel
   *  refuses a send while file editing is off, because the send's log entry is a disk write and a send the
   *  log cannot record would be offered again (kernel: _file_comments_send_op). The refusal's text carries
   *  the phrase the consent helper matches, so the panel re-offers the consent naming the machine and, on
   *  yes, sends once more; a no, or a second refusal, is the caller's error row. */
  private async sendOnce(msg: Record<string, unknown>, retried: boolean): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    try { return await this.requestSend(msg); }
    catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off" && await this.ctx.ensureEditingAllowed(e.error)) return this.sendOnce(msg, true);
      throw err;
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────────────────────────
  render(): void {
    if (!this.root || !this.open) return;
    const s = this.status;
    const { head, cards, send, log } = this.sections;
    if (!this.root.contains(head)) this.root.replaceChildren(head, this.composerBox, cards, send, log);   // built once per open
    const keep = this.focusKey();                      // the control holding focus, by identity: the rebuild detaches it
    head.replaceChildren(this.renderHead(s));
    this.renderComposer();
    cards.replaceChildren(this.renderCards(s));
    send.replaceChildren(this.renderSend(s));
    log.replaceChildren(this.renderLog(s));
    if (keep) this.refocus(keep);
  }
  // Every section's children are rebuilt per render, and a removed element loses its focus to the body — so
  // Enter on a card's head opened the card and left the keyboard nowhere: the second Enter did nothing (or
  // fell through to the chat's composer), and the person had to Tab back in after every toggle. The composer's
  // input persists for the same reason (the sections comment); the rebuilt controls are re-found instead, by
  // what they ARE — the action plus the id, key or slot that names its subject — never by their node, the way
  // render.ts refocuses the active tab after `#tabs` is rebuilt.
  private focusKey(): { act: string; id?: string; key?: string; slot?: string } | null {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !this.root || !this.root.contains(a) || !a.dataset) return null;
    if (a.dataset.act) return { act: a.dataset.act, id: a.dataset.id, key: a.dataset.key, slot: a.dataset.slot };
    if (a.dataset.opt) return { act: "opt", key: a.dataset.opt };   // a confirm checkbox, re-found by its option
    return null;
  }
  private refocus(k: { act: string; id?: string; key?: string; slot?: string }): void {
    if (!this.root || this.root.contains(document.activeElement)) return;   // still focused (the input): nothing to mend
    if (k.act === "opt") { (this.root.querySelector('[data-opt="' + k.key + '"]') as HTMLElement | null)?.focus({ preventScroll: true }); return; }
    for (const n of Array.from(this.root.querySelectorAll("[data-act]")) as HTMLElement[]) {
      const d = n.dataset;
      if (d.act !== k.act || d.id !== k.id || d.key !== k.key || d.slot !== k.slot) continue;
      // the first FOCUSABLE match: a collapsed card carries the head's act and id too, but no tabindex
      if ((n.tabIndex >= 0 || n.tagName.toUpperCase() === "BUTTON") && !(n as HTMLButtonElement).disabled) { n.focus({ preventScroll: true }); return; }
    }
  }
  private errRow(slot: string): HTMLElement | null {
    const e = this.errors.get(slot);
    if (!e) return null;
    const row = el("div", "fileview-err fc-err" + (e.warn ? " fc-err-warn" : ""));
    row.dataset.slot = slot;
    const text = el("span", undefined, e.text);
    text.style.overflowWrap = "anywhere";              // the host names paths in its refusals; the poll names its target
    row.appendChild(text);
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
      // the folder of the path the kernel acts on (filePath); when the panel cannot name it, the label says
      // "Its folder" and no more — the host computes the entry from the real path either way
      const abs = this.filePath();
      const f = btn(abs ? "Its folder " : "Its folder", "fctrackfolder");
      if (abs) { appendPath(f, folderOf(abs)); shrinkable(f); }
      f.title = "Everything under the folder, files not written yet included";
      pick.appendChild(f);
      pick.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(pick);
    }
    if (this.trackStop && s?.trackedBy) {
      const stop = el("div", "fc-row fc-choice");
      const ask = el("span", "fc-note", "Stop tracking everything under ");
      appendPath(ask, s.trackedBy.entry); ask.appendChild(document.createTextNode("?"));
      stop.appendChild(ask);
      stop.appendChild(btn("Stop", "fctrackstop"));
      stop.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(stop);
    }
    for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll")]) if (n) head.appendChild(n);
    // a Reload from the head's or the poll's row: the slot wears the loader where the row was, until the answer (refresh)
    for (const n of [this.loader("head"), this.loader("poll")]) if (n) head.appendChild(n);
    if (s && s.agentTooling === "absent") {
      head.appendChild(el("div", "fc-warn", "The session cannot reply to comments yet: the track-changents tooling is not linked into ~/.claude on the file's machine. Run romp's install.sh there."));
    }
    return head;
  }
  private renderComposer(): void {
    const c = this.composer;
    const box = this.composerBox;
    box.hidden = !c;
    if (!c) { this.input.hidden = false; return; }   // a re-place hid it; the next note needs it
    const ref = this.composerRef;
    ref.replaceChildren();
    this.input.hidden = c.kind === "replace";          // a re-place takes a drag on the picture, not words
    if (c.kind === "reply") ref.appendChild(el("span", "fc-note", "Reply on " + c.ref));
    else if (c.kind === "change") ref.appendChild(el("span", "fc-note", "Reply on the change " + c.ref));
    else if (c.kind === "replace") ref.appendChild(el("span", "fc-note", "Drag the comment's new place on the image (now " + c.ref + "). Cancel keeps it where it is."));
    else if (c.kind === "region") {
      if (c.refusal) {
        // no embed line, so no region — but a passage on that line can carry the note, and the switch keeps it (switchToRaw)
        // where Cancel drops it (closeComposer clears the input): the sentence points at the switch, never at Cancel
        ref.appendChild(el("span", "fc-note fc-refused", c.refusal[0].toUpperCase() + c.refusal.slice(1) + ". Select its line in the Raw view instead; the note stays."));
        const sw = btn("Switch to Raw", "fcraw");
        sw.title = "Raw view; select the line that embeds this image there";
        ref.appendChild(sw);
      } else {
        ref.appendChild(el("span", "fc-note", "On " + regionDesc(c.region)));
        const crop = cropThumb(c.img, c.region);
        if (crop) ref.appendChild(crop);
        if (c.range && c.text !== undefined && c.text !== this.ctx.text()) {   // the file changed and the embed line was not re-found (retargetComposer)
          const t = el("span", "fc-tag", "passage changed");
          t.title = "The file changed and the line embedding this figure was not found in it; Save asks the file's machine to place it, and refuses if it cannot";
          ref.appendChild(t);
        }
      }
    }
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
      if (c.range && c.text !== undefined && c.text !== this.ctx.text()) {   // the file changed and the passage was not re-found in it (retargetComposer)
        const t = el("span", "fc-tag", "passage changed");
        t.title = "The file changed and this passage was not found in it; Save asks the file's machine to place it, and refuses if it cannot";
        ref.appendChild(t);
      }
    } else ref.appendChild(el("span", "fc-note", "On this file"));
    const acts = this.composerActs;
    const saving = this.busy.has("composer");
    const save = btn(saving ? "Saving…" : "Save", "fcsave");
    save.disabled = saving;                            // posts-and-waits: disabled and relabeled for the round trip (ui/CLAUDE.md)
    this.input.readOnly = saving;                      // what is typed during the round trip would be lost with the note that lands
    // a refused mapping has nothing to save to — Raw or Cancel; Save would silently write a whole-file comment; a
    // refused region likewise, and a re-place saves nothing (the drawn region is the action)
    const noSave = c.kind === "replace" || ((c.kind === "comment" || c.kind === "region") && !!c.refusal);
    acts.replaceChildren(...(noSave ? [] : [save]), btn("Cancel", "fccancel"));
    const err = this.composerErr;
    err.replaceChildren(...[this.loader("composer"), this.errRow("composer")].filter((n): n is HTMLElement => !!n));
    if (!box.contains(this.input)) box.replaceChildren(ref, this.input, acts, err);   // built once; the input keeps its focus across renders
  }
  private renderCards(s: Status | null): HTMLElement {
    const list = el("div", "fc-cards");
    // a comment bound to a pending change is shown on that change's card; the rest stand on their own
    const cards = this.cards().filter((c) => c.hunk === null);
    const view = this.changeView();
    if (!s) {
      // a wait wears the romp loader while a status ask is out (refresh); once the kernel refused, say what
      // follows — the reason and Reload are the head's row. Never a line claiming a read nothing is making.
      const w = this.loader("status");
      if (w) list.appendChild(w);
      else if (this.statusRefusal) list.appendChild(el("div", "fc-empty", "The comments could not be read, so none can be shown or written."));
      return list;
    }
    if (!cards.length && !view.cards.length) {
      // the gesture is named wherever an overlay in view takes it (drawsRegions): the media body's picture, or a figure in
      // rendered markdown — the panel's guidance is the one place the drag is discoverable from; the overlay's own label
      // reaches assistive tech alone, and the crosshair names nothing
      const draws = this.drawsRegions();
      list.appendChild(el("div", "fc-empty", this.ctx.mode() === "media"
        ? (draws ? "No comments yet. Drag a rectangle on the image, or comment on this file." : "No comments yet. Comment on this file to leave one.")
        : draws ? "No comments yet. Select a passage and press Comment, drag a rectangle on a figure, or comment on this file."
        : "No comments yet. Select a passage and press Comment, or comment on this file."));
      return list;
    }
    // the session's pending changes first: grouped by paragraph, the first GROUP_LIMIT groups shown, the rest
    // behind one row (moreChangesOpen), then Accept all · Reject all — the plan's Slice 2 surface
    if (view.cards.length) {
      for (const g of view.shown) {
        if (g.title) { const gh = el("div", "fc-note fc-group", g.title); gh.title = "The paragraph these changes fall in"; list.appendChild(gh); }
        for (const c of g.changes) list.appendChild(this.renderChangeCard(c));
      }
      if (view.hiddenChanges) {
        const more = btn(moreChangesLabel(view.hiddenChanges), "fcmore", "fc-sec");
        more.title = "Show every change"; more.setAttribute("aria-expanded", "false");
        list.appendChild(more);
      } else if (this.moreChangesOpen && view.groups.length > GROUP_LIMIT) {
        const fewer = btn("▾ Fewer changes", "fcmore", "fc-sec");
        fewer.setAttribute("aria-expanded", "true");
        list.appendChild(fewer);
      }
      list.appendChild(this.renderChangesFoot(view.cards.length));
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
    const picture = c.target ? this.regionImageFor(c) : null;   // the picture the region is on, in this view; null when it shows none
    const card = el("div", "fc-card" + (isOpen ? " open" : "") + (loc && loc.state === "detached" ? " fc-card-detached" : ""));
    card.dataset.id = c.id;
    // the expand/collapse target: the whole card while collapsed, the HEAD alone once open — the open body
    // is text to select and copy (the sheet gives it cursor: text), and a click there must not fold the card
    // away from under the selection. The head is a Tab stop and takes Enter/Space (KEY_ACTS).
    if (!isOpen) card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.dataset.id = c.id; head.dataset.act = "fccard";
    head.tabIndex = 0; head.setAttribute("role", "button"); head.setAttribute("aria-expanded", isOpen ? "true" : "false");
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.kind === "passage" ? "“" + c.ref + "”" : c.ref);
    ref.title = c.kind === "passage" ? c.anchor?.quote || c.ref : c.ref;
    if ((c.anchor || c.target) && loc && loc.painted) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.id; ref.classList.add("fc-link"); ref.title = c.target ? "Scroll to the region" : "Scroll to the passage";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    }
    head.appendChild(ref);
    // a region (Slice 3): whether the image still has the bytes it was drawn on (E2) — dashed on the picture, a tag here
    const regionSt = c.target ? regionState(c.target, this.status) : "current";
    // A RESOLVED region has no staleness left to report: the plan and the guide end "stale" at resolve or re-place, the
    // picture paints no rectangle for it (paintRegions), and the card offers no Re-place — so the stale tag, whose title
    // names that button, and the unknown tag and note would point at nothing. Its card wears "resolved" alone (the
    // 2026-09-06 review, which found a resolved region wearing both).
    const shownSt = c.resolved ? "current" : regionSt;
    if (shownSt === "stale") { const t = el("span", "fc-tag fc-tag-stale", "stale"); t.title = "The image changed after this region was drawn; Re-place it, or resolve it"; head.appendChild(t); }
    if (shownSt === "unknown" && c.target) { const t = el("span", "fc-tag", "unknown"); t.title = unknownReason(c.target, this.status); head.appendChild(t); }
    // a region whose picture this view does not show, with no passage to reveal in its place: a standalone image's region
    // seen in the SVG Source view (the XML). No seam call returns to the picture from here (setMode is the markdown
    // pair only), so the tag names the way back rather than leaving the card a dead end (ui/CLAUDE.md)
    if (c.target && !c.anchor && !picture && this.ctx.mode() !== "media") {
      const t = el("span", "fc-tag", "not shown");
      t.title = this.ctx.media() === "svg" ? "The Source view shows the XML, not the image; press Source again to see the region on it" : "This view does not show the image the region is on";
      head.appendChild(t);
    }
    if (loc && loc.state === "context") head.appendChild(el("span", "fc-tag", "text changed"));
    if (loc && loc.state === "detached") head.appendChild(el("span", "fc-tag", "detached"));
    if (c.decision) { const d = el("span", "fc-tag", c.decision); d.title = "You " + c.decision + " the change this comment is on"; head.appendChild(d); }
    if (c.resolved) head.appendChild(el("span", "fc-tag", "resolved"));
    if (c.replies.length && !isOpen) head.appendChild(el("span", "fc-tag fc-count", String(c.replies.length)));
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (!isOpen) { card.appendChild(el("div", "fc-preview", c.body.replace(/\s+/g, " ").trim())); return card; }
    if (picture) { const crop = this.cropFor(picture, c); if (crop) card.appendChild(crop); }   // the region cut from the picture (E5)
    card.appendChild(el("div", "fc-body", c.body));
    // the open card says in words why the region's staleness is unknown (unknownReason): the tag's title never reaches touch
    if (shownSt === "unknown" && c.target) card.appendChild(el("div", "fc-note", unknownReason(c.target, this.status)));
    if (c.replies.length) card.appendChild(this.renderTurns(c.replies));
    const acts = el("div", "fc-actions");
    const reply = btn("Reply", "fcreply"); reply.dataset.id = c.id; acts.appendChild(reply);
    const res = btn(c.resolved ? "Reopen" : "Resolve", "fcresolve"); res.dataset.id = c.id; res.dataset.on = c.resolved ? "0" : "1"; acts.appendChild(res);
    if (picture && !c.resolved && this.drawsRegions()) {   // Re-place needs the picture in view and a pointer that can draw
      const rp = btn("Re-place", "fcreplace"); rp.dataset.id = c.id;
      rp.title = regionSt === "stale" ? "The image changed: draw the region again where it belongs now" : "Draw the region again; the comment keeps its words";
      acts.appendChild(rp);
    }
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
  /** The turns under a comment, in `ts` order: words as before; a revision (the session's answering
   *  track-edit, recorded as a reply with old and new text) as the same row with the texts instead of a body. */
  private renderTurns(turns: CardTurn[]): HTMLElement {
    const rs = el("div", "fc-replies");
    for (const r of turns) {
      const row = el("div", "fc-reply" + (r.author === "you" ? " fc-reply-you" : ""));
      const meta = el("div", "fc-meta");
      meta.appendChild(this.chip(r.author, r.authorId));
      if (r.kind === "rev") { const t = el("span", "fc-tag", "revised"); t.title = "The session revised the text in answer"; meta.appendChild(t); }
      meta.appendChild(el("span", "fc-time", clock(r.ts)));
      row.appendChild(meta);
      row.appendChild(r.kind === "msg" ? el("div", "fc-body", r.body) : this.diffBody(r.oldText, r.newText));
      rs.appendChild(row);
    }
    return rs;
  }
  /** Old and new text as a body: the old struck (<del>), the new marked (<ins>) — the browser's own dress for
   *  both, so the sheets need no rule for it; either side may be empty (a pure insertion or deletion). */
  private diffBody(oldText: string, newText: string): HTMLElement {
    const b = el("div", "fc-body fc-diff");
    if (oldText) b.appendChild(el("del", "fc-old", oldText));
    if (oldText && newText) b.appendChild(document.createTextNode(" → "));
    if (newText) b.appendChild(el("ins", "fc-new", newText));
    if (!oldText && !newText) b.appendChild(el("span", "fc-note", "(no text)"));
    return b;
  }
  // ── the change cards (Slice 2) ─────────────────────────────────────────────────────────────────
  /** One card per pending change. Collapsed: the author's chip, the one-line reference (a link to its mark
   *  when the view shows one), and the buttons — Accept and Reject are the card's reason to exist, so they
   *  never hide behind the expand. Open: the old and new text, and the comments bound to the change with
   *  their turns and their own Reply and Resolve. Reveal on a deletion (never painted in Rendered; a point in
   *  Raw) and on any change whose mark the view does not show, so the compact card never dead-ends. */
  private renderChangeCard(c: ChangeCard): HTMLElement {
    const isOpen = this.openCards.has(c.key);
    const painted = this.paintedChanges.has(c.id);
    const slot = "change:" + c.id;
    const card = el("div", "fc-card fc-change" + (isOpen ? " open" : ""));
    card.dataset.id = c.key; card.dataset.change = c.id; card.dataset.kind = c.kind;
    if (!isOpen) card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.dataset.id = c.key; head.dataset.act = "fccard";
    head.tabIndex = 0; head.setAttribute("role", "button"); head.setAttribute("aria-expanded", isOpen ? "true" : "false");
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.ref);
    ref.title = c.kind === "ins" ? "Added: " + c.newText : c.kind === "del" ? "Removed: " + c.oldText : c.oldText + " → " + c.newText;
    if (painted) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.key; ref.classList.add("fc-link"); ref.title = "Scroll to the change";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    }
    head.appendChild(ref);
    const src = this.ctx.text();
    if (!painted && src !== null && this.ctx.mode() !== "media") {
      const t = el("span", "fc-tag", "not shown");
      t.title = this.ctx.mode() === "rendered" && c.kind === "del" ? "The Rendered view cannot show a deletion; Reveal opens it in Raw" : "This view does not show the change; Reveal opens it in Raw";
      head.appendChild(t);
    }
    if (c.comments.length && !isOpen) head.appendChild(el("span", "fc-tag fc-count", String(c.comments.length)));
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (isOpen) {
      card.appendChild(this.diffBody(c.oldText, c.newText));
      for (const cm of c.comments) card.appendChild(this.renderHosted(cm));
    }
    const acts = el("div", "fc-actions");
    const busy = this.busy.has(slot); const verb = this.busyVerb.get(slot);
    const ok = btn(busy && verb === "accept" ? "Accepting…" : "Accept", "fcaccept"); ok.dataset.id = c.id; ok.disabled = busy;
    ok.title = "Keep the text as it is and drop the change";
    const no = btn(busy && verb === "reject" ? "Rejecting…" : "Reject", "fcreject"); no.dataset.id = c.id; no.disabled = busy;
    no.title = "Put the old text back in the file";
    acts.appendChild(ok); acts.appendChild(no);
    if (!c.comments.length) {   // with a comment on the card, the comment's own Reply is the way to answer it
      const re = btn("Reply", "fcchangereply"); re.dataset.id = c.id; re.title = "Comment on this change; the session's answer comes back to it";
      acts.appendChild(re);
    }
    if (c.kind === "del" || !painted) {
      const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.key;
      rv.title = "Show the change in the Raw view" + (src !== null ? " (line " + (rawOffsetToLine(src, c.curFrom) + 1) + ")" : "");
      acts.appendChild(rv);
    }
    card.appendChild(acts);
    for (const n of [this.loader(slot), this.errRow(slot)]) if (n) card.appendChild(n);
    return card;
  }
  /** A comment bound to the change, ON its card (the plan's contract): the comment's own words and turns in
   *  the reply dress, with its Reply and Resolve — the same acts a standalone card has, by the comment's id. */
  private renderHosted(c: Card): HTMLElement {
    const box = el("div", "fc-hosted");
    box.dataset.id = c.id;
    const row = el("div", "fc-reply" + (c.author === "you" ? " fc-reply-you" : ""));
    const meta = el("div", "fc-meta");
    meta.appendChild(this.chip(c.author, c.authorId));
    if (c.resolved) meta.appendChild(el("span", "fc-tag", "resolved"));
    meta.appendChild(el("span", "fc-time", clock(c.ts)));
    row.appendChild(meta);
    row.appendChild(el("div", "fc-body", c.body));
    box.appendChild(row);
    if (c.replies.length) box.appendChild(this.renderTurns(c.replies));
    const acts = el("div", "fc-actions");
    const reply = btn("Reply", "fcreply"); reply.dataset.id = c.id; acts.appendChild(reply);
    const res = btn(c.resolved ? "Reopen" : "Resolve", "fcresolve"); res.dataset.id = c.id; res.dataset.on = c.resolved ? "0" : "1"; acts.appendChild(res);
    box.appendChild(acts);
    for (const n of [this.loader("card:" + c.id), this.errRow("card:" + c.id)]) if (n) box.appendChild(n);
    return box;
  }
  /** Accept all · Reject all, while any change is pending. Reject all rewrites the file, so it asks once,
   *  pane-locally (the folder-off confirm's idiom), naming the count. */
  private renderChangesFoot(n: number): HTMLElement {
    const foot = el("div", "fc-foot");
    const row = el("div", "fc-actions");
    const busy = this.busy.has("changes"); const verb = this.busyVerb.get("changes");
    const all = btn(busy && verb === "accept-all" ? "Accepting…" : "Accept all", "fcacceptall"); all.disabled = busy;
    all.title = "Keep the text as it is and drop every change";
    const none = btn(busy && verb === "reject-all" ? "Rejecting…" : "Reject all", "fcrejectall"); none.disabled = busy;
    none.title = "Put the old text back for every change";
    none.setAttribute("aria-expanded", this.rejectAllConfirm ? "true" : "false");
    row.appendChild(all); row.appendChild(none);
    foot.appendChild(row);
    if (this.rejectAllConfirm) {
      const ask = el("div", "fc-row fc-choice");
      ask.appendChild(el("span", "fc-note", "Put the old text back for " + (n === 1 ? "the change" : "all " + n + " changes") + "?"));
      ask.appendChild(btn("Reject all", "fcrejectallgo"));
      ask.appendChild(btn("Cancel", "fcrejectallcancel"));
      foot.appendChild(ask);
    }
    for (const x of [this.loader("changes"), this.errRow("changes")]) if (x) foot.appendChild(x);
    return foot;
  }
  private renderSend(s: Status | null): HTMLElement {
    const box = el("div", "fc-send");
    const n = s ? unsentCount(s.unsent) : 0;
    const b = btn(this.sending ? "Sending…" : "Send to session" + (n ? " (" + n + ")" : ""), "fcsend");
    // a status refusal (refresh, requireStatus) leaves the LAST status showing so the cards stay readable, but
    // what is unsent was derived from a disk the kernel can no longer read for us: a file deleted or moved
    // since, a sidecar gone corrupt. A send built from that would go out and be recorded (or re-recorded)
    // against a state that may no longer hold — the duplicate-send leg of the review's finding — so Send
    // stands down until a fresh status lands (applyStatus clears the refusal; Reload in the head asks).
    const stale = !!this.statusRefusal;
    b.disabled = !s || !n || this.sending || !this.ctx.sid || stale;
    b.title = !this.ctx.sid ? "No session owns this file; open it from a session's link or todo to send"
      : stale ? "The comments could not be re-read; Reload above, then send"
      : !n ? "Nothing unsent: every comment, reply, and decision has gone" : "Hand everything unsent to the session as one message";
    box.appendChild(b);
    // why Send is off, VISIBLE (the GitHub link's caption idiom): a tooltip never reaches touch, and a
    // disabled button takes no focus. Nothing-unsent is captioned only once there are comments to have sent.
    if (!this.ctx.sid) box.appendChild(el("div", "fc-note", "No session owns this file; open it from a session's link or todo to send."));
    else if (stale && s && n) box.appendChild(el("div", "fc-note", "The comments could not be re-read, so nothing can be sent until Reload above succeeds."));
    else if (s && !n && !this.sending && this.cards().length) box.appendChild(el("div", "fc-note", "Nothing unsent: every comment, reply, and decision has gone."));
    if (this.sendConfirm && s && n && !this.sending) {
      const parts = sendParts(s);
      const pending = (s.hunks || []).length;
      // the same A and R the send will carry (doSend): the log's unsent decisions plus the pending changes the
      // checkbox accepts on the way — so the list and the preview show the sent text
      const counts = sendCounts(parts, this.sendOpts.accept, pending);
      const cf = el("div", "fc-confirm");
      cf.appendChild(el("div", "fc-note", "This goes to " + this.sessionName() + ":"));
      const ul = el("ul", "fc-list");
      for (const c of parts.comments) {
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", c.desc + ": "));
        li.appendChild(el("span", undefined, c.body.replace(/\s+/g, " ").trim()));
        ul.appendChild(li);
      }
      if (counts.accepted || counts.rejected) ul.appendChild(el("li", undefined, counts.accepted + " accepted, " + counts.rejected + " rejected"));
      cf.appendChild(ul);
      const opts = el("div", "fc-opts");
      if (this.ctx.todoId && !this.todoAnswered) opts.appendChild(this.opt("todo", "answer the todo this file was opened from"));
      if (!s.trackedBy) opts.appendChild(this.opt("track", "turn on tracking so the session's edits come back as changes"));
      if (pending) opts.appendChild(this.opt("accept", "accept the " + pending + " pending " + (pending === 1 ? "change" : "changes")));
      if (opts.childNodes.length) cf.appendChild(opts);
      const pv = btn((this.previewOpen ? "▾ " : "▸ ") + "The message", "fcpreview", "fc-sec");
      cf.appendChild(pv);
      if (this.previewOpen) {
        const media = this.ctx.media() === "image" || this.ctx.media() === "pdf";
        const tracked = !!s.trackedBy || this.sendOpts.track;   // the post-toggle verdict the send will carry
        // the path the kernel will name (filePath), never the spelling the viewer was opened with: a relative
        // todo token or a `~/` link would preview a header and two --file arguments the session never receives
        const abs = this.filePath();
        if (abs === null) cf.appendChild(el("div", "fc-note", "The message names this file by its absolute path, which the kernel resolves from " + this.ctx.path + "; this panel cannot show it."));
        else cf.appendChild(el("pre", "fc-msg", buildSendMessage({ absPath: abs, comments: parts.comments, accepted: counts.accepted, rejected: counts.rejected, tracked, media })));
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
  private opt(key: "todo" | "track" | "accept", label: string): HTMLElement {
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
    // one row per entry is the glance; what the entry holds underneath — the bodies a send carried, the diff of
    // a direct edit — is one click down, keyed so a poll re-render keeps it open (ui/CLAUDE.md: never dead-end)
    for (const e of [...rows].reverse()) {
      const key = String(e.ts) + "|" + String(e.kind);
      const detail = this.logDetail(e);
      const isOpen = !!detail && this.openLog.has(key);
      const row = el("div", "fc-log-row");
      row.appendChild(el("span", "fc-time", clock(e.ts)));
      row.appendChild(el("span", undefined, logRowText(e, nameOf)));
      if (detail) {
        // the row becomes a control; the fold glyph joins its text span, so the row stays time + text (the
        // sheets size it as exactly that) and a re-render keeps it open through openLog
        row.classList.toggle("open", isOpen);
        row.dataset.act = "fclogrow"; row.dataset.key = key;
        row.setAttribute("role", "button"); row.style.cursor = "pointer";
        row.tabIndex = 0; row.setAttribute("aria-expanded", isOpen ? "true" : "false");   // a Tab stop; Enter/Space through KEY_ACTS
        row.title = isOpen ? "Hide" : e.kind === "send" ? "Show what was sent" : e.kind === "edit" ? "Show the edit" : "Show the changes";
        (row.childNodes[1] as HTMLElement).textContent = (isOpen ? "▾ " : "▸ ") + logRowText(e, nameOf);
      }
      box.appendChild(row);
      if (detail && isOpen) box.appendChild(detail);
    }
    if (s?.logTruncated) box.appendChild(el("div", "fc-note", "Showing the last " + rows.length + " entries."));
    return box;
  }
  /** What a Log row has underneath, or null when the line IS the whole entry (a tracking toggle). A send
   *  entry holds the comments as they went — each with what it referred to, in the confirm's own list dress;
   *  an edit entry holds the kernel's diff of the direct edit; an accept or reject entry holds the changes it
   *  decided, old and new text, which the sidecar has since forgotten. */
  private logDetail(e: { kind: string; [k: string]: unknown }): HTMLElement | null {
    if ((e.kind === "accept" || e.kind === "reject") && Array.isArray(e.changes) && e.changes.length) {
      const box = el("div", "fc-log-detail");
      const ul = el("ul", "fc-list");
      for (const ch of e.changes as Array<Record<string, unknown>>) {
        if (!ch || typeof ch !== "object") continue;
        const li = el("li");
        const oldText = typeof ch.oldText === "string" ? ch.oldText : "", newText = typeof ch.newText === "string" ? ch.newText : "";
        li.appendChild(this.diffBody(oldText, newText));
        ul.appendChild(li);
      }
      box.appendChild(ul);
      return box;
    }
    if (e.kind === "send" && Array.isArray(e.comments) && e.comments.length) {
      const box = el("div", "fc-log-detail");
      const ul = el("ul", "fc-list");
      for (const c of e.comments as Array<Record<string, unknown>>) {
        if (!c || typeof c !== "object") continue;
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", String(c.desc ?? "on this file") + ": "));
        li.appendChild(el("span", undefined, String(c.body ?? "")));
        ul.appendChild(li);
      }
      box.appendChild(ul);
      return box;
    }
    if (e.kind === "edit") {
      const f = (e.summary && typeof e.summary === "object" ? e.summary : e) as Record<string, unknown>;
      if (typeof f.diff !== "string" || !f.diff) return null;
      const box = el("div", "fc-log-detail");
      box.appendChild(el("pre", "fc-msg", f.diff));
      if (f.truncated === true) box.appendChild(el("div", "fc-note", "The diff was cut short; the file holds the rest."));
      return box;
    }
    return null;
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
