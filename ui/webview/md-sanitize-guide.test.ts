// The guide's account of what a note's own HTML may do must match the sanitizer (plans/markdown-viewer.md,
// Slice 1: sanitize as GitHub does). md-sanitize.test.ts pins that the paragraph exists and names the rules;
// this pins the one claim it can get wrong in a way no browser test catches: a <style> block's contents go
// with the element (DOMPurify's default FORBID_CONTENTS), while a form's, a control's and a <dialog>'s text
// stays as prose (KEEP_CONTENT). The paragraph once said "their text stays as prose" of all three (review,
// 2026-09-07), promising text the Rendered view never shows.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const GUIDE = path.resolve(process.cwd(), "..", "docs", "guide.md");

/** The "A file's own HTML" paragraph of the guide's Files section, split into its sentences and clauses. */
function htmlParagraphClauses(): string[] {
  const guide = fs.readFileSync(GUIDE, "utf8");
  const files = guide.split("\n### Files\n")[1].split("\n## ")[0];
  const from = files.indexOf("**A file's own HTML.**");
  assert.ok(from >= 0, "the Files section has the paragraph");
  const rest = files.slice(from);
  const end = rest.indexOf("\n\n");
  const para = (end < 0 ? rest : rest.slice(0, end)).replace(/\n/g, " ");
  return para.split(/[;.]\s+/);
}

test("the guide does not say a <style> block's text stays as prose; it says that of a form and a <dialog>", () => {
  const clauses = htmlParagraphClauses();
  const style = clauses.filter((c) => c.includes("`<style>`"));
  assert.equal(style.length, 1, "one clause names the <style> block");
  assert.doesNotMatch(style[0], /stays as prose|text stays/, "a <style> block's contents go with it (DOMPurify's default FORBID_CONTENTS)");
  assert.doesNotMatch(style[0], /`<dialog>`|\bform\b/, "the <style> block is not grouped with the elements whose text survives");
  const prose = clauses.filter((c) => /stays as prose/.test(c));
  assert.equal(prose.length, 1, "one clause says whose text stays as prose");
  assert.match(prose[0], /\bform\b/, "a form's text stays (KEEP_CONTENT)");
  assert.match(prose[0], /`<dialog>`/, "a <dialog>'s text stays (KEEP_CONTENT)");
});
