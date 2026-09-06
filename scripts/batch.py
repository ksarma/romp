#!/usr/bin/env python3
"""scripts/batch.py: land many PRs as one batch PR with one merge commit.

Member PRs stay ordinary PRs against main. This tool merges their heads, in dependency order, into
a fresh branch `batch/<name>`, the batcher runs one full sweep at the batch head, and one PR to main
carries a generated digest. When that PR is merged with a merge commit, GitHub marks every member
merged on its own (a PR is marked merged when its head commits become reachable from its base
branch through another merge: "indirect merges"). No member is ever merged into another PR's
branch, and nothing here squashes or rebases: a squash or rebase of the batch would rewrite the
SHAs, leave every member open, and break retargeting.

Subcommands, in the order a batch goes through them:

  plan       [--labeled] [--name N]   pick the members, order them, predict conflicts, write the plan
  assemble   <name> [--without N] [--resolve N] [--repin N|all] [--continue|--abort]
                                      merge the pinned heads into ../romp-batch-<name> (the branch
                                      is the mutex: refuses if another origin/batch/* exists)
  verify     <name> [--sweep TEXT]    provenance, pinned heads, bases, ledger check, sweep, own CI
  summarize  <name>                   create or update the batch PR body; comment on each member
  pull       <name> N [--reason ..]   rebuild without N (and N's dependents), push, re-summarize
  land       <name> [--auto]          verify again, then merge the batch PR with a merge commit
  finish     <name>                   confirm members read MERGED, retarget, delete branches, orphans
  bisect     <name> -- <cmd...>       first-parent bisect of the batch chain; names the member

State lives in `<git common dir>/batch/<name>.json` (shared by every worktree of the clone). The
tool needs git and the GitHub CLI (`gh`, or the binary named by ROMP_GH); it imports nothing beyond
the standard library. It acts on the clone it lives in (or ROMP_BATCH_REPO), never on the shell's
cwd, so a misnamed cwd cannot make it assemble the wrong repository.

Contracts the tests hold this file to (tests/test_batch_tool.py):
  - plan orders dependents after their bases and excludes drafts, `major-feature` and `hold`;
  - assemble refuses when any other `batch/*` ref exists on origin;
  - provenance fails on an undeclared commit and passes on a `batch:` commit;
  - verify fails when a pinned head moved;
  - pull N drops N's dependents;
  - the body stays under GitHub's 65,536-character cap, details truncated first, the members table
    never.
"""
import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

BODY_CAP = 65_536          # GitHub's PR body limit, in characters
RESOLUTION_LINES = 300     # per conflicted merge, in the "Conflict resolutions" details block
PR_LIST_LIMIT = 200
MAIN = "main"
REMOTE = "origin"
LABEL_MAJOR = "major-feature"
LABEL_HOLD = "hold"
LABEL_LAND = "land"
LABEL_BATCH = "batch"
TIERS = ("fix", "tests-only", "feature", LABEL_MAJOR)
# Paths that put a member under "Read these first" when it touches them.
SENSITIVE_PREFIXES = ("kernel/", ".github/", ".githooks/")
SENSITIVE_FILES = ("install.sh", "uninstall.sh")
LEDGER_SCRIPT = os.path.join("scripts", "upstream-ledger.py")
UPSTREAM_MD = "UPSTREAM.md"

_DEPENDS_ON = re.compile(r"^\s*Depends-on:\s*#?(\d+)", re.IGNORECASE | re.MULTILINE)
_PR_TRAILER = re.compile(r"<!--\s*romp-pr:\s*(\{.*?\})\s*-->", re.DOTALL)
_BATCH_TRAILER = re.compile(r"<!--\s*romp-batch:\s*(\{.*?\})\s*-->", re.DOTALL)
_CONFLICT_LINE = re.compile(r"^CONFLICT \([^)]*\): Merge conflict in (.+)$", re.MULTILINE)
_FIRST_BAD = re.compile(r"^([0-9a-f]{40}) is the first bad commit", re.MULTILINE)
_CONFLICT_MARKER = re.compile(r"^\+(?:<{7} |>{7} |={7}$)", re.MULTILINE)


class Fail(Exception):
    """A refusal with a message for the batcher; exit status 1 (2 for usage and mutex refusals)."""

    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


# ── process helpers ──────────────────────────────────────────────────────────

def _run(cmd, cwd=None, check=True, env=None, input_text=None):
    proc = subprocess.run(cmd, cwd=cwd, env=env, input=input_text, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        raise Fail("%s failed (%d):\n%s%s" % (" ".join(cmd), proc.returncode, proc.stdout, proc.stderr))
    return proc


def git(*args, cwd=None, check=True):
    return _run(["git", *args], cwd=cwd, check=check).stdout.strip()


def git_ok(*args, cwd=None):
    return _run(["git", *args], cwd=cwd, check=False).returncode == 0


def gh_bin():
    gh = os.environ.get("ROMP_GH") or shutil.which("gh")
    if not gh:
        raise Fail("the GitHub CLI (gh) is not on PATH; install it or set ROMP_GH")
    return gh


def gh(*args, cwd=None, check=True):
    return _run([gh_bin(), *args], cwd=cwd, check=check)


def gh_json(*args, cwd=None):
    out = gh(*args, cwd=cwd).stdout
    try:
        return json.loads(out or "null")
    except json.JSONDecodeError as e:
        raise Fail("gh %s returned something that is not JSON: %s" % (" ".join(args), e))


# ── repository layout ────────────────────────────────────────────────────────

def repo_root():
    """The clone this script acts on: ROMP_BATCH_REPO, else the clone the script file lives in."""
    override = os.environ.get("ROMP_BATCH_REPO")
    if override:
        return os.path.realpath(override)
    here = os.path.dirname(os.path.realpath(__file__))
    return git("rev-parse", "--show-toplevel", cwd=here)


def common_dir(root):
    return git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root)


def state_dir(root):
    d = os.path.join(common_dir(root), "batch")
    os.makedirs(d, exist_ok=True)
    return d


def state_path(root, name):
    return os.path.join(state_dir(root), name + ".json")


def load_state(root, name):
    p = state_path(root, name)
    if not os.path.exists(p):
        raise Fail("no plan named %s (%s); run `scripts/batch.py plan` first" % (name, p))
    with open(p) as f:
        return json.load(f)


def save_state(root, state):
    p = state_path(root, state["name"])
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".batch-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


def worktree_dir(root, name):
    return os.path.join(os.path.dirname(root), "romp-batch-" + name)


def branch_of(name):
    return "batch/" + name


def remote_main():
    return "%s/%s" % (REMOTE, MAIN)


def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(state, line):
    """The assembly log: one timestamped line per action, shown in the body's details block."""
    state.setdefault("assembly", {}).setdefault("log", []).append("%s %s" % (now(), line))
    print(line)


def fetch(root, no_fetch):
    if not no_fetch:
        git("fetch", "--quiet", "--prune", REMOTE, cwd=root)


def members_by_n(state):
    return {int(k): v for k, v in state["members"].items()}


def short(sha):
    return (sha or "")[:10]


# ── PR data ──────────────────────────────────────────────────────────────────

PR_FIELDS = "number,title,body,labels,baseRefName,headRefName,headRefOid,isDraft,mergeable,statusCheckRollup,url,state"


def label_names(pr):
    return [l["name"] if isinstance(l, dict) else str(l) for l in (pr.get("labels") or [])]


def tier_of(labels):
    tiers = [l for l in labels if l in TIERS]
    return tiers[0] if tiers else None


def parse_trailer(body):
    """The optional `<!-- romp-pr: {...} -->` trailer: (dict|None, error|None)."""
    m = _PR_TRAILER.search(body or "")
    if not m:
        return None, None
    try:
        t = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        return None, "trailer is not JSON (%s)" % e
    return (t if isinstance(t, dict) else None), (None if isinstance(t, dict) else "trailer is not an object")


def ci_of(pr):
    """One word for the PR's own CI at its head: success, failure, pending, or none.

    `statusCheckRollup` mixes CheckRun entries (status/conclusion) with StatusContext entries
    (state); both spellings are read. An empty rollup on a CONFLICTING PR is the plan's "none (was
    conflicting)": GitHub starts no run for a PR it cannot merge."""
    rollup = pr.get("statusCheckRollup") or []
    if not rollup:
        return "none (was conflicting)" if pr.get("mergeable") == "CONFLICTING" else "none"
    words = set()
    for c in rollup:
        if c.get("__typename") == "StatusContext" or "state" in c:
            words.add((c.get("state") or "").upper())
        else:
            if (c.get("status") or "").upper() != "COMPLETED":
                words.add("PENDING")
            else:
                words.add((c.get("conclusion") or "").upper())
    if words & {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}:
        return "failure"
    if words & {"PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED", ""}:
        return "pending"
    return "success"


def sensitive_paths(paths):
    hits = []
    for p in paths:
        for pre in SENSITIVE_PREFIXES:
            if p.startswith(pre) and pre not in hits:
                hits.append(pre)
        if p in SENSITIVE_FILES and p not in hits:
            hits.append(p)
    return hits


def ensure_object(root, sha, ref_hint):
    """Make sure a pinned head is in the object store; a plain `fetch origin` brings every branch,
    but a head GitHub reports can be newer than the last fetch."""
    if not git_ok("cat-file", "-e", sha + "^{commit}", cwd=root):
        git("fetch", "--quiet", REMOTE, ref_hint, cwd=root)
        if not git_ok("cat-file", "-e", sha + "^{commit}", cwd=root):
            raise Fail("commit %s (head of %s) is not reachable from origin; was the branch force-pushed?" % (short(sha), ref_hint))


def merged_pr_for_branch(root, branch):
    """The number of a MERGED PR whose head was `branch`, or None. A PR based on such a branch is
    the stranded case (2026-09-06: four PRs merged into already-merged bases), so it is refused."""
    rows = gh_json("pr", "list", "--state", "merged", "--head", branch, "--json", "number", "--limit", "5", cwd=root)
    return rows[0]["number"] if rows else None


# ── plan ─────────────────────────────────────────────────────────────────────

def pick_name(root):
    today = _dt.date.today().isoformat()
    remote_batches = set(git("for-each-ref", "--format=%(refname:short)", "refs/remotes/%s/batch/" % REMOTE, cwd=root).split())
    for letter in "abcdefghijklmnopqrstuvwxyz":
        name = today + letter
        if os.path.exists(state_path(root, name)):
            continue
        if "%s/batch/%s" % (REMOTE, name) in remote_batches:
            continue
        return name
    raise Fail("27 batches in one day; pass --name")


def order_members(cands):
    """Dependencies first, then by number (Kahn's algorithm with a number-ordered frontier)."""
    import heapq
    indeg = {n: 0 for n in cands}
    dependents = {n: [] for n in cands}
    for n, m in cands.items():
        for d in m["depends_on"]:
            if d in cands:
                indeg[n] += 1
                dependents[d].append(n)
    heap = [n for n, k in indeg.items() if k == 0]
    heapq.heapify(heap)
    order = []
    while heap:
        n = heapq.heappop(heap)
        order.append(n)
        for d in sorted(dependents[n]):
            indeg[d] -= 1
            if indeg[d] == 0:
                heapq.heappush(heap, d)
    if len(order) != len(cands):
        cyc = sorted(set(cands) - set(order))
        raise Fail("dependency cycle among PRs %s" % ", ".join("#%d" % n for n in cyc))
    return order


def predict_conflicts(root, base_sha, ordered, cands):
    """Read-only merge prediction with `git merge-tree --write-tree` against the accumulating tree.

    Each clean step becomes a dangling commit object (commit-tree; no ref is written, so nothing
    but the object store changes and gc reclaims it) so the next step's merge base is right. A
    conflicting member is recorded with its files and the earlier members whose own diff touches
    those files, and the accumulation continues without it."""
    acc = base_sha
    for n in ordered:
        m = cands[n]
        proc = _run(["git", "merge-tree", "--write-tree", "--name-only", "--no-messages", acc, m["head"]], cwd=root, check=False)
        lines = proc.stdout.splitlines()
        if proc.returncode == 0 and lines:
            tree = lines[0]
            acc = git("commit-tree", tree, "-p", acc, "-p", m["head"], "-m", "batch plan: after #%d" % n, cwd=root)
            m["predicted_conflict"] = None
        elif proc.returncode == 1 and lines:
            files = []
            for l in lines[1:]:
                if not l.strip():
                    break
                files.append(l.strip())
            with_members = [k for k in ordered[:ordered.index(n)]
                            if set(cands[k]["touches"]) & set(files) and cands[k].get("predicted_conflict") is None]
            m["predicted_conflict"] = {"files": files, "with": with_members}
        else:
            m["predicted_conflict"] = {"files": [], "with": [], "error": (proc.stderr or proc.stdout).strip()[:300]}


def cmd_plan(args):
    root = repo_root()
    fetch(root, args.no_fetch)
    base_sha = git("rev-parse", remote_main(), cwd=root)
    name = args.name or pick_name(root)
    prs = gh_json("pr", "list", "--state", "open", "--limit", str(PR_LIST_LIMIT), "--json", PR_FIELDS, cwd=root)
    by_n = {pr["number"]: pr for pr in prs}

    excluded = {}   # n -> reason
    cands = {}
    for n, pr in sorted(by_n.items()):
        labels = label_names(pr)
        if pr.get("isDraft"):
            excluded[n] = "draft"
        elif LABEL_MAJOR in labels:
            excluded[n] = "labeled %s (discussed first)" % LABEL_MAJOR
        elif LABEL_HOLD in labels:
            excluded[n] = "labeled %s" % LABEL_HOLD
        elif LABEL_BATCH in labels or pr["headRefName"].startswith("batch/"):
            excluded[n] = "a batch PR"
        elif args.labeled and LABEL_LAND not in labels:
            excluded[n] = "not labeled %s (plan --labeled)" % LABEL_LAND
        else:
            trailer, terr = parse_trailer(pr.get("body"))
            cands[n] = {
                "n": n, "title": pr["title"], "url": pr.get("url"),
                "head": pr["headRefOid"], "head_ref": pr["headRefName"], "base_ref": pr["baseRefName"],
                "labels": labels, "tier": tier_of(labels),
                "depends_on": sorted({int(x) for x in _DEPENDS_ON.findall(pr.get("body") or "")}),
                "trailer": trailer, "trailer_error": terr,
                "mergeable": pr.get("mergeable"), "ci": ci_of(pr),
                "touches": [], "predicted_conflict": None,
            }
    # A base that is another open PR's branch is a dependency on that PR (and if that PR is not a
    # candidate, the fixpoint below takes the dependent out with it, naming why); any other non-main
    # base leaves the PR out (a base belonging to a merged PR is the stranded case and gets the fix
    # in its reason).
    heads = {pr["headRefName"]: n for n, pr in by_n.items()}
    for n, m in list(cands.items()):
        b = m["base_ref"]
        if b == MAIN:
            continue
        if b in heads and heads[b] != n:
            if heads[b] not in m["depends_on"]:
                m["depends_on"].append(heads[b])
                m["depends_on"].sort()
            continue
        merged = merged_pr_for_branch(root, b)
        if merged:
            excluded[n] = "base %s belongs to merged PR #%d; run `gh pr edit %d --base %s`" % (b, merged, n, MAIN)
        else:
            excluded[n] = "base %s is neither %s nor a candidate's branch" % (b, MAIN)
        del cands[n]
    # A dependency that is not a candidate takes its dependents out too (failure mode 7).
    changed = True
    while changed:
        changed = False
        for n, m in list(cands.items()):
            for d in m["depends_on"]:
                if d not in cands:
                    why = excluded.get(d, "not an open PR")
                    excluded[n] = "depends on #%d (%s)" % (d, why)
                    del cands[n]
                    changed = True
                    break
    for n, m in cands.items():
        ensure_object(root, m["head"], m["head_ref"])
        mb = git("merge-base", base_sha, m["head"], cwd=root)
        m["touches"] = git("diff", "--name-only", mb, m["head"], cwd=root).split()
    ordered = order_members(cands)
    predict_conflicts(root, base_sha, ordered, cands)

    state = {
        "name": name, "created": now(), "base": base_sha, "labeled": bool(args.labeled),
        "order": ordered, "members": {str(n): cands[n] for n in ordered},
        "excluded": [{"n": n, "reason": r} for n, r in sorted(excluded.items())],
        "pulled": [], "assembly": {"log": []}, "sweep": None, "verified": None, "pr": None, "commented": {},
    }
    save_state(root, state)

    print("plan %s: base %s (%s), %d member(s), %d excluded" % (name, remote_main(), short(base_sha), len(ordered), len(excluded)))
    for n in ordered:
        m = cands[n]
        flags = []
        if m["depends_on"]:
            flags.append("after " + ", ".join("#%d" % d for d in m["depends_on"]))
        if m["trailer"] is None:
            flags.append("trailer missing" if not m["trailer_error"] else m["trailer_error"])
        if m["tier"] is None:
            flags.append("unlabeled")
        pc = m["predicted_conflict"]
        if pc:
            flags.append("PREDICTED CONFLICT in %s%s" % (", ".join(pc["files"]) or "?",
                                                         (" with " + ", ".join("#%d" % k for k in pc["with"])) if pc["with"] else ""))
        print("  #%d %s @%s [%s]%s" % (n, m["title"], short(m["head"]), m["tier"] or "unlabeled",
                                     ("  " + "; ".join(flags)) if flags else ""))
    for row in state["excluded"]:
        print("  excluded #%d: %s" % (row["n"], row["reason"]))
    missing = [n for n in ordered if cands[n]["trailer"] is None]
    if missing:
        print("message the authors once (trailer missing): %s" % ", ".join("#%d" % n for n in missing))
    print("written: %s" % state_path(root, name))


# ── assemble ─────────────────────────────────────────────────────────────────

def other_remote_batches(root, name):
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/remotes/%s/batch/" % REMOTE, cwd=root).split()
    return [r for r in refs if r != "%s/%s" % (REMOTE, branch_of(name))]


def merge_in_progress(wt):
    return os.path.exists(os.path.join(git("rev-parse", "--git-path", "MERGE_HEAD", cwd=wt)))


def prepare_worktree(root, name):
    """A fresh `batch/<name>` at origin/main in ../romp-batch-<name>, reusing the directory when it
    is already this batch's worktree. That directory is the tool's, so resetting it is fine; the
    shared checkout is never touched."""
    wt = worktree_dir(root, name)
    br = branch_of(name)
    if os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt):
        if merge_in_progress(wt):
            git("merge", "--abort", cwd=wt)
        git("checkout", "--quiet", "-B", br, remote_main(), cwd=wt)
    else:
        git("worktree", "add", "--quiet", "-B", br, wt, remote_main(), cwd=root)
    # rerere in the repository config: the cache (.git/rr-cache) is shared by every worktree, which
    # is what lets a re-assemble replay a resolution the batcher made once.
    git("config", "rerere.enabled", "true", cwd=wt)
    git("config", "rerere.autoUpdate", "true", cwd=wt)
    return wt


def dependents_of(state, n):
    """Transitive dependents of n among the planned members."""
    members = members_by_n(state)
    out, frontier = set(), {n}
    while frontier:
        nxt = set()
        for k, m in members.items():
            if k not in out and set(m["depends_on"]) & frontier:
                out.add(k)
                nxt.add(k)
        frontier = nxt
    return sorted(out)


def member_rows_added(root, base_sha, head, path=UPSTREAM_MD):
    """The table rows a member ADDS to UPSTREAM.md against its merge base, and whether that is all
    it does to the file. (added_rows, only_rows)."""
    mb = git("merge-base", base_sha, head, cwd=root)
    diff = _run(["git", "diff", "--unified=0", mb, head, "--", path], cwd=root, check=False).stdout
    rows, other = [], False
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "@@", "diff ", "index ")):
            continue
        if line.startswith("+"):
            body = line[1:]
            if body.strip().startswith("|") and body.strip().endswith("|"):
                rows.append(body.strip())
            elif body.strip():
                other = True
        elif line.startswith("-") and line[1:].strip():
            other = True
    return rows, not other


def convert_ledger_rows(root, wt, state, m):
    """The straggler fix inside a member's merge commit: a member that still appends a UPSTREAM.md
    row after the migration conflicts on that file; each added row becomes an entry file through
    `scripts/upstream-ledger.py import --row '<row>'` and the table hunk is dropped by keeping the
    batch side of UPSTREAM.md. Returns the number of rows converted, or None when this conversion
    does not apply (no ledger script in the batch tree, the member changed more than rows, or the
    conversion failed) so the caller treats the conflict like any other.

    The `import --row` interface is the plan's specification of the ledger script (built by a
    sibling branch); the first real batch verifies the two agree."""
    if not os.path.exists(os.path.join(wt, LEDGER_SCRIPT)):
        return None
    rows, only_rows = member_rows_added(root, state["base"], m["head"])
    if not rows or not only_rows:
        return None
    for row in rows:
        proc = _run([sys.executable, LEDGER_SCRIPT, "import", "--row", row], cwd=wt, check=False)
        if proc.returncode != 0:
            log(state, "#%d: import --row failed: %s" % (m["n"], (proc.stderr or proc.stdout).strip()[:300]))
            return None
    git("checkout", "--ours", "--", UPSTREAM_MD, cwd=wt)
    git("add", "--", UPSTREAM_MD, cwd=wt)
    if os.path.isdir(os.path.join(wt, "upstream")):
        git("add", "--", "upstream", cwd=wt)
    return len(rows)


def unmerged_paths(wt):
    return git("diff", "--name-only", "--diff-filter=U", cwd=wt).split()


def hunk_count(wt, merge_sha, path):
    out = _run(["git", "show", "--cc", "--format=", merge_sha, "--", path], cwd=wt, check=False).stdout
    return sum(1 for l in out.splitlines() if l.startswith("@@@"))


def hold_back(root, state, m, reason, files=None, with_members=None, notify=True):
    entry = {"n": m["n"], "reason": reason, "files": files or [], "with": with_members or []}
    state["assembly"].setdefault("held", []).append(entry)
    log(state, "#%d held back: %s" % (m["n"], reason))
    if notify and files is not None:
        named = ", ".join("#%d" % k for k in (with_members or [])) or "an earlier member"
        text = ("This PR conflicts with %s in %s, so this batch goes ahead without it. "
                "Merge origin/%s (or that PR's branch) into yours, push, and comment here; the next batch includes it."
                % (named, ", ".join(files), MAIN))
        # Once per distinct reason: a rebuild after `pull` meets the same conflict again, and the
        # owner does not need the same comment twice.
        told = state.setdefault("held_notified", {})
        if told.get(str(m["n"])) != text:
            gh("pr", "comment", str(m["n"]), "--body", text, cwd=root, check=False)
            told[str(m["n"])] = text
        print("postal (kind: coordinate) to the owner of #%d: %s" % (m["n"], text))


def merge_member(root, wt, state, m, resolve_set):
    """One member merge. Returns 'merged', 'held', or 'stopped' (waiting for --continue)."""
    n = m["n"]
    if m["base_ref"] != MAIN and merged_pr_for_branch(root, m["base_ref"]):
        hold_back(root, state, m, "base %s belongs to a merged PR; retarget it to %s" % (m["base_ref"], MAIN), notify=False)
        return "held"
    ensure_object(root, m["head"], m["head_ref"])
    msg = "Merge #%d: %s" % (n, m["title"])
    env = dict(os.environ, GIT_MERGE_AUTOEDIT="no")
    proc = subprocess.run(["git", "merge", "--no-ff", "--no-edit", "-m", msg, m["head"]], cwd=wt, env=env,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        sha = git("rev-parse", "HEAD", cwd=wt)
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": None})
        log(state, "merged #%d at %s -> %s" % (n, short(m["head"]), short(sha)))
        return "merged"
    if not merge_in_progress(wt):
        raise Fail("git merge of #%d failed without a conflict to resolve:\n%s%s" % (n, proc.stdout, proc.stderr))
    conflicted = sorted(set(_CONFLICT_LINE.findall(proc.stdout + proc.stderr)))
    still = unmerged_paths(wt)
    resolved = None
    if not still and merge_in_progress(wt):
        # rerere replayed a recorded resolution and staged the result (rerere.autoUpdate).
        resolved = {"files": conflicted, "how": "rerere replayed a recorded resolution", "hunks": None, "review": None}
    elif UPSTREAM_MD in still:
        rows = convert_ledger_rows(root, wt, state, m)
        if rows is not None:
            still = unmerged_paths(wt)
            if not still:
                resolved = {"files": [UPSTREAM_MD], "how": "%d UPSTREAM.md row(s) converted to entries (mechanical)" % rows,
                            "hunks": None, "review": "mechanical"}
    if resolved is not None and not unmerged_paths(wt):
        git("commit", "--quiet", "--no-edit", cwd=wt)
        sha = git("rev-parse", "HEAD", cwd=wt)
        resolved["hunks"] = sum(hunk_count(wt, sha, f) for f in resolved["files"])
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": resolved})
        log(state, "merged #%d -> %s with %s" % (n, short(sha), resolved["how"]))
        return "merged"
    files = still or conflicted
    if n in resolve_set:
        state["assembly"]["cursor"] = {"n": n, "files": files}
        log(state, "#%d stopped for resolution in %s; resolve per hunk in %s, `git add` the files, then "
                   "`scripts/batch.py assemble %s --continue [--reviewed '<note>']`" % (n, ", ".join(files), wt, state["name"]))
        return "stopped"
    git("merge", "--abort", cwd=wt)
    earlier = [e["n"] for e in state["assembly"]["merged"]
               if set(members_by_n(state)[e["n"]]["touches"]) & set(files)]
    hold_back(root, state, m, "conflicts with %s in %s" % (", ".join("#%d" % k for k in earlier) or "the batch", ", ".join(files)),
              files=files, with_members=earlier, notify=not state["assembly"].get("no_notify"))
    return "held"


def continue_after_resolution(root, wt, state, reviewed):
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to continue: no member is stopped for resolution")
    if not merge_in_progress(wt):
        raise Fail("no merge is in progress in %s; run assemble again without --continue" % wt)
    m = members_by_n(state)[cur["n"]]
    if git("rev-parse", "MERGE_HEAD", cwd=wt) != m["head"]:
        raise Fail("MERGE_HEAD in %s is not #%d's pinned head" % (wt, m["n"]))
    still = unmerged_paths(wt)
    if still:
        raise Fail("still unmerged: %s (resolve and `git add` them first)" % ", ".join(still))
    staged = _run(["git", "diff", "--cached", "--no-color", "--", *cur["files"]], cwd=wt).stdout
    if _CONFLICT_MARKER.search(staged):
        raise Fail("a conflict marker is still staged in %s" % ", ".join(cur["files"]))
    git("commit", "--quiet", "--no-edit", cwd=wt)
    sha = git("rev-parse", "HEAD", cwd=wt)
    resolved = {"files": cur["files"], "how": "resolved by the batcher, per hunk",
                "hunks": sum(hunk_count(wt, sha, f) for f in cur["files"]),
                "review": reviewed}
    state["assembly"]["merged"].append({"n": m["n"], "merge": sha, "resolved": resolved})
    state["assembly"]["cursor"] = None
    log(state, "merged #%d -> %s after a hand resolution in %s (%d hunks); review round: %s"
        % (m["n"], short(sha), ", ".join(cur["files"]), resolved["hunks"], reviewed or "NOT RECORDED"))


def abort_resolution(root, wt, state):
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to abort: no member is stopped for resolution")
    if merge_in_progress(wt):
        git("merge", "--abort", cwd=wt)
    m = members_by_n(state)[cur["n"]]
    earlier = [e["n"] for e in state["assembly"]["merged"] if set(members_by_n(state)[e["n"]]["touches"]) & set(cur["files"])]
    hold_back(root, state, m, "conflicts with %s in %s (resolution abandoned)" % (", ".join("#%d" % k for k in earlier) or "the batch", ", ".join(cur["files"])),
              files=cur["files"], with_members=earlier, notify=not state["assembly"].get("no_notify"))
    state["assembly"]["cursor"] = None


def run_assembly(root, state, resolve_set, resume):
    """Merge the pending members in order; stop at a --resolve member's conflict; hold the rest back."""
    wt = worktree_dir(root, state["name"])
    members = members_by_n(state)
    pending = list(state["assembly"]["pending"])
    while pending:
        n = pending[0]
        m = members[n]
        held_ns = {h["n"] for h in state["assembly"].get("held", [])}
        blockers = [d for d in m["depends_on"] if d in held_ns or d in state["pulled"]]
        if blockers:
            hold_back(root, state, m, "depends on %s (not in this batch)" % ", ".join("#%d" % d for d in blockers), notify=False)
            pending.pop(0)
            state["assembly"]["pending"] = pending
            continue
        result = merge_member(root, wt, state, m, resolve_set)
        pending.pop(0)
        state["assembly"]["pending"] = pending
        if result == "stopped":
            save_state(root, state)
            return False
        save_state(root, state)
    state["assembly"]["head"] = git("rev-parse", "HEAD", cwd=wt)
    state["assembly"]["pending"] = []
    state["assembly"]["cursor"] = None
    state["verified"] = None
    log(state, "assembled %s at %s: %d merged, %d held back" % (branch_of(state["name"]), short(state["assembly"]["head"]),
                                                                len(state["assembly"]["merged"]), len(state["assembly"].get("held", []))))
    save_state(root, state)
    return True


def cmd_assemble(args):
    root = repo_root()
    state = load_state(root, args.name)
    fetch(root, args.no_fetch)
    others = other_remote_batches(root, args.name)
    if others:
        raise Fail("another batch is open on %s: %s. One batch at a time; finish it (or delete its branch) first."
                   % (REMOTE, ", ".join(others)), code=2)
    wt = worktree_dir(root, args.name)
    if args.cont or args.abort:
        if args.cont:
            continue_after_resolution(root, wt, state, args.reviewed)
        else:
            abort_resolution(root, wt, state)
        save_state(root, state)
        if not run_assembly(root, state, set(args.resolve or []), resume=True):
            raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)
        return
    if os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt) and merge_in_progress(wt) \
            and state["assembly"].get("cursor"):
        raise Fail("#%d is stopped for resolution in %s; finish with --continue or drop it with --abort"
                   % (state["assembly"]["cursor"]["n"], wt))
    members = members_by_n(state)
    for n in args.repin or []:
        targets = list(members) if n == "all" else [int(n)]
        for k in targets:
            if k not in members:
                raise Fail("#%d is not a member of %s" % (k, args.name))
            pr = gh_json("pr", "view", str(k), "--json", "headRefOid,title,body,labels,statusCheckRollup,mergeable", cwd=root)
            old = members[k]["head"]
            members[k]["head"] = pr["headRefOid"]
            members[k]["title"] = pr["title"]
            members[k]["labels"] = label_names(pr)
            members[k]["tier"] = tier_of(members[k]["labels"])
            members[k]["trailer"], members[k]["trailer_error"] = parse_trailer(pr.get("body"))
            members[k]["ci"] = ci_of(pr)
            ensure_object(root, pr["headRefOid"], members[k]["head_ref"])
            mb = git("merge-base", remote_main(), pr["headRefOid"], cwd=root)
            members[k]["touches"] = git("diff", "--name-only", mb, pr["headRefOid"], cwd=root).split()
            state["members"][str(k)] = members[k]
            log(state, "re-pinned #%d: %s -> %s" % (k, short(old), short(pr["headRefOid"])))
    for n in args.without or []:
        if n not in members:
            raise Fail("#%d is not a member of %s" % (n, args.name))
        if n not in state["pulled"]:
            state["pulled"].append(n)
    dropped = []
    for n in list(state["pulled"]):
        for d in dependents_of(state, n):
            if d not in state["pulled"]:
                state["pulled"].append(d)
                dropped.append((d, n))
    state["pulled"].sort()
    prepare_worktree(root, args.name)
    state["base"] = git("rev-parse", remote_main(), cwd=root)
    old_log = state["assembly"].get("log", [])
    state["assembly"] = {"log": old_log, "merged": [], "held": [], "pending": [n for n in state["order"] if n not in state["pulled"]],
                         "cursor": None, "head": None, "no_notify": bool(args.no_notify)}
    log(state, "assembling %s from %s at %s; pulled: %s" % (branch_of(args.name), remote_main(), short(state["base"]),
                                                            ", ".join("#%d" % n for n in state["pulled"]) or "none"))
    for d, n in dropped:
        log(state, "#%d dropped with #%d (depends on it)" % (d, n))
    if not run_assembly(root, state, set(args.resolve or []), resume=False):
        raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)


# ── verify ───────────────────────────────────────────────────────────────────

def parents_of(sha, cwd):
    return git("rev-list", "--parents", "-n", "1", sha, cwd=cwd).split()[1:]


def subject_of(sha, cwd):
    return git("log", "-n", "1", "--format=%s", sha, cwd=cwd)


def is_ancestor(a, b, cwd):
    return git_ok("merge-base", "--is-ancestor", a, b, cwd=cwd)


def clean_merge_tree(p1, p2, cwd):
    """The tree a clean merge of p1 and p2 produces, or None when it conflicts. (None, 'unsupported')
    when this git lacks `merge-tree --write-tree` (added in git 2.38)."""
    proc = _run(["git", "merge-tree", "--write-tree", "--no-messages", p1, p2], cwd=cwd, check=False)
    if proc.returncode == 0:
        return proc.stdout.split()[0], None
    if proc.returncode == 1:
        return None, "conflicts"
    return None, "unsupported"


def check_provenance(root, state, lines):
    """(a) Every non-merge commit the batch adds is a declared `batch:` commit, and the first-parent
    chain since main is exactly the member merges plus declared commits (a merge of origin/main is
    allowed). Each member merge must be the clean merge of its parents unless recorded as resolved:
    an edit slipped into a merge commit is otherwise invisible to `rev-list --no-merges`."""
    ok = True
    br = branch_of(state["name"])
    merged = state["assembly"].get("merged", [])
    members = members_by_n(state)
    heads = {members[e["n"]]["head"]: e["n"] for e in merged}
    excl = ["^" + remote_main()] + ["^" + h for h in heads]
    stray = git("rev-list", br, *excl, "--no-merges", cwd=root).split()
    undeclared = [s for s in stray if not subject_of(s, root).startswith("batch:")]
    declared = [s for s in stray if subject_of(s, root).startswith("batch:")]
    if undeclared:
        ok = False
        for s in undeclared:
            lines.append("FAIL provenance: undeclared commit %s (%s); commit batch changes with a `batch:` subject" % (short(s), subject_of(s, root)))
    chain = git("rev-list", "--first-parent", "--reverse", "%s..%s" % (remote_main(), br), cwd=root).split()
    member_merges = 0
    for c in chain:
        ps = parents_of(c, root)
        if len(ps) == 1:
            if c not in declared:
                ok = False
                lines.append("FAIL provenance: %s on the first-parent chain is not a `batch:` commit" % short(c))
            continue
        if len(ps) != 2:
            ok = False
            lines.append("FAIL provenance: %s is an octopus merge" % short(c))
            continue
        p1, p2 = ps
        if p2 in heads:
            member_merges += 1
            n = heads[p2]
            rec = next(e for e in merged if e["n"] == n)
            if rec["merge"] != c:
                ok = False
                lines.append("FAIL provenance: #%d's merge on the chain is %s, recorded %s" % (n, short(c), short(rec["merge"])))
            tree, why = clean_merge_tree(p1, p2, root)
            merge_tree = git("rev-parse", c + "^{tree}", cwd=root)
            if why == "unsupported":
                lines.append("note provenance: this git cannot check #%d's merge tree (needs git 2.38)" % n)
            elif rec.get("resolved"):
                lines.append("ok   provenance: #%d merge carries a recorded resolution (%s)" % (n, rec["resolved"]["how"]))
            elif tree is None:
                ok = False
                lines.append("FAIL provenance: #%d's merge %s resolved a conflict that is not recorded" % (n, short(c)))
            elif tree != merge_tree:
                ok = False
                lines.append("FAIL provenance: #%d's merge %s differs from the clean merge of its parents (undeclared change)" % (n, short(c)))
        elif is_ancestor(p2, remote_main(), root):
            lines.append("ok   provenance: %s merges %s" % (short(c), remote_main()))
        else:
            ok = False
            lines.append("FAIL provenance: %s merges %s, which is neither a member head nor %s" % (short(c), short(p2), remote_main()))
    if member_merges != len(merged):
        ok = False
        lines.append("FAIL provenance: %d member merges on the chain, %d recorded" % (member_merges, len(merged)))
    if ok:
        lines.append("ok   provenance: %d member merge(s), %d declared batch: commit(s), nothing else" % (member_merges, len(declared)))
    return ok


def cmd_verify(args, quiet=False):
    root = repo_root()
    state = load_state(root, args.name)
    fetch(root, args.no_fetch)
    lines, ok = [], True
    br = branch_of(args.name)
    if not git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        raise Fail("%s does not exist; run assemble first" % br)
    head = git("rev-parse", br, cwd=root)
    if state["assembly"].get("cursor"):
        raise Fail("#%d is still stopped for resolution; --continue or --abort first" % state["assembly"]["cursor"]["n"])
    if state["assembly"].get("head") != head:
        # A `batch:` commit the batcher added after assembly moves the tip; provenance below decides
        # whether what moved it is allowed. The recorded head follows the branch.
        lines.append("note head: %s moved from %s to %s since assembly; the chain is checked below"
                     % (br, short(state["assembly"].get("head")), short(head)))
        state["assembly"]["head"] = head
    ok = check_provenance(root, state, lines) and ok
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    in_batch_refs = {members[e["n"]]["head_ref"] for e in merged}
    for e in merged:
        m = members[e["n"]]
        pr = gh_json("pr", "view", str(m["n"]), "--json", "headRefOid,state,baseRefName,isDraft,statusCheckRollup,mergeable", cwd=root)
        if pr["headRefOid"] != m["head"]:
            ok = False
            lines.append("FAIL head moved: #%d pinned %s, now %s (assemble --repin %d, then re-assemble)"
                         % (m["n"], short(m["head"]), short(pr["headRefOid"]), m["n"]))
        else:
            lines.append("ok   head: #%d at %s" % (m["n"], short(m["head"])))
        if pr.get("state") != "OPEN":
            ok = False
            lines.append("FAIL state: #%d is %s (pull it; if it merged alone, merge %s into the batch)" % (m["n"], pr.get("state"), remote_main()))
        if pr.get("baseRefName") != MAIN:
            b = pr.get("baseRefName")
            if b in in_batch_refs:
                lines.append("ok   base: #%d is based on %s, which is in the batch (land retargets it to %s before the merge)" % (m["n"], b, MAIN))
            elif git_ok("rev-parse", "--verify", "--quiet", "%s/%s" % (REMOTE, b), cwd=root) and is_ancestor("%s/%s" % (REMOTE, b), remote_main(), root):
                lines.append("ok   base: #%d is based on %s, already in %s" % (m["n"], b, MAIN))
            else:
                ok = False
                lines.append("FAIL base: #%d is based on %s, which is neither in the batch nor in %s" % (m["n"], b, MAIN))
        m["ci"] = ci_of(pr)
        lines.append("ci   #%d: %s" % (m["n"], m["ci"]))
        state["members"][str(m["n"])] = m
    wt = worktree_dir(root, args.name)
    ledger = os.path.join(wt, LEDGER_SCRIPT)
    if os.path.exists(ledger):
        proc = _run([sys.executable, LEDGER_SCRIPT, "check"], cwd=wt, check=False)
        if proc.returncode == 0:
            lines.append("ok   ledger: check clean")
            state["ledger"] = "clean"
        else:
            ok = False
            lines.append("FAIL ledger: %s" % (proc.stdout + proc.stderr).strip()[:500])
            state["ledger"] = "failed"
    else:
        lines.append("note ledger: %s is not in the batch tree (pre-migration); not checked" % LEDGER_SCRIPT)
        state["ledger"] = "pre-migration"
    if args.sweep:
        state["sweep"] = {"text": args.sweep, "head": head, "at": now()}
    sw = state.get("sweep")
    if not sw:
        ok = False
        lines.append("FAIL sweep: none recorded; run the full sweep at %s and pass --sweep '<counts>'" % short(head))
    elif sw["head"] != head:
        ok = False
        lines.append("FAIL sweep: recorded at %s, the batch is at %s; sweep again" % (short(sw["head"]), short(head)))
    else:
        lines.append("ok   sweep at %s: %s" % (short(head), sw["text"]))
    state["verified"] = {"head": head, "at": now(), "ok": ok, "lines": lines}
    save_state(root, state)
    if not quiet:
        print("\n".join(lines))
        print("verify %s: %s at %s" % (args.name, "OK" if ok else "FAILED", short(head)))
    if not ok:
        raise Fail("verify failed")
    return state


# ── summarize (the body) ─────────────────────────────────────────────────────

def _cell(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def sweep_cell(trailer):
    if not trailer:
        return "not stated"
    sw = trailer.get("sweep")
    if not isinstance(sw, dict):
        return "not stated"
    parts = []
    for k in ("pytest", "bats", "npm", "typecheck"):
        if k in sw:
            parts.append("%s %s" % (k, sw[k]))
    if trailer.get("sweep_head"):
        parts.append("@%s" % short(str(trailer["sweep_head"])))
    return ", ".join(parts) if parts else "not stated"


def read_first_reasons(m, resolved):
    """The computed rule: a member is listed under "Read these first" when its merge needed a
    resolution, when its tier is `feature` or unlabeled, when it touches kernel/, .github/,
    .githooks/, install.sh or uninstall.sh, when its trailer is missing, or when its own CI never
    ran because it was conflicting."""
    reasons = []
    if resolved:
        note = resolved.get("review")
        rev = ("one review round: %s" % note) if note and note != "mechanical" else (
            "mechanical" if note == "mechanical" else "review round NOT recorded")
        hunks = resolved.get("hunks")
        reasons.append("conflict resolved in %s (%s); %s. [combined diff below]"
                       % (", ".join(resolved["files"]), ("%d hunk%s" % (hunks, "" if hunks == 1 else "s")) if hunks is not None else resolved["how"], rev))
    if m.get("tier") is None:
        reasons.append("unlabeled")
    elif m["tier"] == "feature":
        reasons.append("feature")
    sens = sensitive_paths(m.get("touches") or [])
    if sens:
        reasons.append("touches " + ", ".join(sens))
    if m.get("trailer") is None:
        reasons.append("trailer not stated" if not m.get("trailer_error") else m["trailer_error"])
    if (m.get("ci") or "").startswith("none"):
        reasons.append("own CI: %s" % m["ci"])
    return reasons


def gather_body_inputs(root, state):
    """Everything the body needs that comes from git: resolution diffs and the ledger entry table."""
    br = branch_of(state["name"])
    members = members_by_n(state)
    resolutions = []
    for e in state["assembly"].get("merged", []):
        if e.get("resolved"):
            out = _run(["git", "show", "--cc", "--format=", "--no-color", e["merge"], "--", *e["resolved"]["files"]], cwd=root, check=False).stdout
            resolutions.append({"n": e["n"], "diff": out})
    entries = []
    if git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        mb = git("merge-base", remote_main(), br, cwd=root)
        for line in git("diff", "--name-status", mb, br, "--", "upstream/", cwd=root).splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status, path = parts[0][0], parts[-1]
            title, st = "", ""
            if status != "D":
                text = _run(["git", "show", "%s:%s" % (br, path)], cwd=root, check=False).stdout
                hdr = {}
                if text.startswith("---"):
                    for l in text.split("\n")[1:]:
                        if l.strip() == "---":
                            break
                        if ":" in l:
                            k, v = l.split(":", 1)
                            hdr[k.strip()] = v.strip()
                title, st = hdr.get("title", ""), hdr.get("status", "")
            who = [n for n, m in members.items() if path in (m.get("touches") or [])]
            entries.append({"path": path, "title": title, "status": st,
                            "change": {"A": "added", "M": "modified", "D": "deleted"}.get(status, status),
                            "members": who})
    return {"resolutions": resolutions, "entries": entries}


def render_body(state, inputs, cap=BODY_CAP):
    """The batch PR body. Pure over its inputs so the cap rule is testable: when the body exceeds
    the cap the details blocks are truncated first (resolutions, then the assembly log), then the
    ledger table collapses to a count; the members table and the trailer are never cut, and a body
    still over the cap after that is refused with the advice to split the batch."""
    name = state["name"]
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    held = state["assembly"].get("held", [])
    pulled = state.get("pulled", [])
    resolved_by_n = {e["n"]: e.get("resolved") for e in merged}
    v = state.get("verified") or {}
    sw = state.get("sweep") or {}
    head = state["assembly"].get("head") or ""
    extra = []
    if held:
        extra.append("%d held back" % len(held))
    if pulled:
        extra.append("%d pulled" % len(pulled))
    title = "# Batch %s: %d PR%s%s" % (name, len(merged), "" if len(merged) == 1 else "s", (" (%s)" % ", ".join(extra)) if extra else "")
    if v.get("ok") and v.get("head") == head:
        ledger = {"clean": "ledger check clean", "pre-migration": "ledger: pre-migration, not checked", "failed": "ledger check FAILED"}.get(state.get("ledger"), "ledger: not checked")
        verified = ("Merge with \"Create a merge commit\". Verified at %s: %s; provenance clean; %s. CI on this PR: see checks."
                    % (short(head), sw.get("text", "sweep not recorded"), ledger))
    else:
        verified = "Merge with \"Create a merge commit\". NOT VERIFIED at %s: run `scripts/batch.py verify %s` (verification is %s)." % (
            short(head), name, "stale" if v else "missing")

    read_first = []
    for e in merged:
        m = members[e["n"]]
        reasons = read_first_reasons(m, resolved_by_n.get(e["n"]))
        if reasons:
            read_first.append("- #%d %s: %s." % (m["n"], m["head_ref"], "; ".join(reasons).rstrip(".")))
    read_first_block = "\n".join(read_first) if read_first else "- none: every member is labeled, carries a trailer, touches no sensitive path, merged clean and had its own CI."

    rows = ["| # | Title | Tier | Rounds | Sweep at own head | Own CI | Flags | Ledger |",
            "|---|---|---|---|---|---|---|---|"]
    entries = inputs.get("entries") or []
    for e in merged:
        m = members[e["n"]]
        t = m.get("trailer") or {}
        flags = []
        if resolved_by_n.get(e["n"]):
            flags.append("resolved")
        if m.get("tier") is None:
            flags.append("unlabeled")
        flags += sensitive_paths(m.get("touches") or [])
        if m.get("trailer") is None:
            flags.append("no trailer")
        ledger_n = sum(1 for x in entries if e["n"] in x["members"])
        rows.append("| #%d | %s | %s | %s | %s | %s | %s | %s |" % (
            m["n"], _cell(m["title"]), _cell(m.get("tier") or "unlabeled"),
            _cell(t.get("rounds", "not stated")) if t else "not stated",
            _cell(sweep_cell(m.get("trailer"))), _cell(m.get("ci") or "unknown"),
            _cell(", ".join(flags) or "-"), ("+%d" % ledger_n) if ledger_n else "-"))
    members_table = "\n".join(rows)

    def entries_table(full):
        if not entries:
            return "(none)"
        if not full:
            return "(%d entries; table omitted to stay under the body cap; see `git diff %s...%s -- upstream/`)" % (len(entries), remote_main(), branch_of(name))
        out = ["| Entry | Title | Status | Change | Member |", "|---|---|---|---|---|"]
        for x in entries:
            out.append("| `%s` | %s | %s | %s | %s |" % (x["path"], _cell(x["title"]), _cell(x["status"]), x["change"],
                                                       ", ".join("#%d" % n for n in x["members"]) or "-"))
        return "\n".join(out)

    held_lines = []
    for h in held:
        if h.get("files"):
            held_lines.append("- #%d: conflicts with %s in %s; owner told." % (
                h["n"], ", ".join("#%d" % k for k in h.get("with") or []) or "the batch", ", ".join(h["files"])))
        else:
            held_lines.append("- #%d: %s." % (h["n"], h["reason"].rstrip(".")))
    for n in pulled:
        held_lines.append("- #%d: pulled; the PR stays open against %s." % (n, MAIN))
    held_block = "\n".join(held_lines) if held_lines else "- none"

    def resolutions_block(budget_lines):
        parts = []
        for r in inputs.get("resolutions") or []:
            lines = r["diff"].splitlines()
            cut = lines[:min(budget_lines, RESOLUTION_LINES)]
            more = len(lines) - len(cut)
            parts.append("### #%d\n\n```diff\n%s\n```%s" % (r["n"], "\n".join(cut), ("\n(%d more lines)" % more) if more > 0 else ""))
        return "\n\n".join(parts) if parts else "(none)"

    def log_block(budget_lines):
        lines = state["assembly"].get("log") or []
        cut = lines[-budget_lines:] if budget_lines else []
        more = len(lines) - len(cut)
        return ("(%d earlier lines omitted)\n" % more if more > 0 else "") + "\n".join(cut) if cut else "(omitted)"

    trailer = "<!-- romp-batch: %s -->" % json.dumps({
        "name": name, "base": state.get("base"),
        "members": [{"n": e["n"], "head": members[e["n"]]["head"]} for e in merged]}, separators=(",", ":"))

    def assemble(res_lines, log_lines, full_entries):
        return "\n".join([
            title, verified, "",
            "## Read these first", read_first_block, "",
            "## Members, in merge order", members_table, "",
            "## Upstream entries this batch adds or changes (%d)" % len(entries), entries_table(full_entries), "",
            "## Held back", held_block, "",
            "## To pull a member",
            "Comment `pull #N`. The batch is rebuilt without it; the PR stays open against %s." % MAIN, "",
            "<details><summary>Conflict resolutions</summary>\n\n%s\n\n</details>" % resolutions_block(res_lines),
            "<details><summary>Assembly log</summary>\n\n```\n%s\n```\n\n</details>" % log_block(log_lines),
            trailer, ""])

    res_lines, log_lines, full_entries = RESOLUTION_LINES, 10_000, True
    body = assemble(res_lines, log_lines, full_entries)
    while len(body) > cap and res_lines > 0:
        res_lines = max(0, res_lines - 50)
        body = assemble(res_lines, log_lines, full_entries)
    while len(body) > cap and log_lines > 0:
        log_lines = 0 if log_lines <= 20 else log_lines // 2 if log_lines < 10_000 else 40
        body = assemble(res_lines, log_lines, full_entries)
    if len(body) > cap and full_entries:
        full_entries = False
        body = assemble(res_lines, log_lines, full_entries)
    if len(body) > cap:
        raise Fail("the body is %d characters with every detail cut; GitHub caps it at %d. Split the batch (two a day beat one of twenty)."
                   % (len(body), cap))
    return body


def find_batch_pr(root, state):
    if state.get("pr") and state["pr"].get("number"):
        return state["pr"]["number"]
    rows = gh_json("pr", "list", "--state", "open", "--head", branch_of(state["name"]), "--json", "number,url", "--limit", "5", cwd=root)
    if rows:
        state["pr"] = {"number": rows[0]["number"], "url": rows[0].get("url")}
        return rows[0]["number"]
    return None


def cmd_summarize(args):
    root = repo_root()
    state = load_state(root, args.name)
    if not state["assembly"].get("head"):
        raise Fail("nothing assembled yet")
    body = render_body(state, gather_body_inputs(root, state))
    if args.print_only:
        print(body)
        return
    b = find_batch_pr(root, state)
    n_members = len(state["assembly"]["merged"])
    title = "Batch %s: %d PR%s" % (args.name, n_members, "" if n_members == 1 else "s")
    if b:
        _run([gh_bin(), "pr", "edit", str(b), "--title", title, "--body-file", "-"], cwd=root, input_text=body)
        print("updated batch PR #%d" % b)
    else:
        proc = _run([gh_bin(), "pr", "create", "--base", MAIN, "--head", branch_of(args.name), "--title", title,
                     "--label", LABEL_BATCH, "--body-file", "-"], cwd=root, input_text=body)
        url = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
        try:
            b = int(url.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            rows = gh_json("pr", "list", "--state", "open", "--head", branch_of(args.name), "--json", "number,url", "--limit", "5", cwd=root)
            if not rows:
                raise Fail("gh pr create printed no PR URL and the PR is not listed: %r" % url)
            b, url = rows[0]["number"], rows[0].get("url")
        state["pr"] = {"number": b, "url": url}
        print("opened batch PR #%d %s" % (b, url))
    head = state["assembly"]["head"]
    for e in state["assembly"]["merged"]:
        key = str(e["n"])
        if state["commented"].get(key) == head:
            continue
        gh("pr", "comment", key, "--body", "in batch %s at %s" % (args.name, head), cwd=root)
        state["commented"][key] = head
    save_state(root, state)


# ── pull, land, finish, bisect ───────────────────────────────────────────────

def push_batch(root, state, force):
    br = branch_of(state["name"])
    args = ["push", "--quiet", "-u", REMOTE, br]
    if force:
        args.insert(2, "--force-with-lease")
    git(*args, cwd=root)


def cmd_pull(args):
    root = repo_root()
    state = load_state(root, args.name)
    members = members_by_n(state)
    if args.n not in members:
        raise Fail("#%d is not a member of %s" % (args.n, args.name))
    before = set(state["pulled"])
    ns = argparse.Namespace(name=args.name, without=[args.n], resolve=[], repin=[], cont=False, abort=False,
                            reviewed=None, no_fetch=args.no_fetch, no_notify=args.no_notify)
    cmd_assemble(ns)
    state = load_state(root, args.name)
    dropped = sorted(set(state["pulled"]) - before - {args.n})
    if args.no_push:
        print("pulled #%d%s; not pushed (--no-push)" % (args.n, (", dropped with it: " + ", ".join("#%d" % d for d in dropped)) if dropped else ""))
        return
    push_batch(root, state, force=True)
    cmd_summarize(argparse.Namespace(name=args.name, print_only=False))
    state = load_state(root, args.name)
    reason = args.reason or "the maintainer asked"
    text = "Pulled from batch %s (%s). This PR stays open against %s and is not in that batch." % (args.name, reason, MAIN)
    if not args.no_notify:
        gh("pr", "comment", str(args.n), "--body", text, cwd=root, check=False)
        for d in dropped:
            gh("pr", "comment", str(d), "--body", "Dropped from batch %s with #%d, which it depends on. It stays open against %s."
               % (args.name, args.n, MAIN), cwd=root, check=False)
    print("pulled #%d%s; pushed and re-summarized" % (args.n, (", dropped with it: " + ", ".join("#%d" % d for d in dropped)) if dropped else ""))


def repo_settings(root):
    return gh_json("repo", "view", "--json", "mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge", cwd=root) or {}


def ruleset_exists(root):
    """Whether main has a ruleset. `gh pr merge --auto` is only useful (and only used here) when one
    exists: without required checks auto-merge merges at once. The decision to create one comes
    after the first batch has shown the check names; this detects, it never assumes."""
    proc = gh("api", "repos/{owner}/{repo}/rulesets", cwd=root, check=False)
    if proc.returncode != 0:
        return False
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return bool(rows)


def retarget_stacked_members(root, state):
    """A member based on another member's branch is retargeted to main right before the merge.

    GitHub marks a PR merged when its head becomes reachable from ITS BASE. The batch merges into
    main, so a member whose base is a sibling branch would stay open (its base never moves) even
    though its content is in main. Against main, the documented indirect-merge rule applies to it
    like every other member. Done here and not at plan time so the member keeps its stacked diff
    and review until the moment it lands."""
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    in_batch = {members[e["n"]]["head_ref"] for e in merged}
    for e in merged:
        m = members[e["n"]]
        if m["base_ref"] != MAIN and m["base_ref"] in in_batch:
            gh("pr", "edit", str(m["n"]), "--base", MAIN, cwd=root)
            log(state, "retargeted #%d from %s to %s before the merge, so the indirect merge marks it" % (m["n"], m["base_ref"], MAIN))
            m["base_ref"] = MAIN
            state["members"][str(m["n"])] = m
    save_state(root, state)


def cmd_land(args):
    root = repo_root()
    state = cmd_verify(argparse.Namespace(name=args.name, sweep=None, no_fetch=args.no_fetch), quiet=False)
    b = find_batch_pr(root, state)
    if not b:
        raise Fail("no open batch PR for %s; run summarize first" % branch_of(args.name))
    settings = repo_settings(root)
    if settings.get("mergeCommitAllowed") is False:
        raise Fail("the repository does not allow merge commits; a batch must land as one (repo settings)")
    for k in ("squashMergeAllowed", "rebaseMergeAllowed"):
        if settings.get(k):
            print("warning: %s is on; a squash or rebase of a batch leaves every member open" % k)
    head = state["verified"]["head"]
    remote_head = git("ls-remote", REMOTE, "refs/heads/" + branch_of(args.name), cwd=root).split()
    if not remote_head or remote_head[0] != head:
        raise Fail("%s on %s is at %s, verified %s; push the batch first" % (branch_of(args.name), REMOTE, short(remote_head[0]) if remote_head else "nothing", short(head)))
    retarget_stacked_members(root, state)
    cmd = ["pr", "merge", str(b), "--merge", "--match-head-commit", head]
    if args.auto:
        if not ruleset_exists(root):
            raise Fail("--auto needs a ruleset on %s (none found); merge without --auto" % MAIN)
        cmd.append("--auto")
    gh(*cmd, cwd=root)
    poll = float(os.environ.get("ROMP_BATCH_POLL", "3"))
    for _ in range(20):
        pr = gh_json("pr", "view", str(b), "--json", "state,mergeCommit", cwd=root)
        if pr.get("state") == "MERGED":
            break
        if args.auto:
            print("auto-merge armed on #%d; run `scripts/batch.py finish %s` once it lands" % (b, args.name))
            save_state(root, state)
            return
        time.sleep(poll)
    else:
        raise Fail("#%d did not read MERGED after the merge call; check it, then run finish" % b)
    state["landed"] = {"pr": b, "merge": (pr.get("mergeCommit") or {}).get("oid"), "at": now()}
    save_state(root, state)
    print("merged batch PR #%d" % b)
    cmd_finish(argparse.Namespace(name=args.name, no_fetch=False, no_notify=args.no_notify, keep_worktree=False))


def cmd_finish(args):
    root = repo_root()
    state = load_state(root, args.name)
    fetch(root, args.no_fetch)
    b = find_batch_pr(root, state)
    if not b:
        raise Fail("no batch PR recorded for %s" % args.name)
    bpr = gh_json("pr", "view", str(b), "--json", "state,mergeCommit,url", cwd=root)
    if bpr.get("state") != "MERGED":
        raise Fail("batch PR #%d is %s, not MERGED; finish runs after the merge" % (b, bpr.get("state")))
    merge_sha = (bpr.get("mergeCommit") or {}).get("oid")
    if merge_sha and not is_ancestor(merge_sha, remote_main(), root):
        raise Fail("batch PR #%d's merge commit %s is not an ancestor of %s; was it squashed or rebased?" % (b, short(merge_sha), remote_main()))
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    member_refs = {members[e["n"]]["head_ref"] for e in merged} | {branch_of(args.name)}
    report = {"merged": [], "open": [], "retargeted": [], "deleted": [], "already_gone": [], "observations": []}
    for e in merged:
        m = members[e["n"]]
        pr = gh_json("pr", "view", str(m["n"]), "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
        was_stacked = pr.get("baseRefName") in member_refs
        if pr.get("state") == "OPEN" and was_stacked:
            # The maintainer merged by hand, so land's retarget did not run: a member still based on
            # a sibling branch cannot have been marked merged. Retarget now and look again; whether
            # GitHub marks it merged on the retarget is to verify on the first batch, so the outcome
            # is recorded either way.
            gh("pr", "edit", str(m["n"]), "--base", MAIN, cwd=root)
            pr = gh_json("pr", "view", str(m["n"]), "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
            report["observations"].append("#%d was still based on a member branch; retargeted to %s, now %s" % (m["n"], MAIN, pr.get("state")))
        if pr.get("state") == "MERGED":
            report["merged"].append(m["n"])
            continue
        report["open"].append(m["n"])
        moved = pr.get("headRefOid") != m["head"]
        if moved:
            why = "its head moved to %s after the cut at %s, so the batch carried the old head" % (short(pr.get("headRefOid")), short(m["head"]))
            todo = "Merge origin/%s, push, and it goes into the next batch." % MAIN
        elif was_stacked:
            why = "it was based on another PR's branch, and GitHub marks a PR merged only when its base reaches its head"
            todo = "It is retargeted to %s now; its content is already there, so close it if it does not read merged by itself." % MAIN
        else:
            why = "GitHub did not mark it merged although the batch carried its head %s" % short(m["head"])
            todo = "Its content is in %s; close it if it does not read merged by itself." % MAIN
        text = "This PR was in batch %s but is not marked merged: %s. %s" % (args.name, why, todo)
        if not args.no_notify:
            gh("pr", "comment", str(m["n"]), "--body", text, cwd=root, check=False)
        if not moved:
            report["observations"].append("#%d: indirect-merge marking did not fire (head %s is in %s)" % (m["n"], short(m["head"]), MAIN))
    # Retarget still-open PRs based on a member branch or the batch branch BEFORE deleting anything:
    # GitHub retargets dependents itself when it deletes a head branch on merge, but whether that
    # happens for an indirectly merged PR's branch (and after an explicit delete) is to verify on
    # the first batch, so the tool does it explicitly.
    open_prs = gh_json("pr", "list", "--state", "open", "--limit", str(PR_LIST_LIMIT), "--json", "number,baseRefName,headRefName", cwd=root) or []
    for pr in open_prs:
        if pr["baseRefName"] in member_refs:
            gh("pr", "edit", str(pr["number"]), "--base", MAIN, cwd=root)
            report["retargeted"].append(pr["number"])
    remote_branches = set(git("ls-remote", "--heads", REMOTE, cwd=root).replace("refs/heads/", "").split()[1::2])
    for n in report["merged"]:
        ref = members[n]["head_ref"]
        if ref in remote_branches:
            git("push", "--quiet", REMOTE, "--delete", ref, cwd=root)
            report["deleted"].append(ref)
        else:
            report["already_gone"].append(ref)
    if report["already_gone"]:
        report["observations"].append("GitHub deleted the head branch of indirectly merged PR(s): %s" % ", ".join(report["already_gone"]))
    if report["deleted"]:
        report["observations"].append("finish deleted head branches GitHub left: %s" % ", ".join(report["deleted"]))
    if branch_of(args.name) in remote_branches:
        git("push", "--quiet", REMOTE, "--delete", branch_of(args.name), cwd=root)
    for n in report["retargeted"]:
        pr = gh_json("pr", "view", str(n), "--json", "baseRefName,state", cwd=root)
        if pr.get("baseRefName") != MAIN or pr.get("state") != "OPEN":
            report["observations"].append("#%d after retarget and base deletion: base %s, state %s" % (n, pr.get("baseRefName"), pr.get("state")))
    wt = worktree_dir(root, args.name)
    if not args.keep_worktree and os.path.isdir(wt):
        git("worktree", "remove", "--force", wt, cwd=root)
    if git_ok("rev-parse", "--verify", "--quiet", branch_of(args.name), cwd=root) and not args.keep_worktree:
        git("branch", "-D", branch_of(args.name), cwd=root)
    orphans = _run([os.path.join(root, "scripts", "pr-orphans.sh")], cwd=root, check=False)
    report["orphans"] = {"exit": orphans.returncode, "out": (orphans.stdout + orphans.stderr).strip()}
    run_url = "none yet"
    runs = gh("run", "list", "--branch", MAIN, "--limit", "1", "--json", "url", cwd=root, check=False)
    if runs.returncode == 0:
        try:
            rows = json.loads(runs.stdout or "[]")
            if rows:
                run_url = rows[0].get("url") or run_url
        except json.JSONDecodeError:
            pass
    state["finished"] = {"at": now(), "report": report}
    save_state(root, state)
    print("batch #%d landed, %d member(s) marked merged, %s CI run: %s" % (b, len(report["merged"]), MAIN, run_url))
    if report["open"]:
        print("STILL OPEN (told on the PR): %s" % ", ".join("#%d" % n for n in report["open"]))
    if report["retargeted"]:
        print("retargeted to %s: %s" % (MAIN, ", ".join("#%d" % n for n in report["retargeted"])))
    for o in report["observations"]:
        print("observed: %s" % o)
    if report["orphans"]["exit"] != 0:
        print("pr-orphans.sh: exit %d\n%s" % (report["orphans"]["exit"], report["orphans"]["out"]))
    else:
        print("pr-orphans.sh: clean")
    if report["merged"]:
        print("postal (kind: coordinate) to the owners of %s: batch %s merged; remove your worktree and local branch (%s); the remote branch is gone."
              % (", ".join("#%d" % n for n in report["merged"]), args.name, ", ".join(members[n]["head_ref"] for n in report["merged"])))


def cmd_bisect(args):
    root = repo_root()
    state = load_state(root, args.name)
    wt = worktree_dir(root, args.name)
    if not os.path.isdir(wt):
        raise Fail("no batch worktree at %s" % wt)
    if not args.cmd:
        raise Fail("bisect needs a command after --, e.g. `-- pytest tests/test_x.py -q`", code=2)
    tip = git("rev-parse", branch_of(args.name), cwd=wt)
    base = git("merge-base", remote_main(), tip, cwd=wt)
    git("bisect", "start", "--first-parent", tip, base, cwd=wt)
    try:
        proc = _run(["git", "bisect", "run", *args.cmd], cwd=wt, check=False)
        m = _FIRST_BAD.search(proc.stdout + proc.stderr)
        if not m:
            raise Fail("bisect did not name a first bad commit:\n%s" % (proc.stdout + proc.stderr)[-2000:])
        bad = m.group(1)
    finally:
        git("bisect", "reset", cwd=wt, check=False)
    members = members_by_n(state)
    hit = next((e for e in state["assembly"].get("merged", []) if e["merge"] == bad), None)
    if hit:
        print("first bad: #%d %s (merge %s); pull it and say why in the body" % (hit["n"], members[hit["n"]]["title"], short(bad)))
    else:
        print("first bad: %s (%s), not a member merge" % (short(bad), subject_of(bad, wt)))


# ── entry point ──────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(prog="scripts/batch.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="subcommand", required=True)

    p = sub.add_parser("plan", help="pick and order the members, predict conflicts, write the plan")
    p.add_argument("--labeled", action="store_true", help="only PRs labeled `%s`" % LABEL_LAND)
    p.add_argument("--name", help="batch name (default: today's date plus the first free letter)")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("assemble", help="merge the pinned heads into ../romp-batch-<name>")
    p.add_argument("name")
    p.add_argument("--without", type=int, action="append", metavar="N", help="leave N (and its dependents) out")
    p.add_argument("--resolve", type=int, action="append", metavar="N", help="stop at N's conflict for a hand resolution")
    p.add_argument("--repin", action="append", metavar="N|all", help="re-read N's head from GitHub before assembling")
    p.add_argument("--continue", dest="cont", action="store_true", help="commit the resolved merge and go on")
    p.add_argument("--abort", action="store_true", help="abandon the stopped resolution; hold that member back")
    p.add_argument("--reviewed", metavar="NOTE", help="with --continue: who reviewed the resolution and the verdict")
    p.add_argument("--no-notify", action="store_true", help="do not comment on held-back PRs")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("verify", help="provenance, pinned heads, bases, ledger, sweep, own CI")
    p.add_argument("name")
    p.add_argument("--sweep", metavar="TEXT", help="record the full sweep's counts at the current batch head")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("summarize", help="create or update the batch PR; comment on each member")
    p.add_argument("name")
    p.add_argument("--print-only", action="store_true", help="print the body; touch nothing")
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("pull", help="rebuild without N and its dependents, push, re-summarize")
    p.add_argument("name")
    p.add_argument("n", type=int)
    p.add_argument("--reason")
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--no-notify", action="store_true")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("land", help="verify, merge the batch PR with a merge commit, finish")
    p.add_argument("name")
    p.add_argument("--auto", action="store_true", help="arm auto-merge instead (needs a ruleset on %s)" % MAIN)
    p.add_argument("--no-notify", action="store_true")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_land)

    p = sub.add_parser("finish", help="after the merge: member states, retargets, branch deletion, orphans")
    p.add_argument("name")
    p.add_argument("--no-notify", action="store_true")
    p.add_argument("--keep-worktree", action="store_true")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(func=cmd_finish)

    p = sub.add_parser("bisect", help="first-parent bisect over the batch chain; names the member")
    p.add_argument("name")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- <command that fails on the bad tree>")
    p.set_defaults(func=cmd_bisect)

    args = ap.parse_args(argv)
    if args.subcommand == "bisect" and args.cmd[:1] == ["--"]:
        args.cmd = args.cmd[1:]
    try:
        args.func(args)
    except Fail as e:
        print("batch: %s" % e, file=sys.stderr)
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
