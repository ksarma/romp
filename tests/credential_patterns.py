"""Credential-shaped tokens, by pattern: the one list two places scrub with.

tests/conftest.py's report redaction removes every value seen in the process environment. That net
cannot see a token that never touched the environment (read from a file, printed by a child process,
typed into a fixture). This is the second net, independent of provenance: the key formats an
installation may meet, each as the prefix its provider fixed plus a long tail, and one generic rule
for a token of unknown format. The live session-move test scrubs a child's output with the same list
before a failure renders it (tests/test_session_move_live.py), so the two cannot drift.

The generic rule fires on a token of 24 characters or more that has a digit (a hex, base64 or random
token of that length has one with near certainty, while a long identifier does not, so
`testMethod=test_a_long_descriptive_name` in a failure header stays readable), and on one of 40 or
more that mixes upper and lower case with no digit. It applies where a value sits (after `=`, after
`:` or `: `, after `Bearer `, inside the quotes of a dict repr, as an element of a list, tuple or set
repr: after `[`, `(`, `{` or `, `), to a line that is one such token and nothing else, which is what
an apiKeyHelper's stdout is, and to pytest's own renderings of a failed comparison, which are value
positions too though nothing marks them as one: the `- <token>` and `+ <token>` lines of its diff
under the `E` marker (a container's elements spread over such lines included), the quoted operands
of `assert '<a>' == '<b>'` (and unittest's `'<a>' != '<b>'`), the haystack of `assert '<a>' in '<b>'`
(unittest's `'<a>' not found in '<b>'`), the `+  where '<a>' = f()` and `+  and   '<b>' = g()` lines
that explain an assert's operands, unittest's `Lists differ:` line and the quoted element lines under
it, and a `--showlocals` line `name = '<token>'`. Two shapes it leaves alone: the segment after a
pytest node id's `::` (a test's name, not a value), and a 40-hex git sha named as a commit
(`commit: <sha>`, `{'commit': '<sha>'}`) or sitting in a path or after an `@`. It still matches a
synthetic uuid in a value position and a test method name with a digit in it, so a failing dict
comparison may show the marker where a test's placeholder sid was. That is the cost of catching a
token of unknown format; the failure is still readable.

Nothing here is a credential: the file holds prefixes and character classes only.
"""
import re

REDACTED = "[REDACTED-CREDENTIAL]"

# Where a value sits. Each alternative is one fixed-width lookbehind (the form Python's re accepts). A
# colon counts only when it is not the second of a `::` pair: that pair separates a pytest node id's
# segments, and what follows it is a test's name. The second and third rows are pytest's own rendering
# of a failed comparison, where the token is a compared value and nothing else marks it: the quoted
# operands of `assert '<a>' == '<b>'` (unittest's `'<a>' != '<b>'`), a --showlocals line `name = '<a>'`,
# the `+  where '<a>' = f()` and `+  and   '<b>' = g()` lines that explain the operands, and the
# haystack of `assert '<a>' in '<b>'` (unittest's `'<a>' not found in '<b>'`). The fourth row is an
# element of a list, tuple or set repr (`['<a>', '<b>']`, `('<a>',)`, `{'<a>'}`): the first after the
# opening bracket, the rest after `, `. unittest's `Lists differ:` line is one such repr per side.
_VALUE_POSITION = (r"(?:(?<=Bearer )|(?<==)|(?<==\")|(?<==')|(?<=: )|(?<=: \")|(?<=: ')|(?<=[^:]:)"
                   r"|(?<== \")|(?<== ')|(?<=== \")|(?<=== ')|(?<=!= \")|(?<=!= ')|(?<=assert \")|(?<=assert ')"
                   r"|(?<=where \")|(?<=where ')|(?<=and   \")|(?<=and   ')|(?<=in \")|(?<=in ')"
                   r"|(?<=[\[({]\")|(?<=[\[({]')|(?<=, \")|(?<=, '))")
_TOKEN_CHARS = r"[A-Za-z0-9_\-]"
# A token of unknown format: 24 or more characters with a digit, or 40 or more mixing upper and lower case
_GENERIC = (r"(?:(?=" + _TOKEN_CHARS + r"*\d)" + _TOKEN_CHARS + r"{24,}"
            r"|(?=" + _TOKEN_CHARS + r"*[a-z])(?=" + _TOKEN_CHARS + r"*[A-Z])" + _TOKEN_CHARS + r"{40,})")

# pytest's diff of two compared values, one line per side: `E         - <a>` and `E         + <a>`, the
# token alone after the marker and the sign, or one element of a container repr that unittest's diff
# spreads over lines, quoted and closed by the repr's own punctuation (`E       -  '<a>']`,
# `E       +  '<a>',`). The prefix is captured (pfx) and kept, so the diff still reads as one; without
# the marker a `- <token>` line is a bullet in someone's captured output. unittest's `First differing
# element` lines render each element alone and quoted after the marker: `E       '<a>'`.
_DIFF_LINE = r"^(?P<pfx>E[ \t]+[-+][ \t]+['\"]?)" + _GENERIC + r"(?=['\"]?[\]),]*$)"
_QUOTED_LINE = r"^(?P<pfxq>E[ \t]+['\"])" + _GENERIC + r"(?=['\"]$)"

TOKEN_RE = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{20,}"                   # Anthropic API keys
    r"|sk-or-[A-Za-z0-9_\-]{20,}"                   # OpenRouter
    r"|sk-proj-[A-Za-z0-9_\-]{20,}"                 # OpenAI project keys
    r"|hf_[A-Za-z0-9]{20,}"                         # Hugging Face
    r"|AIza[A-Za-z0-9_\-]{30,}"                     # Google API keys
    r"|rpa_[A-Za-z0-9]{20,}"                        # RunPod
    r"|" + _VALUE_POSITION + _GENERIC +             # a token of unknown format where a value sits...
    r"|^" + _GENERIC + r"$"                         # ...or alone on its line (an apiKeyHelper's stdout)...
    r"|" + _DIFF_LINE +                             # ...or one side of pytest's diff of two compared values...
    r"|" + _QUOTED_LINE,                            # ...or unittest's quoted rendering of one differing element
    re.MULTILINE,
)

# A git sha (40 lowercase hex) is no credential when the text says what it is: named as a commit
# (`commit=<sha>`, `commit: <sha>`, `{'commit': '<sha>'}`), or sitting in a path or after an `@`. Under
# today's value positions only the commit form can precede a match (a token after `/` or `@` is in no
# value position); the other two guard the rule should a position be added.
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
_GIT_SHA_CONTEXT = re.compile(r"(?:commit\W{0,4}|/|@)$", re.IGNORECASE)


def _is_git_sha_in_context(text, m):
    tok = m.group(0)
    return bool(_GIT_SHA_RE.fullmatch(tok)) and bool(_GIT_SHA_CONTEXT.search(text[max(0, m.start() - 12):m.start()]))


def scrub(text):
    """`text` with every match replaced by REDACTED (a diff line keeps its marker and sign, a quoted
    element line its marker and quotes); anything that is not a str comes back as is."""
    if not isinstance(text, str):
        return text

    def one(m):
        if _is_git_sha_in_context(text, m):
            return m.group(0)
        return (m.group("pfx") or m.group("pfxq") or "") + REDACTED
    return TOKEN_RE.sub(one, text)
