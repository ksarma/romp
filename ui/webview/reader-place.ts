// The reader's place across a paint of the file viewer's body (plans/markdown-viewer.md, Slice 2: "reader keeps
// their place"). A paint that REPLACES the body's children (a Rendered/Raw switch, a reload after a session's write)
// leaves the numeric scrollTop standing over new content, so the passage under the reader's eye changes: on the audit's
// note a reload that inserted twenty paragraphs above moved the top passage from 40 to 28, and the Rendered/Raw round
// trip drifted 648 to 918px (the Raw view is taller). A reflow that keeps the children (the pane dragged, the Comments
// aside opening or closing, a text-size step) moves the passage the same way: closing the aside at 900px took the top
// paragraph from 40 to 73. So the place is kept in the file's own terms: the top-visible BLOCK, one of the top-level
// blocks the markdown lexer finds in the file (anchor-map.ts sourceBlockSpans: a paragraph, a heading, a code block, a
// table, an html block), the first whose box ends below the body's top edge, as its source span, plus how far its top
// edge sits from the body's top and how tall its box is. Both views show the same blocks. In Rendered a block is a
// top-level element (an html block of sibling tags several, whose boxes are read together; a block the browser nested
// inside an html wrapper its own element inside the wrapper, read through the wrapper: "what the place refuses" below); in Raw it is the run of
// rows from its first line to its last, so a blank row between two paragraphs belongs to neither and the block after
// it is the place (the Slice 2 review: read as its own place, a blank top row seated the paragraph BEFORE the first
// text the reader saw), while a blank row inside a fenced code block belongs to the code block; a row of a block that
// renders nothing of its own (closing tags alone, `</details>`, `</details>\n</div>`, `</details></div>`, a wrapper's
// end; a comment) or whose own element is never seated (an html block that opens a wrapper the browser nests the
// markdown after it into: its `<div align="center">` or `<details>` row, its `<summary>`, a README's `<h1>` and `<p>`
// lead rows, an `<img>` line, and the blank row before it) reads as the block after it the same way, through a run of
// such blocks (readsAsNext; the Slice 5 review, round 1: read as its own place, a shut fold's closing row seated
// nothing in Rendered, since the seat walked back through the fold's unshown paragraphs to the wrapper's refused
// block, and the numeric scrollTop stood, off by the fold's source height, 370px at 900px; round 2: the owner's ruling
// extended the rule to the wrapper's own rows, which the seat refuses (below), so a fold title at the pane's top lost
// 26 to 203px on the round trip, and to a block of two closers and a comment's row, which render nothing too; a block
// that is the document's last stays its own place). A Raw row inside a `<details>` shows its text whether the Rendered
// view folds it shut or not, and the fold's state is the Rendered DOM's (file-view.ts keeps a fold as the person left
// it across a paint), so such a row is read as its own block and CARRIES the block after the fold, and after each fold
// in turn that block lies in, each with its first row's top (Place.after): the seat takes the first of them the view
// shows when the kept block is not (round 2: a shut fold whose summary wraps put the fold's hidden rows on top of Raw
// after the switch, the way back refused them, and the reader landed 361 to 562px down), and with none to take, the
// fold ending the document or only a comment, a wrapper's end or a reference definition after it, stands on the fold's
// summary at the edge, the cap's own limit (round 6: a fold with nothing standing after it carried no Place.after, so
// the seat walked back through the hidden paragraphs to the wrapper's refused block and left the numeric scrollTop
// standing over the shorter view, the summary 617 to 636px down at 380px, off the pane, and the way back 505 to 729px
// low; the seat asks for the summary at the edge, which the pane's end mostly clamps, the summary near its bottom, and
// a clamped seat holds the Raw place in file-view.ts, so the way back returns the row exactly). A block seated from Raw below
// a SHUT fold, the carried block or a block read through the fold's closing row and the rows after it that render
// nothing, keeps its row's distance only as far as the fold's summary at the edge: the seat stands on what is shown, and
// what the reader had above that row was the fold's source or its end, which Rendered shows as the summary alone, never
// the tail of the block before the fold (round 3, the owner's ruling: seated at its own row's top, the block after a
// fifteen-paragraph fold put the summary 816px down at 900px and 1713 at 380, off the pane, from the fold's own rows, a
// hidden row, or the closing row of a wrapper before it; and from the closing row followed by a comment, the block
// before the fold showed its tail under the edge, the way back read that tail by its fraction, and the fold's whole
// source, 460 to 820px, came back between; a fold whose summary is partway above the edge keeps its carried block's
// distance, the round trip from a wrapped summary staying exact). One row of a wrapper's block is the seat's in both
// directions: the tag line of a picture of the block's own (a README's banner or logo in a centred div, a linked logo,
// a badge row: Place.pic), which is seated as a top-level picture is, its depth kept as a fraction of its height from
// the picture to the line's row and back (round 3: read as the first nested block below the picture, a banner 150px
// into view came back 435px off, the paragraph before the wrapper on top of Raw and its fraction the way back); and the
// picture BELOW the edge with a row of the block's own at it (in Raw the `<div align="center">` opener, an `<h1>` lead row
// or the blank before the opener, in Rendered a lead `<h1>` the edge is inside) is carried the same way and keeps its
// distance below the edge, as any block that starts below the edge keeps its own, so the picture stands where its tag's
// row was and the way back returns the row (round 4: read as the first nested block at its row's distance, with the
// picture between the two, 120 to 508px tall in Rendered against one Raw row, the picture landed above the edge, the way
// back seated its row at that fraction, and the opener's row came back 32 to 109px above the edge, off the pane, where
// main had kept it in view 38 to 45px low; round 5: the picture is found through the whole run of blocks the row reads
// past, so a comment's row or a closer's before the opener, the outer opener of a wrapper two deep and the blanks beside
// them carry it too, where round 4 asked the row's own block alone and those rows still dropped the logo 4 to 22px and
// the banner 60 to 410px above the edge and came back 44 to 94px above it, off the pane, main in view, and the picture
// seated from a shut fold's closing row keeps the fold's cap, the summary at the edge at most; the picture carried
// from Rendered is the one AT the edge among the block's own, the one the edge is inside whose top is nearest it, else the
// topmost below it, not the first in the DOM, since pictures of different heights on one line share a baseline and a line
// of small badges before a tall logo has its tops 96px below the logo's, so the logo at the edge carried the badges' line
// and the round trip lost 129 to 440px, while from the badges' own row, which puts them at the edge with the logo above
// it, the badges are read again and that trip stays exact; and every `<img>` of
// a row counts, one in a `<p>` beside the project's name too, the Raw read's definition, where the Rendered read had
// refused a row with text and the two directions seated different things, 64 to 82px lost; a commented-out `<img` tag is
// no picture's, since the parser makes no element of it, and counting it paired the picture with the comment's row;
// round 6: the pictures whose tags share one source LINE are one box to both reads, their union, since one Raw row
// cannot tell them apart and the union is the one box it inverts: read per picture, the edge 105px into a logo with a
// 24px badge beside it on one line carried the badge, the picture the edge was inside whose top was nearest, the Raw
// seat put the shared row at the badge's fraction, and the way back took the line's first tag, the logo, at that
// fraction, 60 to 62px lost, 12 to 13 for two badges of 48 and 24px, where 701728eae's first-in-DOM carry had named
// one picture both ways; round 7: a line whose pictures sit in one row of the block's own that holds text of the note's
// beside them, the `<p align="center">` around the logo, a `<br>` and the project's name, is that ROW's box to both reads,
// not the pictures' union, since the row's line is the one Raw row and the text under the picture is part of what it
// inverts: read from that text, the Rendered read carried no picture, the union ending above the edge, and seated the
// nested heading at its distance, the Raw read carried the row's line as the picture's, and the way back put the union at
// the row's fraction, the name 32 to 71px down at 900 and 20 to 59 at 380 (rowOfLine, lineBoxes; Pic.imgs keeps the
// pictures' own box beside the row's for the same-view reflow below); and a seat into Raw with the edge inside a picture
// leaves the picture's row two pixels below the edge at least, so the read back takes it as the top row (ROW_SHOWN: with
// the edge in the last ten pixels of a 508px banner over a 72px row the row's bottom rounded to one pixel, the read passed
// it for the blank after it, the nested heading was seated at that row's distance, and the picture came back 12 to 20px
// higher, wholly above the edge); round 8: with such a row's picture's top within the pixel the browser snaps to below the
// edge, and the half pixel a seat's own landing adds, the picture is at the edge and keeps the picture's rule (PIC_AT_EDGE:
// classified exactly, a text-first `<p>` whose logo's top a whole-pixel scroll landed 0.3 to 0.9px below the edge took the
// row's fraction on one step and the picture's on the next, and the logo drifted 2.6 to 3px per text-size step, where
// 78c0806ce's picture rule held it within 0.5), and since the review's closing pass the seat asks for a top within that band,
// either side of the edge, at the whole pixel nearest where it stood, the same ask on every reflow, where asking for the landed
// top walked it past the band at 700 to 800px (0.91, 1.27, 1.75 over A+, A+, then the row's fraction, 2.5px); a row whose
// pictures stand beside its text on ONE line, a 24px icon before a README's `<h1>` name, keeps the row's rule, the line being
// what the reader has at the edge (picInLine, by the row's line-height: the picture's rule held
// the icon and let the heading's text rise by the line's growth, 4.5px per step at 380, where the row's holds the text and
// the icon falls with its baseline); and the text under such a row's picture keeps its distance from the picture's bottom
// scaled by the row's line-height, not by the part's height, so a pane drag that wraps the tagline under the name holds the
// name and the tagline's line where they were (the part's fraction moved the name 3.6 to 4.6px on the drag between 900 and
// 380 and the tagline's line 9.6 to 12.6, taking the wrapped lines for growth). Recorded and not fixed (round 8): the band
// ROW_SHOWN leaves and the top-level picture's, at ROW_SHOWN. Recorded and not fixed (round 6): the badges-then-logo header read from RAW with a row of
// the wrapper's block BEFORE the badge line at the edge, the opener, the `<h1>` or the blank before the opener, comes
// back 245 to 454px high, the second face of the residual the badge row's 2px tail is the first of (the plan's item
// 1b): the Raw carry names the badge line at its row's distance, Rendered puts the badges there with the logo, 96px
// taller on the same baseline, reaching above the edge, and the way back reads the logo, the picture the edge is
// inside, whose row the Raw seat puts at that fraction; that Rendered geometry is the one a reader 60 to 78px into the
// logo makes, whose own trip must read the logo to invert, so no rule of the Rendered view alone tells the two apart
// (701728eae's first-in-DOM carry inverted these rows by accident and lost the logo's own trips, 129 to 440px). The
// one rule that inverts every one of these scenes is a wider unit, the pictures of CONSECUTIVE tag lines as one box
// in both reads; it changes which Raw row tops the view from the logo at the edge (the badge line's, not the logo's,
// which the html leg's test 12 pins) and waits on the owner's word.
// A same-view reflow in Rendered (a text-size step, the pane dragged, the Comments aside opening or closing) with a
// shown row of a wrapper's block's own at the edge, its summary, a lead `<h1>` or `<p>`, the picture's own `<p>`, puts
// that row back where it was (Place.lead: the block, the row's ordinal among the block's own rows, its box; seated as the
// picture is, at its fraction of its height when the edge is inside it, at its distance below the edge otherwise), the
// Rendered counterpart of the Raw rule below (round 5: the kept block, nested after the row or after a shut fold, kept
// its distance and the row's own growth landed above the edge, a wrapping fold title 90px above it on a drag from 900 to
// 380px and 180 to 190 down after the drag back, 23 above it when the aside opened, 4.5 to 4.9 per text-size step, where
// before the slice the browser's own anchoring held it within 0.2px; the picture outranks the row when the edge is
// inside the picture, or the picture ends above the edge in the row the edge is in, the text right under it at the edge,
// or the picture stands at or above the row's own top and the row holds one of its line's pictures, since a row's box can
// stand poorly for its picture's: an inline `<a>` around a logo has its font's box, 18px at the picture's bottom, so a
// text-size step seated by the row held that box and let the logo fall by the font's growth, 2.1px per step and 4.3 over
// two, and the `<p>` around a logo and the project's name, seated by the `<p>`'s fraction, drifted 1.9 to 2.9 per step,
// where 701728eae's picture rule alone had held both within 0.1 (round 6); a row whose own text stands above its picture,
// the project's name over the logo, keeps the row's rule with the edge in that text, since that text is what the reader
// sees (round 7: taken for holding the picture, the picture's rule let the name rise 2.9 to 6.9px per text-size step
// where the row's held it within 1.3 over two); the row is still never the place, which is the nested block, and never
// seated across a view switch: across one the picture's row is seated as the picture, above). When the reader is
// partway into a block that shows LINES (any block in Raw; in Rendered a markdown code block, fenced or indented, whose
// code element shows the block's lines one for one), the line at the edge is kept too, as its own source span and its
// top edge: the Raw row under the edge, or, in Rendered, the code's row under the edge (code-block.ts wraps every fence
// in one `.cl` row per line, blank lines included, and the row is read as a Raw row is: the first whose box ends below
// the edge, its box's top). The row's top on both sides, never a glyph's or a Range's (the Slice 3 review, round 2: a
// blank line's row holds no character, so the hit test read no line and the seat fell to the block fraction, a Range
// around the empty row read back a zero-height rect at its baseline, 9px under the row's top, and a text row read at
// its glyph's top, 2px under the row's, left the row above it showing at the Raw edge, so the way back kept that row
// instead; a blank row at the edge and every code line under one came back 14 to 17px high). A code element with no
// rows keeps the depth rule below: the viewer builds none (file-view.ts mdBlock wraps every `pre code` but the math
// fill's source fallback, whose block opens with `$$` or `\[` and is no code block to codeOf), so the hit test Slice 2
// read a code line with (caretRangeFromPoint on the code's first column, a one-character Range for the line's top),
// kept for such an element and documented as the math fill's, reached no DOM of the viewer's and went (the Slice 3
// review, round 3). An html block's `<pre>` is not a code block here: its lines and the block's are one off (the
// block's first line is the tag), so it keeps the depth rule below, within a line. After the paint the block is found
// in the new view, whichever view it is, and the body is scrolled so it sits where the block sat:
//   - a block that started below the edge keeps that distance;
//   - a block the reader was partway into keeps the LINE when one was kept and it still STANDS (its own span followed
//     through the edit, followPassage's `moved`): the row goes where the line's top was, so line 50 of a code block is
//     line 50 after the switch, after a reload that inserted five lines above
//     it inside the block (the review round 2: the block's top held and line 45 stood at the edge), and after one that
//     deleted five below it. A line the write rewrote, or one whose text recurs so that no copy is its own, is no line
//     to follow, and the depth rule applies (the review round 3: a walk to the line after the nearest standing
//     predecessor seated the edit's first line, 44 rows up, when every line between was a copy; a rewritten line's
//     neighbours inside the edit cannot place it exactly, so the rule is kept to the scene it wins, a line that
//     stands). Otherwise the DEPTH is kept. As a fraction of the block's height when the block is the same text (a
//     view switch, a reflow of the same text): the height differs between the views (a 60-row table is 1800px
//     rendered and 1100px raw, a 600px figure one raw row) and changes with the column's width, and the fraction
//     keeps the words at the edge near the edge, so row 45 of the table comes back near row 45 and a reader 400px into
//     the figure comes back 400px into it (the review: the top-edge offset alone put the table's first row 1300px
//     above the edge, past its last row in Raw, and the reader four paragraphs on after the figure; and a Raw row's
//     offset seated the whole block at the row's height, so line 50 came back as line 1). In pixels when the write
//     REPLACED the block (the block under the eye rewritten, or a block whose line at the edge is gone with no line of
//     it standing on either side): a reader 30px into a paragraph a session appended a sentence to stays 30px in, and
//     a block now SHORTER than it was, by however much, is moved down by the difference, to the edge at most, so as
//     much of it shows below the edge as showed of the block before (the review: a one-line replacement for a
//     two-line paragraph the reader was 30px into sat wholly above the edge; a block that lost two of five lines while
//     the reader was 30px in reaches the edge and shows whole).
//   - a block DELETED under the reader's eye (the blocks before and after it now adjacent, so nothing stands in its
//     place) is read as replaced by nothing: the block after it is seated as a replacement of no height would be, at
//     the edge when the deleted block reached below it, at the deleted block's old distance below the edge otherwise
//     (the review round 2: the successor inherited the reader's depth into the deleted block, its first line above
//     the edge though the reader never read into it).
//   - a body at its very top stays at its very top: the views pad differently (14px rendered, 10px raw), so seating
//     the first block at the other view's padding drifted a round trip from scrollTop 0 to 4.
//   - a reflow of the same Raw text (a text-size step, the pane dragged, the aside opening or closing) keeps the top ROW:
//     the row at the edge goes back where it was (Place.row), whatever the rows between it and the kept block grew or
//     shrank to, since the rows are the view's own lines and the reader's eye is on the top one (the Slice 5 review,
//     round 4: a comment's row, a closer's, a wrapper's opener or the blank before a fold's opener, read as the block
//     after them, rose 5 to 11px per text-size step, 2.7px for each row between, where before the slice each was its own
//     block and held within half a pixel; a plain blank row between paragraphs rose 3px the same way, there and here);
//     and a reflow of the same RENDERED text with a row of a wrapper's block's own at the edge keeps that row the same
//     way (Place.lead, above; round 5).
// Across a reload the span is followed through the edit first (followPassage, the composer's own follow): a block
// after the inserted paragraphs shifts by their length, one before them keeps its offset, and one the write rewrote is
// placed by the block before it, followed the same way, so the reader lands on what replaced it; with that block
// rewritten too, by the block after (a session rewriting two paragraphs and adding a preamble above them); with both
// neighbours gone as well, by the nearest block before it that still stands, walking outward (the kept block is the
// one after it), else the nearest after (the review round 2: three paragraphs deleted and twenty inserted above fell
// to where the edit begins, the top of the document; now the paragraph after the deleted three); only with no block
// standing on either side does the place fall to where the edit begins.
//
// What the place refuses, and what it descends into. The anchor map pairs the Rendered elements to the blocks. Every
// block but an html block renders as one element; an html block of sibling tags renders as several, and the map's
// pairing across one is a resync on the blocks after it. An html block that opens a wrapper the browser nests the
// following markdown into (`<details>` with a blank line after its summary, a centred `<div>` around a heading, one
// whose closing tag is the document's last block or is missing) is paired to the wrapper itself (and, through the
// resync, to the wrapper's own children in the raw: its `<summary>`), each block nested in it to its own element inside
// the wrapper, and two html blocks a blank line apart (`<p>Alpha</p>` over `<p>Beta</p>`, a README's centred heading
// over its tagline) to one element each; anchor-map.ts renderedBlockWrappers names the wrapper (Slice 5 of the plan, the
// flattened walk: the tag scan over the block's raw says which tags it leaves open, and the pairing takes the open
// element's children into the block table right after it). Before that walk the wrapper's block took every element after
// it, since no later top-level element carried a nested block's text (the Slice 2 review, round 2, and the plan's defect
// "an unclosed HTML wrapper swallows later blocks": read as that block, a Raw switch from paragraph 80 landed on
// `<summary>`, 3500px up), a wrapper closing last or never took exactly one element, itself, holding every paragraph
// after it (round 4: the Raw switch from a nested paragraph 60 landed on the `<div align="center">` row with the passage
// 1395px below the viewport, and the paragraph's Raw row switched to Rendered borrowed the wrapper's box and landed on
// paragraph 43), and the two adjacent html blocks paired as nothing and both; this module refused every element of such
// a run and every seat into one. Now the Rendered view is read through the root's element children and DESCENDS: an
// element the map names as a wrapper stands for the blocks nested in it, so its element children are read in its place,
// in order and recursively (a wrapper inside a wrapper); an element paired to a wrapper's block that is not itself one
// of the block's wrappers (the summary; a tag the block closed before opening the wrapper) is a row of the block's own,
// never the place, and is passed over for the block after it, so the wrapper's box at the edge reads the first nested
// block (the owner's rulings for Slice 5: the wrapper's own rows are never the place in either direction, and the edge
// inside a wrapper reads what is nested there; a closed `<details>`, whose nested content the browser does not show, reads
// the block after it: boxOf reads that content as no layout by checkVisibility, since Chromium lays a shut fold's content
// out all the same and the first hidden paragraph's rect coincides with the block after the fold's). Each level is
// searched on its own (topVisibleIndex over that level's children, then the descent into the child the search lands
// on), not over one flattened list: the map's index checks the root's shape, every child by
// identity, on each read, so a read per top-level child would cost the square of the document on every scroll frame.
// An html block's pairing to one element or several is trusted only when its own source, parsed by the browser's HTML
// parser (DOMParser), yields as many elements with the same text, whitespace and the viewer's own controls apart (a
// gated figure's placeholder, a fence's Copy button: their text is the viewer's, never the block's, and is skipped as
// the anchor map skips it; the Slice 4 review found a `<p>` holding a gated picture read "Image from host. Click to
// load." against a parse reading nothing, and the figure at the edge refused). That parser is the one the sanitizer
// read the block with, so entities, inline tags and line breaks decode the same on both sides and nothing is decoded by
// hand (the review round 3: a hand decoder threw on an out-of-range numeric entity, which stopped the Raw click and the
// text-size step where it stood, and knew six entity names, so a caption hanging on `&mdash;` read as swallowed). Any
// other block's one element is trusted without a parse (its source is markdown, not html; a paragraph nested in a
// wrapper is such a block); an html block is told from the rest by marked's lexer over its own text, the lexer the
// map's table comes from, asked only for a block that opens with `<`. A pairing the parse does not confirm reads as NO
// place from whichever element is at the edge, so the numeric scrollTop stands, as it did before the slice; and a seat
// that would borrow such a block's box for a block with no element of its own declines the same way, the body unmoved.
// The wrapper's own block is one such pairing in the SEAT direction: its source parses to one element, the wrapper with
// the summary's text or with none, against the wrapper holding the nested paragraphs' text (and its summary beside it),
// so the wrapper's own block is never seated (the review round 3: a Raw row of `<summary>` seated the whole swallowed
// run, 3200px, in Rendered; kept under Slice 5, ruling 2); since the Slice 5 review's round 2 its Raw rows are read as
// the first block nested in it (readPlace, the header), so a Raw row of `<div align="center">` or `<summary>` switched
// to Rendered seats that block where its own row was, where a Raw row of a nested paragraph seats at the paragraph's
// own element, and a Raw row of the closing tag reads as the block after it (as the document's last block, its own
// place, seated at the nearest block before it with an element, the last nested paragraph). An html block of sibling tags,
// each in its source, is read as one block still. Where DOMParser is absent (a stand-in) such a block reads as no place
// too. Two shapes the parse reads as no place though the pairing is right, both malformed input and each recorded in
// the plan's Slice 2 build note: an html block holding a tag the sanitizer removes, when the removal changes the block's
// text (a `<script>` or `<style>` inside a tag goes with its text) or its element count (a `<style>`, an `<iframe>` or a
// form control between two `<p>`s goes, the control's text staying as a text node), parses to other elements or other
// text than the sanitizer kept (a removed tag nested inside a tag, its text kept as a `<label>`'s is or none as an
// `<iframe>`'s, is trusted as ever); and a hex character reference with no digits (`&#x;`), which Chromium decodes to
// U+FFFD when its fast-path parser reads a short string of simple tags (the block's source alone) and keeps as the
// literal text when its full parser reads it, which the sanitizer's whole-document parse is whenever the note holds a
// tag outside that path's subset (a heading, a code block, emphasis, a picture), so the two sides disagree on that one
// form in nearly every note. Every other entity form, valid or not, decodes alike on both sides.
//
// Written over the DOM the viewer builds and nothing else (querySelector, childNodes, getBoundingClientRect,
// checkVisibility where the browser has it, scrollTop, and one style, a row's computed line-height where the document has
// one: lineHeightOf) and the anchor map's block table, so a stand-in with no layout
// (every box at 0,0) reads no place and seats nothing, and the node tests over the viewer run unchanged; the browser legs
// (file-view-place-browser.test.ts, file-view-place-blocks-browser.test.ts, file-view-place-edits-browser.test.ts,
// file-view-place-html-browser.test.ts, file-view-place-wrapper-end-browser.test.ts,
// file-view-place-closed-details-browser.test.ts) measure the real thing.
import { Lexer } from "marked";
import { followPassage } from "./file-comments";
import { sourceBlockSpans, renderedBlockIndex, renderedBlockElements, renderedBlockWrappers, rawRows, rawRowForOffset, rawRowSpan, commentsOnly, type SourceRange } from "./anchor-map";

export type View = "rendered" | "raw";
/** A line of the kept block at the body's top edge: the span of its text in the file (before its line ending) and its
 *  top edge measured from the body's top. */
export type Line = SourceRange & { top: number };
/** Where the reader is: the file text the view was painted from and which view it was; the source span of the
 *  top-visible block in it; that block's top edge measured from the body's top edge (negative when the reader is
 *  partway into it) and its box's height in that view; whether the body stood at its very top; the spans of the
 *  blocks before and after it, the first fallbacks when the write rewrote the block itself; and, when the reader is
 *  partway into a block that shows lines (a Raw block, a Rendered code block), the line at the edge. */
export type Place = {
  source: string; view: View;
  start: number; end: number;
  top: number; height: number;
  atTop: boolean;
  prev: SourceRange | null; next: SourceRange | null;
  line?: Line | null;
  row?: Line | null;
  after?: Stand[];
  pic?: Pic | null;
  lead?: Lead | null;
};
/** Place.row: the Raw row at the body's top edge when the kept block starts at or below the edge (a blank row between
 *  blocks, a row read as the block after it, the block's own first row at the edge), as its span and its top; a reflow of
 *  the same Raw text (a text-size step, the pane dragged, the Comments aside opening or closing) puts that row back where
 *  it was, whatever the rows between it and the kept block grew or shrank to (the header). Partway into the block the row
 *  is Place.line, and this is unset. */
/** A block after a `<details>` the kept block lies in, read in Raw (the header): its source span and its first row's top
 *  edge measured from the body's top. The seat stands on the first of these the Rendered view shows when the kept block
 *  is not shown (the fold shut), where the kept block itself has no box and the block after it is what the reader had,
 *  no lower than the fold's summary at the edge (seatPlaceOutcome). An EMPTY list is a block inside a fold with nothing
 *  standing after it (the fold ends the document, or only a comment, a wrapper's end or a reference definition follows
 *  it): the seat then stands on the fold's summary at the edge, the cap's own limit; a place with no list at all is one
 *  read in no fold, or of another making, and a fold's hidden block seats nothing from it. */
export type Stand = SourceRange & { top: number };
/** A picture of a wrapper's block's own with the reader's edge inside it, or below the edge with a row of the block's own
 *  at the edge above it (the header): the source span of the line its `<img` tag starts on, and the box one Raw row of that
 *  line inverts, from the body's top edge. In Raw the line's row. In Rendered the box of every `<img>` whose tag starts on
 *  that line together (the line's pictures are ONE box to both reads, since one Raw row cannot tell them apart: a logo and a
 *  badge on one line, a common baseline, are read and seated as their union; linePictures), or, when the line's pictures all
 *  sit in one row of the block's own that holds text of the note's beside them and whose box contains them (the
 *  `<p align="center">` around the logo, a `<br>` and the project's name; the `<p>` around a linked logo and its tagline), that
 *  ROW's box (rowOfLine, lineBoxes): the row's line is the one Raw row, and the text under the picture is part of what it
 *  inverts (the review's round 7: from the text under the picture the Rendered read carried no picture, the union ending above
 *  the edge, and seated the nested heading at its distance, the Raw read carried the row's line as the picture's, and the way
 *  back put the pictures' union at the row's fraction, the name 32 to 71px down). `imgs` is then the pictures' own box beside
 *  the row's, which a same-view reflow holds when the edge is inside the picture or right under it (picOutranksRow): the text
 *  grows and the picture does not, so the row's fraction drifted the picture 1.9 to 2.9px per text-size step (round 6); `lh` is
 *  then the row's line-height as read (lineHeightOf), which the text under the picture keeps its distance from the picture's
 *  bottom by across the reflow (rowPartsTop; round 8), unset where the document has none to read. The
 *  seat puts the box, or its row, at the same fraction of its height when the edge is inside it, as it does a top-level
 *  picture, and at the same distance below the edge otherwise, as any block that starts below the edge keeps its own. */
export type Pic = SourceRange & { top: number; height: number; imgs?: { top: number; height: number }; lh?: number };
/** The shown row of a wrapper's block's own at the body's top edge in RENDERED (its `<summary>`, a README's lead `<h1>` or
 *  `<p>`, the `<p>` or `<a>` around its picture, the picture itself: the row readRendered passes over for the block nested
 *  after it; the header): the wrapper's block as its source span, the row's ordinal among the block's own rows in document
 *  order (`k`: renderedBlockElements less the block's wrappers, the index Place.pic's picture is found by), and the row's box
 *  from the body's top edge. A reflow of the same Rendered text (a text-size step, the pane dragged, the Comments aside opening
 *  or closing) puts that row back where it was, at the same fraction of its height when the edge is inside it and at the same
 *  distance below the edge otherwise, as Place.pic seats the picture and Place.row the Raw row (seatPlaceOutcome); the picture
 *  outranks the row when the edge is inside the picture or right under it, or the picture stands at or above the row's own top
 *  and the row holds one of its line's pictures (picOutranksRow: an inline `<a>` around a logo has its font's box, not the
 *  logo's; a row whose text stands over its picture keeps its rule, and so does one whose pictures stand beside its text on
 *  one line, picInLine); a view switch or other text leaves it unused (the review's round 5:
 *  the kept block's distance alone let the row's own growth land above the edge, a wrapping fold title 90px above it on a drag
 *  from 900 to 380px). The row itself is never the place: Place names the nested block still (the owner's rulings 2 and 13). */
export type Lead = SourceRange & { k: number; top: number; height: number };

type Box = { top: number; bottom: number };

/** The index of the first of `count` boxes, stacked top to bottom, whose bottom edge lies below `edge`; `count` when
 *  none does. A binary search over the boxes' bottoms, which increase down a column of blocks (a Rendered view's
 *  top-level elements, a Raw view's rows), so a long document costs a handful of box reads per scroll frame, not one
 *  per block. Two kinds of box break the order and are read around. A box with no layout at all (a hidden element;
 *  `bottomOf` answers NaN) is passed over for the next box with one, in the search and in the answer, so a hidden
 *  element below the reader on the search's path cannot send it past every block before it (the Slice 2 review: a
 *  `<div hidden>` at the search's first probe read as above the edge and the place was read twenty-four blocks below
 *  the reader). A floated or positioned figure that reaches below the blocks beside it (the paragraphs wrapping an
 *  `<img align="left">`) is a box whose successors end above the edge: the top block is then the first of those that
 *  ends below it, the paragraph the reader is reading beside the figure, whichever box the search happened to land
 *  on, and that paragraph is what a view switch or a reflow keeps (the figure, kept instead, is one row in Raw and
 *  moves when the paragraphs beside it grow taller). When no box at all ends below the edge, the last TAIL boxes are
 *  read for a figure at the document's end that still does. */
const TAIL = 8;
export function topVisibleIndex(count: number, bottomOf: (i: number) => number, edge: number): number {
  let lo = 0, hi = count;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    let m = mid, b = bottomOf(m);
    while (Number.isNaN(b) && m + 1 < hi) b = bottomOf(++m);
    if (Number.isNaN(b)) hi = mid;                    // no box with a layout from mid on: the answer, if any, lies before mid
    else if (b > edge) hi = m; else lo = m + 1;
  }
  while (lo < count && Number.isNaN(bottomOf(lo))) lo++;   // the answer is a box with a layout
  if (lo === count) {
    for (let i = count - 1, k = 0; i >= 0 && k < TAIL; i--, k++) if (bottomOf(i) > edge) return i;
    return count;
  }
  let j = lo + 1, above = false;
  for (; j < count; j++) { const b = bottomOf(j); if (Number.isNaN(b)) continue; if (b > edge) break; above = true; }
  return above && j < count ? j : lo;
}

/** The index of the block, among `spans` in source order, whose start is the largest at or below `offset`; -1 when
 *  none starts there or before. */
export function blockIndexAt(spans: SourceRange[], offset: number): number {
  let lo = 0, hi = spans.length - 1;
  if (hi < 0 || spans[0].start > offset) return -1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (spans[mid].start <= offset) lo = mid; else hi = mid - 1;
  }
  return lo;
}
/** The block holding `offset` (its start at or before it, its text's end after it), else the block after the gap the
 *  offset lies in (a blank line between two blocks, a reference definition; the first block for one before it); -1 for
 *  an offset past the last block's text. */
export function blockHolding(spans: SourceRange[], offset: number): number {
  const k = blockIndexAt(spans, offset);
  if (k < 0) return spans.length ? 0 : -1;
  return offset < spans[k].end ? k : k + 1 < spans.length ? k + 1 : -1;
}

const elementsOf = (n: Node): Element[] => Array.from(n.childNodes).filter((c) => c.nodeType === 1) as Element[];
const hasBox = (n: unknown): n is Element => !!n && typeof (n as Element).getBoundingClientRect === "function";
/** An element's box, or null for one with no layout: every edge 0 and no client rect (display: none, a `hidden`
 *  attribute the sanitizer keeps; a stand-in with no layout reads the same, and so keeps no place), or an element the
 *  browser does not SHOW though it answers a rect (checkVisibility false). The content of a closed `<details>` is the
 *  second kind: Chromium skips it through the fold's `::details-content` pseudo-element (content-visibility: hidden) and
 *  still lays it out on a forced read, so a paragraph inside a shut fold answers a full box and a client rect, the fold's
 *  blocks stacked from where it would open, the first coinciding with the block after the fold's (the Slice 5 review,
 *  round 1: read by its rect, the hidden paragraph was the place, and the Raw switch seated the fold's hidden source at
 *  the edge under the summary's row where the reader had the block after the fold in view; the plan's rule for a closed
 *  fold, the block after it, had assumed the content has no layout; md-config-goto-closed-details-browser.test.ts and
 *  anchor-map-obsidian.test.ts record the same phantom under a highlight). checkVisibility is the browser's own answer
 *  to "is this shown", and the one thing that tells the phantom from the block it coincides with; where a browser
 *  offers none (a stand-in) the rect alone decides, as before. */
function boxOf(el: Element): Box | null {
  const r = el.getBoundingClientRect();
  if (r.top === 0 && r.bottom === 0 && r.width === 0 && r.height === 0 && (typeof el.getClientRects !== "function" || el.getClientRects().length === 0)) return null;
  if (typeof el.checkVisibility === "function" && !el.checkVisibility()) return null;
  return { top: r.top, bottom: r.bottom };
}
const bottomOrNaN = (el: Element): number => { const b = boxOf(el); return b ? b.bottom : NaN; };
/** An element's computed line-height in pixels (the browser resolves the sheet's `line-height: 1.5` to a length), the one
 *  style this module reads: the height of one line of a row's text, which tells a picture beside the row's text on one line
 *  from one on a line of its own (picInLine) and scales the text under a row's picture across a same-view reflow (rowPartsTop;
 *  the review's round 8). NaN where the document has no computed style to read (a stand-in) or the value is no length
 *  (`normal`), and the rules that read it stand down to the ones before them. */
function lineHeightOf(el: Element): number {
  const w = typeof window !== "undefined" ? window : null;
  if (!w || typeof w.getComputedStyle !== "function") return NaN;
  try { const v = parseFloat(w.getComputedStyle(el).lineHeight); return v > 0 ? v : NaN; } catch { return NaN; }
}
/** The boxes together: the topmost top to the bottommost bottom; null when none has a layout. */
function union(boxes: (Box | null)[]): Box | null {
  let out: Box | null = null;
  for (const b of boxes) { if (b) out = out ? { top: Math.min(out.top, b.top), bottom: Math.max(out.bottom, b.bottom) } : b; }
  return out;
}
/** Block `b`'s box in the Rendered view: its elements' boxes together (an html block of sibling tags), null when none
 *  has a layout or the pairing is not trusted (ownedElements). */
const renderedBlockBox = (md: Element, source: string, spans: SourceRange[], b: number): Box | null => { const els = ownedElements(md, source, spans[b], b); return els ? union(els.map(boxOf)) : null; };
/** A block's box in the Raw view: the row of its first line through the row of its last. */
function rawBlockBox(code: Element, source: string, span: SourceRange): Box | null {
  const first = rawRowForOffset(code, source, span.start), last = rawRowForOffset(code, source, Math.max(span.start, span.end - 1));
  const a = first && boxOf(first), z = last && boxOf(last);
  return a && z ? { top: a.top, bottom: z.bottom } : null;
}
const placeOf = (source: string, view: View, spans: SourceRange[], b: number, box: Box, edge: number, atTop: boolean, line: Line | null): Place => ({
  source, view, start: spans[b].start, end: spans[b].end, top: box.top - edge, height: box.bottom - box.top, atTop,
  prev: b > 0 ? spans[b - 1] : null, next: b + 1 < spans.length ? spans[b + 1] : null, line,
});

// ── the elements paired to a block: trusted, or a pairing the map got wrong (the header's "what the place refuses") ──
const stripWs = (s: string): string => s.replace(/\s+/g, "");
/** The classes of the elements the viewer builds inside the rendered markup, whose text is the viewer's and not the
 *  note's: the fence's Copy button (code-block.ts), a formula KaTeX rendered (math.ts), a footnote's back link and the
 *  front matter's fold label (md-config.ts), a gated figure's placeholder (figure-gate.ts). These five are in
 *  anchor-map.ts's CONTROL_CLASSES, which every text walk there skips (isControl). That list also holds the fill's two
 *  fallback shapes (`katex-error`, `md-math-src`: the TeX shown as text), which are NOT skipped here on purpose: the
 *  map's tokens make a formula a zero-text hole, but an html block's fallback can only come from a placeholder the
 *  author typed, whose TeX the parse of the block's source reads too, so the texts agree and the pairing holds. */
const CONTROL_CLASSES = ["code-copy", "katex", "md-fnback", "md-frontmatter-head", "fv-gate"];
const isControl = (n: Node): boolean => {
  if (n.nodeType !== 1 || typeof (n as Element).getAttribute !== "function") return false;
  const c = " " + ((n as Element).getAttribute("class") || "") + " ";
  return CONTROL_CLASSES.some((cls) => c.indexOf(" " + cls + " ") >= 0);
};
/** A rendered node's text as the anchor map reads it: its text nodes' data with the viewer's controls skipped, the node
 *  itself when it is one (a bare `<img>` line on a gated host renders as the placeholder alone). textContent read the
 *  controls' labels too, so an html block holding a gated picture read "Image from host. Click to load." against a parse
 *  of its source reading nothing, and its pairing was refused as a wrong one: the Raw switch from the figure at the edge
 *  seated nothing and the way back landed fourteen paragraphs past it (the Slice 4 review). */
function noteText(n: Node): string {
  if (n.nodeType === 3) return (n as Text).data;
  if (isControl(n)) return "";
  let s = "";
  for (let i = 0; i < n.childNodes.length; i++) s += noteText(n.childNodes[i]);
  return s;
}
/** Whether the block is an html block (marked's `html` token), the one kind whose element count the map's pairing
 *  guesses. Every kind of html block opens with `<` after at most three spaces, so a block that does not is none and
 *  costs no lex (every paragraph); one that does is lexed alone, by the lexer the anchor map's block table comes from:
 *  a block's kind is decided at its first line, at a block's start either way, so the block's own text lexes to the
 *  token it lexed to inside the file (a paragraph opening with an inline tag or an autolink lexes to a paragraph). */
function isHtmlBlock(source: string, span: SourceRange): boolean {
  if (!/^ {0,3}</.test(source.slice(span.start, Math.min(span.end, span.start + 4)))) return false;
  try { const t = Lexer.lex(source.slice(span.start, span.end))[0]; return !!t && t.type === "html"; } catch { return false; }
}
/** Whether the block is closing tags alone (`</details>`, `</div>`, `</details>\n</div>`, `</details></div>`, after at
 *  most three spaces, nothing else on its lines): the end of a wrapper the browser nested markdown into, or of two
 *  nested ones closed on consecutive lines or on one line, which marked lexes as one html block; it owns no element
 *  (anchor-map.ts pairs it to none, as a comment's block) and renders nothing of its own, so its Raw row is read as a
 *  blank row between blocks is (the Slice 5 review, round 2: one closing tag alone was accepted, so `</details>\n</div>`
 *  stayed its own place and seated the last nested paragraph at the row, 63 to 144px off). */
const closesAlone = (source: string, span: SourceRange): boolean => /^ {0,3}(?:<\/[a-zA-Z][\w:-]*\s*>\s*)+$/.test(source.slice(span.start, span.end));
/** Whether the block is html comments alone, whitespace between them (`<!-- a note to self -->`): it renders nothing, so
 *  its Raw row is read as a closing tag's is. The pairing's own reading (anchor-map.ts commentsOnly, which gives such a
 *  block no node), so the two agree on which block is a comment's. */
const isCommentBlock = (source: string, span: SourceRange): boolean => commentsOnly(source.slice(span.start, span.end));
const PROBE = "data-romp-place-probe";
/** The element carrying the probe attribute under `n`, by a walk over the parsed block (a stand-in's parser offers no
 *  attribute selector). */
function probeIn(n: Node): Element | null {
  for (let i = 0; i < n.childNodes.length; i++) {
    const c = n.childNodes[i];
    if (c.nodeType !== 1) continue;
    if (typeof (c as Element).getAttribute === "function" && (c as Element).getAttribute(PROBE) !== null) return c as Element;
    const inner = probeIn(c);
    if (inner) return inner;
  }
  return null;
}
/** Whether the html block opens a wrapper the browser nests the markdown after it into (`<div align="center">`, a
 *  `<details>` with its summary, `<div><div>`), told by the browser's own parser: the block's source with a paragraph
 *  appended, as marked renders the block after it, parsed by DOMParser (the parser the sanitizer read the block with,
 *  as ownedElements uses it), and the paragraph read back nested inside an element of the block's rather than beside it.
 *  A `<p>` and not a made-up tag, since the parser closes a `<p>` the block leaves open when the next block's own tag
 *  comes (every block marked renders opens with one that does), so no markdown nests in it, and foster-parents one out
 *  of an unclosed `<table>`, as it does the markdown after such a block; anchor-map.ts's tag scan (topTags) reads the
 *  same implied ends by hand for the pairing. Such a block's own element is never seated (ownedElements refuses it), so
 *  its rows read as the first block nested in it (readsAsNext, the header). False for any other block, for an html block
 *  that closes what it opens (`<p>Alpha</p>`), and where DOMParser is absent (a stand-in), which then keeps the block as
 *  its own place, as before. */
function opensWrapper(source: string, span: SourceRange): boolean {
  if (!isHtmlBlock(source, span) || typeof DOMParser !== "function") return false;
  const body = new DOMParser().parseFromString(source.slice(span.start, span.end) + "\n<p " + PROBE + "></p>", "text/html").body;
  const probe = probeIn(body);
  return !!probe && probe.parentNode !== body;
}
/** Whether a Raw row of block `b` reads as the block after it (the header): the block renders nothing of its own (closing
 *  tags alone, comments alone) or is an html block that opens a wrapper, whose own element is never seated. The answer is
 *  a function of the block's own text alone (two scans of it, and for a block opening with `<` opensWrapper's lex, and for
 *  an html token its parse, of the whole block), so it is kept per block for the last source read, as foldDepths keeps the
 *  fold table: a new source is the one event that changes it, and a scroll frame or a reflow over the same text reads the
 *  kept answer (the Slice 5 PR's review, round 1: readPlace runs once per scroll frame in Raw and asked this of the top
 *  row's block on every frame, so a large html block with any block after it, an .html or .xml file ending in a comment,
 *  a note with one big html block, was lexed and parsed whole per frame with a walk over the parse, about 15 ms of a
 *  16.7 ms frame in headless Chromium; the document's last block is never asked, nextShown stopping before it, so a file
 *  that is one html block cost nothing either way). Filled as blocks are asked, not for the whole table at once: one lex
 *  and one parse per html block whose row tops the view or lies in a run the top row reads past, or that a fold the
 *  place carries hands to foldStands, over the life of the source. */
let nextCache: { source: string; next: Int8Array } | null = null;   // per block: -1 not asked yet, 0 false, 1 true
function readsAsNext(source: string, spans: SourceRange[], b: number): boolean {
  if (!nextCache || nextCache.source !== source || nextCache.next.length !== spans.length) nextCache = { source, next: new Int8Array(spans.length).fill(-1) };
  let v = nextCache.next[b];
  if (v < 0) { v = closesAlone(source, spans[b]) || isCommentBlock(source, spans[b]) || opensWrapper(source, spans[b]) ? 1 : 0; nextCache.next[b] = v; }
  return v === 1;
}
/** The block a Raw row of block `b` reads as: `b` itself, or the first block after it past a run of blocks that read as
 *  the block after them (readsAsNext); the document's last block whatever it is. */
function nextShown(source: string, spans: SourceRange[], b: number): number {
  while (b + 1 < spans.length && readsAsNext(source, spans, b)) b++;
  return b;
}
/** For each block, how many `<details>` are open where it starts, from the source alone: the details tags of the blocks
 *  before it in order, an end tag closing the innermost open one, a fence's or an indented code block's text and comments
 *  skipped. The Rendered view's fold state is not read here (a fold the person opened or shut stays so across a paint,
 *  file-view.ts's fold keeper, and the Raw view has no DOM of it), only which blocks a fold holds, so the seat can be
 *  handed the block after the fold (Place.after) and decide by the DOM whether the kept block is shown. Kept for the
 *  last source read, as the anchor map keeps its block table: the viewer reads the same text once per scroll frame. A
 *  details tag inside inline code miscounts one block's depth, which costs nothing when the block is shown (the seat
 *  reads the DOM first) and leaves a shut fold's row to the refusal it had when it is not. */
let foldCache: { source: string; depth: Int32Array } | null = null;
const CODE_HEAD = /^ {0,3}(?:`{3,}|~{3,})|^(?: {4}|\t)/;
const DETAILS_TAG = /<!--[\s\S]*?(?:-->|$)|<(\/?)details(?=[\s>\/])[^>]*>/gi;
function foldDepths(source: string, spans: SourceRange[]): Int32Array {
  if (foldCache && foldCache.source === source && foldCache.depth.length === spans.length) return foldCache.depth;
  const depth = new Int32Array(spans.length);
  let d = 0;
  for (let b = 0; b < spans.length; b++) {
    depth[b] = d;
    const text = source.slice(spans[b].start, spans[b].end);
    if (text.indexOf("<") < 0 || CODE_HEAD.test(text) || !/details/i.test(text)) continue;
    DETAILS_TAG.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = DETAILS_TAG.exec(text))) { if (m[0].startsWith("<!--")) continue; if (m[1]) { if (d > 0) d--; } else d++; }
  }
  foldCache = { source, depth };
  return depth;
}
/** The blocks the seat stands on when block `b`, read in Raw, is inside a `<details>` the Rendered view folds shut
 *  (Place.after, the header): the first block after that fold that reads as its own place (nextShown), with its first
 *  row's top from the body's top; then, when that block lies in a fold itself (a fold right after a fold, a README's
 *  run of shut sections), the first block after that one, and so on out to a block in no fold. null for a block in no
 *  fold; for a block in a fold the list, EMPTY when nothing after the fold reads as its own place (the fold ends the
 *  document, or only a comment or a wrapper's end follows it), which the seat reads as "stand on the fold's summary at
 *  the edge" (the review's round 6: null there left the seat to walk back through the hidden paragraphs to the wrapper's
 *  refused block and seat nothing, the summary off the pane at 380px). */
function foldStands(code: Element, source: string, spans: SourceRange[], b: number, edge: number): Stand[] | null {
  const depth = foldDepths(source, spans);
  if (!(depth[b] > 0)) return null;
  const out: Stand[] = [];
  for (let k = b, d = depth[b]; d > 0;) {
    let j = k + 1;
    while (j < spans.length && depth[j] >= d) j++;
    if (j >= spans.length) break;
    j = nextShown(source, spans, j);
    if (readsAsNext(source, spans, j)) break;
    const box = rawBlockBox(code, source, spans[j]);
    if (!box) break;
    out.push({ start: spans[j].start, end: spans[j].end, top: box.top - edge });
    k = j; d = depth[j];
  }
  return out;
}
/** Block `b`'s elements when the pairing can be trusted, null when it cannot. None always can, and one element of any
 *  block but an html block (every other block renders as exactly one, a paragraph nested in an html wrapper included).
 *  An html block's, one or several, are trusted when the block's own source, parsed by the browser's HTML parser,
 *  yields as many elements with the same text, whitespace and the viewer's controls apart (noteText): the parser the
 *  sanitizer read the block with, so entities, inline tags and `<br>` decode alike on both sides and nothing is decoded
 *  here. A wrapper's own block is not (one element parsed, the wrapper with its summary's text or none, against the
 *  wrapper holding the nested paragraphs' text, and its summary beside it: the seat direction's refusal of the
 *  wrapper's own rows, the header), nor an html block a sanitizer drop reshaped, nor any such block where DOMParser is
 *  absent (a stand-in). Before Slice 5's walk the wrapper's swallowed run (one element parsed, the rest of the document
 *  paired), a wrapper closing last or never (one parsed with the block's own text, one paired holding every paragraph
 *  after it: the review round 4, which found the third round trusting any one element) and the second of two adjacent
 *  html blocks (one parsed, two paired) were refused here too; the map pairs those right now, and readPlace reads a
 *  wrapper's nested blocks through it (readRendered). */
function ownedElements(md: Element, source: string, span: SourceRange, b: number): Element[] | null {
  const els = renderedBlockElements(md, source, b);
  if (!els.length || (els.length === 1 && !isHtmlBlock(source, span))) return els;
  if (typeof DOMParser !== "function") return null;
  const parsed = elementsOf(new DOMParser().parseFromString(source.slice(span.start, span.end), "text/html").body);
  if (parsed.length !== els.length) return null;
  for (let i = 0; i < els.length; i++) if (stripWs(parsed[i].textContent || "") !== stripWs(noteText(els[i]))) return null;
  return els;
}

// ── a wrapper's own rows: its picture (Place.pic) and the row at the edge (Place.lead), the header ─────────────
/** An `<img` tag of a block's source, or an html comment, which is skipped: a commented-out tag (`<!-- <img src="old.svg"> -->`
 *  above the live one, a README's leftover) is no picture's, since the parser makes no element of a comment and the sanitizer
 *  keeps none, so counting it paired the k-th picture with the tag before its own and put the comment's row where the picture
 *  was (the review's round 5); the same alternative DETAILS_TAG skips comments by. */
const IMG_TAG = /<!--[\s\S]*?(?:-->|$)|<img(?=[\s/>])/gi;
const tagOf = (el: Element): string => String(el.tagName || "").toUpperCase();
/** The `<img>` elements under `n` in document order, `n` itself when it is one. */
function imgsIn(n: Element, out: Element[] = []): Element[] {
  if (tagOf(n) === "IMG") { out.push(n); return out; }
  for (const c of elementsOf(n)) imgsIn(c, out);
  return out;
}
/** Html block `b`'s own rows in the Rendered view: its elements that are not its wrappers (a `<summary>`, a README's lead `<h1>`
 *  and `<p>`, an `<img>` or the `<a>` or `<p>` around it), in document order; the order Place.lead counts by (Lead.k). */
const ownRows = (md: Element, source: string, b: number): Element[] => { const wrappers = renderedBlockWrappers(md, source, b); return renderedBlockElements(md, source, b).filter((e) => wrappers.indexOf(e) < 0); };
/** The pictures of html block `b`'s own rows in document order, every `<img>` under a row whether or not the row holds text of
 *  the note's beside it (a logo alone, a linked logo `<a><img></a>`, a line of badges, a `<p align="center">` holding the logo,
 *  a `<br>` and the project's name): one per `<img` tag of the block's source outside comments when the sanitizer kept them
 *  all, so the k-th picture is the k-th tag's (imgLine, imgIndexBefore). The one definition of the block's pictures for both
 *  views, the Raw read's through imgLine and the Rendered read's here (the review's round 5: the Rendered read had refused a
 *  picture in a row holding text while the Raw read counted it, so the two directions seated different things and a header of
 *  that common shape lost 64 to 82px on the round trip). A wrapper's nested blocks are other blocks, and their pictures are
 *  not counted. */
function picturesOf(md: Element, source: string, b: number): Element[] {
  const out: Element[] = [];
  for (const e of ownRows(md, source, b)) imgsIn(e, out);
  return out;
}
/** For each `<img` tag of block `span`'s source outside comments, in order, the line of the block it starts on (the line's
 *  span within the block): the k-th picture's line is the k-th entry (imgLine), and the pictures of one line are the entries
 *  with one start (linePictures). */
function pictureLines(source: string, span: SourceRange): SourceRange[] {
  const text = source.slice(span.start, span.end);
  const out: SourceRange[] = [];
  IMG_TAG.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = IMG_TAG.exec(text))) {
    if (m[0].charCodeAt(1) === 33) continue;   // `<!--`: a comment, no tag
    const at = span.start + m.index;
    let e = source.indexOf("\n", at);
    if (e < 0 || e > span.end) e = span.end;
    out.push({ start: Math.max(source.lastIndexOf("\n", at) + 1, span.start), end: e });
  }
  return out;
}
/** The line of block `span`'s source on which its k-th `<img` tag (0-based, comments skipped) starts, within the block; null
 *  when the block has no such tag. */
const imgLine = (source: string, span: SourceRange, k: number): SourceRange | null => (k < 0 ? null : pictureLines(source, span)[k] || null);
/** How many `<img` tags of block `span`'s source, outside comments, start before `offset`: the index of the first tag on the
 *  line there. */
function imgIndexBefore(source: string, span: SourceRange, offset: number): number {
  const text = source.slice(span.start, Math.min(Math.max(offset, span.start), span.end));
  IMG_TAG.lastIndex = 0;
  let n = 0, m: RegExpExecArray | null;
  while ((m = IMG_TAG.exec(text))) if (m[0].charCodeAt(1) !== 33) n++;
  return n;
}
/** The `<img>` elements of html block `b` whose tags start on the line at `lineStart` of its source, in document order: the
 *  pictures one Raw row holds, which are ONE box to both reads (Place.pic, the header; the review's round 6: read one by one, a
 *  logo and a badge on one line were carried as the badge, the picture the edge was inside, and seated as the logo, the line's
 *  first tag, 60 to 62px lost on the round trip). The k-th picture is the k-th tag's (picturesOf, pictureLines). */
function linePictures(md: Element, source: string, spans: SourceRange[], b: number, lineStart: number): Element[] {
  const pics = picturesOf(md, source, b), lines = pictureLines(source, spans[b]);
  const out: Element[] = [];
  for (let k = 0; k < lines.length && k < pics.length; k++) if (lines[k].start === lineStart) out.push(pics[k]);
  return out;
}
/** The row of html block `b`'s own whose box stands for the picture line whose pictures `pics` are, when one does (Pic, the
 *  header): the one row holding every picture of the line and no other line's, with text of the note's beside them (noteText,
 *  the anchor map's reading: a `<p align="center">` around the logo, a `<br>` and the project's name; the `<p>` around a
 *  linked logo and its tagline), never the picture itself. null for a line whose pictures are rows themselves (an `<img>`
 *  line, a line of badges in the wrapper), sit in a row holding no text (`<a href><img></a>`, `<p><img></p>`: the pictures'
 *  union is that row's box, less an inline anchor's font box, which stands poorly for the picture) or in two rows, or share
 *  their row with another line's pictures (one Raw row cannot invert two). */
function rowOfLine(md: Element, source: string, b: number, pics: Element[]): Element | null {
  if (!pics.length) return null;
  const row = ownRows(md, source, b).find((e) => tagOf(e) !== "IMG" && imgsIn(e).indexOf(pics[0]) >= 0);
  if (!row) return null;
  const own = imgsIn(row);
  if (own.length !== pics.length || pics.some((p) => own.indexOf(p) < 0)) return null;
  return stripWs(noteText(row)) ? row : null;
}
/** The Rendered boxes of the picture line whose pictures `pics` are (linePictures): `box`, the one box one Raw row of the line
 *  inverts (the row's, when rowOfLine names one and its box contains the pictures; the pictures' union otherwise: Pic), `imgs`,
 *  the pictures' union, the box a same-view reflow holds, and `lh`, the row's line-height when the row's box is the line's
 *  (lineHeightOf; NaN otherwise), which tells a picture beside the row's text on one line from one on a line of its own and
 *  scales the text under the picture across a reflow (picInLine, rowPartsTop). null when the view shows none of the pictures. */
type LineBoxes = { box: Box; imgs: Box; lh: number };
function lineBoxes(md: Element, source: string, b: number, pics: Element[]): LineBoxes | null {
  const imgs = union(pics.map(boxOf));
  if (!imgs) return null;
  const row = rowOfLine(md, source, b, pics);
  const rb = row ? boxOf(row) : null;
  if (row && rb && rb.top <= imgs.top + 1 && rb.bottom >= imgs.bottom - 1) return { box: rb, imgs, lh: lineHeightOf(row) };
  return { box: imgs, imgs, lh: NaN };
}
/** lineBoxes for the line at `lineStart` of html block `b`. */
const lineBoxesAt = (md: Element, source: string, spans: SourceRange[], b: number, lineStart: number): LineBoxes | null => lineBoxes(md, source, b, linePictures(md, source, spans, b, lineStart));

// ── the shut fold a seat from Raw stands under (the header: the summary at the edge at most) ──────────────
/** The box of the summary of the shut fold hiding `el` (a kept block's element the view does not show): the nearest
 *  `<details>` ancestor whose summary the view shows (a fold inside a shut fold is hidden with it, and the fold outside is
 *  the one shown); a details with no summary element shows its own marker, whose box stands in. null when no fold shows
 *  one (the element is hidden some other way). */
function shownFoldOf(el: Element): Box | null {
  for (let p = el.parentNode as Element | null; p && p.nodeType === 1; p = p.parentNode as Element | null) {
    if (tagOf(p) !== "DETAILS") continue;
    const box = boxOf(elementsOf(p).find((k) => tagOf(k) === "SUMMARY") || p);
    if (box) return box;
  }
  return null;
}
/** The box of the summary of a SHUT fold that stands right before block `b` in the Rendered view's shown order, or
 *  null. The element before `b`'s first shown element: its previous sibling with a box, or, for the first shown child of
 *  a wrapper, the element before the wrapper; read into the last shown child of every wrapper it is (a centred div whose
 *  last block is a fold), which is the summary when the fold is shut (its content has no box) and a nested block when it
 *  is open, in which case there is no shut fold before `b` and the answer is null. A summary met as the previous sibling
 *  of `b`'s own element makes `b` the first block nested in that fold, which is shown, so the fold is OPEN and the answer
 *  is null too (the Slice 5 review's round 4: read as a shut fold's, it capped the first nested block at the summary from the
 *  fold's own Raw rows, so the `<summary>` row's round trip lost 6px where it had been exact, and the opener's put the
 *  summary at the edge in place of the row's own distance); a stand-in reading rects alone, where a shut fold's content
 *  keeps a box, reaches the same summary with the fold shut, and that is the shut fold's summary as ever. */
function shutFoldBefore(md: Element, source: string, b: number): Box | null {
  let el: Element | null = renderedBlockElements(md, source, b).find((e) => !!boxOf(e)) || null;
  let prev: Element | null = null;
  while (el && !prev) {
    const parent = el.parentNode as Element | null;
    if (!parent) return null;
    const sibs = elementsOf(parent);
    for (let j = sibs.indexOf(el) - 1; j >= 0 && !prev; j--) if (boxOf(sibs[j])) prev = sibs[j];
    if (!prev) el = parent === md ? null : parent;
  }
  for (;;) {
    if (!prev) return null;
    const t = tagOf(prev);
    if (t === "SUMMARY") {
      const fold = prev.parentNode as Element | null;
      return fold && tagOf(fold) === "DETAILS" && fold.getAttribute("open") === null ? boxOf(prev) : null;
    }
    if (t === "DETAILS" && prev.getAttribute("open") === null) return boxOf(elementsOf(prev).find((k) => tagOf(k) === "SUMMARY") || prev);
    const pb = renderedBlockIndex(md, source, prev);
    if (pb < 0 || renderedBlockWrappers(md, source, pb).indexOf(prev) < 0) return null;
    const kids = elementsOf(prev).filter((k) => !!boxOf(k));
    prev = kids.length ? kids[kids.length - 1] : null;
  }
}

// ── lines: the Raw rows, and the code lines of a Rendered code block ─────────────────────────────────
/** The count of line feeds in `s[a, b)`. */
function countNL(s: string, a: number, b: number): number {
  let n = 0;
  for (let i = a; i < b; i++) if (s.charCodeAt(i) === 10) n++;
  return n;
}
/** Line `k` (0-based) of the block's source text, its line ending excluded (a CR before the LF too); null past the
 *  block's last line. */
function lineSpanIn(source: string, span: SourceRange, k: number): SourceRange | null {
  let s = span.start;
  for (let i = 0; i < k; i++) { const nl = source.indexOf("\n", s); if (nl < 0 || nl >= span.end) return null; s = nl + 1; }
  if (s > span.end) return null;
  let e = source.indexOf("\n", s);
  if (e < 0 || e > span.end) e = span.end;
  if (e > s && source.charCodeAt(e - 1) === 13) e--;
  return { start: s, end: e };
}
/** A Rendered markdown code block: its code element (`pre > code`) and how many of the block's source lines the code
 *  does not show (`skip`: the fence line of a fenced block; none for an indented one, whose lines the code shows one
 *  for one, indentation apart). null for any other block, an html block's `<pre>` included: the tag is its first line,
 *  so its lines and the code's are one off, and the block keeps the depth rule (the review round 3). Exported for the
 *  pure part's test (file-view-place-blocks.test.ts): the stand-in's fences have no rows, so only the browser leg reads
 *  a line through it. */
export type Code = { code: Element; skip: number };
export function codeOf(source: string, span: SourceRange, els: Element[]): Code | null {
  if (els.length !== 1 || String(els[0].tagName).toUpperCase() !== "PRE") return null;
  const head = source.slice(span.start, Math.min(span.end, span.start + 8));
  const skip = /^ {0,3}(?:`{3,}|~{3,})/.test(head) ? 1 : /^(?: {4}|\t)/.test(head) ? 0 : -1;
  return skip < 0 ? null : { code: els[0].querySelector("code") || els[0], skip };
}
/** The rows of a code element code-block.ts wrapped (its element children wearing `cl`, one per line, a blank line's
 *  holding no text), in line order; none for a code element nothing wrapped, which then shows no line and keeps the
 *  depth rule (the viewer builds none: mdBlock wraps every `pre code` but the math fill's source fallback, whose block
 *  codeOf refuses). */
const codeRows = (code: Element): Element[] => elementsOf(code).filter((c) => typeof c.getAttribute === "function" && (" " + (c.getAttribute("class") || "") + " ").indexOf(" cl ") >= 0);
/** The code line under the body's top edge in a Rendered code block, when the code's text starts above the edge, as
 *  its source span and its top. The code's rows are read as the Raw rows are: the first row whose box ends below the
 *  edge is the line, its index among the rows its line number (one row per line, so it agrees with anchor-map's
 *  codeLineAt for a position in the row), and its box's top is the line's top. Not a hit test and not a character's
 *  box: a blank line's row holds no character (the hit on its empty `.ct` measured nothing and the line was dropped),
 *  and a text row's glyph top sits under the row's top by the half-leading, while the Raw seat puts a row's TOP there,
 *  so the row above showed at the Raw edge and the way back kept that one (the Slice 3 review, round 2). A code
 *  element with no rows shows no line and the block keeps the depth rule: Slice 2's hit test on the code's first
 *  column, kept here for "the math fill's source fallback", a block codeOf refuses, reached no code element the viewer
 *  builds and went (the review, round 3; file-view-place-blocks.test.ts pins the rowless read over a document that
 *  offers a hit test). */
function renderedLineAt(source: string, span: SourceRange, els: Element[], edge: number): Line | null {
  const c = codeOf(source, span, els);
  if (!c) return null;
  if (!(c.code.getBoundingClientRect().top < edge)) return null;
  const rows = codeRows(c.code);
  const i = topVisibleIndex(rows.length, (j) => bottomOrNaN(rows[j]), edge + 1);
  const box = i < rows.length ? boxOf(rows[i]) : null;
  const ls = box ? lineSpanIn(source, span, i + c.skip) : null;
  return box && ls ? { start: ls.start, end: ls.end, top: box.top - edge } : null;
}
/** Where a source line of block `span` starts in the Rendered code block: its row's top (the top renderedLineAt reads,
 *  a blank line's included: a Range around its empty row read back one zero-height rect at the row's baseline, 9px
 *  under its top, and seated the row 9px high); null for any other block, a code element with no rows (the depth rule)
 *  or a line the code does not show. */
function renderedLineTop(source: string, span: SourceRange, els: Element[], lineStart: number): number | null {
  const c = codeOf(source, span, els);
  if (!c) return null;
  const k = countNL(source, span.start, lineStart) - c.skip;
  const rows = codeRows(c.code);
  const box = k >= 0 && k < rows.length ? boxOf(rows[k]) : null;
  return box ? box.top : null;
}
/** Where a source line of block `span` starts in the Raw view: its row's top; null when the row is not the block's. */
function rawLineTop(code: Element, source: string, span: SourceRange, lineStart: number): number | null {
  const row = rawRowForOffset(code, source, lineStart);
  const sp = row && rawRowSpan(code, source, row);
  if (!row || !sp || sp.start < span.start || sp.start >= span.end) return null;
  const box = boxOf(row);
  return box ? box.top : null;
}

/** The reader's place in `body` as it stands: the top-visible block of the Rendered view (`.fileview-md`'s children,
 *  read to their blocks, an html wrapper's descended into: readRendered) or of the Raw view (the block holding the top
 *  row of `code.hljs .fv-cl`, or the one after a blank row between blocks or after a run of blocks whose rows read as
 *  the block after them, closing tags, comments and a wrapper's own rows: readsAsNext, the header; a block inside a
 *  `<details>` carrying the blocks after the fold, Place.after), read against `source`, the text that view
 *  was painted from, with the line at the edge when the reader is partway into a block that shows lines. null when the
 *  body shows neither view, when nothing is in view (a stand-in with no layout), when no element at or below the top
 *  edge is a block's (whitespace between blocks, an html block's leftover node, a row of a wrapper's block's own: the
 *  next is read), when the top element's pairing is one the map got wrong (the header), or when the Raw rows disagree
 *  with the source. An element showing under a pixel below the edge is not the top one, here and in the code rows: the
 *  browser snaps scrollTop to whole pixels, so a seat lands a block up to half a pixel from where it asked (the Slice 3
 *  review, round 2: at the chat's end, a paragraph's last line seated 0.525px under the edge landed at 0.64 and was
 *  read back as the top block, so the round trip came back 11px off). */
export function readPlace(body: HTMLElement, source: string): Place | null {
  if (!hasBox(body)) return null;
  const edge = body.getBoundingClientRect().top;
  const atTop = !((body.scrollTop || 0) > 0.5);
  const spans = sourceBlockSpans(source);
  const md = body.querySelector(".fileview-md");
  if (md) {
    const carry: Carry = { pic: null, lead: null };
    const found = readRendered(md, source, spans, elementsOf(md), edge, atTop, carry);
    if (found && carry.pic) found.pic = carry.pic;
    if (found && carry.lead) found.lead = carry.lead;
    return found === undefined ? null : found;
  }
  const code = body.querySelector("code.hljs");
  const rows = code ? rawRows(code, source) : null;
  if (!code || !rows) return null;
  for (let i = topVisibleIndex(rows.length, (k) => bottomOrNaN(rows[k]), edge + 1); i < rows.length; i++) {
    const rowBox = boxOf(rows[i]);
    if (!rowBox) continue;
    const span = rawRowSpan(code, source, rows[i]);
    if (!span) return null;
    const held = blockHolding(spans, span.start);
    if (held < 0) return null;
    // a row of a block that renders nothing of its own (closing tags, a comment) or whose element is never seated (a wrapper's
    // own rows) reads as the block after it, as a blank row between blocks does, through a run of such blocks (the header);
    // one that is the document's last block stays its own, seated through the nearest block before it with a box
    // (renderedBoxNear)
    const b = nextShown(source, spans, held);
    const box = rawBlockBox(code, source, spans[b]);
    if (!box) return null;
    // the row is the block's own when the block starts above the edge: a blank row between blocks, or a closing tag's, reads
    // as the block after it, whose rows all start below the row and so below the edge
    const place = placeOf(source, "raw", spans, b, box, edge, atTop, box.top < edge ? { start: span.start, end: span.end, top: rowBox.top - edge } : null);
    // the row at the edge when the block starts at or below it (a blank row, a row read as the block after it, the block's own
    // first row): a reflow of the same Raw text puts the row back where it was (Place.row, the header); partway into the block
    // the line above is that row
    if (!place.line) place.row = { start: span.start, end: span.end, top: rowBox.top - edge };
    // a block inside a `<details>`: the Raw view shows its rows whether the Rendered view folds it shut or not, so the blocks
    // after the fold travel with the place for the seat to stand on when the block is not shown (the header)
    const after = foldStands(code, source, spans, b, edge);
    if (after) place.after = after;
    // the tag line of a picture of a wrapper's block's own (a README's banner): the line the top row is on, or the first `<img`
    // line after the top row in the run of blocks the row reads past (the opener's row, an `<h1>` lead row, the blank before the
    // opener; and, the review's round 5, a comment's row or a closer's before the opener, the outer opener of a wrapper two deep,
    // the blanks beside them, whose blocks hold no tag and whose run reaches the wrapper's block that does), with that line's
    // row travels with the place, and the seat puts the picture where the row was, at the row's fraction of its height when the
    // row straddles the edge, at the row's distance below it otherwise (Place.pic, the header). The block the line is found in
    // is a wrapper's without a second parse: every block of the run reads as the block after it (nextShown), and of those only
    // one that opens a wrapper can hold a tag, a block of closing tags or of comments alone holding none (round 4 asked
    // opensWrapper of the row's block a second time here, a lex and a parse more per scroll frame while the row was on top)
    for (let k = held; k < b; k++) {
      const line = imgLine(source, spans[k], k === held ? imgIndexBefore(source, spans[k], span.start) : 0);
      if (!line) continue;
      const row = rawRowForOffset(code, source, line.start);
      const pb = row ? boxOf(row) : null;
      if (pb) place.pic = { start: line.start, end: line.end, top: pb.top - edge, height: pb.bottom - pb.top };
      break;
    }
    return place;
  }
  return null;
}
/** The reader's place among `kids`, one level of the Rendered view (the root's element children, or an html wrapper's):
 *  the first at or below the edge that is a block's, read as its block with its box; `undefined` when the level holds
 *  none (every child ends above the edge, or is no block's, or is a row of a wrapper's block's own, or has no layout),
 *  so the caller reads on after the level's parent; null for a pairing the map got wrong (ownedElements), which is no
 *  place from any element of it. A child the map names as a wrapper of its block (renderedBlockWrappers) stands for
 *  the blocks the browser nested in it, and its element children are read in its place the same way, recursively; a
 *  child paired to a wrapper's block that is not itself one of the block's wrappers (a `<details>`' summary, a tag the
 *  block closed before opening the wrapper) is a row of the block's own and is passed over for the block after it, so
 *  the wrapper's box at the edge reads the first nested block (the header). The search runs per level, on that level's
 *  boxes alone (the header: the map's index is a whole-shape check per read). From the level's first box on, the row of the
 *  block's own AT the edge (atEdge: the one the edge is inside whose top is nearest it, else the topmost below it) is carried to
 *  the place as Place.lead (the header): the block, the row's ordinal among the block's own rows and its box, for a reflow of the
 *  same Rendered text to put the row back; and the picture at the edge among those rows' pictures (the picture the edge is
 *  inside, or the first one below the edge under a lead `<h1>` the edge is inside; every `<img>` of a row counts, one in a `<p>`
 *  beside the project's name too, and the pictures whose tags share one source line are one box, their union: linePictures)
 *  is carried as Place.pic (the header): the picture's tag line and its box. Not the first in document order: pictures of
 *  different heights on one line sit on a common baseline, so a line of small badges before a tall logo has its tops below the
 *  logo's while it comes first in the DOM (the review's round 5: the badges' line was carried with the edge at the logo's top,
 *  and the Raw seat put the badges' row 96px down and the logo's 276). */
type Carry = { pic: Pic | null; lead: Lead | null };
/** Whether box `a` is nearer the edge than `best` among boxes of one block's own rows (readRendered's carry): a box ending above
 *  the edge never; else, with the edge inside both (the top above the edge, within the pixel the browser snaps scrollTop to), the
 *  one whose top is nearest the edge; a box the edge is inside over one below it; of two below it, the topmost. */
function atEdge(a: Box, best: Box | null, edge: number): boolean {
  if (!(a.bottom > edge + 1)) return false;
  if (!best) return true;
  const ia = a.top < edge + 1, ib = best.top < edge + 1;
  if (ia !== ib) return ia;
  return ia ? a.top > best.top : a.top < best.top;
}
function readRendered(md: Element, source: string, spans: SourceRange[], kids: Element[], edge: number, atTop: boolean, carry: Carry): Place | null | undefined {
  const first = topVisibleIndex(kids.length, (k) => bottomOrNaN(kids[k]), edge + 1);
  for (let i = first; i < kids.length; i++) {
    const b = renderedBlockIndex(md, source, kids[i]);
    if (b < 0 || b >= spans.length) continue;
    const wrappers = renderedBlockWrappers(md, source, b);
    if (wrappers.length) {
      if (wrappers.indexOf(kids[i]) < 0) {   // a row of the wrapper's block's own (its summary, a lead picture): the blocks nested after it are read
        if (i === first && (!carry.lead || !carry.pic)) {
          // the row of the block's own AT the edge, from the level's first box on, is carried to the place (Place.lead, the header)
          // for a reflow of the same Rendered text to put back, and the picture at the edge among those rows' pictures as Place.pic;
          // the walk ends at the first element that is not a row of the block's own (a nested block, a wrapper of the block's). At
          // the edge: of the boxes ending below it, the one the edge is inside whose top is nearest the edge, else the topmost below
          // it (a lead `<h1>` the edge is inside carries the banner under it); not the box the search landed on, since rows on one
          // line share a baseline and the first in the DOM can be the lowest (a line of badges before a logo, the header), and not
          // the deepest, since a seat from the badges' row puts them at the edge with the logo above it, and the way back must
          // read the badges again (atEdge)
          let lead: Element | null = null, lb: Box | null = null;
          for (let j = i; j < kids.length && renderedBlockIndex(md, source, kids[j]) === b && wrappers.indexOf(kids[j]) < 0; j++) {
            const rb = boxOf(kids[j]);
            if (rb && atEdge(rb, lb, edge)) { lead = kids[j]; lb = rb; }
          }
          if (!carry.lead && lead && lb) {
            const k = ownRows(md, source, b).indexOf(lead);
            if (k >= 0) carry.lead = { start: spans[b].start, end: spans[b].end, k, top: lb.top - edge, height: lb.bottom - lb.top };
          }
          if (!carry.pic) {
            // the block's pictures by their tag LINE, each line's as the one box its Raw row inverts (lineBoxes, the header: the
            // pictures' union, since one Raw row holds them all, or the box of the row of the block's own that holds them beside
            // text of the note's, the `<p>` around the logo and the project's name, whose text under the picture the row inverts
            // too; a row of the block's own above the edge ends above it and is passed over by atEdge as its pictures are)
            const pics = picturesOf(md, source, b), lines = pictureLines(source, spans[b]);
            let picLine: SourceRange | null = null, pb: LineBoxes | null = null;
            for (let k = 0; k < lines.length && k < pics.length; k++) {
              if (k > 0 && lines[k].start === lines[k - 1].start) continue;   // one box per line, read at the line's first tag
              const lb = lineBoxes(md, source, b, pics.filter((_, n) => n < lines.length && lines[n].start === lines[k].start));
              if (lb && atEdge(lb.box, pb ? pb.box : null, edge)) { picLine = lines[k]; pb = lb; }
            }
            if (picLine && pb) {
              carry.pic = { start: picLine.start, end: picLine.end, top: pb.box.top - edge, height: pb.box.bottom - pb.box.top };
              if (pb.imgs !== pb.box) {
                carry.pic.imgs = { top: pb.imgs.top - edge, height: pb.imgs.bottom - pb.imgs.top };
                if (pb.lh > 0) carry.pic.lh = pb.lh;   // the row's line-height, for the text under the picture across a reflow (rowPartsTop)
              }
            }
          }
        }
        continue;
      }
      const inner = readRendered(md, source, spans, elementsOf(kids[i]), edge, atTop, carry);
      if (inner !== undefined) return inner;
      continue;   // nothing nested in the wrapper ends below the edge with a layout (a closed details' content, boxOf): the element after it
    }
    const els = ownedElements(md, source, spans[b], b);
    if (!els) return null;   // a pairing the map got wrong (an html block a sanitizer drop reshaped): no place
    const box = union(els.map(boxOf));
    if (!box) continue;
    return placeOf(source, "rendered", spans, b, box, edge, atTop, box.top < edge ? renderedLineAt(source, spans[b], els, edge) : null);
  }
  return undefined;
}

// ── following spans through an edit ─────────────────────────────────────────────────────────────────
/** The two texts' common prefix `p` and suffix `s` (followPassage's own bounds on the span the edit changed). */
function commonEnds(old: string, nw: string): { p: number; s: number } {
  const oldLen = old.length, newLen = nw.length, min = Math.min(oldLen, newLen);
  let p = 0;
  while (p < min && old.charCodeAt(p) === nw.charCodeAt(p)) p++;
  let s = 0;
  while (s < min - p && old.charCodeAt(oldLen - 1 - s) === nw.charCodeAt(newLen - 1 - s)) s++;
  return { p, s };
}
/** Whether a span of the old text lies in the region the edit changed (any of it past the common prefix and before
 *  the common suffix); a span outside it stands where it was, or shifted by the edit's length, with no search. */
const inEdit = (old: string, sp: SourceRange, p: number, s: number): boolean => !(sp.end <= p || sp.start >= old.length - s);
/** Where a span of `old` starts in `nw`, or null when its text stands intact nowhere the edit put text (followPassage:
 *  `gone`, `tied` between copies, or `elsewhere`). Exact and free for a span outside the edit. */
function survive(old: string, nw: string, sp: SourceRange, p: number, s: number): number | null {
  const range = { start: sp.start, end: Math.max(sp.end, sp.start + 1) };
  if (range.end <= p) return range.start;
  if (range.start >= old.length - s) return range.start + (nw.length - old.length);
  const f = followPassage(old, range, nw);
  return f.state === "moved" ? f.range.start : null;
}
/** How many spans INSIDE the edit a walk searches for (followPassage's anchor search over the new text) before it
 *  settles for the spans outside it, which cost nothing: a whole document rewritten is one search per block otherwise. */
const PROBES = 8;

/** Where the kept block stands in `newText`: `at`, an offset inside it (`step` 0); or, when the write rewrote it,
 *  inside the block BEFORE it (`step` 1: the kept block is the one after that), or inside the block AFTER it (`step`
 *  -1: the one before that). Its own offset when the text is unchanged; followed through the edit otherwise
 *  (followPassage: unchanged before the edit, shifted by the edit's length after it, re-found when the block's text
 *  moved whole). A block the edit rewrote, or one whose text recurs so that no copy is its own, is placed by its
 *  neighbours, followed the same way, so a write that inserted paragraphs above AND rewrote the block under the
 *  reader's eye still lands on what replaced it, and one that rewrote that block and the one before it too (a section
 *  rewritten, a preamble added) lands there by the block after; with both neighbours gone as well, by the nearest
 *  block before it that stands, walking outward through the old block table (each block inside the edit one anchor
 *  search, PROBES of them at most; a block outside the edit stands for free), else the nearest after; with none, the
 *  place is where the edit begins, the first character that differs, and no further than the block's own start (a
 *  block that began before the edit keeps its start, since the text there is unchanged). */
export type Followed = { at: number; step: -1 | 0 | 1 };
export function followPlace(place: Place, newText: string): Followed {
  const { at, step } = followBlock(place, newText);
  return { at, step };
}
type Survivor = { at: number; span: SourceRange };
/** followPlace, with `deleted`: the kept block was placed by the block before it, and between that block and the
 *  nearest block after the kept one that stands there is nothing but whitespace in the new text, so nothing stands in
 *  the kept block's place (it was deleted, alone or with its neighbours), and the block the step lands on is that
 *  block after. */
function followBlock(place: Place, newText: string): Followed & { deleted: boolean } {
  const old = place.source;
  if (old === newText) return { at: place.start, step: 0, deleted: false };
  const { p, s } = commonEnds(old, newText);
  const clamp = (n: number) => Math.max(0, Math.min(n, newText.length));
  const f = survive(old, newText, place, p, s);
  if (f !== null) return { at: clamp(f), step: 0, deleted: false };
  const gap = (pred: Survivor, succ: Survivor | null): boolean => !!succ && /^\s*$/.test(newText.slice(pred.at + (pred.span.end - pred.span.start), succ.at));
  // the neighbours the place carries, first: no block table to build
  const g = place.prev ? survive(old, newText, place.prev, p, s) : null;
  const h = place.next ? survive(old, newText, place.next, p, s) : null;
  const pred1 = g !== null && place.prev ? { at: g, span: place.prev } : null, succ1 = h !== null && place.next ? { at: h, span: place.next } : null;
  if (pred1) return { at: clamp(pred1.at), step: 1, deleted: gap(pred1, succ1) };
  if (succ1) return { at: clamp(succ1.at), step: -1, deleted: false };
  // both gone: the old block table, walked outward on each side from the next block on
  const oldSpans = sourceBlockSpans(old);
  const bi = blockIndexAt(oldSpans, place.start);
  const walk = (from: number, dir: -1 | 1): Survivor | null => {
    let budget = PROBES;
    for (let k = from; k >= 0 && k < oldSpans.length; k += dir) {
      const sp = oldSpans[k];
      if (inEdit(old, sp, p, s)) { if (budget <= 0) continue; budget--; }
      const r = survive(old, newText, sp, p, s);
      if (r !== null) return { at: r, span: sp };
    }
    return null;
  };
  const pred = bi >= 0 ? walk(bi - 2, -1) : null;
  const succ = bi >= 0 ? walk(bi + 2, 1) : null;
  if (pred) return { at: clamp(pred.at), step: 1, deleted: gap(pred, succ) };
  if (succ) return { at: clamp(succ.at), step: -1, deleted: false };
  return { at: Math.min(place.start, p), step: 0, deleted: false };
}

/** Where the kept line starts in `newText`, inside `block` (the kept block's span there): its own start when it stands
 *  (followed as a block is: unchanged before the edit, shifted after it, re-found when the edit moved it whole); null
 *  when the write rewrote it, when its text recurs so that no copy is its own (followPassage's `tied`), or when the
 *  line found lies outside the block. Nothing else: a rewritten line's neighbours inside the edit cannot place it
 *  exactly (the header), and the block's depth rule takes over. */
function followLine(place: Place, newText: string, block: SourceRange): number | null {
  const { p, s } = commonEnds(place.source, newText);
  const f = survive(place.source, newText, place.line as Line, p, s);
  return f !== null && f >= block.start && f < block.end ? f : null;
}

/** Where the kept block's top edge goes, measured from the body's top, given the block's box `height` in the view
 *  being seated (`view`): its old distance when it started below the edge; else the reader's depth into it, as a
 *  fraction of the block's height when the block's text is the `same` (a view switch, a reflow: the words at the edge
 *  stay near the edge, whatever the block's height is now) or the view changed, and in pixels when the write changed
 *  the block's text in the same view (30px into a paragraph the session appended to stays 30px in), less whatever the
 *  block is now shorter than it was, so as much of it shows below the edge as showed before, and no further down than
 *  the edge itself (a block that fits shows whole, its top at the edge: seated lower, the tail of the block before it
 *  would come into view above it). A `height` of 0 is a block replaced by nothing (deleted), and answers where the
 *  block after it goes. */
export function seatedTop(place: Place, view: View, height: number, same: boolean): number {
  if (place.top >= 0) return place.top;
  if (same || view !== place.view) return place.height > 0 ? place.top * height / place.height : 0;
  return Math.min(0, place.top + Math.max(0, place.height - height));
}

/** Scroll `body`, now painted from `source`, so the block holding the kept place's offset (followPlace: followed
 *  through any edit, stepped to a neighbour when the block itself was rewritten) sits where the kept block sat: the
 *  kept line where the line sat when the block stands and the line, or a line of the block beside it, does
 *  (followLine); else the block's top where seatedTop puts it, and, for a block deleted under the reader's eye (its
 *  neighbours now adjacent: the block the step lands on is the old neighbour itself), the block after it as a
 *  replacement of no height. A body that stood at its very top goes to its very top. false when the body shows no
 *  text view, when no block stands at or before the offset, or when the block has no box (the Raw rows disagree with
 *  the source; the block's pairing, or the box to borrow, is a wrapper's swallowed run). A write the browser clamps (the
 *  new view is shorter) leaves the body at its end; seatPlaceOutcome says when that happened. */
export function seatPlace(body: HTMLElement, source: string, place: Place): boolean {
  return seatPlaceOutcome(body, source, place).seated;
}
/** How far below the edge a picture's top may stand for the picture to count as AT the edge when a same-view reflow chooses
 *  between the picture's rule and its row's (picOutranksRow, rowPartsTop): the pixel the browser snaps scrollTop to (atEdge's
 *  bound, the read's) and the half pixel a seat's own landing adds to it (ROW_SHOWN's reasoning: a seat asks for a fraction and
 *  the body takes a whole pixel, so a seat lands up to half a pixel from where it asked). Classified exactly (`imgs.top > 0` the
 *  text's part), a text-first `<p>` whose logo's top a whole-pixel scroll landed 0.3 to 0.9px below the edge took the row's
 *  fraction on one step and the picture's on the next, as the landing fell, and the logo drifted 2.6 to 3px per text-size step
 *  at 900 and 380, 2px off after A+, A+, A-, A-, where 78c0806ce's picture rule held it within 0.5 (the review's round 8).
 *  With the top within this band on EITHER side of the edge (the same pixel and half pixel above it, the edge inside the
 *  picture's first pixel) rowPartsTop asks for the picture's top at the WHOLE PIXEL nearest where it stood, the edge or the
 *  pixel above or below it (the top is at the edge, and the browser's scroll can put it nowhere finer: a wheel scroll lands
 *  whole pixels), so the ask is the same on every reflow of the scene and every landing, within half a pixel of it, stays
 *  inside the band, and the four steps A+, A+, A-, A- end where they began; round 8 had asked for the top where it landed, and
 *  the landings walked: at 700 to 800px the logo's top went 0.91, 1.27, 1.75 over A+, A+, past the band, and the first A- took
 *  the row's fraction, 2.5px (the review's closing pass; 380 and 900 had bounced within half a pixel of the start). The band
 *  reaches both ways because a fixed ask needs its landings to stay under it: asked for the edge from 0.45px below it, the top
 *  landed 0.2 above, and the picture's fraction from there asked for each landing again and walked to 0.56 above, 1.01px from
 *  the start over two steps (measured at 300px with the band below the edge alone). */
const PIC_AT_EDGE = 1.5;
/** Whether the pictures of a row of the block's own that holds text beside them stand BESIDE that text on one line, as a 24px
 *  icon does before a README's `<h1>` name, rather than on a line of their own over or under the text, as the logo does in the
 *  `<p>` around it and the project's name: told by the row's line-height (`now.lh`, the row's own), an exact reading of the
 *  row's boxes and no glyph's. The pictures are no taller than a line of the row's text, so the line holds them (a badge, an
 *  icon), or the row is less than a line taller than they are, so no line of text stands over or under them (a tall logo with
 *  the name beside it: a line box holding a picture is the picture and the text's descent below its baseline, and a line of
 *  words over or under it adds the row's line-height at least). Such a row keeps the ROW's rule on a same-view reflow: the line
 *  is what the reader has at the edge, its text grows about its baseline and the picture hangs from that baseline, and no seat
 *  holds both; the row's fraction scales the line about the edge, so the heading's cap tops at the edge hold within half a pixel
 *  per text-size step with the edge 5px into the heading and within 2px with it 8px in (1.1px at 900 and 1.7 at 380 after two
 *  steps, picture-line test 7's bound), and the icon falls with its baseline, 2.5 to 3.8px per step and 5.3 to 7.3 over two,
 *  where the picture's rule held the icon and let the text rise by the line's growth, 4.5px per step at 380 and 3.7 at 900, out
 *  of the pane after two (the review's round 8: rowPartsTop's three parts, text over the picture, the picture and text under it,
 *  took the edge inside the icon for the picture's part, and HEAD flipped between the two rules with the sub-pixel landing, the
 *  icon's top 0.44px below the edge at 900 taking the row's). Without a line-height to read (a stand-in) the parts model stands. */
const picInLine = (now: LineBoxes): boolean => {
  if (!(now.lh > 0)) return false;
  const rowH = now.box.bottom - now.box.top, picH = now.imgs.bottom - now.imgs.top;
  return picH <= now.lh || rowH - picH < now.lh;
};
/** Whether a same-view Rendered reflow seats the place's picture (Place.pic, the picture's rule) rather than the row of the
 *  wrapper's block's own at the edge (Place.lead), the view showing the line's pictures: when the edge is inside the picture
 *  (its top within PIC_AT_EDGE below the edge: the pixel the browser snaps scrollTop to, atEdge's bound, and a seat's own
 *  landing), or the picture stands at or above the row's own top and `row` holds one of the pictures of the carried line. A row's
 *  box can stand poorly for its picture's: an inline `<a>` around a logo has its font's box, 18px at the picture's bottom, so the
 *  row's rule held that box across a text-size step and the logo fell by the font's growth, 2.1px per step, and the `<p>` around
 *  a logo and the project's name, seated by the `<p>`'s fraction, drifted 1.9 to 2.9 (round 6; 701728eae, the picture's rule
 *  alone, held both within 0.1). A row holding no picture of the line (a summary, a lead `<h1>` with the picture below it) keeps
 *  its own rule, the row's growth being what the reader sees; so does a row whose own text stands ABOVE its picture with the edge
 *  in that text, since that text is what the reader sees and the picture below it is not (round 7: taken for holding the
 *  picture, the picture's rule let the name rise 2.9px per text-size step, 6.9 with two lines of words over the logo); and so
 *  does a row whose pictures stand beside its text on one line, an icon before a heading's name, whatever row the edge is in
 *  (picInLine, round 8). A row that holds its picture on a line of its own beside text over or under it is seated by its parts
 *  before this is asked (rowPartsTop), so this decides for a picture that is a row itself or sits in a row without text. */
/** Where a row of a wrapper's block's own that holds its picture beside text (Pic.imgs: the `<p>` around the logo and the project's
 *  name) goes on a same-view Rendered reflow, as its top from the edge. The row is three parts, the text above the picture, the
 *  picture and the text under it, and the text grows with a text-size step or wraps on a pane drag while the picture does not.
 *  The edge inside the picture keeps the picture's fraction of its height, the picture's rule (round 6: held so, where the `<p>`'s
 *  fraction drifted it 1.9 to 2.9px per step); the picture's top AT the edge, within PIC_AT_EDGE either side of it, goes back
 *  at the whole pixel nearest where it stood, a fixed ask whose landings stay in the band (round 8: the band below the edge;
 *  the closing pass: the fixed ask and the band's upper half, PIC_AT_EDGE above). The edge in the text UNDER the picture keeps
 *  its distance from the picture's bottom scaled by the row's LINE-HEIGHT (`before.lh` as read, `now.lh` after the reflow): the
 *  part is lines of that height and the strut between the picture's bottom and its first line, all of which scale with the font
 *  and none of which changes when the part's later lines wrap, so the name under the logo
 *  holds within a pixel across a text-size step (the `<p>`'s fraction moved it 2.3 to 8.7px per step, and the picture held, 1.5 the
 *  other way by the strut's growth; the review's round 7) and exactly across a pane drag that wraps the tagline under it (the
 *  part's own fraction, round 7's rule, took the wrapped lines for growth and moved the name 3.6 to 4.6px on the drag between 900
 *  and 380, and the tagline's line at the edge 9.6 to 12.6, where its line stands where it was; round 8); with no line-height to
 *  read (a stand-in) the part's fraction stands. The edge in the text ABOVE the picture keeps the ROW's fraction, the row's own
 *  rule: for the text at the edge in the row's FIRST line, whose top stays the half-leading under the row's top, the row's
 *  fraction, diluted by the picture that does not grow, moves it 0.1 to 1.3px over two steps (the name 8px in), where the text
 *  part's own fraction moved it by its depth times the line's growth, 1.9 and 2.7 (measured, round 7); with the edge in a SECOND
 *  line of words over the picture the first line's growth lands on it, less the row's shift, so the `<p>` moves 3.7px up over two
 *  steps at 900 and 3.2 at 380 and the words at the edge 4.1 to 4.6 down (measured, round 8; the bound above is the first
 *  line's); the exact seat there would be the line's own top, which this module does not read for Rendered text (the Slice 3
 *  review ruled out a Range hit test). A row below the edge keeps its distance, as any block does. `before` is the row as read
 *  (Pic: the row's box, `imgs` the picture's), `now` its boxes after the reflow (lineBoxes). */
function rowPartsTop(before: Pic, imgs: { top: number; height: number }, now: LineBoxes): number {
  const d = -before.top;                                                                   // the edge's depth into the row
  if (d <= 0) return before.top;
  const above = imgs.top - before.top, picH = imgs.height, below = before.height - above - picH;
  const rowH2 = now.box.bottom - now.box.top, above2 = now.imgs.top - now.box.top, picH2 = now.imgs.bottom - now.imgs.top, below2 = rowH2 - above2 - picH2;
  if (d < above - PIC_AT_EDGE) return before.height > 0 ? before.top * rowH2 / before.height : before.top;   // in the text above the picture: the row's fraction
  if (d < above + Math.min(PIC_AT_EDGE, picH)) return Math.max(-1, Math.min(1, Math.round(imgs.top))) - above2;   // the picture's top AT the edge, within the band either side of it: the whole pixel nearest where it stood
  if (d < above + picH) return (picH > 0 ? imgs.top * picH2 / picH : imgs.top) - above2;     // inside the picture: its fraction
  const dB = d - above - picH;                                                             // under the picture: its distance from the picture's bottom, by the line-height
  const scale = before.lh && before.lh > 0 && now.lh > 0 ? now.lh / before.lh : below > 0 ? below2 / below : 0;
  return -(dB * scale) - picH2 - above2;
}
function picOutranksRow(md: Element, source: string, spans: SourceRange[], place: Place, row: Element): boolean {
  const pic = place.pic;
  if (!pic) return false;
  const pb = blockIndexAt(spans, pic.start);
  if (pb < 0) return false;
  const imgs = linePictures(md, source, spans, pb, pic.start), now = lineBoxes(md, source, pb, imgs);
  if (!now) return false;                       // a picture the view does not show: the row stands
  if (now.box !== now.imgs && picInLine(now)) return false;   // the pictures beside the row's text on one line: the row's rule
  const at = pic.imgs || pic;                   // the pictures' own box (Pic.imgs beside a row's box, the picture's alone otherwise)
  if (at.top < PIC_AT_EDGE) return true;
  if (place.lead && !(at.top < place.lead.top + 1)) return false;   // the row's own content stands above its picture: the row's rule
  const own = imgsIn(row);
  return imgs.some((img) => own.indexOf(img) >= 0);
}
/** The least a row's bottom is asked below the edge when a seat into Raw with the edge inside a picture of a wrapper's block's
 *  own (Place.pic, the one picture the Rendered read carries) means the row to be the top row on a read back: the read passes
 *  over a row within a pixel of the edge (readPlace, `edge + 1`, since the browser snaps scrollTop to whole pixels and a seat
 *  lands up to half a pixel from where it asked), and the landing is within that half pixel, so an ask of two lands at 1.5 or
 *  more. The picture's fraction seat asks for less at a tall picture's foot: with the edge in the last ten pixels of a picture
 *  seven times taller than its tag row (a 900x600 banner, 508px at 900px, over a 72px row) the row's bottom rounded to one
 *  pixel below the edge, the read took the blank row after it, the way back seated the nested heading at that row's distance,
 *  and the picture came back 12 to 20px higher, wholly above the edge (the review's round 7). Clamped, the row is read, and the
 *  picture returns within the clamp scaled by its height over the row's, its foot in view. Two bands of the same class stand
 *  beside the clamp, recorded and not fixed (the review's round 8), each the fraction seat's residual at a picture many times
 *  taller than its row. The band the clamp leaves: with the picture's bottom from about the nested block's gap less the blank
 *  row above the edge to the snap pixel below it (the 508px banner's from 9.5px above to 0.5 below at 900, one whole-pixel
 *  scroll of it) the Rendered read carries no picture (atEdge: its bottom is not past `edge + 1`) and the nested heading at its
 *  distance, 19 to 29px; the Raw seat puts the heading's row there, so the blank row before it ends 1 to 11px below the edge
 *  and the tag row's tail shows above the blank; the read back takes the tag row as the top row, right for a Raw reader with
 *  that tail in view, and carries the picture at its fraction, and the way back returns the banner 23 to 77px lower (18 for a
 *  120px logo at 900, 9 at 380), the heading the reader had at 29px at 106; identical on 78c0806ce and 8924fa17e, and main
 *  refused the wrapper's rows (324px). The Rendered gap is wider than the Raw blank, so no seat keeps the heading's distance
 *  and the tag row out of the read at once; a cap on the heading's Raw distance at the tag row's bottom at the edge (the
 *  shut-fold cap's shape) would trade the banner's 77px for the heading's 10, a change to the distance rule that waits on the
 *  owner's word. And the clamp's scope: a TOP-LEVEL tall picture (an `<a href><img></a>` block or a `![banner]()` paragraph
 *  outside any wrapper) carries no Place.pic and keeps Slice 2's fraction seat (seatedTop, the seat's last branch) unclamped,
 *  so with its foot 1.5 to 5.5px below the edge at 900 its one row's bottom rounds to one pixel, the read passes it, and the
 *  banner comes back with its foot at -9.5px, 11 to 15px higher, wholly above the edge; identical on main 213fde5fa (Slice 2's
 *  seat and Slice 3's threshold), so recorded for the owner and not this slice's to change; at 380 both shapes round-trip. */
const ROW_SHOWN = 2;
/** seatPlace, and whether the browser CLAMPED its write: `seated` is seatPlace's answer; `clamped` is true when the scroll the
 *  seat asked for was not the one the body took (the view is shorter than the one the place was read in and the body stands
 *  at its end, or the seat asked for a position above the body's top), within the pixel the browser snaps a fractional
 *  scrollTop to. A clamped seat leaves the body showing an earlier passage than the reader's, and a read of the body would
 *  name THAT block as the reader's place: file-view.ts keeps the place it seated across a clamp instead, so the swap back
 *  seats the passage the reader had (the Slice 3 review: the Rendered/Raw round trip from the end of the taller view came
 *  back one paragraph early). */
export function seatPlaceOutcome(body: HTMLElement, source: string, place: Place): { seated: boolean; clamped: boolean } {
  let clamped = false;
  const scrollBy = (delta: number) => { const want = body.scrollTop + delta; body.scrollTop = want; clamped = Math.abs(body.scrollTop - want) >= 1; };
  const outcome = (seated: boolean) => ({ seated, clamped });
  if (!hasBox(body)) return outcome(false);
  const md = body.querySelector(".fileview-md");
  const code = md ? null : body.querySelector("code.hljs");
  if (!md && !code) return outcome(false);
  if (place.atTop) { if (body.scrollTop !== 0) body.scrollTop = 0; return outcome(true); }
  const spans = sourceBlockSpans(source);
  const edge = body.getBoundingClientRect().top;
  // a reflow of the same Raw text (a text-size step, the pane dragged, the Comments aside opening or closing): the row at the
  // edge goes back where it was (Place.row, the header), whatever the rows between it and the kept block grew or shrank to; the
  // rows are the Raw view's own lines, so this is exact where the kept block's distance is not (the Slice 5 review, round 4: a comment's
  // row, a closer's, a wrapper's opener or the blank before a fold's opener, read as the block after them, rose 5 to 11px per
  // text-size step, 2.7px for each row between, where the block was its own place before the slice and the row held)
  if (code && place.row && place.view === "raw" && place.source === source) {
    const row = rawRowForOffset(code, source, place.row.start);
    const rb = row ? boxOf(row) : null;
    if (rb) {
      const delta = rb.top - (edge + place.row.top);
      if (Math.abs(delta) >= 0.5) scrollBy(delta);
      return outcome(true);
    }
  }
  // a reflow of the same Rendered text with a shown row of a wrapper's block's own at the edge (its summary, a lead `<h1>`, the
  // `<p>` around its picture: Place.lead, the header): that row goes back where it was, at its fraction of its height when the
  // edge is inside it and at its distance below the edge otherwise, as the picture is seated below, whatever the row grew or
  // shrank to (the Slice 5 review, round 5: the kept block, the block nested after the row or the block after a shut fold, kept
  // its distance and the row's own growth landed above the edge, a wrapping fold title 90px above it on a pane drag from 900 to
  // 380px, 180 to 190 down after the drag back, 23 above it when the Comments aside opened, 4.5 to 4.9 per text-size step,
  // where before the slice the browser's own anchoring held every one within 0.2px); a row the view no longer shows leaves the
  // place to the rules below, and so does a row the place's picture outranks (picOutranksRow: the edge inside the picture or right
  // under it, or the row holding one of its line's pictures at or above its own top; round 6: seated by the row, a linked logo `<a href><img></a>` was held by the anchor's
  // font box, 18px at the picture's bottom, and fell 2.1px per text-size step by the font's growth, where the picture's own box,
  // the rule below, holds it)
  if (md && place.lead && place.view === "rendered" && place.source === source) {
    const lead = place.lead, lb = blockIndexAt(spans, lead.start);
    const row = lb >= 0 && spans[lb].start === lead.start ? ownRows(md, source, lb)[lead.k] : undefined;
    const box = row ? boxOf(row) : null;
    const pic = place.pic;
    // the row is the picture's and holds it on a line of its own beside text over or under it (Pic.imgs, the header): its parts each
    // keep the edge's place in their own height, the picture's rule for the picture, the row's for the text above it and the
    // line-height's for the text under it (rowPartsTop; round 7); a row whose pictures stand beside its text on ONE line, an icon
    // before a heading's name, is no such row and keeps the row's rule below (picInLine, round 8)
    if (box && row && pic && pic.imgs && pic.top === lead.top && pic.height === lead.height) {
      const pb = blockIndexAt(spans, pic.start), now = pb < 0 ? null : lineBoxesAt(md, source, spans, pb, pic.start);
      if (now && now.box !== now.imgs && !picInLine(now)) {
        const delta = (now.box.top - edge) - rowPartsTop(pic, pic.imgs, now);
        if (Math.abs(delta) >= 0.5) scrollBy(delta);
        return outcome(true);
      }
    }
    if (box && row && !picOutranksRow(md, source, spans, place, row)) {
      const delta = (box.top - edge) - seatedTop({ ...place, top: lead.top, height: lead.height }, "rendered", box.bottom - box.top, true);
      if (Math.abs(delta) >= 0.5) scrollBy(delta);
      return outcome(true);
    }
  }
  // the reader's edge inside a picture of a wrapper's block's own (Place.pic, the header): the picture in Rendered, the row of the
  // block's own holding it beside text across a view switch (lineBoxes), or its tag line's row in Raw, at the same fraction of its
  // height, as a top-level picture is seated, or, the picture below the edge
  // with a row of the block's own at it, at the same distance below the edge, and, read from Raw through a SHUT fold's closing
  // row and the rows after it (the fold right before the wrapper), no lower than the fold's summary at the edge, the cap every
  // block read so keeps (shutFoldBefore, below: what the reader had above the row was the fold's source, which Rendered shows
  // as the summary alone; the Slice 5 review, round 5: seated at its row's distance the picture left the paragraph before the
  // fold's tail under the edge, and the way back, that tail's fraction seat, brought the fold's whole source back between,
  // 127px; capped, the row returns above the edge by the rows' excess over the summary's box, the recorded closing-row
  // class); a picture the view does not show (the sanitizer dropped it, a fold hides it) leaves the place to the rules below
  if (place.pic && place.source === source) {
    const pic = place.pic, pb = blockIndexAt(spans, pic.start);
    // the box put where the carried one was: in Raw the line's row; in Rendered from Raw the box one Raw row inverts (lineBoxes: the
    // row's for a `<p>` holding text beside its pictures, the pictures' union otherwise), and for a same-view reflow the pictures'
    // own box against Pic.imgs where a row's box was carried, since the picture does not grow with the text (the header)
    const same = !!md && place.view === "rendered";
    const lb = pb < 0 || !md ? null : lineBoxesAt(md, source, spans, pb, pic.start);
    const box = pb < 0 ? null : md ? (lb ? (same ? lb.imgs : lb.box) : null) : (() => { const row = rawRowForOffset(code as Element, source, pic.start); return row ? boxOf(row) : null; })();
    const ref = same && pic.imgs ? pic.imgs : pic;
    if (box) {
      const height = box.bottom - box.top;
      let top = seatedTop({ ...place, top: ref.top, height: ref.height }, md ? "rendered" : "raw", height, true);
      if (md && place.view === "raw" && top > 0) { const fold = shutFoldBefore(md, source, pb); if (fold) top = Math.min(top, box.top - fold.top); }
      // into Raw with the edge inside the picture: the row shows ROW_SHOWN below the edge at least, so the read back takes it as the top row
      if (!md && top < 0 && top + height < ROW_SHOWN) top = ROW_SHOWN - height;
      const delta = (box.top - edge) - top;
      if (Math.abs(delta) >= 0.5) scrollBy(delta);
      return outcome(true);
    }
  }
  const { at, step, deleted } = followBlock(place, source);
  const found = blockIndexAt(spans, at);
  if (found < 0) return outcome(false);
  const b = Math.max(0, Math.min(spans.length - 1, found + step));
  const els = md ? renderedBlockElements(md, source, b) : [];
  // the kept line, when the block stands or a block stands in its place (a changed block is found through a neighbour,
  // and the line is followed into it; a line found outside it is not the block's)
  if (place.line && place.top < 0 && !deleted) {
    const ls = followLine(place, source, spans[b]);
    const top = ls === null ? null : md ? renderedLineTop(source, spans[b], els, ls) : rawLineTop(code as Element, source, spans[b], ls);
    if (top !== null) {
      const delta = top - (edge + place.line.top);
      if (Math.abs(delta) >= 0.5) scrollBy(delta);
      return outcome(true);
    }
  }
  const view: View = md ? "rendered" : "raw";
  // the kept block read in Raw inside a `<details>` the Rendered view folds shut (Place.after, the header): its elements are
  // there and none is shown (boxOf, checkVisibility), so the seat stands on the first block after the fold the view shows,
  // where that block's own row was, and no lower than the fold's summary at the edge (shownFoldOf: the reader had the fold's
  // source on top, which Rendered shows as its summary; seated at its row's top alone, the carried block put the summary of
  // a long fold off the pane); a fold the person opened shows the kept block itself, and the block is seated as ever; a block
  // the fold hides with no carried block the view shows (none carried: the fold ends the document, or only
  // a comment, a wrapper's end or a reference definition follows it; or none with a box) the seat stands on the summary itself,
  // at the edge, the cap's own limit (the review's round 6: left to the rules below, the seat walked back through the hidden
  // paragraphs to the wrapper's refused block and seated nothing, the numeric scrollTop standing over the shorter view and the
  // summary off the pane at 380px; the pane's end mostly clamps this write, and the clamp holds the Raw place in file-view.ts)
  if (md && place.after && step === 0 && place.source === source) {
    const own = ownedElements(md, source, spans[b], b);
    if (own && own.length && !union(own.map(boxOf))) {
      const fold = shownFoldOf(own[0]);
      for (const s of place.after) {
        const k = blockIndexAt(spans, s.start);
        if (k < 0 || spans[k].start !== s.start) continue;
        const stand = renderedBlockBox(md, source, spans, k);
        if (!stand) continue;
        const delta = (stand.top - edge) - (fold ? Math.min(s.top, stand.top - fold.top) : s.top);
        if (Math.abs(delta) >= 0.5) scrollBy(delta);
        return outcome(true);
      }
      if (fold) {
        const delta = fold.top - edge;
        if (Math.abs(delta) >= 0.5) scrollBy(delta);
        return outcome(true);
      }
    }
  }
  const box = md ? renderedBoxNear(md, source, spans, b) : rawBlockBox(code as Element, source, spans[b]);
  if (!box) return outcome(false);
  // the same block with the same text (a view switch, a reflow, an edit elsewhere), or one the write changed: a
  // paragraph the session added a sentence to is its own span followed intact, and still a longer block now
  const same = step === 0 && source.slice(spans[b].start, spans[b].end) === place.source.slice(place.start, place.end);
  let top = deleted ? seatedTop(place, view, 0, false) : seatedTop(place, view, box.bottom - box.top, same);
  // a block read from Raw below a SHUT fold, through the fold's closing row and the rows after it that render nothing (a blank,
  // a comment, a reference definition), keeps its row's distance only as far as the fold's summary at the edge (shutFoldBefore,
  // the header): lower, the tail of the block before the fold shows under the edge, and the way back reads that tail by its
  // fraction with the fold's whole source between it and the closing row; an open fold shows its content, and the distance stands
  if (md && place.view === "raw" && !deleted && top > 0) {
    const fold = shutFoldBefore(md, source, b);
    if (fold) top = Math.min(top, box.top - fold.top);
  }
  const delta = (box.top - edge) - top;
  if (Math.abs(delta) >= 0.5) scrollBy(delta);
  return outcome(true);
}
/** Block `b`'s box in the Rendered view, or, when it has no element with a layout (a comment, a hidden element, a block
 *  the sanitizer dropped, a wrapper's closing tag, a paragraph nested in a closed `<details>`, which boxOf reads as
 *  none), the nearest block's before it, else after it. null when block `b`'s own pairing, or the nearest before it
 *  with elements, is one the map got wrong or the wrapper's own (a paragraph nested in an OPEN wrapper has its own
 *  element since Slice 5's walk and never reaches the wrapper here; one nested in a closed `<details>` walks back
 *  through the fold's unshown paragraphs to the wrapper's block and seats nothing, the body left where it stands, when
 *  the place carries no block after the fold to stand on (Place.after: a place readPlace read in Raw carries one, so
 *  this walk is reached for such a paragraph only through a place of another making); the wrapper's own rows and the
 *  fold's closing tag reach here only as the document's last block, since readPlace reads their Raw rows as the block
 *  after them): the wrapper's box is the rest of the document's, and no seat is better than that one (the review round
 *  3: a Raw row of `<summary>` seated the run's union, 3200px, in Rendered). */
function renderedBoxNear(md: Element, source: string, spans: SourceRange[], b: number): Box | null {
  const own = ownedElements(md, source, spans[b], b);
  if (!own) return null;
  const box = union(own.map(boxOf));
  if (box) return box;
  for (let k = b - 1; k >= 0; k--) {
    if (!renderedBlockElements(md, source, k).length) continue;
    const els = ownedElements(md, source, spans[k], k);
    if (!els) return null;
    const near = union(els.map(boxOf));
    if (near) return near;
  }
  for (let k = b + 1; k < spans.length; k++) { const after = renderedBlockBox(md, source, spans, k); if (after) return after; }
  return null;
}
