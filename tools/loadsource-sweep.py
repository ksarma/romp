#!/usr/bin/env python3
"""Rewrite tests/*.py from `SourceFileLoader(name, path).load_module()` to `load_source(name, path)`.

load_module() is removed in Python 3.15 (kernel/loadsource.py is the replacement; tests reach it as
`from romp_load import load_source`). This script converts every test module mechanically, so the
change can be regenerated instead of merged: run it again after another branch lands test files
written in the old idiom, and commit the result. It is idempotent, and a file it has already
converted is left alone. The isolation ratchet (tests/test_state_isolation_order.py) refuses the old
idiom, so a stale file fails the suite until this is re-run.

What it changes, per file, from the AST (never text inside a string or comment):
- every `X(<args>).load_module()` where X is a name bound by `from importlib.machinery import
  SourceFileLoader [as X]`, at any depth, becomes `load_source(<args>)`, arguments verbatim;
- an import of SourceFileLoader whose name is no longer used in code is dropped: a top-level import
  of only that name becomes `from romp_load import load_source`, one that imports other names too
  keeps them and gains that line after it, a nested (in-function) import is deleted;
- a module that converted a call and has no top-level `from romp_load import load_source` gets one,
  after the last top-level import that precedes its first load.
A name still used in code (a mock patching it, a loader built for another purpose) keeps its import.

Usage: tools/loadsource-sweep.py [--check] [paths...]. With no paths every tests/*.py is read
(romp_load.py, conftest.py and __init__.py excepted). --check rewrites nothing and exits 1 when a file
would change, which is how the ratchet can be run by hand. Exit 0 otherwise.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TESTS = os.path.join(ROOT, "tests")
SKIP = {"romp_load.py", "conftest.py", "__init__.py", "credential_patterns.py"}
IMPORT_LINE = "from romp_load import load_source"


def _byte_offset(line_starts, lineno, col):
    """ast positions are 1-based lines and UTF-8 byte columns."""
    return line_starts[lineno - 1] + col


def _line_starts(src_bytes):
    starts = [0]
    for i, b in enumerate(src_bytes):
        if b == 0x0A:
            starts.append(i + 1)
    return starts


def _aliases(tree):
    """(names bound to SourceFileLoader, the ImportFrom nodes that bind them)."""
    names, nodes = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "importlib.machinery":
            for a in node.names:
                if a.name == "SourceFileLoader":
                    names.add(a.asname or a.name)
                    nodes.append(node)
    return names, nodes


def _load_calls(tree, aliases):
    """Every `X(...).load_module()` call node, X an alias."""
    out = []
    for node in ast.walk(tree):
        f = node.func if isinstance(node, ast.Call) else None
        if (f is not None and not node.args and not node.keywords and isinstance(f, ast.Attribute)
                and f.attr == "load_module" and isinstance(f.value, ast.Call)
                and isinstance(f.value.func, ast.Name) and f.value.func.id in aliases):
            out.append(node)
    return out


def _names_in_code(tree, aliases):
    """Uses of the alias names as expressions (an ImportFrom binds through alias nodes, not Names,
    so the import statements themselves never count)."""
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in aliases:
            used.add(node.id)
    return used


def _has_top_level_import(tree):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "romp_load" and any(
                a.name == "load_source" for a in node.names):
            return True
    return False


def convert(src):
    """The converted source, or `src` unchanged when nothing applies."""
    tree = ast.parse(src)
    aliases, import_nodes = _aliases(tree)
    if not aliases:
        return src
    calls = _load_calls(tree, aliases)
    b = src.encode("utf-8")
    starts = _line_starts(b)
    edits = []                                   # (start_byte, end_byte, replacement bytes)
    for node in calls:
        inner = node.func.value                  # X(<args>)
        s = _byte_offset(starts, inner.func.lineno, inner.func.col_offset)
        args_start = _byte_offset(starts, inner.func.end_lineno, inner.func.end_col_offset)
        args_end = _byte_offset(starts, inner.end_lineno, inner.end_col_offset)
        e = _byte_offset(starts, node.end_lineno, node.end_col_offset)
        edits.append((s, e, b"load_source" + b[args_start:args_end]))
    if not edits:
        return src
    for s, e, rep in sorted(edits, reverse=True):
        b = b[:s] + rep + b[e:]
    src = b.decode("utf-8")
    # second pass, on the converted text: retire the imports whose names went out of use
    tree = ast.parse(src)
    aliases, import_nodes = _aliases(tree)
    used = _names_in_code(tree, aliases)
    lines = src.splitlines(keepends=True)
    top_level = {id(n) for n in tree.body}
    need_import = not _has_top_level_import(tree)
    line_edits = []                              # (first_line_index, last_line_index, replacement text)
    for node in import_nodes:
        keep = [a for a in node.names if not (a.name == "SourceFileLoader" and (a.asname or a.name) not in used)]
        if len(keep) == len(node.names):
            if id(node) in top_level and need_import:
                line_edits.append((node.end_lineno, node.end_lineno - 1, IMPORT_LINE + "\n"))   # insert after
                need_import = False
            continue
        indent = lines[node.lineno - 1][:len(lines[node.lineno - 1]) - len(lines[node.lineno - 1].lstrip())]
        if keep:
            text = indent + "from importlib.machinery import " + ", ".join(
                a.name + (" as " + a.asname if a.asname else "") for a in keep) + "\n"
            if id(node) in top_level and need_import:
                text += IMPORT_LINE + "\n"
                need_import = False
        elif id(node) in top_level and need_import:
            text = IMPORT_LINE + "\n"
            need_import = False
        else:
            text = ""
        line_edits.append((node.lineno - 1, node.end_lineno - 1, text))
    if need_import:
        # no top-level import statement was converted in place: add the line after the module's
        # leading import block
        last_import_end = 0
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                last_import_end = node.end_lineno
            elif last_import_end:
                break
        line_edits.append((last_import_end, last_import_end - 1, IMPORT_LINE + "\n"))
        need_import = False
    for first, last, text in sorted(line_edits, key=lambda t: t[0], reverse=True):
        lines[first:last + 1] = [text] if text else []
    return "".join(lines)


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if a != "--check"]
    if not paths:
        paths = [os.path.join(TESTS, fn) for fn in sorted(os.listdir(TESTS))
                 if fn.endswith(".py") and fn not in SKIP]
    changed = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            src = f.read()
        out = convert(src)
        if out != src:
            changed.append(p)
            if not check:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(out)
    for p in changed:
        print(("would rewrite " if check else "rewrote ") + os.path.relpath(p, ROOT))
    print("%d file(s) %s" % (len(changed), "to rewrite" if check else "rewritten"))
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
