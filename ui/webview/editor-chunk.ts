// The file viewer's EDITING SUBSTRATE (the user 2026-08-22): CodeMirror 6 replacing the raw-mode
// textarea. This module is its OWN esbuild entry (dist/editor-chunk.js), loaded on demand by
// file-view.ts the first time someone enters edit mode — people who never edit download nothing,
// and the main chat/feed bundles stay byte-stable (they import nothing from here; the contract is
// the window global below). CodeMirror's own ecosystem is the plugin system, curated HERE per the
// no-plugin-API doctrine (2026-08-20): syntax highlighting by file extension, local word
// autocomplete, bracket matching + auto-indent, in-buffer search, history/undo. EXPLICITLY OUT:
// language servers (an IDE's maintenance tail; agent-assisted edits through the message flow are
// the smart path), themes beyond the dashboard's own look, and any romp-level extension surface.
//
// The ONE romp-level addition is the typed, internal `track` mount option (plans/file-review.md,
// decision 14, 2026-09-06): a tracked file's pending changes ride into the editor as marks (an
// insertion tinted, a deletion struck inline, a substitution as both), typing remaps them rather
// than desyncing them, click accepts and modifier-click rejects, and undo restores either. It is an
// OPTION of the mount call, consumed only by file-view.ts, with a fixed shape — not an extension
// hook, not a way to register anything: the record-list field is the vendored track-changents
// field (vendor/track-changents/obsidian/src/track-cm.js, bundled unchanged), the marks are romp's
// derived track-decorations.ts, and both are curated here like every other extension. The handle
// hands back the remapped records and a net ledger of decisions so a Save can send both, and the
// one rule romp adds over the field's ids keeps those two lists disjoint: an id the ledger holds is
// never minted again (the filter in trackSetup).
//
// The SAVE PATH IS NOT THIS MODULE'S: the consent gate, the nanosecond conflict floor, and the
// edit trace all live behind file-view's saveFile op — this is the text surface only, handing the
// same string to the same op. Byte fidelity is the mount contract: value() returns the buffer
// EXACTLY (CodeMirror joins lines with \n and never invents or strips a trailing newline; the
// CRLF restore stays file-view's, as it was for the textarea). In-editor accept and reject are
// buffer-local until that save: nothing here persists anything.
import { EditorState, StateEffect, StateField, Transaction, type Extension, type TransactionSpec } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap, indentWithTab, invertedEffects, isolateHistory } from "@codemirror/commands";
import { bracketMatching, indentOnInput, syntaxHighlighting, defaultHighlightStyle, StreamLanguage } from "@codemirror/language";
import { autocompletion, completeAnyWord, closeBrackets, closeBracketsKeymap, completionKeymap } from "@codemirror/autocomplete";
import { search, searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { css } from "@codemirror/lang-css";
import { html } from "@codemirror/lang-html";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { yaml } from "@codemirror/legacy-modes/mode/yaml";
import { toml } from "@codemirror/legacy-modes/mode/toml";
import { setSuggestions, syncAnnotation, makeSuggestionField, makeInvertedEffects } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import * as engine from "../../vendor/track-changents/engine.js";
import { trackDecorations, idsAtPosition, type TrackHost, type TrackRecord } from "./track-decorations";

/** The curated extension→language map, as a pure NAME so tests can pin the curation without a DOM.
 *  null = no highlighter (plain text) — everything else about the editor still applies. */
export function langNameFor(ext: string): string | null {
  const e = (ext || "").toLowerCase();
  if (["js", "jsx", "ts", "tsx", "mjs", "cjs"].includes(e)) return "javascript";
  if (["py", "pyi"].includes(e)) return "python";
  if (e === "css") return "css";
  if (["html", "htm", "svg", "vue"].includes(e)) return "html";
  if (e === "json") return "json";
  if (["md", "markdown"].includes(e)) return "markdown";
  if (["sh", "bash", "zsh", "bats"].includes(e)) return "shell";
  if (["yml", "yaml"].includes(e)) return "yaml";
  if (e === "toml") return "toml";
  return null;
}

function langExt(ext: string): Extension[] {
  switch (langNameFor(ext)) {
    case "javascript": return [javascript({ typescript: /^[cm]?tsx?$/.test(ext.toLowerCase()), jsx: /x$/.test(ext.toLowerCase()) })];
    case "python": return [python()];
    case "css": return [css()];
    case "html": return [html()];
    case "json": return [json()];
    case "markdown": return [markdown()];
    case "shell": return [StreamLanguage.define(shell)];
    case "yaml": return [StreamLanguage.define(yaml)];
    case "toml": return [StreamLanguage.define(toml)];
    default: return [];
  }
}

// The dashboard's own look and nothing more: the panel palette from styles.css, the accent only
// where the app already uses it (selection, matches, focus cues — via color-mix over var(--accent),
// which resolves to the dark literal rgba(156,210,255,…) washes exactly), the mono stack and 13px
// the viewer's read mode already renders — no new fonts, no new sizes (the font-size rule; and like
// the timeline, an adopted style must DECLARE font-family, never inherit a host's). Built per mount,
// not per module: `dark` is a CodeMirror-side branch (its base theme for panels/popups), so it must
// read the LIVE body class — a module-load constant froze the first theme forever (and was
// hardcoded { dark: true }, which kept the search panel near-black under body.theme-light — the
// user 2026-09-02, who saw a near-black file editor).
function rompTheme(): Extension {
  const light = typeof document !== "undefined" && document.body.classList.contains("theme-light");
  return EditorView.theme({
    "&": { height: "100%", fontSize: "13px", backgroundColor: "var(--bg, #1e1e1e)", color: "var(--fg, #d4d4d4)" },
    ".cm-content": { fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", caretColor: "var(--fg, #d4d4d4)" },
    ".cm-scroller": { fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", overflow: "auto" },
    "&.cm-focused": { outline: "none" },
    ".cm-gutters": { backgroundColor: "var(--bg, #1e1e1e)", color: "var(--dim, #8a8f98)", border: "none",
      borderRight: "1px solid var(--hairline, #3a3a3a)" },
    ".cm-activeLine": { backgroundColor: "var(--overlay-05, rgba(255, 255, 255, 0.06))" },
    ".cm-activeLineGutter": { backgroundColor: "var(--overlay-05, rgba(255, 255, 255, 0.06))" },
    ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": {
      backgroundColor: "color-mix(in srgb, var(--accent, #9cd2ff) 22%, transparent)" },
    ".cm-selectionMatch": { backgroundColor: "color-mix(in srgb, var(--accent, #9cd2ff) 14%, transparent)" },
    ".cm-matchingBracket": { backgroundColor: "color-mix(in srgb, var(--accent, #9cd2ff) 18%, transparent)",
      outline: "1px solid color-mix(in srgb, var(--accent, #9cd2ff) 40%, transparent)" },
    ".cm-cursor": { borderLeftColor: "var(--fg, #d4d4d4)" },
    // the search panel wears the shared menu vocabulary (one dropdown skin, 2026-08-09)
    ".cm-panels": { backgroundColor: "var(--surface-raised, #252526)", color: "var(--fg, #d4d4d4)",
      borderTop: "1px solid var(--box-border, rgba(255, 255, 255, 0.12))" },
    ".cm-panel.cm-search input, .cm-panel.cm-search button": {
      fontFamily: "inherit", fontSize: "12px", background: "var(--bg, #1e1e1e)",
      color: "var(--fg, #d4d4d4)", border: "1px solid var(--box-border, rgba(255, 255, 255, 0.12))", borderRadius: "4px" },
  }, { dark: !light });
}

// ── the track option: pending changes as marks, decisions as a ledger ────────────────────────────

/** One decision on one record: its id and the two texts as the record held them at that moment. */
export interface TrackLedgerEntry { id: string; oldText: string; newText: string }
/** The decisions taken inside the editor since the mount, NET of undo: an undone accept or reject leaves no
 *  entry, a redone one puts it back. A later save sends this beside the remapped records. */
export interface TrackLedger { accepted: TrackLedgerEntry[]; rejected: TrackLedgerEntry[] }

export interface TrackOpts {
  /** The file's pending changes, as the sidecar's status returned them (the storage format's records). */
  suggestions: unknown[];
  /** The author's session colour for the marks' `--fc-author`, or null for none. */
  authorColor?: (author: string) => string | null;
  /** Called with the new ledger whenever a decision lands, is undone, or is redone. */
  onLedger?: (ledger: TrackLedger) => void;
}

/** What the mount handle exposes when `track` was given. Both read the LIVE state: the records as the field
 *  holds them now (remapped through every keystroke since the mount), and the net ledger. No id is in both: a
 *  decided id is never minted again for a later split (trackSetup's id filter), which is what the host's save
 *  requires of the two lists it is sent. */
export interface TrackHandle { suggestions(): unknown[]; ledger(): TrackLedger }

export interface EditorHandle {
  value(): string;
  focus(): void;
  destroy(): void;
  track?: TrackHandle;
}

export interface MountOpts {
  text: string;               // the buffer, LF-normalized by the caller (same as the textarea got)
  ext: string;                // file extension, picks the highlighter
  onChange: () => void;       // any doc change — the caller derives dirty from value() (an accept changes no
                              // text and fires onLedger instead; a reject changes text and fires both)
  onSave: () => void;         // Mod-s inside the editor — same chord the textarea honored
  track?: TrackOpts;          // the file's pending changes; absent for an untracked file
}

export const EMPTY_LEDGER: TrackLedger = { accepted: [], rejected: [] };

type Decision = { side: "accepted" | "rejected"; entries: TrackLedgerEntry[] };
// A decision and its inverse are a pair of effects: a decision transaction carries `decide`, history stores
// `undecide` as its inverse (invertedEffects), so an undo REMOVES the entries and the redo of that undo puts
// them back. The ledger is a fold over these effects and nothing else — no counter, no diff of id sets (a
// record the person types over vanishes from the field with no decision, and a split record gets new ids).
const decide = StateEffect.define<Decision>();
const undecide = StateEffect.define<Decision>();

/** Pure: the ledger with `d`'s entries added (`add`) or removed. Returns the SAME object when nothing changes,
 *  so a listener can key on identity. An id sits on one side at most: a decision on an id replaces any earlier
 *  entry for it on either side. */
export function applyDecision(ledger: TrackLedger, d: Decision, add: boolean): TrackLedger {
  const ids = new Set(d.entries.map((e) => e.id));
  const strip = (list: TrackLedgerEntry[]) => list.filter((e) => !ids.has(e.id));
  const other: Decision["side"] = d.side === "accepted" ? "rejected" : "accepted";
  const same = strip(ledger[d.side]);
  const next: TrackLedger = { accepted: ledger.accepted, rejected: ledger.rejected };
  next[other] = strip(ledger[other]);
  next[d.side] = add ? [...same, ...d.entries] : same;
  const unchanged = (["accepted", "rejected"] as const).every((k) =>
    next[k].length === ledger[k].length && next[k].every((e, i) => e === ledger[k][i]));
  return unchanged ? ledger : next;
}

/** The pure half of a mount's track option: the vendored field, the ledger, the marks and the decision
 *  transactions, built without a view so a test can drive them through EditorState + history alone. */
export interface TrackSetup {
  extensions: Extension[];
  /** Apply ONCE to the fresh state, before any view exists: the records and the meta, outside history. */
  seed: TransactionSpec;
  suggestions(state: EditorState): TrackRecord[];
  ledger(state: EditorState): TrackLedger;
  /** The transaction that accepts (or, with `reject`, rejects) the change whose display item starts at `from`:
   *  the engine's remapped records, the buffer edits of a reject, and the ledger entries, in ONE transaction
   *  isolated in history, so one undo reverses the whole decision. null when nothing starts at `from`. */
  resolve(state: EditorState, from: number, reject: boolean): TransactionSpec | null;
}

export function trackSetup(opts: TrackOpts): TrackSetup {
  const field = makeSuggestionField();
  const ledgerField = StateField.define<TrackLedger>({
    create: () => EMPTY_LEDGER,
    update(value, tr) {
      let out = value;
      for (const e of tr.effects) {
        if (e.is(decide)) out = applyDecision(out, e.value, true);
        else if (e.is(undecide)) out = applyDecision(out, e.value, false);
      }
      return out;
    },
  });
  const ledgerInvert = invertedEffects.of((tr) => {
    const out: StateEffect<Decision>[] = [];
    for (const e of tr.effects) {
      if (e.is(decide)) out.push(undecide.of(e.value));
      else if (e.is(undecide)) out.push(decide.of(e.value));
    }
    return out;
  });
  // Romp's one rule over the field's ids (2026-09-06): an id the ledger holds is never minted again. The engine
  // mints a split's right half against the ids in play NOW (`X~1` for the first split of X) and the vendored field
  // passes it no `mint` — sound where every decision persists at once, as upstream's does, but here a decided
  // fragment leaves the field for the ledger, so the next split of the same parent minted `X~1` a second time: a
  // save then named one id as decided AND pending, which the host refuses (requireDecisions) though the records fit
  // the text, and a decision on the new `X~1` replaced the earlier entry by id, so the first was never logged. This
  // filter reads what the field made of the change and renames any id the ledger holds to the parent's next free
  // suffix (the engine's own scheme); the renamed list lands as an explicit setSuggestions on the same transaction,
  // which the field takes verbatim and history snapshots as it does any list. Undo and redo dispatch with
  // filter:false and restore recorded lists, where the rule already held. Only a doc change can mint, an explicit
  // list never does, and an empty ledger has nothing to collide with, so those three are checked before the
  // transaction's state is read; when no id collides the transaction passes through and the state it computed is
  // the one the dispatch uses.
  const ledgerIds = (l: TrackLedger) => new Set([...l.accepted, ...l.rejected].map((e) => e.id));
  const freshIds = EditorState.transactionFilter.of((tr) => {
    if (!tr.docChanged || tr.effects.some((e) => e.is(setSuggestions))) return tr;
    const start = tr.startState.field(ledgerField);
    if (!start.accepted.length && !start.rejected.length) return tr;
    const ops = tr.state.field(field);
    const decided = ledgerIds(tr.state.field(ledgerField));
    if (!ops.some((o) => decided.has(String(o.id)))) return tr;
    const taken = new Set([...decided, ...ops.map((o) => String(o.id))]);
    const renamed = ops.map((o) => {
      const id = String(o.id);
      if (!decided.has(id)) return o;
      const parent = id.replace(/~\d+$/, "");   // a fragment's parent is its id less the last suffix
      let n = 1, fresh: string;
      while (taken.has(fresh = `${parent}~${n}`)) n++;
      taken.add(fresh);
      return { ...o, id: fresh };
    });
    return [tr, { effects: setSuggestions.of(renamed) }];
  });
  const records = opts.suggestions as TrackRecord[];
  const setup: TrackSetup = {
    extensions: [],
    // The records alone: the overlay shows while any record is pending (the meta field keeps its default —
    // the option does not know whether tracking is on, and carries no comments).
    seed: {
      effects: [setSuggestions.of(records)],
      annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
    },
    suggestions: (state) => state.field(field),
    ledger: (state) => state.field(ledgerField),
    resolve(state, from, reject) {
      const ops = state.field(field);
      const ids = idsAtPosition(ops, state.doc.toString(), from);
      if (!ids.length) return null;
      const want = new Set(ids);
      const entries = ops.filter((o) => want.has(String(o.id)))
        .map((o) => ({ id: String(o.id), oldText: o.oldText || "", newText: o.newText || "" }));
      const r = reject ? engine.rejectSuggestions(ops, ids) : engine.acceptSuggestions(ops, ids);
      const spec: TransactionSpec = {
        effects: [setSuggestions.of(r.suggestions), decide.of({ side: reject ? "rejected" : "accepted", entries })],
        annotations: isolateHistory.of("full"),
      };
      if (r.edits.length) spec.changes = r.edits;
      return spec;
    },
  };
  const host: TrackHost = {
    // No panel is reachable from the chunk, and the option feeds no comments; a comment mark's click goes nowhere.
    onOpenPanel: () => {},
    resolveInline: (from, reject, view) => {
      const spec = setup.resolve(view.state, from, reject);
      if (spec) view.dispatch(spec);
    },
    hasResolvableAt: (view, from) => idsAtPosition(view.state.field(field, false) || [], view.state.doc.toString(), from).length > 0,
    // Nothing persists mid-edit: a save reads the field and the ledger through the handle.
    onOpsChanged: () => {},
    // The seed is applied to the initial state before the view exists, so there is nothing to load here.
    hydrateView: () => {},
  };
  setup.extensions = [
    field, makeInvertedEffects(field),
    ledgerField, ledgerInvert, freshIds,
    ...trackDecorations(field, host, { authorColor: opts.authorColor }),
    EditorView.updateListener.of((u) => {
      if (opts.onLedger && u.startState.field(ledgerField) !== u.state.field(ledgerField)) opts.onLedger(u.state.field(ledgerField));
    }),
  ];
  return setup;
}

/** The editor's extension set, apart from the view so a test can build an EditorState from it without a
 *  DOM and check what the state carries (editor-lazy.test.ts). `track` (a trackSetup) adds the record field,
 *  the marks and the click handlers; the caller applies its seed to the state it creates. */
export function extensionsFor(ext: string, opts: Pick<MountOpts, "onChange" | "onSave">, track?: TrackSetup | null): Extension[] {
  return [
    lineNumbers(), highlightActiveLine(), drawSelection(),
    history(),
    indentOnInput(), bracketMatching(), closeBrackets(),
    autocompletion({ override: [completeAnyWord] }),   // LOCAL word completion — no servers, by design
    search({ top: true }),
    highlightSelectionMatches(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    ...langExt(ext),
    // long lines soft-wrap while editing, as they do in the read view (the user 2026-09-04; the view has
    // always wrapped since 2026-08-24, with no toggle) — a display facet, so the buffer, its newlines and
    // the cursor are untouched, and the textarea fallback wraps the same way (file-view.ts enterFallback)
    EditorView.lineWrapping,
    rompTheme(),
    keymap.of([
      { key: "Mod-s", run: () => { opts.onSave(); return true; } },
      ...closeBracketsKeymap, ...defaultKeymap, ...searchKeymap,
      ...historyKeymap, ...completionKeymap, indentWithTab,
    ]),
    EditorView.updateListener.of((u) => { if (u.docChanged) opts.onChange(); }),
    // the track option's extensions: keymap-free — its gestures are the mouse's (mousedown/click), not chords
    ...(track ? track.extensions : []),
  ];
}

export function mount(host: HTMLElement, opts: MountOpts): EditorHandle {
  const track = opts.track ? trackSetup(opts.track) : null;
  let state = EditorState.create({ doc: opts.text, extensions: extensionsFor(opts.ext, opts, track) });
  // The records enter the INITIAL state, outside history: the first paint shows the marks, no undo step
  // reaches before them, and the handle reads them from the first tick (no microtask a caller could race).
  if (track) state = state.update(track.seed).state;
  const view = new EditorView({ parent: host, state });
  const handle: EditorHandle = {
    value: () => view.state.doc.toString(),
    focus: () => view.focus(),
    destroy: () => view.destroy(),
  };
  if (track) handle.track = { suggestions: () => track.suggestions(view.state), ledger: () => track.ledger(view.state) };
  return handle;
}

// The mount contract with file-view.ts: a window global, NOT an import — an import would drag all
// of CodeMirror into the main render bundle and break the lazy discipline this chunk exists for.
// (guarded: the test bundle imports langNameFor under node, where there is no window)
if (typeof window !== "undefined") (window as any).__rompEditor = { mount, langNameFor };
