// The reader's place over a wrapper's own PICTURE rows, in headless Chromium over the REAL module (plans/markdown-viewer.md
// Slice 5, item 1b; reader-place.ts Place.pic and Place.lead; the Slice 5 review's round 6). Two scenes the round-5 rules
// got wrong, each measured against 701728eae (the round-4 tree, the picture's rule alone), which held both:
//   - a LINKED logo (`<a href><img></a>` inside `<div align="center">`, the common README header) across a text-size step
//     in Rendered: round 5's Place.lead put the row of the block's own at the edge back where it was, before the picture's
//     rule, and the row here is an inline `<a>` whose box is its FONT's box, 18px tall at the picture's bottom, not the
//     picture's; so A+ held that thin box and the logo fell by the font's growth, 2.1px per step and 4.3 over two, at the
//     edge, 48 and 100px in alike (701728eae: 0.1 and 0.33, the browser's own snap); the `<p align="center">` around a
//     logo, a `<br>` and the project's name, seated by the `<p>`'s fraction, drifted 1.9 to 2.9 per step. Now the picture
//     outranks the row when the edge is inside the picture or the row holds one of its line's pictures (picOutranksRow),
//     and the logo holds within a pixel across A+, A+, A-, A-, a pane drag and the Comments aside;
//   - pictures of DIFFERENT heights on ONE source line (a logo and a 24px badge, `<img> <img>` on one line, a common
//     baseline so the badge's top is 96px below the logo's): round 5's pick carried the picture the edge was inside whose
//     top was nearest it, the badge with the edge 105px into the logo, and the Raw seat put the SHARED row at the badge's
//     fraction (9/24); the way back took the line's first tag, the logo, and seated it at that fraction, 60 to 62px lost
//     (12 to 13 for badges of 48 and 24px; the badge first on the line with the edge 50px into the logo alone, 56).
//     701728eae's first-in-DOM carry named one picture both ways and was exact. One Raw row cannot tell the line's
//     pictures apart, so the line's pictures are ONE box to both reads now, their union (linePictures, lineBoxes), and the
//     trips are exact within the row's whole-pixel snap scaled by the union's height over the row's, test 9's bound.
// The review's round 7 added three (tests 3 to 5), each measured against 78c0806ce (the round-6 tree), which lost all three:
//   - the row's own TEXT above its picture (`<p align="center"><b>Project name here</b><br><img></p>`, the name first) with
//     the edge in the name: round 6's picOutranksRow handed the reflow to the picture whenever the row held one of the line's
//     pictures, wherever the edge was in the row, so the logo below the edge was held and the name at the edge rose 2.9px per
//     text-size step, 6.9 with two lines of words over the logo; now a picture below the row's own top leaves the row its rule;
//   - a `<p>` holding a picture AND text read from the TEXT under the picture: the Rendered read carried no picture (the
//     union ends above the edge) and seated the nested heading at its distance, the Raw read carried the `<p>`'s line as the
//     picture's, and the way back put the pictures' union at the row's fraction, 32 to 71px lost; now the `<p>`'s box is what
//     the one Raw row inverts in both directions (rowOfLine, lineBoxes), and Pic.imgs keeps the pictures' own box for the
//     same-view reflow, which holds the picture and so the name right under it;
//   - a tall picture's last few pixels at the edge: the picture's fraction asked for the tag row's bottom under a pixel below
//     the edge, the browser's snap made it one, the read passed the row for the blank after it, and the banner came back 12
//     to 20px higher, wholly above the edge; now a seat into Raw leaves the row two pixels below the edge at least (ROW_SHOWN).
// Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, paintsReach, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
/** Within the Raw row's whole-pixel snap scaled by the picture's height over the row's (the html leg's test 9 bound). */
const nearScaled = (a: number, b: number, what: string, picH: number, rowH: number) => near(a, b, what, Math.max(1.5, 0.5 * picH / rowH + 1));
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const svg = (w: number, h: number, fill: string) => "data:image/svg+xml;utf8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" fill="${fill}"/></svg>`);
const img = (alt: string, w: number, h: number, fill: string) => `<img src="${svg(w, h, fill)}" alt="${alt}" width="${w}" height="${h}">`;
const LOGO_IMG = img("logo", 200, 120, "darkseagreen");
const BADGE = img("badge", 24, 24, "tomato");
const TALL = img("tall", 24, 48, "gold");
const SHORT = img("short", 24, 24, "tomato");
const readme = (lead: string) => "# Report\n\n" + paras(1, 5) + "\n\n<div align=\"center\">\n" + lead + "\n\n## Centred title\n\n" + paras(6, 8) + "\n\n</div>\n\n" + paras(9, 25) + "\n";
const LINKED = readme(`<a href="https://example.test/">${LOGO_IMG}</a>`);
const P_IMG_TEXT = readme(`<p align="center">${LOGO_IMG}<br><b>Project</b></p>`);
const MIXED_LINE = readme(LOGO_IMG + " " + BADGE);
const BADGE_FIRST = readme(BADGE + " " + LOGO_IMG);
const TWO_HEIGHTS = readme(TALL + " " + SHORT);
/** round 7: the project's name FIRST and the logo under it, the row's own text above its picture; and two lines of words over it */
const P_TEXT_IMG = readme(`<p align="center"><b>Project name here</b><br>${LOGO_IMG}</p>`);
const P_TEXT2_IMG = readme(`<p align="center"><b>Project name here</b><br>A second line of words about it<br>${LOGO_IMG}</p>`);
/** round 7: the logo and a badge on one line inside the `<p>`, the project's name under them */
const P_MIXED = readme(`<p align="center">${LOGO_IMG} ${BADGE}<br><b>Project</b></p>`);
/** round 7: a linked logo over the project's name and a tagline that wraps in a narrow pane */
const P_LINKED_TEXT = readme(`<p align="center"><a href="https://example.test/">${LOGO_IMG}</a><br><b>Project</b><br>A tagline under the logo that wraps in a narrow pane</p>`);
/** round 7: a 900x600 banner in an `<a>`: 508px tall at 900 over one 72px Raw row */
const LINKED_BANNER = readme(`<a href="https://example.test/">${img("banner", 900, 600, "steelblue")}</a>`);

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
const imagesDone = (page: any) => page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 10000 });
/** The first Raw row ending below the body's top edge: its text and its top. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 48), top: Math.round((rr.top - br.top) * 10) / 10 }; }
  return null;
});
/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t)); if (!el) return null;
  const r = el.getBoundingClientRect(); return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10 };
}, [sel, text]);
/** The Rendered picture with that alt: its top from the body's top edge, its height, and its parent row's tag and box. */
const imgByAlt = (page: any, alt: string) => page.evaluate((a: string) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const r10 = (x: number) => Math.round(x * 10) / 10;
  const i = document.querySelector(`.fileview-md img[alt="${a}"]`)!; const r = i.getBoundingClientRect(); const p = i.parentElement!; const pr = p.getBoundingClientRect();
  return { top: r10(r.top - br.top), height: r10(r.height), row: { tag: p.tagName, display: getComputedStyle(p).display, top: r10(pr.top - br.top), height: r10(pr.height) } };
}, alt);
/** Scroll so the picture with that alt has its top `above` px above the body's top edge. */
const imgToEdge = (page: any, alt: string, above = 0) => page.evaluate(([a, x]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!; const i = document.querySelector(`.fileview-md img[alt="${a}"]`)!;
  body.scrollTop += i.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [alt, above]);
const sizeStep = async (page: any, label: string) => { const p: number = await page.evaluate(() => (window as any).__paints); await page.locator(`#romp-fileview button[aria-label="${label}"]`).click(); await paintsReach(page, p + 1); await frames(page, 3); };
const dragTo = async (page: any, width: number) => { const p: number = await page.evaluate(() => (window as any).__paints); await page.setViewportSize({ width, height: 600 }); await paintsReach(page, p + 1); await frames(page, 3); };

test("in a browser, the real module: a same-view reflow in RENDERED with a LINKED logo (`<a href><img></a>` in a centred div) at the edge, 48px in and 100px in holds the logo within a pixel across A+, a second A+ and the two A- back, and so does the `<p align=\"center\"><img><br><b>Project</b></p>` row 48px in; a pane drag to 380 and back and the Comments aside opening and closing hold the linked logo too (the review's round 6: Place.lead, the row's rule, ran before the picture's for every same-view Rendered seat, and the inline `<a>`'s box is its font's, 18px at the picture's bottom, so the logo fell 2.1px per step and 4.3 over two where 701728eae held it within 0.1; the `<p>`'s fraction drifted 1.9 per step; now the picture outranks the row when the edge is inside it or the row holds it)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [name, doc, at] of [["the linked logo at the edge", LINKED, 0], ["the linked logo 48px in", LINKED, 48], ["the linked logo 100px in", LINKED, 100], ["the <p> row's logo 48px in", P_IMG_TEXT, 48]] as const) {
      const where = `${name}, pane 900, text-size steps`;
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: doc } }); await imagesDone(page);
      await imgToEdge(page, "logo", at); await frames(page, 2);
      const before = await imgByAlt(page, "logo");
      near(before.top, -at, where + ": the scene starts with the logo at its place", 1);
      if (doc === LINKED) assert.ok(before.row.tag === "A" && before.row.display === "inline" && before.row.height < 40 && before.row.top > before.top + 60, where + `: the fixture: the logo's row is an inline <a> whose box is its font's, at the picture's bottom (${JSON.stringify(before.row)})`);
      else assert.ok(before.row.tag === "P" && before.row.height > before.height, where + `: the fixture: the logo's row is the <p> holding it and the project's name (${JSON.stringify(before.row)})`);
      await sizeStep(page, "Larger text");
      near((await imgByAlt(page, "logo")).top, before.top, where + ": after A+ the logo is where it was (round 5: 2.1px lower for the linked logo, 1.9 higher in the <p>)", 1);
      await sizeStep(page, "Larger text");
      near((await imgByAlt(page, "logo")).top, before.top, where + ": after a second A+ the logo is where it was (round 5: 4.3px lower for the linked logo, 2.7 higher in the <p>)", 1);
      await sizeStep(page, "Smaller text"); await sizeStep(page, "Smaller text");
      near((await imgByAlt(page, "logo")).top, before.top, where + ": after A- twice the logo is where it was", 1);
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
    {
      const where = "the linked logo 48px in, pane 900, a drag to 380 and back";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: LINKED } }); await imagesDone(page);
      await imgToEdge(page, "logo", 48); await frames(page, 2);
      const before = await imgByAlt(page, "logo");
      await dragTo(page, 380);
      near((await imgByAlt(page, "logo")).top, before.top, where + ": at 380 the logo is where it was");
      await dragTo(page, 900);
      near((await imgByAlt(page, "logo")).top, before.top, where + ": back at 900 the logo is where it was");
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
    {
      const where = "the linked logo at the edge, pane 900, the Comments aside";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: LINKED } }); await imagesDone(page);
      await imgToEdge(page, "logo", 0); await frames(page, 2);
      const before = await imgByAlt(page, "logo");
      await openPanel(page);
      near((await imgByAlt(page, "logo")).top, before.top, where + ": with the aside open the logo is where it was");
      await closePanel(page);
      near((await imgByAlt(page, "logo")).top, before.top, where + ": with the aside closed the logo is where it was");
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: pictures of different heights on ONE source line inside `<div align=\"center\">` (a 200x120 logo and a 24px badge, `<img> <img>`, on a common baseline so the badge's top is 96px below the logo's) are one box to both reads: Rendered to Raw to Rendered with the edge 105px into the logo, and so 9px into the badge, is exact within the row's snap at 900 and 380px, the shared tag row the top Raw row at the LINE's fraction between; the badge first on the line with the edge 50px into the logo alone, and two badges of 48 and 24px with the edge 12px into the short one, the same (the review's round 6: round 5 carried the picture the edge was inside whose top was nearest, the badge, seated the shared row at the badge's fraction, and the way back took the line's first tag, the logo, at that fraction, 60 to 62px lost, 56 for the badge-first line, 12 to 13 for the two badges; 701728eae named one picture both ways and was exact; main refused the rows)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SCENES: Array<[string, string, string, string, number, number]> = [
      // name, doc, the picture tracked, the line's tallest picture (the union's height is its), px of the tracked picture above the edge, the union's height
      ["the logo and a badge, the edge 105px into the logo", MIXED_LINE, "logo", "logo", 105, 120],
      ["the logo and a badge, the edge 50px into the logo (the badge wholly below the edge)", MIXED_LINE, "logo", "logo", 50, 120],
      ["the badge first, the edge 50px into the logo", BADGE_FIRST, "logo", "logo", 50, 120],
      ["badges of 48 and 24px, the edge 12px into the short one", TWO_HEIGHTS, "short", "tall", 12, 48],
    ];
    for (const width of [900, 380]) {
      for (const [name, doc, alt, tallest, above, unionH] of SCENES) {
        const where = `pane ${width}, ${name}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc } }); await imagesDone(page);
        const shape = await page.evaluate((tall: string) => {
          const imgs = Array.from(document.querySelectorAll(".fileview-md img")) as HTMLImageElement[]; const t = imgs.find((i) => i.alt === tall)!.getBoundingClientRect();
          return { count: imgs.length, sameBottom: imgs.every((i) => Math.abs(i.getBoundingClientRect().bottom - t.bottom) < 0.5), topsBelow: imgs.every((i) => i.getBoundingClientRect().top >= t.top - 0.5), parent: imgs[0].parentElement!.tagName };
        }, tallest);
        assert.deepEqual(shape, { count: 2, sameBottom: true, topsBelow: true, parent: "DIV" }, where + ": the fixture: two pictures on one line box, a common baseline, the tallest topmost, rows of the div's block");
        await imgToEdge(page, alt, above); await frames(page, 2);
        const before = await imgByAlt(page, alt), tallBefore = await imgByAlt(page, tallest);
        near(before.top, -above, where + ": the scene starts with the picture at its place", 1);
        assert.equal(Math.round(tallBefore.height), unionH, where + ": the fixture: the line's tallest picture is the union's height");
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        const rowBox = (await box(page, "code.hljs .fv-cl", `alt="${alt}"`))!;
        const rowH = rowBox.bottom - rowBox.top;
        assert.ok(row.text.startsWith("<img src="), where + `: the line's tag row is the top Raw row (got ${JSON.stringify(row.text)} at ${row.top})`);
        // the shared row at the LINE's fraction: the union's top (the tallest picture's) over the union's height, scaled to the row
        near(rowBox.top, tallBefore.top * rowH / unionH, where + ": the row at the line's fraction of its height (round 5: at the fraction of the one picture the edge was inside whose top was nearest)", 1.5);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgByAlt(page, alt);
        nearScaled(after.top, before.top, where + `: back in Rendered the picture is where it was (round 5: the line's first tag seated at the other picture's fraction)`, unionH, rowH);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

// ── round 7 ──────────────────────────────────────────────────────────────────────────────────────────
/** The box of the first element under `.fileview-md` matching `sel`, from the body's top edge. */
const elBox = (page: any, sel: string) => page.evaluate((s: string) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect(); const r10 = (x: number) => Math.round(x * 10) / 10;
  const el = document.querySelector(".fileview-md " + s)!; const r = el.getBoundingClientRect();
  return { top: r10(r.top - br.top), bottom: r10(r.bottom - br.top), height: r10(r.height), tag: el.tagName };
}, sel);
/** Scroll so the first element under `.fileview-md` matching `sel` has its top `into` px above the body's top edge. */
const elToEdge = (page: any, sel: string, into: number) => page.evaluate(([s, x]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!; const el = document.querySelector(".fileview-md " + s)!;
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [sel, into]);
/** Scroll so the picture with that alt has its BOTTOM `below` px below the body's top edge. */
const imgBottomTo = (page: any, alt: string, below: number) => page.evaluate(([a, x]: [string, number]) => {
  const body = document.querySelector(".fileview-body")!; const i = document.querySelector(`.fileview-md img[alt="${a}"]`)!;
  body.scrollTop += i.getBoundingClientRect().bottom - body.getBoundingClientRect().top - x;
}, [alt, below]);
/** The Raw row whose text includes `text`: its box from the body's top edge. */
const rowBox = (page: any, text: string) => box(page, "code.hljs .fv-cl", text);

test("in a browser, the real module: a same-view reflow in RENDERED with a row's own TEXT above its picture at the edge (`<p align=\"center\"><b>Project name here</b><br><img></p>`, the name first, the edge 8px into the name; and with two lines of words over the logo) keeps the row's rule and holds the name within 1.5px across A+, a second A+ and the two A- back, at 900 and 380px; the logo first with the edge 48px into it, the control, holds the logo as before (the review's round 7: round 6's picOutranksRow handed the reflow to the picture whenever the row held one of the line's pictures, wherever the edge was in the row, so the logo below the edge was held and the name the reader had at the edge rose 2.9px per step and 5.7 over two, 6.9 and 12.7 with two lines, where 8924fa17e's row rule had held it within 1.3; now a picture below the row's own top leaves the row its rule)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      for (const [name, doc] of [["the name over the logo", P_TEXT_IMG], ["two lines of words over the logo", P_TEXT2_IMG]] as const) {
        const where = `pane ${width}, ${name}, the edge 8px into the name, text-size steps`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc } }); await imagesDone(page);
        await elToEdge(page, "div[align] b", 8); await frames(page, 2);
        const text0 = await elBox(page, "div[align] b"), logo0 = await imgByAlt(page, "logo");
        near(text0.top, -8, where + ": the scene starts with the name 8px into the edge", 1);
        assert.ok(logo0.top > 8 && logo0.row.tag === "P" && logo0.row.top < text0.top + 1, where + `: the fixture: the logo is wholly below the edge inside the <p> whose own text stands above it (${JSON.stringify({ text: text0, logo: logo0 })})`);
        const steps: number[] = [];
        for (const label of ["Larger text", "Larger text", "Smaller text", "Smaller text"]) {
          await sizeStep(page, label);
          steps.push(Math.round(((await elBox(page, "div[align] b")).top - text0.top) * 10) / 10);
        }
        for (const [i, d] of steps.entries()) assert.ok(Math.abs(d) <= 1.5, where + `: after step ${i + 1} the name is where it was (moved ${d}px; all steps ${JSON.stringify(steps)}; 78c0806ce: -2.9, -5.7, -2.9, 0 for the name over the logo, -6.9 and -12.7 with two lines)`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
    {
      const where = "pane 900, the logo over the name, the edge 48px into the logo (the control)";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: P_IMG_TEXT } }); await imagesDone(page);
      await imgToEdge(page, "logo", 48); await frames(page, 2);
      const before = await imgByAlt(page, "logo");
      await sizeStep(page, "Larger text"); await sizeStep(page, "Larger text");
      near((await imgByAlt(page, "logo")).top, before.top, where + ": after two A+ the logo is where it was (round 6's pin)", 1);
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
  });
});

test("in a browser, the real module: a `<p align=\"center\">` row of the wrapper's own holding a picture AND text (the logo and a badge over the project's name; a linked logo over the name and a wrapping tagline) round-trips Rendered to Raw to Rendered from the TEXT under the picture, the edge 2px into the name and 150px into the `<p>` (in the tagline), within the row's snap scaled by the `<p>`'s height over the row's at 900 and 380px, the `<p>`'s tag row the top Raw row at the `<p>`'s fraction of its height between, and from the picture 48px in too, the row at the `<p>`'s fraction now, not the picture's; and a text-size step with the name under the logo at the edge holds the name within 1px, the picture held (the review's round 7: the Rendered read carried no picture from the text, the union ending above the edge, and seated the nested heading at its distance, the Raw read carried the `<p>`'s line as the picture's, and the way back put the pictures' union at the row's fraction, 32 and 71px lost at 900, 20 and 51 at 380, 64 and 59 from the tagline; A+ moved the name 2.3 to 8.7px per step by the `<p>`'s fraction; the `<p>`'s box is what the one Raw row inverts, and the picture's own box is what a reflow holds)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const SCENES: Array<[string, string, string, number]> = [
      // name, doc, the element at the edge, px of it above the edge
      ["the logo and a badge over the name, the edge 2px into the name", P_MIXED, "div[align] b", 2],
      ["a linked logo over the name, the edge 2px into the name", P_LINKED_TEXT, "div[align] b", 2],
      ["a linked logo over the name and a tagline, the edge 150px into the <p>", P_LINKED_TEXT, "div[align] p", 150],
      ["the logo and a badge over the name, the edge 48px into the logo (the picture's own trip)", P_MIXED, 'div[align] img[alt="logo"]', 48],
    ];
    for (const width of [900, 380]) {
      for (const [name, doc, sel, into] of SCENES) {
        const where = `pane ${width}, ${name}`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc } }); await imagesDone(page);
        await elToEdge(page, sel, into); await frames(page, 2);
        const target0 = await elBox(page, sel), p0 = await elBox(page, "div[align] p"), logo0 = await imgByAlt(page, "logo");
        near(target0.top, -into, where + ": the scene starts with the element at its depth", 1);
        assert.ok(p0.tag === "P" && p0.top <= logo0.top + 0.5 && p0.bottom > logo0.top + logo0.height + 10, where + `: the fixture: the <p> holds the logo and text under it (${JSON.stringify({ p: p0, logo: logo0 })})`);
        if (sel.endsWith(" b")) assert.ok(logo0.top + logo0.height < -1, where + `: the fixture: the picture ends above the edge (bottom ${logo0.top + logo0.height})`);
        await click(page, "Raw");
        const row = (await rowAtTop(page))!;
        assert.ok(row.text.startsWith('<p align="center">'), where + `: the <p>'s tag row is the top Raw row (got ${JSON.stringify(row.text)} at ${row.top})`);
        const pRow = (await rowBox(page, '<p align="center">'))!;
        const rowH = pRow.bottom - pRow.top;
        near(pRow.top, p0.top * rowH / p0.height, where + `: the row at the <p>'s fraction of its height (the <p> ${p0.height}px, the row ${rowH}; 78c0806ce: the picture's fraction from the picture, the nested heading's distance from the text)`, 1);
        await click(page, "Rendered"); await imagesDone(page);
        const target1 = await elBox(page, sel);
        nearScaled(target1.top, target0.top, where + `: back in Rendered the element is where it was (78c0806ce: ${into === 48 ? "exact" : "32 to 71px down at 900, 20 to 59 at 380"})`, p0.height, rowH);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
      {
        const where = `pane ${width}, the logo and a badge over the name, the edge 2px into the name, text-size steps`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: P_MIXED } }); await imagesDone(page);
        await elToEdge(page, "div[align] b", 2); await frames(page, 2);
        const text0 = await elBox(page, "div[align] b");
        const steps: number[] = [];
        for (const label of ["Larger text", "Larger text", "Smaller text", "Smaller text"]) {
          await sizeStep(page, label);
          steps.push(Math.round(((await elBox(page, "div[align] b")).top - text0.top) * 10) / 10);
        }
        for (const [i, d] of steps.entries()) assert.ok(Math.abs(d) <= 1, where + `: after step ${i + 1} the name is where it was (moved ${d}px; all steps ${JSON.stringify(steps)}; 78c0806ce: -2.5 per step at 900, -2.3 at 380, the <p>'s fraction)`);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});

test("in a browser, the real module: a tall picture in an `<a>` (a 900x600 banner, 508px at 900 over one 72px Raw row) with the reader's edge in its last few pixels, the banner's bottom 8.5 and 5.5px below the edge, round-trips Rendered to Raw to Rendered with the `<a href` row the top Raw row, its bottom two pixels below the edge at least, and the banner back with its foot in view, within two row pixels scaled by the picture's height over the row's; at 380 (the banner 229px) the same edges round-trip within the row's snap scaled, as before (the review's round 7: the picture's fraction asked for the row's bottom under a pixel below the edge, the browser's whole-pixel snap made it exactly one, the read passed the row over for the blank after it, the nested heading was seated at that row's distance, and the banner came back 12 to 20px higher, wholly above the edge; now a seat into Raw leaves the row two pixels below the edge at least, ROW_SHOWN)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [900, 380]) {
      for (const below of [8.5, 5.5]) {
        const where = `pane ${width}, the banner's bottom ${below}px below the edge`;
        const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: LINKED_BANNER } }); await imagesDone(page);
        await imgBottomTo(page, "banner", below); await frames(page, 2);
        const before = await imgByAlt(page, "banner");
        near(before.top + before.height, below, where + ": the scene starts with the banner's foot below the edge", 1);
        assert.ok(before.height > (width === 900 ? 400 : 200) && before.row.tag === "A", where + `: the fixture: a tall linked banner (${JSON.stringify(before)})`);
        await click(page, "Raw");
        const aRow = (await rowBox(page, '<a href="https://example.test/"><img'))!;
        const rowH = aRow.bottom - aRow.top;
        const top = (await rowAtTop(page))!;
        assert.ok(aRow.bottom >= 1.5, where + `: the tag row's bottom is two pixels below the edge at least, so the read back takes it (got ${aRow.bottom}; 78c0806ce: 1, the blank row after it read as the top row${top.text ? "" : ", as here"})`);
        if (width === 900) assert.ok(rowH < before.height / 4, where + `: the fixture: the row is many times shorter than the picture (${rowH} against ${before.height})`);
        await click(page, "Rendered"); await imagesDone(page);
        const after = await imgByAlt(page, "banner");
        assert.ok(after.top + after.height > 1, where + `: back in Rendered the banner's foot is in view (bottom ${after.top + after.height}; 78c0806ce: -9.5 to -11.5, the banner wholly above the edge)`);
        if (width === 900) near(after.top, before.top, where + ": back in Rendered the banner is within two row pixels scaled (78c0806ce: 14 to 20px high)", 2 * before.height / rowH + 1);
        else nearScaled(after.top, before.top, where + ": back in Rendered the banner is where it was, within the row's snap scaled", before.height, rowH);
        assert.deepEqual(errors, [], where + ": no script error");
        await page.close();
      }
    }
  });
});
