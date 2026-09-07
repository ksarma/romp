// The curated emoji list behind the tab menu's picker (2026-09-07): its shape, checked for real. Every
// entry is exactly one fully-qualified emoji the kernel's validator accepts as written (a base with the
// U+FE0F selector where the code point is text-default, a keycap, a two-letter flag, or a joined
// sequence), no skin tones (out of scope: the free-text field takes them), no duplicates, every category
// drawn, names and keywords present and plain. Node's own Unicode tables do the checking: Intl.Segmenter
// for "one grapheme", the \p{Emoji} property escapes for "an emoji code point".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EMOJI_CATEGORIES } from "./emoji-data";

// Intl.Segmenter is Node 16+ and typed in the ES2022 lib; the extension compiles against ES2021, so it is reached untyped
const seg: { segment(s: string): Iterable<unknown> } = new (Intl as any).Segmenter("en", { granularity: "grapheme" });
const cps = (s: string): number[] => Array.from(s, (ch) => ch.codePointAt(0) as number);
const ZWJ = 0x200D, VS16 = 0xFE0F, VS15 = 0xFE0E, KEYCAP = 0x20E3;
const isRI = (cp: number) => cp >= 0x1F1E6 && cp <= 0x1F1FF;
const isTag = (cp: number) => cp >= 0xE0020 && cp <= 0xE007F;
const isTone = (cp: number) => cp >= 0x1F3FB && cp <= 0x1F3FF;
const isEmojiCp = (cp: number) => /\p{Emoji}/u.test(String.fromCodePoint(cp));
const hasPresentation = (cp: number) => /\p{Emoji_Presentation}/u.test(String.fromCodePoint(cp));

const ALL = EMOJI_CATEGORIES.flatMap((c) => c.items.map((it) => ({ cat: c.id, emoji: it[0], name: it[1], keywords: it[2] })));

test("the nine categories, in the picker's order, each with an icon and items", () => {
  assert.deepEqual(EMOJI_CATEGORIES.map((c) => c.id),
                   ["smileys", "people", "animals", "food", "travel", "activities", "objects", "symbols", "flags"]);
  assert.deepEqual(EMOJI_CATEGORIES.map((c) => c.label),
                   ["Smileys", "People", "Animals & nature", "Food & drink", "Travel & places", "Activities", "Objects", "Symbols", "Flags"]);
  for (const c of EMOJI_CATEGORIES) {
    assert.ok(c.items.length > 0, c.id + " has items");
    assert.equal([...seg.segment(c.icon)].length, 1, c.id + "'s icon is one emoji");
  }
  assert.ok(ALL.length >= 400 && ALL.length <= 600, "a curated list, not a Unicode dump: " + ALL.length);
});

test("every entry is exactly one emoji: one grapheme, emoji code points only, fully qualified, no skin tone", () => {
  for (const { emoji, name } of ALL) {
    const where = name + " " + JSON.stringify(emoji);
    assert.equal([...seg.segment(emoji)].length, 1, "one grapheme: " + where);
    const c = cps(emoji);
    for (let i = 0; i < c.length; i++) {
      const cp = c[i];
      assert.ok(!isTone(cp), "no skin tone: " + where);
      assert.notEqual(cp, VS15, "no text presentation selector: " + where);
      assert.ok(isEmojiCp(cp) || cp === ZWJ || cp === VS16 || cp === KEYCAP || isTag(cp), "an emoji code point: " + where);
      // fully qualified: a text-default emoji code point carries the emoji selector right after it
      if (isEmojiCp(cp) && !hasPresentation(cp) && cp !== ZWJ && cp !== VS16 && cp !== KEYCAP && !isRI(cp) && !isTag(cp)) {
        assert.equal(c[i + 1], VS16, "text-default code point U+" + cp.toString(16).toUpperCase() + " needs U+FE0F: " + where);
      }
    }
    // a flag is exactly two regional indicators; a keycap is base + FE0F + 20E3
    if (isRI(c[0])) assert.ok(c.length === 2 && isRI(c[1]), "a flag is two regional indicators: " + where);
    if (c.includes(KEYCAP)) assert.deepEqual(c.slice(1), [VS16, KEYCAP], "a keycap is base, U+FE0F, U+20E3: " + where);
  }
});

test("no duplicate emoji anywhere, no duplicate name within a category; names and keywords are plain lowercase words", () => {
  const seen = new Map<string, string>();
  for (const { cat, emoji, name, keywords } of ALL) {
    const prior = seen.get(emoji);
    assert.equal(prior, undefined, `${JSON.stringify(emoji)} appears twice (${prior} and ${cat}/${name})`);
    seen.set(emoji, cat + "/" + name);
    assert.match(name, /^[a-z0-9]+(?:[ -][a-z0-9]+)*$/, "a plain lowercase name: " + JSON.stringify(name));
    assert.match(keywords, /^[a-z0-9]+(?: [a-z0-9]+)*$/, "plain lowercase keywords for " + name + ": " + JSON.stringify(keywords));
  }
  for (const c of EMOJI_CATEGORIES) {
    const names = c.items.map((it) => it[1]);
    assert.equal(new Set(names).size, names.length, "unique names within " + c.id);
  }
});

test("names are spelled the American way (the cell's tooltip shows the name; a British form may stay a keyword)", () => {
  // the two CLDR names that differed (review r1), plus the forms most likely to arrive with a new entry
  const british = /\b(chequered|doughnut|colour|coloured|grey|centre|theatre|favourite|armour|jewellery|aeroplane|tyre|pyjamas|moustache|whisky|programme|catalogue|dialogue|defence|licence|practise|travelling|cancelled|ageing|mould|plough|sceptical|aluminium|cosy|mum|storey|kerb)\b/;
  for (const { name } of ALL) assert.doesNotMatch(name, british, name);
  assert.ok(ALL.some((e) => e.name === "checkered flag"), "the flag's name");
  assert.ok(ALL.some((e) => e.name === "donut"), "the donut's name");
  assert.ok(ALL.some((e) => e.name === "checkered flag" && /\bchequered\b/.test(e.keywords)), "the British spelling still finds it");
});

test("the module is data only, ASCII only, and says skin tones are out of scope", () => {
  const src = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "emoji-data.ts"), "utf8");
  assert.doesNotMatch(src, /^import /m, "no imports: cheap to load");
  assert.doesNotMatch(src, /\bfunction\b|=>/, "no code, data only");
  assert.doesNotMatch(src, /[^\x00-\x7F]/, "escapes, not literal characters, so the file diffs as text");
  assert.match(src, /[Ss]kin-tone variants are out of scope/);
  // the kernel's validator stays the authority; the list is a convenience in front of it
  assert.match(src, /_emoji_check/);
});
