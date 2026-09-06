#!/usr/bin/env python3
"""A fake GitHub CLI for the land.sh tests (tests/test_land_sh.py).

Installed on PATH as `gh`. Its GitHub is a JSON file (FAKE_GH_STATE) plus a local bare repository
(the fixture's `origin`): PR metadata lives in the file, head SHAs are read live from the bare
repository's refs, and a merge is a real merge commit there, so pr-orphans.sh's ancestry check runs
against real history. Every call is appended to FAKE_GH_LOG, one JSON line per argv.

It models the gh and GitHub behaviors land.sh's rules rest on, so a test can show each rule
biting; each is named here so the fake is not mistaken for evidence about GitHub:
  - `pr merge --delete-branch` also deletes the LOCAL branch of that name in the caller's clone,
    the way gh does (gh v2.97.0 merge.go: the local delete runs whenever the branch exists locally
    and --repo was not given), and fails after the remote merge when git refuses (the branch is
    checked out in a worktree). This is the behavior land.sh must never trigger.
  - `--auto` when the PR's checks are pending: rejected unless the repository's allow_auto_merge is
    on (GitHub: auto-merge must be enabled for the repository); with it on, the PR is armed and
    stays OPEN. A PR whose checks passed merges at once, --auto or not (gh drops --auto for an
    immediately mergeable PR).
  - Squash and rebase are refused when the settings forbid them; merge commits likewise.
  - With deleteBranchOnMerge the head branch of the merged PR is deleted and open PRs based on it
    are retargeted to the merged PR's base (documented). Indirect-merge marking: open PRs against
    the same base whose head is now reachable read MERGED.
  - `api repos/{owner}/{repo}` answers allow_auto_merge; `.../rules/branches/<b>` the rules on that
    branch; `.../branches/<b>/protection` 404s unless `protection` is set; `-X DELETE
    .../git/refs/heads/<b>` deletes the remote ref. `--jq` covers the expressions the scripts use.

Synthetic data only: PR numbers, titles and branches are the tests' inventions.
"""
import datetime
import json
import os
import subprocess
import sys


def die(msg, code=1):
    sys.stderr.write("fake gh: %s\n" % msg)
    sys.exit(code)


def load():
    with open(os.environ["FAKE_GH_STATE"]) as f:
        return json.load(f)


def save(state):
    tmp = os.environ["FAKE_GH_STATE"] + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    os.replace(tmp, os.environ["FAKE_GH_STATE"])


def log_call(argv):
    p = os.environ.get("FAKE_GH_LOG")
    if p:
        with open(p, "a") as f:
            f.write(json.dumps(argv) + "\n")


def git(state, *args, check=True):
    proc = subprocess.run(["git", "-C", state["bare"], *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        die("git %s: %s" % (" ".join(args), proc.stderr.strip()))
    return proc


def live_head(state, pr):
    proc = git(state, "rev-parse", "--verify", "--quiet", "refs/heads/" + pr["headRefName"], check=False)
    if proc.returncode == 0:
        pr["headRefOid"] = proc.stdout.strip()
    return pr.get("headRefOid") or "0" * 40


def project(state, pr, fields):
    live_head(state, pr)
    out = {}
    for f in fields:
        if f == "mergeCommit":
            out[f] = {"oid": pr["mergeCommit"]} if pr.get("mergeCommit") else None
        elif f == "isDraft":
            out[f] = bool(pr.get("isDraft"))
        elif f == "state":
            out[f] = pr.get("state", "OPEN")
        else:
            out[f] = pr.get(f)
    return out


def opts(argv, flags_with_value):
    got = {"_": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in flags_with_value:
            got.setdefault(a, []).append(argv[i + 1] if i + 1 < len(argv) else "")
            i += 2
        elif a.startswith("-"):
            got.setdefault(a, []).append(True)
            i += 1
        else:
            got["_"].append(a)
            i += 1
    return got


def apply_jq(rows, expr):
    if expr == ".[] | [.number, (.mergeCommit.oid // \"none\"), .baseRefName] | @tsv":
        return "\n".join("%d\t%s\t%s" % (r["number"], (r.get("mergeCommit") or {}).get("oid") or "none", r["baseRefName"]) for r in rows)
    if expr == ".[0].number":
        return str(rows[0]["number"]) if rows else "null"
    if expr == "length":
        return str(len(rows))
    if expr.startswith(".") and "." not in expr[1:] and isinstance(rows, dict):
        v = rows.get(expr[1:])
        return json.dumps(v)
    die("unsupported --jq expression %r" % expr)


def get_pr(state, n):
    pr = state["prs"].get(str(n))
    if not pr:
        die("no pull request #%s" % n)
    return pr


def pr_list(state, argv):
    o = opts(argv, {"--state", "--head", "--base", "--limit", "--json", "--jq"})
    want = (o.get("--state") or ["open"])[0].upper()
    rows = []
    for pr in sorted(state["prs"].values(), key=lambda p: -p["number"]):
        st = pr.get("state", "OPEN")
        if want == "OPEN" and st != "OPEN":
            continue
        if want == "MERGED" and st != "MERGED":
            continue
        if want == "CLOSED" and st not in ("CLOSED", "MERGED"):
            continue
        if o.get("--head") and pr.get("headRefName") != o["--head"][0]:
            continue
        if o.get("--base") and pr.get("baseRefName") != o["--base"][0]:
            continue
        rows.append(pr)
    rows = rows[:int((o.get("--limit") or ["30"])[0])]
    fields = (o.get("--json") or ["number"])[0].split(",")
    out = [project(state, pr, fields) for pr in rows]
    print(apply_jq(out, o["--jq"][0]) if o.get("--jq") else json.dumps(out))


def pr_view(state, argv):
    o = opts(argv, {"--json", "--jq"})
    pr = get_pr(state, o["_"][0])
    fields = (o.get("--json") or ["number,title,state"])[0].split(",")
    out = project(state, pr, fields)
    print(apply_jq(out, o["--jq"][0]) if o.get("--jq") else json.dumps(out))


def mark_indirect(state, base, new_tip):
    for pr in state["prs"].values():
        if pr.get("state") != "OPEN" or pr.get("baseRefName") != base:
            continue
        head = live_head(state, pr)
        if git(state, "merge-base", "--is-ancestor", head, new_tip, check=False).returncode == 0:
            pr["state"] = "MERGED"
            pr["mergeCommit"] = new_tip
            pr["mergedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()


def delete_remote_branch(state, branch, new_base):
    git(state, "update-ref", "-d", "refs/heads/" + branch, check=False)
    state.setdefault("deleted_refs", []).append(branch)
    for pr in state["prs"].values():
        if pr.get("state") == "OPEN" and pr.get("baseRefName") == branch:
            pr["baseRefName"] = new_base


def delete_local_branch(head):
    """What gh does after the remote merge when --delete-branch is given: `git branch -D <head>` in
    the caller's clone if a local branch of that name exists. Fails the command when git refuses."""
    exists = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "refs/heads/" + head],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if exists.returncode != 0:
        return
    proc = subprocess.run(["git", "branch", "-D", head], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        die("failed to delete local branch %s: %s" % (head, proc.stderr.strip()))


def pr_merge(state, argv):
    o = opts(argv, {"--match-head-commit", "--subject", "-t", "--body", "-b"})
    pr = get_pr(state, o["_"][0])
    repo = state.get("repo", {})
    if o.get("--squash") or o.get("-s"):
        die("Squash merges are not allowed on this repository" if not repo.get("squashMergeAllowed", True) else "this fake does not squash")
    if o.get("--rebase") or o.get("-r"):
        die("Rebase merges are not allowed on this repository" if not repo.get("rebaseMergeAllowed", True) else "this fake does not rebase")
    if not repo.get("mergeCommitAllowed", True):
        die("Merge commits are not allowed on this repository")
    if pr.get("state") != "OPEN":
        die("#%d is %s" % (pr["number"], pr.get("state")))
    head = live_head(state, pr)
    if o.get("--match-head-commit") and o["--match-head-commit"][0] != head:
        die("head commit %s does not match %s" % (head, o["--match-head-commit"][0]))
    if o.get("--auto") and pr.get("checks") == "pending":
        if not repo.get("allow_auto_merge"):
            die("Auto-merge is not allowed for this repository")
        pr["autoMerge"] = True
        save(state)
        print("Pull request #%d will be automatically merged when all requirements are met" % pr["number"])
        return
    base = pr["baseRefName"]
    base_tip = git(state, "rev-parse", "refs/heads/" + base).stdout.strip()
    mt = git(state, "merge-tree", "--write-tree", "--no-messages", base_tip, head, check=False)
    if mt.returncode != 0:
        die("#%d is not mergeable (conflicts)" % pr["number"])
    tree = mt.stdout.split()[0]
    env = dict(os.environ, GIT_AUTHOR_NAME="fake github", GIT_AUTHOR_EMAIL="noreply@example.invalid",
               GIT_COMMITTER_NAME="fake github", GIT_COMMITTER_EMAIL="noreply@example.invalid")
    commit = subprocess.run(["git", "-C", state["bare"], "commit-tree", tree, "-p", base_tip, "-p", head, "-m",
                             "Merge pull request #%d from owner/%s" % (pr["number"], pr["headRefName"])],
                            env=env, text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
    git(state, "update-ref", "refs/heads/" + base, commit, base_tip)
    pr["state"] = "MERGED"
    pr["mergeCommit"] = commit
    pr["mergedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    mark_indirect(state, base, commit)
    if repo.get("deleteBranchOnMerge") or o.get("--delete-branch") or o.get("-d"):
        delete_remote_branch(state, pr["headRefName"], base)
    state.setdefault("merges", []).append({"pr": pr["number"], "auto": bool(o.get("--auto")), "commit": commit})
    save(state)
    print("Merged pull request #%d" % pr["number"])
    if o.get("--delete-branch") or o.get("-d"):
        delete_local_branch(pr["headRefName"])


def repo_view(state, argv):
    o = opts(argv, {"--json", "--jq"})
    fields = (o.get("--json") or [""])[0].split(",")
    repo = state.get("repo", {})
    print(json.dumps({f: repo.get(f) for f in fields if f}))


def api(state, argv):
    o = opts(argv, {"--jq", "-q", "--method", "-X", "-f", "-F", "-H"})
    path = o["_"][0]
    method = (o.get("-X") or o.get("--method") or ["GET"])[0].upper()
    jq = (o.get("--jq") or [None])[0]
    if method == "DELETE" and "/git/refs/heads/" in path:
        branch = path.split("/git/refs/heads/", 1)[1]
        if git(state, "rev-parse", "--verify", "--quiet", "refs/heads/" + branch, check=False).returncode != 0:
            die("Reference does not exist (HTTP 422)", code=1)
        delete_remote_branch(state, branch, "main")
        save(state)
        return
    if path.endswith("/rulesets") or "/rules/branches/" in path:
        rows = state.get("rules", [])
        print(apply_jq(rows, jq) if jq else json.dumps(rows))
        return
    if "/branches/" in path and path.endswith("/protection"):
        if state.get("protection"):
            print(json.dumps({"required_status_checks": {"contexts": ["ci"]}}))
            return
        die("Branch not protected (HTTP 404)", code=1)
    if path.rstrip("/") == "repos/{owner}/{repo}":
        repo = state.get("repo", {})
        out = {"allow_auto_merge": bool(repo.get("allow_auto_merge")),
               "delete_branch_on_merge": bool(repo.get("deleteBranchOnMerge")),
               "allow_merge_commit": repo.get("mergeCommitAllowed", True)}
        print(apply_jq(out, jq) if jq else json.dumps(out))
        return
    die("unsupported api path %s" % path)


def main(argv):
    log_call(argv)
    state = load()
    if argv[:2] == ["pr", "list"]:
        pr_list(state, argv[2:])
    elif argv[:2] == ["pr", "view"]:
        pr_view(state, argv[2:])
    elif argv[:2] == ["pr", "merge"]:
        pr_merge(state, argv[2:])
    elif argv[:2] == ["repo", "view"]:
        repo_view(state, argv[2:])
    elif argv[:1] == ["api"]:
        api(state, argv[1:])
    else:
        die("unsupported command: %s" % " ".join(argv), code=2)


if __name__ == "__main__":
    main(sys.argv[1:])
