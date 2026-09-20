#!/usr/bin/env python3
"""The anchor slugger's oracle: marked, the extension's renderer, over the derived heading corpus and the emphasis battery.

A documented command, not a test (round 12 of fork PR #778, tests-2, extra8-1, extra8-2). tests/test_docs_anchors.py slugs
every heading of the documentation as GitHub does, and the only thing that can say whether its reading of CommonMark's
emphasis rules is right is a renderer. This recipe runs one: for every heading corpus_headings() derives (every ATX heading
of the anchor pin's population and of plans/) and every shape battery() generates, node renders `## <heading>` with the marked
in vscode-extension/node_modules (12.0.2 at this writing; the version is read from its package.json and recorded), and the
h element's inner HTML, its tags removed and its entities decoded, is the text content GitHub's anchor filter slugs. The
slug is github-slugger's: lowercased, everything but letters, numbers, marks, spaces, hyphens and underscores removed,
spaces to hyphens. GitHub itself renders with cmark-gfm rather than marked, replaces an emoji shortcode before it slugs,
numbers a repeated slug and prefixes the id with user-content-; the module docstring says how each bears on the check.

The result is written to tests/fixtures/docs_anchor_slugs.json, one row per heading text, sorted, and
tests/test_docs_anchors.py holds the slugger to it in the suite, where no node runs (CI's Python job installs no
node_modules). Run it when a heading is added or changed in the corpus, when battery() changes, or when the extension
moves marked: `python3 tests/docs-anchors-oracle.py` rewrites the table; `--check` rewrites nothing and exits 1 naming
the rows that would change. Without node, or without marked under vscode-extension/node_modules (`npm ci` there
installs it), it exits 2 saying so; it never skips."""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import test_docs_anchors as anchors  # noqa: E402

MARKED = os.path.join(ROOT, "vscode-extension", "node_modules", "marked")

ORACLE_JS = r"""
const { marked } = require(process.env.ROMP_MARKED);
const fs = require('fs');
const headings = JSON.parse(fs.readFileSync(0, 'utf8'));
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };
function decode(s) {
  return s.replace(/&(#x([0-9a-f]+)|#([0-9]+)|([a-z]+));/gi, (m, _a, hex, dec, name) => {
    if (hex) return String.fromCodePoint(parseInt(hex, 16));
    if (dec) return String.fromCodePoint(parseInt(dec, 10));
    if (name in ENT) return ENT[name];
    return m;
  });
}
// github-slugger: lowercase, drop everything but letters, numbers, marks, spaces, hyphens and underscores, spaces to hyphens
function slug(text) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}\p{M} _-]/gu, '').replace(/ /g, '-');
}
const out = [];
for (const h of headings) {
  const html = marked.parse('## ' + h, { gfm: true, async: false });
  const m = /^<h2(?:[^>]*)>([\s\S]*)<\/h2>\s*$/.exec(html);
  if (!m) { out.push([h, null, html]); continue; }
  out.push([h, slug(decode(m[1].replace(/<[^>]*>/g, '')))]);
}
process.stdout.write(JSON.stringify(out));
"""


def marked_version():
    with open(os.path.join(MARKED, "package.json"), encoding="utf-8") as f:
        return json.load(f)["version"]


def render(headings, node):
    r = subprocess.run([node, "-e", ORACLE_JS], input=json.dumps(headings), capture_output=True, text=True,
                       env=dict(os.environ, ROMP_MARKED=MARKED), timeout=120)
    if r.returncode != 0:
        sys.exit("node failed:\n" + r.stderr)
    rows = json.loads(r.stdout)
    bad = [(h, html) for h, s, *html in rows if s is None]
    if bad:
        sys.exit("marked rendered no heading for:\n" + "\n".join("  %r -> %r" % b for b in bad))
    return [[h, s] for h, s, *_ in rows]


def derive(node):
    corpus = anchors.corpus_headings()
    shapes = anchors.battery()
    texts = sorted(set(corpus) | set(shapes))
    rows = render(texts, node)
    return {"_": "The slug GitHub gives each heading, by execution: marked (the extension's; the version below) renders the heading and "
                 "github-slugger's rule slugs the h element's text (tests/docs-anchors-oracle.py says exactly how). Rows: every ATX "
                 "heading of every tracked markdown file the anchor pin guards and of plans/ (corpus_headings), and every shape "
                 "battery() generates, in tests/test_docs_anchors.py, which holds its slugger to this table. Regenerate with the "
                 "command below; the table is derived, never edited by hand. Synthetic shapes beside the repository's own headings.",
            "marked": marked_version(), "regenerate": anchors.REGENERATE,
            "corpus": {"files": len(anchors.corpus_files()), "headings": sum(len(v) for v in corpus.values()), "distinct": len(corpus),
                       "battery": len(shapes)},
            "rows": rows}


def dumps(table):
    """The table's text: the header fields, then one row a line, so a heading's change is one line of diff. Non-ASCII is
    written as JSON escapes (the file holds the repository's own headings, and the hygiene scans over added lines read the
    characters, not the JSON), the same value once parsed."""
    parts = ["{"]
    for k in ("_", "marked", "regenerate", "corpus"):
        parts.append(" %s: %s," % (json.dumps(k), json.dumps(table[k])))
    parts.append(' "rows": [')
    parts.append(",\n".join("  " + json.dumps(r) for r in table["rows"]))
    parts.append(" ]\n}\n")
    return "\n".join(parts)


def main(argv):
    check = "--check" in argv
    node = shutil.which("node")
    if not node:
        print("no node on PATH: the oracle is marked under node; install node (CI's extension job has it)", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(os.path.join(MARKED, "package.json")):
        print("no marked under %s: run `npm ci` in vscode-extension/ (the extension's lockfile pins it)" % os.path.relpath(MARKED, ROOT),
              file=sys.stderr)
        sys.exit(2)
    table = derive(node)
    text = dumps(table)
    assert json.loads(text) == table
    if check:
        try:
            with open(anchors.TABLE, encoding="utf-8") as f:
                have = json.load(f)
        except (OSError, ValueError) as e:
            sys.exit("%s is unreadable (%s): run without --check to write it" % (os.path.relpath(anchors.TABLE, ROOT), e))
        old, new = dict(have.get("rows", [])), dict(table["rows"])
        changed = sorted(set(old) ^ set(new) | {h for h in old if h in new and old[h] != new[h]})
        meta = [k for k in ("marked", "regenerate", "corpus") if have.get(k) != table[k]]
        if changed or meta:
            for h in changed:
                print("  %r: table %r, oracle %r" % (h, old.get(h), new.get(h)))
            for k in meta:
                print("  %s: table %r, oracle %r" % (k, have.get(k), table[k]))
            sys.exit("%d rows and %d fields differ from %s: run %s" % (len(changed), len(meta), os.path.relpath(anchors.TABLE, ROOT), anchors.REGENERATE))
        print("%s agrees with the oracle: %d rows, marked %s" % (os.path.relpath(anchors.TABLE, ROOT), len(new), table["marked"]))
        return 0
    with open(anchors.TABLE, "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s: %d rows (%d distinct headings of %d in %d files, %d battery shapes), marked %s"
          % (os.path.relpath(anchors.TABLE, ROOT), len(table["rows"]), table["corpus"]["distinct"], table["corpus"]["headings"],
             table["corpus"]["files"], table["corpus"]["battery"], table["marked"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
