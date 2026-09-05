"""Credential-shaped tokens, by pattern: the one list two places scrub with.

tests/conftest.py's report redaction removes every value seen in the process environment. That net
cannot see a token that never touched the environment (read from a file, printed by a child process,
typed into a fixture). This is the second net, independent of provenance: the key formats an
installation may meet, each as the prefix its provider fixed plus a long tail, and one generic rule
for a long token sitting where a value sits (after `=`, after `:` or `: `, after `Bearer `, inside
the quotes of a dict repr). The live session-move test scrubs a child's output with the same list
before a failure renders it (tests/test_session_move_live.py), so the two cannot drift.

The generic rule wants a digit in the token: a hex, base64 or random token of 32 characters has one
with near certainty, while a long identifier does not, so `testMethod=test_a_long_descriptive_name`
in a failure header stays readable. It still matches a synthetic uuid in a value position (36
characters of its alphabet), so a failing dict comparison may show the marker where a test's
placeholder sid was. That is the cost of catching a token of unknown format; the failure is still
readable.

Nothing here is a credential: the file holds prefixes and character classes only.
"""
import re

REDACTED = "[REDACTED-CREDENTIAL]"

# Where a value sits. Each alternative is one fixed-width lookbehind (the form Python's re accepts).
_VALUE_POSITION = r"(?:(?<=Bearer )|(?<==)|(?<==\")|(?<==')|(?<=: )|(?<=: \")|(?<=: ')|(?<=:))"

TOKEN_RE = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{20,}"                   # Anthropic API keys
    r"|sk-or-[A-Za-z0-9_\-]{20,}"                   # OpenRouter
    r"|sk-proj-[A-Za-z0-9_\-]{20,}"                 # OpenAI project keys
    r"|hf_[A-Za-z0-9]{20,}"                         # Hugging Face
    r"|AIza[A-Za-z0-9_\-]{30,}"                     # Google API keys
    r"|rpa_[A-Za-z0-9]{20,}"                        # RunPod
    r"|" + _VALUE_POSITION + r"(?=[A-Za-z0-9_\-]*\d)[A-Za-z0-9_\-]{32,}"   # any long token, with a digit, where a value sits
)


def scrub(text):
    """`text` with every match replaced by REDACTED; anything that is not a str comes back as is."""
    if not isinstance(text, str):
        return text
    return TOKEN_RE.sub(REDACTED, text)
