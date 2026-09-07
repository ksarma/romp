#!/usr/bin/env python3
"""A fake GitHub CLI for the batch-tool tests (tests/test_batch_tool.py).

Installed on PATH as `gh`. Its GitHub is a JSON file (FAKE_GH_STATE) plus a local bare repository
(the fixture's `origin`): PR metadata lives in the file, and every head SHA is read live from the
bare repository's refs, so a branch that moves after the plan pinned it moves here too. Every call
is appended to FAKE_GH_LOG, one JSON line per argv, so a test can assert what the tool asked for.

What it models of GitHub, and what it assumes (each assumption is the plan's "to verify" and is
named so the fake does not pass as evidence):
  - `pr merge N --merge --match-head-commit SHA` performs a real merge commit in the bare
    repository (refusing when SHA is not the live head, or when squash or rebase is asked for and
    the settings forbid it), marks N MERGED, and then marks MERGED every open PR against the same
    base whose head is now reachable from it (GitHub's documented "indirect merge" marking; the
    merge commit recorded for such a PR is the merge that made it reachable, an assumption).
  - With deleteBranchOnMerge the head branch of the DIRECTLY merged PR is deleted and open PRs
    based on it are retargeted to the merged PR's base (documented). The head branches of
    indirectly merged PRs are NOT deleted unless FAKE_GH_DELETE_INDIRECT=1 (undocumented; the
    tool deletes them itself and records which case it met).
  - `--auto` is accepted and, with no ruleset, merges at once (nothing is required, so nothing
    waits); with a ruleset it also merges at once, which stands in for "when the checks pass".
  - `--jq` is supported for the expressions the scripts use, and refused otherwise.
  - A MERGED or CLOSED PR keeps the head SHA it had at that moment, as GitHub reports it; only an
    OPEN PR's head follows its branch (a branch name reused after a merge is a different PR).
  - `api` serves the repository (`repos/{owner}/{repo}`: `allow_auto_merge` from the state's
    `repo.allowAutoMerge`, off by default like the fork's, and the merge settings), the rulesets
    list, the rules that apply to main (`rules/branches/main`, the same rows), classic protection
    (`branches/main/protection`: the `protection` object, or the 404 GitHub returns when there is
    none), and `-X DELETE .../git/refs/heads/<ref>` (deletes the branch and retargets its
    dependents to main, as GitHub does).
  - FAKE_GH_FAIL (`|`-separated argv prefixes) makes the matching calls fail with an HTTP 502, so
    a test can see what the tool does when a call does not land. `fail` in the state maps an
    endpoint (`rules`, `protection`) to a gh error line the fake prints and exits 1 with, the way a
    5xx or an auth failure (an HTTP 403 on protection) would; the 404 for an unprotected branch
    needs no injection.

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
    """An OPEN PR's head follows its branch; a MERGED or CLOSED PR keeps the head it had at that
    moment (GitHub reports the SHA as of the merge), so a branch name reused after the merge does
    not move the old PR's head. A closed PR with no recorded head reads the branch once."""
    if pr.get("state", "OPEN") != "OPEN" and pr.get("headRefOid"):
        return pr["headRefOid"]
    proc = git(state, "rev-parse", "--verify", "--quiet", "refs/heads/" + pr["headRefName"], check=False)
    if proc.returncode == 0:
        pr["headRefOid"] = proc.stdout.strip()
    return pr.get("headRefOid") or "0" * 40


def rollup_for(pr):
    """A CheckRun rollup in the shape `gh pr view --json statusCheckRollup` returns."""
    checks = pr.get("checks")
    if not checks:
        return []
    if checks == "pending":
        return [{"__typename": "CheckRun", "name": "Python 3.13 (ubuntu-latest)", "status": "IN_PROGRESS", "conclusion": None}]
    return [{"__typename": "CheckRun", "name": "Python 3.13 (ubuntu-latest)", "status": "COMPLETED",
             "conclusion": "SUCCESS" if checks == "success" else "FAILURE"}]


def project(state, pr, fields):
    live_head(state, pr)
    out = {}
    for f in fields:
        if f == "labels":
            out[f] = [{"name": l} for l in pr.get("labels", [])]
        elif f == "statusCheckRollup":
            out[f] = rollup_for(pr)
        elif f == "mergeCommit":
            out[f] = {"oid": pr["mergeCommit"]} if pr.get("mergeCommit") else None
        elif f == "url":
            out[f] = pr.get("url") or "https://example.invalid/pull/%d" % pr["number"]
        elif f == "isDraft":
            out[f] = bool(pr.get("isDraft"))
        elif f == "mergeable":
            out[f] = pr.get("mergeable", "MERGEABLE")
        elif f == "state":
            out[f] = pr.get("state", "OPEN")
        else:
            out[f] = pr.get(f)
    return out


def opts(argv, flags_with_value):
    """A tiny option splitter: {flag: [values]} for the flags named, positionals in '_'."""
    got = {"_": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in flags_with_value:
            got.setdefault(a, []).append(argv[i + 1] if i + 1 < len(argv) else "")
            i += 2
        elif a.startswith("--") and "=" in a and a.split("=", 1)[0] in flags_with_value:
            k, v = a.split("=", 1)
            got.setdefault(k, []).append(v)
            i += 1
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
    die("unsupported --jq expression %r" % expr)


def pr_list(state, argv):
    o = opts(argv, {"--state", "--head", "--base", "--label", "--limit", "--json", "--jq", "-L", "-s", "-H", "-B", "-l"})
    want_state = (o.get("--state") or o.get("-s") or ["open"])[0].upper()
    rows = []
    for pr in sorted(state["prs"].values(), key=lambda p: -p["number"]):
        st = pr.get("state", "OPEN")
        if want_state == "OPEN" and st != "OPEN":
            continue
        if want_state == "MERGED" and st != "MERGED":
            continue
        if want_state == "CLOSED" and st not in ("CLOSED", "MERGED"):
            continue
        for flag, key in (("--head", "headRefName"), ("-H", "headRefName"), ("--base", "baseRefName"), ("-B", "baseRefName")):
            if o.get(flag) and pr.get(key) != o[flag][0]:
                break
        else:
            if (o.get("--label") or o.get("-l")) and (o.get("--label") or o.get("-l"))[0] not in pr.get("labels", []):
                continue
            rows.append(pr)
    limit = int((o.get("--limit") or o.get("-L") or ["30"])[0])
    rows = rows[:limit]
    fields = (o.get("--json") or ["number"])[0].split(",")
    out = [project(state, pr, fields) for pr in rows]
    if o.get("--jq"):
        print(apply_jq(out, o["--jq"][0]))
    else:
        print(json.dumps(out))


def get_pr(state, n):
    pr = state["prs"].get(str(n))
    if not pr:
        die("no pull request #%s" % n)
    return pr


def pr_view(state, argv):
    o = opts(argv, {"--json", "--jq", "--repo", "-R"})
    pr = get_pr(state, o["_"][0])
    fields = (o.get("--json") or ["number,title,state"])[0].split(",")
    print(json.dumps(project(state, pr, fields)))


def read_body(o):
    if o.get("--body"):
        return o["--body"][0]
    if o.get("-b"):
        return o["-b"][0]
    if o.get("--body-file") or o.get("-F"):
        p = (o.get("--body-file") or o.get("-F"))[0]
        return sys.stdin.read() if p == "-" else open(p).read()
    return None


def pr_edit(state, argv):
    o = opts(argv, {"--base", "-B", "--add-label", "--remove-label", "--title", "-t", "--body", "-b", "--body-file", "-F"})
    pr = get_pr(state, o["_"][0])
    if o.get("--base") or o.get("-B"):
        pr["baseRefName"] = (o.get("--base") or o.get("-B"))[0]
    for l in o.get("--add-label", []):
        if l not in pr.setdefault("labels", []):
            pr["labels"].append(l)
    for l in o.get("--remove-label", []):
        if l in pr.get("labels", []):
            pr["labels"].remove(l)
    if o.get("--title") or o.get("-t"):
        pr["title"] = (o.get("--title") or o.get("-t"))[0]
    body = read_body(o)
    if body is not None:
        pr["body"] = body
    save(state)


def pr_create(state, argv):
    o = opts(argv, {"--base", "-B", "--head", "-H", "--title", "-t", "--label", "-l", "--body", "-b", "--body-file", "-F"})
    n = state.get("next_number", 900)
    state["next_number"] = n + 1
    head = (o.get("--head") or o.get("-H") or [""])[0]
    if git(state, "rev-parse", "--verify", "--quiet", "refs/heads/" + head, check=False).returncode != 0:
        die("head branch %r is not on origin" % head)
    pr = {"number": n, "title": (o.get("--title") or o.get("-t") or ["untitled"])[0], "body": read_body(o) or "",
          "labels": list(o.get("--label", []) + o.get("-l", [])), "baseRefName": (o.get("--base") or o.get("-B") or ["main"])[0],
          "headRefName": head, "isDraft": False, "state": "OPEN", "mergeCommit": None, "mergedAt": None,
          "mergeable": "MERGEABLE", "checks": "success", "comments": [], "url": "https://example.invalid/pull/%d" % n}
    state["prs"][str(n)] = pr
    save(state)
    print(pr["url"])


def pr_comment(state, argv):
    o = opts(argv, {"--body", "-b", "--body-file", "-F"})
    pr = get_pr(state, o["_"][0])
    pr.setdefault("comments", []).append(read_body(o) or "")
    save(state)


def mark_indirect(state, base, new_tip):
    """GitHub's indirect-merge marking: every open PR against `base` whose head is now reachable
    from the base branch reads MERGED. The merge commit it records is the one that made the head
    reachable (an assumption of this fake, not a documented fact)."""
    marked = []
    for pr in state["prs"].values():
        if pr.get("state") != "OPEN" or pr.get("baseRefName") != base:
            continue
        head = live_head(state, pr)
        if git(state, "merge-base", "--is-ancestor", head, new_tip, check=False).returncode == 0:
            pr["state"] = "MERGED"
            pr["mergeCommit"] = new_tip
            pr["mergedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            marked.append(pr)
    return marked


def delete_branch_and_retarget(state, branch, new_base):
    git(state, "update-ref", "-d", "refs/heads/" + branch, check=False)
    for pr in state["prs"].values():
        if pr.get("state") == "OPEN" and pr.get("baseRefName") == branch:
            pr["baseRefName"] = new_base


def pr_merge(state, argv):
    o = opts(argv, {"--match-head-commit", "--subject", "-t", "--body", "-b", "--body-file", "-F", "--author-email", "-A"})
    pr = get_pr(state, o["_"][0])
    repo = state.get("repo", {})
    if o.get("--squash") or o.get("-s"):
        if not repo.get("squashMergeAllowed", True):
            die("Squash merges are not allowed on this repository")
        die("this fake does not squash")
    if o.get("--rebase") or o.get("-r"):
        if not repo.get("rebaseMergeAllowed", True):
            die("Rebase merges are not allowed on this repository")
        die("this fake does not rebase")
    if not repo.get("mergeCommitAllowed", True):
        die("Merge commits are not allowed on this repository")
    if pr.get("state") != "OPEN":
        die("#%d is %s" % (pr["number"], pr.get("state")))
    head = live_head(state, pr)
    if o.get("--match-head-commit") and o["--match-head-commit"][0] != head:
        die("head commit %s does not match %s" % (head, o["--match-head-commit"][0]))
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
    indirect = mark_indirect(state, base, commit)
    if repo.get("deleteBranchOnMerge") or o.get("--delete-branch") or o.get("-d"):
        delete_branch_and_retarget(state, pr["headRefName"], base)
        if os.environ.get("FAKE_GH_DELETE_INDIRECT") == "1":
            for ipr in indirect:
                delete_branch_and_retarget(state, ipr["headRefName"], base)
    state.setdefault("merges", []).append({"pr": pr["number"], "auto": bool(o.get("--auto")), "commit": commit,
                                           "indirect": [p["number"] for p in indirect]})
    save(state)
    print("Merged pull request #%d" % pr["number"])


def repo_view(state, argv):
    o = opts(argv, {"--json", "--jq"})
    fields = (o.get("--json") or [""])[0].split(",")
    repo = state.get("repo", {})
    print(json.dumps({f: repo.get(f) for f in fields if f}))


def api(state, argv):
    """Three read-only endpoints. `rulesets` is the repository-wide list; `rules/branches/<b>` the
    rules that apply to branch b (this fake serves the same `rulesets` rows for main, none for any
    other branch); `branches/<b>/protection` is classic branch protection: the `protection` object
    when set, else GitHub's 404 ("Branch not protected") as gh reports it, exit 1."""
    o = opts(argv, {"--jq", "-q", "--method", "-X", "-f", "-F"})
    path = o["_"][0]
    method = (o.get("--method") or o.get("-X") or ["GET"])[0].upper()
    if method == "DELETE" and "/git/refs/heads/" in path:
        ref = path.split("/git/refs/heads/", 1)[1]
        if git(state, "rev-parse", "--verify", "--quiet", "refs/heads/" + ref, check=False).returncode != 0:
            print(json.dumps({"message": "Reference does not exist", "status": "422"}))
            sys.stderr.write("gh: Reference does not exist (HTTP 422)\n")
            sys.exit(1)
        delete_branch_and_retarget(state, ref, "main")
        save(state)
        return
    if path in ("repos/{owner}/{repo}", "repos/{owner}/{repo}/"):
        repo = state.get("repo", {})
        info = {"allow_auto_merge": bool(repo.get("allowAutoMerge", False)),
                "allow_merge_commit": repo.get("mergeCommitAllowed", True),
                "allow_squash_merge": repo.get("squashMergeAllowed", True),
                "allow_rebase_merge": repo.get("rebaseMergeAllowed", True),
                "delete_branch_on_merge": bool(repo.get("deleteBranchOnMerge", False))}
        if o.get("--jq"):
            expr = o["--jq"][0]
            if expr.startswith(".") and expr[1:] in info:
                print(json.dumps(info[expr[1:]]))
                return
            die("unsupported --jq expression %r" % expr)
        print(json.dumps(info))
        return
    fail = state.get("fail") or {}
    if path.endswith("/rulesets") or "/rules/branches/" in path:
        if fail.get("rules"):
            die(fail["rules"], code=1)
        rows = state.get("rulesets", []) if (path.endswith("/rulesets") or path.endswith("/rules/branches/main")) else []
        if o.get("--jq"):
            print(apply_jq(rows, o["--jq"][0]))
        else:
            print(json.dumps(rows))
        return
    if "/branches/" in path and path.endswith("/protection"):
        if fail.get("protection"):
            die(fail["protection"], code=1)
        prot = state.get("protection")
        if prot:
            print(json.dumps(prot))
            return
        print(json.dumps({"message": "Branch not protected", "status": "404"}))
        sys.stderr.write("gh: Branch not protected (HTTP 404)\n")
        sys.exit(1)
    die("unsupported api path %s" % path)


def maybe_fail(argv):
    """Failure injection: FAKE_GH_FAIL holds `|`-separated argv prefixes (words separated by spaces);
    a call that starts with one of them exits 1 with an HTTP-502-shaped error, the way a flaky gh
    would, so tests can see what the tool does when a call does not land."""
    spec = os.environ.get("FAKE_GH_FAIL")
    if not spec:
        return
    for prefix in spec.split("|"):
        words = prefix.split()
        if words and argv[:len(words)] == words:
            sys.stderr.write("fake gh: HTTP 502: Bad Gateway (FAKE_GH_FAIL matched %r)\n" % prefix)
            sys.exit(1)


def run_list(state, argv):
    print(json.dumps([{"url": "https://example.invalid/actions/runs/1", "status": "completed", "conclusion": "success"}]))


def main(argv):
    log_call(argv)
    maybe_fail(argv)
    state = load()
    if argv[:2] == ["pr", "list"]:
        pr_list(state, argv[2:])
    elif argv[:2] == ["pr", "view"]:
        pr_view(state, argv[2:])
    elif argv[:2] == ["pr", "edit"]:
        pr_edit(state, argv[2:])
    elif argv[:2] == ["pr", "create"]:
        pr_create(state, argv[2:])
    elif argv[:2] == ["pr", "comment"]:
        pr_comment(state, argv[2:])
    elif argv[:2] == ["pr", "merge"]:
        pr_merge(state, argv[2:])
    elif argv[:2] == ["repo", "view"]:
        repo_view(state, argv[2:])
    elif argv[:1] == ["api"]:
        api(state, argv[1:])
    elif argv[:2] == ["run", "list"]:
        run_list(state, argv[2:])
    elif argv[:2] == ["label", "create"]:
        pass
    else:
        die("unsupported command: %s" % " ".join(argv), code=2)


if __name__ == "__main__":
    main(sys.argv[1:])
