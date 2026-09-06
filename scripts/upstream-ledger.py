#!/usr/bin/env python3
"""The fork's upstream ledger: one file per candidate under `upstream/`, rendered on demand.

UPSTREAM.md used to hold one Markdown table and every branch that landed something upstream-worthy
appended a row, so any two such PRs conflicted on the ledger, and the merges that resolved the
conflicts duplicated rows (2026-09-06). Now each candidate is its own file,
`upstream/<YYYY-MM-DD>-<slug>.md`, UPSTREAM.md holds prose only, and this script renders the table
when someone wants to read it. Nothing shared is edited per change, so unrelated PRs cannot conflict
on the ledger; two writers touching the SAME entry conflict on that one file, which is a real
disagreement and should.

Entry format: a strict subset of YAML that this file parses without PyYAML (not in the test venv).
`key: value`, one pair per line, between `---` lines, no nesting, no multi-line values; the body is
Markdown and its first paragraph is the rendered Notes cell.

    ---
    title: Kernel performance counters and `romp perf`
    status: candidate
    where: fork PR #199 (`romp-perf`): `kernel/kernel.py` (`_PerfStats`), `bin/romp` (`perf`)
    added: 2026-09-06
    pr: 199
    tier: feature
    offered:
    closed:
    ---
    Why upstream wants it, in one paragraph.

    Anything longer goes here. The upstream session appends a dated line whenever it acts on the entry.

Commands (stdlib only):
    new <slug> --title T --where W [--pr N] [--tier t] [--status s] [--notes text]
    check                        every rule the guard test runs; exit 1 with the problems
    render [--active] [--link-base URL]
    list [--status a,b]          one JSON object per line
    set <slug> <key> <value>     rewrites one header line, leaves the body alone
    import <UPSTREAM.md> <dir>   the migration: one file per table row, re-runnable
    import --row '<row>'         the straggler fix for a branch that still appended a row
"""
import argparse
import json
import re
import signal
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REQUIRED = ("title", "status", "where", "added")
OPTIONAL = ("pr", "tier", "offered", "closed", "supersedes")
KEYS = REQUIRED + OPTIONAL
TIERS = ("fix", "tests-only", "feature", "major-feature")

# The status vocabulary. `approved` is the maintainer's word: offer it. The four terminal statuses
# collapse in the rendering; divergence and keep-private get a short table of their own.
OPEN = ("approved", "candidate", "waiting", "follow-up", "offered")
SIDE = ("divergence", "keep-private")
TERMINAL = ("merged", "landed", "resolved-upstream", "declined")
STATUSES = OPEN + SIDE + TERMINAL

DIR = "upstream"
FRONT = "UPSTREAM.md"
TITLE_PREFIX = 60     # two versions of one entry agree on how the title starts
NOTES_CUT = 200       # the rendered title, Where and Notes cells; the link carries the reader to the full text
FILENAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9-]{3,60})\.md$")
SLUG = re.compile(r"^[a-z0-9-]{3,60}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADER_LINE = re.compile(r"^([a-z]+):(?: (.*))?$")
CONFLICT = re.compile(r"^(?:<{7}|>{7})(?: |$)|^={7}$")
STATUS_DETAIL = "Status detail (migrated from the table): "
ROW_HINT = "a table row; entries live in upstream/ now: run scripts/upstream-ledger.py import --row"
TABLE_HEADER = "| What | Where it lives here | Status | Notes |"
TABLE_SEPARATOR = "|---|---|---|---|"


# ---------------------------------------------------------------- parsing and checking

class Entry:
    """One ledger file: its header pairs (in file order), its body, and where it came from."""

    def __init__(self, name, header, body, path=None):
        self.name = name          # the filename, e.g. 2026-09-06-romp-perf.md
        self.header = header      # dict, insertion-ordered
        self.body = body          # text after the closing ---, verbatim
        self.path = path

    def get(self, key, default=""):
        return self.header.get(key, default) or default

    @property
    def slug(self):
        m = FILENAME.match(self.name)
        return m.group(2) if m else self.name

    @property
    def notes(self):
        """The body's first paragraph, joined onto one line."""
        return first_paragraph(self.body)

    @property
    def status_detail(self):
        for line in self.body.split("\n"):
            if line.startswith(STATUS_DETAIL):
                return line[len(STATUS_DETAIL):]
        return ""


def first_paragraph(body):
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    out = []
    while i < len(lines) and lines[i].strip():
        out.append(lines[i].strip())
        i += 1
    para = " ".join(out)
    return "" if para.startswith(STATUS_DETAIL) else para


def split_entry(text):
    """(header_lines, body, problems) for an entry's text. Never raises; problems are strings."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None, None, ["line 1: expected the opening `---`"]
    end = next((i for i, l in enumerate(lines[1:], 1) if l.rstrip() == "---"), None)
    if end is None:
        return None, None, ["no closing `---` after the header"]
    return lines[1:end], "\n".join(lines[end + 1:]), []


def parse_entry(name, text, path=None):
    """(Entry or None, problems). Problems name the file and the key or line."""
    problems = []
    for n, line in enumerate(text.split("\n"), 1):
        if CONFLICT.match(line):
            problems.append(f"{name}:{n}: git conflict marker: {line[:40]!r}")
    m = FILENAME.match(name)
    if not m:
        problems.append(f"{name}: filename must match YYYY-MM-DD-<slug>.md with a slug of 3 to 60 [a-z0-9-]")
    header_lines, body, split_problems = split_entry(text)
    if split_problems:
        return None, problems + [f"{name}: {p}" for p in split_problems]
    header = {}
    for i, line in enumerate(header_lines, 2):
        hm = HEADER_LINE.match(line)
        if not hm:
            problems.append(f"{name}:{i}: header line is not `key: value`: {line[:60]!r}")
            continue
        key, value = hm.group(1), (hm.group(2) or "").strip()
        if key not in KEYS:
            problems.append(f"{name}: unknown key `{key}` (known: {', '.join(KEYS)})")
            continue
        if key in header:
            problems.append(f"{name}: key `{key}` appears twice")
            continue
        header[key] = value
    for key in REQUIRED:
        if key not in header:
            problems.append(f"{name}: missing required key `{key}`")
        elif not header[key]:
            problems.append(f"{name}: required key `{key}` is blank")
    if header.get("status") and header["status"] not in STATUSES:
        problems.append(f"{name}: status {header['status']!r} is not one of {', '.join(STATUSES)}")
    for key in ("added", "closed"):
        if header.get(key) and not ISO_DATE.match(header[key]):
            problems.append(f"{name}: {key} must be an ISO date (YYYY-MM-DD), got {header[key]!r}")
    if header.get("pr") and not header["pr"].isdigit():
        problems.append(f"{name}: pr must be blank or an integer, got {header['pr']!r}")
    if header.get("tier") and header["tier"] not in TIERS:
        problems.append(f"{name}: tier {header['tier']!r} is not one of {', '.join(TIERS)}")
    if m and header.get("added") and ISO_DATE.match(header["added"]) and header["added"] != m.group(1):
        problems.append(f"{name}: added {header['added']} does not match the filename date {m.group(1)}")
    if problems:
        return None, problems
    return Entry(name, header, body, path), []


def load_entries(dir_path):
    """(entries, problems) for every file under `dir_path`, sorted by filename."""
    dir_path = Path(dir_path)
    entries, problems = [], []
    if not dir_path.is_dir():
        return entries, [f"{dir_path}: not a directory"]
    for p in sorted(dir_path.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_dir() or not p.name.endswith(".md"):
            problems.append(f"{p.name}: only YYYY-MM-DD-<slug>.md entry files belong under {dir_path.name}/")
            continue
        e, ps = parse_entry(p.name, p.read_text(encoding="utf-8"), p)
        problems.extend(ps)
        if e:
            entries.append(e)
    return entries, problems


def duplicate_problems(entries):
    """No two entries share the first 60 characters of `title`: one candidate written twice, or
    imported twice, or one entry in two versions after a merge."""
    seen = {}
    out = []
    for e in entries:
        head = e.get("title")[:TITLE_PREFIX]
        if head in seen:
            out.append(f"{e.name}: title shares its first {TITLE_PREFIX} characters with {seen[head]} (one entry in two versions?)")
        else:
            seen[head] = e.name
    return out


def is_row(line):
    s = line.rstrip()
    return s.startswith("|") and s.endswith("|") and len(s) >= 2


def documented_statuses(text):
    """The bold tokens of UPSTREAM.md's status paragraph (the one that starts `Status meanings:`)."""
    paras = re.split(r"\n\s*\n", text)
    for para in paras:
        if para.lstrip().startswith("Status meanings:"):
            return re.findall(r"\*\*([a-z][a-z-]*)\*\*", para)
    return []


def front_problems(text, name=FRONT):
    """UPSTREAM.md holds prose only: no table row, no conflict marker, the offering tail, and the
    status vocabulary exactly as the parser accepts it."""
    out = []
    lines = text.split("\n")
    for n, line in enumerate(lines, 1):
        if CONFLICT.match(line):
            out.append(f"{name}:{n}: git conflict marker: {line[:40]!r}")
        elif is_row(line):
            out.append(f"{name}:{n}: {ROW_HINT} {json.dumps(line.strip()[:60] + ('…' if len(line.strip()) > 60 else ''))}")
    if "When offering:" not in text:
        out.append(f"{name}: the `When offering:` paragraph is gone; the offering guidance lives here")
    documented = documented_statuses(text)
    if not documented:
        out.append(f"{name}: no `Status meanings:` paragraph with bold status words")
    else:
        missing = [s for s in STATUSES if s not in documented]
        extra = [s for s in documented if s not in STATUSES]
        if missing:
            out.append(f"{name}: statuses the parser accepts but the prose does not document: {', '.join(missing)}")
        if extra:
            out.append(f"{name}: statuses the prose documents but the parser refuses: {', '.join(extra)}")
    return out


def check(root):
    """Every problem in `root`'s ledger: the entries, their titles, and UPSTREAM.md."""
    root = Path(root)
    entries, problems = load_entries(root / DIR)
    problems += duplicate_problems(entries)
    front = root / FRONT
    if front.exists():
        problems += front_problems(front.read_text(encoding="utf-8"))
    else:
        problems.append(f"{FRONT}: missing")
    return entries, problems


# ---------------------------------------------------------------- rendering

def escape_cell(text):
    """One table cell: pipes escaped (GitHub splits on a pipe even inside a code span), no newlines."""
    text = text.replace("\n", " ")
    return re.sub(r"(?<!\\)\|", r"\\|", text)


def cut(text, limit=NOTES_CUT):
    """The first `limit` characters, ending on a word boundary and never inside a code span (an
    unbalanced backtick would let the next cell's backtick pair with it and swallow a separator)."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    sp = head.rfind(" ")
    if sp > limit // 2:
        head = head[:sp]
    if head.count("`") % 2:
        head = head[:head.rfind("`")]
    return head.rstrip() + "…"


def _sort_key(e):
    return (e.get("added"), e.name)


def status_cell(e):
    status = e.get("status")
    bits = [status]
    if status == "offered":
        if e.get("offered"):
            bits = [f"offered — {e.get('offered')}"]
    elif status in TERMINAL:
        ref = e.get("offered")
        when = e.get("closed")
        if ref and when:
            bits = [f"{status} — {ref} ({when})"]
        elif ref:
            bits = [f"{status} — {ref}"]
        elif when:
            bits = [f"{status} ({when})"]
    if e.get("tier") and status in OPEN:
        bits.append(e.get("tier"))
    return ", ".join(bits)


def title_cell(e, link_base=""):
    title = cut(e.get("title"))
    target = f"{link_base}{DIR}/{e.name}"
    if "[" in title or "]" in title:   # brackets inside link text break the link; link beside the title instead
        return f"{escape_cell(title)} ([entry]({target}))"
    return f"[{escape_cell(title)}]({target})"


def table(entries, link_base=""):
    rows = [TABLE_HEADER, TABLE_SEPARATOR]
    for e in entries:
        rows.append("| " + " | ".join([
            title_cell(e, link_base),
            escape_cell(cut(e.get("where"))),
            escape_cell(status_cell(e)),
            escape_cell(cut(e.notes)),
        ]) + " |")
    return "\n".join(rows)


def render_sections(entries, link_base=""):
    """[(heading, entries in rendered order)] for the three tables."""
    by = {s: sorted((e for e in entries if e.get("status") == s), key=_sort_key, reverse=True) for s in STATUSES}
    open_rows = [e for s in OPEN for e in by[s]]
    side_rows = [e for s in SIDE for e in by[s]]
    closed_rows = [e for s in TERMINAL for e in by[s]]
    return [
        (f"Open ({len(open_rows)}): " + ", ".join(OPEN), open_rows),
        (f"Divergence and keep-private ({len(side_rows)})", side_rows),
        (f"Closed ({len(closed_rows)}): " + ", ".join(TERMINAL), closed_rows),
    ]


def render(entries, active=False, link_base=""):
    sections = render_sections(entries, link_base)
    out = ["# Upstream ledger", ""]
    out.append(f"{len(entries)} entries, rendered from `{DIR}/*.md` by `scripts/upstream-ledger.py render`. "
               "Edit an entry file (or run `set`), never this table: it is generated on every push to main.")
    out.append("")
    for i, (heading, rows) in enumerate(sections):
        if active and i > 0:
            break
        body = table(rows, link_base) if rows else "(none)"
        if i == 2:
            out += [f"<details><summary>{heading}</summary>", "", body, "", "</details>", ""]
        else:
            out += [f"## {heading}", "", body, ""]
    return "\n".join(out)


# ---------------------------------------------------------------- writing

def format_entry(header, body):
    lines = ["---"]
    for key in KEYS:
        if key in header and (header[key] or key != "supersedes"):
            lines.append(f"{key}: {header[key]}".rstrip())
    lines.append("---")
    text = "\n".join(lines) + "\n"
    if body:
        text += body.rstrip("\n") + "\n"
    return text


def today():
    return date.today().isoformat()


def new_entry(dir_path, slug, title, where, status="candidate", pr="", tier="", notes="", added=None):
    if not SLUG.match(slug):
        raise SystemExit(f"slug {slug!r} must be 3 to 60 characters of [a-z0-9-]")
    added = added or today()
    path = Path(dir_path) / f"{added}-{slug}.md"
    if path.exists():
        raise SystemExit(f"{path} exists; pick another slug or edit that file")
    header = {"title": title.strip(), "status": status, "where": where.strip(), "added": added,
              "pr": str(pr) if pr else "", "tier": tier or "", "offered": "", "closed": ""}
    _, problems = parse_entry(path.name, format_entry(header, notes))
    if problems:
        raise SystemExit("\n".join(problems))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_entry(header, notes), encoding="utf-8")
    return path


def resolve(dir_path, ref):
    """An entry by slug, filename, or path. Refuses an ambiguous slug by naming the candidates."""
    dir_path = Path(dir_path)
    p = Path(ref)
    if p.is_file():
        return p
    if (dir_path / ref).is_file():
        return dir_path / ref
    hits = [q for q in sorted(dir_path.glob("*.md")) if FILENAME.match(q.name) and FILENAME.match(q.name).group(2) == ref]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f"no entry {ref!r} under {dir_path}/")
    raise SystemExit(f"{ref!r} names {len(hits)} entries; use the filename: " + ", ".join(h.name for h in hits))


def set_key(path, key, value):
    """Rewrite one header line (adding the key if the header lacks it); the body stays byte-identical."""
    path = Path(path)
    if key not in KEYS:
        raise SystemExit(f"unknown key `{key}` (known: {', '.join(KEYS)})")
    if key == "added":
        raise SystemExit("`added` is the filename's date; rename the file instead")
    text = path.read_text(encoding="utf-8")
    header_lines, body, problems = split_entry(text)
    if problems:
        raise SystemExit(f"{path.name}: " + "; ".join(problems))
    value = value.strip()
    new_line = f"{key}: {value}".rstrip()
    out, done = [], False
    for line in header_lines:
        hm = HEADER_LINE.match(line)
        if hm and hm.group(1) == key and not done:
            out.append(new_line)
            done = True
        else:
            out.append(line)
    if not done:
        out.append(new_line)
    new_text = "---\n" + "\n".join(out) + "\n---\n" + body
    _, problems = parse_entry(path.name, new_text)
    if problems:
        raise SystemExit("\n".join(problems))
    path.write_text(new_text, encoding="utf-8")
    return path


# ---------------------------------------------------------------- the table import

_ESCAPED_PIPE = re.compile(r"\\\|")
_CODE_SPAN = re.compile(r"`[^`]*`")


def row_cells(row):
    """The four cells of an old-table row, verbatim, with escaped and code-span pipes ignored as
    separators (the old checker's rule; three rows carry `\\|`, one of them outside a code span)."""
    s = row.strip()
    masked = _ESCAPED_PIPE.sub("__", s)
    masked = _CODE_SPAN.sub(lambda m: "`" + "_" * (len(m.group()) - 2) + "`", masked)
    idx = [i for i, c in enumerate(masked) if c == "|"]
    return [s[a + 1:b].strip() for a, b in zip(idx, idx[1:])]


def table_rows(text):
    """[(line_number, row_text)] of the old UPSTREAM.md table: every row under the separator."""
    lines = text.split("\n")
    try:
        head = next(i for i, l in enumerate(lines) if l.rstrip() == TABLE_HEADER)
    except StopIteration:
        return []
    rows = []
    n = head + 2
    while n < len(lines) and is_row(lines[n]):
        rows.append((n + 1, lines[n]))
        n += 1
    return rows


# Keyword forms of the vocabulary as they appear in the old Status cells. The plan's derivation
# order (merged, landed, resolved upstream, declined, keep-private, divergence, offered, waiting,
# follow-up, candidate; first match wins) is kept as PLAN_ORDER and printed beside the result when
# it disagrees; the derivation itself takes the keyword that appears EARLIEST in the cell, because a
# cell like `waiting: gated on X being offered first` leads with its status and the plan's order
# would have read it as offered.
KEYWORDS = [
    ("merged", re.compile(r"\bmerged\b", re.I)),
    ("landed", re.compile(r"\blanded\b", re.I)),
    ("resolved-upstream", re.compile(r"\bresolved[ -]upstream\b", re.I)),
    ("declined", re.compile(r"\bdeclined\b", re.I)),
    ("keep-private", re.compile(r"\bkeep[ -]private\b", re.I)),
    ("divergence", re.compile(r"\bdivergence\b", re.I)),
    ("offered", re.compile(r"\boffered\b", re.I)),
    ("waiting", re.compile(r"\bwaiting\b", re.I)),
    ("follow-up", re.compile(r"\bfollow[ -]up\b", re.I)),
    ("candidate", re.compile(r"\bcandidate\b", re.I)),
]
UPSTREAM_REF = re.compile(r"\b(?:their (?:PR )?#(\d+)|upstream PR #(\d+)|romp-on/romp#(\d+))")
FORK_PR = re.compile(r"\bfork PR #(\d+)")
TIER_WORD = re.compile(r"label `?(fix|tests-only|feature|major-feature)`?|\b(major-feature|tests-only)\b")
ANY_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def derive_status(cell):
    """(status by earliest keyword, status by the plan's order); either may be None."""
    hits = [(m.start(), status) for status, rx in KEYWORDS for m in [rx.search(cell)] if m]
    earliest = min(hits)[1] if hits else None
    plan_order = hits[0][1] if hits else None   # KEYWORDS is in the plan's order
    return earliest, plan_order


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(s) > 60:
        s = s[:60]
        if "-" in s:
            s = s[:s.rfind("-")]
    s = s.strip("-")
    return s if len(s) >= 3 else "entry"


def derive(what, where, status_cell, notes):
    """The header an old row becomes, plus the derivation facts for the report."""
    status, plan_status = derive_status(status_cell)
    ref = UPSTREAM_REF.search(status_cell)
    offered = f"their PR #{next(g for g in ref.groups() if g)}" if ref else ""
    closed = ""
    if status in TERMINAL:
        d = ANY_DATE.search(status_cell)
        closed = d.group(1) if d else ""
    tier_m = TIER_WORD.search(status_cell)
    tier = (tier_m.group(1) or tier_m.group(2)) if tier_m else ""
    pr_m = FORK_PR.search(where)
    pr = pr_m.group(1) if pr_m else ""
    header = {"title": what, "status": status or "", "where": where, "added": "",
              "pr": pr, "tier": tier, "offered": offered, "closed": closed}
    body = (notes + "\n\n" if notes else "") + STATUS_DETAIL + status_cell + "\n"
    return header, body, plan_status


def added_date(root, row, fallback=None):
    """The author date of the first commit whose diff introduced the row's first 60 characters."""
    prefix = row.strip()[:60]
    try:
        out = subprocess.run(["git", "-C", str(root), "log", "--format=%as", "--reverse", "-S" + prefix, "--", FRONT],
                             capture_output=True, text=True, check=False).stdout.split()
    except OSError:
        out = []
    return (out[0], "git") if out else (fallback or today(), "today (no commit introduced this row)")


def import_rows(rows, dir_path, root, report):
    """Write one entry per row into dir_path. Re-runnable: a row whose title prefix already has an
    entry rewrites that file in place, keeping its filename (so a rename sticks) and, when the cell
    derives no status, its status (so a hand-set one sticks)."""
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    existing, _ = load_entries(dir_path)
    by_prefix = {e.get("title")[:TITLE_PREFIX]: e for e in existing}
    taken = {p.name for p in dir_path.glob("*.md")}
    unmatched, disagree, written = [], [], []
    for i, (line_no, row) in enumerate(rows, 1):
        cells = row_cells(row)
        if len(cells) != 4:
            report.append(f"{i:04d}: line {line_no}: {len(cells)} cells, expected 4; skipped: {row[:60]!r}")
            continue
        what, where, status_cell, notes = cells
        header, body, plan_status = derive(what, where, status_cell, notes)
        prev = by_prefix.get(what[:TITLE_PREFIX])
        kept = ""
        if prev is not None:
            header["added"] = prev.get("added")
            path = prev.path
            if not header["status"] and prev.get("status"):
                header["status"] = kept = prev.get("status")
        else:
            header["added"], _how = added_date(root, row)
            slug = slugify(what)
            name = f"{header['added']}-{slug}.md"
            k = 2
            while name in taken:
                name = f"{header['added']}-{slug[:57]}-{k}.md"
                k += 1
            taken.add(name)
            path = dir_path / name
        path.write_text(format_entry(header, body), encoding="utf-8")
        written.append(path)
        shown = status_cell[:60].replace('"', "'")
        tail = []
        if not header["status"]:
            tail.append("SET BY HAND")
            unmatched.append(i)
        elif kept:
            tail.append(f"no keyword; kept the file's hand-set {kept}")
            unmatched.append(i)
        if plan_status and header["status"] and plan_status != header["status"]:
            tail.append(f"plan order: {plan_status}")
            disagree.append(i)
        facts = " ".join(f"{k}={header[k]}" for k in ("offered", "closed", "tier", "pr") if header[k])
        report.append(f'{i:04d}: "{shown}" -> {header["status"] or "(none)"}'
                      + (f" [{facts}]" if facts else "") + (f" ({'; '.join(tail)})" if tail else "")
                      + f" {DIR}/{path.name}")
    return written, unmatched, disagree


def round_trip(rows, dir_path):
    """The multiset of (title, where, status detail, notes) from the files must equal the table's."""
    want = Counter()
    for _, row in rows:
        c = row_cells(row)
        if len(c) == 4:
            want[(c[0], c[1], c[2], c[3])] += 1
    entries, problems = load_entries(dir_path)
    got = Counter((e.get("title"), e.get("where"), e.status_detail, e.notes) for e in entries if e.status_detail)
    missing = want - got
    extra = got - want
    lines = [f"round-trip: {sum(want.values())} rows, {sum(got.values())} migrated files, "
             + ("diff empty" if not missing and not extra else f"{sum(missing.values())} missing, {sum(extra.values())} extra")]
    for k, n in missing.items():
        lines.append(f"  only in the table ×{n}: {k[0][:60]!r}")
    for k, n in extra.items():
        lines.append(f"  only in the files ×{n}: {k[0][:60]!r}")
    for p in problems:
        lines.append(f"  entry problem: {p}")
    return lines, not missing and not extra


def import_file(front_path, dir_path, root):
    front_path = Path(front_path)
    text = front_path.read_text(encoding="utf-8")
    rows = table_rows(text)
    report = [f"import: {len(rows)} rows from {front_path} into {dir_path}/", ""]
    written, unmatched, disagree = import_rows(rows, dir_path, root, report)
    report.append("")
    report.append(f"{len(written)} files written; {len(unmatched)} rows matched no status keyword"
                  + (": " + ", ".join(f"{i:04d}" for i in unmatched) + " (set by hand: blank on a first run, kept on a re-run)" if unmatched else ""))
    if disagree:
        report.append(f"{len(disagree)} rows where the plan's keyword order would differ: " + ", ".join(f"{i:04d}" for i in disagree))
    report.append("")
    lines, ok = round_trip(rows, dir_path)
    report += lines
    blank = [e for e in load_entries(dir_path)[1] if "`status` is blank" in e]
    return report, ok and not blank


def import_row(row, dir_path, root):
    rows = [(0, row)]
    report = []
    written, unmatched, _ = import_rows(rows, dir_path, root, report)
    if not written:
        raise SystemExit("\n".join(report))
    lines, ok = round_trip(rows, dir_path)
    front = Path(root) / FRONT
    if front.exists() and row.strip() in front.read_text(encoding="utf-8"):
        report.append(f"now delete the row from {FRONT}")
    return report + lines, written[0]


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="upstream-ledger.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=None, help="repository root (default: this script's grandparent directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="write upstream/<today>-<slug>.md")
    p.add_argument("slug")
    p.add_argument("--title", required=True)
    p.add_argument("--where", required=True)
    p.add_argument("--pr", default="")
    p.add_argument("--tier", default="", choices=("",) + TIERS)
    p.add_argument("--status", default="candidate", choices=STATUSES)
    p.add_argument("--notes", default="", help="the body's first paragraph (the rendered Notes cell)")

    sub.add_parser("check", help="every rule the guard test runs")

    p = sub.add_parser("render", help="the ledger as Markdown tables")
    p.add_argument("--active", action="store_true", help="the open table only")
    p.add_argument("--link-base", default="", help="prefix for entry links, e.g. https://github.com/o/r/blob/main/")

    p = sub.add_parser("list", help="one JSON object per entry")
    p.add_argument("--status", default="", help="comma-separated statuses to keep")

    p = sub.add_parser("set", help="rewrite one header line")
    p.add_argument("slug")
    p.add_argument("key")
    p.add_argument("value")

    p = sub.add_parser("import", help="the table migration, or one straggler row")
    p.add_argument("source", nargs="?", help="the UPSTREAM.md holding the old table")
    p.add_argument("dir", nargs="?", help="the entry directory")
    p.add_argument("--row", default=None, help="one table row's text")

    a = ap.parse_args(argv)
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # `render | head` ends quietly
    root = Path(a.root) if a.root else Path(__file__).resolve().parents[1]
    entries_dir = root / DIR

    if a.cmd == "new":
        print(new_entry(entries_dir, a.slug, a.title, a.where, a.status, a.pr, a.tier, a.notes))
    elif a.cmd == "check":
        entries, problems = check(root)
        if problems:
            print("\n".join(problems))
            return 1
        print(f"ok: {len(entries)} entries under {DIR}/, {FRONT} holds no table")
    elif a.cmd == "render":
        entries, problems = check(root)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(render(entries, active=a.active, link_base=a.link_base))
    elif a.cmd == "list":
        entries, problems = load_entries(entries_dir)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        keep = {s for s in a.status.split(",") if s}
        for e in entries:
            if keep and e.get("status") not in keep:
                continue
            print(json.dumps({"file": f"{DIR}/{e.name}", "title": e.get("title"), "status": e.get("status"),
                              "where": e.get("where"), "pr": int(e.get("pr")) if e.get("pr") else None,
                              "tier": e.get("tier") or None, "offered": e.get("offered") or None,
                              "added": e.get("added"), "closed": e.get("closed") or None}, ensure_ascii=False))
    elif a.cmd == "set":
        print(set_key(resolve(entries_dir, a.slug), a.key, a.value))
    elif a.cmd == "import":
        if a.row is not None:
            report, path = import_row(a.row, Path(a.dir) if a.dir else entries_dir, root)
            print("\n".join(report))
            print(path)
        else:
            if not a.source or not a.dir:
                ap.error("import needs <UPSTREAM.md> <dir>, or --row '<row text>'")
            report, ok = import_file(a.source, a.dir, root)
            print("\n".join(report))
            return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
