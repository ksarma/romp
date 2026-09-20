#!/usr/bin/env python3
"""Parsed views of a served page, for pins that read the ELEMENT or the PARSED RULE they pin rather than page text.

A substring assertion over a served page is satisfied by a comment that spells the same token (D1 round 1, 2026-09-19:
three viewport-meta pins were satisfied by a served comment after the meta had lost the token), and a census that
substring-searches declarations misses members written through a custom-property indirection, with whitespace inside
the var() call, under a split selector, inside a style element carrying an attribute, or re-topped through the inset
shorthand (D1 round 2, 2026-09-19). This module is the instrument both kinds of pin read instead.

Elements (round 8, 2026-09-20): the element and attribute layer is the standard library's HTML tokenizer, html.parser
(`_Elements`, `elements(html)`), not regular expressions over the markup. The question was put after the same silent-pass
shape closed three times here (a linked sheet unread, round 6; `rel="preload stylesheet"` past a start-anchored token read,
round 7; a `>` inside a quoted attribute value ending a regex's element early, and a `<style media=print>` read as
unconditional CSS, round 8), and the answer is yes: the tokenizer reads tags, attributes (unquoted values, lower-cased names,
the first of a duplicate), comments, and script and style CDATA the way HTML does, and getpos() maps to absolute offsets by
line start, which is all this layer needs; those three closed members are its unit cases. What it does not do, and this module
still does itself: tokenize CSS and JS (the scanners below), and the HTML5 script-data escaped states (a `<!-- <script>` inside
a script), which the served pages do not use. The tokenizer's CDATA end-tag and comment rules were tightened in the 3.12 and
3.13 maintenance releases (a `</script` ends the element only before whitespace, `/` or `>`; a comment closes at `-->` or
`--!>`); the shapes this module's unit cases pin read the same under 3.10, 3.11, 3.12, 3.13 and 3.14, and the eight served
pages gave byte-identical spans, scripts and rules under each at round 8. Refuses a script or style element the page never
closes, and a self-closing `<script/>` or `<style/>` (a start tag to HTML).

Style rules: `rules(html)` parses every live style element (any attributes; a style or script element inside an HTML comment
is comment text, not an element, round 5, 2026-09-20), strips its comments, and brace-matches it into Rule(index, at, selector,
declarations, decls): `at` is the tuple of enclosing at-rule preludes (an @media query, a @supports condition), with the
element's own `media` attribute as the outermost prelude where it conditions anything (`media_prelude`: `@media print`;
absent, empty, `all` and `screen` add nothing; round 8: a rule under `<style media=print>` had read as unconditional, so a
census over what applies on the phone's screen passed over a page whose only origin sat in one), `declarations` the block's raw
text, `decls` its (property, value) pairs split at ; outside parentheses and quotes; a statement at-rule (@charset, @namespace,
`@layer name;`: an at-prelude ended by ; with no block) is consumed and dropped, never folded into the next rule's prelude
(round 5). CSS the parser cannot read REFUSES rather than shrinking a census silently (round 6, 2026-09-20): a `<link>` whose
rel set carries the stylesheet token anywhere (`rel=stylesheet`, `rel="preload stylesheet"`, `alternate stylesheet` too; round
7, 2026-09-20: a token after another had passed; round 8: the rel read from the tokenizer's attributes, so a `>` inside a quoted
value before it no longer hides it) in the live markup and an `@import` statement, ended by `;` or by the end of the element
(round 7: a trailing statement had been dropped unread), both raise, the way an unclosed style element does, since what an
external file adds or re-tops is outside every rule the parse returns (a rule the file merely moves still reds the pins that
name it); a caller that reads a page which links its stylesheets by design passes `linked=True` and takes the style elements
alone. Keywords and function names are compared case-insensitively, as CSS reads them (`position:FIXED`, `VAR(--app-h)`,
`! IMPORTANT`).
Custom properties: `closure(rules, "--app-h")` is the fixed point of the names whose declared value names var(--app-h) or
a name already in the set, so a declaration keyed to the shell height through any depth of indirection is seen
(`names_any(value, names)`); `bare_var(value)` is the one custom property a value consists of (`var(--app-top,0px)` and
nothing outside the function; None for `calc(var(--app-top) - 40px)`), and `aliases(rules, name, member)` the fixed point
of the names declared as a bare var() of one in the set, for a pin that needs the VALUE, not a mention, less any name a
rule that can select `member` re-declares to something else (round 6, 2026-09-20: the table had been sheet-global, so an
alias on one rule counted where the member's own rule re-declared it), the refusal following the chain on the member's
rules to a fixed point (round 7: a name declared on the member's rule as a bare var() of a REFUSED name had stayed); `is_fixed(rule, rules)` reads position:fixed
through the same indirection (a bare var() resolved against every declaration of the name, its fallback when undeclared;
round 6). A property published only by script, never declared in the served CSS, is outside any served-CSS census by
construction, and so is the sheet a `<link>` or an `@import` names (the parse refuses those, above). Selectors:
`members(selector)` splits a comma list, `subject(member)` is the subject compound (the last compound of a complex
selector), `parts(compound)` its simple selectors, `restricting(compound)` the ones that tell elements apart (a type, an
id, a class, a plain pseudo-class or a pseudo-element; `*`, an attribute selector and a functional pseudo-class such as
:not(), :is(), :where(), :has() or :nth-child() restrict nothing in a static reading), `can_match(a, b)` whether two
compounds can select one element (one's restricting selectors are a subset of the other's: `iframe` and `iframe.lifted`,
`body` and `body.picker-open`, `*` and anything; not `#f-chat` and `iframe.lifted`, which a static reading of the sheet
cannot unite), `surely(compound, known)` whether a compound selects every element known to carry the simple selectors
in `known` (its restricting selectors are all among them, and it carries no attribute selector or functional pseudo-class,
which select by a state the sheet cannot show: `body:not(.picker-open)` may select the body or not, round 6, 2026-09-20;
`*` alone passes), `compound(known)` the canonical compound naming an element
known by a set of simple selectors (`iframe.lifted` for {iframe, .lifted}), `specificity(member)` the (ids, classes,
types) triple, `important(value)` whether a declaration value ends in !important however spaced or cased.

Script code and markup: `scripts(html)` is every live <script> element's code with its comments removed, by a scanner
over string, template and regular-expression literals and both comment forms; `comment_spans(html)` is every span of the
page that is comment text (an HTML comment outside a script or style element, a /* */ inside a style element, a /* */
or // inside a script element), which tests/test_served_pins_read_elements.py reads to find a pin a comment could
satisfy; `code(html)` is the page with every such span blanked, for a token that has no parsed form (a markup attribute,
a string inside a script); `js_code(js)` and `css_code(css)` blank the comments of one script or style fragment, for a pin
over one of the kernel's served constants (a string spliced into a page), which the same census reads; `element_spans(html)`
is every live script and style element's content span with its kind, for a reader that needs to know which kind of element
a text landed in (the census picks a constant's comment scanner by it, round 7, 2026-09-20); `linked_sheets(html)` the
offsets of the live `<link>` elements whose rel set carries stylesheet (`rel_tokens`), the parse's refusal and the census's pin
reading one predicate; `attr(element, name)` an element's attribute as the tokenizer read it. A script element's `type`
attribute is read and not judged: a data block (`<script type=application/json>`) is still script text to `scripts()` and
`element_spans()`, and no served page carries one today (disclosed, not closed).

Loads no romp code, so it needs no state preamble.
"""
import functools
import re
from collections import namedtuple
from html.parser import HTMLParser

Rule = namedtuple("Rule", "index at selector declarations decls")
# a live script, style or link element: absolute offsets of the element and of its content (a link has none: content_start,
# content_end and end coincide at the end of its tag), and its attributes as the tokenizer read them, (name, value) pairs with
# the name lower-cased and the value unquoted (None for a bare attribute)
Element = namedtuple("Element", "kind start content_start content_end end attrs")

_VAR = re.compile(r"var\(\s*(--[\w-]+)", re.I)
_IMPORTANT = re.compile(r"!\s*important\s*$", re.I)
_BARE_VAR = re.compile(r"^var\(\s*(--[\w-]+)\s*(?:,(.*))?\)$", re.S | re.I)
# a style element's media attribute that conditions nothing: absent, empty, `all`, or `screen` (every page here is a screen)
_UNCONDITIONAL_MEDIA = {"", "all", "screen"}


class _Elements(HTMLParser):
    """The element and attribute layer of a served page, read by the standard library's HTML tokenizer (round 8, 2026-09-20):
    every live script, style and link element with absolute offsets and its attributes, and every HTML comment's span. A
    script or style element's content is the tokenizer's CDATA (it ends at the element's own end tag, whatever the content
    spells, a `<!--` in a script string included), a `<style` or `<link` inside an HTML comment or a script string is comment
    or script text and no element, and an attribute value is read as HTML reads it, so a `>` inside a quoted value does not
    end the tag. Positions come from getpos() (line and column) mapped onto the page's line starts; a comment's span ends where
    the tokenizer began the next construct, so it is what the tokenizer read as the comment whatever closed it. Refuses a
    script or style element the page never closes, and a self-closing `<script/>` or `<style/>` (a start tag to HTML)."""

    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.html, self.elements, self.comments, self.open, self.pending = html, [], [], None, None
        self.starts = [0] + [m.end() for m in re.finditer("\n", html)]
        self.feed(html)
        self.close()
        self._event(len(html))
        assert self.open is None, "a <%s> element the served page never closes (opened at offset %d)" % (self.open or ("?", -1))[:2]

    def _pos(self):
        line, col = self.getpos()
        return self.starts[line - 1] + col

    def _event(self, pos):
        if self.pending is not None:   # the construct after a comment begins where the comment ended
            self.comments.append((self.pending, pos))
            self.pending = None

    def _link(self, pos, attrs):
        end = pos + len(self.get_starttag_text())
        self.elements.append(Element("link", pos, end, end, end, tuple(attrs)))

    def handle_starttag(self, tag, attrs):
        pos = self._pos()
        self._event(pos)
        if tag in ("script", "style"):
            self.open = (tag, pos, pos + len(self.get_starttag_text()), tuple(attrs))
        elif tag == "link":
            self._link(pos, attrs)

    def handle_startendtag(self, tag, attrs):
        pos = self._pos()
        self._event(pos)
        assert tag not in ("script", "style"), "a self-closing <%s/> at offset %d is a start tag to HTML; this reader refuses it" % (tag, pos)
        if tag == "link":
            self._link(pos, attrs)

    def handle_endtag(self, tag):
        pos = self._pos()
        self._event(pos)
        if tag in ("script", "style"):
            assert self.open is not None and self.open[0] == tag, "a </%s> at offset %d with no open %s element" % (tag, pos, tag)
            kind, start, content_start, attrs = self.open
            self.elements.append(Element(kind, start, content_start, pos, self.html.index(">", pos) + 1, attrs))
            self.open = None

    def handle_comment(self, data):
        pos = self._pos()
        self._event(pos)
        self.pending = pos

    def handle_data(self, data):
        self._event(self._pos())

    def handle_entityref(self, name):
        self._event(self._pos())

    def handle_charref(self, name):
        self._event(self._pos())

    def handle_decl(self, decl):
        self._event(self._pos())

    def handle_pi(self, data):
        self._event(self._pos())

    def unknown_decl(self, data):
        self._event(self._pos())


@functools.lru_cache(maxsize=64)
def elements(html):
    """Every live script, style and link element of a page, as Element records in document order (parsed once per page text)."""
    return tuple(_Elements(html).elements)


@functools.lru_cache(maxsize=64)
def html_comment_spans(html):
    """Spans of the page's HTML comments: a <!-- the tokenizer read as a comment, which is one outside a script or style
    element (inside one it is script or style text: a `<!--` in a served script's regular expression is not a comment, and
    one that opens a comment holding a `</script>` would otherwise swallow the element's end)."""
    return list(_Elements(html).comments)


def markup(html):
    """The page with its HTML comments blanked (offsets preserved): the text a reader that wants live markup only reads, so a
    <style> or <script> written inside an HTML comment is neither an element nor a tag opening (round 5, 2026-09-20: it had been
    read as live markup, so a census accepted an origin rule that existed only in commented-out markup). The element layer
    itself no longer needs it: the tokenizer reads a comment as a comment."""
    return _blank(html, html_comment_spans(html))


def attr(element, name):
    """The value of an element's attribute as the tokenizer read it (unquoted; None when absent or bare); HTML keeps the first of
    a duplicated attribute, so does this."""
    return next((v for k, v in element.attrs if k == name), None)


def rel_tokens(element):
    """The tokens of a link element's rel set, lower-cased: HTML reads rel as whitespace-separated tokens and applies the keyword
    wherever it sits (round 7, 2026-09-20: `rel="preload stylesheet"` had passed a start-anchored reading in silence)."""
    value = attr(element, "rel")
    return set((value or "").lower().split())


def linked_sheets(html):
    """Offsets of every live `<link>` element whose rel set carries the stylesheet token (outside script elements and HTML
    comments; the element's extent and its attributes are the tokenizer's, so a `>` inside a quoted value before rel does not
    hide the rel, round 8, 2026-09-20): the one predicate behind the parse's refusal and a census's pin that a page links no
    sheet."""
    return [e.start for e in elements(html) if e.kind == "link" and "stylesheet" in rel_tokens(e)]


def element_spans(html):
    """[(start, end, kind)] for the content span of every live script and style element, kind 'script' or 'style', in
    document order: a text that lands inside one is script or style text, and one outside every span is markup."""
    return sorted((e.content_start, e.content_end, e.kind) for e in elements(html) if e.kind in ("script", "style"))


def style_elements(html, linked=False):
    """Every live style element, as Element records; refuses when the live markup links an external stylesheet (a `<link>`
    whose rel set carries stylesheet, outside script elements: linked_sheets), whose rules no parse of the page's style
    elements returns (round 6, 2026-09-20: an unconsumed tag refused while the linked sheet passed in silence, which taught a
    reader that unread CSS is always caught); `linked=True` states that the caller knows the page links its stylesheets and
    wants the style elements alone. A style element the page never closes refuses in the tokenizer (_Elements)."""
    links = linked_sheets(html)
    assert linked or not links, "the served page links %d external stylesheet(s) this parse does not read; pass linked=True to take the style elements alone" % len(links)
    return [e for e in elements(html) if e.kind == "style"]


def style_blocks(html, linked=False):
    """[(start, css)] for every live style element (style_elements), the content's offset and text."""
    return [(e.content_start, html[e.content_start:e.content_end]) for e in style_elements(html, linked)]


def media_prelude(element):
    """The at-rule prelude a style element's own media attribute puts over every rule it holds (`@media print`), or None where
    the attribute conditions nothing (absent, empty, `all`, `screen`): round 8 (2026-09-20), a `<style media=print>` had been
    read as unconditional CSS, so a census over what applies on the phone's screen passed over a page whose only origin sat in
    one. The query text is kept as written (whitespace collapsed); a folded prelude never equals the shell's mobile query, so
    a rule under it is not the mobile block's."""
    value = attr(element, "media")
    if value is None or value.strip().lower() in _UNCONDITIONAL_MEDIA:
        return None
    return "@media " + " ".join(value.split())


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


def _statement(buf):
    """A statement at-rule's text (`@import url(x); @charset "utf-8"; @namespace svg url(...); @layer base;`), met at a `;`
    outside any block or left at the end of the element (CSS ends an at-rule at EOF as well as at `;`, round 7, 2026-09-20: a
    trailing `@import url(x.css)` with no semicolon had been dropped unread): anything else at that level is a parse this
    instrument cannot account for and refuses, and an `@import` refuses because its sheet is outside the parse."""
    text = buf.strip()
    assert text.startswith("@"), "text outside a declaration block that is no statement at-rule: %r" % (text[:80],)
    assert not text.lower().startswith("@import"), "an @import in a served style element pulls in a sheet this parse does not read: %r" % (text[:80],)


def rules(html, linked=False):
    """Every rule of every served style element, comments stripped, as Rule tuples in document order, a style element's own
    media attribute folded into its rules' `at` as the outermost prelude (media_prelude); refuses a linked stylesheet
    (style_elements) and an `@import` statement, ended by `;` or by the end of the element (its sheet is outside this parse)."""
    out = []
    for el in style_elements(html, linked):
        css = html[el.content_start:el.content_end]
        css = _blank(css, css_comment_spans(css))
        media = media_prelude(el)   # the element's own media attribute conditions every rule it holds (round 8, 2026-09-20)
        outer = (media,) if media else ()
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
                    out.append(Rule(len(out), outer + tuple(stack), prelude, css[i + 1:j], tuple(declarations(css[i + 1:j]))))
                    i = j
            elif ch == "}":
                assert stack, "an unmatched } in a served style element"
                stack.pop()
                buf = ""
            elif ch == ";":
                # a statement at-rule (@import url(x); @charset "utf-8"; @namespace svg url(...); @layer base;) ends here
                # with no block. Round 5 (2026-09-20): it had accumulated into the NEXT rule's prelude, which then began
                # with @ and was pushed as a nested at-rule, dropping that rule and its declarations silently.
                _statement(buf)
                buf = ""
            else:
                buf += ch
            i += 1
        if buf.strip():
            _statement(buf)   # a statement at-rule the end of the element ends (round 7, 2026-09-20)
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
    restricting()): each restricting selector of the compound is among them, and the compound carries no attribute selector
    or functional pseudo-class. `iframe` and `iframe.lifted` surely select the element known as {iframe, .lifted};
    `iframe.lifted.big` only may (can_match), the element may lack .big; `body:not(.picker-open)`, `:is(#f-chat)` and
    `body[data-x]` only may too, they select by a state or an attribute the sheet cannot show (round 6, 2026-09-20: those
    had been dropped from the reading, as can_match rightly drops them, so a rule that cannot select the member at all
    was accepted as its origin). `*` alone restricts nothing and passes. The subject compound only is read: an
    ancestor-conditioned origin (html.kb body) still passes, and the state question is the served leg's."""
    found = parts(compound)
    if found is None or any(p != "*" and _NEVER_RESTRICTS.match(p) for p in found):
        return False
    return {p for p in found if p != "*"} <= set(known)


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


def is_fixed(rule, rules_=None):
    """Whether a rule declares position:fixed, the keyword read case-insensitively; with the sheet's rules given, through a
    custom-property indirection too (round 6, 2026-09-20: `position:var(--pos)` with `:root{--pos:fixed}`, or
    `position:var(--nope,fixed)`, had been read as not fixed while the sizing half of the census resolved its var() to a
    fixed point): a bare var() value resolves against EVERY declaration of the name in the sheet (any of them reading fixed
    counts, a name can be redeclared per element, so the reading is over-inclusive), and against its fallback text when the
    name is undeclared, to a fixed point. Not read: a shorthand reset (`all:initial`) or a later `position` declaration that
    un-fixes a member; the census reads the top-edge cascade only, and names `all` there."""
    return any(p == "position" and _reads_fixed(v, rules_, ()) for p, v in rule.decls)


def _reads_fixed(value, rules_, seen):
    text = value.split("!")[0].strip()
    if text.lower() == "fixed":
        return True
    name = bare_var(text)
    if name is None or rules_ is None or name in seen:
        return False
    declared = [v for r in rules_ for p, v in r.decls if p == name]
    if declared:
        return any(_reads_fixed(v, rules_, seen + (name,)) for v in declared)
    fallback = _BARE_VAR.match(text).group(2)
    return fallback is not None and _reads_fixed(fallback.strip(), rules_, seen + (name,))


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


def aliases(rules_, name, member=None):
    """The custom properties declared as a BARE var() of name or of one already in the set, to a fixed point, with name
    itself: the names whose value IS the property's value (`--x:var(--app-top)`), not merely a function of it
    (`--x:calc(var(--app-top) - 40px)` is in closure() and not here). For a pin that needs the value, not a mention. With
    `member`, a compound naming the element the pin is about, a name that any rule able to select that element declares to
    something other than a bare var() of a name in the set is refused (round 6, 2026-09-20: the table had been sheet-global
    with no cascade, so `--x:var(--app-top)` on one rule made `top:var(--x)` the pan even where the member's own rule
    re-declared `--x:0`), and the refusal follows the chain on the member's rules to a fixed point (round 7, 2026-09-20: it had
    run once, so `--y:var(--x)` on the member's own rule stayed an alias after `--x` was refused there, though the engine
    computes `--y` on the member from the member's own `--x`; a `--y:var(--x)` declared on `:root` stays, the root computes it
    as the pan and the member inherits that). This is not a cascade: a re-declaration on an ANCESTOR of the member, which the
    member would inherit, is not read (no served rule takes that shape today), so the table stays over-inclusive there and the
    served leg reads the boxes."""
    custom = [(r, p, v) for r in rules_ for p, v in r.decls if p.startswith("--")]
    names = {name}
    while True:
        more = {p for _, p, v in custom if p not in names and bare_var(v) in names}
        if not more:
            break
        names |= more
    if member is None:
        return names
    selects = lambda r: any(can_match(subject(m), member) for m in members(r.selector))
    while True:
        refused = {p for r, p, v in custom if p != name and p in names and bare_var(v) not in names and selects(r)}
        if not refused:
            return names
        names -= refused


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
    spans = list(html_comment_spans(html))
    for el in elements(html):
        if el.kind in ("script", "style"):
            scan = js_comment_spans if el.kind == "script" else css_comment_spans
            spans += [(el.content_start + s, el.content_start + e) for s, e in scan(html[el.content_start:el.content_end])]
    return sorted(spans)


def code(html):
    """The page with every comment span blanked (HTML comments, style-element comments, script-element comments): the
    markup and the code a pin can read where no parsed form of the token exists (a markup attribute, a script string)."""
    return _blank(html, comment_spans(html))


def scripts(html):
    """Every live script element's code, its comments removed, in document order (a script inside an HTML comment is not
    an element)."""
    out = []
    for el in elements(html):
        if el.kind == "script":
            js = html[el.content_start:el.content_end]
            out.append(_blank(js, js_comment_spans(js)))
    return out


def js_code(js):
    """A script fragment with its comments blanked (offsets preserved): the text a pin over one of the kernel's served script
    CONSTANTS reads (round 6, 2026-09-20: a bare token asserted over such a constant was satisfiable by the constant's own
    comment, and the pins census reads the constants now)."""
    return _blank(js, js_comment_spans(js))


def css_code(css):
    """A stylesheet fragment with its /* */ comments blanked (offsets preserved), for a pin over a served CSS constant."""
    return _blank(css, css_comment_spans(css))
