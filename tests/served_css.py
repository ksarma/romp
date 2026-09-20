#!/usr/bin/env python3
"""Parsed views of a served page, for pins that read the ELEMENT or the PARSED RULE they pin rather than page text.

A substring assertion over a served page is satisfied by a comment that spells the same token (D1 round 1, 2026-09-19:
three viewport-meta pins were satisfied by a served comment after the meta had lost the token), and a census that
substring-searches declarations misses members written through a custom-property indirection, with whitespace inside
the var() call, under a split selector, inside a style element carrying an attribute, or re-topped through the inset
shorthand (D1 round 2, 2026-09-19). This module is the instrument both kinds of pin read instead.

Style rules: `rules(html)` parses every <style> element that is live markup (any attributes; a style or script element
inside an HTML comment is comment text, not an element, round 5, 2026-09-20; the number of `<style` tag openings outside
script elements and HTML comments must equal the number of elements consumed, or the parse refuses), strips its comments,
and brace-matches it into Rule(index, at, selector, declarations, decls): `at` is the tuple of enclosing at-rule preludes
(an @media query, a @supports condition), `declarations` the block's raw text, `decls` its (property, value) pairs split
at ; outside parentheses and quotes; a statement at-rule (@import, @charset, @namespace, `@layer name;`: an at-prelude
ended by ; with no block) is consumed and dropped, never folded into the next rule's prelude (round 5). Keywords and
function names are compared case-insensitively, as CSS reads them (`position:FIXED`, `VAR(--app-h)`, `! IMPORTANT`).
Custom properties: `closure(rules, "--app-h")` is the fixed point of the names whose declared value names var(--app-h) or
a name already in the set, so a declaration keyed to the shell height through any depth of indirection is seen
(`names_any(value, names)`); `bare_var(value)` is the one custom property a value consists of (`var(--app-top,0px)` and
nothing outside the function; None for `calc(var(--app-top) - 40px)`), and `aliases(rules, name)` the fixed point of the
names declared as a bare var() of one in the set, for a pin that needs the VALUE, not a mention; a property published
only by script, never declared in the served CSS, is outside any served-CSS census by construction. Selectors:
`members(selector)` splits a comma list, `subject(member)` is the subject compound (the last compound of a complex
selector), `parts(compound)` its simple selectors, `restricting(compound)` the ones that tell elements apart (a type, an
id, a class, a plain pseudo-class or a pseudo-element; `*`, an attribute selector and a functional pseudo-class such as
:not(), :is(), :where(), :has() or :nth-child() restrict nothing in a static reading), `can_match(a, b)` whether two
compounds can select one element (one's restricting selectors are a subset of the other's: `iframe` and `iframe.lifted`,
`body` and `body.picker-open`, `*` and anything; not `#f-chat` and `iframe.lifted`, which a static reading of the sheet
cannot unite), `surely(compound, known)` whether a compound selects every element known to carry the simple selectors
in `known` (its restricting selectors are all among them), `compound(known)` the canonical compound naming an element
known by a set of simple selectors (`iframe.lifted` for {iframe, .lifted}), `specificity(member)` the (ids, classes,
types) triple, `important(value)` whether a declaration value ends in !important however spaced or cased.

Script code and markup: `scripts(html)` is every live <script> element's code with its comments removed, by a scanner
over string, template and regular-expression literals and both comment forms; `comment_spans(html)` is every span of the
page that is comment text (an HTML comment outside a script or style element, a /* */ inside a style element, a /* */
or // inside a script element), which tests/test_served_pins_read_elements.py reads to find a pin a comment could
satisfy; `code(html)` is the page with every such span blanked, for a token that has no parsed form (a markup attribute,
a string inside a script).

Loads no romp code, so it needs no state preamble.
"""
import re
from collections import namedtuple

Rule = namedtuple("Rule", "index at selector declarations decls")

_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
_SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)
_STYLE_OPEN = re.compile(r"<style(?=[\s>/])", re.I)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_VAR = re.compile(r"var\(\s*(--[\w-]+)", re.I)
_IMPORTANT = re.compile(r"!\s*important\s*$", re.I)
_BARE_VAR = re.compile(r"^var\(\s*(--[\w-]+)\s*(?:,(.*))?\)$", re.S | re.I)


def _outside(pos, spans):
    return not any(s <= pos < e for s, e in spans)


def html_comment_spans(html):
    """Spans of the page's HTML comments: a <!-- that opens outside a script or style element (inside one it is script
    or style text: a `<!--` in a served script's regular expression is not a comment, and one that opens a comment
    holding a `</script>` would otherwise swallow the element's end)."""
    raw = [(m.start(1), m.end(1)) for m in _SCRIPT.finditer(html)] + [(m.start(1), m.end(1)) for m in _STYLE.finditer(html)]
    spans, i = [], 0
    while True:
        i = html.find("<!--", i)
        if i < 0:
            return spans
        if _outside(i, raw):
            j = html.find("-->", i + 4)
            j = len(html) if j < 0 else j + 3
            spans.append((i, j))
            i = j
        else:
            i += 4


def markup(html):
    """The page with its HTML comments blanked (offsets preserved): the text the element locators read, so a <style> or
    <script> written inside an HTML comment is neither an element nor a tag opening (round 5, 2026-09-20: it had been read as
    live markup, so a census accepted an origin rule that existed only in commented-out markup)."""
    return _blank(html, html_comment_spans(html))


def _script_spans(html):
    return [(m.start(1), m.end(1)) for m in _SCRIPT.finditer(markup(html))]


def style_blocks(html):
    """[(start, css)] for every live style element; refuses when a `<style` tag opening outside a script element or an
    HTML comment was not consumed."""
    live = markup(html)
    blocks = [(m.start(1), m.group(1)) for m in _STYLE.finditer(live)]
    scripts = _script_spans(html)
    opens = [m.start() for m in _STYLE_OPEN.finditer(live) if _outside(m.start(), scripts)]
    assert len(opens) == len(blocks), "the served page opens %d style elements and the parser consumed %d" % (len(opens), len(blocks))
    return blocks


def css_comment_spans(css):
    """Spans of /* */ comments outside quotes, as offsets into css."""
    spans, i, n = [], 0, len(css)
    while i < n:
        c = css[i]
        if c in "'\"":
            j = i + 1
            while j < n and css[j] != c:
                j += 2 if css[j] == "\\" else 1
            i = j + 1
        elif c == "/" and css.startswith("/*", i):
            j = css.find("*/", i + 2)
            j = n if j < 0 else j + 2
            spans.append((i, j))
            i = j
        else:
            i += 1
    return spans


def _blank(text, spans):
    out = list(text)
    for s, e in spans:
        for k in range(s, min(e, len(out))):
            out[k] = " " if out[k] != "\n" else "\n"
    return "".join(out)


def declarations(block):
    """(property, value) pairs of a declaration block: split at ; outside parentheses, brackets and quotes."""
    out, depth, buf, i, n = [], 0, "", 0, len(block)
    while i < n:
        c = block[i]
        if c in "'\"":
            j = i + 1
            while j < n and block[j] != c:
                j += 2 if block[j] == "\\" else 1
            buf += block[i:j + 1]
            i = j + 1
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == ";" and depth == 0:
            out.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    out.append(buf)
    pairs = []
    for d in out:
        if ":" not in d or not d.strip():
            continue
        p, v = d.split(":", 1)
        p = p.strip()
        pairs.append((p if p.startswith("--") else p.lower(), v.strip()))   # a custom property's name is case-sensitive
    return pairs


# at-rules whose block holds declarations rather than rules; their contents are outside any selector census
_DECLARATION_AT = {"@font-face", "@page", "@counter-style", "@property", "@viewport", "@color-profile", "@font-palette-values", "@font-feature-values"}


def rules(html):
    """Every rule of every served style element, comments stripped, as Rule tuples in document order."""
    out = []
    for _, css in style_blocks(html):
        css = _blank(css, css_comment_spans(css))
        stack, buf, i, n = [], "", 0, len(css)
        while i < n:
            ch = css[i]
            if ch == "{":
                prelude, buf = buf.strip(), ""
                if prelude.startswith("@") and prelude.split()[0].lower() in _DECLARATION_AT:
                    j, depth = i, 0   # a declaration block (@font-face, @page): no rules inside, skipped whole
                    while True:
                        depth += (css[j] == "{") - (css[j] == "}")
                        if depth == 0:
                            break
                        j += 1
                        assert j < n, "unbalanced braces in a served %s block" % prelude
                    i = j
                elif prelude.startswith("@"):
                    stack.append(prelude)
                else:
                    j = css.index("}", i)
                    out.append(Rule(len(out), tuple(stack), prelude, css[i + 1:j], tuple(declarations(css[i + 1:j]))))
                    i = j
            elif ch == "}":
                assert stack, "an unmatched } in a served style element"
                stack.pop()
                buf = ""
            elif ch == ";":
                # a statement at-rule (@import url(x); @charset "utf-8"; @namespace svg url(...); @layer base;) ends here
                # with no block. Round 5 (2026-09-20): it had accumulated into the NEXT rule's prelude, which then began
                # with @ and was pushed as a nested at-rule, dropping that rule and its declarations silently.
                assert buf.strip().startswith("@"), "a ; outside a declaration block that ends no statement at-rule: %r" % (buf.strip()[:80],)
                buf = ""
            else:
                buf += ch
            i += 1
        assert not stack, "unbalanced braces in a served style element: %r" % (stack,)
    return out


def _split_top(text, seps):
    """Split text at any character in seps found outside parentheses and brackets."""
    out, depth, buf = [], 0, ""
    for c in text:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if depth == 0 and c in seps:
            out.append(buf)
            buf = ""
        else:
            buf += c
    out.append(buf)
    return out


def members(selector):
    """The comma members of a selector list, stripped, empty ones dropped."""
    return [m.strip() for m in _split_top(selector, ",") if m.strip()]


def subject(member):
    """The subject compound of one complex selector: its last compound after every combinator."""
    compounds = [c for c in _split_top(re.sub(r"\s*([>+~])\s*", r"\1", member.strip()), " >+~") if c]
    return compounds[-1] if compounds else ""


def subjects(selector):
    return [subject(m) for m in members(selector)]


_SIMPLE = re.compile(r"\*|[a-zA-Z][\w-]*|#[\w-]+|\.[\w-]+|\[[^\]]*\]|::[\w-]+(?:\([^)]*\))?|:[\w-]+(?:\([^)]*(?:\([^)]*\)[^)]*)*\))?")


def parts(compound):
    """The simple selectors of one compound, as a set of strings ('iframe', '.lifted', '#f-chat', ':not(.x)'); None for a
    prelude that is not a compound selector (a keyframe step such as 0% or from)."""
    found = _SIMPLE.findall(compound)
    return set(found) if found and "".join(found) == compound else None


_NEVER_RESTRICTS = re.compile(r"^(?:\*|\[.*\]|:[\w-]+\(.*\))$", re.S)


def restricting(compound):
    """The simple selectors of a compound that tell elements apart in a static reading: a type, an id, a class, a plain
    pseudo-class or a pseudo-element. Dropped: `*`, an attribute selector and a functional pseudo-class (:not(), :is(),
    :where(), :has(), :nth-child()), which can hold for any element the rest of the compound selects (round 5, 2026-09-20:
    can_match had read them as selectors the other compound must also carry, so `*`, `iframe[id]` and `iframe:not(.foo)`
    were read as unable to select the lifted frame). None for a prelude that is not a compound selector."""
    found = parts(compound)
    return None if found is None else {p for p in found if not _NEVER_RESTRICTS.match(p)}


def can_match(a, b):
    """Whether two compounds can select the same element by a static reading of the sheet: one's restricting selectors
    are a subset of the other's (a class or pseudo-class the other lacks may still be on the element). Pseudo-elements
    are boxes of their own, so a compound naming one matches only a compound naming the same one; a prelude that is no
    compound (a keyframe step) matches nothing."""
    pa, pb = restricting(a), restricting(b)
    if pa is None or pb is None:
        return False
    if {p for p in pa if p.startswith("::")} != {p for p in pb if p.startswith("::")}:
        return False
    return pa <= pb or pb <= pa


def surely(compound, known):
    """Whether a compound selects every element known to carry the simple selectors in `known` (a set from
    restricting()): each restricting selector of the compound is among them. `iframe` and `iframe.lifted` surely select
    the element known as {iframe, .lifted}; `iframe.lifted.big` only may (can_match), the element may lack .big."""
    rs = restricting(compound)
    return rs is not None and rs <= set(known)


def compound(known):
    """The canonical compound naming an element known by a set of restricting simple selectors: type, id, classes,
    pseudo-classes, pseudo-elements, each group sorted; `*` for an element nothing restricts."""
    order = lambda p: (0 if p[0].isalpha() else 1 if p[0] == "#" else 2 if p[0] == "." else 4 if p.startswith("::") else 3, p)
    return "".join(sorted(known, key=order)) or "*"


def specificity(member):
    """(ids, classes and attributes and pseudo-classes, types and pseudo-elements) of one complex selector; :not(), :is()
    and :has() count their argument, :where() counts nothing."""
    text = re.sub(r":where\([^)]*\)", "", member)
    text = re.sub(r":(?:not|is|has)\(", "(", text)
    a = len(re.findall(r"#[\w-]+", text))
    b = len(re.findall(r"\.[\w-]+|\[[^\]]*\]|(?<!:):[\w-]+", text))
    c = len(re.findall(r"::[\w-]+|(?<![\w#.:\[-])[a-zA-Z][\w-]*(?![\w-]*[=\]])", re.sub(r"\[[^\]]*\]", "", text)))
    return (a, b, c)


def important(value):
    """Whether a declaration value carries !important, however spaced or cased (`0 ! important`, `0!IMPORTANT`)."""
    return bool(_IMPORTANT.search(value))


def is_fixed(rule):
    return any(p == "position" and v.split("!")[0].strip().lower() == "fixed" for p, v in rule.decls)


def var_names(value):
    return set(_VAR.findall(value))


def bare_var(value):
    """The custom property a value consists of and nothing else: `var(--app-top,0px)` gives '--app-top', with any
    fallback; None for a value with anything outside the one function (`calc(var(--app-top,0px) - 40px)`,
    `var(--app-top) - 40px`, `var(--a) var(--b)`), which reads the property but does not equal it."""
    text = value.split("!")[0].strip()
    m = _BARE_VAR.match(text)
    if not m:
        return None
    depth = 0
    for i, c in enumerate(text):
        depth += (c == "(") - (c == ")")
        if c == ")" and depth == 0 and i < len(text) - 1:
            return None   # the var( closed before the end: something follows the function
    return m.group(1)


def closure(rules_, name):
    """The custom properties whose value names var(<name>) or one already in the set, to a fixed point, with name itself."""
    custom = [(p, v) for r in rules_ for p, v in r.decls if p.startswith("--")]
    names = {name}
    while True:
        more = {p for p, v in custom if p not in names and var_names(v) & names}
        if not more:
            return names
        names |= more


def aliases(rules_, name):
    """The custom properties declared as a BARE var() of name or of one already in the set, to a fixed point, with name
    itself: the names whose value IS the property's value (`--x:var(--app-top)`), not merely a function of it
    (`--x:calc(var(--app-top) - 40px)` is in closure() and not here). For a pin that needs the value, not a mention."""
    custom = [(p, v) for r in rules_ for p, v in r.decls if p.startswith("--")]
    names = {name}
    while True:
        more = {p for p, v in custom if p not in names and bare_var(v) in names}
        if not more:
            return names
        names |= more


def names_any(value, names):
    """Whether a declaration value names one of the custom properties through var()."""
    return bool(var_names(value) & set(names))


_REGEX_PREV = set("(,=:[!&|?{};+-*%<>~^")
_REGEX_WORDS = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else", "yield", "await"}


def js_comment_spans(js):
    """Spans of // and /* */ comments in a script, as offsets into js; string, template and regular-expression literals
    are skipped (a / opens a regular expression after an operator, an opening bracket, a keyword or nothing, and divides
    after an operand)."""
    spans, i, n, prev, word = [], 0, len(js), "", ""
    while i < n:
        c = js[i]
        if c in "'\"":
            j = i + 1
            while j < n and js[j] != c and js[j] != "\n":
                j += 2 if js[j] == "\\" else 1
            i, prev, word = j + 1, c, ""
        elif c == "`":
            j = i + 1
            while j < n and js[j] != "`":
                j += 2 if js[j] == "\\" else 1
            i, prev, word = j + 1, c, ""
        elif c == "/" and js.startswith("//", i):
            j = js.find("\n", i)
            j = n if j < 0 else j
            spans.append((i, j))
            i = j
        elif c == "/" and js.startswith("/*", i):
            j = js.find("*/", i + 2)
            j = n if j < 0 else j + 2
            spans.append((i, j))
            i = j
        elif c == "/" and (prev == "" or prev in _REGEX_PREV or word in _REGEX_WORDS):
            j, in_class = i + 1, False
            while j < n and js[j] != "\n":
                d = js[j]
                if d == "\\":
                    j += 2
                    continue
                if d == "[":
                    in_class = True
                elif d == "]":
                    in_class = False
                elif d == "/" and not in_class:
                    break
                j += 1
            j += 1
            while j < n and js[j].isalpha():
                j += 1
            i, prev, word = j, "/", ""
        elif c.isspace():
            i += 1
        elif c.isalnum() or c in "_$":
            j = i
            while j < n and (js[j].isalnum() or js[j] in "_$"):
                j += 1
            word, prev, i = js[i:j], js[j - 1], j
        else:
            prev, word, i = c, "", i + 1
    return spans


def comment_spans(html):
    """Every span of the page that is comment text: HTML comments (outside script and style elements), style-element
    comments, script-element comments; the elements are the live ones (a style or script inside an HTML comment is
    already in that comment's span)."""
    spans = html_comment_spans(html)
    live = markup(html)
    for m in _STYLE.finditer(live):
        spans += [(m.start(1) + s, m.start(1) + e) for s, e in css_comment_spans(m.group(1))]
    for m in _SCRIPT.finditer(live):
        spans += [(m.start(1) + s, m.start(1) + e) for s, e in js_comment_spans(m.group(1))]
    return sorted(spans)


def code(html):
    """The page with every comment span blanked (HTML comments, style-element comments, script-element comments): the
    markup and the code a pin can read where no parsed form of the token exists (a markup attribute, a script string)."""
    return _blank(html, comment_spans(html))


def scripts(html):
    """Every live script element's code, its comments removed, in document order (a script inside an HTML comment is not
    an element)."""
    out = []
    for m in _SCRIPT.finditer(markup(html)):
        js = m.group(1)
        out.append(_blank(js, js_comment_spans(js)))
    return out
