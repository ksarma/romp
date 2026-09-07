// Types for the vendored track-changents modules the editor chunk bundles (vendor/track-changents/, pinned
// upstream commit plus its patch series; see the README there). They are CommonJS with no declaration files,
// and nothing romp writes may sit under vendor/ (the drift test pins that tree to upstream's file set), so the
// declarations live here. Pattern ambient modules ("*/…") are how TypeScript types a RELATIVE import of a .js
// file this tsconfig does not compile: module resolution finds the file, cannot type it (no allowJs), and
// then falls back to the matching pattern. A `declare module` with a relative name is not allowed, hence the
// leading `*`. Only what romp calls is declared; the vendored sources document the rest.
//
// The record types are declared once, in the engine's block, and imported by the others through the same
// pattern name. anchor-map.ts imports the engine too; its `// @ts-ignore` line predates this file and is now a
// no-op, as its comment anticipated.

declare module "*/vendor/track-changents/engine.js" {
  /** A pending change as the sidecar stores it (the storage format's word is "suggestion"): the span it occupies
   *  in the CURRENT text starts at `from` and runs the length of `newText`; a deletion is a zero-width point with
   *  its `oldText`. Records may carry more fields than these; the extras ride along untouched. */
  export interface TrackRecord {
    id: string;
    author?: string;
    authorId?: string;
    ts?: number;
    kind?: string;
    from: number;
    newText?: string;
    oldText?: string;
    anchor?: unknown;
    [extra: string]: unknown;
  }
  /** toHunks' per-record view: the span in the current text and in the derived baseline, and the two texts. */
  export interface TrackHunk {
    id: string;
    author: string;
    ts: number;
    kind: "ins" | "del" | "sub";
    curFrom: number;
    curTo: number;
    baseFrom: number;
    baseTo: number;
    oldText: string;
    newText: string;
    anchor: unknown;
  }
  /** A CodeMirror-style change spec in pre-image coordinates. */
  export interface TrackEdit { from: number; to: number; insert: string }
  export function toHunks(suggestions: TrackRecord[]): TrackHunk[];
  export function baselineOf(current: string, suggestions: TrackRecord[]): string;
  export function ingestHumanChanges(suggestions: TrackRecord[], changes: TrackEdit[], mint?: (baseId: string, n: number) => string): TrackRecord[];
  export function acceptSuggestion(suggestions: TrackRecord[], id: string): { edit: null; suggestions: TrackRecord[] };
  export function rejectSuggestion(suggestions: TrackRecord[], id: string): { edit: TrackEdit | null; suggestions: TrackRecord[] };
  export function acceptSuggestions(suggestions: TrackRecord[], ids: string[]): { edits: TrackEdit[]; suggestions: TrackRecord[] };
  export function rejectSuggestions(suggestions: TrackRecord[], ids: string[]): { edits: TrackEdit[]; suggestions: TrackRecord[] };
  export function acceptAll(suggestions: TrackRecord[]): { edits: TrackEdit[]; suggestions: TrackRecord[] };
  export function rejectAll(suggestions: TrackRecord[]): { edits: TrackEdit[]; suggestions: TrackRecord[] };
  /** A comment anchor: the quoted text with `ctx` (default 24) characters of context either side. */
  export function makeAnchor(text: string, from: number, to: number, ctx?: number): { quote: string; prefix: string; suffix: string };
  export function locateAnchor(text: string, anchor: unknown, hint?: number): { from: number; to: number } | null;
  export function messageStillPending(current: string, anchor: unknown): boolean;
}

declare module "*/vendor/track-changents/obsidian/src/track-cm.js" {
  import type { AnnotationType, Extension, StateEffectType, StateField } from "@codemirror/state";
  import type { TrackRecord } from "*/vendor/track-changents/engine.js";
  /** Replace the record list (an accept, a reject, or loading the store). */
  export const setSuggestions: StateEffectType<TrackRecord[]>;
  /** Replace the side data the overlay reads: whether tracking is on, and the comments to highlight. */
  export const setTrackMeta: StateEffectType<{ trackingOn: boolean; comments: unknown[] }>;
  /** Marks a load/sync dispatch so a persist listener does not echo it back. */
  export const syncAnnotation: AnnotationType<boolean>;
  /** The record-list field: a factory, one instance per extension set. */
  export function makeSuggestionField(): StateField<TrackRecord[]>;
  /** The undo glue: the previous record list stored as the inverse of any transaction that changed it. */
  export function makeInvertedEffects(field: StateField<TrackRecord[]>): Extension;
}

declare module "*/vendor/track-changents/obsidian/src/track-logic.js" {
  import type { TrackHunk } from "*/vendor/track-changents/engine.js";
  /** planDiffDisplay's item: a hunk plus how to show it; a merged paragraph carries the ids it stands for. */
  export interface DisplayItem extends TrackHunk {
    display: "inline" | "block" | "deletion" | "paragraph";
    ids?: string[];
  }
  export function planDiffDisplay(hunks: TrackHunk[], baseline: string, current: string): DisplayItem[];
  export function idsOf(item: DisplayItem | null | undefined): string[];
  export function shouldShowTrackUI(trackingOn: boolean, pendingChangeCount: number, commentCount: number): boolean;
  export function frontmatterEnd(text: string): number;
  export function keptEmbedTokens(text: string, current: string): string[];
  export function segmentsByKeptTokens(line: string, keptTokens: string[]): Array<{ text: string; kept: boolean }>;
}
