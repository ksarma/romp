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
  assemble   <name> [--without N] [--resolve N] [--repin N|all] [--continue|--abort] [--merge-main]
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
  - plan orders dependents after their bases and excludes drafts, `major-feature` and `hold`; a
    `Depends-on` cycle excludes its members (and their dependents), not the plan;
  - assemble refuses when any other `batch/*` ref exists on origin;
  - provenance fails on an undeclared commit and passes on a `batch:` commit;
  - every merge on the chain (a member's or origin/main's) equals the clean merge of its parents,
    or carries a recorded resolution and then differs from it only in the resolution's files, which
    cover every path merge-tree calls conflicted and hold no conflict marker (nor does --continue
    ever commit one); a stop lists the files rerere replayed along with the ones still unmerged;
  - a resolution that took one side wholesale says so, in the digest line and above its diff, which
    runs from the clean merge of the parents to the merge;
  - verify fails when a pinned head moved, and when an assembly did not finish; so does finish;
  - pull N drops N's dependents, unless N already merged into main;
  - the body stays under GitHub's 65,536-character cap, the members table never cut and the
    details fitted to the budget (entries table, then resolutions, then the log).
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

# `Depends-on:` is read from the body's first lines only (docs/batching.md asks for it there), outside
# fenced code blocks, one line per dependency or a `#N, #M` list on one line.
DEPENDS_ON_LINES = 20
_DEPENDS_ON = re.compile(r"^\s*Depends-on:\s*(.*)$", re.IGNORECASE)
_FENCE = re.compile(r"^\s*(```|~~~)")
_PR_TRAILER = re.compile(r"<!--\s*romp-pr:\s*(\{.*?\})\s*-->", re.DOTALL)
_BATCH_TRAILER = re.compile(r"<!--\s*romp-batch:\s*(\{.*?\})\s*-->", re.DOTALL)
_FIRST_BAD = re.compile(r"^([0-9a-f]{40}) is the first '?bad'? commit", re.MULTILINE)  # git 2.43 says bad; 2.4x+ says 'bad'
# A conflict marker line in a file's content. `=======` alone is not one: a Markdown heading underline
# is a legitimate line of exactly that; the `<<<<<<<`, `|||||||` and `>>>>>>>` lines are not.
_CONFLICT_MARKER = re.compile(r"^(?:<{7}|>{7}|\|{7})(?: |$)", re.MULTILINE)


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


def parse_depends_on(body):
    """The PR numbers a body declares with `Depends-on:` in its first DEPENDS_ON_LINES lines, outside
    fenced code blocks; `#N` tokens, or a bare number list. Sorted, without duplicates."""
    out, fence, seen = set(), None, 0
    for line in (body or "").splitlines():
        f = _FENCE.match(line)
        if f:
            if fence is None:
                fence = f.group(1)
            elif f.group(1) == fence:
                fence = None
            continue
        if fence:
            continue
        seen += 1
        if seen > DEPENDS_ON_LINES:
            break
        m = _DEPENDS_ON.match(line)
        if not m:
            continue
        rest = m.group(1)
        nums = re.findall(r"#(\d+)", rest)
        if not nums and re.fullmatch(r"[\d,\s]+", rest.strip() or "x"):
            nums = re.findall(r"\d+", rest)
        out.update(int(x) for x in nums)
    return sorted(out)


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
    """(number, head sha at the merge) of the latest MERGED PR whose head was `branch`, or (None,
    None). A PR based on such a branch is the stranded case (2026-09-06: four PRs merged into
    already-merged bases), so it is refused, but by SHA and not by name alone: the fork reuses branch
    names, and a live branch that has moved on from the merged head is not that PR's."""
    rows = gh_json("pr", "list", "--state", "merged", "--head", branch, "--json", "number,headRefOid", "--limit", "5", cwd=root)
    return (rows[0]["number"], rows[0].get("headRefOid")) if rows else (None, None)


def dependency_status(root, d):
    """A declared dependency that is not an open PR: "satisfied" when it merged into main (its content
    is in the base every batch starts from), else why it cannot be satisfied."""
    proc = gh("pr", "view", str(d), "--json", "state,mergeCommit,headRefOid", cwd=root, check=False)
    if proc.returncode != 0:
        return "not a PR"
    try:
        pr = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return "not a PR"
    if pr.get("state") != "MERGED":
        return "%s, not merged" % (pr.get("state") or "unknown").lower()
    merge = (pr.get("mergeCommit") or {}).get("oid")
    for sha in (merge, pr.get("headRefOid")):
        if sha and git_ok("cat-file", "-e", sha + "^{commit}", cwd=root) and is_ancestor(sha, remote_main(), root):
            return "satisfied"
    return "merged, but not into %s" % MAIN


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
    """Dependencies first, then by number (Kahn's algorithm with a number-ordered frontier). Returns
    (order, stuck): `stuck` are the candidates a dependency cycle keeps out of the order, the cycle's
    own members and everything that depends on them; the caller excludes them with the cycle named
    and plans the rest."""
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
    return order, sorted(set(cands) - set(order))


def reaches(cands, a, b):
    """Whether a's `Depends-on` chain among the candidates reaches b (a == b: a is in a cycle)."""
    seen, frontier = set(), [d for d in cands[a]["depends_on"] if d in cands]
    while frontier:
        d = frontier.pop()
        if d == b:
            return True
        if d in seen:
            continue
        seen.add(d)
        frontier.extend(x for x in cands[d]["depends_on"] if x in cands)
    return False


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
    if os.path.exists(state_path(root, name)) and not args.force:
        old = load_state(root, name)
        if old.get("assembly", {}).get("head"):
            raise Fail("%s is already assembled (pulled: %s); re-planning would forget that. Use a new --name, or --force."
                       % (name, ", ".join("#%d" % n for n in old.get("pulled", [])) or "none"), code=2)
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
                "depends_on": parse_depends_on(pr.get("body")),
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
        merged, merged_head = merged_pr_for_branch(root, b)
        live = git("rev-parse", "--verify", "--quiet", "%s/%s" % (REMOTE, b), cwd=root, check=False) or None
        if merged and (live is None or live == merged_head or is_ancestor(live, base_sha, root)):
            excluded[n] = "base %s belongs to merged PR #%d; run `gh pr edit %d --base %s`" % (b, merged, n, MAIN)
        elif merged:
            excluded[n] = "base %s was merged PR #%d's branch and now holds other commits with no open PR" % (b, merged)
        else:
            excluded[n] = "base %s is neither %s nor a candidate's branch" % (b, MAIN)
        del cands[n]
    # A dependency that is not a candidate takes its dependents out too (failure mode 7), unless it
    # already merged into main: then it is satisfied by the base every batch starts from, and the
    # dependent stays (docs tell authors to leave `Depends-on` in the body; it must not strand them).
    satisfied = {}

    def drop_dependents_of_excluded():
        changed = True
        while changed:
            changed = False
            for n, m in list(cands.items()):
                for d in list(m["depends_on"]):
                    if d in cands:
                        continue
                    if d not in excluded:
                        status = satisfied.get(d) or dependency_status(root, d)
                        satisfied[d] = status
                        if status == "satisfied":
                            m["depends_on"].remove(d)
                            m.setdefault("depends_on_merged", []).append(d)
                            continue
                    why = excluded.get(d) or satisfied.get(d) or "not an open PR"
                    excluded[n] = "depends on #%d (%s)" % (d, why)
                    del cands[n]
                    changed = True
                    break

    drop_dependents_of_excluded()
    for n, m in cands.items():
        ensure_object(root, m["head"], m["head_ref"])
        mb = git("merge-base", base_sha, m["head"], cwd=root)
        m["touches"] = git("diff", "--name-only", mb, m["head"], cwd=root).split()
    ordered, stuck = order_members(cands)
    if stuck:
        # A `Depends-on` cycle (a PR naming itself, two naming each other) is that PR's mistake, not
        # the batch's: its members are excluded with the cycle named, their dependents with them
        # (through the fixpoint above), and the rest is planned.
        cyclic = [n for n in stuck if reaches(cands, n, n)]
        partners = {n: [k for k in cyclic if k != n and reaches(cands, n, k) and reaches(cands, k, n)] for n in cyclic}
        for n in cyclic:
            excluded[n] = ("in a dependency cycle with %s" % ", ".join("#%d" % k for k in partners[n])) if partners[n] \
                else "depends on itself (Depends-on: #%d)" % n
            del cands[n]
        drop_dependents_of_excluded()
        ordered, stuck = order_members(cands)
        if stuck:
            raise Fail("dependency cycle among PRs %s" % ", ".join("#%d" % n for n in stuck))
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
        git("worktree", "prune", cwd=root)    # a directory removed by hand leaves a registration that blocks -B
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


def staged_paths(wt, paths):
    """Among `paths`, those the index holds at stage 0: staged whole, neither unmerged nor absent."""
    if not paths:
        return []
    out = []
    for entry in _run(["git", "ls-files", "--stage", "-z", "--", *paths], cwd=wt).stdout.split("\0"):
        meta, _, path = entry.partition("\t")
        if path and meta.split()[2] == "0":
            out.append(path)
    return out


def replayed_paths(wt, conflicted, still):
    """The conflicted paths rerere replayed and staged: conflicted, not unmerged, and in the index at
    stage 0. The last condition is not implied by the first two: for a distinct-types conflict (a file
    on one side, a symlink on the other) merge-tree names the aside copy after the SHA it was given
    (`notes.txt~<sha>`) while `git merge` names it `notes.txt~HEAD`, so the merge-tree path is
    conflicted and not unmerged and exists nowhere; without the index check a first assembly said
    rerere had replayed it."""
    return sorted(staged_paths(wt, sorted(set(conflicted) - set(still))))


def resolution_diff(cwd, merge, paths):
    """The resolution as a diff: from the merge-tree of the merge's parents (conflict markers left in
    the conflicted files) to the merge, over `paths`. That shows the conflict text turning into the
    chosen text; a combined diff (`git show --cc`) omits every hunk equal to one parent, so a side
    taken wholesale rendered as nothing. None when this git cannot compute the merge-tree."""
    ps = parents_of(merge, cwd)
    if len(ps) != 2:
        return None
    mt, _, _ = merge_tree_of(ps[0], ps[1], cwd)
    if mt is None:
        return None
    return _run(["git", "diff", "--no-color", mt, merge + "^{tree}", "--", *paths], cwd=cwd, check=False).stdout


def resolution_hunks(cwd, merge, paths):
    out = resolution_diff(cwd, merge, paths)
    return None if out is None else sum(1 for l in out.splitlines() if l.startswith("@@"))


def blob_of(rev, path, cwd):
    return git("rev-parse", "--verify", "--quiet", "%s:%s" % (rev, path), cwd=cwd, check=False) or None


def resolution_choices(cwd, merge, paths, label1, label2):
    """Per path, what the resolution chose when it equals one parent's version: {path: phrase}. label1
    names the merge's first parent (the batch), label2 the second (a member, or origin/main). A path
    combined by hand, or one both parents agree on, has no entry."""
    ps = parents_of(merge, cwd)
    if len(ps) != 2:
        return {}
    out = {}
    for p in paths:
        b, b1, b2 = (blob_of(x, p, cwd) for x in (merge, ps[0], ps[1]))
        if b1 == b2:
            continue
        if b == b2:
            out[p] = ("deleted the file, as %s did" % label2) if b2 is None else \
                "took %s's version" % label2 + (", which %s deleted" % label1 if b1 is None else "")
        elif b == b1:
            out[p] = ("kept the file deleted, as %s had it" % label1) if b1 is None else \
                "kept %s's version" % label1 + (", which %s deleted" % label2 if b2 is None else "")
    return out


def marker_paths(tree, paths, cwd):
    """The paths among `paths` whose blob in `tree` (a tree or commit) holds a conflict marker line."""
    out = []
    for p in paths:
        proc = subprocess.run(["git", "cat-file", "-p", "%s:%s" % (tree, p)], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0 and _CONFLICT_MARKER.search(proc.stdout.decode("utf-8", "replace")):
            out.append(p)
    return out


def hold_back(root, state, m, reason, files=None, against=None, with_members=None, notify=True):
    """Record a member held back and, for a conflict, tell its owner once per distinct reason.
    `against` is what the member conflicts with, in the owner's terms: "origin/main", "#101, #102"
    or "the batch". Whether the owner was told is RECORDED (`told`), never assumed: a failed
    `gh pr comment` is logged, printed for a postal message, and retried on the next rebuild."""
    entry = {"n": m["n"], "reason": reason, "files": files or [], "with": with_members or [], "told": None}
    state["assembly"].setdefault("held", []).append(entry)
    log(state, "#%d held back: %s" % (m["n"], reason))
    if files is None:
        return
    text = ("This PR conflicts with %s in %s, so this batch goes ahead without it. "
            "Merge origin/%s%s into yours, push, and comment here; the next batch includes it."
            % (against or "the batch", ", ".join(files), MAIN, " (or that PR's branch)" if with_members else ""))
    told = state.setdefault("held_notified", {})
    if not notify:
        entry["told"], entry["told_why"] = False, "--no-notify"
    elif told.get(str(m["n"])) == text:
        # Once per distinct reason: a rebuild after `pull` meets the same conflict again, and the
        # owner does not need the same comment twice.
        entry["told"], entry["told_why"] = True, "in an earlier assembly"
    else:
        proc = gh("pr", "comment", str(m["n"]), "--body", text, cwd=root, check=False)
        if proc.returncode == 0:
            told[str(m["n"])] = text
            entry["told"] = True
        else:
            err = [l for l in (proc.stderr or proc.stdout).strip().splitlines() if l.strip()]
            entry["told"], entry["told_why"] = False, "comment failed: %s" % (err[-1] if err else "exit %d" % proc.returncode)
            log(state, "#%d: gh pr comment failed (%s); the owner is NOT told, send the postal message below" % (m["n"], entry["told_why"]))
    print("postal (kind: coordinate) to the owner of #%d: %s" % (m["n"], text))


def conflict_attribution(root, state, m, files):
    """What a held-back member conflicts with, in the owner's terms: (text, earlier member numbers).
    A member that conflicts with origin/main by itself is told so (merging main fixes it); otherwise
    the earlier members whose own diff touches the conflicted files are named; failing both, "the
    batch"."""
    _, kind, _ = merge_tree_of(state["base"], m["head"], root)
    if kind == "conflicts":
        return remote_main(), []
    members = members_by_n(state)
    earlier = [e["n"] for e in state["assembly"]["merged"] if set(members[e["n"]]["touches"]) & set(files)]
    return (", ".join("#%d" % k for k in earlier) or "the batch"), earlier


def prior_resolution(state, key, files):
    """The resolution an earlier assembly of this batch recorded under `key` (a member number as a
    string, or "main") for the same files, so a rerere replay of the same conflict keeps its review."""
    rec = (state["assembly"].get("previous_resolutions") or {}).get(key)
    if rec and sorted(rec.get("files") or []) == sorted(files):
        return rec
    return None


def commit_resolution(wt, files):
    """Commit the staged result of a conflicted merge once no conflict marker is staged and it passes
    the subset rule: the result may differ from the merge git makes of the two parents by itself ONLY
    in the conflicted files (plus upstream/ entries for a row conversion). Anything else staged would
    land inside the merge commit unseen; the refusal names the paths and the tree that holds the
    merge's own content for them. The marker scan reads the conflicted files and every path that
    differs from that tree: a conflicted file left as merge-tree wrote it does not differ from it.
    The parents are named by SHA, as verify names them, so the two merge-trees are the same object
    (the identifiers label the markers). Returns (sha, paths that differ from the clean merge)."""
    index_tree = git("write-tree", cwd=wt)
    mt, kind, _ = merge_tree_of(git("rev-parse", "HEAD", cwd=wt), git("rev-parse", "MERGE_HEAD", cwd=wt), wt)
    if mt is None:
        raise Fail("this git cannot compare the resolution with the clean merge of its parents (needs git 2.38); the merge is not committed")
    paths = git("diff-tree", "--name-only", "-r", mt, index_tree, cwd=wt).split()
    marked = marker_paths(index_tree, sorted(set(paths) | set(files)), wt)
    if marked:
        raise Fail("a conflict marker is still staged in %s; resolve it, `git add` the file, then run --continue again" % ", ".join(marked))
    stray = stray_resolution_paths(files, paths)
    if stray:
        raise Fail("the staged merge also changes %s, outside the conflicted files (%s). A resolution may change only "
                   "the files that conflicted: restore the others to the merge's own content with "
                   "`git restore --source=%s --staged --worktree -- %s`, or move that change into a separate `batch:` "
                   "commit after the merge; then run --continue again."
                   % (", ".join(stray), ", ".join(files), mt, " ".join(stray)))
    git("commit", "--quiet", "--no-edit", cwd=wt)
    return git("rev-parse", "HEAD", cwd=wt), paths


def base_branch_verdict(root, state, m):
    """What a member's non-main base is, compared by SHA and not by name alone (the fork reuses
    branch names). ("member", k): another member's branch, a dependency the order handles.
    ("merged", k): merged PR #k's branch, deleted or still at the merged head: the stranded case.
    ("reused", k): merged PR #k's branch name, now holding other commits that no member carries.
    ("unknown", None): neither main, nor a member's branch, nor a merged PR's."""
    b = m["base_ref"]
    for k, mm in members_by_n(state).items():
        if k != m["n"] and mm["head_ref"] == b:
            return "member", k
    merged_n, merged_head = merged_pr_for_branch(root, b)
    live = git("rev-parse", "--verify", "--quiet", "%s/%s" % (REMOTE, b), cwd=root, check=False) or None
    if merged_n:
        if live is None or live == merged_head or is_ancestor(live, remote_main(), root):
            return "merged", merged_n
        return "reused", merged_n
    return "unknown", None


def merge_member(root, wt, state, m, resolve_set):
    """One member merge. Returns 'merged', 'contained' (its head was already in the batch, so no
    merge commit of its own), 'held', or 'stopped' (waiting for --continue)."""
    n = m["n"]
    if m["base_ref"] != MAIN:
        what, k = base_branch_verdict(root, state, m)
        if what == "merged":
            hold_back(root, state, m, "base %s belongs to merged PR #%d; retarget it to %s (`gh pr edit %d --base %s`)" % (m["base_ref"], k, MAIN, n, MAIN))
            return "held"
        if what == "reused":
            hold_back(root, state, m, "base %s was merged PR #%d's branch and now holds other commits that no member carries; "
                                      "make its PR a member or retarget #%d to %s" % (m["base_ref"], k, n, MAIN))
            return "held"
        if what == "unknown":
            hold_back(root, state, m, "base %s is neither %s nor a member's branch" % (m["base_ref"], MAIN))
            return "held"
    ensure_object(root, m["head"], m["head_ref"])
    before = git("rev-parse", "HEAD", cwd=wt)
    if is_ancestor(m["head"], before, wt):
        # `git merge` would say "Already up to date" and make no commit; recording HEAD as this
        # member's merge would be a bogus record (verify then fails on the count with no cause).
        members = members_by_n(state)
        by = next(("#%d" % e["n"] for e in state["assembly"]["merged"] if is_ancestor(m["head"], members[e["n"]]["head"], wt)), remote_main())
        state["assembly"].setdefault("contained", []).append({"n": n, "contained_by": by})
        log(state, "#%d is already contained by %s (its head %s is in the batch); no merge of its own%s"
            % (n, by, short(m["head"]), "; add Depends-on or reorder" if by != remote_main() else ""))
        return "contained"
    msg = "Merge #%d: %s" % (n, m["title"])
    env = dict(os.environ, GIT_MERGE_AUTOEDIT="no")
    proc = subprocess.run(["git", "merge", "--no-ff", "--no-edit", "-m", msg, m["head"]], cwd=wt, env=env,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode == 0:
        sha = git("rev-parse", "HEAD", cwd=wt)
        if sha == before or parents_of(sha, wt) != [before, m["head"]]:
            raise Fail("git merge of #%d made no merge commit of %s onto %s:\n%s%s" % (n, short(m["head"]), short(before), proc.stdout, proc.stderr))
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": None})
        log(state, "merged #%d at %s -> %s" % (n, short(m["head"]), short(sha)))
        return "merged"
    if not merge_in_progress(wt):
        raise Fail("git merge of #%d failed without a conflict to resolve:\n%s%s" % (n, proc.stdout, proc.stderr))
    # The files that conflicted are what git would conflict on by itself (merge-tree, plumbing) plus
    # what is unmerged in the index; those of the difference that the index holds at stage 0 are what
    # rerere replayed and staged (replayed_paths says why the index check is needed). A stop lists
    # ALL of them: a replayed file left off the cursor read as a stray change at --continue, and the
    # restore that refusal advised wrote the conflicted tree's markers into it.
    still = unmerged_paths(wt)
    _, _, would = merge_tree_of(before, m["head"], wt)
    conflicted = sorted(set(still) | set(would or []))
    replayed = replayed_paths(wt, conflicted, still)
    resolved = None
    if not still and merge_in_progress(wt):
        # rerere replayed a recorded resolution and staged the result (rerere.autoUpdate). The review
        # of the earlier assembly's resolution carries over when it is the same conflict (same member,
        # same files): the replayed hunks are that resolution.
        prior = prior_resolution(state, str(n), conflicted)
        resolved = {"files": conflicted, "hunks": None, "replayed": True,
                    "how": "rerere replayed the resolution recorded in the earlier assembly" if prior else "rerere replayed a recorded resolution",
                    "review": prior["review"] if prior else None}
    elif UPSTREAM_MD in still:
        rows = convert_ledger_rows(root, wt, state, m)
        if rows is not None:
            still = unmerged_paths(wt)
            if not still:
                how, review = "%d UPSTREAM.md row(s) converted to entries (mechanical)" % rows, "mechanical"
                if replayed:
                    prior = prior_resolution(state, str(n), replayed)
                    how += "; rerere replayed the earlier assembly's resolution in %s" % ", ".join(replayed)
                    review = prior["review"] if prior else None
                resolved = {"files": conflicted, "how": how, "hunks": None, "review": review}
                if replayed:
                    resolved["replayed_files"] = replayed
    if resolved is not None and not unmerged_paths(wt):
        sha, _ = commit_resolution(wt, resolved["files"])
        resolved["hunks"] = resolution_hunks(wt, sha, resolved["files"])
        resolved["choices"] = resolution_choices(wt, sha, resolved["files"], "the batch", "#%d" % n)
        state["assembly"]["merged"].append({"n": n, "merge": sha, "resolved": resolved})
        log(state, "merged #%d -> %s with %s" % (n, short(sha), resolved["how"]))
        return "merged"
    files = conflicted
    if n in resolve_set:
        state["assembly"]["cursor"] = {"n": n, "files": files, "replayed": replayed}
        log(state, "#%d stopped for resolution in %s%s; resolve per hunk in %s, `git add` the files, then "
                   "`scripts/batch.py assemble %s --continue [--reviewed '<note>']`"
            % (n, ", ".join(files),
               (" (rerere replayed %s from the earlier assembly and staged it; the review covers the whole resolution)" % ", ".join(replayed)) if replayed else "",
               wt, state["name"]))
        return "stopped"
    git("merge", "--abort", cwd=wt)
    against, earlier = conflict_attribution(root, state, m, files)
    hold_back(root, state, m, "conflicts with %s in %s" % (against, ", ".join(files)),
              files=files, against=against, with_members=earlier, notify=not state["assembly"].get("no_notify"))
    return "held"


def continue_after_resolution(root, wt, state, reviewed):
    """Commit the merge a --resolve (or --merge-main) stop left in the worktree. Returns True when it
    was the merge of origin/main (no members follow it), False for a member."""
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to continue: no member is stopped for resolution")
    if not merge_in_progress(wt):
        raise Fail("no merge is in progress in %s; run assemble again without --continue" % wt)
    is_main = cur.get("main") is not None
    if is_main:
        expected, label = cur["main"], "the merge of %s" % remote_main()
    else:
        m = members_by_n(state)[cur["n"]]
        expected, label = m["head"], "#%d" % m["n"]
    if git("rev-parse", "MERGE_HEAD", cwd=wt) != expected:
        raise Fail("MERGE_HEAD in %s is not %s's pinned head" % (wt, label))
    still = unmerged_paths(wt)
    if still:
        raise Fail("still unmerged: %s (resolve and `git add` them first)" % ", ".join(still))
    files, replayed = cur["files"], cur.get("replayed") or []
    sha, _ = commit_resolution(wt, files)
    how = "resolved by the batcher, per hunk"
    if replayed:
        how += "; rerere replayed the earlier assembly's resolution in %s" % ", ".join(replayed)
    resolved = {"files": files, "how": how, "hunks": resolution_hunks(wt, sha, files), "review": reviewed,
                "choices": resolution_choices(wt, sha, files, "the batch", remote_main() if is_main else "#%d" % cur["n"])}
    if replayed:
        resolved["replayed_files"] = replayed
    if is_main:
        state["assembly"].setdefault("main_merges", []).append({"merge": sha, "main": cur["main"], "resolved": resolved})
        state["assembly"]["head"] = sha
        state["verified"] = None
    else:
        state["assembly"]["merged"].append({"n": cur["n"], "merge": sha, "resolved": resolved})
    state["assembly"]["cursor"] = None
    log(state, "merged %s -> %s after a hand resolution in %s (%s hunks); review round: %s"
        % (label, short(sha), ", ".join(files), resolved["hunks"], reviewed or "NOT RECORDED"))
    return is_main


def abort_resolution(root, wt, state):
    """Abandon the stopped merge: a member is held back (its owner told); the merge of origin/main is
    just dropped. Returns True when it was the merge of origin/main."""
    cur = state["assembly"].get("cursor")
    if not cur:
        raise Fail("nothing to abort: no member is stopped for resolution")
    if merge_in_progress(wt):
        git("merge", "--abort", cwd=wt)
    state["assembly"]["cursor"] = None
    if cur.get("main") is not None:
        log(state, "the merge of %s (%s) was abandoned; the batch stays at %s" % (remote_main(), short(cur["main"]), short(state["assembly"].get("head"))))
        return True
    m = members_by_n(state)[cur["n"]]
    against, earlier = conflict_attribution(root, state, m, cur["files"])
    hold_back(root, state, m, "conflicts with %s in %s (resolution abandoned)" % (against, ", ".join(cur["files"])),
              files=cur["files"], against=against, with_members=earlier, notify=not state["assembly"].get("no_notify"))
    return False


def merge_main(root, wt, state):
    """Merge origin/main into the assembled batch in its worktree, so a batch that fell behind main
    or into conflict with it catches up without a rebuild (verify allows a merge of main). Clean:
    recorded, and provenance checks it equals the clean merge. Conflict: stops for a hand resolution
    the way --resolve does (main cannot be held back); `--continue --reviewed` commits it under the
    subset rule and the body shows the diff from the clean merge. Returns False when stopped."""
    if not state["assembly"].get("head"):
        raise Fail("nothing assembled yet; run assemble first")
    if not (os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt)):
        raise Fail("no batch worktree at %s; run assemble first" % wt)
    main_sha = git("rev-parse", remote_main(), cwd=root)
    if is_ancestor(main_sha, "HEAD", wt):
        print("%s (%s) is already in %s" % (remote_main(), short(main_sha), branch_of(state["name"])))
        return True
    msg = "Merge %s into %s" % (remote_main(), branch_of(state["name"]))
    env = dict(os.environ, GIT_MERGE_AUTOEDIT="no")
    proc = subprocess.run(["git", "merge", "--no-ff", "--no-edit", "-m", msg, main_sha], cwd=wt, env=env,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    resolved = None
    if proc.returncode == 0:
        sha = git("rev-parse", "HEAD", cwd=wt)
    elif not merge_in_progress(wt):
        raise Fail("git merge of %s failed without a conflict to resolve:\n%s%s" % (remote_main(), proc.stdout, proc.stderr))
    else:
        still = unmerged_paths(wt)
        _, _, would = merge_tree_of(git("rev-parse", "HEAD", cwd=wt), main_sha, wt)
        conflicted = sorted(set(still) | set(would or []))
        replayed = replayed_paths(wt, conflicted, still)
        if still:
            state["assembly"]["cursor"] = {"n": None, "main": main_sha, "files": conflicted, "replayed": replayed}
            log(state, "the merge of %s stopped for resolution in %s%s; resolve per hunk in %s, `git add` the files, then "
                       "`scripts/batch.py assemble %s --continue [--reviewed '<note>']` (or --abort)"
                % (remote_main(), ", ".join(conflicted),
                   (" (rerere replayed %s from the earlier assembly and staged it; the review covers the whole resolution)" % ", ".join(replayed)) if replayed else "",
                   wt, state["name"]))
            save_state(root, state)
            return False
        prior = prior_resolution(state, "main", conflicted)
        resolved = {"files": conflicted, "hunks": None, "replayed": True,
                    "how": "rerere replayed the resolution recorded in the earlier assembly" if prior else "rerere replayed a recorded resolution",
                    "review": prior["review"] if prior else None}
        sha, _ = commit_resolution(wt, conflicted)
        resolved["hunks"] = resolution_hunks(wt, sha, conflicted)
        resolved["choices"] = resolution_choices(wt, sha, conflicted, "the batch", remote_main())
    state["assembly"].setdefault("main_merges", []).append({"merge": sha, "main": main_sha, "resolved": resolved})
    state["assembly"]["head"] = sha
    state["verified"] = None
    log(state, "merged %s (%s) into %s -> %s%s" % (remote_main(), short(main_sha), branch_of(state["name"]), short(sha),
                                                   (" with " + resolved["how"]) if resolved else ""))
    save_state(root, state)
    return True


def run_assembly(root, state, resolve_set, resume):
    """Merge the pending members in order; stop at a --resolve member's conflict; hold the rest back."""
    wt = worktree_dir(root, state["name"])
    members = members_by_n(state)
    pending = list(state["assembly"]["pending"])
    satisfied = set(state["assembly"].get("satisfied") or [])
    while pending:
        n = pending[0]
        m = members[n]
        held_ns = {h["n"] for h in state["assembly"].get("held", [])}
        blockers = [d for d in m["depends_on"] if d in held_ns or (d in state["pulled"] and d not in satisfied)]
        if blockers:
            hold_back(root, state, m, "depends on %s (not in this batch)" % ", ".join("#%d" % d for d in blockers))
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
    log(state, "assembled %s at %s: %d merged, %d already contained, %d held back"
        % (branch_of(state["name"]), short(state["assembly"]["head"]), len(state["assembly"]["merged"]),
           len(state["assembly"].get("contained", [])), len(state["assembly"].get("held", []))))
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
        was_main = continue_after_resolution(root, wt, state, args.reviewed) if args.cont else abort_resolution(root, wt, state)
        save_state(root, state)
        if was_main:
            return
        if not run_assembly(root, state, set(args.resolve or []), resume=True):
            raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)
        return
    if os.path.isdir(wt) and git_ok("rev-parse", "--is-inside-work-tree", cwd=wt) and merge_in_progress(wt) \
            and state["assembly"].get("cursor"):
        cur = state["assembly"]["cursor"]
        raise Fail("%s is stopped for resolution in %s; finish with --continue or drop it with --abort"
                   % (merge_label(cur.get("n")), wt))
    if args.merge_main:
        if args.without or args.repin or args.resolve:
            raise Fail("--merge-main merges %s into the assembled batch and takes no other option" % remote_main(), code=2)
        if not merge_main(root, wt, state):
            raise Fail("stopped at the merge of %s for a hand resolution (see above)" % remote_main(), code=3)
        return
    members = members_by_n(state)
    for n in args.repin or []:
        targets = list(members) if n == "all" else [int(n)]
        for k in targets:
            if k not in members:
                raise Fail("#%d is not a member of %s" % (k, args.name))
            pr = gh_json("pr", "view", str(k), "--json", "headRefOid,title,body,labels,statusCheckRollup,mergeable,baseRefName", cwd=root)
            old = members[k]["head"]
            members[k]["head"] = pr["headRefOid"]
            members[k]["title"] = pr["title"]
            members[k]["labels"] = label_names(pr)
            members[k]["tier"] = tier_of(members[k]["labels"])
            members[k]["trailer"], members[k]["trailer_error"] = parse_trailer(pr.get("body"))
            members[k]["ci"] = ci_of(pr)
            if pr.get("baseRefName") and pr["baseRefName"] != members[k]["base_ref"]:
                log(state, "re-pinned #%d: base %s -> %s" % (k, members[k]["base_ref"], pr["baseRefName"]))
                members[k]["base_ref"] = pr["baseRefName"]
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
    # A pulled member's dependents go with it, unless the member is already in origin/main (it merged
    # alone): then the dependency is satisfied by the new base and the dependents stay.
    dropped, satisfied = [], []
    for n in list(state["pulled"]):
        if is_ancestor(members[n]["head"], remote_main(), root):
            satisfied.append(n)
            continue
        for d in dependents_of(state, n):
            if d not in state["pulled"]:
                state["pulled"].append(d)
                dropped.append((d, n))
    state["pulled"].sort()
    prepare_worktree(root, args.name)
    state["base"] = git("rev-parse", remote_main(), cwd=root)
    old_log = state["assembly"].get("log", [])
    # Resolutions the earlier assemblies recorded, so a rerere replay of the same conflict keeps its review.
    prev = dict(state["assembly"].get("previous_resolutions") or {})
    for e in state["assembly"].get("merged", []):
        if e.get("resolved"):
            prev[str(e["n"])] = e["resolved"]
    for e in state["assembly"].get("main_merges", []):
        if e.get("resolved"):
            prev["main"] = e["resolved"]
    state["assembly"] = {"log": old_log, "merged": [], "contained": [], "held": [], "main_merges": [], "declared": [],
                         "previous_resolutions": prev, "satisfied": satisfied,
                         "pending": [n for n in state["order"] if n not in state["pulled"]],
                         "cursor": None, "head": None, "no_notify": bool(args.no_notify)}
    log(state, "assembling %s from %s at %s; pulled: %s" % (branch_of(args.name), remote_main(), short(state["base"]),
                                                            ", ".join("#%d" % n for n in state["pulled"]) or "none"))
    for n in satisfied:
        log(state, "#%d is pulled but already in %s; its dependents stay in the batch" % (n, remote_main()))
    for d, n in dropped:
        log(state, "#%d dropped with #%d (depends on it)" % (d, n))
    if not run_assembly(root, state, set(args.resolve or []), resume=False):
        raise Fail("stopped at #%d for a hand resolution (see above)" % state["assembly"]["cursor"]["n"], code=3)


def in_batch(state):
    """The members the batch lands, in plan order: the merged records and the already-contained
    ones (a contained member has no merge commit; its head is reachable through an earlier member's)."""
    order = state["order"]
    recs = list(state["assembly"].get("merged", [])) + list(state["assembly"].get("contained", []))
    return sorted(recs, key=lambda e: order.index(e["n"]) if e["n"] in order else len(order))


# ── verify ───────────────────────────────────────────────────────────────────

def parents_of(sha, cwd):
    return git("rev-list", "--parents", "-n", "1", sha, cwd=cwd).split()[1:]


def subject_of(sha, cwd):
    return git("log", "-n", "1", "--format=%s", sha, cwd=cwd)


def is_ancestor(a, b, cwd):
    return git_ok("merge-base", "--is-ancestor", a, b, cwd=cwd)


def merge_tree_of(p1, p2, cwd):
    """The tree `git merge-tree --write-tree` produces for p1 and p2, and the paths it reports as
    conflicted: (tree, "clean", []) or (tree, "conflicts", paths) with the conflict markers left in
    the conflicted files. (None, "unsupported", None) when this git lacks `merge-tree --write-tree`
    (added in git 2.38). The markers are labeled with the identifiers given, so two callers get the
    same tree for the same merge only when both name the parents the same way: pass SHAs."""
    proc = _run(["git", "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", p1, p2], cwd=cwd, check=False)
    fields = proc.stdout.split("\0")
    if proc.returncode in (0, 1) and fields and fields[0].strip():
        if proc.returncode == 0:
            return fields[0].strip(), "clean", []
        paths = []
        for f in fields[1:]:
            if not f:
                break
            paths.append(f)
        return fields[0].strip(), "conflicts", paths
    return None, "unsupported", None


def paths_off_clean_merge(p1, p2, tree, cwd):
    """The paths in `tree` that differ from what git makes of p1 and p2 by itself: the conflicted
    files a resolution had to touch, plus anything else a hand put into the merge. (paths, kind,
    conflicted) with kind "clean" or "conflicts" and the paths merge-tree calls conflicted, or
    (None, "unsupported", None)."""
    mt, kind, conflicted = merge_tree_of(p1, p2, cwd)
    if mt is None:
        return None, kind, None
    return git("diff-tree", "--name-only", "-r", mt, tree, cwd=cwd).split(), kind, conflicted


def stray_resolution_paths(files, paths):
    """The paths a resolution changed that it had no business changing. A resolution may touch its
    conflicted files, and entry files under upstream/ when UPSTREAM.md was among them (a row
    conversion writes entries); every other path is a change the body would never show."""
    allowed = set(files)
    return sorted(p for p in paths
                  if p not in allowed and not (UPSTREAM_MD in allowed and p.startswith("upstream/")))


def merge_label(rec_n):
    return "#%d" % rec_n if rec_n is not None else "the merge of %s" % remote_main()


def check_merge_tree(rec, label, c, p1, p2, root, lines):
    """One first-parent merge against the merge git would make of its parents by itself. Equal: fine.
    Different with a recorded resolution: the differing paths must be the resolution's (the subset
    rule, so a stray staged file cannot ride inside a resolved merge unseen). Different without one:
    an unrecorded resolution or an edit hidden in the merge. When the parents' own merge conflicts,
    every path merge-tree calls conflicted must be covered by the recorded resolution and hold no
    conflict marker in the merge: a conflicted file kept as merge-tree wrote it (markers, or the
    modified side of a modify/delete) does not differ from that tree, so the comparison alone would
    read it as the clean merge. Returns ok."""
    merge_tree = git("rev-parse", c + "^{tree}", cwd=root)
    paths, kind, conflicted = paths_off_clean_merge(p1, p2, merge_tree, root)
    if paths is None:
        lines.append("FAIL provenance: this git cannot check %s's merge tree (needs git 2.38)" % label)
        return False
    resolved = (rec or {}).get("resolved")
    if kind == "conflicts":
        if not resolved:
            lines.append("FAIL provenance: %s merge %s resolved a conflict that is not recorded (in %s)"
                         % (label, short(c), ", ".join(conflicted)))
            return False
        uncovered = [p for p in conflicted if p not in resolved["files"]]
        if uncovered:
            lines.append("FAIL provenance: %s merge %s resolved a conflict in %s that its recorded resolution (%s) does not cover"
                         % (label, short(c), ", ".join(uncovered), ", ".join(resolved["files"])))
            return False
        marked = marker_paths(merge_tree, conflicted, root)
        if marked:
            lines.append("FAIL provenance: %s merge %s carries a conflict marker in %s" % (label, short(c), ", ".join(marked)))
            return False
    if not paths and kind == "clean":
        lines.append("ok   provenance: %s merge %s equals the clean merge of its parents" % (label, short(c)))
        return True
    if resolved:
        stray = stray_resolution_paths(resolved["files"], paths)
        if stray:
            lines.append("FAIL provenance: %s merge %s changes %s outside its recorded resolution (%s)"
                         % (label, short(c), ", ".join(stray), ", ".join(resolved["files"])))
            return False
        lines.append("ok   provenance: %s merge carries a recorded resolution (%s) in %s" % (label, resolved["how"], ", ".join(paths or conflicted)))
        return True
    lines.append("FAIL provenance: %s merge %s differs from the clean merge of its parents (undeclared change in %s)" % (label, short(c), ", ".join(paths)))
    return False


def declared_commit_record(sha, cwd):
    """What the body says about a `batch:` commit: its subject, files and shortstat."""
    stat = [l.strip() for l in git("show", "--shortstat", "--format=", sha, cwd=cwd).splitlines() if l.strip()]
    return {"sha": sha, "subject": subject_of(sha, cwd),
            "files": git("diff-tree", "--no-commit-id", "--name-only", "-r", sha, cwd=cwd).split(),
            "stat": stat[-1] if stat else ""}


def check_provenance(root, state, lines):
    """(a) Every non-merge commit the batch adds is a declared `batch:` commit, and the first-parent
    chain since main is exactly the member merges plus declared commits and merges of origin/main.
    Every merge on the chain, a member's or main's, must equal the clean merge of its parents unless
    it carries a recorded resolution, and then it may differ only in the resolution's files: an edit
    slipped into a merge commit is otherwise invisible to `rev-list --no-merges`. A member recorded
    as already contained must be reachable from the tip."""
    ok = True
    br = branch_of(state["name"])
    merged = state["assembly"].get("merged", [])
    main_merges = {e["merge"]: e for e in state["assembly"].get("main_merges", [])}
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
            ok = check_merge_tree(rec, "#%d" % n, c, p1, p2, root, lines) and ok
        elif is_ancestor(p2, remote_main(), root):
            ok = check_merge_tree(main_merges.get(c), "the %s" % remote_main(), c, p1, p2, root, lines) and ok
        else:
            ok = False
            lines.append("FAIL provenance: %s merges %s, which is neither a member head nor %s" % (short(c), short(p2), remote_main()))
    if member_merges != len(merged):
        ok = False
        lines.append("FAIL provenance: %d member merges on the chain, %d recorded" % (member_merges, len(merged)))
    for e in state["assembly"].get("contained", []):
        if not is_ancestor(members[e["n"]]["head"], br, root):
            ok = False
            lines.append("FAIL provenance: #%d is recorded as already contained (by %s) but its head %s is not in %s"
                         % (e["n"], e["contained_by"], short(members[e["n"]]["head"]), br))
    state["assembly"]["declared"] = [declared_commit_record(s, root) for s in declared]
    if ok:
        lines.append("ok   provenance: %d member merge(s), %d declared batch: commit(s), nothing else" % (member_merges, len(declared)))
    return ok


def ledger_check_on_branch(root, br):
    """`scripts/upstream-ledger.py check` on the BRANCH's tree, in a temporary detached worktree, so
    the verdict is the branch's and not some directory's (the batch worktree may be gone or dirty).
    None when the branch carries no ledger script (pre-migration); else the completed process."""
    if not git_ok("cat-file", "-e", "%s:%s" % (br, LEDGER_SCRIPT), cwd=root):
        return None
    holder = tempfile.mkdtemp(prefix="romp-batch-ledger-")
    tree = os.path.join(holder, "tree")
    try:
        git("worktree", "add", "--quiet", "--detach", tree, br, cwd=root)
        return _run([sys.executable, LEDGER_SCRIPT, "check"], cwd=tree, check=False)
    finally:
        git("worktree", "remove", "--force", tree, cwd=root, check=False)
        shutil.rmtree(holder, ignore_errors=True)


def cmd_verify(args, quiet=False):
    root = repo_root()
    state = load_state(root, args.name)
    # The earlier verdict is cleared first: a verify that dies half-way (a gh error) must not leave
    # a green verification behind for summarize to publish.
    if state.get("verified"):
        state["verified"] = None
        save_state(root, state)
    fetch(root, args.no_fetch)
    lines, ok = [], True
    br = branch_of(args.name)
    if not git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        raise Fail("%s does not exist; run assemble first" % br)
    head = git("rev-parse", br, cwd=root)
    if state["assembly"].get("cursor"):
        raise Fail("%s is still stopped for resolution; --continue or --abort first" % merge_label(state["assembly"]["cursor"].get("n")))
    pending = state["assembly"].get("pending") or []
    if pending or not state["assembly"].get("head"):
        raise Fail("assembly incomplete: %s never merged; run assemble again"
                   % (", ".join("#%d" % n for n in pending) or "the last assembly did not finish, so the members"))
    if state["assembly"].get("head") != head:
        # A `batch:` commit the batcher added after assembly moves the tip; provenance below decides
        # whether what moved it is allowed. The recorded head follows the branch.
        lines.append("note head: %s moved from %s to %s since assembly; the chain is checked below"
                     % (br, short(state["assembly"].get("head")), short(head)))
        state["assembly"]["head"] = head
    ok = check_provenance(root, state, lines) and ok
    members = members_by_n(state)
    landing = in_batch(state)
    in_batch_refs = {members[e["n"]]["head_ref"] for e in landing}
    for e in landing:
        m = members[e["n"]]
        pr = gh_json("pr", "view", str(m["n"]), "--json", "headRefOid,state,baseRefName,isDraft,statusCheckRollup,mergeable", cwd=root)
        if pr["headRefOid"] != m["head"]:
            ok = False
            lines.append("FAIL head moved: #%d pinned %s, now %s (assemble --repin %d, then re-assemble)"
                         % (m["n"], short(m["head"]), short(pr["headRefOid"]), m["n"]))
        else:
            lines.append("ok   head: #%d at %s%s" % (m["n"], short(m["head"]),
                                                    (" (already contained by %s, no merge of its own)" % e["contained_by"]) if e.get("contained_by") else ""))
        if pr.get("state") != "OPEN":
            ok = False
            lines.append("FAIL state: #%d is %s (pull it; the rebuild starts from the current %s, which carries whatever merged alone)"
                         % (m["n"], pr.get("state"), remote_main()))
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
    proc = ledger_check_on_branch(root, br)
    if proc is None:
        lines.append("note ledger: %s is not on %s (pre-migration); not checked" % (LEDGER_SCRIPT, br))
        state["ledger"] = "pre-migration"
    elif proc.returncode == 0:
        lines.append("ok   ledger: check clean")
        state["ledger"] = "clean"
    else:
        ok = False
        lines.append("FAIL ledger: %s" % (proc.stdout + proc.stderr).strip()[:500])
        state["ledger"] = "failed"
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


def resolution_reason(resolved):
    """The "Read these first" phrase for a recorded resolution."""
    note = resolved.get("review")
    rev = ("one review round: %s" % note) if note and note != "mechanical" else (
        "mechanical" if note == "mechanical" else "review round NOT recorded")
    if resolved.get("replayed") and note and note != "mechanical":
        rev = "one review round in the earlier assembly, replayed by rerere: %s" % note
    hunks, files, choices = resolved.get("hunks"), resolved["files"], resolved.get("choices") or {}
    # A side taken wholesale is said in words ("took #108's version"); the hunk count alone hid it
    # (and read 0 when the kept file is what merge-tree left, as in a modify/delete).
    parts = [("%s: %s" % (f, choices[f])) if len(files) > 1 else choices[f] for f in files if choices.get(f)]
    if hunks is None and not parts:
        parts.append(resolved["how"])
    elif hunks or not parts:
        parts.append("%d hunk%s" % (hunks, "" if hunks == 1 else "s"))
    return "conflict resolved in %s (%s); %s. [diff from the clean merge below]" % (", ".join(files), "; ".join(parts), rev)


def read_first_reasons(m, resolved, contained_by=None):
    """The computed rule: a member is listed under "Read these first" when its merge needed a
    resolution, when it was already contained by an earlier member (no merge of its own, so a
    missing `Depends-on`), when its tier is `feature` or unlabeled, when it touches kernel/,
    .github/, .githooks/, install.sh or uninstall.sh, when its trailer is missing, or when its own
    CI never ran because it was conflicting."""
    reasons = []
    if resolved:
        reasons.append(resolution_reason(resolved))
    if contained_by:
        reasons.append("already contained by %s: no merge commit of its own (add `Depends-on` or reorder next time)" % contained_by)
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
    """Everything the body needs that comes from git: resolution diffs and the ledger entry table.
    A resolution's diff runs from the merge-tree of the parents to the merge and covers EVERY path
    that differs from it (the recorded files and anything else), so what the maintainer reads is the
    whole difference; per path, whose version was taken when one side won outright."""
    br = branch_of(state["name"])
    members = members_by_n(state)
    resolutions = []
    # The merge shown is the one ON THE BRANCH for that second parent (a merge amended after the
    # record was written is what the maintainer would land), the recorded sha as the fallback.
    on_chain = {}
    if git_ok("rev-parse", "--verify", "--quiet", br, cwd=root):
        for c in git("rev-list", "--first-parent", "%s..%s" % (remote_main(), br), cwd=root).split():
            ps = parents_of(c, root)
            if len(ps) == 2:
                on_chain.setdefault(ps[1], c)
    recs = [(e["n"], members[e["n"]]["head"], e) for e in state["assembly"].get("merged", [])] + \
           [(None, e.get("main"), e) for e in state["assembly"].get("main_merges", [])]
    for n, p2, e in recs:
        if not e.get("resolved"):
            continue
        merge = on_chain.get(p2, e["merge"])
        paths = list(e["resolved"]["files"])
        ps = parents_of(merge, root)
        if len(ps) == 2:
            off, _, _ = paths_off_clean_merge(ps[0], ps[1], merge + "^{tree}", root)
            paths = sorted(set(paths) | set(off or []))
        out = resolution_diff(root, merge, paths)
        if out is None:
            out = "(this git cannot compute the clean merge of the parents; needs git 2.38)"
        choices = resolution_choices(root, merge, paths, "the batch", ("#%d" % n) if n is not None else remote_main())
        resolutions.append({"n": n, "merge": merge, "diff": out, "choices": choices})
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


def _largest_fitting(lo, hi, fits):
    """The largest n in [lo, hi] with fits(n), assuming fits is monotone (True below some point);
    lo is assumed to fit."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def render_body(state, inputs, cap=BODY_CAP):
    """The batch PR body. Pure over its inputs so the cap rule is testable. The members table, the
    first block, "Read these first", "Held back" and the trailer are never cut. When the body would
    exceed the cap the rest is fitted to the budget in priority order, each block keeping as much as
    fits: the ledger entries table (else a count), then the conflict resolutions (up to
    RESOLUTION_LINES per merge; the diff from the clean merge is what the maintainer reads), then the
    assembly log (its newest lines). A body still over the cap with all of that gone is refused with
    the advice to split the batch."""
    name = state["name"]
    members = members_by_n(state)
    merged = state["assembly"].get("merged", [])
    contained = state["assembly"].get("contained", [])
    landing = in_batch(state)
    held = state["assembly"].get("held", [])
    pulled = state.get("pulled", [])
    declared = state["assembly"].get("declared") or []
    main_merges = state["assembly"].get("main_merges") or []
    resolved_by_n = {e["n"]: e.get("resolved") for e in merged}
    contained_by = {e["n"]: e["contained_by"] for e in contained}
    v = state.get("verified") or {}
    sw = state.get("sweep") or {}
    head = state["assembly"].get("head") or ""
    extra = []
    if held:
        extra.append("%d held back" % len(held))
    if pulled:
        extra.append("%d pulled" % len(pulled))
    title = "# Batch %s: %d PR%s%s" % (name, len(landing), "" if len(landing) == 1 else "s", (" (%s)" % ", ".join(extra)) if extra else "")
    if v.get("ok") and v.get("head") == head:
        ledger = {"clean": "ledger check clean", "pre-migration": "ledger: pre-migration, not checked", "failed": "ledger check FAILED"}.get(state.get("ledger"), "ledger: not checked")
        verified = ("Merge with \"Create a merge commit\". Verified at %s: %s; provenance clean; %s. CI on this PR: see checks."
                    % (short(head), sw.get("text", "sweep not recorded"), ledger))
    else:
        verified = "Merge with \"Create a merge commit\". NOT VERIFIED at %s: run `scripts/batch.py verify %s` (verification is %s)." % (
            short(head), name, "stale" if v else "missing")

    read_first = []
    for e in landing:
        m = members[e["n"]]
        reasons = read_first_reasons(m, resolved_by_n.get(e["n"]), contained_by.get(e["n"]))
        if reasons:
            read_first.append("- #%d %s: %s." % (m["n"], m["head_ref"], "; ".join(reasons).rstrip(".")))
    for e in main_merges:
        if e.get("resolved"):
            read_first.append("- merge of %s (%s): %s." % (remote_main(), short(e["merge"]), resolution_reason(e["resolved"]).rstrip(".")))
    for d in declared:
        read_first.append("- `batch:` commit %s by the batcher: %s; %s%s." % (
            short(d["sha"]), d["subject"], d.get("stat") or "no diffstat",
            ("; touches " + ", ".join(d["files"])) if d.get("files") else ""))
    read_first_block = "\n".join(read_first) if read_first else \
        "- none: every member is labeled, carries a trailer, touches no sensitive path, merged clean and had its own CI; the batch adds no commit of its own."

    rows = ["| # | Title | Tier | Rounds | Sweep at own head | Own CI | Flags | Ledger |",
            "|---|---|---|---|---|---|---|---|"]
    entries = inputs.get("entries") or []
    for e in landing:
        m = members[e["n"]]
        t = m.get("trailer") or {}
        flags = []
        if resolved_by_n.get(e["n"]):
            flags.append("resolved")
        if contained_by.get(e["n"]):
            flags.append("contained by %s" % contained_by[e["n"]])
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
            told = h.get("told")
            owner = "owner told" if told else ("owner NOT told (%s)" % h.get("told_why", "comment failed") if told is False else "owner not told")
            held_lines.append("- #%d: %s; %s." % (h["n"], h["reason"].rstrip("."), owner))
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
            heading = ("### #%d" % r["n"]) if r.get("n") is not None else "### merge of %s (%s)" % (remote_main(), short(r.get("merge")))
            notes = "".join("- %s: %s\n" % (p, why) for p, why in sorted((r.get("choices") or {}).items()))
            block = ("```diff\n%s\n```%s" % ("\n".join(cut), ("\n(%d more lines)" % more) if more > 0 else "")) if lines \
                else "(no diff: the merge keeps these paths as git left them in the conflicted tree)"
            parts.append("%s\n\n%s%s%s" % (heading, notes, "\n" if notes else "", block))
        return "\n\n".join(parts) if parts else "(none)"

    log_all = state["assembly"].get("log") or []

    def log_block(budget_lines):
        cut = log_all[-budget_lines:] if budget_lines else []
        more = len(log_all) - len(cut)
        return ("(%d earlier lines omitted)\n" % more if more > 0 else "") + "\n".join(cut) if cut else "(omitted)"

    trailer = "<!-- romp-batch: %s -->" % json.dumps({
        "name": name, "base": state.get("base"),
        "members": [{"n": e["n"], "head": members[e["n"]]["head"]} for e in landing]}, separators=(",", ":"))

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

    res_max = min(RESOLUTION_LINES, max([len(r["diff"].splitlines()) for r in inputs.get("resolutions") or []] or [0]))
    log_max = len(log_all)
    body = assemble(res_max, log_max, True)
    if len(body) <= cap:
        return body
    full_entries = len(assemble(0, 0, True)) <= cap
    if len(assemble(0, 0, full_entries)) > cap:
        raise Fail("the body is %d characters with every detail cut; GitHub caps it at %d. Split the batch (two a day beat one of twenty)."
                   % (len(assemble(0, 0, full_entries)), cap))
    res_lines = _largest_fitting(0, res_max, lambda k: len(assemble(k, 0, full_entries)) <= cap)
    log_lines = _largest_fitting(0, log_max, lambda k: len(assemble(res_lines, k, full_entries)) <= cap)
    body = assemble(res_lines, log_lines, full_entries)
    while len(body) > cap and (res_lines or log_lines):
        # The "(N more lines)" notes make the size not quite monotone; back off a line at a time.
        if log_lines:
            log_lines -= 1
        else:
            res_lines -= 1
        body = assemble(res_lines, log_lines, full_entries)
    if len(body) > cap:
        raise Fail("the body is %d characters with every detail cut; GitHub caps it at %d. Split the batch (two a day beat one of twenty)."
                   % (len(body), cap))
    return body


def find_batch_pr(root, state):
    if state.get("pr") and state["pr"].get("number"):
        return state["pr"]["number"]
    # --state all: after the maintainer clicks merge, the PR is no longer open, and finish must
    # still find it when summarize never recorded it (a PR opened by hand).
    rows = gh_json("pr", "list", "--state", "all", "--head", branch_of(state["name"]), "--json", "number,url", "--limit", "5", cwd=root)
    if rows:
        state["pr"] = {"number": rows[0]["number"], "url": rows[0].get("url")}
        return rows[0]["number"]
    return None


def comment_or_report(root, state, n, text, what):
    """Post a comment on #n and say so when it fails, instead of assuming it landed. Returns ok."""
    proc = gh("pr", "comment", str(n), "--body", text, cwd=root, check=False)
    if proc.returncode == 0:
        return True
    err = [l for l in (proc.stderr or proc.stdout).strip().splitlines() if l.strip()]
    log(state, "#%d: gh pr comment failed (%s) for %s; tell the owner by postal: %s" % (n, err[-1] if err else "exit %d" % proc.returncode, what, text))
    return False


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
    n_members = len(in_batch(state))
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
    for e in in_batch(state):
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
                            reviewed=None, no_fetch=args.no_fetch, no_notify=args.no_notify, merge_main=False)
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
        comment_or_report(root, state, args.n, text, "the pull")
        for d in dropped:
            comment_or_report(root, state, d, "Dropped from batch %s with #%d, which it depends on. It stays open against %s."
                              % (args.name, args.n, MAIN), "the drop")
        save_state(root, state)
    print("pulled #%d%s; pushed and re-summarized" % (args.n, (", dropped with it: " + ", ".join("#%d" % d for d in dropped)) if dropped else ""))


def repo_settings(root):
    return gh_json("repo", "view", "--json", "mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,deleteBranchOnMerge", cwd=root) or {}


def auto_merge_allowed(root):
    """The repository's "Allow auto-merge" setting (REST `allow_auto_merge`; off on the fork at
    writing): GitHub refuses `--auto` on a PR until it is on. True, False, or None when unreadable."""
    proc = gh("api", "repos/{owner}/{repo}", cwd=root, check=False)
    if proc.returncode != 0:
        return None
    try:
        v = json.loads(proc.stdout or "{}").get("allow_auto_merge")
    except (json.JSONDecodeError, AttributeError):
        return None
    return v if isinstance(v, bool) else None


# Ruleset rule types that make a merge wait for something. The rest (non_fast_forward, deletion,
# creation, update, ...) protect the ref and gate no merge, so --auto would merge at once.
GATING_RULE_TYPES = ("required_status_checks", "pull_request", "required_deployments", "merge_queue", "code_scanning")
# The classic branch-protection settings that gate a merge, and how the go-ahead names them.
GATING_PROTECTION = {"required_status_checks": "status checks", "required_pull_request_reviews": "reviews"}


def main_protection(root):
    """What on main gates a merge, as (gating, found). `gating` names it, or is None when nothing
    does: ruleset rules of a type in GATING_RULE_TYPES, read from the rules that apply to the branch
    (`rules/branches/main`, not the repository-wide rulesets list, which counts tag and push rulesets
    too; the endpoint lists the protective rules as well, so the types are read, not counted), or
    classic branch protection with required status checks or required reviews. `found` says what was
    there instead, for the refusal. A rules read that fails, or a protection read that fails with
    anything but a 404 (GitHub's answer for an unprotected branch), raises Fail with gh's error: a
    failed read is not "none". `gh pr merge --auto` is only useful with a gating rule: with nothing
    required, auto-merge merges at once. This detects, it never assumes (scripts/land.sh applies the
    same gate)."""
    proc = gh("api", "repos/{owner}/{repo}/rules/branches/%s" % MAIN, cwd=root, check=False)
    if proc.returncode != 0:
        raise Fail("--auto, and could not read the rules on %s: %s" % (MAIN, (proc.stderr + proc.stdout).strip()))
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as e:
        raise Fail("--auto, and could not read the rules on %s: not JSON (%s)" % (MAIN, e))
    types = [str(r.get("type") or "?") for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    gating = [t for t in types if t in GATING_RULE_TYPES]
    other = [t for t in types if t not in GATING_RULE_TYPES]
    proc = gh("api", "repos/{owner}/{repo}/branches/%s/protection" % MAIN, cwd=root, check=False)
    protected, prot_set, prot_gating = False, [], []
    if proc.returncode == 0:
        try:
            body = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError as e:
            raise Fail("--auto, and could not read %s's branch protection: not JSON (%s)" % (MAIN, e))
        protected = True
        prot_set = sorted(k for k, v in body.items() if v is not None) if isinstance(body, dict) else []
        prot_gating = [k for k in GATING_PROTECTION if k in prot_set]
    elif "HTTP 404" not in proc.stderr + proc.stdout:
        raise Fail("--auto, and could not read %s's branch protection: %s" % (MAIN, (proc.stderr + proc.stdout).strip()))
    if gating or prot_gating:
        parts = []
        if gating:
            parts.append("rules on %s gate a merge (%s)" % (MAIN, ", ".join(gating)))
        if prot_gating:
            parts.append("classic branch protection on %s requires %s" % (MAIN, " and ".join(GATING_PROTECTION[k] for k in prot_gating)))
        return ", and ".join(parts), None
    found = [("ruleset rules %s, which protect the branch and gate no merge" % ", ".join(other)) if other
             else "no rules apply to %s" % MAIN]
    found.append(("branch protection on %s requires no checks and no reviews (set: %s)" % (MAIN, ", ".join(prot_set) or "nothing"))
                 if protected else "it has no classic protection")
    return None, ", and ".join(found)


def retarget_stacked_members(root, state):
    """A member based on another member's branch is retargeted to main right before the merge.

    GitHub marks a PR merged when its head becomes reachable from ITS BASE. The batch merges into
    main, so a member whose base is a sibling branch would stay open (its base never moves) even
    though its content is in main. Against main, the documented indirect-merge rule applies to it
    like every other member. Done here and not at plan time so the member keeps its stacked diff
    and review until the moment it lands."""
    members = members_by_n(state)
    landing = in_batch(state)
    in_batch_refs = {members[e["n"]]["head_ref"] for e in landing}
    for e in landing:
        m = members[e["n"]]
        if m["base_ref"] != MAIN and m["base_ref"] in in_batch_refs:
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
    cmd = ["pr", "merge", str(b), "--merge", "--match-head-commit", head]
    if args.auto:
        # Both preconditions are read, never assumed (scripts/land.sh applies the same two), and
        # before anything is changed: GitHub refuses auto-merge until the repository setting is on,
        # and with nothing required on main --auto merges at once and protects nothing.
        allowed = auto_merge_allowed(root)
        if allowed is not True:
            raise Fail("--auto needs the repository's \"Allow auto-merge\" setting, which is %s (REST allow_auto_merge). "
                       "Turning it on is the maintainer's call: `gh repo edit --enable-auto-merge`. Merge without --auto instead."
                       % ("off" if allowed is False else "unreadable"))
        gating, found = main_protection(root)
        if not gating:
            raise Fail("--auto needs a ruleset or branch protection on %s that gates a merge (read from GitHub: %s); "
                       "with nothing required, auto-merge merges at once and protects nothing. Merge without --auto." % (MAIN, found))
        print("merging with --auto: auto-merge is allowed and %s" % gating)
        cmd.append("--auto")
    retarget_stacked_members(root, state)
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
    """After the batch PR merged: confirm each member reads MERGED (and tell the ones that do not),
    retarget still-open dependents, delete member branches and the batch branch, run the orphan
    check, report. Every observation about GitHub's behavior (did it mark the member merged, did
    it delete the branch) is recorded the FIRST time finish sees it, before finish changes anything,
    and kept across re-runs: a run that dies half-way and is run again must not attribute its own
    deletions to GitHub, forget that a member was stacked, or comment on a member twice. A state
    whose last assembly did not finish is refused with the pending members named: its member list is
    not what the merged branch carried (a rebuild that died after an earlier complete assembly had
    been pushed), and acting on it would clean up the wrong set."""
    root = repo_root()
    state = load_state(root, args.name)
    fetch(root, args.no_fetch)
    b = find_batch_pr(root, state)
    if not b:
        raise Fail("no batch PR recorded for %s" % args.name)
    pending = state["assembly"].get("pending") or []
    if state["assembly"].get("cursor") or pending or not state["assembly"].get("head"):
        raise Fail("assembly incomplete: %s never merged in the last assembly, so this state does not say which members "
                   "batch PR #%d carried; finish acts only on a complete assembly. Check the pending member(s) by hand: %s"
                   % (", ".join("#%d" % n for n in pending) or "the last assembly did not finish, so the members", b,
                      "; ".join("`gh pr view %d`" % n for n in pending) or "`gh pr view N`"))
    bpr = gh_json("pr", "view", str(b), "--json", "state,mergeCommit,url", cwd=root)
    if bpr.get("state") != "MERGED":
        raise Fail("batch PR #%d is %s, not MERGED; finish runs after the merge" % (b, bpr.get("state")))
    merge_sha = (bpr.get("mergeCommit") or {}).get("oid")
    if merge_sha and not is_ancestor(merge_sha, remote_main(), root):
        raise Fail("batch PR #%d's merge commit %s is not an ancestor of %s; was it squashed or rebased?" % (b, short(merge_sha), remote_main()))
    members = members_by_n(state)
    landing = in_batch(state)
    member_refs = {members[e["n"]]["head_ref"] for e in landing} | {branch_of(args.name)}
    prog = state.setdefault("finish_progress", {"members": {}, "branches": {}, "retargeted": []})
    report = {"merged": [], "open": [], "retargeted": [], "deleted": [], "already_gone": [], "observations": []}
    for e in landing:
        m = members[e["n"]]
        key = str(m["n"])
        pr = gh_json("pr", "view", key, "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
        first = prog["members"].get(key)
        if first is None:
            # Recorded before anything is changed: what GitHub did by itself.
            first = prog["members"][key] = {"state": pr.get("state"), "base": pr.get("baseRefName"), "head": pr.get("headRefOid"), "told": False}
            save_state(root, state)
        was_stacked = first["base"] in member_refs
        if pr.get("state") == "OPEN" and was_stacked and pr.get("baseRefName") != MAIN:
            # The maintainer merged by hand, so land's retarget did not run: a member still based on
            # a sibling branch cannot have been marked merged. Retarget now and look again; whether
            # GitHub marks it merged on the retarget is to verify on the first batch, so the outcome
            # is recorded either way.
            gh("pr", "edit", key, "--base", MAIN, cwd=root)
            pr = gh_json("pr", "view", key, "--json", "state,headRefOid,baseRefName,headRefName", cwd=root)
            first["retargeted_to_main"] = pr.get("state")
            save_state(root, state)
        if first.get("retargeted_to_main"):
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
        if not args.no_notify and not first.get("told"):
            if comment_or_report(root, state, m["n"], text, "the still-open notice"):
                first["told"] = True
                save_state(root, state)
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
            if pr["number"] not in prog["retargeted"]:
                prog["retargeted"].append(pr["number"])
                save_state(root, state)
    report["retargeted"] = list(prog["retargeted"])
    remote_branches = set(git("ls-remote", "--heads", REMOTE, cwd=root).replace("refs/heads/", "").split()[1::2])
    for n in report["merged"]:
        ref = members[n]["head_ref"]
        seen = prog["branches"].get(ref)
        if seen is None:
            # Recorded once, before the delete: whether GitHub had already removed the branch.
            seen = prog["branches"][ref] = "present" if ref in remote_branches else "already gone"
            save_state(root, state)
        if seen == "present":
            if ref in remote_branches:
                git("push", "--quiet", REMOTE, "--delete", ref, cwd=root)
                prog["branches"][ref] = "deleted by finish"
                save_state(root, state)
            report["deleted"].append(ref)
        elif seen == "deleted by finish":
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
    """First-parent bisect of the batch chain. The command is run at the tip and at the base FIRST:
    `git bisect` takes "tip bad, base good" on faith, so a command that never fails would name the
    last member and one that fails everywhere the first; both are said instead of a member."""
    root = repo_root()
    state = load_state(root, args.name)
    wt = worktree_dir(root, args.name)
    if not os.path.isdir(wt):
        raise Fail("no batch worktree at %s" % wt)
    if not args.cmd:
        raise Fail("bisect needs a command after --, e.g. `-- pytest tests/test_x.py -q`", code=2)
    br = branch_of(args.name)
    tip = git("rev-parse", br, cwd=wt)
    base = git("merge-base", remote_main(), tip, cwd=wt)
    if git("rev-parse", "HEAD", cwd=wt) != tip:
        raise Fail("%s is not checked out at %s (HEAD is %s)" % (wt, br, short(git("rev-parse", "HEAD", cwd=wt))))
    if subprocess.run(args.cmd, cwd=wt).returncode == 0:
        raise Fail("the command passes at the batch tip %s; nothing to bisect (does it run the failing test?)" % short(tip))
    git("checkout", "--quiet", "--detach", base, cwd=wt)
    try:
        at_base = subprocess.run(args.cmd, cwd=wt).returncode
    finally:
        git("checkout", "--quiet", br, cwd=wt)
    if at_base != 0:
        raise Fail("the command fails at the base %s (%s) too; no member made it fail. Check the command and the environment before blaming a member"
                   % (short(base), remote_main()))
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

HELP_NAME = "the batch's name (`plan` prints it; state lives in <git common dir>/batch/<name>.json)"
HELP_NO_FETCH = "skip `git fetch --prune %s` first (the default fetches so heads and %s are current)" % (REMOTE, MAIN)
HELP_NO_NOTIFY = "post no comment on the member PRs this touches (the postal text is still printed)"


def main(argv=None):
    doc = __doc__.split("\n\n")
    # The epilog is the docstring's explanation, subcommand table and state paragraph; the test
    # contracts that follow them are for a reader of the source.
    ap = argparse.ArgumentParser(prog="scripts/batch.py", description=doc[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(p for p in doc[1:] if not p.startswith("Contracts the tests")))
    sub = ap.add_subparsers(dest="subcommand", required=True, metavar="<subcommand>")

    p = sub.add_parser("plan", help="pick and order the members, predict conflicts, write the plan",
                       description="Pick the members: open, non-draft PRs against %s or against another candidate's branch, not labeled "
                                   "`%s` or `%s`. Order them dependencies first (a base that is another candidate's branch, or "
                                   "`Depends-on: #N` in the body's first lines), then by number; predict conflicts read-only "
                                   "against the accumulating tree; pin every head SHA; write the plan. Nothing is merged."
                                   % (MAIN, LABEL_MAJOR, LABEL_HOLD))
    p.add_argument("--labeled", action="store_true", help="only PRs labeled `%s`" % LABEL_LAND)
    p.add_argument("--name", help="batch name (default: today's date plus the first free letter)")
    p.add_argument("--force", action="store_true", help="overwrite a plan that was already assembled")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("assemble", help="merge the pinned heads into ../romp-batch-<name>",
                       description="Merge the pinned heads, in plan order, with `git merge --no-ff` into a fresh `batch/<name>` at "
                                   "%s in the worktree ../romp-batch-<name> (rerere on). Refuses while another `%s/batch/*` "
                                   "exists: the branch is the mutex. A conflicting member is held back and its owner told, "
                                   "unless named by --resolve: then assemble stops with exit 3, you resolve per hunk in the "
                                   "worktree and `git add`, and `--continue --reviewed '<note>'` commits it (only the "
                                   "conflicted files may differ from the clean merge) or `--abort` drops it. Re-running "
                                   "rebuilds the branch from the current %s." % (remote_main(), REMOTE, remote_main()))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--without", type=int, action="append", metavar="N", help="leave N (and its dependents) out")
    p.add_argument("--resolve", type=int, action="append", metavar="N", help="stop at N's conflict for a hand resolution")
    p.add_argument("--repin", action="append", metavar="N|all", help="re-read N's head, title, labels, trailer and base from GitHub before assembling")
    p.add_argument("--continue", dest="cont", action="store_true", help="commit the resolved merge and go on")
    p.add_argument("--abort", action="store_true", help="abandon the stopped resolution; hold that member back")
    p.add_argument("--reviewed", metavar="NOTE", help="with --continue: who reviewed the resolution and the verdict")
    p.add_argument("--merge-main", action="store_true",
                   help="merge %s into the assembled batch instead of rebuilding (when %s moved); a conflict stops like --resolve" % (remote_main(), MAIN))
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (held-back PRs)")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_assemble)

    p = sub.add_parser("verify", help="provenance, pinned heads, bases, ledger, sweep, own CI",
                       description="The gate `land` re-runs. Provenance: every commit the batch adds is a member merge, a `batch:` "
                                   "commit or a merge of %s, and every merge equals the clean merge of its parents unless it "
                                   "carries a recorded resolution (then only the resolution's files may differ). Every member's "
                                   "live head still equals the pinned SHA, is OPEN, and has its base in the batch or in %s. "
                                   "The ledger check runs on the branch's tree. The sweep must be recorded at the current head."
                                   % (remote_main(), MAIN))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--sweep", metavar="TEXT", help="record the full sweep's counts at the current batch head")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("summarize", help="create or update the batch PR; comment on each member",
                       description="Render the body (first block, Read these first, members table, ledger entries, held back, "
                                   "conflict resolutions, assembly log) and create or edit the batch PR against %s with the "
                                   "`%s` label; comment `in batch <name> at <sha>` on each member once per head." % (MAIN, LABEL_BATCH))
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--print-only", action="store_true", help="print the body; touch nothing")
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("pull", help="rebuild without N and its dependents, push, re-summarize",
                       description="Take member N out (the maintainer's `pull #N`): rebuild the branch without it and its "
                                   "dependents (unless N already merged into %s, then they stay), force-push with lease, "
                                   "regenerate the body, and comment on N and on each dropped dependent." % MAIN)
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("n", type=int, help="the member PR's number")
    p.add_argument("--reason", metavar="TEXT", help="why, for the comment on N (default: the maintainer asked)")
    p.add_argument("--no-push", action="store_true", help="rebuild only; do not push or re-summarize")
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY)
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("land", help="verify, merge the batch PR with a merge commit, finish",
                       description="On the maintainer's word for this batch: run verify again (the last drift check), retarget "
                                   "stacked members to %s, `gh pr merge --merge --match-head-commit <verified sha>`, then run "
                                   "finish. Never squash or rebase: that would leave every member open." % MAIN)
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--auto", action="store_true",
                   help="arm auto-merge instead (lands when the required checks pass; needs the repository's \"Allow auto-merge\" "
                        "setting and a rule on %s that gates a merge: a ruleset rule such as required_status_checks or "
                        "pull_request, or classic protection with required checks or reviews)" % MAIN)
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (passed on to finish)")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_land)

    p = sub.add_parser("finish", help="after the merge: member states, retargets, branch deletion, orphans",
                       description="After the batch PR merged (by land or by hand): confirm each member reads MERGED and comment "
                                   "on any that does not, retarget still-open dependents to %s, delete the member branches and "
                                   "`batch/<name>`, remove the worktree, run scripts/pr-orphans.sh, report one line. Safe to "
                                   "re-run: what it observed the first time is kept." % MAIN)
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("--no-notify", action="store_true", help=HELP_NO_NOTIFY + " (members that did not read merged)")
    p.add_argument("--keep-worktree", action="store_true", help="leave ../romp-batch-<name> and the local batch branch in place")
    p.add_argument("--no-fetch", action="store_true", help=HELP_NO_FETCH)
    p.set_defaults(func=cmd_finish)

    p = sub.add_parser("bisect", help="first-parent bisect over the batch chain; names the member",
                       description="When the batch's CI is red: run the command at the tip and at the base first (a command that "
                                   "never fails, or fails everywhere, is reported instead of a member), then `git bisect "
                                   "--first-parent` over the member merges with `git bisect run`, and name the member to pull.")
    p.add_argument("name", help=HELP_NAME)
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- <command that fails on the bad tree>, run in the batch worktree")
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
